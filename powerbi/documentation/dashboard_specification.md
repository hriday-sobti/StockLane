# Power BI Operational Dashboard Specification

## Design Guidelines

The StockLane dashboards are built for dark store operations and inventory planners. The interface focuses on exception identification, root causes, and actionable recommendations.

- **Theme & Colors:**
  * Background: Clean light neutral (`#F8F9FA`)
  * Text & Cards: Deep Slate (`#1E293B`)
  * Normal / Safe: Green (`#10B981`)
  * Moderate / Warning: Amber (`#F59E0B`)
  * High Risk: Orange (`#EA580C`)
  * Critical / Stockout Breach: Red (`#DC2626`)

---

## Page 1: Instock Command Center

**Focus:** Daily network health overview and active exceptions.

- **KPI Cards:**
  1. Network Availability % (`Availability_Pct`)
  2. Order Fill Rate % (`Fill_Rate_Pct`)
  3. Stockout Rate % (`Stockout_Rate_Pct`)
  4. Lost Sales Exposure ($) (`Total_Lost_Sales_Value`)
  5. Critical SKU-Store Pairs (`Critical_Stockout_Count`)
  6. Average Days of Cover (`Average_Days_of_Cover`)
- **Visuals:**
  * Line Chart: 180-Day Network Availability Trend against a 98% target line.
  * Bar Chart: Availability and fill rate by product category.
  * Store Grid: Availability % by store, sorted ascending to surface lagging stores first.
  * Action Queue: Top 10 immediate operational interventions from `pbi_fact_action_queue`.

---

## Page 2: Stockout & Overstock Risk

**Focus:** Identifying which specific SKU-store combinations are running low or holding dead stock.

- **Filters:** City, Dark Store, Category, Priority Class (A/B/C), Risk Level.
- **Visuals:**
  * Risk Heatmap: City x dark store matrix colored by mean risk score.
  * Scatter Plot: Days of Cover (X-axis) vs Forecast Daily Demand (Y-axis), sized by lost sales exposure. Highlights both stockouts (bottom-left) and overstock (bottom-right).
  * High-Risk Table: Store, SKU, Category, Closing Stock, Safety Stock, Reorder Point, Days of Cover, Hours to Stockout, Risk Score, and Recommended Action.

---

## Page 3: Hyperlocal Inventory Redistribution

**Focus:** Lateral inter-store transfers within the same city.

- **Filters:** City, Category, Maximum Distance Slider.
- **Visuals:**
  * Transfer Summary Cards: Total Transfer Opportunities, Recommended Units, Projected Lost Sales Avoided ($), Average Distance (km).
  * Transfer Execution Table: Source Store, Destination Store, SKU, Transfer Qty, Source DoC (Before -> After), Destination DoC (Before -> After), Distance, Estimated Lost Sales Avoided ($), and Algorithmic Reason.

---

## Page 4: Demand Signals & Time-Series Forecasting

**Focus:** Comparing forecasting models and demand patterns.

- **Visuals:**
  * Multi-Line Trend: Actual Latent Demand vs Moving Average vs Seasonal Naive vs Holt-Winters.
  * Day-of-Week Column Chart: Demand profile showing Friday-Sunday volume surges.
  * Model Evaluation Scorecard: MAE, RMSE, WAPE (%) comparison table with best-model indicator.
  * Category Uplift Chart: Uplift percentage across promotional events.

---

## Page 5: Replenishment Execution & Plan Variance

**Focus:** Supplier performance, arrival delays, and plan-vs-actual variance.

- **Visuals:**
  * Status Breakdown: Donut chart showing orders (Completed, Partially Completed, Delayed, Cancelled).
  * KPI Cards: On-Time SLA Adherence %, Quantity Adherence %.
  * Root Cause Breakdown: Bar chart showing lost sales split by cause (Delayed Inbound vs Demand Spike vs Forecast Underestimation).
  * Plan-vs-Actual Table: Planned vs Requested vs Fulfilled units with variance percentage.
