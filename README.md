# StockLane: Hyperlocal Inventory & Instock Planning

StockLane is an end-to-end inventory planning and dark store replenishment system built for quick-commerce networks. 

In quick commerce (10- to 20-minute delivery), city-wide inventory numbers can be misleading. A city might have plenty of stock on paper, but if Store A has 10 days of cover while Store B two neighborhoods over runs out in two hours, customers experience stockouts. StockLane simulates a 40-store network across 4 cities over 180 days, tracks stock at the SKU-store-day grain, and generates automated replenishment and lateral redistribution transfers to keep products in stock.

---

## The Problem

Quick-commerce fulfillment centers (dark stores) operate with tight physical constraints:
1. **Short delivery radii (2-3 km):** A store cannot fulfill orders from across town. Inventory must be physically present in the local catchment.
2. **Sales censoring during stockouts:** When a store runs out of an item, sales drop to zero. Training demand forecasts on raw sales data creates a downward bias where the model assumes zero customer interest.
3. **Physical warehouse limits:** Dark stores have strict storage limits, supplier minimum order quantities (MOQs), and pack sizes. Planners cannot simply order arbitrary quantities.
4. **Intra-city misallocation:** It is common for one dark store to hold surplus inventory while a nearby store faces an impending stockout for the exact same item.

StockLane models these dynamics, calculates inventory health (Days of Cover, Safety Stock, Reorder Points), and produces constraint-aware recommendations.

---

## How It Works

```
Simulated Operational Telemetry (Demand, Footfall, Lead Times)
                           │
                           ▼
Raw Staging & Quarantine (Data Quality, Balance Checks)
                           │
                           ▼
Core Relational Warehouse (PostgreSQL / DuckDB Schemas & Views)
                           │
                           ▼
Time-Series Forecasting (Moving Average vs Seasonal Naive vs Holt-Winters)
                           │
                           ▼
Inventory Health Engine (Days of Cover, Safety Stock Z=1.645, ROP)
                           │
                           ├── Replenishment Queue (MOQ, Case Packs, Capacity Buffer)
                           └── Intra-City Redistribution (Surplus -> Deficit within 25km)
                           │
                           ▼
Intervention & Stress Simulation (+10% to +50% Demand Shocks)
                           │
                           ▼
Cross-Layer Reconciliation (Python == SQL == Power BI)
```

---

## Key Numbers (Deterministic Seed: 42)

- **Network Scope:** 4 cities (Bengaluru, Delhi, Mumbai, Hyderabad), 40 dark stores, 300 SKUs, 180 days (2.16M observations).
- **Network Availability:** 99.74%
- **Order Fill Rate:** 99.83%
- **Total Demand Processed:** 58,054,124 units
- **Total Fulfilled Revenue:** $10,412,597,317.43
- **Forecast Model Selected:** Additive Holt-Winters with 7-day seasonality (WAPE: 10.14%, MAE: 3.34, RMSE: 7.00).
- **Inventory Balance Invariant:** 0 discrepancies across 2,159,951 daily records (`Closing = Opening + Inbound + Transfer_In - Transfer_Out - Sold - Damaged`).
- **Redistribution Impact:** Identified 713 feasible inter-store transfers, preventing an estimated $1,155,485.14 in lost sales without drawing any source store below 3.5 Days of Cover.

---

## Core Components

### 1. Latent Demand vs Fulfilled Sales
To prevent sales censoring, the simulation tracks customer demand separately from fulfilled units:
$$\text{Fulfilled Units} = \min(\text{Available Inventory}, \text{Requested Demand})$$
$$\text{Lost Units} = \text{Requested Demand} - \text{Fulfilled Units}$$
This allows the forecasting engine to train on actual customer intent rather than truncated sales history.

### 2. Time-Series Forecasting
Three models are evaluated using a strict chronological holdout split (first 20 weeks for training, final 4 weeks for evaluation):
- **Model A:** 4-week Moving Average
- **Model B:** 7-day Seasonal Naive baseline
- **Model C:** Additive Holt-Winters Exponential Smoothing

Models are evaluated using Weighted Absolute Percentage Error (WAPE) rather than MAPE to avoid division-by-zero errors on intermittent demand days:
$$\text{WAPE} = \frac{\sum |A_t - F_t|}{\sum A_t}$$

### 3. Inventory Health & Risk Scoring
- **Safety Stock:** $Z \times \sigma_{\text{demand}} \times \sqrt{L_{\text{days}}}$ with $Z=1.645$ (95% target cycle service level).
- **Reorder Point (ROP):** $(\text{Daily Demand} \times L_{\text{days}}) + \text{Safety Stock}$
- **Target Stock:** $(\text{Daily Demand} \times \text{Coverage Horizon}) + \text{Safety Stock}$
- **Stockout Risk Score (0-100):** A composite score reflecting stock coverage against safety stock, hours to stockout, and product priority class.

