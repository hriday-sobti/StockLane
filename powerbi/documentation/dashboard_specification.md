# Power BI Operational Dashboard Specification

## Overview & Analytical Intent
The StockLane Power BI reporting suite is designed strictly as an **operational decision-support system**, avoiding visual noise, decorative 3D elements, or arbitrary rainbow palettes.

Color Palette:
- Neutral Light Background: `#F8F9FA`
- Primary Typography & Cards: Deep Slate `#1E293B`
- Status Accents:
  * Safe / Low Risk: `#10B981` (Emerald Green)
  * Medium / Warning: `#F59E0B` (Amber)
  * High Risk: `#EA580C` (Orange)
  * Critical / Stockout Breach: `#DC2626` (Crimson)

---

## Page 1: Instock Command Center
**Analytical Question:** *What is the macro instock health across our dark-store network right now?*

- **Top KPI Strip (Cards):**
  1. Network Availability % (`Availability_Pct`)
  2. Order Fill Rate % (`Fill_Rate_Pct`)
  3. Stockout Rate % (`Stockout_Rate_Pct`)
  4. Lost Sales Exposure ($) (`Total_Lost_Sales_Value`)
  5. Critical SKU-Store Pairs (`Critical_Stockout_Count`)
  6. Average Days of Cover (`Average_Days_of_Cover`)
- **Visual 1 (Line Chart):** 180-Day Network Availability Trend vs 98.0% Target SLA Line.
- **Visual 2 (Bar Chart):** Availability & Fill Rate by Product Category.
- **Visual 3 (Matrix Grid):** Dark Store Availability % by City (Columns: City, Store, Availability %, Fill Rate, Lost Sales).
- **Visual 4 (High-Priority Action Table):** Top 10 immediate operational interventions from `pbi_fact_action_queue`.

---

## Page 2: Stockout & Overstock Risk
**Analytical Question:** *Which specific SKU-Store combinations are at risk, and why?*

- **Slicers:** City, Dark Store, Category, Priority Class (A/B/C), Risk Level.
- **Visual 1 (Heatmap Matrix):** City × Dark Store with cells colored by Mean Stockout Risk Score (0-100).
- **Visual 2 (Scatter Plot):** Days of Cover (X-axis) vs Forecast Daily Demand (Y-axis), bubble size = Lost Sales Exposure, color = Risk Category. Exposes both bottom-left (acute stockouts) and bottom-right (dead excess stock).
- **Visual 3 (Detailed Action Table):**
  * Store Name, SKU Name, Category, Closing Stock, Safety Stock, Reorder Point, Days of Cover, Hours to Stockout, Risk Score, Action.

---

## Page 3: Hyperlocal Inventory Redistribution
**Analytical Question:** *Where can excess dark-store inventory be redirected to prevent nearby stockouts?*

- **Slicers:** City (Bengaluru, Delhi, Mumbai, Hyderabad), Category, Maximum Transfer Distance.
- **Visual 1 (Sankey / Route Matrix):** Source Dark Store $\longrightarrow$ Destination Dark Store transfer volume.
- **Visual 2 (Summary Cards):**
  * Active Redistribution Opportunities Count
  * Total Units Recommended for Transfer
  * Total Projected Lost Sales Avoided ($)
  * Average Transfer Distance (km)
- **Visual 3 (Redistribution Execution Table):**
  * Source Store, Destination Store, SKU Name, Recommended Transfer Qty, Source DoC (Before $\rightarrow$ After), Destination DoC (Before $\rightarrow$ After), Distance (km), Estimated Lost Sales Avoided ($), Algorithmic Justification Reason.

---

## Page 4: Demand Signals & Time-Series Forecasting
**Analytical Question:** *How well is our forecasting engine capturing baseline demand, weekend surges, and event uplifts?*

- **Visual 1 (Multi-Line Chart):** Actual Latent Demand vs 4-Week Moving Average vs Seasonal Naive vs Holt-Winters Forecast over time.
- **Visual 2 (Clustered Column Chart):** Day-of-Week Demand Profile (Surges on Friday, Saturday, Sunday).
- **Visual 3 (Table / Matrix):** Forecast Evaluation Scorecard across models:
  * Model Name, MAE, RMSE, WAPE (%), Selected Best Model Flag.
- **Visual 4 (Category Uplift Bar Chart):** Uplift impact of promotional events across categories.

---

## Page 5: Replenishment Execution & Plan Variance
**Analytical Question:** *Are suppliers delivering replenishment orders on time, and where are operational bottlenecks occurring?*

- **Visual 1 (Donut / Status Breakdown):** Replenishment Orders by Status (Completed, Partially Completed, Delayed, Cancelled).
- **Visual 2 (KPI Cards):** On-Time Fulfillment Adherence %, Quantity Adherence %.
- **Visual 3 (Root-Cause Breakdown Bar Chart):** Root-Cause Distribution of Lost Sales (Delayed Inbound vs Demand Spike vs Forecast Underestimation).
- **Visual 4 (Plan-vs-Actual Variance Table):** Planned Units vs Actual Requested vs Fulfilled Units with variance percentage and root-cause classification.
