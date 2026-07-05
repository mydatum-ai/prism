from pathlib import Path


def test_phase6_runtime_code_does_not_import_enterprise_repo() -> None:
    runtime_roots = [Path("apps"), Path("packages")]
    offenders: list[Path] = []
    for root in runtime_roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "prism_enterprise" in text or "prism-enterprise" in text:
                offenders.append(path)

    assert offenders == []
