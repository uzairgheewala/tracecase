from __future__ import annotations

from pathlib import Path

from tracecase_analyzers import AnalyzerEngine
from tracecase_bundle import BundleReader
from tracecase_graph import GraphAssembler


def _analyze(name: str):
    case = BundleReader(Path("fixtures/bundles") / name).load_case()
    graph = GraphAssembler().assemble(case.evidence.execution)
    return AnalyzerEngine().analyze(case, graph)


def test_baseline_has_no_open_findings() -> None:
    report = _analyze("context-continuity-baseline.tracecase")
    assert report.findings == ()


def test_context_finding_links_invariant_evidence_and_inspection_point() -> None:
    report = _analyze("context-continuity-failure.tracecase")
    finding = next(item for item in report.findings if item.classification == "context.required-continuity")
    assert finding.related_invariant_result_refs
    assert finding.node_refs
    assert finding.context_refs
    assert finding.recommended_inspection_points


def test_retry_analyzer_emits_specific_duplicate_effect_finding() -> None:
    report = _analyze("duplicate-effect-failure.tracecase")
    finding = next(item for item in report.findings if item.classification == "retry.duplicate-durable-effect")
    assert finding.effect_refs
    assert finding.attributes["durable_count"] == 2
    assert finding.attributes["attempts"] == [1, 2]


def test_causal_gap_finding_distinguishes_reconstruction_from_recorded_edge() -> None:
    report = _analyze("causal-gap-observed.tracecase")
    classifications = {item.classification for item in report.findings}
    assert "observability.required-linkage" in classifications
    assert "observability.link-reconstructed" in classifications
