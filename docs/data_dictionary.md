# Data Dictionary

## Dimension Tables

### `core.dim_city`
- **Grain:** One row per city.
- **Primary Key:** `city_id`
| Column | Type | Nullable | Description | Values / Range |
| :--- | :--- | :--- | :--- | :--- |
| `city_id` | INT | NO | City identifier | 1 to 4 |
| `city_name` | VARCHAR(50) | NO | City name | Bengaluru, Delhi, Mumbai, Hyderabad |
| `region` | VARCHAR(50) | NO | Geographic region | South, North, West |
| `demand_multiplier` | NUMERIC(5,2)| NO | Relative market scale factor | 1.05 to 1.25 |

### `core.dim_store`
- **Grain:** One row per dark store (10 per city = 40 total).
- **Primary Key:** `store_id`
| Column | Type | Nullable | Description | Values / Range |
| :--- | :--- | :--- | :--- | :--- |
| `store_id` | INT | NO | Store identifier | 1 to 40 |
| `city_id` | INT | NO | Foreign key to `dim_city` | 1 to 4 |
| `store_name` | VARCHAR(50) | NO | Dark store code | e.g. `BEN_DS_01` |
| `latitude` | NUMERIC(9,6)| NO | Store latitude | e.g. 12.971600 |
| `longitude` | NUMERIC(9,6)| NO | Store longitude | e.g. 77.594600 |
| `capacity_units` | INT | NO | Maximum holding capacity | 65,000 to 110,000 units |
| `operating_hours`| INT | NO | Daily fulfillment hours | 18 hours (06:00 to 24:00) |
| `local_demand_multiplier` | NUMERIC(5,2) | NO | Catchment footfall index | 0.80 to 1.30 |
| `store_priority`| INT | NO | Operational tier | 1 (High), 2 (Medium), 3 (Low) |
| `active_flag` | BOOLEAN | NO | Active status | TRUE |

### `core.dim_product`
- **Grain:** One row per SKU (300 products across 10 categories).
- **Primary Key:** `sku_id`
| Column | Type | Nullable | Description | Values / Range |
| :--- | :--- | :--- | :--- | :--- |
| `sku_id` | INT | NO | Product identifier | 1 to 300 |
| `sku_name` | VARCHAR(100)| NO | Formatted product label | e.g. `DAIR_MILK_01` |
| `category` | VARCHAR(50) | NO | Product category | Dairy, Snacks, Staples, etc. |
| `subcategory` | VARCHAR(50) | NO | Product subcategory | Milk, Chips, Atta, etc. |
| `unit_cost` | NUMERIC(10,2)| NO | Unit cost (COGS) | $10.00 to $500.00 |
| `selling_price` | NUMERIC(10,2)| NO | Selling price | $12.00 to $650.00 |
| `lead_time_hours`| INT | NO | Replenishment lead time | 12, 24, 36, 48, 72, 96 hours |
| `shelf_life_days`| INT | NO | Freshness duration | 2 to 720 days |
| `priority_class`| VARCHAR(5) | NO | ABC inventory class | A (Top 20%), B (30%), C (50%) |
| `velocity_class`| VARCHAR(20) | NO | Movement velocity | High, Medium, Low |
| `minimum_order_quantity` | INT | NO | Supplier MOQ | 4 to 96 units |
| `case_pack_size`| INT | NO | Units per carton | 4, 6, 8, 12, 24 |
| `active_flag` | BOOLEAN | NO | Active status | TRUE |

### `core.dim_date`
- **Grain:** One row per calendar date (180 days).
- **Primary Key:** `date_key`
| Column | Type | Nullable | Description | Values / Range |
| :--- | :--- | :--- | :--- | :--- |
| `date_key` | INT | NO | Date integer key | 20260101 to 20260629 |
| `date` | DATE | NO | ISO date string | 2026-01-01 to 2026-06-29 |
| `year` | INT | NO | Year | 2026 |
| `month` | INT | NO | Month number | 1 to 6 |
| `week` | INT | NO | ISO week number | 1 to 27 |
| `day_of_week` | INT | NO | Day number (1=Mon, 7=Sun) | 1 to 7 |
| `day_name` | VARCHAR(20) | NO | Day name | Monday to Sunday |
| `is_weekend` | BOOLEAN | NO | Weekend flag | TRUE / FALSE |
| `holiday_flag` | BOOLEAN | NO | Holiday flag | TRUE / FALSE |
| `event_flag` | BOOLEAN | NO | Promotional event day | TRUE / FALSE |
| `month_name` | VARCHAR(20) | NO | Month name | January to June |

---

## Fact Tables

### `core.fact_sales`
- **Grain:** One SKU × Store × Day (2,160,000 potential rows).
- **Primary Key:** `(date_key, store_id, sku_id)`
| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `date_key` | INT | NO | Date foreign key |
| `store_id` | INT | NO | Dark store foreign key |
| `sku_id` | INT | NO | Product foreign key |
| `requested_units` | INT | NO | Customer demand |
| `fulfilled_units` | INT | NO | Fulfilled customer units: $\min(\text{Available}, \text{Requested})$ |
| `cancelled_units` | INT | NO | Unmet units: $\text{Requested} - \text{Fulfilled}$ |
| `selling_price` | NUMERIC(10,2)| NO | Selling price per unit |
| `revenue` | NUMERIC(12,2)| NO | Fulfilled gross revenue: $\text{Fulfilled} \times \text{Price}$ |

### `core.fact_inventory`
- **Grain:** One SKU × Store × Day.
- **Primary Key:** `(date_key, store_id, sku_id)`
| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `date_key` | INT | NO | Date foreign key |
| `store_id` | INT | NO | Dark store foreign key |
| `sku_id` | INT | NO | Product foreign key |
| `opening_stock` | INT | NO | Morning stock on hand |
| `inbound_stock` | INT | NO | Arrived replenishment units |
| `transfer_in` | INT | NO | Units received from peer store |
| `transfer_out` | INT | NO | Units sent to peer store |
| `sold_units` | INT | NO | Sales fulfilled |
| `damaged_units` | INT | NO | Scrapped / damaged units |
| `closing_stock` | INT | NO | End of day stock on hand |
