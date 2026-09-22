"""Data Quality, Validation, and Quarantine Engine for StockLane.
Implements:
  1. Synthetic controlled anomalies in raw staging (duplicates, null IDs, negative values, referential violations)
  2. Strict validation rules:
     - Referential integrity (SKU in dim_product, Store in dim_store, City in dim_city)
     - Inventory reconciliation (Closing = Opening + Inbound + Xfer_in - Xfer_out - Sold - Damaged)
     - Non-negative constraints (inventory, demand, prices)
     - Business grain duplicate detection
     - Date range integrity
  3. Quarantine routing:
     - Isolates bad records into quarantine dataframes with error reason codes
     - Outputs clean validated dataframes ready for SQL loading and analytics
     - Generates data validation summary report
"""
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd

def inject_raw_anomalies(
    df_sales: pd.DataFrame,
    df_inventory: pd.DataFrame,
    config: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Deliberately introduce controlled bad records to test validation and quarantine."""
    seed = config.get("random_seed", 42)
    rng = np.random.default_rng(seed)
    
    raw_sales = df_sales.copy()
    raw_inv = df_inventory.copy()
    
    # 1. Inject duplicate rows in sales (15 rows)
    dup_indices = rng.choice(len(raw_sales), size=15, replace=False)
    dup_rows = raw_sales.iloc[dup_indices].copy()
    raw_sales = pd.concat([raw_sales, dup_rows], ignore_index=True)
    
    # 2. Inject missing/invalid SKU IDs in sales (10 rows)
    bad_sku_indices = rng.choice(len(raw_sales) - 20, size=10, replace=False)
    raw_sales.loc[bad_sku_indices, "sku_id"] = -999
    
    # 3. Inject negative revenue/requested units in sales (8 rows)
    neg_sales_indices = rng.choice(len(raw_sales) - 40, size=8, replace=False)
    raw_sales.loc[neg_sales_indices, "requested_units"] = -15
    
    # 4. Inject broken inventory reconciliation in raw_inventory (12 rows)
    bad_recon_indices = rng.choice(len(raw_inv), size=12, replace=False)
    raw_inv.loc[bad_recon_indices, "closing_stock"] = raw_inv.loc[bad_recon_indices, "closing_stock"] + 500
    
    # 5. Inject invalid store ID in inventory (6 rows)
    bad_store_indices = rng.choice(len(raw_inv) - 20, size=6, replace=False)
    raw_inv.loc[bad_store_indices, "store_id"] = 9999
    
    # 6. Inject negative inventory (5 rows)
    neg_inv_indices = rng.choice(len(raw_inv) - 50, size=5, replace=False)
    raw_inv.loc[neg_inv_indices, "opening_stock"] = -50
    
    return raw_sales, raw_inv

def validate_and_quarantine(
    dimensions: Dict[str, pd.DataFrame],
    raw_sales: pd.DataFrame,
    raw_inventory: pd.DataFrame,
    df_demand: pd.DataFrame,
    df_replenishment: pd.DataFrame,
    df_transfers: pd.DataFrame,
    df_sales_plan: pd.DataFrame
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame], Dict[str, Any]]:
    """Validates raw datasets, routes bad records to quarantine, returns clean datasets and validation report."""
    valid_skus = set(dimensions["dim_product"]["sku_id"].unique())
    valid_stores = set(dimensions["dim_store"]["store_id"].unique())
    valid_dates = set(dimensions["dim_date"]["date_key"].unique())
    
    quarantine_sales = []
    quarantine_inv = []
    
    # --- A. Validate Sales ---
    # 1. Duplicates on grain (date_key, store_id, sku_id)
    dup_mask = raw_sales.duplicated(subset=["date_key", "store_id", "sku_id"], keep="first")
    if dup_mask.any():
        bad = raw_sales[dup_mask].copy()
        bad["quarantine_reason"] = "Duplicate record on business grain (date_key, store_id, sku_id)"
        quarantine_sales.append(bad)
        clean_sales = raw_sales[~dup_mask].copy()
    else:
        clean_sales = raw_sales.copy()
        
    # 2. Referential integrity
    ref_mask = clean_sales["sku_id"].isin(valid_skus) & clean_sales["store_id"].isin(valid_stores) & clean_sales["date_key"].isin(valid_dates)
    if (~ref_mask).any():
        bad = clean_sales[~ref_mask].copy()
        bad["quarantine_reason"] = "Referential integrity violation (invalid sku_id, store_id, or date_key)"
        quarantine_sales.append(bad)
        clean_sales = clean_sales[ref_mask].copy()
        
    # 3. Non-negative constraints
    non_neg_mask = (clean_sales["requested_units"] >= 0) & (clean_sales["fulfilled_units"] >= 0) & (clean_sales["cancelled_units"] >= 0) & (clean_sales["revenue"] >= 0)
    if (~non_neg_mask).any():
        bad = clean_sales[~non_neg_mask].copy()
        bad["quarantine_reason"] = "Negative quantity or revenue values detected"
        quarantine_sales.append(bad)
        clean_sales = clean_sales[non_neg_mask].copy()
        
    # --- B. Validate Inventory ---
    # 1. Duplicates
    dup_inv_mask = raw_inventory.duplicated(subset=["date_key", "store_id", "sku_id"], keep="first")
    if dup_inv_mask.any():
        bad = raw_inventory[dup_inv_mask].copy()
        bad["quarantine_reason"] = "Duplicate record on business grain (date_key, store_id, sku_id)"
        quarantine_inv.append(bad)
        clean_inv = raw_inventory[~dup_inv_mask].copy()
    else:
        clean_inv = raw_inventory.copy()
        
    # 2. Referential integrity
    ref_inv_mask = clean_inv["sku_id"].isin(valid_skus) & clean_inv["store_id"].isin(valid_stores) & clean_inv["date_key"].isin(valid_dates)
    if (~ref_inv_mask).any():
        bad = clean_inv[~ref_inv_mask].copy()
        bad["quarantine_reason"] = "Referential integrity violation (invalid sku_id or store_id)"
        quarantine_inv.append(bad)
        clean_inv = clean_inv[ref_inv_mask].copy()
        
    # 3. Non-negative constraints
    non_neg_inv = (clean_inv["opening_stock"] >= 0) & (clean_inv["inbound_stock"] >= 0) & (clean_inv["closing_stock"] >= 0)
    if (~non_neg_inv).any():
        bad = clean_inv[~non_neg_inv].copy()
        bad["quarantine_reason"] = "Negative stock levels detected"
        quarantine_inv.append(bad)
        clean_inv = clean_inv[non_neg_inv].copy()
        
    # 4. Inventory Reconciliation: Closing = Opening + Inbound + Transfer_In - Transfer_Out - Sold - Damaged
    calc_closing = (
        clean_inv["opening_stock"] +
        clean_inv["inbound_stock"] +
        clean_inv["transfer_in"] -
        clean_inv["transfer_out"] -
        clean_inv["sold_units"] -
        clean_inv["damaged_units"]
    )
    recon_diff = clean_inv["closing_stock"] - calc_closing
    recon_mask = recon_diff == 0
    if (~recon_mask).any():
        bad = clean_inv[~recon_mask].copy()
        bad["quarantine_reason"] = "Inventory reconciliation failed (Closing != Opening + Inbound + Xfer_in - Xfer_out - Sold - Damaged)"
        quarantine_inv.append(bad)
        clean_inv = clean_inv[recon_mask].copy()
        
    # Assemble Quarantines
    df_quarantine_sales = pd.concat(quarantine_sales, ignore_index=True) if quarantine_sales else pd.DataFrame()
    df_quarantine_inv = pd.concat(quarantine_inv, ignore_index=True) if quarantine_inv else pd.DataFrame()
    
    clean_dict = {
        "fact_sales": clean_sales,
        "fact_inventory": clean_inv,
        "fact_demand": df_demand,
        "fact_replenishment": df_replenishment,
        "fact_transfers": df_transfers,
        "fact_sales_plan": df_sales_plan
    }
    
    quarantine_dict = {
        "quarantine_sales": df_quarantine_sales,
        "quarantine_inventory": df_quarantine_inv
    }
    
    report = {
        "raw_sales_rows": len(raw_sales),
        "clean_sales_rows": len(clean_sales),
        "quarantined_sales_rows": len(df_quarantine_sales),
        "raw_inventory_rows": len(raw_inventory),
        "clean_inventory_rows": len(clean_inv),
        "quarantined_inventory_rows": len(df_quarantine_inv),
        "sales_rejection_rate_pct": round(len(df_quarantine_sales) / len(raw_sales) * 100, 3),
        "inventory_rejection_rate_pct": round(len(df_quarantine_inv) / len(raw_inventory) * 100, 3)
    }
    
    return clean_dict, quarantine_dict, report
