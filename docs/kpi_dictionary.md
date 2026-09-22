# StockLane KPI Dictionary

## Authoritative Cross-Layer KPI Definitions
To ensure 100% consistency across Python, PostgreSQL/DuckDB, and Power BI, each metric has a single canonical formula.

---

### 1. Availability %
- **Business Meaning:** The proportion of demand opportunities where inventory was available to fulfill customer orders without stockouts.
- **Canonical Formula:**
  $$\text{Availability } \% = \left(1 - \frac{\text{Count of SKU-Store Days with Cancelled Units } > 0}{\text{Total Demanded SKU-Store Days}}\right) \times 100$$
- **Grain:** Network / City / Store / Category / SKU level over time window.
- **Python Implementation:** `(1.0 - (df['cancelled_units'] > 0).mean()) * 100.0`
- **SQL Implementation:** `(1.0 - SUM(CASE WHEN cancelled_units > 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(*)) * 100.0`
- **Power BI Measure:** `DIVIDE(TotalDemanded - StockoutCount, TotalDemanded, 1.0) * 100`

---

### 2. Order Fill Rate %
- **Business Meaning:** The percentage of demanded product units successfully delivered to consumers.
- **Canonical Formula:**
  $$\text{Fill Rate } \% = \frac{\sum \text{Fulfilled Units}}{\sum \text{Requested Units}} \times 100$$
- **Edge Cases:** When requested units = 0, default to 100.0% (no unfilled demand).
- **Python Implementation:** `(df['fulfilled_units'].sum() / df['requested_units'].sum()) * 100.0`
- **SQL Implementation:** `ROUND(SUM(fulfilled_units) * 100.0 / NULLIF(SUM(requested_units), 0), 3)`
- **Power BI Measure:** `DIVIDE(SUM(fact_sales[fulfilled_units]), SUM(fact_sales[requested_units]), 1.0) * 100`

---

### 3. Stockout Rate %
- **Business Meaning:** Proportion of operational intervals where inventory was exhausted.
- **Canonical Formula:**
  $$\text{Stockout Rate } \% = 100.0 - \text{Availability } \%$$
- **Python Implementation:** `(df['cancelled_units'] > 0).mean() * 100.0`
- **SQL Implementation:** `ROUND(SUM(CASE WHEN cancelled_units > 0 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 3)`

---

### 4. Days of Cover (DoC)
- **Business Meaning:** Number of future days that current on-hand inventory will sustain expected customer demand.
- **Canonical Formula:**
  $$\text{Days of Cover} = \frac{\text{Closing Stock}}{\max(\text{Expected Daily Demand}, 0.2)}$$
- **Edge Cases:** Safe denominator floor (0.2) prevents division-by-zero or infinite spikes for slow-moving SKUs.
- **Python Implementation:** `np.round(df['closing_stock'] / np.maximum(0.2, df['forecast_daily_mean']), 2)`
- **SQL Implementation:** `ROUND(closing_stock / GREATEST(rolling_7d_velocity, 0.5), 2)`

---

### 5. Safety Stock
- **Business Meaning:** Buffer inventory held to protect against demand volatility and supplier lead-time delays during replenishment.
- **Canonical Formula:**
  $$\text{Safety Stock} = \left\lceil Z \times \sigma_{\text{demand}} \times \sqrt{L_{\text{days}}} \right\rceil$$
- **Parameters:**
  * $Z = 1.645$ (corresponding to a 95% target cycle service level)
  * $\sigma_{\text{demand}} =$ Standard deviation of daily forecast demand
  * $L_{\text{days}} = \max(0.5, \text{Lead Time Hours} / 24.0)$

---

### 6. Reorder Point (ROP)
- **Business Meaning:** Threshold inventory level that triggers an automated purchase / replenishment order.
- **Canonical Formula:**
  $$\text{ROP} = \left\lceil (\text{Daily Demand} \times L_{\text{days}}) + \text{Safety Stock} \right\rceil$$

---

### 7. Target Stock
- **Business Meaning:** Ideal inventory ceiling to cover the replenishment order cycle plus buffer.
- **Canonical Formula:**
  $$\text{Target Stock} = \left\lceil (\text{Daily Demand} \times \text{Coverage Horizon Days}) + \text{Safety Stock} \right\rceil$$

---

### 8. Forecast Error Metrics (MAE, RMSE, WAPE)
- **Weighted Absolute Percentage Error (WAPE):**
  $$\text{WAPE} = \frac{\sum |A_t - F_t|}{\sum A_t}$$
- **Rationale:** Avoids the fatal division-by-zero and extreme distortion of standard MAPE on zero-demand days in quick commerce.
