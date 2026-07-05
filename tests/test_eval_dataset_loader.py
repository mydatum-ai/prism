from prism_evaluation import load_dataset


def test_phase5_loads_jsonl_dataset() -> None:
    cases = load_dataset("datasets/synthetic_pii")

    assert [case.id for case in cases] == ["synthetic-1", "synthetic-2"]
    assert cases[0].session_id == "case_1"
