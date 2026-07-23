from .models import PathforgeBinding, PathforgeWorkflowKind

def pathforge_bindings():
    return (
        PathforgeBinding(binding_id="pathforge.requirement-audit.v1",workflow_kind=PathforgeWorkflowKind.REQUIREMENT_AUDIT,title="Requirement audit execution",generic_invariants=("context.required_continuity.v1","effect.required_eventuality.v1","contract.schema_compatible.v1","observability.required_linkage.v1"),domain_event_types=("audit.requested","audit.candidates.generated","audit.solver.completed","audit.explanation.generated","audit.persisted")),
        PathforgeBinding(binding_id="pathforge.integration-reconciliation.v1",workflow_kind=PathforgeWorkflowKind.INTEGRATION_RECONCILIATION,title="Integration reconciliation execution",generic_invariants=("context.required_continuity.v1","effect.at_most_once.v1","consistency.required_freshness.v1"),domain_event_types=("source.observed","record.normalized","projection.updated","reconciliation.completed")),
    )

def get_binding(binding_id):
    return next(item for item in pathforge_bindings() if item.binding_id==binding_id)
