from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import Field, JsonValue, model_validator

from tracecase_model import (
    BoundaryKind,
    ComponentKind,
    DerivationKind,
    EffectKind,
    NodeKind,
    PropagationContract,
    RelationKind,
    SensitivityLabel,
    TracecaseModel,
)
from tracecase_model.types import CanonicalId, Namespace


class UniverseAxis(StrEnum):
    EXECUTION_TOPOLOGY = "execution_topology"
    BOUNDARY_PROPAGATION = "boundary_propagation"
    STATE_EFFECTS = "state_effects"
    TIME_CONCURRENCY = "time_concurrency"
    FAILURE_RECOVERY = "failure_recovery"
    CONTRACT_EVOLUTION = "contract_evolution"
    RESOURCES_PERFORMANCE = "resources_performance"
    ISOLATION_PRIVACY = "isolation_privacy"
    DEPLOYMENT_CONFIGURATION = "deployment_configuration"
    OBSERVABILITY_EVIDENCE = "observability_evidence"


class ScenarioFamilyClass(StrEnum):
    SAFETY = "safety"
    LIVENESS = "liveness"
    CONTINUITY = "continuity"
    ISOLATION = "isolation"
    IDENTITY = "identity"
    EFFECT = "effect"
    ORDERING = "ordering"
    CONSISTENCY = "consistency"
    RECOVERY = "recovery"
    TIMEOUT = "timeout"
    CONTRACT = "contract"
    DEPLOYMENT = "deployment"
    RESOURCE = "resource"
    PERFORMANCE = "performance"
    OBSERVABILITY = "observability"
    PRIVACY = "privacy"


class TopologyMotifKind(StrEnum):
    SYNCHRONOUS_CHAIN = "synchronous_chain"
    ASYNC_HANDOFF = "async_handoff"
    TRANSACTIONAL_ASYNC = "transactional_async"
    FAN_OUT = "fan_out"
    FAN_IN = "fan_in"
    PIPELINE = "pipeline"
    WORKFLOW_DAG = "workflow_dag"
    PRODUCER_CONSUMER = "producer_consumer"
    SAGA = "saga"
    BATCH = "batch"


class FaultOperatorClass(StrEnum):
    SEMANTIC = "semantic"
    OBSERVABILITY = "observability"


class FaultOperatorKind(StrEnum):
    DROP_CONTEXT_FIELD = "drop_context_field"
    MUTATE_CONTEXT_FIELD = "mutate_context_field"
    COPY_CONTEXT_FROM_OTHER_SCOPE = "copy_context_from_other_scope"
    BREAK_TRACE_LINK = "break_trace_link"
    COLLAPSE_EXECUTION_IDENTITY = "collapse_execution_identity"
    DUPLICATE_EFFECT = "duplicate_effect"
    OMIT_EFFECT = "omit_effect"
    FAIL_AFTER_EFFECT = "fail_after_effect"
    DELAY_OPERATION = "delay_operation"
    REORDER_OPERATIONS = "reorder_operations"
    DUPLICATE_DELIVERY = "duplicate_delivery"
    DROP_OBSERVATION = "drop_observation"
    CLOCK_SKEW = "clock_skew"
    INJECT_CONTRADICTORY_OBSERVATION = "inject_contradictory_observation"
    SCHEMA_VERSION_SKEW = "schema_version_skew"
    CAPTURE_PROHIBITED_FIELD = "capture_prohibited_field"
    EXHAUST_RESOURCE = "exhaust_resource"
    AMPLIFY_OPERATION = "amplify_operation"


class FaultTargetKind(StrEnum):
    ROLE = "role"
    EDGE = "edge"
    CONTEXT = "context"
    EFFECT = "effect"
    OBSERVATION = "observation"
    RESOURCE = "resource"
    SYSTEM = "system"


class ConstraintOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    IN = "in"
    NOT_IN = "not_in"
    REQUIRES = "requires"
    EXCLUDES = "excludes"


class InvariantExpectedStatus(StrEnum):
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    INCONCLUSIVE = "inconclusive"
    CONTRADICTED = "contradicted"
    NOT_APPLICABLE = "not_applicable"


class ObservabilityProfile(StrEnum):
    COMPLETE = "complete"
    SOURCE_ONLY = "source_only"
    DESTINATION_ONLY = "destination_only"
    MISSING_BOUNDARY = "missing_boundary"
    BROKEN_TRACE = "broken_trace"
    CLOCK_SKEWED = "clock_skewed"
    CONTRADICTORY = "contradictory"
    REDACTED = "redacted"


class EnumParameterDomain(TracecaseModel):
    kind: Literal["enum"] = "enum"
    parameter: str
    values: tuple[JsonValue, ...]
    default: JsonValue | None = None

    @model_validator(mode="after")
    def default_must_be_allowed(self) -> "EnumParameterDomain":
        if not self.values:
            raise ValueError("enum parameter domain must contain at least one value")
        if self.default is not None and self.default not in self.values:
            raise ValueError(f"default for {self.parameter} must be one of values")
        return self


