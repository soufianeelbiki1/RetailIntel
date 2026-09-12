# Forecast evaluation semantics

Business question: does the replenishment demand estimate outperform the simplest
weekly baseline, and where are its errors concentrated? This report makes that
comparison inspectable; it does not automatically change replenishment policy.

## Protocol

- Target: net units ordered less returned units at SKU/calendar-day grain.
- Last seven calendar days of the warehouse form the scored window.
- Trailing mean: average of the previous seven days, including zero-demand days.
- Seasonal naive: observed demand exactly seven calendar days earlier.
- Both methods use exactly the same eligible rows: a complete seven-day history
  and a non-null weekly lag. Short histories produce no score rather than invented accuracy.
- Predictions are walk-forward one-day predictions; earlier observed holdout
  demand is available. This is not a fixed-origin multi-day replenishment simulation.

## Metrics

| Column | Meaning |
| --- | --- |
| evaluated_sku_days | Number of scored SKU-day observations, not number of customers/orders |
| actual_units | Sum of observed demand in eligible scored rows |
| mae_units | Mean absolute error, in units per SKU-day |
| wape | Total absolute error / total actual units; null when actual units are zero |
| mean_error_units | Mean prediction minus actual; negative means underprediction |
| holdout_start / holdout_end | Actual eligible scored date range |

Category metrics pool errors over their SKU-days (micro-average); they are not
an unweighted average of SKU WAPE percentages and do not score aggregated
category forecasts. Product rows use evaluation_grain = sku; category rows have
evaluation_grain = category and a null product_id.

## Evidence and limitations

Tests hand-calculate errors for a known demand step, check zero-demand WAPE,
short-history exclusion, shared baseline populations and category pooling.
Changing the last observed demand does not change its own or prior trailing
forecasts. Existing tests separately verify prior-only trailing windows.

All input data is synthetic. A single short holdout is not sufficient to select
a production model, estimate inventory savings or claim service-level results.
The target uses final recorded returns; delayed real-world returns would require
point-in-time data availability modelling. Further work should test longer
histories and multiple rolling windows before recommending a policy change.
