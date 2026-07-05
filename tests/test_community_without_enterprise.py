from prism_compiler.plugins import configured_domain_packs, load_semantic_analyzer
from pytest import MonkeyPatch


def test_phase6_community_mode_runs_without_enterprise(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("PRISM_SEMANTIC_ANALYZER", raising=False)
    monkeypatch.delenv("PRISM_DOMAIN_PACKS", raising=False)

    assert load_semantic_analyzer() is None
    assert configured_domain_packs() == []
