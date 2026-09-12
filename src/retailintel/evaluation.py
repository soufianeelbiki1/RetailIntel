"""Export reproducible synthetic forecast evidence without hosted services."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from retailintel.synthetic import generate_retail_dataset
from retailintel.warehouse import build_warehouse


def build_evaluation_report(seed: int = 20260831, order_count: int = 600) -> dict:
    dataset = generate_retail_dataset(seed=seed, order_count=order_count)
    connection = build_warehouse(dataset)
    try:
        result = connection.execute(
            "select * from mart_forecast_evaluation "
            "order by evaluation_grain, category, product_id nulls first, baseline"
        )
        columns = [column[0] for column in result.description]
        rows = [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        for row in rows:
            for field in ("holdout_start", "holdout_end"):
                row[field] = row[field].isoformat()
            # Parallel floating-point sums may differ at machine epsilon.
            # Declare report precision so byte-level evidence is reproducible.
            for field in ("mae_units", "wape", "mean_error_units"):
                if row[field] is not None:
                    row[field] = round(float(row[field]), 12)
        start, end, sku_days = connection.execute(
            "select min(metric_date), max(metric_date), count(*) from mart_demand_daily"
        ).fetchone()
        return {
            "schema_version": 1,
            "metric_decimal_places": 12,
            "source": {
                "kind": "synthetic",
                "seed": seed,
                "order_count": order_count,
                "product_count": len(dataset.products),
                "duckdb_version": duckdb.__version__,
            },
            "protocol": {
                "target": "final recorded net units per SKU/calendar day",
                "method": "walk-forward one-day; prior observations only",
                "window": "final seven calendar days; complete prior seven days required",
                "category_aggregation": "pooled SKU-day errors, not category forecasts",
                "zero_demand_wape": None,
            },
            "history": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "sku_days": sku_days,
            },
            "metrics": {
                "mae_units": "mean absolute error in units per SKU-day",
                "wape": "absolute error / actual units; fraction, null at zero actual demand",
                "mean_error_units": "prediction minus actual; negative is underprediction",
            },
            "limitations": [
                "Synthetic results are not real retailer accuracy or inventory savings.",
                "One short window does not justify selecting a production policy.",
                "Final returns are not a model of point-in-time real data availability.",
                "Earlier observed holdout demand is available; not a fixed-origin forecast.",
            ],
            "evaluation": rows,
        }
    finally:
        connection.close()


def write_evaluation(path: str | Path, seed: int = 20260831, order_count: int = 600) -> Path:
    # Generate/validate before creating the output; no NaN/Infinity JSON values.
    content = (
        json.dumps(build_evaluation_report(seed, order_count), indent=2, allow_nan=False) + "\n"
    )
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="build/forecast-evaluation.json")
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--order-count", type=int, default=600)
    args = parser.parse_args()
    if args.order_count <= 0:
        parser.error("--order-count must be positive")
    print(write_evaluation(args.output, args.seed, args.order_count))


if __name__ == "__main__":
    main()
