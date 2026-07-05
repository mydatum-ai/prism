import json
from pathlib import Path

from prism_evaluation import run_evaluation, write_reports


def test_phase5_writes_json_and_markdown_reports(tmp_path: Path) -> None:
    report = run_evaluation("datasets/synthetic_pii")

    write_reports(report, tmp_path)

    report_json = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    report_md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert report_json["metrics"]["rehydration_accuracy"] == 1.0
    assert "identity_leakage_score" in report_md
