"""Exercise the distributable package, not pytest's checkout import path."""

import json
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


def test_installed_wheel_runs_outside_checkout(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    wheel_dir = tmp_path / "wheels"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(repository),
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(wheel_dir.glob("retailintel-*.whl"))
    with ZipFile(wheel) as archive:
        sql_files = [name for name in archive.namelist() if name.endswith(".sql")]
    assert len(sql_files) == 10
    assert "retailintel/sql/schema.sql" in sql_files
    assert "retailintel/sql/marts/forecast_evaluation.sql" in sql_files

    installed = tmp_path / "installed"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            str(wheel),
            "--no-deps",
            "--no-index",
            "--target",
            str(installed),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(installed)
    subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "from pathlib import Path",
                    "import retailintel",
                    "assert Path(retailintel.__file__).is_relative_to(Path('installed').resolve())",
                    "from retailintel.evaluation import write_evaluation",
                    "from retailintel.dashboard import write_dashboard",
                    "write_evaluation('evaluation.json', order_count=30)",
                    "write_dashboard('dashboard.html')",
                ]
            ),
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads((tmp_path / "evaluation.json").read_text())
    assert len(report["evaluation"]) == 48
    assert report["source"]["kind"] == "synthetic"
    assert "Inventory decisions" in (tmp_path / "dashboard.html").read_text()
