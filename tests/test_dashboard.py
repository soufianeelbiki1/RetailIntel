import subprocess
import sys
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from retailintel import generate_retail_dataset
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
    assert "Evidence provenance" in html
    assert "Caller-provided DuckDB warehouse" in html
    assert "Demand history" in html
    assert "Decision cutoff" in html
    assert str(product) in html
    assert str(supplier) in html
    assert "Replenishment queue" in html
    assert "Supplier reliability" in html
    assert "95% service-level" in html
    assert "not proof of" in html
    assert "How uncertain is the demand estimate?" in html
    assert "Seasonal naive" in html
    assert "Policy 7-day mean" in html
    assert "Policy mean (7d)" in html
    assert "Policy holdout evidence" in html
    assert "Seasonal comparator" in html
    assert "MAE " in html
    assert "SKU-days" in html
    assert "WAPE can exceed 100%" in html
    assert html.count('tabindex="0" role="region"') == 3
    assert 'aria-label="Supplier reliability, horizontally scrollable"' in html
    assert 'aria-label="Replenishment queue, horizontally scrollable"' in html
    assert "#707a89" not in html
    assert "#596273" in html
    assert 'scope="col"' in html
    assert html.count('class="evidence-cell"') == 30


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
    assert "Not scored" in html


def test_dashboard_places_matching_sku_evidence_in_the_queue_row() -> None:
    connection = build_warehouse()
    try:
        product, policy_samples, policy_mae, policy_wape, seasonal_mae = connection.execute(
            """
            with prioritized as (
                select *
                from mart_replenishment_recommendation
                order by
                    case recommended_action
                        when 'stockout' then 0
                        when 'reorder' then 1
                        when 'watch' then 2
                        else 3
                    end,
                    recommended_reorder_qty desc,
                    product_name
                limit 1
            )
            select
                p.product_name,
                max(e.evaluated_sku_days) filter (where e.baseline = 'trailing_mean_7d'),
                max(e.mae_units) filter (where e.baseline = 'trailing_mean_7d'),
                max(e.wape) filter (where e.baseline = 'trailing_mean_7d'),
                max(e.mae_units) filter (where e.baseline = 'seasonal_naive_7d')
            from prioritized r
            join dim_product p using (product_id)
            join mart_forecast_evaluation e using (product_id)
            where e.evaluation_grain = 'sku'
            group by r.product_id, p.product_name
            """
        ).fetchone()
        html = build_dashboard_html(connection)
    finally:
        connection.close()

    start = html.index(f'<th scope="row">{product}</th>')
    row = html[start : html.index("</tr>", start)]
    assert f"MAE {policy_mae:.2f} units" in row
    assert f"WAPE {policy_wape * 100:.1f}% · {policy_samples} SKU-days" in row
    assert f"MAE {seasonal_mae:.2f} units" in row


def test_dashboard_hides_evidence_observed_after_the_inventory_snapshot() -> None:
    dataset = generate_retail_dataset()
    latest_snapshot = max(row[0] for row in dataset.inventory_snapshots)
    cutoff = latest_snapshot - timedelta(days=10)
    lagged_inventory = replace(
        dataset,
        inventory_snapshots=[row for row in dataset.inventory_snapshots if row[0] <= cutoff],
    )
    connection = build_warehouse(lagged_inventory)
    try:
        html = build_dashboard_html(connection)
    finally:
        connection.close()

    assert html.count("Not scored") == 30


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
    assert "Seed 20,260,831 · 600 generated orders" in content
    assert "2026-07-01 – 2026-07-30" in content
    assert "Inventory 2026-07-30 · evaluation 2026-07-30" in content


def test_dashboard_custom_inputs_are_visible_and_invalid_cli_preserves_output(
    tmp_path: Path,
) -> None:
    output = write_dashboard(tmp_path / "inventory.html", seed=7, order_count=30)
    content = output.read_text(encoding="utf-8")
    assert "Seed 7 · 30 generated orders" in content

    command = [sys.executable, "-m", "retailintel.dashboard", "--output", str(output)]
    before = output.read_bytes()
    invalid = subprocess.run(
        command + ["--order-count", "0"], capture_output=True, text=True, check=False
    )
    assert invalid.returncode == 2
    assert "must be positive" in invalid.stderr
    assert output.read_bytes() == before


def test_dashboard_rejects_provenance_for_a_caller_provided_connection(tmp_path: Path) -> None:
    connection = build_warehouse()
    try:
        with pytest.raises(ValueError, match="caller-provided connection"):
            write_dashboard(tmp_path / "inventory.html", connection, seed=7, order_count=30)
    finally:
        connection.close()
    assert not (tmp_path / "inventory.html").exists()
