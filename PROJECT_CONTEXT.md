# RetailIntel operating brief

RetailIntel is the commercial analytics and retail decision-intelligence flagship. It should answer inventory, merchandising, margin, return, and supplier questions rather than function as a decorative sales dashboard.

## Guardrails

- Synthetic data must remain explicitly synthetic and reproducible.
- Keep order, order-line, inventory-snapshot, and purchase-order grains separate.
- Calculate money from order-line facts; never multiply revenue through joins to inventory or supplier facts.
- Returns must never exceed ordered quantity.
- Supplier reliability must be measured from actual vs expected receipt dates.
- Reorder recommendations must expose their assumptions and must not pretend to be optimized until demand uncertainty and service-level targets are modeled.
- All monetary values use integer minor units in the warehouse.

## Current slice

- DuckDB analytical warehouse with supplier/product dimensions.
- Order, order-line, daily inventory-snapshot, and purchase-order facts.
- Reproducible synthetic retail operations with promotions, returns, inventory depletion, and supplier receipt timing.
- Product-day mart for gross sales, net sales after returns, COGS, gross margin, margin rate, and order counts.
- Latest-SKU inventory action mart with stockout/reorder/watch/healthy state and reorder gap.
- Supplier reliability mart with actual lead time, on-time delivery rate, and late-day measures.
- Regression tests for margin identities, bounded supplier rates, actionable low stock, fact grains, and return constraints.

## Next highest-value slice

Add customer/RFM and cohort marts, promotion-margin decomposition, demand history at day × SKU grain, rolling demand volatility, service-level assumptions, safety-stock/reorder quantity recommendations, and time-based forecast validation. Then build a decision dashboard that prioritizes high-margin stockout risk and low-reliability suppliers rather than ranking products by sales alone.
