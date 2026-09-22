# StockLane
### Hyperlocal Inventory & Instock Planning System for Quick-Commerce Dark Stores

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![PostgreSQL / DuckDB](https://img.shields.io/badge/SQL-PostgreSQL%20%7C%20DuckDB-orange.svg)](https://duckdb.org/)
[![Power BI Ready](https://img.shields.io/badge/PowerBI-Export%20Ready-yellow.svg)](https://powerbi.microsoft.com/)
[![Tests](https://img.shields.io/badge/pytest-154%20passed-brightgreen.svg)](https://pytest.org/)

---

## 1. Executive Summary & Business Mission
In hyperlocal quick-commerce operations (10-to-20 minute delivery windows), inventory availability is constrained by micro-catchments. Aggregating inventory across an entire city frequently conceals localized stockouts: **network inventory sufficiency does not guarantee local availability**.

**StockLane** is an analytical planning and decision-support system modeling a 4-city, 40-dark-store, 300-SKU, 180-day quick-commerce network. It transforms raw operational telemetry into prioritized, constraint-respecting replenishment and inter-store redistribution decisions.

```
Raw Staging Data (2.16M rows)
       ↓
Data Quality Engine & Quarantine Layer
       ↓
PostgreSQL / DuckDB Relational Model (staging, core, analytics)
       ↓
Analytical SQL Views (Window functions, CTEs, Rolling velocity)
       ↓
Time-Series Forecasting Engine (Moving Average, Seasonal Naive, Holt-Winters)
       ↓
Inventory Health & Explainable Risk Scoring (Days of Cover, Safety Stock Z=1.645, ROP)
       ↓
Constrained Replenishment Engine (MOQ, Case Packs, Capacity Buffer)
       ↓
Explainable Greedy Redistribution Engine (Surplus -> Shortage within 25km)
       ↓
Intervention Simulation & Demand Scenario Stress-Testing (+10% to +50%)
       ↓
Authoritative KPI Reconciliation (Python vs SQL vs BI)
       ↓
Power BI Decision-Support Dashboards (5 Pages)
```

---

## 2. Key Operational Metrics (Deterministic Seed = 42)
All metrics reflect verified executions from the pipeline:
- **Network Availability %:** **99.74%**
- **Order Fill Rate %:** **99.83%**
- **Stockout Rate %:** **0.26%**
- **Total Customer Demand Processed:** **58,054,124 units**
- **Total Fulfilled Gross Revenue:** **$10,412,597,317.43**
- **Forecast Model Selected:** **Additive Holt-Winters (7-day seasonality) — WAPE: 10.14%, MAE: 3.34, RMSE: 7.00**
- **Current Critical Risk SKU-Store Pairs:** **26 pairs**
- **Intra-City Redistribution Opportunities:** **713 transfers identified**
- **Projected Lost Sales Avoided via Redistribution:** **$1,155,485.14**
- **Inventory Reconciliation Invariant:** **100.0% verified (0 discrepancies across 2.16M rows)**

---

## 3. Core System Architecture

### A. Dimensional Modeling & Latent Demand
- **Dimensions:** `dim_city` (4 cities), `dim_store` (40 dark stores with coordinates and capacity limits), `dim_product` (300 SKUs across 10 categories with MOQs and case packs), `dim_date` (180 days deterministic), `dim_event` (promotional campaigns), and `dim_promotion`.
- **Latent Demand:** Distinguishes underlying customer demand from fulfilled sales to eliminate sales-censoring bias during stockouts. Incorporates base velocity, day-of-week surges (Friday-Sunday peaks), regional catchment multipliers, and calendar events.

### B. Data Quality & Quarantine Pipeline
- Synthetically injects anomalies (duplicates on business grain, referential integrity violations, negative quantities, broken inventory balance).
- Routes bad records to `data/quarantine/` with human-readable reason codes, ensuring zero defective records enter the core relational warehouse.

### C. Relational SQL Warehouse & Analytical Views
- Dual database support: Full PostgreSQL DDL/DML in `sql/schema/01_core_schema.sql` plus embedded DuckDB zero-dependency execution.
- Window functions and CTEs in `sql/views/02_analytical_views.sql`:
  * `v_inventory_health`: Computes rolling 7-day velocity, Days of Cover, and historical stockouts.
  * `v_stockout_risk`: Identifies acute shortages.
  * `v_redistribution_opportunities`: Pairs surplus and deficit stores in the same city.
  * `v_lost_sales_summary`: Aggregates commercial impact by category and city.

### D. Decision & Operations Engines
1. **Inventory Health & Risk Score (0-100):**
   * Safety stock calculated via $Z \times \sigma_{\text{demand}} \times \sqrt{L_{\text{days}}}$ ($Z=1.645$ for 95% service level).
   * Reorder Point (ROP) and Target Stock.
   * Explainable linear composite risk score incorporating coverage ratio, hours to stockout, and SKU priority.
2. **Constrained Replenishment Engine:**
   * Reorder triggered when projected inventory $\le$ ROP.
   * Enforces supplier MOQs, whole case-pack rounding, and store physical capacity buffers.
3. **Hyperlocal Redistribution Engine:**
   * Explainable greedy matching pairing surplus stores ($\text{DoC} \ge 4.0$d) with deficit stores ($\text{DoC} \le 2.0$d) within a 25 km radius.
   * **Guaranteed Source Protection:** Source store is never drawn down below 3.5 Days of Cover.
4. **Intervention Simulator & Stress-Testing:**
   * Simulates Before vs After intervention impact on availability and lost sales.
   * Stress-tests demand surges (+10%, +20%, +25%, +30%, +50%).
   * Diagnoses stockout root causes (delayed inbound vs demand spike vs forecast underestimation).

---

## 4. Power BI Operational Dashboard Suite
Exported analytical datasets and DAX measures support 5 operational dashboard pages:
1. **Instock Command Center:** Macro network health, availability trends, fill rates, and top exception queue.
2. **Stockout & Overstock Risk:** City $\times$ Store risk heatmap, Days of Cover scatter plot, and critical SKU action list.
3. **Hyperlocal Inventory Redistribution:** Source $\rightarrow$ Destination transfer routing, transfer distance, and avoided lost sales.
4. **Demand Signals & Forecasting:** Forecast vs actual comparison, WAPE scorecard, and day-of-week surge profiles.
5. **Replenishment Control & Plan Variance:** Supplier SLA adherence, delayed delivery root causes, and plan-vs-actual variance.

Full dashboard specifications and DAX definitions are located in `powerbi/`.

---

## 5. Repository Structure
```
StockLane/
├── README.md
├── requirements.txt
├── .gitignore
├── config/
│   └── project_config.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   └── quarantine/
├── python/
│   ├── common/             # Config loader, structured logging
│   ├── generation/         # Dimension, demand, and inventory generators
│   ├── validation/         # Data quality validator and quarantine routing
│   ├── database/           # Dual PostgreSQL / DuckDB manager
│   ├── forecasting/        # Moving average, Seasonal Naive, Holt-Winters
│   ├── inventory/          # Health, risk scoring, action queue
│   ├── replenishment/      # Constrained replenishment engine
│   ├── redistribution/     # Explainable greedy redistribution
│   ├── simulation/         # Intervention simulator, scenarios, root-cause
│   └── reporting/          # Authoritative cross-layer KPI reconciler
├── sql/
│   ├── schema/             # PostgreSQL DDL for core warehouse
│   └── views/              # Analytical SQL views with window functions
├── powerbi/
│   ├── exports/            # Validated CSV exports ready for BI ingestion
│   ├── measures/           # Authoritative DAX measures
│   ├── model/              # Semantic star schema relationships
│   └── documentation/      # 5-page dashboard specifications
├── reports/
│   ├── fact_sheet.yaml     # Machine-readable verified metrics
│   ├── executive_summary.md# Operational findings
│   └── validation_report.md# QA audit log
├── docs/
│   ├── architecture.md     # System architecture
│   ├── data_dictionary.md  # Detailed table grains and field descriptions
│   ├── kpi_dictionary.md   # Canonical KPI formulas
│   ├── assumptions.md      # Model assumptions and logistics physics
│   └── limitations.md      # Analytical limitations
├── tests/
│   ├── test_stocklane.py   # Core integration tests
│   └── test_comprehensive.py # 150+ parameterized boundary condition tests
└── scripts/
    └── run_pipeline.py     # End-to-end master orchestrator
```

---

## 6. How to Reproduce & Run

### A. Environment Setup
```bash
# Clone and enter directory
cd StockLane

# Install dependencies
pip install -r requirements.txt
```

### B. Execute Master Pipeline
Run the end-to-end 22-stage pipeline with one command:
```bash
python scripts/run_pipeline.py
```

### C. Run Test Suite
Run automated unit and integration tests verifying inventory invariants and constraints:
```bash
python -m pytest tests/ -v
```
