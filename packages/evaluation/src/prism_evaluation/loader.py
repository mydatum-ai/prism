import json
from pathlib import Path

from prism_evaluation.models import EvaluationCase


def load_dataset(path: str | Path) -> list[EvaluationCase]:
    dataset_path = Path(path)
    cases_file = dataset_path / "cases.jsonl" if dataset_path.is_dir() else dataset_path
    cases: list[EvaluationCase] = []
    with cases_file.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            data = json.loads(stripped)
            data.setdefault("session_id", f"case_{line_number}")
            cases.append(EvaluationCase.model_validate(data))
    return cases
