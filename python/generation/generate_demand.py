"""Generates daily customer demand across stores and products, incorporating
base velocity, day-of-week patterns, city indices, and marketing campaigns.
"""
from typing import Dict, Any
import numpy as np
import pandas as pd
from datetime import datetime

def generate_demand(dimensions: Dict[str, pd.DataFrame], config: Dict[str, Any]) -> pd.DataFrame:
    seed = config.get("random_seed", 42)
    rng = np.random.default_rng(seed)
    
    df_city = dimensions["dim_city"]
    df_store = dimensions["dim_store"]
    df_product = dimensions["dim_product"]
    df_date = dimensions["dim_date"]
    df_event = dimensions["dim_event"]
    df_promotion = dimensions["dim_promotion"]
    
    # 1. Precompute lookup mappings for high-performance vectorization
    city_mult_map = df_city.set_index("city_id")["demand_multiplier"].to_dict()
    store_city_map = df_store.set_index("store_id")["city_id"].to_dict()
    store_local_mult = df_store.set_index("store_id")["local_demand_multiplier"].to_dict()
    
    # Product baseline demand by category and velocity
    # High velocity: ~25-70 units/day; Medium: ~10-30 units/day; Low: ~2-10 units/day
    prod_vel = df_product.set_index("sku_id")["velocity_class"].to_dict()
    prod_cat = df_product.set_index("sku_id")["category"].to_dict()
    
    sku_base_demand = {}
    for sku_id, vel in prod_vel.items():
        if vel == "High":
            sku_base_demand[sku_id] = float(rng.uniform(25.0, 65.0))
        elif vel == "Medium":
            sku_base_demand[sku_id] = float(rng.uniform(10.0, 28.0))
        else:
            sku_base_demand[sku_id] = float(rng.uniform(2.5, 9.0))
            
    # Day of week factor: quick commerce surges on Fri(1.15), Sat(1.35), Sun(1.40)
    # Mon-Thu: Mon(0.90), Tue(0.85), Wed(0.85), Thu(0.92)
    dow_multipliers = {
        1: 0.90, # Mon
        2: 0.85, # Tue
        3: 0.85, # Wed
        4: 0.92, # Thu
        5: 1.18, # Fri
        6: 1.38, # Sat
        7: 1.42  # Sun
    }
    
    # Build complete cross product of (date x store x sku)
    # 180 dates * 40 stores * 300 skus = 2,160,000 combinations
    # For lightning performance and deterministic vectorized operations, we process by date chunks or arrays
    dates = df_date["date"].values
    date_keys = df_date["date_key"].values
    dows = df_date["day_of_week"].values
    is_weekends = df_date["is_weekend"].values
    
    store_ids = df_store["store_id"].values
    sku_ids = df_product["sku_id"].values
    
    n_dates = len(dates)
    n_stores = len(store_ids)
    n_skus = len(sku_ids)
    total_rows = n_dates * n_stores * n_skus
    
    # Vectorized grid creation
    # Repeating arrays:
    date_key_arr = np.repeat(date_keys, n_stores * n_skus)
    date_str_arr = np.repeat(dates, n_stores * n_skus)
    dow_arr = np.repeat(dows, n_stores * n_skus)
    weekend_arr = np.repeat(is_weekends, n_stores * n_skus)
    
    store_tile = np.tile(np.repeat(store_ids, n_skus), n_dates)
    sku_tile = np.tile(sku_ids, n_dates * n_stores)
    
    # Map factors
    store_mult_arr = np.array([store_local_mult[s] for s in store_ids], dtype=np.float32)
    city_mult_arr = np.array([city_mult_map[store_city_map[s]] for s in store_ids], dtype=np.float32)
    store_factor_full = np.tile(np.repeat(store_mult_arr, n_skus), n_dates)
    city_factor_full = np.tile(np.repeat(city_mult_arr, n_skus), n_dates)
    
    sku_base_arr = np.array([sku_base_demand[k] for k in sku_ids], dtype=np.float32)
    sku_base_full = np.tile(sku_base_arr, n_dates * n_stores)
    
    dow_factor_lookup = np.array([dow_multipliers[d] for d in range(1, 8)], dtype=np.float32)
    dow_factor_full = dow_factor_lookup[dow_arr - 1]
    
    # Seasonality (slight sine cycle over 180 days: +/- 8%)
    t = np.linspace(0, 2 * np.pi, n_dates)
    seasonality_daily = 1.0 + 0.08 * np.sin(t)
    seasonality_full = np.repeat(seasonality_daily, n_stores * n_skus).astype(np.float32)
    
    # Event Uplift mapping: (date, category)
    event_dict = {}
    for _, ev in df_event.iterrows():
        cat = ev["affected_category"]
        s_date = ev["start_date"]
        e_date = ev["end_date"]
        uplift = ev["demand_uplift_percent"]
        # Find matching dates
        m_dates = df_date[(df_date["date"] >= s_date) & (df_date["date"] <= e_date)]["date"].values
        for d in m_dates:
            event_dict[(d, cat)] = 1.0 + uplift
            
    # Promotion Uplift mapping: (date, sku_id)
    promo_dict = {}
    for _, pr in df_promotion.iterrows():
        p_sku = pr["sku_id"]
        s_date = pr["start_date"]
        e_date = pr["end_date"]
        uplift = pr["demand_uplift_percent"]
        m_dates = df_date[(df_date["date"] >= s_date) & (df_date["date"] <= e_date)]["date"].values
        for d in m_dates:
            promo_dict[(d, p_sku)] = 1.0 + uplift
            
    # Category lookup for sku
    sku_cat_arr = np.array([prod_cat[k] for k in sku_ids])
    
    # Base calculation
    expected_demand = (
        sku_base_full *
        dow_factor_full *
        store_factor_full *
        city_factor_full *
        seasonality_full
    )
    
    # Apply promotions and events efficiently
    # Notice that promotions and events affect a subset of rows
    # Event factors:
    event_factors = np.ones(total_rows, dtype=np.float32)
    if event_dict:
        # Vectorize by matching event date and category
        for (d, cat), factor in event_dict.items():
            date_mask = (date_str_arr == d)
            cat_mask = np.isin(sku_tile, df_product[df_product["category"] == cat]["sku_id"].values)
            comb_mask = date_mask & cat_mask
            if np.any(comb_mask):
                event_factors[comb_mask] *= factor
                
    # Promotion factors:
    promo_factors = np.ones(total_rows, dtype=np.float32)
    if promo_dict:
        for (d, p_sku), factor in promo_dict.items():
            comb_mask = (date_str_arr == d) & (sku_tile == p_sku)
            if np.any(comb_mask):
                promo_factors[comb_mask] *= factor
                
    latent_demand_float = expected_demand * event_factors * promo_factors
    
    # Add random variation: Poisson/Gaussian noise around latent demand
    # Quick commerce has variance proportional to mean
    sigma = np.sqrt(latent_demand_float) * 0.40
    noise = rng.normal(0, sigma, size=total_rows).astype(np.float32)
    actual_latent = np.maximum(1.0, latent_demand_float + noise)
    
    # 2. Inject Controlled Demand Spikes (both known event-related and unexpected anomalies)
    # A few random SKU-Store days get unexpected 2x - 3.5x demand surges
    n_spikes = int(total_rows * 0.005) # 0.5% of rows get sudden spikes
    spike_indices = rng.choice(total_rows, size=n_spikes, replace=False)
    spike_mults = rng.uniform(2.0, 3.5, size=n_spikes).astype(np.float32)
    actual_latent[spike_indices] *= spike_mults
    
    latent_demand_int = np.round(actual_latent).astype(np.int32)
    forecast_baseline = np.round(expected_demand * event_factors).astype(np.int32) # Standard forecast misses unmodeled spikes & random noise
    
    df_demand = pd.DataFrame({
        "date_key": date_key_arr,
        "date": date_str_arr,
        "store_id": store_tile,
        "sku_id": sku_tile,
        "baseline_demand": np.round(sku_base_full, 2),
        "weekday_factor": np.round(dow_factor_full, 2),
        "weekend_factor": np.where(weekend_arr, 1.35, 1.0).astype(np.float32),
        "local_store_factor": np.round(store_factor_full, 2),
        "city_factor": np.round(city_factor_full, 2),
        "event_factor": np.round(event_factors, 2),
        "promotion_factor": np.round(promo_factors, 2),
        "latent_demand": latent_demand_int,
        "forecast_demand": forecast_baseline
    })
    
    return df_demand
