# StockLane Data Dictionary

## 1. Dimensional Model Overview
StockLane organizes its analytical architecture around a star-like relational model with schemas `staging`, `core`, and `analytics`.

---

## 2. Dimension Tables

### `core.dim_city`
- **Grain:** One row per synthetic city.
- **Primary Key:** `city_id`
| Column | Type | Nullable | Description | Valid Range / Example |
| :--- | :--- | :--- | :--- | :--- |
| `city_id` | INT | NO | Unique synthetic city identifier | 1 to 4 |
| `city_name` | VARCHAR(50) | NO | Name of city | Bengaluru, Delhi, Mumbai, Hyderabad |
| `region` | VARCHAR(50) | NO | Geographical zone | South, North, West |
| `demand_multiplier` | NUMERIC(5,2)| NO | Synthetic baseline market size index | 1.05 to 1.25 |

### `core.dim_store`
- **Grain:** One row per dark store (10 dark stores per city = 40 total).
- **Primary Key:** `store_id`
| Column | Type | Nullable | Description | Valid Range / Example |
| :--- | :--- | :--- | :--- | :--- |
| `store_id` | INT | NO | Unique dark store identifier | 1 to 40 |
| `city_id` | INT | NO | FK referencing `dim_city` | 1 to 4 |
| `store_name` | VARCHAR(50) | NO | Store identifier code | e.g. `BEN_DS_01` |
| `latitude` | NUMERIC(9,6)| NO | Geospatial latitude coordinate | e.g. 12.971600 |
| `longitude` | NUMERIC(9,6)| NO | Geospatial longitude coordinate | e.g. 77.594600 |
| `capacity_units` | INT | NO | Maximum physical holding capacity | 65,000 to 110,000 units |
| `operating_hours`| INT | NO | Daily order fulfillment hours | 18 hours (06:00 - 24:00) |
| `local_demand_multiplier` | NUMERIC(5,2) | NO | Catchment footfall factor | 0.80 to 1.30 |
| `store_priority`| INT | NO | Operational strategic tier | 1 (High), 2 (Medium), 3 (Low) |
| `active_flag` | BOOLEAN | NO | Store active status | TRUE |

### `core.dim_product`
- **Grain:** One row per SKU (300 total across 10 categories).
- **Primary Key:** `sku_id`
| Column | Type | Nullable | Description | Valid Range / Example |
| :--- | :--- | :--- | :--- | :--- |
| `sku_id` | INT | NO | Unique product identifier | 1 to 300 |
| `sku_name` | VARCHAR(100)| NO | Formatted SKU label | e.g. `DAIR_MILK_01` |
| `category` | VARCHAR(50) | NO | Product department | Dairy, Snacks, Staples, etc. |
| `subcategory` | VARCHAR(50) | NO | Sub-department classification | Milk, Chips, Atta, etc. |
| `unit_cost` | NUMERIC(10,2)| NO | Cost of goods sold (COGS) | $10.00 to $500.00 |
| `selling_price` | NUMERIC(10,2)| NO | Retail consumer price | $12.00 to $650.00 |
| `lead_time_hours`| INT | NO | Supplier replenishment delivery SLA | 12, 24, 36, 48, 72, 96 hours |
| `shelf_life_days`| INT | NO | Maximum freshness duration | 2 to 720 days |
| `priority_class`| VARCHAR(5) | NO | ABC inventory prioritization | A (Top 20%), B (30%), C (50%) |
| `velocity_class`| VARCHAR(20) | NO | Movement velocity tier | High, Medium, Low |
| `minimum_order_quantity` | INT | NO | Supplier order minimum (MOQ) | Multiple of case pack (4 to 96) |
| `case_pack_size`| INT | NO | Units per carton/case | 4, 6, 8, 12, 24 |
| `active_flag` | BOOLEAN | NO | SKU active status | TRUE |

### `core.dim_date`
- **Grain:** One row per calendar date (180 days).
- **Primary Key:** `date_key`
| Column | Type | Nullable | Description | Valid Range / Example |
| :--- | :--- | :--- | :--- | :--- |
| `date_key` | INT | NO | YYYYMMDD integer key | 20260101 to 20260629 |
| `date` | DATE | NO | ISO standard date string | 2026-01-01 to 2026-06-29 |
| `year` | INT | NO | Calendar year | 2026 |
| `month` | INT | NO | Month number | 1 to 6 |
| `week` | INT | NO | ISO week number | 1 to 27 |
| `day_of_week` | INT | NO | Day number (1=Mon, 7=Sun) | 1 to 7 |
| `day_name` | VARCHAR(20) | NO | Day string | Monday to Sunday |
| `is_weekend` | BOOLEAN | NO | True if Saturday or Sunday | TRUE / FALSE |
| `holiday_flag` | BOOLEAN | NO | Public holiday indicator | TRUE / FALSE |
| `event_flag` | BOOLEAN | NO | High-impact promotional surge day | TRUE / FALSE |
| `month_name` | VARCHAR(20) | NO | Full month name | January to June |

---

## 3. Fact Tables

### `core.fact_sales`
- **Grain:** One SKU × Store × Day (2,160,000 potential rows).
- **Primary Key:** `(date_key, store_id, sku_id)`
| Column | Type | Nullable | Description | Invariant / Logic |
| :--- | :--- | :--- | :--- | :--- |
| `date_key` | INT | NO | Date foreign key | FK -> `dim_date` |
| `store_id` | INT | NO | Dark store foreign key | FK -> `dim_store` |
| `sku_id` | INT | NO | Product foreign key | FK -> `dim_product` |
| `requested_units` | INT | NO | Underlying customer demand units | Latent demand |
| `fulfilled_units` | INT | NO | Successfully fulfilled customer sales | $\min(\text{Available}, \text{Requested})$ |
| `cancelled_units` | INT | NO | Lost demand units from stockout | $\text{Requested} - \text{Fulfilled}$ |
| `selling_price` | NUMERIC(10,2)| NO | Selling price per unit | From `dim_product` |
| `revenue` | NUMERIC(12,2)| NO | Total fulfilled gross revenue | $\text{Fulfilled} \times \text{Price}$ |

### `core.fact_inventory`
- **Grain:** One SKU × Store × Day.
- **Primary Key:** `(date_key, store_id, sku_id)`
| Column | Type | Nullable | Description | Invariant / Logic |
| :--- | :--- | :--- | :--- | :--- |
| `date_key` | INT | NO | Date foreign key | FK -> `dim_date` |
| `store_id` | INT | NO | Dark store foreign key | FK -> `dim_store` |
| `sku_id` | INT | NO | Product foreign key | FK -> `dim_product` |
| `opening_stock` | INT | NO | Inventory on hand at 06:00 | Previous day's closing stock |
| `inbound_stock` | INT | NO | Arrived replenishment units | Supplier receipts |
| `transfer_in` | INT | NO | Units received from peer store | Inter-store transfers |
| `transfer_out` | INT | NO | Units dispatched to peer store | Inter-store transfers |
| `sold_units` | INT | NO | Fulfilled sales units | Outflow |
| `damaged_units` | INT | NO | Transit / handling damaged units | Scrap write-off |
| `closing_stock` | INT | NO | Inventory on hand at 24:00 | $\text{Opening} + \text{Inbound} + \text{XIn} - \text{XOut} - \text{Sold} - \text{Damaged}$ |
