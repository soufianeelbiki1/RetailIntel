from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

import duckdb

from retailintel.synthetic import (
    DEFAULT_SYNTHETIC_ORDER_COUNT,
    DEFAULT_SYNTHETIC_SEED,
    generate_retail_dataset,
)
from retailintel.warehouse import build_warehouse

STYLES = """
:root {
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  color: #172033;
  background: #f5f6f8;
}
* { box-sizing: border-box; }
body { margin: 0; }
main { max-width: 1220px; margin: auto; padding: 40px 24px 64px; }
h1 { font-size: clamp(2rem, 6vw, 4rem); margin: 5px 0 8px; }
h2 { font-size: 1.1rem; margin: 0 0 16px; }
.sub { color: #626d7d; max-width: 780px; line-height: 1.6; }
.note { color: #596273; font-size: .82rem; }
.cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 24px 0;
}
.card, .panel {
  background: white;
  border: 1px solid #dfe4ea;
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(20, 30, 50, .05);
}
.card { padding: 18px; }
.card span { color: #596273; font-size: .8rem; text-transform: uppercase; }
.card strong { display: block; margin-top: 8px; font-size: 1.65rem; }
.provenance {
  margin: 24px 0;
  padding: 18px 0;
  border-top: 1px solid #dfe4ea;
  border-bottom: 1px solid #dfe4ea;
}
.provenance h2 { margin-bottom: 12px; }
.provenance dl {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px 20px;
  margin: 0;
}
.provenance dl div { min-width: 0; }
.provenance dt {
  color: #596273;
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .04em;
}
.provenance dd { margin: 5px 0 0; font-size: .9rem; overflow-wrap: anywhere; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.panel { min-width: 0; padding: 20px; }
.full { margin-top: 18px; }
table { width: 100%; border-collapse: collapse; font-size: .88rem; }
th, td {
  padding: 10px 8px;
  text-align: left;
  border-bottom: 1px solid #edf0f3;
  white-space: nowrap;
}
th { color: #596273; font-weight: 600; }
.bar-row {
  display: grid;
  grid-template-columns: 100px 1fr 50px;
  gap: 10px;
  align-items: center;
  margin: 13px 0;
}
.bar-track { height: 10px; background: #edf0f3; border-radius: 20px; overflow: hidden; }
.bar { height: 100%; background: #334155; border-radius: 20px; }
.action { padding: 3px 8px; border-radius: 999px; font-size: .78rem; }
.action-stockout { background: #fee2e2; }
.action-reorder { background: #ffedd5; }
.action-watch { background: #fef3c7; }
.action-healthy { background: #dcfce7; }
.table-scroll { overflow-x: auto; }
.table-scroll:focus-visible { outline: 3px solid #334155; outline-offset: 3px; }
.evidence-note { color: #334155; line-height: 1.6; max-width: 900px; }
.evidence-cell { min-width: 150px; white-space: normal; }
.evidence-cell strong, .evidence-cell small { display: block; }
.evidence-cell strong { font-size: .84rem; }
.evidence-cell small { color: #596273; line-height: 1.45; margin-top: 3px; }
@media (max-width: 850px) {
  .cards { grid-template-columns: 1fr 1fr; }
  .provenance dl { grid-template-columns: 1fr 1fr; }
  .grid { grid-template-columns: 1fr; }
}
@media (max-width: 520px) {
  .cards, .provenance dl { grid-template-columns: 1fr; }
}
"""


def _bar(label: str, value: int, maximum: int) -> str:
    width = 0 if maximum <= 0 else max(3, round(value / maximum * 100))
    return (
        '<div class="bar-row">'
        f"<span>{escape(label)}</span>"
        '<div class="bar-track">'
        f'<div class="bar" style="width:{width}%"></div>'
        "</div>"
        f"<strong>{value:,}</strong>"
        "</div>"
    )


def _forecast_evidence(samples: int | None, mae: float | None, wape: float | None) -> str:
    if samples is None or mae is None:
        return '<span class="note">Not scored</span>'
    wape_text = "WAPE undefined" if wape is None else f"WAPE {float(wape) * 100:.1f}%"
    return (
        f"<strong>MAE {float(mae):.2f} units</strong>"
        f"<small>{wape_text} · {int(samples)} SKU-days</small>"
    )


def _baseline_label(baseline: str) -> str:
    labels = {
        "trailing_mean_7d": "Policy 7-day mean",
        "seasonal_naive_7d": "Seasonal naive",
    }
    return escape(labels.get(baseline, baseline))


