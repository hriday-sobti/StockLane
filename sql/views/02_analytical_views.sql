-- StockLane Analytical SQL Views
-- Implements window functions, CTEs, LAG, rolling calculations, and exception detection.

-- 1. View: v_inventory_health
-- Computes rolling 7-day sales velocity, Days of Cover, and historical stockout events
CREATE OR REPLACE VIEW analytics.v_inventory_health AS
WITH daily_stats AS (
    SELECT
        inv.date_key,
        d.date,
        inv.store_id,
        s.store_name,
        s.city_id,
        c.city_name,
        inv.sku_id,
        p.sku_name,
        p.category,
        p.priority_class,
        inv.opening_stock,
        inv.inbound_stock,
        inv.transfer_in,
        inv.transfer_out,
        inv.sold_units,
        inv.damaged_units,
        inv.closing_stock,
        sal.requested_units,
        sal.fulfilled_units,
        sal.cancelled_units,
        sal.revenue,
        p.selling_price,
        p.lead_time_hours,
        -- Rolling 7-day demand velocity
        AVG(sal.requested_units) OVER (
            PARTITION BY inv.store_id, inv.sku_id 
            ORDER BY inv.date_key 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7d_velocity,
        -- Stockout flag: closing stock is zero or customer orders were cancelled
        CASE WHEN inv.closing_stock = 0 OR sal.cancelled_units > 0 THEN 1 ELSE 0 END AS is_stockout
    FROM core.fact_inventory inv
    JOIN core.dim_date d ON inv.date_key = d.date_key
    JOIN core.dim_store s ON inv.store_id = s.store_id
    JOIN core.dim_city c ON s.city_id = c.city_id
    JOIN core.dim_product p ON inv.sku_id = p.sku_id
    JOIN core.fact_sales sal ON inv.date_key = sal.date_key AND inv.store_id = sal.store_id AND inv.sku_id = sal.sku_id
)
SELECT
    *,
    -- Days of cover: Closing Stock / Max(rolling_7d_velocity, 0.5)
    ROUND(closing_stock / GREATEST(rolling_7d_velocity, 0.5), 2) AS days_of_cover,
    -- Estimated lost revenue = cancelled units * selling price
    ROUND(cancelled_units * selling_price, 2) AS lost_sales_value,
    -- Prior day closing stock using LAG
    LAG(closing_stock, 1) OVER (PARTITION BY store_id, sku_id ORDER BY date_key) AS prev_day_closing_stock
FROM daily_stats;

-- 2. View: v_stockout_risk
-- Identifies critical SKU-Store combinations with low Days of Cover
CREATE OR REPLACE VIEW analytics.v_stockout_risk AS
SELECT
    date_key,
    date,
    city_name,
    store_name,
    store_id,
    sku_name,
    sku_id,
    category,
    priority_class,
    closing_stock,
    rolling_7d_velocity,
    days_of_cover,
    lost_sales_value,
    CASE 
        WHEN days_of_cover <= 1.0 THEN 'Critical'
        WHEN days_of_cover <= 2.5 THEN 'High'
        WHEN days_of_cover <= 5.0 THEN 'Medium'
        ELSE 'Low'
    END AS risk_category,
    -- Estimated hours to stockout
    ROUND(days_of_cover * 18.0, 1) AS hours_to_stockout
FROM analytics.v_inventory_health;

-- 3. View: v_replenishment_adherence
-- Evaluates execution adherence of replenishment orders (Completed vs Delayed vs Cancelled)
CREATE OR REPLACE VIEW analytics.v_replenishment_adherence AS
SELECT
    r.replenishment_id,
    r.date_key,
    d.date,
    s.store_id,
    s.store_name,
    c.city_name,
    p.sku_id,
    p.sku_name,
    p.category,
    r.recommended_quantity,
    r.actual_quantity,
    ROUND(CAST(r.actual_quantity AS NUMERIC) / NULLIF(r.recommended_quantity, 0), 4) AS quantity_adherence_rate,
    r.status,
    r.reason_code,
    CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END AS is_on_time_fulfilled
FROM core.fact_replenishment r
JOIN core.dim_date d ON r.date_key = d.date_key
JOIN core.dim_store s ON r.store_id = s.store_id
JOIN core.dim_city c ON s.city_id = c.city_id
JOIN core.dim_product p ON r.sku_id = p.sku_id;

-- 4. View: v_redistribution_opportunities
-- Identifies city-level misallocation: Surplus store (> 7 DoC) paired with Deficit store (< 2 DoC) for same SKU
CREATE OR REPLACE VIEW analytics.v_redistribution_opportunities AS
WITH latest_date AS (
    SELECT MAX(date_key) AS max_date_key FROM core.fact_inventory
),
current_health AS (
    SELECT * FROM analytics.v_inventory_health
    WHERE date_key = (SELECT max_date_key FROM latest_date)
),
surplus_stores AS (
    SELECT * FROM current_health WHERE days_of_cover >= 6.0 AND closing_stock >= 30
),
deficit_stores AS (
    SELECT * FROM current_health WHERE days_of_cover <= 2.0
)
SELECT
    sur.city_name,
    sur.store_id AS source_store_id,
    sur.store_name AS source_store_name,
    def.store_id AS dest_store_id,
    def.store_name AS dest_store_name,
    sur.sku_id,
    sur.sku_name,
    sur.category,
    sur.closing_stock AS source_closing_stock,
    sur.days_of_cover AS source_doc,
    def.closing_stock AS dest_closing_stock,
    def.days_of_cover AS dest_doc,
    def.lost_sales_value AS dest_lost_sales_exposure,
    -- Candidate transfer quantity: Move enough to reach ~3.5 DoC at destination while keeping >= 3.5 DoC at source
    LEAST(
        CAST(FLOOR(sur.closing_stock - (sur.rolling_7d_velocity * 3.5)) AS INT),
        CAST(CEIL((def.rolling_7d_velocity * 3.5) - def.closing_stock) AS INT)
    ) AS potential_transfer_units
FROM surplus_stores sur
JOIN deficit_stores def 
    ON sur.city_id = def.city_id 
    AND sur.sku_id = def.sku_id 
    AND sur.store_id <> def.store_id
WHERE sur.closing_stock > (sur.rolling_7d_velocity * 3.5)
  AND (def.rolling_7d_velocity * 3.5) > def.closing_stock;

-- 5. View: v_lost_sales_summary
-- Aggregated lost sales and availability summary by Category and City
CREATE OR REPLACE VIEW analytics.v_lost_sales_summary AS
SELECT
    c.city_name,
    p.category,
    SUM(sal.requested_units) AS total_requested_units,
    SUM(sal.fulfilled_units) AS total_fulfilled_units,
    SUM(sal.cancelled_units) AS total_lost_units,
    ROUND(SUM(sal.fulfilled_units) * 100.0 / NULLIF(SUM(sal.requested_units), 0), 2) AS overall_fill_rate_pct,
    ROUND(SUM(sal.revenue), 2) AS fulfilled_revenue,
    ROUND(SUM(sal.cancelled_units * p.selling_price), 2) AS total_lost_sales_value
FROM core.fact_sales sal
JOIN core.dim_store s ON sal.store_id = s.store_id
JOIN core.dim_city c ON s.city_id = c.city_id
JOIN core.dim_product p ON sal.sku_id = p.sku_id
GROUP BY c.city_name, p.category;
