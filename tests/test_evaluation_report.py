import json
import subprocess
import sys
from pathlib import Path

import pytest

from retailintel.evaluation import build_evaluation_report, write_evaluation


def test_report_is_deterministic_and_self_describing() -> None:
    first = build_evaluation_report(seed=42, order_count=30)
    assert first == build_evaluation_report(seed=42, order_count=30)
    assert first["source"]["kind"] == "synthetic"
    assert first["source"]["seed"] == 42
    assert first["source"]["order_count"] == 30
    assert first["history"]["sku_days"] == 600
    assert first["protocol"]["policy_baseline"] == ("prior seven-day mean used by replenishment")
    assert len(first["evaluation"]) == 48  # 20 SKUs + 4 categories, two baselines
    assert first["limitations"]
    assert all(row["evaluated_sku_days"] > 0 for row in first["evaluation"])
    assert first["evaluation"][0]["holdout_start"] == "2026-07-24"


def test_writer_preserves_null_wape_and_creates_nested_output(tmp_path: Path) -> None:
    output = write_evaluation(tmp_path / "nested" / "report.json", seed=42, order_count=30)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["source"]["order_count"] == 30
    assert report["evaluation"]
    undefined = [row for row in report["evaluation"] if row["wape"] is None]
    assert undefined
    assert all(row["actual_units"] == 0 for row in undefined)
    assert any(row["product_id"] is None for row in report["evaluation"])


def test_short_history_exports_empty_scores_not_invented_accuracy() -> None:
    report = build_evaluation_report(order_count=1)
    assert report["evaluation"] == []
    assert report["history"]["start"] == report["history"]["end"]


def test_invalid_generation_does_not_create_output(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    with pytest.raises(ValueError, match="positive"):
        write_evaluation(output, order_count=0)
    assert not output.exists()


def test_cli_generates_valid_json_and_rejects_invalid_count(tmp_path: Path) -> None:
    output = tmp_path / "cli.json"
    command = [sys.executable, "-m", "retailintel.evaluation", "--output", str(output)]
    result = subprocess.run(
        command + ["--order-count", "1", "--seed", "7"], capture_output=True, text=True, check=True
    )
    assert str(output) in result.stdout
    assert json.loads(output.read_text())["source"]["seed"] == 7
    before = output.read_bytes()
    invalid = subprocess.run(
        command + ["--order-count", "0"], capture_output=True, text=True, check=False
    )
    assert invalid.returncode == 2
    assert "must be positive" in invalid.stderr
    assert output.read_bytes() == before
