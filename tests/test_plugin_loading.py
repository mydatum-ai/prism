import sys
from pathlib import Path

from prism_compiler.plugins import configured_domain_packs, load_object, load_semantic_analyzer
from pytest import MonkeyPatch


def test_phase6_loads_object_by_import_path() -> None:
    loaded = load_object("prism_compiler.providers.MockProvider")

    assert isinstance(loaded, type)
    assert loaded.__name__ == "MockProvider"


def test_phase6_loads_semantic_analyzer_from_env(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    plugin_file = tmp_path / "fake_plugin.py"
    plugin_file.write_text(
        "\n".join(
            [
                "from prism_compiler.enterprise import SemanticAnalysis",
                "class FakeAnalyzer:",
                "    def analyze(self, text):",
                "        return SemanticAnalysis()",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("fake_plugin", None)
    monkeypatch.setenv("PRISM_SEMANTIC_ANALYZER", "fake_plugin.FakeAnalyzer")

    analyzer = load_semantic_analyzer()

    assert analyzer is not None
    assert analyzer.analyze("hello").entities == []


def test_phase6_reads_domain_pack_config(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PRISM_DOMAIN_PACKS", "pulse, logsentry")

    assert configured_domain_packs() == ["pulse", "logsentry"]
