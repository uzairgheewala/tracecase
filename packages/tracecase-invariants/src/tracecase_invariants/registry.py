from __future__ import annotations

from .models import (
    EvidenceRequirement,
    EvaluatorKind,
    InsufficientEvidencePolicy,
    InvariantClass,
    InvariantDefinition,
    InvariantSeverity,
    ScopeKind,
    ScopeSelector,
)


def build_default_invariant_registry() -> tuple[InvariantDefinition, ...]:
    def definition(
        invariant_id: str,
        title: str,
        description: str,
        invariant_class: InvariantClass,
        evaluator_kind: EvaluatorKind,
        *,
        severity: InvariantSeverity = InvariantSeverity.HIGH,
        evidence: tuple[str, ...] = (),
        parameters: dict[str, object] | None = None,
        scope: ScopeKind = ScopeKind.CASE,
    ) -> InvariantDefinition:
        return InvariantDefinition(
            invariant_id=invariant_id,
            title=title,
            description=description,
            invariant_class=invariant_class,
            evaluator_kind=evaluator_kind,
            severity=severity,
            scope=ScopeSelector(kind=scope),
            parameters=parameters or {},
            required_evidence=tuple(EvidenceRequirement(kind=item) for item in evidence),
            insufficient_evidence_policy=InsufficientEvidencePolicy.INCONCLUSIVE,
            tags=(invariant_class.value,),
        )

    return (
        definition(
            "invariant.context.required-continuity.v1",
            "Required context continuity",
            "Required context remains present and semantically equivalent across its declared propagation path.",
            InvariantClass.CONTINUITY,
            EvaluatorKind.CONTEXT_REQUIRED_CONTINUITY,
            evidence=("nodes", "contexts"),
            scope=ScopeKind.CONTEXT_PATH,
        ),
        definition(
            "invariant.context.forbidden-propagation.v1",
            "Forbidden context propagation",
            "Context marked forbidden does not cross beyond its origin scope.",
            InvariantClass.PRIVACY,
            EvaluatorKind.CONTEXT_FORBIDDEN_PROPAGATION,
            evidence=("contexts",),
            scope=ScopeKind.CONTEXT_PATH,
        ),
        definition(
            "invariant.identity.execution-isolation.v1",
            "Execution identity isolation",
            "Independent tenant and workflow executions remain distinguishable.",
            InvariantClass.ISOLATION,
            EvaluatorKind.IDENTITY_EXECUTION_ISOLATION,
            evidence=("nodes",),
            scope=ScopeKind.IDENTITY_GROUP,
        ),
        definition(
            "invariant.identity.workflow-correlatable.v1",
            "Workflow correlatability",
            "A logical workflow remains correlatable across all participating execution boundaries.",
            InvariantClass.OBSERVABILITY,
            EvaluatorKind.IDENTITY_WORKFLOW_CORRELATABLE,
            evidence=("nodes",),
            scope=ScopeKind.IDENTITY_GROUP,
        ),
        definition(
            "invariant.effect.at-most-once.v1",
            "At-most-once durable effect",
            "A logical effect becomes durable no more than its declared maximum count.",
            InvariantClass.SAFETY,
            EvaluatorKind.EFFECT_AT_MOST_ONCE,
            evidence=("effects",),
            scope=ScopeKind.EFFECT_GROUP,
            parameters={"default_maximum": 1},
        ),
        definition(
            "invariant.effect.required-eventuality.v1",
            "Required effect eventuality",
            "Every declared required logical effect is eventually present in the execution evidence.",
            InvariantClass.LIVENESS,
            EvaluatorKind.EFFECT_REQUIRED_EVENTUALITY,
            evidence=("nodes",),
            scope=ScopeKind.EFFECT_GROUP,
        ),
        definition(
            "invariant.ordering.read-after-visibility.v1",
            "Read after visibility",
            "A dependent read begins only after the producing transaction or write becomes visible.",
            InvariantClass.ORDERING,
            EvaluatorKind.ORDERING_READ_AFTER_VISIBILITY,
            evidence=("nodes",),
            scope=ScopeKind.RELATION,
        ),
        definition(
            "invariant.consistency.required-freshness.v1",
            "Required freshness",
            "State observations meet their declared freshness and cache validity requirements.",
            InvariantClass.SAFETY,
            EvaluatorKind.CONSISTENCY_REQUIRED_FRESHNESS,
            evidence=("nodes",),
        ),
        definition(
            "invariant.contract.schema-compatible.v1",
            "Schema compatibility",
            "Collaborating producer and consumer schema versions are compatible.",
            InvariantClass.COMPATIBILITY,
            EvaluatorKind.CONTRACT_SCHEMA_COMPATIBLE,
            evidence=("nodes",),
        ),
        definition(
            "invariant.resource.capacity-bounded.v1",
            "Resource capacity bound",
            "The execution does not exceed a declared resource capacity bound.",
            InvariantClass.RESOURCE,
            EvaluatorKind.RESOURCE_CAPACITY_BOUNDED,
            evidence=("nodes",),
        ),
        definition(
            "invariant.performance.work-amplification.v1",
            "Work amplification bound",
            "Semantically equivalent work remains within the configured amplification limit.",
            InvariantClass.RESOURCE,
            EvaluatorKind.PERFORMANCE_WORK_AMPLIFICATION,
            evidence=("nodes",),
            parameters={"default_maximum": 1},
        ),
        definition(
            "invariant.observability.required-linkage.v1",
            "Required causal linkage",
            "Expected causal boundaries retain source-backed execution linkage.",
            InvariantClass.OBSERVABILITY,
            EvaluatorKind.OBSERVABILITY_REQUIRED_LINKAGE,
            evidence=("nodes",),
            scope=ScopeKind.RELATION,
        ),
        definition(
            "invariant.privacy.prohibited-capture.v1",
            "Prohibited sensitive capture",
            "Credentials and explicitly prohibited sensitive values are absent from collected evidence.",
            InvariantClass.PRIVACY,
            EvaluatorKind.PRIVACY_PROHIBITED_CAPTURE,
            severity=InvariantSeverity.CRITICAL,
            evidence=("observations",),
        ),
    )


class InvariantRegistry:
    def __init__(self, definitions: tuple[InvariantDefinition, ...] | None = None) -> None:
        self.definitions = definitions or build_default_invariant_registry()
        self._by_id = {item.invariant_id: item for item in self.definitions}
        if len(self._by_id) != len(self.definitions):
            raise ValueError("invariant IDs must be unique")

    def get(self, invariant_id: str) -> InvariantDefinition:
        try:
            return self._by_id[invariant_id]
        except KeyError as exc:
            raise KeyError(f"unknown invariant: {invariant_id}") from exc

    def select(self, invariant_ids: tuple[str, ...] | None = None) -> tuple[InvariantDefinition, ...]:
        if invariant_ids is None:
            return self.definitions
        return tuple(self.get(item) for item in invariant_ids)
