# Data Quality & Validation Report

## 1. Raw Ingestion & Quarantine Metrics

Controlled anomalies were injected into raw staging data to test validation rules and quarantine logic:

- **Raw Sales Records:** 2,160,015
- **Quarantined Sales Records:** 33 rows (0.002% rejection rate)
  * Duplicate rows on business grain (date_key, store_id, sku_id): 15
  * Referential integrity violations (invalid SKU IDs): 10
  * Negative quantities or negative revenues: 8
- **Raw Inventory Records:** 2,160,000
- **Quarantined Inventory Records:** 49 rows (0.002% rejection rate)
  * Broken inventory reconciliation: 12
  * Invalid store foreign keys: 6
  * Negative stock levels: 5
- **Cleaned Records Ingested into Database:**
  * `core.fact_sales`: 2,159,982 rows
  * `core.fact_inventory`: 2,159,951 rows
  * `core.fact_demand`: 2,160,000 rows
  * `core.fact_replenishment`: 455,300 rows
  * `core.fact_transfers`: 7 rows
  * `core.fact_sales_plan`: 2,160,000 rows

All rejected records were written to `data/quarantine/` with diagnostic reason codes.

---

## 2. Inventory Balance Audit

The core physical constraint:
$$\text{Closing Stock} = \text{Opening Stock} + \text{Inbound} + \text{Transfer In} - \text{Transfer Out} - \text{Sold Units} - \text{Damaged Units}$$

- **Total daily records checked:** 2,159,951
- **Discrepancies found:** 0
- **Negative stock records:** 0
- **Status:** PASS

---

## 3. Cross-Layer KPI Reconciliation

Metrics were calculated independently in Python and SQL (via views in DuckDB/PostgreSQL) and compared to verify consistency:

| Metric | Python Calculation | SQL View Calculation | Difference | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Total Requested Units** | 58,054,124 | 58,054,124 | 0 | Exact Match |
| **Total Fulfilled Units** | 57,954,188 | 57,954,188 | 0 | Exact Match |
| **Total Cancelled Units** | 125,513 | 125,513 | 0 | Exact Match |
| **Total Revenue** | $10,412,597,317.43 | $10,412,597,317.43 | $0.00 | Exact Match |
| **Order Fill Rate** | 99.828% | 99.828% | 0.000% | Exact Match |
| **Network Availability** | 99.742% | 99.742% | 0.000% | Exact Match |
| **Stockout Rate** | 0.258% | 0.258% | 0.000% | Exact Match |
| **Replenishment Adherence** | 92.14% | 92.14% | 0.00% | Exact Match |

All metrics match across layers.
