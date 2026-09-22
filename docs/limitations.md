# Limitations & Scope

This project simulates a quick-commerce network and has several documented modeling simplifications:

1. **Synthetic Operational Data:**
   All demand patterns, sales transactions, store coordinates, and supplier deliveries are generated for analytical modeling. The dataset does not use proprietary data from any commercial operator.

2. **Distance Approximations:**
   Distances between dark stores are calculated using planar haversine approximations rather than a live road-routing API (such as Google Maps or OSRM). Real-world routing would need to account for dynamic urban traffic, one-way streets, and peak delivery windows.

3. **Transfer Cost Assumptions:**
   Inter-store transfer costs are modeled with a flat base fee plus a per-kilometer rate ($20 + $1.50/km). In production, these costs would also factor in warehouse labor for picking and packing pallets, vehicle leasing, and driver wages.

4. **Product Substitution:**
   Customer demand is modeled independently per SKU. In reality, when a specific brand of whole milk is out of stock, some percentage of customers will buy an alternative brand (cross-price elasticity / cannibalization). StockLane currently treats all unfulfilled demand as lost sales.

5. **Vehicle Volume Constraints:**
   The redistribution engine assumes delivery vans have sufficient cubic capacity to handle the recommended transfers, focusing on unit counts and case packs rather than 3D volumetric pack fitting.
