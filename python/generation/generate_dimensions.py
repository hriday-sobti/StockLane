"""Synthetic Dimension Generator for StockLane.
Generates:
  - dim_city (4 synthetic cities)
  - dim_store (40 stores, 10 per city, varied capacities and coordinates)
  - dim_product (300 SKUs, realistic price, lead times, shelf life, MOQs, case packs)
  - dim_date (180 days with calendar attributes, deterministic)
  - dim_event (synthetic events like Weekend Rush, Festive Spike, Payday)
  - dim_promotion (SKU-level discount/promotion campaigns)
"""
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_dimensions(config: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    seed = config.get("random_seed", 42)
    rng = np.random.default_rng(seed)
    
    # 1. Dim City
    cities_data = [
        {"city_id": 1, "city_name": "Bengaluru", "region": "South", "demand_multiplier": 1.15},
        {"city_id": 2, "city_name": "Delhi", "region": "North", "demand_multiplier": 1.20},
        {"city_id": 3, "city_name": "Mumbai", "region": "West", "demand_multiplier": 1.25},
        {"city_id": 4, "city_name": "Hyderabad", "region": "South", "demand_multiplier": 1.05},
    ]
    df_city = pd.DataFrame(cities_data)
    
    # 2. Dim Store (10 per city = 40 stores)
    # Centroids for coordinates
    city_coords = {
        1: (12.9716, 77.5946), # Bengaluru
        2: (28.7041, 77.1025), # Delhi
        3: (19.0760, 72.8777), # Mumbai
        4: (17.3850, 78.4867), # Hyderabad
    }
    
    stores_list = []
    store_id_counter = 1
    for city in cities_data:
        c_id = city["city_id"]
        c_name = city["city_name"]
        lat_base, lon_base = city_coords[c_id]
        
        for s_idx in range(1, 11):
            # Spread stores within ~15-20km radius (approx 0.01 deg ~= 1.1 km)
            d_lat = rng.normal(0, 0.05)
            d_lon = rng.normal(0, 0.05)
            capacity = int(rng.choice([65000, 75000, 85000, 95000, 110000]))
            # Some stores naturally high or low demand
            local_multiplier = round(float(rng.uniform(0.80, 1.30)), 2)
            priority = int(rng.choice([1, 2, 3], p=[0.25, 0.50, 0.25])) # 1 = high, 3 = low
            
            stores_list.append({
                "store_id": store_id_counter,
                "city_id": c_id,
                "store_name": f"{c_name[:3].upper()}_DS_{s_idx:02d}",
                "latitude": round(lat_base + d_lat, 6),
                "longitude": round(lon_base + d_lon, 6),
                "capacity_units": capacity,
                "operating_hours": 18, # 06:00 to 24:00 (18 hours)
                "local_demand_multiplier": local_multiplier,
                "store_priority": priority,
                "active_flag": True
            })
            store_id_counter += 1
            
    df_store = pd.DataFrame(stores_list)
    
    # 3. Dim Product (300 SKUs across 10 categories)
    categories_info = [
        {"cat": "Dairy", "subcats": ["Milk", "Curd", "Butter", "Cheese", "Paneer"], "cost_range": (20, 180), "lead_hours": (12, 24), "shelf_life": (3, 10), "velocity": "High"},
        {"cat": "Beverages", "subcats": ["Juices", "Cold Drinks", "Tea & Coffee", "Energy Drinks", "Water"], "cost_range": (15, 120), "lead_hours": (24, 48), "shelf_life": (90, 270), "velocity": "High"},
        {"cat": "Snacks", "subcats": ["Chips", "Biscuits", "Namkeen", "Chocolates", "Nuts"], "cost_range": (10, 150), "lead_hours": (24, 48), "shelf_life": (90, 180), "velocity": "High"},
        {"cat": "Packaged Foods", "subcats": ["Noodles", "Pasta", "Sauces", "Breakfast Cereals", "Ready to Eat"], "cost_range": (25, 200), "lead_hours": (24, 72), "shelf_life": (120, 360), "velocity": "Medium"},
        {"cat": "Fruits & Vegetables", "subcats": ["Fresh Veggies", "Exotic Veggies", "Daily Fruits", "Seasonal Fruits", "Cut Fruits"], "cost_range": (15, 90), "lead_hours": (12, 24), "shelf_life": (2, 5), "velocity": "High"},
        {"cat": "Staples", "subcats": ["Atta & Flours", "Rice", "Dals & Pulses", "Edible Oils", "Spices"], "cost_range": (40, 450), "lead_hours": (48, 96), "shelf_life": (180, 360), "velocity": "Medium"},
        {"cat": "Personal Care", "subcats": ["Soaps & Body Wash", "Hair Care", "Oral Care", "Skin Care", "Sanitary"], "cost_range": (35, 300), "lead_hours": (48, 96), "shelf_life": (360, 720), "velocity": "Low"},
        {"cat": "Household", "subcats": ["Detergents", "Dishwashers", "Cleaners", "Disposables", "Repellents"], "cost_range": (30, 250), "lead_hours": (48, 96), "shelf_life": (360, 720), "velocity": "Low"},
        {"cat": "Baby Care", "subcats": ["Diapers", "Baby Wipes", "Baby Food", "Baby Skincare"], "cost_range": (60, 500), "lead_hours": (48, 96), "shelf_life": (270, 720), "velocity": "Medium"},
        {"cat": "Pet Care", "subcats": ["Dog Food", "Cat Food", "Pet Treats", "Pet Hygiene"], "cost_range": (50, 450), "lead_hours": (48, 96), "shelf_life": (180, 360), "velocity": "Low"},
    ]
    
    products_list = []
    sku_id = 1
    skus_per_cat = 30 # 10 * 30 = 300 SKUs
    for cat_spec in categories_info:
        cat_name = cat_spec["cat"]
        subcats = cat_spec["subcats"]
        cost_min, cost_max = cat_spec["cost_range"]
        lead_min, lead_max = cat_spec["lead_hours"]
        shelf_min, shelf_max = cat_spec["shelf_life"]
        vel_profile = cat_spec["velocity"]
        
        for k in range(1, skus_per_cat + 1):
            subcat = subcats[(k - 1) % len(subcats)]
            cost = round(float(rng.uniform(cost_min, cost_max)), 2)
            margin = float(rng.uniform(0.18, 0.40)) # 18% to 40% margin
            selling_price = round(cost * (1.0 + margin), 2)
            lead_time = int(rng.choice([12, 24, 36, 48, 72])) if lead_max <= 72 else int(rng.choice([24, 48, 72, 96]))
            shelf_life = int(rng.integers(shelf_min, shelf_max + 1))
            
            # MOQs and case packs
            case_pack = int(rng.choice([4, 6, 8, 12, 24]))
            moq_mult = int(rng.choice([1, 2, 3, 4]))
            moq = case_pack * moq_mult
            
            p_class = "A" if vel_profile == "High" and k <= 10 else ("B" if vel_profile in ["High", "Medium"] else "C")
            
            products_list.append({
                "sku_id": sku_id,
                "sku_name": f"{cat_name[:4].upper()}_{subcat[:4].upper()}_{k:02d}",
                "category": cat_name,
                "subcategory": subcat,
                "unit_cost": cost,
                "selling_price": selling_price,
                "lead_time_hours": lead_time,
                "shelf_life_days": shelf_life,
                "priority_class": p_class,
                "velocity_class": vel_profile,
                "minimum_order_quantity": moq,
                "case_pack_size": case_pack,
                "active_flag": True
            })
            sku_id += 1
            
    df_product = pd.DataFrame(products_list)
    
    # 4. Dim Date (180 days)
    start_str = config.get("start_date", "2026-01-01")
    n_days = config.get("simulation_days", 180)
    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
    
    date_records = []
    for d_idx in range(n_days):
        current_dt = start_dt + timedelta(days=d_idx)
        date_str = current_dt.strftime("%Y-%m-%d")
        date_key = int(current_dt.strftime("%Y%m%d"))
        dow = current_dt.weekday() # 0 = Monday, 6 = Sunday
        is_weekend = dow in [5, 6] # Sat, Sun
        
        date_records.append({
            "date_key": date_key,
            "date": date_str,
            "year": current_dt.year,
            "month": current_dt.month,
            "week": current_dt.isocalendar()[1],
            "day_of_week": dow + 1, # 1=Mon, 7=Sun
            "day_name": current_dt.strftime("%A"),
            "is_weekend": is_weekend,
            "holiday_flag": False, # Updated by events
            "event_flag": False,
            "month_name": current_dt.strftime("%B")
        })
    df_date = pd.DataFrame(date_records)
    
    # 5. Dim Event (Festive, Payday Weekend, Seasonal)
    # Target dates across 180 days
    events_spec = [
        {"event_id": 1, "event_name": "New Year Kickoff", "day_offset_start": 0, "duration": 3, "uplift": 0.35, "category": "Beverages"},
        {"event_id": 2, "event_name": "Republic Day Festive Sale", "day_offset_start": 24, "duration": 3, "uplift": 0.40, "category": "Snacks"},
        {"event_id": 3, "event_name": "Payday Rush Feb", "day_offset_start": 30, "duration": 4, "uplift": 0.25, "category": "Staples"},
        {"event_id": 4, "event_name": "Cricket Tournament Opener", "day_offset_start": 65, "duration": 5, "uplift": 0.45, "category": "Beverages"},
        {"event_id": 5, "event_name": "Payday Rush Mar", "day_offset_start": 59, "duration": 4, "uplift": 0.25, "category": "Household"},
        {"event_id": 6, "event_name": "Holi Festive Surge", "day_offset_start": 80, "duration": 4, "uplift": 0.50, "category": "Dairy"},
        {"event_id": 7, "event_name": "Summer Refresh Week", "day_offset_start": 115, "duration": 7, "uplift": 0.30, "category": "Fruits & Vegetables"},
        {"event_id": 8, "event_name": "Payday Rush May", "day_offset_start": 121, "duration": 4, "uplift": 0.25, "category": "Personal Care"},
        {"event_id": 9, "event_name": "Mid-Year Flash Deals", "day_offset_start": 155, "duration": 5, "uplift": 0.35, "category": "Snacks"},
    ]
    
    event_rows = []
    for ev in events_spec:
        s_date = (start_dt + timedelta(days=ev["day_offset_start"])).strftime("%Y-%m-%d")
        e_date = (start_dt + timedelta(days=ev["day_offset_start"] + ev["duration"] - 1)).strftime("%Y-%m-%d")
        event_rows.append({
            "event_id": ev["event_id"],
            "event_name": ev["event_name"],
            "start_date": s_date,
            "end_date": e_date,
            "demand_uplift_percent": ev["uplift"],
            "affected_category": ev["category"]
        })
    df_event = pd.DataFrame(event_rows)
    
    # Mark event_flag in dim_date
    for _, ev in df_event.iterrows():
        mask = (df_date["date"] >= ev["start_date"]) & (df_date["date"] <= ev["end_date"])
        df_date.loc[mask, "event_flag"] = True
        
    # 6. Dim Promotion (SKU-level campaigns)
    promotions_list = []
    promo_id = 1
    # Pick a random sample of 60 SKUs to receive distinct promotions across the window
    promo_skus = rng.choice(df_product["sku_id"].values, size=60, replace=False)
    for p_sku in promo_skus:
        max_offset = max(1, n_days - 5)
        start_offset = int(rng.integers(0, max_offset))
        duration = int(rng.integers(1, min(14, max(2, n_days - start_offset))))
        p_start = (start_dt + timedelta(days=start_offset)).strftime("%Y-%m-%d")
        p_end = (start_dt + timedelta(days=start_offset + duration)).strftime("%Y-%m-%d")
        p_type = str(rng.choice(["Price Cut 15%", "Buy 1 Get 1", "Weekend Flash 20%", "Bundle Offer"]))
        uplift = round(float(rng.uniform(0.20, 0.45)), 2)
        
        promotions_list.append({
            "promotion_id": promo_id,
            "sku_id": int(p_sku),
            "start_date": p_start,
            "end_date": p_end,
            "promotion_type": p_type,
            "demand_uplift_percent": uplift
        })
        promo_id += 1
    df_promotion = pd.DataFrame(promotions_list)
    
    return {
        "dim_city": df_city,
        "dim_store": df_store,
        "dim_product": df_product,
        "dim_date": df_date,
        "dim_event": df_event,
        "dim_promotion": df_promotion
    }
