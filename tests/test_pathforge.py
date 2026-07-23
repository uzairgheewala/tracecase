from tracecase_analyzers import AnalyzerEngine
from tracecase_graph import GraphAssembler
from tracecase_pathforge import PathforgeTraceBridge, pathforge_bindings

def test_pathforge_integration_remains_namespaced_and_analyzable():
    bridge=PathforgeTraceBridge(); case=bridge.demo_case(seed=51)
    assert "pathforge.academic" in case.extensions
    assert all("pathforge.academic" in node.extensions for node in case.evidence.execution.nodes)
    graph=GraphAssembler().assemble(case.evidence.execution); analysis=AnalyzerEngine().analyze(case,graph)
    assert len(analysis.findings)==0

def test_pathforge_context_loss_uses_generic_comparison():
    bridge=PathforgeTraceBridge(); baseline,candidate,comparison=bridge.compare_demo(seed=52,fault="tenant-loss")
    assert comparison.summary.aligned_nodes==5
    first=next(d for d in comparison.divergences if d.divergence_id==comparison.first_meaningful_divergence_ref)
    assert first.dimension.value in {"identity","context"}
    result=bridge.analyze(candidate)
    assert result.finding_count>0

def test_pathforge_registry():
    assert {item.binding_id for item in pathforge_bindings()}=={"pathforge.requirement-audit.v1","pathforge.integration-reconciliation.v1"}
