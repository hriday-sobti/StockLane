"""Consolidated Operations Action Queue Engine for StockLane.
Aggregates prioritized decisions into a single operational interface:
  - Priority Rank
  - Date
  - City / Store / SKU / Category
  - Issue Type (Impending Stockout, Severe Overstock, Inter-Store Misallocation)
  - Risk Score
  - Recommended Action (Replenish, Redistribute, Monitor, Liquidate/Slow Inbound)
  - Recommended Quantity
  - Hours to Stockout
  - Expected Impact
  - Source / Destination Store
  - Explainable Reason
"""
from typing import Dict, Any
import numpy as np
import pandas as pd

def build_action_queue(
    df_health: pd.DataFrame,
    df_replenishment: pd.DataFrame,
    df_transfers: pd.DataFrame
) -> pd.DataFrame:
    action_items = []
    
    # 1. Action Items from Redistribution (Highest Immediate Impact)
    if not df_transfers.empty:
        for _, xfer in df_transfers.iterrows():
            action_items.append({
                "date_key": int(df_health["date_key"].max()),
                "store_name": xfer["destination_store_name"],
                "sku_id": int(xfer["sku_id"]),
                "sku_name": xfer["sku_name"],
                "category": xfer["category"],
                "issue_type": "Inter-Store Misallocation / Impending Shortage",
                "risk_score": int(xfer["destination_risk_score"]),
                "recommended_action": "Redistribute Stock",
                "recommended_quantity": int(xfer["recommended_quantity"]),
                "hours_to_stockout": float(xfer["hours_to_stockout"]),
                "expected_impact": f"Avoids ${xfer['estimated_lost_sales_avoided']:,.2f} lost sales; lifts DoC from {xfer['destination_doc_before']:.1f} to {xfer['destination_doc_after']:.1f}d",
                "source_store": xfer["source_store_name"],
                "destination_store": xfer["destination_store_name"],
                "reason": xfer["reason"]
            })
            
    # 2. Action Items from Replenishment Queue
    if not df_replenishment.empty:
        for _, repl in df_replenishment.iterrows():
            action_items.append({
                "date_key": int(repl["date_key"]),
                "store_name": repl["store_name"],
                "sku_id": int(repl["sku_id"]),
                "sku_name": repl["sku_name"],
                "category": repl["category"],
                "issue_type": "Stock Below Reorder Point",
                "risk_score": int(repl["risk_score"]),
                "recommended_action": repl["action"],
                "recommended_quantity": int(repl["recommended_quantity"]),
                "hours_to_stockout": float(repl["hours_to_stockout"]),
                "expected_impact": f"Protects ${repl['lost_sales_exposure']:,.2f} sales exposure; targets {repl['target_stock']} units",
                "source_store": "Regional Distribution Center",
                "destination_store": repl["store_name"],
                "reason": repl["reason"]
            })
            
    # 3. Action Items from Severe Overstock
    overstocked = df_health[df_health["is_overstocked"]].copy()
    if not overstocked.empty:
        for _, ov in overstocked.head(50).iterrows(): # Top overstock exceptions
            action_items.append({
                "date_key": int(ov["date_key"]),
                "store_name": ov["store_name"],
                "sku_id": int(ov["sku_id"]),
                "sku_name": ov["sku_name"],
                "category": ov["category"],
                "issue_type": "Excess Working Capital / High Days of Cover",
                "risk_score": 15,
                "recommended_action": "Pause Inbound / Consider Promotional Clearance",
                "recommended_quantity": int(ov["excess_units"]),
                "hours_to_stockout": 999.0,
                "expected_impact": f"Rebalances {ov['excess_units']} excess units ({ov['days_of_cover']:.1f} DoC)",
                "source_store": ov["store_name"],
                "destination_store": "N/A",
                "reason": f"Inventory exceeds target by {ov['excess_units']} units with {ov['days_of_cover']:.1f} Days of Cover."
            })
            
    df_queue = pd.DataFrame(action_items)
    if not df_queue.empty:
        # Sort queue by Risk Score desc, Hours to Stockout asc
        df_queue = df_queue.sort_values(by=["risk_score", "hours_to_stockout"], ascending=[False, True]).reset_index(drop=True)
        df_queue.insert(0, "priority_rank", range(1, len(df_queue) + 1))
        
    return df_queue
