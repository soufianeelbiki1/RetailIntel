from __future__ import annotations

import duckdb
import pytest

from retailintel import build_warehouse, generate_retail_dataset


def scalar(connection: duckdb.DuckDBPyConnection, query: str):
    return connection.execute(query).fetchone()[0]


def test_generator_is_deterministic() -> None:
    first = generate_retail_dataset(seed=5, order_count=50)
    second = generate_retail_dataset(seed=5, order_count=50)

    assert first == second
    assert len(first.products) == 20
    assert len(first.orders) == 50


def test_warehouse_builds_expected_grains() -> None:
    connection = build_warehouse(generate_retail_dataset(order_count=200))

    assert scalar(connection, "select count(*) from dim_product") == 20
    assert scalar(connection, "select count(*) from dim_supplier") == 4
    assert scalar(connection, "select count(*) from fact_order") == 200
    assert scalar(connection, "select count(*) from fact_order_line") >= 200
    assert scalar(connection, "select count(*) from fact_inventory_snapshot") == 600
    assert scalar(connection, "select count(*) from fact_purchase_order") > 0


def test_profitability_mart_preserves_margin_identity() -> None:
    connection = build_warehouse()

    violations = scalar(
        connection,
        """
        select count(*)
        from mart_product_daily
        where net_sales_minor - cogs_minor <> gross_margin_minor
           or net_sales_minor > gross_sales_minor
           or gross_margin_rate < 0
           or gross_margin_rate > 1
        """,
    )

    assert violations == 0


def test_inventory_mart_surfaces_actionable_low_stock() -> None:
    connection = build_warehouse()

    assert scalar(connection, "select count(*) from mart_inventory_action") == 20
    assert scalar(
        connection,
        "select count(*) from mart_inventory_action "
        "where inventory_action in ('reorder', 'stockout')",
    ) > 0
    assert scalar(
        connection,
        "select count(*) from mart_inventory_action where reorder_gap_qty < 0",
    ) == 0


def test_supplier_reliability_rates_are_bounded() -> None:
    connection = build_warehouse()

    assert scalar(connection, "select count(*) from mart_supplier_reliability") == 4
    assert scalar(
        connection,
        """
        select count(*)
        from mart_supplier_reliability
        where on_time_delivery_rate < 0 or on_time_delivery_rate > 1
        """,
    ) == 0


def test_return_quantity_constraint_fails_closed() -> None:
    connection = build_warehouse(generate_retail_dataset(order_count=5))

    with pytest.raises(duckdb.ConstraintException):
        connection.execute(
            """
            insert into fact_order_line values (
                'ord-00001', 99, 'sku-001', 1, 2, 5000, 2500
            )
            """
        )
