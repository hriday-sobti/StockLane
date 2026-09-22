# StockLane Analytical Limitations

1. **Synthetic Nature of Operational Data:**
   All customer demand, sales volumes, store coordinates, and supplier deliveries are synthetically generated for simulation and demonstration purposes. No proprietary or confidential quick-commerce data is utilized.

2. **Simplified Intra-City Routing:**
   Distance between dark stores is estimated via haversine planar projection rather than real-time road routing APIs (e.g., Google Maps Distance Matrix). Real-world urban congestion and traffic peaks during delivery windows are not dynamically modeled.

3. **Homogeneous Order Picking Costs:**
   Warehouse labor costs for pick-and-pack operations and inter-store palletizing are approximated via flat base transfer fees rather than detailed time-and-motion labor models.

4. **Independent SKU Demand:**
   Demand cross-price elasticity (cannibalization or substitution between brands when a specific SKU stocks out) is omitted in this baseline version. When Brand A milk stocks out, consumers are assumed to register a lost sale rather than automatically purchasing Brand B.

5. **Linear Vehicle Capacity:**
   Redistribution vans are assumed to have flexible micro-capacity without strict volumetric cubing constraints, focusing primarily on unit and case-pack limits.
