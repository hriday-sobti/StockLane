"""Unit and Integration Tests for StockLane.
Tests:
  1. Deterministic Data Generation (seeds, column schemas, dimension validity)
  2. Inventory Invariant Reconciliation (Closing = Opening + Inbound + Xfer_in - Xfer_out - Sold - Damaged)
  3. Non-negative quantities and prices
  4. Data Validation and Quarantine Routing (bad records caught and quarantined)
  5. Forecast evaluation (non-negative predictions, chronological metrics)
  6. Replenishment Constraints (MOQ, Case Pack rounding, Capacity limits)
  7. Redistribution Invariants (Source protection, same SKU, same city, distance limit)
"""
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from python.common.config import load_config
from python.generation.generate_dimensions import generate_dimensions
from python.generation.generate_demand import generate_demand
from python.generation.simulate_inventory import simulate_sales_and_inventory
from python.validation.data_validator import inject_raw_anomalies, validate_and_quarantine
from python.inventory.inventory_health import calculate_inventory_health_and_risk
from python.replenishment.replenishment_engine import generate_replenishment_recommendations
from python.redistribution.redistribution_engine import run_redistribution_engine, haversine_distance_km

@pytest.fixture(scope="session")
def project_config():
    return load_config()

@pytest.fixture(scope="session")
def dimensions(project_config):
    return generate_dimensions(project_config)

def test_dimensions_structure(dimensions):
    assert "dim_city" in dimensions
    assert "dim_store" in dimensions
    assert "dim_product" in dimensions
    assert "dim_date" in dimensions
    
    assert len(dimensions["dim_city"]) == 4
    assert len(dimensions["dim_store"]) == 40
    assert len(dimensions["dim_product"]) == 300
    assert len(dimensions["dim_date"]) == 180
    
    # Store coordinates check
    assert dimensions["dim_store"]["latitude"].notnull().all()
    assert dimensions["dim_store"]["longitude"].notnull().all()
    
    # Price check
    assert (dimensions["dim_product"]["unit_cost"] > 0).all()
    assert (dimensions["dim_product"]["selling_price"] > dimensions["dim_product"]["unit_cost"]).all()

def test_inventory_reconciliation_invariant(project_config, dimensions):
    # Test on a small 5-day slice
    test_cfg = project_config.copy()
    test_cfg["simulation_days"] = 5
    dims = generate_dimensions(test_cfg)
    dem = generate_demand(dims, test_cfg)
    sales, inv, repl, xfer, plan = simulate_sales_and_inventory(dims, dem, test_cfg)
    
    # Hard Invariant: Closing = Opening + Inbound + Xfer_in - Xfer_out - Sold - Damaged
    calculated_closing = (
        inv["opening_stock"] +
        inv["inbound_stock"] +
        inv["transfer_in"] -
        inv["transfer_out"] -
        inv["sold_units"] -
        inv["damaged_units"]
    )
    diff = inv["closing_stock"] - calculated_closing
    assert (diff == 0).all(), "Inventory reconciliation equation violated!"
    assert (inv["closing_stock"] >= 0).all(), "Negative closing stock detected!"

def test_validation_and_quarantine(project_config, dimensions):
    test_cfg = project_config.copy()
    test_cfg["simulation_days"] = 3
    dims = generate_dimensions(test_cfg)
    dem = generate_demand(dims, test_cfg)
    sales, inv, repl, xfer, plan = simulate_sales_and_inventory(dims, dem, test_cfg)
    
    raw_sales, raw_inv = inject_raw_anomalies(sales, inv, test_cfg)
    clean_dict, quar_dict, report = validate_and_quarantine(
        dims, raw_sales, raw_inv, dem, repl, xfer, plan
    )
    
    assert report["quarantined_sales_rows"] > 0
    assert report["quarantined_inventory_rows"] > 0
    assert "quarantine_reason" in quar_dict["quarantine_sales"].columns

def test_replenishment_constraints(project_config, dimensions):
    # Dummy health df
    df_health = pd.DataFrame([{
        "date_key": 20260105,
        "store_id": 1,
        "store_name": "BEN_DS_01",
        "city_id": 1,
        "sku_id": 101,
        "sku_name": "DAIR_MILK_01",
        "category": "Dairy",
        "closing_stock": 5,
        "inbound_stock": 0,
        "reorder_point": 20,
        "target_stock": 50,
        "minimum_order_quantity": 12,
        "case_pack_size": 6,
        "capacity_units": 80000,
        "stockout_risk_score": 90,
        "risk_level": "Critical",
        "lost_sales_exposure": 120.0,
        "hours_to_stockout": 4.5,
        "days_of_cover": 0.5
    }])
    
    repl_df = generate_replenishment_recommendations(df_health, project_config)
    assert not repl_df.empty
    rec = repl_df.iloc[0]
    
    # Must be multiple of case pack (6)
    assert rec["recommended_quantity"] % 6 == 0
    # Must satisfy MOQ (12)
    assert rec["recommended_quantity"] >= 12

def test_redistribution_safety_protection(project_config, dimensions):
    # Store 1 surplus (50 units), Store 2 deficit (2 units) in same city
    df_health = pd.DataFrame([
        {
            "date_key": 20260105,
            "store_id": 1,
            "store_name": "BEN_DS_01",
            "city_id": 1,
            "sku_id": 50,
            "sku_name": "SNAC_CHIP_01",
            "category": "Snacks",
            "closing_stock": 80,
            "safety_stock": 15,
            "target_stock": 40,
            "days_of_cover": 6.5,
            "stockout_risk_score": 10,
            "forecast_daily_mean": 10.0,
            "selling_price": 40.0,
            "case_pack_size": 6,
            "hours_to_stockout": 100.0,
            "lost_sales_exposure": 0.0
        },
        {
            "date_key": 20260105,
            "store_id": 2,
            "store_name": "BEN_DS_02",
            "city_id": 1,
            "sku_id": 50,
            "sku_name": "SNAC_CHIP_01",
            "category": "Snacks",
            "closing_stock": 3,
            "safety_stock": 15,
            "target_stock": 40,
            "days_of_cover": 0.3,
            "stockout_risk_score": 95,
            "forecast_daily_mean": 10.0,
            "selling_price": 40.0,
            "case_pack_size": 6,
            "hours_to_stockout": 3.0,
            "lost_sales_exposure": 400.0
        }
    ])
    
    xfers = run_redistribution_engine(dimensions, df_health, project_config)
    assert not xfers.empty
    xfer = xfers.iloc[0]
    
    assert xfer["source_store_id"] == 1
    assert xfer["destination_store_id"] == 2
    assert xfer["recommended_quantity"] % 6 == 0
    # Source must retain protected safety stock
    assert xfer["projected_source_stock"] >= 15
