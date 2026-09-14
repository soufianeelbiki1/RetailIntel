from dataclasses import replace
from datetime import date, timedelta

import pytest

from retailintel import build_warehouse, generate_retail_dataset
from retailintel.synthetic import SyntheticRetailDataset


def fixture(demand: list[int]) -> SyntheticRetailDataset:
    start = date(2026, 7, 1)
    return SyntheticRetailDataset(
        suppliers=[("sup-1", "Test supplier", 5)],
        products=[("sku-1", "Test SKU", "test", "sup-1", 100, 200)],
        orders=[(f"ord-{i}", start + timedelta(days=i), "cus-1", None) for i in range(len(demand))],
        order_lines=[
            (f"ord-{i}", 1, "sku-1", max(units, 1), 0 if units else 1, 200, 100)
            for i, units in enumerate(demand)
        ],
        inventory_snapshots=[(start + timedelta(days=len(demand) - 1), "sku-1", 10, 0, 5, 2)],
        purchase_orders=[],
    )


def test_baselines_have_hand_calculated_holdout_errors() -> None:
    connection = build_warehouse(fixture([2] * 7 + [4] * 7))
    rows = connection.execute(
        "select baseline, evaluated_sku_days, actual_units, mae_units, wape, mean_error_units "
        "from mart_forecast_evaluation where evaluation_grain = 'sku' order by baseline"
    ).fetchall()
    assert rows[0] == ("seasonal_naive_7d", 7, 28, 2, 0.5, -2)
    assert rows[1][0:3] == ("trailing_mean_7d", 7, 28)
    assert rows[1][3:] == pytest.approx((8 / 7, 2 / 7, -8 / 7))


def test_zero_demand_has_undefined_wape_not_fake_perfect_accuracy() -> None:
    connection = build_warehouse(fixture([0] * 14))
    rows = connection.execute(
        "select actual_units, mae_units, wape from mart_forecast_evaluation"
    ).fetchall()
    assert len(rows) == 4
    assert all(row == (0, 0, None) for row in rows)


def test_insufficient_history_emits_no_evaluation() -> None:
    connection = build_warehouse(fixture([2] * 7))
    assert connection.execute("select count(*) from mart_forecast_evaluation").fetchone()[0] == 0


def test_category_metrics_pool_errors_and_baselines_share_observations() -> None:
    connection = build_warehouse(generate_retail_dataset())
    assert (
        connection.execute(
            "select count(*) from (select category, product_id, count(distinct baseline) as n, "
            "min(evaluated_sku_days) as lo, max(evaluated_sku_days) as hi "
            "from mart_forecast_evaluation group by category, product_id having n <> 2 or lo <> hi)"
        ).fetchone()[0]
        == 0
    )
    for category, baseline, observations, actual, mae, wape in connection.execute(
        "select category, baseline, evaluated_sku_days, actual_units, mae_units, wape "
        "from mart_forecast_evaluation where evaluation_grain = 'category'"
    ).fetchall():
        pooled = connection.execute(
            "select sum(evaluated_sku_days), sum(actual_units), "
            "sum(mae_units * evaluated_sku_days) / sum(evaluated_sku_days), "
            "sum(mae_units * evaluated_sku_days) / nullif(sum(actual_units), 0) "
            "from mart_forecast_evaluation where evaluation_grain = 'sku' "
            "and category = ? and baseline = ?",
            [category, baseline],
        ).fetchone()
        assert pooled == pytest.approx((observations, actual, mae, wape))


def test_prior_forecasts_do_not_change_when_a_future_observation_changes() -> None:
    dataset = fixture([2] * 7 + [4] * 7)
    changed = replace(
        dataset, order_lines=dataset.order_lines[:-1] + [("ord-13", 1, "sku-1", 99, 0, 200, 100)]
    )
    query = "select metric_date, forecast_7d_mean from mart_demand_daily order by metric_date"
    original = build_warehouse(dataset).execute(query).fetchall()
    mutated = build_warehouse(changed).execute(query).fetchall()
    assert original == mutated
