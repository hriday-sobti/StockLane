"""Computes store-level Days of Cover, safety stock, reorder thresholds,
and composite stockout risk scores for dark store planning.
"""
from typing import Dict, Any
import numpy as np
import pandas as pd

def calculate_inventory_health_and_risk(
    dimensions: Dict[str, pd.DataFrame],
    df_clean_inventory: pd.DataFrame,
    df_forecast: pd.DataFrame,
    config: Dict[str, Any]
) -> pd.DataFrame:
    df_product = dimensions["dim_product"]
    df_store = dimensions["dim_store"]
    
    # Extract latest snapshot date
    latest_date_key = df_clean_inventory["date_key"].max()
    latest_inv = df_clean_inventory[df_clean_inventory["date_key"] == latest_date_key].copy()
    
    # Merge with dimensions
    merged = latest_inv.merge(
        df_product[["sku_id", "sku_name", "category", "unit_cost", "selling_price", "lead_time_hours", "case_pack_size", "minimum_order_quantity", "priority_class"]],
        on="sku_id",
        how="left"
    ).merge(
        df_store[["store_id", "store_name", "city_id", "store_priority", "capacity_units"]],
        on="store_id",
        how="left"
    ).merge(
        df_forecast,
        on=["store_id", "sku_id"],
        how="left"
    )
    
    # Configuration parameters
    z_score = config.get("z_score", 1.645)
    cov_horizon = config.get("coverage_horizon_days", 7)
    excess_doc_threshold = config.get("excess_days_of_cover", 14.0)
    
    # Calculations
    # Lead time in days (rounded up to min 0.5 day)
    lead_time_days = np.maximum(0.5, merged["lead_time_hours"] / 24.0)
    daily_demand = np.maximum(0.2, merged["forecast_daily_mean"])
    std_demand = np.maximum(0.1, merged["forecast_std_daily"])
    
    # 1. Safety Stock = Z * std * sqrt(lead_time_days)
    safety_stock = np.ceil(z_score * std_demand * np.sqrt(lead_time_days)).astype(int)
    
    # 2. Reorder Point = (daily_demand * lead_time_days) + safety_stock
    reorder_point = np.ceil((daily_demand * lead_time_days) + safety_stock).astype(int)
    
    # 3. Target Stock = (daily_demand * cov_horizon) + safety_stock
    target_stock = np.ceil((daily_demand * cov_horizon) + safety_stock).astype(int)
    
    # 4. Days of Cover = closing_stock / daily_demand
    days_of_cover = np.round(merged["closing_stock"] / daily_demand, 2)
    
    # 5. Hours to Stockout = (closing_stock / daily_demand) * 18 operating hours
    hours_to_stockout = np.round(days_of_cover * 18.0, 1)
    
    # 6. Explainable Stockout Risk Score (0 to 100)
    # Component 1: Coverage ratio = closing_stock / safety_stock
    cov_ratio = merged["closing_stock"] / np.maximum(1, safety_stock)
    # When cov_ratio <= 0.5 -> 100 pts, when cov_ratio >= 2.0 -> 0 pts
    score_coverage = np.clip(100.0 - (cov_ratio / 2.0 * 100.0), 0.0, 100.0)
    
    # Component 2: Hours to stockout
    # <= 6 hours -> 100 pts, >= 48 hours -> 0 pts
    score_timing = np.clip(100.0 - (hours_to_stockout / 48.0 * 100.0), 0.0, 100.0)
    
    # Component 3: SKU & Store Priority
    # Store priority: 1=high, 2=med, 3=low; SKU priority: A=high, B=med, C=low
    prio_map_sku = {"A": 100.0, "B": 60.0, "C": 30.0}
    score_priority = merged["priority_class"].map(prio_map_sku).fillna(50.0).values
    
    # Weighted composite score
    composite_risk = (
        0.50 * score_coverage +
        0.30 * score_timing +
        0.20 * score_priority
    )
    risk_score = np.round(np.clip(composite_risk, 0.0, 100.0)).astype(int)
    
    # Risk Level mapping
    risk_level = np.where(
        risk_score >= 80, "Critical",
        np.where(risk_score >= 60, "High",
        np.where(risk_score >= 30, "Medium", "Low"))
    )
    
    # Overstock Classification
    is_overstocked = (days_of_cover > excess_doc_threshold) | (merged["closing_stock"] > (target_stock * 2.0))
    excess_units = np.maximum(0, merged["closing_stock"] - target_stock)
    
    # Lost Sales Exposure = Estimated daily lost demand * selling price if stockout occurs within 24h
    lost_sales_exposure = np.where(
        hours_to_stockout <= 24.0,
        np.round(daily_demand * merged["selling_price"], 2),
        0.0
    )
    
    df_health = merged.copy()
    df_health["lead_time_days"] = np.round(lead_time_days, 2)
    df_health["safety_stock"] = safety_stock
    df_health["reorder_point"] = reorder_point
    df_health["target_stock"] = target_stock
    df_health["days_of_cover"] = days_of_cover
    df_health["hours_to_stockout"] = hours_to_stockout
    df_health["stockout_risk_score"] = risk_score
    df_health["risk_level"] = risk_level
    df_health["is_overstocked"] = is_overstocked
    df_health["excess_units"] = excess_units
    df_health["lost_sales_exposure"] = lost_sales_exposure
    
    return df_health
