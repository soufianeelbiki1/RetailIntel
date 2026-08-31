# RetailIntel

RetailIntel is a DuckDB retail analytics project focused on inventory, margin, customer behavior, supplier reliability and replenishment decisions.

The warehouse keeps commercial facts at separate grains so revenue, stock and supplier metrics are not accidentally multiplied through joins.

## Warehouse model

- product and supplier dimensions;
- order and order-line facts;
- daily inventory snapshots;
- purchase-order facts.

Current marts include product-day profitability, supplier reliability, customer RFM, acquisition cohorts, promotion/category economics, dense SKU-day demand history and replenishment recommendations.

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
```

CI runs on Python 3.11 and 3.12.

`docs/data_dictionary.md` documents warehouse grains and metric definitions.

## Roadmap

- compare the trailing mean with seasonal-naive and other transparent baselines;
- report WAPE/MAE by SKU and category on time-based holdouts;
- model supplier lead-time variability in replenishment scenarios;
- compare service-level and order-quantity scenarios;
- add an interactive inventory and merchandising dashboard backed by the warehouse.
