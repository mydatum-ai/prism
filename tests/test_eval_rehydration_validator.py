from prism_evaluation import run_evaluation


def test_phase5_validates_rehydration_accuracy() -> None:
    report = run_evaluation("datasets/synthetic_pii")

    assert report.metrics.rehydration_accuracy == 1.0
