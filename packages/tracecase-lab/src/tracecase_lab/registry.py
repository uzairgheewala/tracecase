from __future__ import annotations

from .models import LabBinding, LabMode


_BINDINGS = (
    LabBinding(
        binding_id="lab.transcript-import.v1",
        family_ref="workflow.distributed-operation.v1",
        title="Transcript import and audit recomputation",
        description="Browser upload through API transaction, broker, worker, mock SIS/OCR, projection, audit, and notification.",
        supported_faults=(
            "fault.context.drop.v1",
            "fault.ordering.publish-before-commit.v1",
            "fault.effect.duplicate.v1",
            "fault.consistency.stale-cache.v1",
            "fault.contract.schema-skew.v1",
            "fault.observability.break-link.v1",
            "fault.privacy.capture-secret.v1",
            "fault.external.timeout-after-effect.v1",
        ),
        topology_roles=("browser", "api", "transaction", "publisher", "worker", "external", "projection", "audit", "notification"),
        invariant_refs=(
            "context.required_continuity.v1",
            "effect.at_most_once.v1",
            "ordering.read_after_visibility.v1",
            "contract.schema_compatible.v1",
            "observability.required_linkage.v1",
            "privacy.prohibited_capture.v1",
        ),
        runtime_modes=(LabMode.IN_PROCESS, LabMode.DISTRIBUTED),
    ),
)


def lab_bindings() -> tuple[LabBinding, ...]:
    return _BINDINGS


def get_binding(binding_id: str) -> LabBinding:
    for binding in _BINDINGS:
        if binding.binding_id == binding_id:
            return binding
    raise KeyError(binding_id)
