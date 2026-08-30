from __future__ import annotations

from pathlib import Path

import duckdb

from retailintel.synthetic import SyntheticRetailDataset, generate_retail_dataset

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"


def _execute_script(connection: duckdb.DuckDBPyConnection, path: Path) -> None:
    connection.execute(path.read_text(encoding="utf-8"))


def build_warehouse(
    dataset: SyntheticRetailDataset | None = None,
    database: str = ":memory:",
) -> duckdb.DuckDBPyConnection:
    dataset = dataset or generate_retail_dataset()
    connection = duckdb.connect(database)
    _execute_script(connection, SQL_DIR / "schema.sql")

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

    _execute_script(connection, SQL_DIR / "marts" / "product_daily.sql")
    _execute_script(connection, SQL_DIR / "marts" / "inventory_action.sql")
    _execute_script(connection, SQL_DIR / "marts" / "supplier_reliability.sql")
    return connection
