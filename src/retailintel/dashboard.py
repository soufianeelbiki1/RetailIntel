from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

import duckdb

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
.note { color: #707a89; font-size: .82rem; }
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
.card span { color: #707a89; font-size: .8rem; text-transform: uppercase; }
.card strong { display: block; margin-top: 8px; font-size: 1.65rem; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.panel { padding: 20px; overflow: auto; }
.full { margin-top: 18px; }
table { width: 100%; border-collapse: collapse; font-size: .88rem; }
th, td {
  padding: 10px 8px;
  text-align: left;
  border-bottom: 1px solid #edf0f3;
  white-space: nowrap;
}
th { color: #707a89; font-weight: 600; }
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
@media (max-width: 850px) {
  .cards { grid-template-columns: 1fr 1fr; }
  .grid { grid-template-columns: 1fr; }
}
@media (max-width: 520px) { .cards { grid-template-columns: 1fr; } }
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


def build_dashboard_html(connection: duckdb.DuckDBPyConnection) -> str:
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
            product_name,
            category,
            supplier_name,
            on_hand_qty,
            on_order_qty,
            mean_demand_28d,
            demand_stddev_28d,
            recommended_safety_stock_qty,
            recommended_reorder_point_qty,
            recommended_reorder_qty,
            recommended_action
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
        f"<td>{escape(str(product))}</td>"
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
        ) in reorder_rows
    )
    supplier_html = "".join(
        "<tr>"
        f"<td>{escape(str(name))}</td>"
        f"<td>{int(contracted):,}</td>"
        f"<td>{'—' if actual is None else f'{float(actual):.1f}'}</td>"
        f"<td>{'—' if on_time is None else f'{float(on_time) * 100:.1f}%'}</td>"
        f"<td>{'—' if late is None else f'{float(late):.1f}'}</td>"
        f"<td>{int(orders):,}</td>"
        "</tr>"
        for name, contracted, actual, on_time, late, orders in supplier_rows
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
    <table>
      <thead><tr><th>Supplier</th><th>Contract days</th><th>Actual days</th>
      <th>On-time</th><th>Late days</th><th>POs</th></tr></thead>
      <tbody>{supplier_html}</tbody>
    </table>
  </div>
</section>
<section class="panel full">
  <h2>Replenishment queue</h2>
  <table>
    <thead><tr><th>Product</th><th>Category</th><th>Supplier</th><th>On hand</th>
    <th>On order</th><th>Mean demand</th><th>Volatility</th><th>Safety stock</th>
    <th>Reorder point</th><th>Order qty</th><th>Action</th></tr></thead>
    <tbody>{reorder_html}</tbody>
  </table>
  <p class="note">
    Reorder quantities are planning outputs from the current baseline policy, not proof of
    globally optimal inventory. Forecasts use prior observations only.
  </p>
</section>
</main>
</body>
</html>"""


def write_dashboard(
    path: str | Path,
    connection: duckdb.DuckDBPyConnection | None = None,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    owns_connection = connection is None
    conn = connection or build_warehouse()
    try:
        output.write_text(build_dashboard_html(conn), encoding="utf-8")
    finally:
        if owns_connection:
            conn.close()
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the RetailIntel inventory dashboard")
    parser.add_argument("--output", default="build/retailintel-dashboard.html")
    args = parser.parse_args()
    print(write_dashboard(args.output))


if __name__ == "__main__":
    main()
