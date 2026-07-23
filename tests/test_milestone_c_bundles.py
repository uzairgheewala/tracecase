from pathlib import Path

from tracecase_bundle import BundleProfile, BundleReader
from tracecase_compare import SemanticComparison
from tracecase_analyzers import AnalysisReport

ROOT = Path(__file__).resolve().parents[1]
BUNDLES = ROOT / "fixtures" / "bundles"


def test_analyzed_bundles_are_valid_and_reconstruct_reports() -> None:
    stems = (
        "context-analysis-baseline",
        "context-analysis-failure",
        "duplicate-effect-analysis",
        "causal-gap-analysis",
    )
    for stem in stems:
        reader = BundleReader(BUNDLES / f"{stem}.tracecase")
        assert reader.verify().valid
        assert BundleProfile.ANALYZED in reader.manifest.profiles
        report = AnalysisReport.model_validate(reader.read_json("analysis/analysis_report.json"))
        assert report.case_id == reader.manifest.case_id
        assert report.invariant_report.results
        assert reader.has_artifact("analysis/findings.jsonl")


def test_context_failure_has_violation_while_baseline_is_satisfied() -> None:
    baseline = AnalysisReport.model_validate(
        BundleReader(BUNDLES / "context-analysis-baseline.tracecase").read_json("analysis/analysis_report.json")
    )
    failure = AnalysisReport.model_validate(
        BundleReader(BUNDLES / "context-analysis-failure.tracecase").read_json("analysis/analysis_report.json")
    )
    baseline_result = next(item for item in baseline.invariant_report.results if item.invariant_ref == "invariant.context.required-continuity.v1")
    failure_result = next(item for item in failure.invariant_report.results if item.invariant_ref == "invariant.context.required-continuity.v1")
    assert baseline_result.status.value == "satisfied"
    assert failure_result.status.value == "violated"
    assert failure_result.counterexample_refs


def test_comparison_bundle_contains_semantic_alignment_and_first_divergence() -> None:
    reader = BundleReader(BUNDLES / "semantic-context-comparison.tracecase")
    assert reader.verify().valid
    assert BundleProfile.COMPARISON in reader.manifest.profiles
    comparison = SemanticComparison.model_validate(reader.read_json("comparison/semantic_comparison.json"))
    assert comparison.summary.aligned_nodes >= 4
    assert comparison.first_meaningful_divergence_ref
    first = next(item for item in comparison.divergences if item.divergence_id == comparison.first_meaningful_divergence_ref)
    assert first.dimension.value == "context"
    assert first.consequential


def test_archived_milestone_c_bundles_verify() -> None:
    for stem in (
        "context-analysis-baseline",
        "context-analysis-failure",
        "duplicate-effect-analysis",
        "causal-gap-analysis",
        "semantic-context-comparison",
    ):
        reader, temporary = BundleReader.open(BUNDLES / f"{stem}.tracecase.zip")
        try:
            assert reader.verify().valid
        finally:
            if temporary:
                temporary.cleanup()
