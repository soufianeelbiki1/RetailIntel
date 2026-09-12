from pathlib import Path

from retailintel.dashboard import build_dashboard_html, write_dashboard
from retailintel.warehouse import build_warehouse


def test_dashboard_uses_replenishment_and_supplier_marts() -> None:
    connection = build_warehouse()
    try:
        html = build_dashboard_html(connection)
        product = connection.execute(
            """
            select product_name
            from mart_replenishment_recommendation
            order by product_name
            limit 1
            """
        ).fetchone()[0]
        supplier = connection.execute(
            "select supplier_name from dim_supplier order by supplier_id limit 1"
        ).fetchone()[0]
    finally:
        connection.close()

    assert "SYNTHETIC DATA" in html
    assert str(product) in html
    assert str(supplier) in html
    assert "Replenishment queue" in html
    assert "Supplier reliability" in html
    assert "95% service-level" in html
    assert "not proof of" in html
    assert "How uncertain is the demand estimate?" in html
    assert "Seasonal naive" in html
    assert "Trailing mean" in html
    assert "SKU-days" in html
    assert "WAPE can exceed 100%" in html
    assert 'tabindex="0" role="region"' in html
    assert 'scope="col"' in html


def test_dashboard_does_not_invent_accuracy_when_evaluation_is_empty() -> None:
    connection = build_warehouse()
    try:
        connection.execute(
            "create table evaluation_fixture as select * from mart_forecast_evaluation where false"
        )
        connection.execute(
            "create or replace view mart_forecast_evaluation as select * from evaluation_fixture"
        )
        html = build_dashboard_html(connection)
    finally:
        connection.close()
    assert "No eligible observations" in html
    assert "No accuracy score is inferred" in html


def test_dashboard_preserves_undefined_wape_and_escapes_categories() -> None:
    connection = build_warehouse()
    try:
        connection.execute(
            "create table evaluation_fixture as "
            "select * replace (NULL::double as wape, '<test>' as category) "
            "from mart_forecast_evaluation"
        )
        connection.execute(
            "create or replace view mart_forecast_evaluation as select * from evaluation_fixture"
        )
        html = build_dashboard_html(connection)
    finally:
        connection.close()
    assert "Undefined (zero demand)" in html
    assert "&lt;test&gt;" in html
    assert "<test>" not in html


def test_dashboard_writer_creates_standalone_html(tmp_path: Path) -> None:
    output = write_dashboard(tmp_path / "inventory.html")

    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert content.startswith("<!doctype html>")
    assert "Inventory decisions" in content
    assert "<style>" in content
