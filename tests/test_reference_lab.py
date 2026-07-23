from tracecase_lab import LabRunRequest, ReferenceLab, lab_bindings


def _violations(result):
    return {
        item.invariant_ref
        for item in result.analysis.invariant_report.results
        if item.status.value == "violated"
    }


def test_reference_lab_baseline_is_clean() -> None:
    result = ReferenceLab().run(LabRunRequest(seed=41))
    assert len(result.case.evidence.execution.nodes) == 10
    assert not _violations(result)
    assert not result.analysis.findings
    assert result.graph.report.source_relation_count >= 9


def test_reference_lab_generic_fault_bindings() -> None:
    lab = ReferenceLab()
    expectations = {
        "fault.context.drop.v1": "invariant.context.required-continuity.v1",
        "fault.effect.duplicate.v1": "invariant.effect.at-most-once.v1",
        "fault.ordering.publish-before-commit.v1": "invariant.ordering.read-after-visibility.v1",
        "fault.contract.schema-skew.v1": "invariant.contract.schema-compatible.v1",
        "fault.consistency.stale-cache.v1": "invariant.consistency.required-freshness.v1",
        "fault.privacy.capture-secret.v1": "invariant.privacy.prohibited-capture.v1",
    }
    for index, (fault, invariant) in enumerate(expectations.items(), start=1):
        result = lab.run(
            LabRunRequest(
                seed=50 + index,
                fault_operator_ref=fault,
                include_sensitive_payload=fault == "fault.privacy.capture-secret.v1",
            )
        )
        assert invariant in _violations(result)


def test_observability_fault_preserves_semantic_effects() -> None:
    baseline = ReferenceLab().run(LabRunRequest(seed=61))
    broken = ReferenceLab().run(
        LabRunRequest(seed=61, observability_fault_ref="fault.observability.break-link.v1")
    )
    assert len(baseline.case.evidence.execution.effects) == len(broken.case.evidence.execution.effects)
    assert "invariant.observability.required-linkage.v1" in _violations(broken)
    assert "invariant.context.required-continuity.v1" not in _violations(broken)


def test_live_lab_comparison_finds_context_divergence() -> None:
    result = ReferenceLab().compare(
        LabRunRequest(seed=62, fault_operator_ref="fault.context.drop.v1")
    )
    first = next(
        item
        for item in result.comparison.divergences
        if item.divergence_id == result.comparison.first_meaningful_divergence_ref
    )
    assert first.dimension.value in {"identity", "context"}
    assert first.temporal_rank_ms is not None


def test_registry_exposes_real_and_in_process_modes() -> None:
    binding = lab_bindings()[0]
    assert "fault.context.drop.v1" in binding.supported_faults
    assert {mode.value for mode in binding.runtime_modes} == {"in_process", "distributed"}