def build_dashboard_html(
    connection: duckdb.DuckDBPyConnection,
    *,
    seed: int | None = None,
    order_count: int | None = None,
) -> str:
    history_start, history_end = connection.execute(
        "select min(metric_date), max(metric_date) from mart_demand_daily"
    ).fetchone()
    snapshot_date = connection.execute(
        "select max(snapshot_date) from mart_replenishment_recommendation"
    ).fetchone()[0]
    evidence_end = connection.execute(
        "select max(holdout_end) from mart_forecast_evaluation"
    ).fetchone()[0]

    if seed is None or order_count is None:
        generator_value = "Caller-provided DuckDB warehouse"
    else:
        generator_value = f"Seed {seed:,} · {order_count:,} generated orders"
    history_range = f"{history_start.isoformat()} – {history_end.isoformat()}"
    evaluation_cutoff = "not scored" if evidence_end is None else evidence_end.isoformat()
    decision_cutoff = f"Inventory {snapshot_date.isoformat()} · evaluation {evaluation_cutoff}"

    total_products, urgent_products, total_reorder_qty = connection.execute(
        """
        select
            count(*),
            count(*) filter (where recommended_action in ('stockout', 'reorder')),
            sum(recommended_reorder_qty)
        from mart_replenishment_recommendation
        """
    ).fetchone()
    average_on_time = connection.execute(
        """
        select coalesce(avg(on_time_delivery_rate), 0)
        from mart_supplier_reliability
        """
    ).fetchone()[0]

    action_rows = connection.execute(
        """
        select recommended_action, count(*)::bigint
        from mart_replenishment_recommendation
        group by recommended_action
        order by count(*) desc, recommended_action
        """
    ).fetchall()
    max_actions = max((int(row[1]) for row in action_rows), default=0)

    reorder_rows = connection.execute(
        """
        select
            r.product_name,
            r.category,
            r.supplier_name,
            r.on_hand_qty,
            r.on_order_qty,
            r.policy_demand_mean_7d,
            r.demand_stddev_28d,
            r.recommended_safety_stock_qty,
            r.recommended_reorder_point_qty,
            r.recommended_reorder_qty,
            r.recommended_action,
            e.policy_samples,
            e.policy_mae,
            e.policy_wape,
            e.seasonal_samples,
            e.seasonal_mae,
            e.seasonal_wape
        from mart_replenishment_recommendation r
        left join (
            select
                product_id,
                max(holdout_end) as evidence_end,
                max(evaluated_sku_days) filter (
                    where baseline = 'trailing_mean_7d'
                ) as policy_samples,
                max(mae_units) filter (
                    where baseline = 'trailing_mean_7d'
                ) as policy_mae,
                max(wape) filter (
                    where baseline = 'trailing_mean_7d'
                ) as policy_wape,
                max(evaluated_sku_days) filter (
                    where baseline = 'seasonal_naive_7d'
                ) as seasonal_samples,
                max(mae_units) filter (
                    where baseline = 'seasonal_naive_7d'
                ) as seasonal_mae,
                max(wape) filter (
                    where baseline = 'seasonal_naive_7d'
                ) as seasonal_wape
            from mart_forecast_evaluation
            where evaluation_grain = 'sku'
            group by product_id
        ) e on e.product_id = r.product_id and e.evidence_end <= r.snapshot_date
        order by
            case r.recommended_action
                when 'stockout' then 0
                when 'reorder' then 1
                when 'watch' then 2
                else 3
            end,
            r.recommended_reorder_qty desc,
            r.product_name
        limit 15
        """
    ).fetchall()

    supplier_rows = connection.execute(
        """
        select
            supplier_name,
            contracted_lead_time_days,
            actual_lead_time_days,
            on_time_delivery_rate,
            average_late_days,
            purchase_orders
        from mart_supplier_reliability
        order by on_time_delivery_rate asc nulls first, supplier_name
        """
    ).fetchall()

    actions_html = "".join(
        _bar(str(action).title(), int(count), max_actions) for action, count in action_rows
    )
    reorder_html = "".join(
        "<tr>"
        f'<th scope="row">{escape(str(product))}</th>'
        f"<td>{escape(str(category))}</td>"
        f"<td>{escape(str(supplier))}</td>"
        f"<td>{int(on_hand):,}</td>"
        f"<td>{int(on_order):,}</td>"
        f"<td>{float(mean_demand or 0):.1f}</td>"
        f"<td>{float(volatility or 0):.1f}</td>"
        f"<td>{int(safety_stock):,}</td>"
        f"<td>{int(reorder_point):,}</td>"
        f"<td><strong>{int(reorder_qty):,}</strong></td>"
        f'<td><span class="action action-{escape(str(action))}">'
        f"{escape(str(action))}</span></td>"
        '<td class="evidence-cell">'
        f"{_forecast_evidence(policy_samples, policy_mae, policy_wape)}"
        "</td>"
        '<td class="evidence-cell">'
        f"{_forecast_evidence(seasonal_samples, seasonal_mae, seasonal_wape)}"
        "</td>"
        "</tr>"
        for (
            product,
            category,
            supplier,
            on_hand,
            on_order,
            mean_demand,
            volatility,
            safety_stock,
            reorder_point,
            reorder_qty,
            action,
            policy_samples,
            policy_mae,
            policy_wape,
            seasonal_samples,
            seasonal_mae,
            seasonal_wape,
        ) in reorder_rows
    )
    supplier_html = "".join(
        "<tr>"
        f'<th scope="row">{escape(str(name))}</th>'
        f"<td>{int(contracted):,}</td>"
        f"<td>{'—' if actual is None else f'{float(actual):.1f}'}</td>"
        f"<td>{'—' if on_time is None else f'{float(on_time) * 100:.1f}%'}</td>"
        f"<td>{'—' if late is None else f'{float(late):.1f}'}</td>"
        f"<td>{int(orders):,}</td>"
        "</tr>"
        for name, contracted, actual, on_time, late, orders in supplier_rows
    )

    evaluation_rows = connection.execute(
        "select category, baseline, holdout_start, holdout_end, evaluated_sku_days, "
        "mae_units, wape, mean_error_units from mart_forecast_evaluation "
        "where evaluation_grain = 'category' order by category, baseline"
    ).fetchall()
    evaluation_html = "".join(
        "<tr>"
        f'<th scope="row">{escape(str(category))}</th>'
        f"<td>{_baseline_label(str(baseline))}</td>"
        f"<td>{start.isoformat()} – {end.isoformat()}</td>"
        f"<td>{int(samples):,}</td>"
        f"<td>{float(mae):.2f}</td>"
        f"<td>{'Undefined (zero demand)' if wape is None else f'{float(wape) * 100:.2f}%'}</td>"
        f"<td>{float(bias):+.2f}</td></tr>"
        for category, baseline, start, end, samples, mae, wape, bias in evaluation_rows
    )
    evaluation_content = (
        '<div class="table-scroll" tabindex="0" role="region" '
        'aria-label="Forecast comparison, horizontally scrollable">'
        "<table><caption>Final-seven-day category comparison on matching SKU-days</caption>"
        '<thead><tr><th scope="col">Category</th><th scope="col">Baseline</th>'
        '<th scope="col">Scored dates</th><th scope="col">SKU-days</th>'
        '<th scope="col">MAE units</th><th scope="col">WAPE</th>'
        '<th scope="col">Mean error units</th></tr></thead>'
        f"<tbody>{evaluation_html}</tbody></table></div>"
        if evaluation_rows
        else "<p>No eligible observations: at least seven prior days are required. "
        "No accuracy score is inferred.</p>"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RetailIntel — Inventory Decisions</title>
<style>{STYLES}</style>
</head>
<body>
<main>
<header>
  <div class="note">SYNTHETIC DATA · REPRODUCIBLE DUCKDB WAREHOUSE</div>
  <h1>Inventory decisions</h1>
  <p class="sub">
    Replenishment priorities, demand uncertainty and supplier reliability generated from
    RetailIntel marts. Recommendations use the documented 95% service-level assumption.
  </p>
</header>
<section class="provenance" aria-labelledby="provenance-heading">
  <h2 id="provenance-heading">Evidence provenance</h2>
  <dl>
    <div><dt>Source</dt><dd>Synthetic operations</dd></div>
    <div><dt>Generator input</dt><dd>{generator_value}</dd></div>
    <div><dt>Demand history</dt><dd>{history_range}</dd></div>
    <div><dt>Decision cutoff</dt><dd>{decision_cutoff}</dd></div>
  </dl>
</section>
<section class="cards">
  <div class="card"><span>Products</span><strong>{int(total_products):,}</strong></div>
  <div class="card"><span>Stockout / reorder</span><strong>{int(urgent_products):,}</strong></div>
  <div class="card">
    <span>Recommended units</span><strong>{int(total_reorder_qty or 0):,}</strong>
  </div>
  <div class="card">
    <span>Avg supplier on-time</span><strong>{float(average_on_time) * 100:.1f}%</strong>
  </div>
</section>
<section class="grid">
  <div class="panel"><h2>Inventory action mix</h2>{actions_html}</div>
  <div class="panel">
    <h2>Supplier reliability</h2>
    <div class="table-scroll" tabindex="0" role="region"
      aria-label="Supplier reliability, horizontally scrollable">
    <table>
      <thead><tr><th scope="col">Supplier</th><th scope="col">Contract days</th>
      <th scope="col">Actual days</th><th scope="col">On-time</th>
      <th scope="col">Late days</th><th scope="col">POs</th></tr></thead>
      <tbody>{supplier_html}</tbody>
    </table>
    </div>
  </div>
</section>
<section class="panel full">
  <h2>Replenishment queue</h2>
  <div class="table-scroll" tabindex="0" role="region"
    aria-label="Replenishment queue, horizontally scrollable">
  <table>
    <thead><tr><th scope="col">Product</th><th scope="col">Category</th>
    <th scope="col">Supplier</th><th scope="col">On hand</th>
    <th scope="col">On order</th><th scope="col">Policy mean (7d)</th>
    <th scope="col">Demand SD (28d)</th><th scope="col">Safety stock</th>
    <th scope="col">Reorder point</th><th scope="col">Order qty</th>
    <th scope="col">Action</th><th scope="col">Policy holdout evidence</th>
    <th scope="col">Seasonal comparator</th></tr></thead>
    <tbody>{reorder_html}</tbody>
  </table>
  </div>
  <p class="note">
    Reorder quantities are planning outputs from the current baseline policy, not proof of
    globally optimal inventory. The policy uses the same prior-only seven-day mean shown
    in its holdout evidence; neither baseline is selected automatically.
  </p>
</section>
<section class="panel full" aria-labelledby="forecast-heading">
  <h2 id="forecast-heading">How uncertain is the demand estimate?</h2>
  <p class="evidence-note">
    Synthetic forecast evidence, not achieved inventory savings. Lower error is better;
    WAPE can exceed 100% and is not an accuracy percentage. Category scores pool SKU-day
    errors, not aggregated category forecasts. Negative mean error means underprediction.
  </p>
  {evaluation_content}
  <p class="evidence-note">
    Walk-forward one-day predictions use prior observations; this is not a fixed-origin
    seven-day forecast. One short synthetic window does not justify selecting a real
    replenishment policy. Review individual SKU evidence before approving orders.
  </p>
</section>
</main>
</body>
</html>"""


def write_dashboard(
    path: str | Path,
    connection: duckdb.DuckDBPyConnection | None = None,
    *,
    seed: int | None = None,
    order_count: int | None = None,
) -> Path:
    output = Path(path)
    owns_connection = connection is None
    if owns_connection:
        resolved_seed = DEFAULT_SYNTHETIC_SEED if seed is None else seed
        resolved_order_count = DEFAULT_SYNTHETIC_ORDER_COUNT if order_count is None else order_count
        dataset = generate_retail_dataset(
            seed=resolved_seed,
            order_count=resolved_order_count,
        )
        conn = build_warehouse(dataset)
    else:
        if seed is not None or order_count is not None:
            raise ValueError("seed and order_count cannot describe a caller-provided connection")
        resolved_seed = None
        resolved_order_count = None
        conn = connection
    try:
        content = build_dashboard_html(
            conn,
            seed=resolved_seed,
            order_count=resolved_order_count,
        )
    finally:
        if owns_connection:
            conn.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the RetailIntel inventory dashboard")
    parser.add_argument("--output", default="build/retailintel-dashboard.html")
    parser.add_argument("--seed", type=int, default=DEFAULT_SYNTHETIC_SEED)
    parser.add_argument("--order-count", type=int, default=DEFAULT_SYNTHETIC_ORDER_COUNT)
    args = parser.parse_args()
    if args.order_count <= 0:
        parser.error("--order-count must be positive")
    print(write_dashboard(args.output, seed=args.seed, order_count=args.order_count))


if __name__ == "__main__":
    main()
