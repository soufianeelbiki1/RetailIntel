# RetailIntel operating brief

RetailIntel is the commercial analytics and retail decision-intelligence flagship. It should answer inventory, merchandising, margin, return, customer, and supplier questions rather than function as a decorative sales dashboard.

## Guardrails

- Synthetic data must remain explicitly synthetic and reproducible.
- Keep order, order-line, inventory-snapshot, and purchase-order grains separate.
- Calculate money from order-line facts; never multiply revenue through joins to inventory or supplier facts.
- Returns must never exceed ordered quantity.
- Supplier reliability must be measured from actual vs expected receipt dates.
- Reorder recommendations must expose their assumptions and must not pretend to be optimized until demand uncertainty and service-level targets are modeled.
- RFM scores are relative to the observed analysis population and are not universal customer labels.
- Promotion comparisons are descriptive unless assignment is randomized or a defensible causal identification strategy is documented.
- All monetary values use integer minor units in the warehouse.

## Current state

- DuckDB analytical warehouse with supplier/product dimensions.
- Order, order-line, daily inventory-snapshot, and purchase-order facts.
- Reproducible synthetic retail operations with promotions, returns, inventory depletion, and supplier receipt timing.
- Product-day mart for gross sales, net sales after returns, COGS, gross margin, margin rate, and order counts.
- Latest-SKU inventory action mart with stockout/reorder/watch/healthy state and reorder gap.
- Supplier reliability mart with actual lead time, on-time delivery rate, and late-day measures.
- Customer RFM mart with recency/frequency/monetary quintiles and explicit customer segments.
- Monthly acquisition cohort mart with cohort age, active customers, retention, sales, orders, and margin.
- Promotion/category profitability mart with orders, units, returns, net sales, COGS, margin, realized unit price, and no causal `lift` claim.
- Documentation explains RFM population dependence, observed-retention semantics, history-boundary risk, and why promotion comparisons are descriptive rather than causal.
- Regression tests reconcile customer/promotion marts to atomic facts and enforce bounded scores, retention, margin, and non-causal naming.

## Next highest-value slice

Add day × SKU demand history, rolling demand volatility, explicit service-level assumptions, safety-stock/reorder quantity recommendations, and time-based forecast validation. Then build a decision dashboard that combines gross margin, stockout risk, supplier reliability, and replenishment uncertainty instead of ranking products by sales alone.
