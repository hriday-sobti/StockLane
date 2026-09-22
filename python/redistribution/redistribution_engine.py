"""Lateral redistribution module pairing dark stores with surplus inventory
to nearby stores facing stockouts within the same city.
"""
from typing import Dict, Any, List
import numpy as np
import pandas as pd

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates approximate distance between coordinates in km."""
    # Simplified planar approximation for city-scale (~0-30km radius)
    d_lat = (lat1 - lat2) * 110.574
    d_lon = (lon1 - lon2) * 111.320 * np.cos(np.radians((lat1 + lat2) / 2.0))
    return float(np.sqrt(d_lat**2 + d_lon**2))

def run_redistribution_engine(
    dimensions: Dict[str, pd.DataFrame],
    df_health: pd.DataFrame,
    config: Dict[str, Any]
) -> pd.DataFrame:
    df_store = dimensions["dim_store"]
    store_coords = df_store.set_index("store_id")[["latitude", "longitude"]].to_dict("index")
    
    max_dist_km = config.get("transfer_distance_limit_km", 25.0)
    base_cost = config.get("transfer_base_cost", 20.0)
    cost_per_km = config.get("transfer_cost_per_km", 1.50)
    min_xfer_units = config.get("min_transfer_units", 6)
    
    # 1. Classify Deficits and Surpluses
    # Deficit: DoC <= 2.0 and closing_stock <= safety_stock
    deficits = df_health[
        (df_health["days_of_cover"] <= 2.0) | 
        (df_health["closing_stock"] <= df_health["safety_stock"])
    ].copy()
    
    # Surplus: DoC >= 4.0 and closing_stock > (df_health["safety_stock"] + 15)
    surpluses = df_health[
        (df_health["days_of_cover"] >= 4.0) & 
        (df_health["closing_stock"] > (df_health["safety_stock"] + 15))
    ].copy()
    
    # Track mutable source available stock during greedy matching
    source_avail_tracker = surpluses.set_index(["store_id", "sku_id"])["closing_stock"].to_dict()
    
    # Sort destinations by urgency (Risk Score desc, Lost Sales Exposure desc)
    sorted_destinations = deficits.sort_values(
        by=["stockout_risk_score", "lost_sales_exposure"],
        ascending=[False, False]
    )
    
    transfers = []
    transfer_id_counter = 1
    
    for _, dest in sorted_destinations.iterrows():
        d_store = int(dest["store_id"])
        d_city = int(dest["city_id"])
        sku = int(dest["sku_id"])
        d_doc_before = float(dest["days_of_cover"])
        d_risk = int(dest["stockout_risk_score"])
        d_hrs = float(dest["hours_to_stockout"])
        d_daily_demand = float(dest["forecast_daily_mean"])
        d_price = float(dest["selling_price"])
        case_pack = int(dest["case_pack_size"])
        d_target = int(dest["target_stock"])
        d_curr_stock = int(dest["closing_stock"])
        
        # Required units to reach ~3.5 DoC
        needed_units = max(0, int(np.ceil((d_daily_demand * 3.5) - d_curr_stock)))
        if needed_units < min_xfer_units:
            continue
            
        # Find candidate sources in same city for same SKU
        candidate_sources = surpluses[
            (surpluses["city_id"] == d_city) & 
            (surpluses["sku_id"] == sku) & 
            (surpluses["store_id"] != d_store)
        ]
        
        if candidate_sources.empty:
            continue
            
        # Evaluate candidate sources by distance
        d_lat = store_coords[d_store]["latitude"]
        d_lon = store_coords[d_store]["longitude"]
        
        best_source = None
        min_distance = 999999.0
        
        for _, src in candidate_sources.iterrows():
            s_store = int(src["store_id"])
            s_lat = store_coords[s_store]["latitude"]
            s_lon = store_coords[s_store]["longitude"]
            dist_km = haversine_distance_km(d_lat, d_lon, s_lat, s_lon)
            
            if dist_km <= max_dist_km:
                # Check current available inventory at source after prior allocations
                curr_s_stock = source_avail_tracker.get((s_store, sku), int(src["closing_stock"]))
                s_safety = int(src["safety_stock"])
                s_daily_d = float(src["forecast_daily_mean"])
                
                # Protect source: source must retain at least safety stock + 2.5 days demand
                protected_reserve = s_safety + int(np.ceil(s_daily_d * 2.5))
                transferable_from_source = curr_s_stock - protected_reserve
                
                if transferable_from_source >= min_xfer_units and dist_km < min_distance:
                    min_distance = dist_km
                    best_source = (s_store, src, transferable_from_source, dist_km)
                    
        if best_source is not None:
            s_store, src_row, max_transferable, dist_km = best_source
            
            # Determine transfer quantity (bounded by need, source availability, and rounded to case pack)
            raw_qty = min(needed_units, max_transferable)
            # Round down to whole case packs
            qty_case_packs = int(raw_qty // case_pack)
            transfer_qty = qty_case_packs * case_pack
            
            if transfer_qty >= min_xfer_units:
                # Update source tracking
                source_avail_tracker[(s_store, sku)] -= transfer_qty
                
                transfer_cost = round(base_cost + dist_km * cost_per_km, 2)
                
                # Compute before vs after metrics
                s_stock_after = source_avail_tracker[(s_store, sku)]
                d_stock_after = d_curr_stock + transfer_qty
                
                s_doc_after = round(s_stock_after / max(0.2, float(src_row["forecast_daily_mean"])), 2)
                d_doc_after = round(d_stock_after / max(0.2, d_daily_demand), 2)
                
                # Estimated avoided lost sales = (additional days of cover gained * daily demand) * price
                avoided_lost_units = min(transfer_qty, int(np.ceil(d_daily_demand * 2.0)))
                avoided_lost_sales = round(avoided_lost_units * d_price, 2)
                
                reason = (
                    f"Destination projected to breach safety stock within {d_hrs}h (DoC: {d_doc_before:.1f}d). "
                    f"Source retains surplus stock above protection threshold (Post-transfer DoC: {s_doc_after:.1f}d). "
                    f"Distance is {dist_km:.1f}km within configured limit."
                )
                
                transfers.append({
                    "transfer_id": transfer_id_counter,
                    "city_id": d_city,
                    "source_store_id": s_store,
                    "source_store_name": src_row["store_name"],
                    "destination_store_id": d_store,
                    "destination_store_name": dest["store_name"],
                    "sku_id": sku,
                    "sku_name": dest["sku_name"],
                    "category": dest["category"],
                    "recommended_quantity": transfer_qty,
                    "source_doc_before": src_row["days_of_cover"],
                    "source_doc_after": s_doc_after,
                    "destination_doc_before": d_doc_before,
                    "destination_doc_after": d_doc_after,
                    "destination_risk_score": d_risk,
                    "hours_to_stockout": d_hrs,
                    "transfer_distance_km": round(dist_km, 2),
                    "transfer_cost": transfer_cost,
                    "projected_source_stock": s_stock_after,
                    "projected_destination_stock": d_stock_after,
                    "estimated_lost_sales_avoided": avoided_lost_sales,
                    "reason": reason
                })
                transfer_id_counter += 1
                
    df_transfers_rec = pd.DataFrame(transfers)
    return df_transfers_rec
