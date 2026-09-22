-- StockLane PostgreSQL Analytical DDL Schema
-- Schemas: staging, core, analytics

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. Dim Date
CREATE TABLE IF NOT EXISTS core.dim_date (
    date_key INT PRIMARY KEY,
    date DATE NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    week INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    holiday_flag BOOLEAN NOT NULL,
    event_flag BOOLEAN NOT NULL,
    month_name VARCHAR(20) NOT NULL
);

-- 2. Dim City
CREATE TABLE IF NOT EXISTS core.dim_city (
    city_id INT PRIMARY KEY,
    city_name VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,
    demand_multiplier NUMERIC(5,2) NOT NULL
);

-- 3. Dim Store
CREATE TABLE IF NOT EXISTS core.dim_store (
    store_id INT PRIMARY KEY,
    city_id INT NOT NULL REFERENCES core.dim_city(city_id),
    store_name VARCHAR(50) NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    capacity_units INT NOT NULL,
    operating_hours INT NOT NULL,
    local_demand_multiplier NUMERIC(5,2) NOT NULL,
    store_priority INT NOT NULL,
    active_flag BOOLEAN NOT NULL
);

-- 4. Dim Product
CREATE TABLE IF NOT EXISTS core.dim_product (
    sku_id INT PRIMARY KEY,
    sku_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50) NOT NULL,
    unit_cost NUMERIC(10,2) NOT NULL,
    selling_price NUMERIC(10,2) NOT NULL,
    lead_time_hours INT NOT NULL,
    shelf_life_days INT NOT NULL,
    priority_class VARCHAR(5) NOT NULL,
    velocity_class VARCHAR(20) NOT NULL,
    minimum_order_quantity INT NOT NULL,
    case_pack_size INT NOT NULL,
    active_flag BOOLEAN NOT NULL
);

-- 5. Fact Sales
CREATE TABLE IF NOT EXISTS core.fact_sales (
    date_key INT NOT NULL REFERENCES core.dim_date(date_key),
    store_id INT NOT NULL REFERENCES core.dim_store(store_id),
    sku_id INT NOT NULL REFERENCES core.dim_product(sku_id),
    requested_units INT NOT NULL,
    fulfilled_units INT NOT NULL,
    cancelled_units INT NOT NULL,
    selling_price NUMERIC(10,2) NOT NULL,
    revenue NUMERIC(12,2) NOT NULL,
    PRIMARY KEY (date_key, store_id, sku_id)
);

-- 6. Fact Inventory
CREATE TABLE IF NOT EXISTS core.fact_inventory (
    date_key INT NOT NULL REFERENCES core.dim_date(date_key),
    store_id INT NOT NULL REFERENCES core.dim_store(store_id),
    sku_id INT NOT NULL REFERENCES core.dim_product(sku_id),
    opening_stock INT NOT NULL,
    inbound_stock INT NOT NULL,
    transfer_in INT NOT NULL,
    transfer_out INT NOT NULL,
    sold_units INT NOT NULL,
    damaged_units INT NOT NULL,
    closing_stock INT NOT NULL,
    PRIMARY KEY (date_key, store_id, sku_id)
);

-- 7. Fact Demand
CREATE TABLE IF NOT EXISTS core.fact_demand (
    date_key INT NOT NULL REFERENCES core.dim_date(date_key),
    date DATE NOT NULL,
    store_id INT NOT NULL REFERENCES core.dim_store(store_id),
    sku_id INT NOT NULL REFERENCES core.dim_product(sku_id),
    baseline_demand NUMERIC(10,2) NOT NULL,
    weekday_factor NUMERIC(5,2) NOT NULL,
    weekend_factor NUMERIC(5,2) NOT NULL,
    local_store_factor NUMERIC(5,2) NOT NULL,
    city_factor NUMERIC(5,2) NOT NULL,
    event_factor NUMERIC(5,2) NOT NULL,
    promotion_factor NUMERIC(5,2) NOT NULL,
    latent_demand INT NOT NULL,
    forecast_demand INT NOT NULL,
    PRIMARY KEY (date_key, store_id, sku_id)
);

-- 8. Fact Replenishment
CREATE TABLE IF NOT EXISTS core.fact_replenishment (
    replenishment_id INT PRIMARY KEY,
    date_key INT NOT NULL REFERENCES core.dim_date(date_key),
    store_id INT NOT NULL REFERENCES core.dim_store(store_id),
    sku_id INT NOT NULL REFERENCES core.dim_product(sku_id),
    recommended_quantity INT NOT NULL,
    actual_quantity INT NOT NULL,
    recommendation_timestamp VARCHAR(30) NOT NULL,
    actual_arrival_timestamp VARCHAR(30),
    supplier_source VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL,
    reason_code VARCHAR(100) NOT NULL
);

-- 9. Fact Transfers
CREATE TABLE IF NOT EXISTS core.fact_transfers (
    transfer_id INT PRIMARY KEY,
    date_key INT NOT NULL REFERENCES core.dim_date(date_key),
    source_store_id INT NOT NULL REFERENCES core.dim_store(store_id),
    destination_store_id INT NOT NULL REFERENCES core.dim_store(store_id),
    sku_id INT NOT NULL REFERENCES core.dim_product(sku_id),
    recommended_quantity INT NOT NULL,
    executed_quantity INT NOT NULL,
    transfer_distance_km NUMERIC(8,2) NOT NULL,
    transfer_cost NUMERIC(10,2) NOT NULL,
    recommendation_reason VARCHAR(255) NOT NULL,
    status VARCHAR(30) NOT NULL
);

-- 10. Fact Sales Plan
CREATE TABLE IF NOT EXISTS core.fact_sales_plan (
    date_key INT NOT NULL REFERENCES core.dim_date(date_key),
    store_id INT NOT NULL REFERENCES core.dim_store(store_id),
    sku_id INT NOT NULL REFERENCES core.dim_product(sku_id),
    planned_units INT NOT NULL,
    actual_requested_units INT NOT NULL,
    actual_fulfilled_units INT NOT NULL,
    variance_units INT NOT NULL,
    variance_percent NUMERIC(7,4) NOT NULL,
    PRIMARY KEY (date_key, store_id, sku_id)
);