class IntegerRangeParameterDomain(TracecaseModel):
    kind: Literal["integer_range"] = "integer_range"
    parameter: str
    minimum: int
    maximum: int
    step: int = Field(default=1, gt=0)
    default: int | None = None

    @model_validator(mode="after")
    def bounds_must_be_valid(self) -> "IntegerRangeParameterDomain":
        if self.maximum < self.minimum:
            raise ValueError("maximum cannot be lower than minimum")
        if self.default is not None and self.default not in self.values():
            raise ValueError(f"default for {self.parameter} is outside the range")
        return self

    def values(self) -> tuple[int, ...]:
        return tuple(range(self.minimum, self.maximum + 1, self.step))


class BooleanParameterDomain(TracecaseModel):
    kind: Literal["boolean"] = "boolean"
    parameter: str
    default: bool = False


ParameterDomain = Annotated[
    Union[EnumParameterDomain, IntegerRangeParameterDomain, BooleanParameterDomain],
    Field(discriminator="kind"),
]


class TopologyRole(TracecaseModel):
    role_id: CanonicalId
    component_kind: ComponentKind
    node_kind: NodeKind
    operation: str
    stage: int = Field(ge=0)
    component_role: str | None = None
    default_status: str = "ok"
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class TopologyEdge(TracecaseModel):
    edge_id: CanonicalId
    source_role_ref: CanonicalId
    target_role_ref: CanonicalId
    relation_kind: RelationKind
    boundary_kind: BoundaryKind
    boundary_name: str | None = None
    derivation: DerivationKind = DerivationKind.EXPLICIT
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class ResourceTemplate(TracecaseModel):
    resource_id: CanonicalId
    kind: str
    name: str
    owner_role_ref: CanonicalId | None = None
    sensitivity: set[SensitivityLabel] = Field(default_factory=set)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class ContextContractSpec(TracecaseModel):
    contract_id: CanonicalId
    namespace: str
    field_name: str
    value: JsonValue
    propagation_contract: PropagationContract
    source_role_ref: CanonicalId
    required_role_refs: tuple[CanonicalId, ...] = ()
    sensitivity: set[SensitivityLabel] = Field(default_factory=set)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}.{self.field_name}"


