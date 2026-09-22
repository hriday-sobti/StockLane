"""Simulates day-by-day inventory progression for every store-SKU combination,
tracking opening stock, receipts, transfers, sales fulfillment, and closing stock.
"""
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd

def simulate_sales_and_inventory(
    dimensions: Dict[str, pd.DataFrame],
    df_demand: pd.DataFrame,
    config: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    seed = config.get("random_seed", 42)
    rng = np.random.default_rng(seed)
    
    df_product = dimensions["dim_product"]
    df_store = dimensions["dim_store"]
    df_date = dimensions["dim_date"]
    
    price_map = df_product.set_index("sku_id")["selling_price"].to_dict()
    cost_map = df_product.set_index("sku_id")["unit_cost"].to_dict()
    case_pack_map = df_product.set_index("sku_id")["case_pack_size"].to_dict()
    lead_time_map = df_product.set_index("sku_id")["lead_time_hours"].to_dict()
    
    store_ids = sorted(df_store["store_id"].unique())
    sku_ids = sorted(df_product["sku_id"].unique())
    dates = df_date["date"].values
    date_keys = df_date["date_key"].values
    
    n_stores = len(store_ids)
    n_skus = len(sku_ids)
    n_dates = len(dates)
    
    # Store-SKU index lookup
    store_to_idx = {s: i for i, s in enumerate(store_ids)}
    sku_to_idx = {k: j for j, k in enumerate(sku_ids)}
    
    # Initial Opening Stock on Day 0 (approx 3 to 7 days of daily demand)
    # Extract mean daily demand per sku
    sku_mean_demand = df_demand.groupby("sku_id")["latent_demand"].mean().to_dict()
    
    # Current stock state matrix: [n_stores, n_skus]
    stock_state = np.zeros((n_stores, n_skus), dtype=np.int32)
    for s_id in store_ids:
        s_idx = store_to_idx[s_id]
        for k_id in sku_ids:
            k_idx = sku_to_idx[k_id]
            mean_d = sku_mean_demand.get(k_id, 15.0)
            # Some stores intentionally initialized with low stock (to trigger early stockouts)
            # and some with excess stock (to trigger overstock & transfer availability)
            doc_init = rng.uniform(1.0, 9.0)
            stock_state[s_idx, k_idx] = int(np.round(mean_d * doc_init))
            
    # Group demand by date for chronological iteration
    # Index demand by (date, store_id, sku_id)
    demand_lookup = df_demand.set_index(["date", "store_id", "sku_id"])["latent_demand"].to_dict()
    plan_lookup = df_demand.set_index(["date", "store_id", "sku_id"])["forecast_demand"].to_dict()
    
    # Inbound pipeline queue: list of tuples: (delivery_date_idx, store_idx, sku_idx, units, repl_id)
    inbound_pipeline = []
    
    # Pre-allocate result collectors
    sales_records = []
    inventory_records = []
    replenishment_records = []
    transfer_records = []
    sales_plan_records = []
    
    repl_counter = 1
    transfer_counter = 1
    
    # Distances between stores within city for transfer cost/distance simulation
    # Cache store coordinates
    store_coords = df_store.set_index("store_id")[["city_id", "latitude", "longitude"]].to_dict("index")
    
    # Pre-select some pairs of stores in the same city for synthetic inter-store transfers
    # to demonstrate the redistribution mechanism (excess store -> shortage store)
    
    for day_idx in range(n_dates):
        current_date = dates[day_idx]
        current_date_key = date_keys[day_idx]
        
        # 1. Process Arriving Inbound for today
        todays_inbound = np.zeros((n_stores, n_skus), dtype=np.int32)
        remaining_pipeline = []
        for delivery_day, s_idx, k_idx, qty in inbound_pipeline:
            if delivery_day == day_idx:
                todays_inbound[s_idx, k_idx] += qty
            elif delivery_day > day_idx:
                remaining_pipeline.append((delivery_day, s_idx, k_idx, qty))
        inbound_pipeline = remaining_pipeline
        
        # 2. Process Transfers (Transfers initiated on day_idx-1 arrive today or same day)
        transfer_in = np.zeros((n_stores, n_skus), dtype=np.int32)
        transfer_out = np.zeros((n_stores, n_skus), dtype=np.int32)
        
        # Deliberate Redistribution Injection:
        # On selected days, find pairs in same city where one store has high stock and another has low stock
        if day_idx % 7 == 3: # Once a week
            for c_id in [1, 2, 3, 4]:
                city_stores = [s for s, attr in store_coords.items() if attr["city_id"] == c_id]
                if len(city_stores) >= 2:
                    # Pick 5 random SKUs to transfer if surplus exists
                    cand_skus = rng.choice(sku_ids, size=5, replace=False)
                    for c_sku in cand_skus:
                        k_idx = sku_to_idx[c_sku]
                        src_store = city_stores[0]
                        dst_store = city_stores[1]
                        src_idx = store_to_idx[src_store]
                        dst_idx = store_to_idx[dst_store]
                        
                        src_avail = stock_state[src_idx, k_idx]
                        dst_avail = stock_state[dst_idx, k_idx]
                        
                        # If src has > 40 and dst has < 10, transfer 18 units
                        c_pack = case_pack_map.get(c_sku, 6)
                        if src_avail > 40 and dst_avail < 10:
                            xfer_qty = c_pack * 3
                            if src_avail >= xfer_qty + 15: # Protect safety stock
                                transfer_out[src_idx, k_idx] += xfer_qty
                                transfer_in[dst_idx, k_idx] += xfer_qty
                                
                                # Distance calculation approx
                                lat1, lon1 = store_coords[src_store]["latitude"], store_coords[src_store]["longitude"]
                                lat2, lon2 = store_coords[dst_store]["latitude"], store_coords[dst_store]["longitude"]
                                dist_km = round(float(np.sqrt((lat1-lat2)**2 + (lon1-lon2)**2) * 111.0), 2)
                                cost = round(20.0 + dist_km * 1.5, 2)
                                
                                transfer_records.append({
                                    "transfer_id": transfer_counter,
                                    "date_key": current_date_key,
                                    "source_store_id": src_store,
                                    "destination_store_id": dst_store,
                                    "sku_id": c_sku,
                                    "recommended_quantity": xfer_qty,
                                    "executed_quantity": xfer_qty,
                                    "transfer_distance_km": dist_km,
                                    "transfer_cost": cost,
                                    "recommendation_reason": "High source DoC with impending destination stockout breach",
                                    "status": "Completed"
                                })
                                transfer_counter += 1
                                
        # 3. Simulate Sales Fulfillment & Inventory Equation
        # Available for sale = Opening + Inbound + Transfer_In - Transfer_Out
        opening_stock = stock_state.copy()
        
        # Damage rate: small random 0.05% of stock
        damaged = np.zeros((n_stores, n_skus), dtype=np.int32)
        # Apply damage occasionally
        damage_mask = rng.random((n_stores, n_skus)) < 0.02
        raw_damaged = np.zeros((n_stores, n_skus), dtype=np.int32)
        raw_damaged[damage_mask] = rng.integers(1, 3, size=np.sum(damage_mask))
        on_hand_before_damage = np.maximum(0, opening_stock + todays_inbound + transfer_in - transfer_out)
        damaged = np.minimum(raw_damaged, on_hand_before_damage)
        
        # Calculate available stock
        available = on_hand_before_damage - damaged
        
        # Retrieve requested demand matrix for today
        # Fast extraction using array
        requested_arr = np.zeros((n_stores, n_skus), dtype=np.int32)
        planned_arr = np.zeros((n_stores, n_skus), dtype=np.int32)
        for s_idx, s_id in enumerate(store_ids):
            for k_idx, k_id in enumerate(sku_ids):
                requested_arr[s_idx, k_idx] = demand_lookup.get((current_date, s_id, k_id), 0)
                planned_arr[s_idx, k_idx] = plan_lookup.get((current_date, s_id, k_id), 0)
                
        # Sales fulfillment: cannot sell more than available
        sold_units = np.minimum(available, requested_arr)
        cancelled_units = requested_arr - sold_units # Lost sales due to stockouts
        
        # Closing stock calculation (Hard Invariant: Opening + Inbound + Xfer_in - Xfer_out - Sold - Damaged)
        closing_stock = opening_stock + todays_inbound + transfer_in - transfer_out - sold_units - damaged
        # Ensure non-negative invariant
        closing_stock = np.maximum(0, closing_stock)
        
        # Update state for next day
        stock_state = closing_stock.copy()
        
        # 4. Generate Replenishment Orders based on Reorder Logic (Target = 5 days of mean demand)
        # When closing stock < 2 days of demand, place order
        for s_idx, s_id in enumerate(store_ids):
            for k_idx, k_id in enumerate(sku_ids):
                curr_closing = closing_stock[s_idx, k_idx]
                mean_d = sku_mean_demand.get(k_id, 10.0)
                lead_h = lead_time_map.get(k_id, 24)
                lead_days = max(1, int(np.ceil(lead_h / 24.0)))
                c_pack = case_pack_map.get(k_id, 6)
                
                # Check reorder condition
                reorder_point = mean_d * (lead_days + 1.5)
                target_stock = mean_d * (lead_days + 5.0)
                
                if curr_closing <= reorder_point:
                    raw_order = target_stock - curr_closing
                    # Round to case pack
                    order_qty = int(np.ceil(max(raw_order, c_pack) / c_pack) * c_pack)
                    
                    # Operational disruption injection:
                    # 92% Completed on time, 4% Delayed delivery (+1 day), 3% Under-executed (only 70% qty), 1% Cancelled
                    rand_exec = rng.random()
                    status = "Completed"
                    actual_qty = order_qty
                    arr_day = day_idx + lead_days
                    reason_code = "Normal SLA fulfillment"
                    
                    if rand_exec < 0.04: # Delayed
                        status = "Delayed"
                        arr_day += 1
                        reason_code = "Supplier Logistics Bottleneck"
                    elif rand_exec < 0.07: # Under-executed
                        status = "Partially Completed"
                        actual_qty = int(np.floor(order_qty * 0.70 / c_pack) * c_pack)
                        reason_code = "Supplier Capacity Allocation Shortage"
                    elif rand_exec < 0.08: # Cancelled
                        status = "Cancelled"
                        actual_qty = 0
                        reason_code = "Stock Allocation Cancelled at Hub"
                        
                    replenishment_records.append({
                        "replenishment_id": repl_counter,
                        "date_key": current_date_key,
                        "store_id": s_id,
                        "sku_id": k_id,
                        "recommended_quantity": order_qty,
                        "actual_quantity": actual_qty,
                        "recommendation_timestamp": f"{current_date} 06:00:00",
                        "actual_arrival_timestamp": f"{dates[min(arr_day, n_dates-1)]} 08:00:00" if actual_qty > 0 else None,
                        "supplier_source": f"Regional_Hub_{df_store.loc[df_store['store_id']==s_id, 'city_id'].values[0]}",
                        "status": status,
                        "reason_code": reason_code
                    })
                    repl_counter += 1
                    
                    # Schedule inbound arrival
                    if actual_qty > 0 and arr_day < n_dates:
                        inbound_pipeline.append((arr_day, s_idx, k_idx, actual_qty))
                        
        # 5. Collect Day's Records
        # Vectorized assembly for today's sales and inventory
        curr_price_arr = np.array([price_map[k] for k in sku_ids], dtype=np.float32)
        revenue_arr = sold_units * curr_price_arr
        
        # Flatten by store and sku
        s_mesh, k_mesh = np.meshgrid(store_ids, sku_ids, indexing="ij")
        s_flat = s_mesh.flatten()
        k_flat = k_mesh.flatten()
        
        # Append to master lists in batch
        df_day_sales = pd.DataFrame({
            "date_key": current_date_key,
            "store_id": s_flat,
            "sku_id": k_flat,
            "requested_units": requested_arr.flatten(),
            "fulfilled_units": sold_units.flatten(),
            "cancelled_units": cancelled_units.flatten(),
            "selling_price": np.tile(curr_price_arr, n_stores),
            "revenue": np.round(revenue_arr.flatten(), 2)
        })
        sales_records.append(df_day_sales)
        
        df_day_inv = pd.DataFrame({
            "date_key": current_date_key,
            "store_id": s_flat,
            "sku_id": k_flat,
            "opening_stock": opening_stock.flatten(),
            "inbound_stock": todays_inbound.flatten(),
            "transfer_in": transfer_in.flatten(),
            "transfer_out": transfer_out.flatten(),
            "sold_units": sold_units.flatten(),
            "damaged_units": damaged.flatten(),
            "closing_stock": closing_stock.flatten()
        })
        inventory_records.append(df_day_inv)
        
        # Sales Plan Records (Plan vs Actual Requested vs Fulfilled)
        variance_units = sold_units.flatten() - planned_arr.flatten()
        var_pct = np.where(planned_arr.flatten() > 0, np.round(variance_units / planned_arr.flatten(), 4), 0.0)
        df_day_plan = pd.DataFrame({
            "date_key": current_date_key,
            "store_id": s_flat,
            "sku_id": k_flat,
            "planned_units": planned_arr.flatten(),
            "actual_requested_units": requested_arr.flatten(),
            "actual_fulfilled_units": sold_units.flatten(),
            "variance_units": variance_units,
            "variance_percent": var_pct
        })
        sales_plan_records.append(df_day_plan)
        
    df_sales = pd.concat(sales_records, ignore_index=True)
    df_inventory = pd.concat(inventory_records, ignore_index=True)
    df_sales_plan = pd.concat(sales_plan_records, ignore_index=True)
    df_replenishment = pd.DataFrame(replenishment_records)
    df_transfers = pd.DataFrame(transfer_records)
    
    return df_sales, df_inventory, df_replenishment, df_transfers, df_sales_plan
