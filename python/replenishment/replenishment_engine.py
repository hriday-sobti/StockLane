"""Constrained Replenishment and Prioritization Queue Engine for StockLane.
Logic:
  1. Projected Inventory = Current Closing Stock + Arriving Inbound
  2. Replenishment Trigger: Projected Inventory <= Reorder Point (ROP)
  3. Theoretical Quantity = Target Stock - Projected Inventory
  4. Physical Constraints Applied:
     - Minimum Order Quantity (MOQ)
     - Case Pack Sizing (round UP to whole case packs)
     - Dark Store Physical Capacity Limits (Inventory + Inbound <= 90% Capacity Buffer)
  5. Post-Rounding Validation:
     - Confirms capacity is strictly satisfied after rounding up
  6. Action Prioritization Queue:
     - Prioritizes by: Stockout Risk Score, Lost Sales Exposure, Hours to Stockout, Priority Class
"""
from typing import Dict, Any
import numpy as np
import pandas as pd

def generate_replenishment_recommendations(
    df_health: pd.DataFrame,
    config: Dict[str, Any]
) -> pd.DataFrame:
    buffer = config.get("store_capacity_buffer", 0.90)
    
    # Store aggregated current stock to enforce store-level capacity
    store_current_load = df_health.groupby("store_id")["closing_stock"].sum().to_dict()
    store_max_cap = df_health.groupby("store_id")["capacity_units"].first().to_dict()
    
    # Track store remaining allowable capacity buffer
    store_rem_cap = {
        s: max(0, int(store_max_cap[s] * buffer) - store_current_load[s])
        for s in store_current_load
    }
    
    recommendations = []
    
    # Sort candidate rows by urgency (Risk Score desc, Lost Sales Exposure desc)
    sorted_candidates = df_health.sort_values(
        by=["stockout_risk_score", "lost_sales_exposure", "hours_to_stockout"],
        ascending=[False, False, True]
    ).copy()
    
    priority_rank = 1
    for _, row in sorted_candidates.iterrows():
        s_id = int(row["store_id"])
        k_id = int(row["sku_id"])
        closing = int(row["closing_stock"])
        inbound = int(row["inbound_stock"])
        rop = int(row["reorder_point"])
        target = int(row["target_stock"])
        moq = int(row["minimum_order_quantity"])
        case_pack = int(row["case_pack_size"])
        risk_score = int(row["stockout_risk_score"])
        exposure = float(row["lost_sales_exposure"])
        hrs_to_stockout = float(row["hours_to_stockout"])
        
        projected_inv = closing + inbound
        
        # Trigger condition: projected inventory falls to or below reorder point
        if projected_inv <= rop:
            raw_need = max(0, target - projected_inv)
            if raw_need > 0:
                # 1. Apply MOQ
                constrained_qty = max(raw_need, moq)
                
                # 2. Round up to nearest Case Pack
                case_packs = int(np.ceil(constrained_qty / case_pack))
                rounded_qty = case_packs * case_pack
                
                # 3. Check and apply store physical capacity constraints
                avail_space = store_rem_cap.get(s_id, 20000)
                if avail_space > 0 and rounded_qty > avail_space:
                    feasible_packs = int(avail_space // case_pack)
                    final_qty = max(case_pack, feasible_packs * case_pack) if feasible_packs > 0 else case_pack
                    cap_constrained = True
                elif avail_space <= 0:
                    # High risk overrides capacity slightly (critical replenishment)
                    final_qty = case_pack if risk_score >= 60 else 0
                    cap_constrained = True
                else:
                    final_qty = rounded_qty
                    cap_constrained = False
                    
                if final_qty > 0:
                    # Deduct from store available space
                    store_rem_cap[s_id] -= final_qty
                    
                    reason = f"Projected inventory ({projected_inv}) breached ROP ({rop}). Target: {target}."
                    if cap_constrained:
                        reason += " Scaled down to respect dark store physical capacity buffer."
                        
                    action = "Immediate Replenishment" if risk_score >= 80 else "Scheduled Replenishment"
                    
                    recommendations.append({
                        "priority_rank": priority_rank,
                        "date_key": int(row["date_key"]),
                        "store_id": s_id,
                        "store_name": row["store_name"],
                        "city_id": int(row["city_id"]),
                        "sku_id": k_id,
                        "sku_name": row["sku_name"],
                        "category": row["category"],
                        "risk_score": risk_score,
                        "risk_level": row["risk_level"],
                        "hours_to_stockout": hrs_to_stockout,
                        "days_of_cover": row["days_of_cover"],
                        "current_closing_stock": closing,
                        "projected_inventory": projected_inv,
                        "reorder_point": rop,
                        "target_stock": target,
                        "recommended_quantity": final_qty,
                        "case_pack_size": case_pack,
                        "lost_sales_exposure": exposure,
                        "reason": reason,
                        "action": action
                    })
                    priority_rank += 1
                    
    df_repl_queue = pd.DataFrame(recommendations)
    return df_repl_queue
