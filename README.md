# RetailIntel

RetailIntel is a DuckDB retail analytics project focused on inventory, margin, customer behavior, supplier reliability and replenishment decisions.

The warehouse keeps commercial facts at separate grains so revenue, stock and supplier metrics are not accidentally multiplied through joins.

## Warehouse model

- product and supplier dimensions;
- order and order-line facts;
- daily inventory snapshots;
- purchase-order facts.

Current marts include product-day profitability, supplier reliability, customer RFM, acquisition cohorts, promotion/category economics, dense SKU-day demand history and replenishment recommendations.

## Inventory dashboard

Generate a standalone browser dashboard from the DuckDB warehouse:

```bash
python -m retailintel.dashboard --output build/retailintel-dashboard.html
```

The dashboard combines:

- stockout, reorder, watch and healthy action counts;
- total recommended reorder quantity;
- SKU-level mean demand and 28-day demand volatility;
- safety stock and reorder points;
- supplier contracted/actual lead time and on-time delivery rate;
- an ordered replenishment queue.

The generated HTML includes its own CSS and requires no dashboard server. All displayed values come from the reproducible synthetic warehouse. Reorder recommendations remain planning outputs under the documented service-level assumptions, not claims of optimal inventory.

## Demand and replenishment

The demand model builds a complete SKU × calendar-day spine, including zero-demand days. Forecasts use a seven-day trailing mean based only on prior observations, and the warehouse also calculates a 28-day demand-volatility estimate.

The current replenishment policy uses a fixed 95% service target (`z = 1.645`) and calculates:

- safety stock;
- reorder point;
- inventory position (`on_hand + on_order`);
- recommended reorder quantity;
- action state: `healthy`, `watch`, `reorder` or `stockout`.

These are transparent planning formulas, not a claim of globally optimal inventory.

## Customer and commercial analysis

- RFM scoring and customer segments;
- monthly acquisition cohorts and observed retention;
- product/category gross margin and returns;
- supplier on-time delivery and lead-time measures;
- promotion/category comparisons.

Promotion analysis is descriptive. The data does not support a causal lift claim.

## Forecast evaluation

Export a self-describing JSON report without a database server or model API:

```bash
python -m retailintel.evaluation --output build/forecast-evaluation.json
```

The report records the synthetic seed, input size, DuckDB version, scoring
protocol, metrics and limitations alongside the scores. See the
[business decision walkthrough](docs/DECISION_WALKTHROUGH.md) to reproduce and
interpret the evidence rather than treating a forecast as an inventory guarantee.

`mart_forecast_evaluation` compares the seven-day trailing mean with a seven-day
seasonal-naive baseline on the same eligible SKU-days in the final seven calendar
days. It reports MAE, WAPE, signed mean error, observed demand and evaluated
sample counts by SKU and category. Category errors are pooled across SKU-days;
WAPE is undefined when observed demand is zero.

```sql
select category, baseline, evaluated_sku_days, mae_units, wape, mean_error_units
from mart_forecast_evaluation
where evaluation_grain = 'category'
order by category, baseline;
```

This is walk-forward one-day evaluation: each prediction can use earlier observed
holdout days, never its own target or later demand. It is not a fixed-origin
seven-day forecast or evidence of real retailer accuracy. The reproducible
synthetic sample is intentionally limited. See [evaluation semantics](docs/forecast_evaluation.md).

## Synthetic data

The repository generates its own retail operations for repeatable tests. It contains no real customer, retailer or supplier records.

## Example

```python
from retailintel import build_warehouse

connection = build_warehouse()
recommendations = connection.execute(
    """
    select product_id, recommended_action, recommended_reorder_qty
    from mart_replenishment_recommendation
    order by recommended_reorder_qty desc
    """
).fetchall()
```

## Run and test

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
pytest -q
python -m retailintel.dashboard --output build/retailintel-dashboard.html
```

CI runs on Python 3.11 and 3.12.

SQL lives in `src/retailintel/sql` and ships as package data. The wheel-install
regression builds and installs the wheel into a temporary directory, then runs
the report and dashboard outside the checkout. Editable-install success alone
does not establish distributable-package correctness.

`docs/data_dictionary.md` documents warehouse grains and metric definitions.

## Roadmap

- test longer histories and multiple holdout windows before selecting a forecasting policy;
- add more transparent baselines without hiding cold-start or zero-demand cases;
- model supplier lead-time variability in replenishment scenarios;
- compare service-level and order-quantity scenarios;
- add dashboard scenario controls once the validation metrics are in place.