### 4. Constrained Replenishment
Orders are triggered when projected inventory (closing stock + arriving inbound) drops to or below the Reorder Point. The engine:
1. Calculates raw need: $\max(0, \text{Target Stock} - \text{Projected Inventory})$
2. Enforces supplier MOQs.
3. Rounds up to whole case-pack sizes.
4. Checks destination dark store capacity (enforcing a 90% buffer for aisle operations).

### 5. Hyperlocal Redistribution
When one store has impending shortages and a nearby store in the same city has excess stock:
- Matches stores within a 25 km radius.
- Enforces strict source protection: the source store must retain at least safety stock plus 2.5 days of demand (minimum 3.5 DoC).
- Models transfer costs ($20 base + $1.50/km) and case-pack rounding.

---

## Power BI Operational Dashboards

The repository includes pre-exported datasets and DAX measures for 5 operational dashboard pages:
1. **Instock Command Center:** Network availability trends, fill rates, critical exception counts, and lost sales exposure.
2. **Stockout & Overstock Risk:** City x store risk heatmap, Days of Cover scatter plot, and high-urgency action queue.
3. **Hyperlocal Redistribution:** Source to destination transfer matrix, transfer distances, and avoided lost sales.
4. **Demand & Forecasting:** Forecast vs actual trends, WAPE scorecards by category, and day-of-week demand curves.
5. **Replenishment Control:** Supplier on-time SLA adherence, delivery status breakdowns, and plan-vs-actual variance.

Exported CSVs are stored in `powerbi/exports/`, DAX definitions are in `powerbi/measures/dax_measures.dax`, and semantic relationships are defined in `powerbi/model/schema_relationships.py`.

---

## Project Structure

```
StockLane/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── config/
│   └── project_config.yaml         # Centralized parameters (service levels, thresholds, costs)
├── data/                           # Raw, processed, and quarantine storage (.gitkeep)
├── python/
│   ├── common/                     # Config loader and structured logger
│   ├── generation/                 # Dimensions, latent demand, and daily inventory simulation
│   ├── validation/                 # Schema checks, referential integrity, and quarantine routing
│   ├── database/                   # Dual PostgreSQL and DuckDB gateway
│   ├── forecasting/                # Moving average, Seasonal Naive, and Holt-Winters engine
│   ├── inventory/                  # Days of Cover, safety stock, risk scoring, action queue
│   ├── replenishment/              # Constrained replenishment orders (MOQ, case packs, capacity)
│   ├── redistribution/             # Explainable greedy transfer engine with source protection
│   ├── simulation/                 # Intervention impact simulator and demand stress scenarios
│   └── reporting/                  # Cross-layer KPI reconciliation (Python vs SQL vs BI)
├── sql/
│   ├── schema/01_core_schema.sql   # Relational DDL (staging, core, analytics)
│   └── views/02_analytical_views.sql # Analytical SQL views with window functions and CTEs
├── powerbi/
│   ├── exports/                    # Validated analytical CSVs for Power BI ingestion
│   ├── measures/dax_measures.dax   # Canonical DAX measures
│   ├── model/schema_relationships.py # Star schema relationship definitions
│   └── documentation/              # 5-page dashboard UI and layout specifications
├── reports/
│   ├── fact_sheet.yaml             # Machine-readable verified run metrics
│   ├── executive_summary.md        # Summary of operational findings and scenario results
│   └── validation_report.md        # Data quality and reconciliation audit log
├── docs/
│   ├── architecture.md             # End-to-end system design
│   ├── data_dictionary.md          # Table grains, schemas, and column descriptions
│   ├── kpi_dictionary.md           # Authoritative formulas and edge-case handling
│   ├── assumptions.md              # Model parameters and logistics assumptions
│   └── limitations.md              # Documented operational simplifications
├── tests/
│   ├── test_stocklane.py           # Core integration and invariant tests
│   └── test_comprehensive.py       # 150+ parameterized boundary condition tests
└── scripts/
    └── run_pipeline.py             # End-to-end orchestrator script
```

---

## Quickstart

### 1. Setup Environment
```bash
git clone https://github.com/hriday-sobti/StockLane.git
cd StockLane

pip install -r requirements.txt
```

### 2. Run the Full Pipeline
Executes data generation, validation, database ingestion, forecasting, inventory risk, replenishment, redistribution, and reporting:
```bash
python scripts/run_pipeline.py
```

### 3. Run the Test Suite
Runs 154 unit and integration tests covering inventory reconciliation, pricing math, safety stock, and redistribution constraints:
```bash
python -m pytest tests/ -v
```
