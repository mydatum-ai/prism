from prism_transformers import detect_entities


def test_phase1_detects_mvp_entities() -> None:
    detections = detect_entities("John Smith emailed john@email.com about INV-1001")

    assert [(item.entity_type, item.text) for item in detections] == [
        ("person", "John Smith"),
        ("email", "john@email.com"),
        ("invoice", "INV-1001"),
    ]
