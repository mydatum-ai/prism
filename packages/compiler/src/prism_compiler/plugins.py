import importlib
import os
from typing import cast

from prism_compiler.enterprise import SemanticAnalyzer


def load_object(import_path: str) -> object:
    module_name, separator, object_name = import_path.rpartition(".")
    if not separator or not module_name or not object_name:
        raise ValueError(f"Invalid import path: {import_path}")
    module = importlib.import_module(module_name)
    return getattr(module, object_name)


def load_semantic_analyzer() -> SemanticAnalyzer | None:
    import_path = os.getenv("PRISM_SEMANTIC_ANALYZER")
    if not import_path:
        return None
    loaded = load_object(import_path)
    if not isinstance(loaded, type):
        raise TypeError(f"Import path does not reference a class: {import_path}")
    return cast(SemanticAnalyzer, loaded())


def configured_domain_packs() -> list[str]:
    raw = os.getenv("PRISM_DOMAIN_PACKS", "")
    return [value.strip() for value in raw.split(",") if value.strip()]
