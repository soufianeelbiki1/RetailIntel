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


def test_dashboard_writer_creates_standalone_html(tmp_path: Path) -> None:
    output = write_dashboard(tmp_path / "inventory.html")

    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert content.startswith("<!doctype html>")
    assert "Inventory decisions" in content
    assert "<style>" in content
