from pathlib import Path

from prism_cli.main import main
from pytest import MonkeyPatch


def test_phase5_cli_eval_writes_reports(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "prism",
            "eval",
            "--dataset",
            "datasets/synthetic_pii",
            "--output",
            str(tmp_path),
        ],
    )

    assert main() == 0
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.md").exists()
