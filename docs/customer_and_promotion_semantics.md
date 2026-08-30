# Customer and promotion analytics semantics

All current observations are reproducible synthetic retail operations.

## RFM

`mart_customer_rfm` has one row per customer and measures:

- **Recency:** days since the customer's last order relative to the latest order date in the dataset.
- **Frequency:** distinct orders.
- **Monetary:** net sales after returned units.
- **Margin:** gross margin after returned units.

R, F, and M scores are relative quintiles inside the current synthetic population, so segment labels are descriptive prioritization tools rather than universal customer definitions. A different retailer, time window, or customer population can materially change score boundaries.

## Cohorts

`mart_customer_cohort` assigns a customer to the month of their first observed order and measures activity by months since that cohort month. Retention is active customers divided by original cohort size.

This is **observed repeat-purchase retention**, not subscription retention and not a causal measure of any marketing intervention. The first observed order may not be a customer's true lifetime first order if upstream history were truncated in a real dataset; a production pipeline would need a documented history boundary.

## Promotion economics

`mart_promotion_margin` compares realized economics across promotion codes and product categories: orders, units, returns, net sales, COGS, gross margin, margin rate, and realized unit price.

The mart intentionally does **not** expose `lift`, `incrementality`, or causal-effect fields. Promotion assignment in the synthetic retail generator is not a randomized experiment. Differences between promoted and non-promoted orders may reflect selection, product mix, customer mix, timing, or other confounding.

A future causal promotion study would require a randomized design or a defensible observational identification strategy with explicit assumptions. Until then, this mart supports margin monitoring and segmentation, not causal incrementality claims.
