from __future__ import annotations

from .models import AnalyzerDefinition, FindingCategory


def build_default_analyzer_registry() -> tuple[AnalyzerDefinition, ...]:
    return (
        AnalyzerDefinition(
            analyzer_id="analyzer.context-continuity.v1",
            title="Context continuity analyzer",
            category=FindingCategory.CONTEXT,
            description="Interprets required, forbidden, mutated, and contaminated context paths.",
            invariant_refs=(
                "invariant.context.required-continuity.v1",
                "invariant.context.forbidden-propagation.v1",
            ),
        ),
        AnalyzerDefinition(
            analyzer_id="analyzer.identity-integrity.v1",
            title="Identity integrity analyzer",
            category=FindingCategory.IDENTITY,
            description="Detects execution collapse, fragmentation, and workflow correlation failures.",
            invariant_refs=(
                "invariant.identity.execution-isolation.v1",
                "invariant.identity.workflow-correlatable.v1",
            ),
        ),
        AnalyzerDefinition(
            analyzer_id="analyzer.retry-effect.v1",
            title="Retry and effect analyzer",
            category=FindingCategory.RETRY_EFFECT,
            description="Detects duplicate, omitted, ambiguous, and repeated durable logical effects.",
            invariant_refs=(
                "invariant.effect.at-most-once.v1",
                "invariant.effect.required-eventuality.v1",
            ),
        ),
        AnalyzerDefinition(
            analyzer_id="analyzer.transaction-ordering.v1",
            title="Transaction ordering analyzer",
            category=FindingCategory.TRANSACTION_ORDERING,
            description="Detects read-before-visibility and causally contradictory transaction timing.",
            invariant_refs=("invariant.ordering.read-after-visibility.v1",),
        ),
        AnalyzerDefinition(
            analyzer_id="analyzer.observability-integrity.v1",
            title="Observability integrity analyzer",
            category=FindingCategory.OBSERVABILITY,
            description="Detects missing source-backed links, disconnected fragments, contradictions, and timestamp conflicts.",
            invariant_refs=("invariant.observability.required-linkage.v1",),
        ),
        AnalyzerDefinition(
            analyzer_id="analyzer.resource-amplification.v1",
            title="Resource and amplification analyzer",
            category=FindingCategory.RESOURCE_PERFORMANCE,
            description="Detects resource exhaustion and prohibited semantic work amplification.",
            invariant_refs=(
                "invariant.resource.capacity-bounded.v1",
                "invariant.performance.work-amplification.v1",
                "invariant.consistency.required-freshness.v1",
            ),
        ),
        AnalyzerDefinition(
            analyzer_id="analyzer.contract-privacy.v1",
            title="Contract and privacy analyzer",
            category=FindingCategory.CONTRACT,
            description="Detects schema incompatibility and prohibited sensitive evidence capture.",
            invariant_refs=(
                "invariant.contract.schema-compatible.v1",
                "invariant.privacy.prohibited-capture.v1",
            ),
        ),
    )
