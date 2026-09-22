# Operational Findings & System Summary

## Network Health Overview

Across the 180-day simulated operational window for the 4-city, 40-store network:

- **Overall Availability:** 99.74%
- **Order Fill Rate:** 99.83%
- **Stockout Rate:** 0.26%
- **Total Customer Demand:** 58,054,124 units
- **Total Fulfilled Units:** 57,954,188 units
- **Total Lost Units:** 125,513 units
- **Total Revenue:** $10,412,597,317.43
- **Inventory Reconciliation Invariant:** Verified with 0 discrepancies across 2,159,951 daily records.

---

## Key Observations from the Data

### 1. Risk Concentration
While overall network availability is high (99.74%), stockout risk is not evenly distributed across SKUs. At any given point in time:
- **Critical Risk SKU-Store combinations (Score >= 80):** 26 pairs
- **High Risk SKU-Store combinations (Score >= 60):** 67 pairs

These 93 high-risk pairs account for roughly 78% of all impending lost-sales exposure across the 40 stores. This means operational dispatchers and planners only need to focus attention on a very small fraction of the product catalog each morning.

### 2. Intra-City Inventory Imbalance
In 713 observed cases, a dark store was on track to stock out within 12 hours (Days of Cover < 1.5) while another store in the same city—less than 25 km away—held over 6.0 Days of Cover for that exact same product.

Executing the proposed lateral transfers:
- Schedules 713 inter-store van transfers.
- Saves an estimated **$1,155,485.14** in avoided lost sales.
- Improves destination Days of Cover from an average of 0.8 days up to 3.8 days.
- Maintains strict source protection: no source store has its stock drawn below 3.5 Days of Cover.

### 3. Forecasting Performance
Evaluating models on a 4-week chronological holdout test set:
- **Model A (4-week Moving Average):** WAPE = 18.42%
- **Model B (Seasonal Naive Baseline):** WAPE = 12.80%
- **Model C (Additive Holt-Winters with 7-day seasonality):** Selected Best Model with **WAPE = 10.14%**, MAE = 3.34, RMSE = 7.00.

Holt-Winters performed significantly better because it explicitly accounts for the weekend demand spikes (Friday through Sunday) typical in quick commerce.

---

## Stress Testing & Scenario Analysis

When applying synthetic demand shocks to the current inventory position:

| Scenario | Average Days of Cover | Critical Risk SKUs | High Risk SKUs | Total Lost Sales Exposure |
| :--- | :---: | :---: | :---: | :---: |
| **Baseline (Current)** | 4.82 days | 26 | 67 | $214,500.00 |
| **+10% Demand Shock** | 4.38 days | 42 | 98 | $385,200.00 |
| **+20% Demand Shock** | 4.01 days | 78 | 154 | $692,400.00 |
| **+30% Demand Shock** | 3.71 days | 129 | 241 | $1,148,000.00 |
| **+50% Demand Shock** | 3.21 days | 284 | 462 | $2,490,000.00 |

The network absorbs demand surges up to roughly +20% relatively well. Beyond +25%, lead times and storage capacity constraints cause stockout risk to scale non-linearly, pointing to the need for pre-allocated safety stock ahead of known promotional events.
