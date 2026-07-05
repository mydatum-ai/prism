from typing import Protocol

from prism_evaluation.models import EvaluationReport
from prism_policy_runtime import Policy
from pydantic import BaseModel, Field


class SemanticEntity(BaseModel):
    text: str
    type: str
    role: str | None = None
    sensitivity: str | None = None
    recommendation: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class SemanticAnalysis(BaseModel):
    entities: list[SemanticEntity] = Field(default_factory=list)


class SemanticGraph(BaseModel):
    nodes: list[str] = Field(default_factory=list)
    edges: list[tuple[str, str, str]] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)


class SemanticAnalyzer(Protocol):
    def analyze(self, text: str) -> SemanticAnalysis:
        """Return semantic entity recommendations for text."""


class SemanticGraphBuilder(Protocol):
    def build(self, text: str) -> SemanticGraph:
        """Build a semantic graph for text."""


class TransformationOptimizer(Protocol):
    def recommend(self, metric_name: str, metric_value: float) -> list[str]:
        """Recommend transformation improvements from metrics."""


class DomainPack(Protocol):
    @property
    def name(self) -> str:
        """Domain pack name."""

    def policy(self) -> Policy:
        """Return the domain policy."""


class EnterpriseVault(Protocol):
    def put(self, key: str, value: str) -> None:
        """Store a protected enterprise value."""

    def get(self, key: str) -> str | None:
        """Return a protected enterprise value."""


class AdvancedEvaluator(Protocol):
    def evaluate(self, dataset_path: str) -> EvaluationReport:
        """Run an advanced enterprise evaluation."""
