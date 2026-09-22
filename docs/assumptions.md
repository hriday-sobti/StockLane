# Model Assumptions & Parameter Choices

## 1. Network Geometry & Dark Stores

- **4 Cities:** Bengaluru, Delhi, Mumbai, and Hyderabad serve as regional clusters.
- **Store Count:** 10 dark stores per city (40 stores total). Each store operates 18 hours daily (06:00 to 24:00), which matches typical quick-commerce operating hours in Indian metros.
- **Storage Capacity:** Dark store holding capacity ranges between 65,000 and 110,000 units. A 90% buffer threshold is applied to ensure aisles remain clear for picking and packing.

## 2. Demand Modeling

- Customer demand is treated as an **unobserved latent demand process** separate from fulfilled sales. Observed sales are capped when inventory reaches zero.
- Demand components:
  * SKU Base Velocity: High-velocity items move 25-65 units/day; medium items move 10-28 units/day; slow movers move 2.5-9 units/day.
  * Day-of-Week Factors: Demand increases noticeably toward the weekend: Monday (0.90), Tuesday (0.85), Wednesday (0.85), Thursday (0.92), Friday (1.18), Saturday (1.38), Sunday (1.42).
  * Local Catchment Index: Each store has a catchment footfall multiplier between 0.80 and 1.30.
  * City Demand Multiplier: Regional market sizes: Bengaluru (1.15), Delhi (1.20), Mumbai (1.25), Hyderabad (1.05).
  * Calendar Events & Promotions: Selected categories receive 20% to 50% demand uplifts during specific date windows.
  * Random Variation: Modeled with heteroskedastic variance proportional to the square root of demand ($\sigma = 0.4 \sqrt{\mu}$).

## 3. Physical Inventory Flow

- **Balance Equation:**
  $$\text{Closing Stock} = \text{Opening Stock} + \text{Inbound} + \text{Transfer In} - \text{Transfer Out} - \text{Sold Units} - \text{Damaged Units}$$
  This equation is verified on every daily record. Damaged stock is capped at available on-hand inventory.
- **Supplier Lead Times:**
  * Fresh Produce / Dairy: 12 to 24 hours
  * Packaged FMCG / Beverages: 24 to 48 hours
  * Staples / Personal Care / Household: 48 to 96 hours
- **Supplier Disruptions:**
  * 92% of orders arrive on schedule with full quantities.
  * 4% arrive 24 hours late due to logistics bottlenecks.
  * 3% arrive partially fulfilled (70% quantity allocation).
  * 1% are cancelled due to hub supply shortages.

## 4. Redistribution Rules

- Transfers only occur **within the same city** up to a 25 km limit.
- Transfer cost formula: $C = \$20.00 + (\$1.50 \times \text{distance in km})$.
- **Source Protection:** A transfer is rejected if it drops the source store's Days of Cover below 3.5 days.
- Minimum transfer threshold is 6 units to prevent uneconomic micro-shipments.
