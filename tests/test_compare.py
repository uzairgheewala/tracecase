from __future__ import annotations

from pathlib import Path

from tracecase_bundle import BundleReader
from tracecase_compare import ComparisonDimension, SemanticComparisonEngine
from tracecase_graph import GraphAssembler


def _load(name: str):
    case = BundleReader(Path("fixtures/bundles") / name).load_case()
    graph = GraphAssembler().assemble(case.evidence.execution)
    return case, graph


def test_context_comparison_finds_first_semantic_divergence_at_consumer() -> None:
    baseline_case, baseline_graph = _load("context-continuity-baseline.tracecase")
    candidate_case, candidate_graph = _load("context-continuity-failure.tracecase")
    comparison = SemanticComparisonEngine().compare(baseline_case, baseline_graph, candidate_case, candidate_graph)
    assert comparison.summary.aligned_nodes == 4
    assert comparison.summary.first_meaningful_divergence_ref
    first = next(item for item in comparison.divergences if item.divergence_id == comparison.first_meaningful_divergence_ref)
    assert first.dimension is ComparisonDimension.CONTEXT
    assert first.classification == "context.changed"
    assert first.candidate_refs == ("node.synthetic.role.consume",)


def test_duplicate_effect_comparison_aligns_primary_attempt_and_marks_retry_extra() -> None:
    baseline_case, baseline_graph = _load("context-continuity-baseline.tracecase")
    candidate_case, candidate_graph = _load("duplicate-effect-failure.tracecase")
    comparison = SemanticComparisonEngine().compare(baseline_case, baseline_graph, candidate_case, candidate_graph)
    assert comparison.summary.aligned_nodes == 4
    assert comparison.summary.candidate_only_nodes == 1
    assert comparison.summary.ambiguous_alignments == 0
    classifications = {item.classification for item in comparison.divergences}
    assert "structure.additional-operation" in classifications
    assert "effect.durable-count-changed" in classifications


def test_regenerated_trace_and_workflow_ids_are_treated_as_noise() -> None:
    baseline_case, baseline_graph = _load("context-continuity-baseline.tracecase")
    candidate_case, candidate_graph = _load("context-continuity-baseline.tracecase")
    changed_nodes = tuple(
        node.model_copy(
            update={
                "identities": node.identities.model_copy(
                    update={"trace_id": "f" * 32, "workflow_id": "workflow-regenerated"}
                )
            }
        )
        for node in candidate_case.evidence.execution.nodes
    )
    candidate_case = candidate_case.model_copy(
        update={
            "evidence": candidate_case.evidence.model_copy(
                update={"execution": candidate_case.evidence.execution.model_copy(update={"nodes": changed_nodes})}
            )
        }
    )
    candidate_graph = GraphAssembler().assemble(candidate_case.evidence.execution)
    comparison = SemanticComparisonEngine().compare(baseline_case, baseline_graph, candidate_case, candidate_graph)
    assert not any(item.dimension is ComparisonDimension.IDENTITY for item in comparison.divergences)
