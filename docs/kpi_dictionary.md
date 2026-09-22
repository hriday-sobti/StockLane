# KPI Dictionary

This document defines all primary metrics used across Python, SQL views, and Power BI dashboards.

---

### 1. Availability %
- **Definition:** The percentage of SKU-store days where customer demand was fully met without a stockout.
- **Formula:**
  $$\text{Availability } \% = \left(1 - \frac{\text{Count of SKU-Store Days with Cancelled Units } > 0}{\text{Total Demanded SKU-Store Days}}\right) \times 100$$
- **Python:** `(1.0 - (df['cancelled_units'] > 0).mean()) * 100.0`
- **SQL View:** `(1.0 - SUM(CASE WHEN cancelled_units > 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(*)) * 100.0`
- **Power BI DAX:** `DIVIDE(TotalDemanded - StockoutCount, TotalDemanded, 1.0) * 100`

---

### 2. Order Fill Rate %
- **Definition:** The share of demanded units successfully delivered to customers.
- **Formula:**
  $$\text{Fill Rate } \% = \frac{\sum \text{Fulfilled Units}}{\sum \text{Requested Units}} \times 100$$
- **Edge cases:** Defaults to 100.0% when requested units = 0.
- **Python:** `(df['fulfilled_units'].sum() / df['requested_units'].sum()) * 100.0`
- **SQL View:** `ROUND(SUM(fulfilled_units) * 100.0 / NULLIF(SUM(requested_units), 0), 3)`
- **Power BI DAX:** `DIVIDE(SUM(fact_sales[fulfilled_units]), SUM(fact_sales[requested_units]), 1.0) * 100`

---

### 3. Stockout Rate %
- **Definition:** Proportion of demand opportunities that encountered a stockout.
- **Formula:**
  $$\text{Stockout Rate } \% = 100.0 - \text{Availability } \%$$
- **Python:** `(df['cancelled_units'] > 0).mean() * 100.0`
- **SQL View:** `ROUND(SUM(CASE WHEN cancelled_units > 0 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 3)`

---

### 4. Days of Cover (DoC)
- **Definition:** How many days current on-hand stock will last given expected daily demand.
- **Formula:**
  $$\text{Days of Cover} = \frac{\text{Closing Stock}}{\max(\text{Expected Daily Demand}, 0.2)}$$
- **Edge cases:** A safe floor of 0.2 units/day prevents division-by-zero on slow-moving SKUs.
- **Python:** `np.round(df['closing_stock'] / np.maximum(0.2, df['forecast_daily_mean']), 2)`
- **SQL View:** `ROUND(closing_stock / GREATEST(rolling_7d_velocity, 0.5), 2)`

---

### 5. Safety Stock
- **Definition:** Buffer inventory held to protect against demand spikes and supplier lead-time variability.
- **Formula:**
  $$\text{Safety Stock} = \left\lceil Z \times \sigma_{\text{demand}} \times \sqrt{L_{\text{days}}} \right\rceil$$
- **Parameters:**
  * $Z = 1.645$ (corresponding to a 95% cycle service level)
  * $\sigma_{\text{demand}} =$ Standard deviation of daily forecast demand
  * $L_{\text{days}} = \max(0.5, \text{Lead Time Hours} / 24.0)$

---

### 6. Reorder Point (ROP)
- **Definition:** The inventory level that triggers a replenishment order.
- **Formula:**
  $$\text{ROP} = \left\lceil (\text{Daily Demand} \times L_{\text{days}}) + \text{Safety Stock} \right\rceil$$

---

### 7. Target Stock
- **Definition:** The target inventory position needed to cover the order lead time plus the replenishment review horizon.
- **Formula:**
  $$\text{Target Stock} = \left\lceil (\text{Daily Demand} \times \text{Coverage Horizon Days}) + \text{Safety Stock} \right\rceil$$

---

### 8. Forecast Error (WAPE)
- **Weighted Absolute Percentage Error (WAPE):**
  $$\text{WAPE} = \frac{\sum |A_t - F_t|}{\sum A_t}$$
- **Rationale:** Avoids the division-by-zero problem of MAPE when actual demand is 0 on intermittent days.
