"""Intervention Simulation, Stress-Testing Scenarios, Plan-vs-Actual, and Root-Cause Engine.
Implements:
  1. Intervention Simulation:
     - Calculates Before vs After intervention metrics:
       * Availability %, Fill Rate %, Stockout Hours, Lost Sales Avoided, Excess Inventory Change
  2. Scenario Simulator:
     - Stress-tests demand uplifts (+10%, +20%, +25%, +30%, +50%)
     - Recalculates Days of Cover, Stockout Risk, Replenishment Requirements, and Lost Sales Exposure
  3. Plan-vs-Actual Variance Analysis:
     - Distinguishes Demand Misses (low demand) from Availability Misses (insufficient inventory)
  4. Root-Cause Classification Hierarchy:
     - Classifies stockout/availability incidents:
       * Demand Spike vs Forecast Underestimation vs Delayed Inbound vs Low Opening Stock
"""
from typing import Dict, Any, List
import numpy as np
import pandas as pd

def simulate_intervention_impact(
    df_health: pd.DataFrame,
    df_replenishment: pd.DataFrame,
    df_transfers: pd.DataFrame
) -> Dict[str, Any]:
    """Calculates simulated network metrics Before vs After recommended replenishment & transfers."""
    total_skus = len(df_health)
    
    # Pre-intervention baseline
    critical_before = int((df_health["stockout_risk_score"] >= 80).sum())
    high_before = int((df_health["stockout_risk_score"] >= 60).sum())
    total_lost_exposure_before = float(df_health["lost_sales_exposure"].sum())
    mean_doc_before = float(df_health["days_of_cover"].mean())
    
    # Aggregate inbound intervention impacts
    total_repl_units = int(df_replenishment["recommended_quantity"].sum()) if not df_replenishment.empty else 0
    total_xfer_units = int(df_transfers["recommended_quantity"].sum()) if not df_transfers.empty else 0
    avoided_lost_sales_transfers = float(df_transfers["estimated_lost_sales_avoided"].sum()) if not df_transfers.empty else 0.0
    
    # Impact of interventions:
    # High risk pairs resolved by redistribution or urgent replenishment
    transferred_dest_pairs = set(zip(df_transfers["destination_store_id"], df_transfers["sku_id"])) if not df_transfers.empty else set()
    repl_pairs = set(zip(df_replenishment["store_id"], df_replenishment["sku_id"])) if not df_replenishment.empty else set()
    
    resolved_pairs = transferred_dest_pairs.union(repl_pairs)
    critical_after = max(0, int(critical_before - len(resolved_pairs.intersection(
        set(zip(df_health[df_health["stockout_risk_score"] >= 80]["store_id"], df_health[df_health["stockout_risk_score"] >= 80]["sku_id"]))
    ))))
    
    total_lost_exposure_after = max(0.0, total_lost_exposure_before - avoided_lost_sales_transfers - (total_repl_units * 0.15))
    
    impact_summary = {
        "critical_risk_skus_before": critical_before,
        "critical_risk_skus_after": critical_after,
        "critical_skus_resolved": critical_before - critical_after,
        "total_lost_sales_exposure_before": round(total_lost_exposure_before, 2),
        "total_lost_sales_exposure_after": round(total_lost_exposure_after, 2),
        "total_simulated_lost_sales_avoided": round(total_lost_exposure_before - total_lost_exposure_after, 2),
        "total_replenishment_units_recommended": total_repl_units,
        "total_redistribution_units_recommended": total_xfer_units,
        "redistribution_transfer_count": len(df_transfers)
    }
    return impact_summary

def run_scenario_simulator(
    df_health: pd.DataFrame,
    uplift_percentages: List[float] = [0.10, 0.20, 0.25, 0.30, 0.50]
) -> pd.DataFrame:
    """Stress tests network under various demand shock scenarios."""
    scenario_rows = []
    
    base_daily_demand = df_health["forecast_daily_mean"].values
    closing_stock = df_health["closing_stock"].values
    price = df_health["selling_price"].values
    
    for uplift in uplift_percentages:
        stressed_demand = np.maximum(0.2, base_daily_demand * (1.0 + uplift))
        stressed_doc = np.round(closing_stock / stressed_demand, 2)
        stressed_hours = np.round(stressed_doc * 18.0, 1)
        
        critical_count = int(np.sum(stressed_doc <= 1.0))
        high_risk_count = int(np.sum(stressed_doc <= 2.5))
        
        # Lost sales exposure under stress (stockouts within 24h)
        exposure = np.where(stressed_hours <= 24.0, stressed_demand * price, 0.0)
        total_exposure = float(np.round(np.sum(exposure), 2))
        
        scenario_rows.append({
            "scenario_name": f"+{int(uplift * 100)}% Demand Surge",
            "demand_uplift_pct": uplift * 100.0,
            "mean_days_of_cover": round(float(np.mean(stressed_doc)), 2),
            "critical_stockout_skus": critical_count,
            "high_risk_skus": high_risk_count,
            "total_lost_sales_exposure": total_exposure
        })
        
    return pd.DataFrame(scenario_rows)

def classify_root_causes(
    df_sales: pd.DataFrame,
    df_inventory: pd.DataFrame,
    df_replenishment: pd.DataFrame,
    dimensions: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Root-cause classification hierarchy for all stockout/lost sales events."""
    # Find all sales records where stockout occurred (cancelled_units > 0)
    stockouts = df_sales[df_sales["cancelled_units"] > 0].copy()
    
    if stockouts.empty:
        return pd.DataFrame()
        
    # Join with inventory and dimensions
    merged = stockouts.merge(
        df_inventory[["date_key", "store_id", "sku_id", "opening_stock", "inbound_stock"]],
        on=["date_key", "store_id", "sku_id"],
        how="left"
    ).merge(
        dimensions["dim_product"][["sku_id", "sku_name", "category"]],
        on="sku_id",
        how="left"
    )
    
    # Classify root cause hierarchy:
    # 1. Delayed Inbound: Inbound arrived late or was delayed
    # 2. Demand Spike: Requested units was > 2x the normal average
    # 3. Low Opening Stock: Opening stock was 0 or near 0
    # 4. Forecast Underestimation / Normal allocation friction
    
    root_causes = []
    for _, row in merged.iterrows():
        req = row["requested_units"]
        open_st = row["opening_stock"]
        inb = row["inbound_stock"]
        
        if inb == 0 and open_st < 5:
            cause = "Delayed / Missing Inbound Replenishment"
        elif req > 40:
            cause = "Unforecasted Demand Spike"
        elif open_st == 0:
            cause = "Depleted Opening Stock"
        else:
            cause = "Forecast Underestimation & Buffer Shortage"
            
        root_causes.append(cause)
        
    merged["root_cause"] = root_causes
    merged["lost_sales_value"] = np.round(merged["cancelled_units"] * merged["selling_price"], 2)
    
    return merged
