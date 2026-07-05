from pathlib import Path
from time import perf_counter

from prism_compiler.schemas import RehydrateRequest, TransformRequest
from prism_rehydration import rehydrate
from prism_transformers import detect_entities, transform
from prism_vault_core import GLOBAL_VAULT

from prism_evaluation.loader import load_dataset
from prism_evaluation.models import EvaluationCaseResult, EvaluationMetrics, EvaluationReport


def run_evaluation(dataset_path: str | Path) -> EvaluationReport:
    GLOBAL_VAULT.clear()
    cases = load_dataset(dataset_path)
    results: list[EvaluationCaseResult] = []

    for case in cases:
        start = perf_counter()
        transform_response = transform(
            TransformRequest(
                tenant_id=case.tenant_id,
                app_id=case.app_id,
                session_id=case.session_id,
                text=case.input,
            )
        )
        rehydrate_response = rehydrate(
            RehydrateRequest(
                tenant_id=case.tenant_id,
                app_id=case.app_id,
                session_id=case.session_id,
                text=transform_response.transformed_text,
            )
        )
        latency = perf_counter() - start
        raw_values = [detection.text for detection in detect_entities(case.input)]
        leaked_values = [
            value for value in raw_values if value in transform_response.transformed_text
        ]
        results.append(
            EvaluationCaseResult(
                id=case.id,
                input=case.input,
                transformed=transform_response.transformed_text,
                rehydrated=rehydrate_response.text,
                leaked_values=leaked_values,
                latency_seconds=latency,
            )
        )

    return EvaluationReport(
        dataset=str(dataset_path),
        case_count=len(results),
        metrics=_metrics(results),
        cases=results,
    )


def _metrics(results: list[EvaluationCaseResult]) -> EvaluationMetrics:
    if not results:
        return EvaluationMetrics(
            identity_leakage_score=0.0,
            rehydration_accuracy=0.0,
            transformation_correctness=0.0,
            quality_delta=0.0,
            latency_overhead=0.0,
        )
    leakage_cases = sum(1 for result in results if result.leaked_values)
    rehydrated_cases = sum(1 for result in results if result.rehydrated == result.input)
    transformed_cases = sum(1 for result in results if result.transformed != result.input)
    latency = sum(result.latency_seconds for result in results) / len(results)
    return EvaluationMetrics(
        identity_leakage_score=leakage_cases / len(results),
        rehydration_accuracy=rehydrated_cases / len(results),
        transformation_correctness=transformed_cases / len(results),
        quality_delta=0.0,
        latency_overhead=latency,
    )
