from prism_compiler.enterprise import SemanticAnalysis, SemanticEntity, SemanticGraph


def test_phase6_enterprise_contract_models() -> None:
    analysis = SemanticAnalysis(
        entities=[
            SemanticEntity(
                text="Maria Santos",
                type="person",
                role="resident",
                sensitivity="medium",
                recommendation="tokenize",
                confidence=0.9,
            )
        ]
    )
    graph = SemanticGraph(nodes=["Maria Santos"], edges=[], hints=["tokenize resident"])

    assert analysis.entities[0].role == "resident"
    assert graph.hints == ["tokenize resident"]