class EffectContractSpec(TracecaseModel):
    contract_id: CanonicalId
    effect_kind: EffectKind
    logical_effect_key: str
    producer_role_ref: CanonicalId
    target_resource_ref: CanonicalId | None = None
    operation: str
    required: bool = True
    maximum_durable_count: int | None = Field(default=1, ge=0)
    idempotency_key: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class TopologyTemplate(TracecaseModel):
    topology_id: CanonicalId
    motif: TopologyMotifKind
    roles: tuple[TopologyRole, ...]
    edges: tuple[TopologyEdge, ...]
    resources: tuple[ResourceTemplate, ...] = ()
    contexts: tuple[ContextContractSpec, ...] = ()
    effects: tuple[EffectContractSpec, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def references_must_resolve(self) -> "TopologyTemplate":
        role_ids = {role.role_id for role in self.roles}
        if len(role_ids) != len(self.roles):
            raise ValueError("topology role IDs must be unique")
        edge_ids = {edge.edge_id for edge in self.edges}
        if len(edge_ids) != len(self.edges):
            raise ValueError("topology edge IDs must be unique")
        resource_ids = {resource.resource_id for resource in self.resources}
        if len(resource_ids) != len(self.resources):
            raise ValueError("topology resource IDs must be unique")
        for edge in self.edges:
            if edge.source_role_ref not in role_ids or edge.target_role_ref not in role_ids:
                raise ValueError(f"edge {edge.edge_id} references unknown role")
        for resource in self.resources:
            if resource.owner_role_ref and resource.owner_role_ref not in role_ids:
                raise ValueError(f"resource {resource.resource_id} references unknown owner role")
        for context in self.contexts:
            refs = {context.source_role_ref, *context.required_role_refs}
            missing = refs - role_ids
            if missing:
                raise ValueError(f"context {context.contract_id} references unknown roles: {sorted(missing)}")
        for effect in self.effects:
            if effect.producer_role_ref not in role_ids:
                raise ValueError(f"effect {effect.contract_id} references unknown producer role")
            if effect.target_resource_ref and effect.target_resource_ref not in resource_ids:
                raise ValueError(f"effect {effect.contract_id} references unknown resource")
        return self


class AdmissibilityConstraint(TracecaseModel):
    constraint_id: CanonicalId
    left_parameter: str
    operator: ConstraintOperator
    right_value: JsonValue | None = None
    right_values: tuple[JsonValue, ...] = ()
    right_parameter: str | None = None
    message: str | None = None


class FaultOperatorDefinition(TracecaseModel):
    operator_id: CanonicalId
    kind: FaultOperatorKind
    operator_class: FaultOperatorClass
    title: str
    description: str
    target_kinds: tuple[FaultTargetKind, ...]
    parameter_domains: tuple[ParameterDomain, ...] = ()
    universe_axes: tuple[UniverseAxis, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class FaultApplication(TracecaseModel):
    application_id: CanonicalId
    operator_ref: CanonicalId
    target_kind: FaultTargetKind
    target_ref: CanonicalId | None = None
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class ExpectedInvariant(TracecaseModel):
    invariant_ref: CanonicalId
    expected_status: InvariantExpectedStatus
    scope_ref: CanonicalId | None = None
    rationale: str | None = None


class MinimizationStrategy(TracecaseModel):
    preserve_role_refs: tuple[CanonicalId, ...] = ()
    preserve_context_refs: tuple[CanonicalId, ...] = ()
    preserve_effect_refs: tuple[CanonicalId, ...] = ()
    dimensions: tuple[str, ...] = (
        "unrelated_roles",
        "retries",
        "context_fields",
        "observations",
        "fault_schedule",
    )


class ScenarioFamily(TracecaseModel):
    family_id: CanonicalId
    family_version: str = "1.0.0"
    title: str
    description: str
    family_class: ScenarioFamilyClass
    universe_axes: tuple[UniverseAxis, ...]
    topology_ref: CanonicalId
    parameter_domains: tuple[ParameterDomain, ...] = ()
    admissibility_constraints: tuple[AdmissibilityConstraint, ...] = ()
    allowed_fault_operator_refs: tuple[CanonicalId, ...] = ()
    invariant_refs: tuple[CanonicalId, ...] = ()
    observability_profiles: tuple[ObservabilityProfile, ...] = (ObservabilityProfile.COMPLETE,)
    minimization: MinimizationStrategy = Field(default_factory=MinimizationStrategy)
    parent_family_ref: CanonicalId | None = None
    tags: tuple[str, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class ScenarioDefinition(TracecaseModel):
    scenario_id: CanonicalId
    title: str
    family_ref: CanonicalId
    parameter_bindings: dict[str, JsonValue] = Field(default_factory=dict)
    faults: tuple[FaultApplication, ...] = ()
    observability_profile: ObservabilityProfile = ObservabilityProfile.COMPLETE
    expected_invariants: tuple[ExpectedInvariant, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class ScenarioInstance(TracecaseModel):
    instance_id: CanonicalId
    scenario_ref: CanonicalId
    family_ref: CanonicalId
    registry_version: str
    seed: int = Field(ge=0)
    resolved_parameters: dict[str, JsonValue]
    topology: TopologyTemplate
    faults: tuple[FaultApplication, ...]
    observability_profile: ObservabilityProfile
    expected_invariants: tuple[ExpectedInvariant, ...]
    coverage_points: tuple[str, ...] = ()
    instance_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class ScenarioRegistry(TracecaseModel):
    registry_id: CanonicalId = "registry.tracecase-core"
    registry_version: str = "1.0.0"
    semantic_universe_version: str = "1.0.0"
    topologies: tuple[TopologyTemplate, ...]
    fault_operators: tuple[FaultOperatorDefinition, ...]
    families: tuple[ScenarioFamily, ...]
    invariant_catalog: dict[CanonicalId, str] = Field(default_factory=dict)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def registry_references_must_resolve(self) -> "ScenarioRegistry":
        topology_ids = {item.topology_id for item in self.topologies}
        fault_ids = {item.operator_id for item in self.fault_operators}
        family_ids = {item.family_id for item in self.families}
        for family in self.families:
            if family.topology_ref not in topology_ids:
                raise ValueError(f"family {family.family_id} references unknown topology")
            missing_faults = set(family.allowed_fault_operator_refs) - fault_ids
            if missing_faults:
                raise ValueError(f"family {family.family_id} references unknown faults: {sorted(missing_faults)}")
            missing_invariants = set(family.invariant_refs) - set(self.invariant_catalog)
            if missing_invariants:
                raise ValueError(
                    f"family {family.family_id} references unknown invariants: {sorted(missing_invariants)}"
                )
            if family.parent_family_ref and family.parent_family_ref not in family_ids:
                raise ValueError(f"family {family.family_id} references unknown parent")
        return self

    def family(self, family_id: str) -> ScenarioFamily:
        for family in self.families:
            if family.family_id == family_id:
                return family
        raise KeyError(family_id)

    def topology(self, topology_id: str) -> TopologyTemplate:
        for topology in self.topologies:
            if topology.topology_id == topology_id:
                return topology
        raise KeyError(topology_id)

    def fault_operator(self, operator_id: str) -> FaultOperatorDefinition:
        for operator in self.fault_operators:
            if operator.operator_id == operator_id:
                return operator
        raise KeyError(operator_id)
