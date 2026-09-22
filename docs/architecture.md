# StockLane: System Architecture

## System Overview
StockLane models an inventory planning workflow for a 4-city, 40-store quick-commerce network. 

The project addresses a common quick-commerce problem: store-level stockouts often happen even when city-wide inventory is sufficient. Delivery zones are small (2-3 km), so stock in Store A cannot serve customers ordering from Store B. StockLane tracks local demand, models physical store constraints, and automates replenishment and inter-store transfers.

## End-to-End Analytical Flow
```
Operational Data Simulation (Deterministic seed=42)
        │
        ▼
Raw Staging Layer (CSV / Parquet)
        │
        ▼
Data Quality Validation Engine (Integrity, Range, Duplicates, Non-negative)
        │
        ├── Rejected Records ───────────► Quarantine Layer (with Reason Codes)
        │
        ▼
Cleaned & Validated Dataset
        │
        ▼
Relational Analytical Store (PostgreSQL / DuckDB Analytical Engine)
        │
        ├── Core Dimensions & Fact Tables
        └── Analytical SQL Views (CTEs, Window Functions, Moving Averages)
        │
        ▼
Demand Feature Engineering Pipeline
        │
        ▼
Time-Series Forecasting Engine (Moving Average, Seasonal Naive, Holt-Winters)
        │ (Chronological Holdout Validation: Train 20 wks / Val 4 wks; MAE, RMSE, WAPE)
        ▼
Inventory Health Engine (Days of Cover, Safety Stock Z=1.645/95%, Reorder Point, Target Stock)
        │
        ▼
Risk Classification Engine (Stockout Risk 0–100, Hours to Stockout, Overstock Classification)
        │
        ├── Replenishment Engine (Target Stock - Projected Inv, MOQ, Case Packs, Capacity, Priority Queue)
        │
        └── Redistribution Engine (Greedy matching: Source Surplus -> Destination Urgency, Safety Stock Protection)
        │
        ▼
Intervention & Scenario Simulator (Demand Uplifts +10% to +50%, Plan-vs-Actual, Root-Cause Hierarchy)
        │
        ▼
Reconciliation Engine (Python vs SQL vs BI Consistency within tolerance)
        │
        ▼
Power BI Analytical Export Layer (Star Schema, DAX Measures, 5-Page Operational Dashboards)
        │
        ▼
Automated Executive Reporting & Fact Sheet
```

## Storage & Database Strategy
- **Primary SQL layer:** Full PostgreSQL DDL/DML scripts in `sql/schema/` and `sql/views/`.
- **Dual database support:** Direct connection to PostgreSQL when host/credentials are supplied via `.env`, paired with a deterministic embedded DuckDB analytical database engine using identical ANSI SQL syntax and PostgreSQL-compatible window functions. This guarantees that anyone cloning the repo can execute the full analytical pipeline out-of-the-box without requiring an external PostgreSQL daemon.
- **Raw & Clean artifacts:** Stored as Parquet and CSV in `data/`.
