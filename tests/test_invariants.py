from __future__ import annotations

from pathlib import Path

from tracecase_bundle import BundleReader
from tracecase_graph import GraphAssembler
from tracecase_invariants import InvariantRuntime, InvariantStatus


def _evaluate(name: str):
    case = BundleReader(Path("fixtures/bundles") / name).load_case()
    graph = GraphAssembler().assemble(case.evidence.execution)
    return InvariantRuntime().evaluate(case, graph)


def test_baseline_invariants_are_satisfied_or_not_applicable() -> None:
    report = _evaluate("context-continuity-baseline.tracecase")
    assert all(item.status in {InvariantStatus.SATISFIED, InvariantStatus.NOT_APPLICABLE} for item in report.results)


def test_context_drop_returns_evidence_linked_counterexample() -> None:
    report = _evaluate("context-continuity-failure.tracecase")
    result = next(item for item in report.results if item.invariant_ref == "invariant.context.required-continuity.v1")
    assert result.status is InvariantStatus.VIOLATED
    assert "node.synthetic.role.consume" in result.node_refs
    assert result.context_refs
    assert result.evaluation_trace


def test_duplicate_effect_violates_at_most_once_without_false_linkage_failure() -> None:
    report = _evaluate("duplicate-effect-failure.tracecase")
    statuses = {item.invariant_ref: item.status for item in report.results}
    assert statuses["invariant.effect.at-most-once.v1"] is InvariantStatus.VIOLATED
    assert statuses["invariant.observability.required-linkage.v1"] is InvariantStatus.SATISFIED


def test_observability_gap_is_distinct_from_ground_truth_context_failure() -> None:
    report = _evaluate("causal-gap-observed.tracecase")
    statuses = {item.invariant_ref: item.status for item in report.results}
    assert statuses["invariant.observability.required-linkage.v1"] is InvariantStatus.VIOLATED
    assert statuses["invariant.context.required-continuity.v1"] is InvariantStatus.SATISFIED
