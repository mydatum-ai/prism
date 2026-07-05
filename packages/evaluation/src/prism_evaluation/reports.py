import json
from pathlib import Path

from prism_evaluation.models import EvaluationReport


def write_reports(report: EvaluationReport, output_dir: str | Path) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (output_path / "report.md").write_text(markdown_report(report), encoding="utf-8")


def markdown_report(report: EvaluationReport) -> str:
    metrics = report.metrics
    return "\n".join(
        [
            f"# Prism Evaluation Report: {report.dataset}",
            "",
            f"- cases: {report.case_count}",
            f"- identity_leakage_score: {metrics.identity_leakage_score:.4f}",
            f"- rehydration_accuracy: {metrics.rehydration_accuracy:.4f}",
            f"- transformation_correctness: {metrics.transformation_correctness:.4f}",
            f"- quality_delta: {metrics.quality_delta:.4f}",
            f"- latency_overhead: {metrics.latency_overhead:.6f}",
            "",
        ]
    )
