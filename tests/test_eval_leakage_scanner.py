from prism_evaluation import run_evaluation


def test_phase5_scans_identity_leakage() -> None:
    report = run_evaluation("datasets/synthetic_pii")

    assert report.metrics.identity_leakage_score == 0.0
    assert all(not result.leaked_values for result in report.cases)
