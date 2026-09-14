from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable

import duckdb

from retailintel.synthetic import SyntheticRetailDataset, generate_retail_dataset

SQL_DIR = files("retailintel").joinpath("sql")


def _execute_script(connection: duckdb.DuckDBPyConnection, path: Traversable) -> None:
    connection.execute(path.read_text(encoding="utf-8"))


def build_warehouse(
    dataset: SyntheticRetailDataset | None = None,
    database: str = ":memory:",
) -> duckdb.DuckDBPyConnection:
    dataset = dataset or generate_retail_dataset()
    connection = duckdb.connect(database)
    _execute_script(connection, SQL_DIR.joinpath("schema.sql"))

    connection.executemany("insert into dim_supplier values (?, ?, ?)", dataset.suppliers)
    connection.executemany("insert into dim_product values (?, ?, ?, ?, ?, ?)", dataset.products)
    connection.executemany("insert into fact_order values (?, ?, ?, ?)", dataset.orders)
    connection.executemany(
        "insert into fact_order_line values (?, ?, ?, ?, ?, ?, ?)", dataset.order_lines
    )
    connection.executemany(
        "insert into fact_inventory_snapshot values (?, ?, ?, ?, ?, ?)",
        dataset.inventory_snapshots,
    )
    if dataset.purchase_orders:
        connection.executemany(
            "insert into fact_purchase_order values (?, ?, ?, ?, ?, ?, ?)",
            dataset.purchase_orders,
        )

    _execute_script(connection, SQL_DIR.joinpath("marts", "product_daily.sql"))
    _execute_script(connection, SQL_DIR.joinpath("marts", "inventory_action.sql"))
    _execute_script(connection, SQL_DIR.joinpath("marts", "supplier_reliability.sql"))
    _execute_script(connection, SQL_DIR.joinpath("marts", "customer_rfm.sql"))
    _execute_script(connection, SQL_DIR.joinpath("marts", "customer_cohort.sql"))
    _execute_script(connection, SQL_DIR.joinpath("marts", "promotion_margin.sql"))
    _execute_script(connection, SQL_DIR.joinpath("marts", "demand_daily.sql"))
    _execute_script(connection, SQL_DIR.joinpath("marts", "forecast_evaluation.sql"))
    _execute_script(connection, SQL_DIR.joinpath("marts", "replenishment_recommendation.sql"))
    return connection
