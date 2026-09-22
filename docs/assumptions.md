# StockLane Model Assumptions & Methodologies

## 1. Geographical & Operational Scope
- **4 Synthetic Cities:** Bengaluru, Delhi, Mumbai, Hyderabad. These act as regional operational clusters.
- **Dark Store Structure:** 10 dark stores per city (40 stores total). Each store operates 18 hours daily (06:00 to 24:00), reflecting quick-commerce fulfillment schedules.
- **Physical Capacity:** Dark store storage capacity ranges between 65,000 and 110,000 units. A 90% buffer threshold is enforced to preserve pick-pack aisle mobility.

## 2. Demand Modeling Assumptions
- Customer demand is modeled as an **unobserved latent demand process** separate from fulfilled sales. Observed fulfilled sales are truncated when on-hand stock hits zero.
- Demand components include:
  * SKU Base Velocity (High: 25-65/day, Medium: 10-28/day, Low: 2.5-9/day)
  * Day of Week Multipliers: Monday (0.90), Tuesday (0.85), Wednesday (0.85), Thursday (0.92), Friday (1.18), Saturday (1.38), Sunday (1.42).
  * Catchment Local Footfall Index: Uniform range between 0.80 and 1.30.
  * Regional Market Multiplier: Bengaluru (1.15), Delhi (1.20), Mumbai (1.25), Hyderabad (1.05).
  * Calendar Events & Promotions: 20% to 50% uplift applied to specific categories or SKUs.
  * Controlled Random Noise: Heteroskedastic variance proportional to square root of demand ($\sigma = 0.4 \sqrt{\mu}$).

## 3. Inventory & Logistics Physics
- **Stock Reconciliation Invariant:**
  $$\text{Closing Stock} = \text{Opening Stock} + \text{Inbound Stock} + \text{Transfer In} - \text{Transfer Out} - \text{Sold Units} - \text{Damaged Units}$$
  This is strictly enforced at machine level. Damaged stock cannot exceed available inventory.
- **Supplier Lead Times:** Categorized by product perishability:
  * Fresh Produce / Dairy: 12 to 24 hours
  * Packaged FMCG / Beverages: 24 to 48 hours
  * Staples / Personal Care / Household: 48 to 96 hours
- **Operational Disruption Rates:**
  * 92% of supplier orders arrive exactly on schedule with full quantity.
  * 4% arrive delayed by +24 hours due to logistics bottlenecks.
  * 3% arrive partially fulfilled (70% quantity allocation).
  * 1% are cancelled due to hub supply shortages.

## 4. Hyperlocal Redistribution Principles
- Redistribution is evaluated strictly **intra-city** (within a 25 km radius limit).
- Transfer cost is modeled as $C = \$20.00 + (\$1.50 \times \text{distance in km})$.
- Source stores **must maintain safety stock protection**: A transfer is prohibited if it causes the source store's Days of Cover to drop below 3.5 days.
- Minimum transfer threshold is 6 units to prevent uneconomic micro-shipments.
