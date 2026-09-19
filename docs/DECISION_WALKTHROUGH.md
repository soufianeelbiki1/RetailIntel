# Inventory planning: a reproducible decision walkthrough

## The decision

A planner needs to choose which SKUs to investigate for replenishment, while
understanding how uncertain the demand estimate is. RetailIntel keeps the
operational calculation and its holdout evidence distinct but visible in the
same queue row: a reorder calculation is not proof that a forecast is accurate
or a purchase order should be placed automatically.

This is a portfolio demonstration using generated operations, not work for a
real retailer. No revenue gains, stockout reductions or production adoption are
claimed. Inventory snapshots and orders are generated separately; this sample
is not a reconciled inventory movement ledger.

## Reproduce from a checkout

Use Python 3.11 or 3.12 in a fresh virtual environment. No cloud credentials,
database server, paid model or API call is needed after installing dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python -m retailintel.evaluation --seed 20260831 --order-count 600 \
  --output build/forecast-evaluation.json
python -m retailintel.dashboard --seed 20260831 --order-count 600 \
  --output build/retailintel-dashboard.html
```

On Windows activate with `.venv\Scripts\Activate.ps1`. The SQL scripts ship as
package resources, so an installed wheel can run outside the repository too.
Open the generated HTML locally. Both default commands use seed `20260831`,
600 orders and 20 products. The JSON records the DuckDB version and scoring
protocol; file generation does not publish anything or change replenishment policy.
Both commands accept `--seed` and `--order-count`. Use the same values for both
artifacts. The dashboard displays those inputs, its demand-history range, the
inventory snapshot date and the evaluation cutoff so mismatched evidence is
visible during review.

## Inspect the evidence

The default synthetic history covers July 1–30, 2026. Its final July 24–30
window scores 35 SKU-days per category for each baseline (five SKUs × seven
days). Category results pool individual SKU-day errors, rather than predicting
aggregate category demand. JSON declares 12 decimal places for error metrics to
stabilise machine-epsilon differences in parallel floating-point aggregation;
this table is rounded further. A history too short to score exports an empty
evaluation array rather than invented accuracy.

Locally reproduced on September 12, 2026 with DuckDB 1.5.5:

| Synthetic category | Trailing-mean WAPE | Seasonal-naive WAPE |
| --- | ---: | ---: |
| Accessories | 61.49% | 88.82% |
| Apparel | 63.07% | 79.26% |
| Footwear | 64.06% | 86.02% |
| Home | 71.90% | 103.30% |

These high errors are useful evidence to show, not conceal. WAPE can exceed
100%; it is error relative to actual demand, not an accuracy score bounded at
100%. The mean baseline has lower pooled error in this one generated window,
but that does not establish a preferred real-world policy. Negative mean error
indicates underprediction; MAE reports typical absolute error in units. Null
WAPE means there was no actual demand in scored rows, not perfect accuracy.
See [metric semantics](forecast_evaluation.md) for eligibility and availability limits.

## Walk through a planner investigation

1. Start with the dashboard's stockout/reorder queue. Inspect on-hand/on-order
   quantities, supplier lead-time evidence, safety stock and proposed order quantity.
2. In the same row, compare the policy mean and seasonal-naive holdout MAE/WAPE
   on matching SKU-days. Use the JSON's `evaluation` array for the exact record.
   Category evidence cannot be substituted for the individual SKU's evidence.
3. Treat a large error or underprediction as a reason to investigate, not as
   an automatic instruction to inflate orders. Review promotions, returns,
   supplier variability and whether the observed period represents future demand.
4. Before approving a real order, require reconciled stock movements, costs,
   lead-time uncertainty and multiple rolling evaluation windows. The demo's
   fixed 95% service target is an input assumption, not an achieved service level.

## Engineering evidence to inspect

- Dense SKU/calendar-day history includes zero-demand days; prior-only windows
  avoid using a target to predict itself.
- Separate fact grains prevent stock and revenue multiplication through joins.
- The evaluated prior-only mean is the same demand input used by the current
  replenishment formula; 28-day volatility remains a separate safety-stock input.
- Comparable baseline populations and pooled category errors are implemented in
  `src/retailintel/sql/marts/forecast_evaluation.sql`, not hand-entered dashboard numbers.
- Tests cover known errors, undefined WAPE, insufficient history, shared
  observations, future perturbation and deterministic JSON export. CI runs the
  suite on two Python versions.
- The report carries provenance and limitations, exports JSON nulls faithfully
  and rejects nonstandard NaN/Infinity. No hosted infrastructure is required.
- The dashboard exposes the generator inputs and point-in-time cutoffs used by
  its queue and forecast tables; it rejects invalid counts without overwriting
  an existing artifact.

Next product step: evaluate longer histories and multiple rolling windows before
changing any policy, then compare service-level and lead-time scenarios.
