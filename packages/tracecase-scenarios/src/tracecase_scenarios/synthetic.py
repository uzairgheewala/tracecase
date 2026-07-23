from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone

from pydantic import Field, JsonValue

from tracecase_model import (
    Boundary,
    CaseCategory,
    CaseEvidence,
    CaseSpecification,
    Component,
    ContextField,
    DerivationKind,
    Effect,
    EvidenceClassification,
    ExecutionCase,
    ExecutionIdentitySet,
    ExecutionModel,
    ExecutionNode,
    ExecutionRelation,
    NodeKind,
    Observation,
    ObservationKind,
    ProvenanceRef,
    RelationKind,
    Resource,
    SensitivityLabel,
    SourceDescriptor,
    StateFact,
    SystemModel,
    TimeObservation,
    TracecaseModel,
)
from tracecase_model.execution import EffectDurability

from .models import (
    ExpectedInvariant,
    FaultApplication,
    FaultOperatorClass,
    FaultOperatorKind,
    InvariantExpectedStatus,
    ObservabilityProfile,
    ScenarioInstance,
    ScenarioRegistry,
)


class SyntheticOracleOutcome(TracecaseModel):
    invariant_ref: str
    expected_status: InvariantExpectedStatus
    basis: str
    scope_ref: str | None = None


class SyntheticRunResult(TracecaseModel):
    scenario_instance: ScenarioInstance
    ground_truth_case: ExecutionCase
    observed_case: ExecutionCase
    oracle_outcomes: tuple[SyntheticOracleOutcome, ...]
    semantic_faults: tuple[FaultApplication, ...]
    observability_faults: tuple[FaultApplication, ...]
    coverage_points: tuple[str, ...]
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class SyntheticExecutionEngine:
    def __init__(self, registry: ScenarioRegistry) -> None:
        self.registry = registry

    def realize(
        self,
        instance: ScenarioInstance,
        *,
        base_time: datetime | None = None,
        title: str | None = None,
    ) -> SyntheticRunResult:
        if base_time is None:
            base_time = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
        if base_time.tzinfo is None:
            raise ValueError("base_time must be timezone-aware")
        family = self.registry.family(instance.family_ref)
        semantic_faults: list[FaultApplication] = []
        observability_faults: list[FaultApplication] = []
        for application in instance.faults:
            operator = self.registry.fault_operator(application.operator_ref)
            if operator.operator_class is FaultOperatorClass.SEMANTIC:
                semantic_faults.append(application)
            else:
                observability_faults.append(application)

        baseline = self._build_baseline_case(instance, base_time=base_time, title=title)
        ground_truth = baseline
        for application in semantic_faults:
            ground_truth = self._apply_semantic_fault(ground_truth, application)
        observed = ground_truth
        for application in observability_faults:
            observed = self._apply_observability_fault(observed, application)
        observed = self._apply_observability_profile(observed, instance.observability_profile)

        outcomes = self._oracle_outcomes(instance, bool(semantic_faults), bool(observability_faults))
        return SyntheticRunResult(
            scenario_instance=instance,
            ground_truth_case=ground_truth,
            observed_case=observed,
            oracle_outcomes=outcomes,
            semantic_faults=tuple(semantic_faults),
            observability_faults=tuple(observability_faults),
            coverage_points=tuple(
                sorted(
                    {
                        *instance.coverage_points,
                        *(f"semantic-fault:{item.operator_ref}" for item in semantic_faults),
                        *(f"observability-fault:{item.operator_ref}" for item in observability_faults),
                    }
                )
            ),
            attributes={
                "ground_truth_observations": len(ground_truth.evidence.execution.observations),
                "observed_observations": len(observed.evidence.execution.observations),
                "family_class": family.family_class.value,
            },
        )

    def _build_baseline_case(
        self,
        instance: ScenarioInstance,
        *,
        base_time: datetime,
        title: str | None,
    ) -> ExecutionCase:
        family = self.registry.family(instance.family_ref)
        topology = instance.topology
        component_by_role: dict[str, str] = {}
        component_by_group: dict[str, str] = {}
        components: list[Component] = []
        for role in topology.roles:
            group = role.component_role or role.role_id
            component_id = component_by_group.get(group)
            if component_id is None:
                component_id = f"component.synthetic.{_slug(group)}"
                component_by_group[group] = component_id
                components.append(
                    Component(
                        component_id=component_id,
                        name=group.replace("-", " ").title(),
                        kind=role.component_kind,
                        role=group,
                        environment="synthetic",
                    )
                )
            component_by_role[role.role_id] = component_id

        boundaries: list[Boundary] = []
        boundary_by_edge: dict[str, str] = {}
        for edge in topology.edges:
            boundary_id = f"boundary.synthetic.{_slug(edge.edge_id)}"
            boundary_by_edge[edge.edge_id] = boundary_id
            boundaries.append(
                Boundary(
                    boundary_id=boundary_id,
                    kind=edge.boundary_kind,
                    source_component_ref=component_by_role[edge.source_role_ref],
                    target_component_ref=component_by_role[edge.target_role_ref],
                    name=edge.boundary_name or edge.edge_id,
                    attributes={"topology_edge_ref": edge.edge_id},
                )
            )

        resources = tuple(
            Resource(
                resource_id=item.resource_id,
                kind=item.kind,
                name=item.name,
                owner_component_ref=(
                    component_by_role[item.owner_role_ref] if item.owner_role_ref else None
                ),
                sensitivity=item.sensitivity,
                attributes=item.attributes,
            )
            for item in topology.resources
        )
        system = SystemModel(
            system_id=f"system.synthetic.{_slug(instance.instance_id)}",
            name=f"Synthetic {topology.motif.value.replace('_', ' ')} laboratory",
            components=tuple(components),
            boundaries=tuple(boundaries),
            resources=resources,
            attributes={
                "scenario_instance": instance.instance_id,
                "topology_ref": topology.topology_id,
            },
        )

        source = SourceDescriptor(
            source_id="source.synthetic-engine",
            source_kind="synthetic_execution",
            name="Tracecase synthetic engine",
            schema_ref="tracecase.synthetic.v1",
            captured_at=base_time + timedelta(seconds=30),
            attributes={"instance_digest": instance.instance_digest},
        )

        workflow_id = f"workflow-{instance.instance_digest[-12:]}"
        trace_id = hashlib.sha256(instance.instance_digest.encode()).hexdigest()[:32]
        role_to_node = {role.role_id: f"node.synthetic.{_slug(role.role_id)}" for role in topology.roles}
        observations: list[Observation] = []
        nodes: list[ExecutionNode] = []
        contexts: list[ContextField] = []

        context_refs_by_role: dict[str, list[str]] = {role.role_id: [] for role in topology.roles}
        for contract in topology.contexts:
            for role_ref in (contract.source_role_ref, *contract.required_role_refs):
                context_id = f"context.synthetic.{_slug(contract.contract_id)}.{_slug(role_ref)}"
                contexts.append(
                    ContextField(
                        context_id=context_id,
                        namespace=contract.namespace,
                        field_name=contract.field_name,
                        value=contract.value,
                        propagation_contract=contract.propagation_contract,
                        origin_node_ref=role_to_node[contract.source_role_ref],
                        observed_at_node_ref=role_to_node[role_ref],
                        sensitivity=contract.sensitivity,
                        extensions={
                            "tracecase.scenario": {
                                "contract_ref": contract.contract_id,
                                "required_role_refs": list(contract.required_role_refs),
                            }
                        },
                    )
                )
                context_refs_by_role[role_ref].append(context_id)

        edge_boundary_refs: dict[str, list[str]] = {role.role_id: [] for role in topology.roles}
        for edge in topology.edges:
            boundary_id = boundary_by_edge[edge.edge_id]
            edge_boundary_refs[edge.source_role_ref].append(boundary_id)
            edge_boundary_refs[edge.target_role_ref].append(boundary_id)

        for role in topology.roles:
            node_id = role_to_node[role.role_id]
            observation_id = f"observation.synthetic.{_slug(role.role_id)}"
            start = base_time + timedelta(milliseconds=role.stage * 100)
            end = start + timedelta(milliseconds=40)
            identities = ExecutionIdentitySet(
                trace_id=trace_id,
                span_id=f"span-{_slug(role.role_id)}",
                workflow_id=workflow_id,
                run_id=instance.instance_id,
                logical_operation_id=f"operation-{_slug(role.operation)}",
                task_id=(f"task-{workflow_id}" if role.node_kind is NodeKind.TASK_ATTEMPT else None),
                task_attempt=(1 if role.node_kind is NodeKind.TASK_ATTEMPT else None),
                message_id=(f"message-{workflow_id}" if role.node_kind in {NodeKind.MESSAGE_PUBLISH, NodeKind.TASK_ATTEMPT} else None),
                tenant_id="tenant-alpha",
            )
            observations.append(
                Observation(
                    observation_id=observation_id,
                    kind=_observation_kind(role.node_kind),
                    provenance=ProvenanceRef(
                        source_id=source.source_id,
                        source_native_id=role.role_id,
                        payload_digest=_digest(role.role_id),
                    ),
                    captured_at=base_time + timedelta(seconds=30),
                    event_time=_time(start, f"clock.{_slug(component_by_role[role.role_id])}"),
                    normalized_refs=(node_id,),
                    attributes={
                        "scenario_role_ref": role.role_id,
                        "operation": role.operation,
                    },
                    sensitivity={SensitivityLabel.INTERNAL},
                )
            )
            parent_span = None
            incoming = [edge for edge in topology.edges if edge.target_role_ref == role.role_id]
            if incoming:
                parent_span = f"span-{_slug(incoming[0].source_role_ref)}"
            nodes.append(
                ExecutionNode(
                    node_id=node_id,
                    kind=role.node_kind,
                    operation=role.operation,
                    component_ref=component_by_role[role.role_id],
                    boundary_refs=tuple(sorted(set(edge_boundary_refs[role.role_id]))),
                    identities=identities.model_copy(update={"parent_span_id": parent_span}),
                    context_refs=tuple(context_refs_by_role[role.role_id]),
                    timing=_time(start, f"clock.{_slug(component_by_role[role.role_id])}"),
                    end_time=_time(end, f"clock.{_slug(component_by_role[role.role_id])}"),
                    status=role.default_status,
                    observation_refs=(observation_id,),
                    attributes={
                        **role.attributes,
                        "scenario_role_ref": role.role_id,
                        "stage": role.stage,
                    },
                )
            )

        relations: list[ExecutionRelation] = []
        for edge in topology.edges:
            relations.append(
                ExecutionRelation(
                    relation_id=f"relation.synthetic.{_slug(edge.edge_id)}",
                    kind=edge.relation_kind,
                    source_ref=role_to_node[edge.source_role_ref],
                    target_ref=role_to_node[edge.target_role_ref],
                    derivation=edge.derivation,
                    evidence_refs=(
                        f"observation.synthetic.{_slug(edge.source_role_ref)}",
                        f"observation.synthetic.{_slug(edge.target_role_ref)}",
                    ),
                    attributes={"topology_edge_ref": edge.edge_id},
                )
            )

        effects: list[Effect] = []
        state_facts: list[StateFact] = []
        for contract in topology.effects:
            effect_id = f"effect.synthetic.{_slug(contract.contract_id)}.1"
            producer_node_ref = role_to_node[contract.producer_role_ref]
            producer_observation = f"observation.synthetic.{_slug(contract.producer_role_ref)}"
            effect = Effect(
                effect_id=effect_id,
                kind=contract.effect_kind,
                logical_effect_key=contract.logical_effect_key,
                producer_node_ref=producer_node_ref,
                target_resource_ref=contract.target_resource_ref,
                operation=contract.operation,
                idempotency_key=contract.idempotency_key,
                durability=EffectDurability.DURABLE,
                completion_status="completed",
                evidence_refs=(producer_observation,),
                attributes={
                    **contract.attributes,
                    "contract_ref": contract.contract_id,
                    "maximum_durable_count": contract.maximum_durable_count,
                    "required": contract.required,
                },
            )
            effects.append(effect)
            relations.append(
                ExecutionRelation(
                    relation_id=f"relation.synthetic.effect.{_slug(contract.contract_id)}.1",
                    kind=RelationKind.PRODUCES_EFFECT,
                    source_ref=producer_node_ref,
                    target_ref=effect_id,
                    derivation=DerivationKind.DETERMINISTIC,
                    evidence_refs=(producer_observation,),
                )
            )
            if contract.target_resource_ref:
                state_facts.append(
                    StateFact(
                        fact_id=f"fact.synthetic.{_slug(contract.contract_id)}.1",
                        subject_ref=contract.target_resource_ref,
                        property_name="last_effect_status",
                        value="completed",
                        observed_time=next(
                            node.timing for node in nodes if node.node_id == producer_node_ref
                        ),
                        observation_ref=producer_observation,
                    )
                )

        effect_refs_by_node: dict[str, list[str]] = {}
        state_refs_by_node: dict[str, list[str]] = {}
        for effect in effects:
            effect_refs_by_node.setdefault(effect.producer_node_ref, []).append(effect.effect_id)
        for fact in state_facts:
            for effect in effects:
                if effect.target_resource_ref == fact.subject_ref:
                    state_refs_by_node.setdefault(effect.producer_node_ref, []).append(fact.fact_id)
        nodes = [
            node.model_copy(
                update={
                    "effect_refs": tuple(effect_refs_by_node.get(node.node_id, [])),
                    "state_refs": tuple(state_refs_by_node.get(node.node_id, [])),
                }
            )
            for node in nodes
        ]

        execution = ExecutionModel(
            execution_id=f"execution.synthetic.{_slug(instance.instance_id)}",
            nodes=tuple(nodes),
            relations=tuple(relations),
            contexts=tuple(contexts),
            state_facts=tuple(state_facts),
            effects=tuple(effects),
            observations=tuple(observations),
            evidence_classification=EvidenceClassification.RECORDED,
            extensions={
                "tracecase.scenario": {
                    "instance_id": instance.instance_id,
                    "family_ref": instance.family_ref,
                    "topology_ref": topology.topology_id,
                    "ground_truth": True,
                    "invariant_refs": list(family.invariant_refs),
                    "expected_effects": [
                        {
                            "contract_ref": contract.contract_id,
                            "logical_effect_key": contract.logical_effect_key,
                            "required": contract.required,
                            "maximum_durable_count": contract.maximum_durable_count,
                        }
                        for contract in topology.effects
                    ],
                    "expected_edges": [
                        {
                            "edge_id": edge.edge_id,
                            "source_role_ref": edge.source_role_ref,
                            "target_role_ref": edge.target_role_ref,
                            "relation_kind": edge.relation_kind.value,
                        }
                        for edge in topology.edges
                    ],
                }
            },
        )
        return ExecutionCase(
            specification=CaseSpecification(
                case_id=f"case.synthetic.{instance.instance_digest[-16:]}",
                title=title or f"Synthetic: {instance.family_ref}",
                category=CaseCategory.SYNTHETIC,
                description="Generated from a generic Tracecase scenario family and topology template.",
                created_at=base_time,
                roots=(
                    {"kind": "workflow_id", "value_token": workflow_id},
                    {"kind": "scenario_instance", "value_token": instance.instance_id},
                ),
                scenario_ref=instance.instance_id,
            ),
            system=system,
            evidence=CaseEvidence(sources=(source,), execution=execution),
            extensions={"tracecase.scenario": {"instance_digest": instance.instance_digest}},
        )

    def _apply_semantic_fault(
        self,
        case: ExecutionCase,
        application: FaultApplication,
    ) -> ExecutionCase:
        operator = self.registry.fault_operator(application.operator_ref)
        execution = case.evidence.execution
        if operator.kind is FaultOperatorKind.DROP_CONTEXT_FIELD:
            return self._drop_context(case, application)
        if operator.kind in {
            FaultOperatorKind.MUTATE_CONTEXT_FIELD,
            FaultOperatorKind.COPY_CONTEXT_FROM_OTHER_SCOPE,
        }:
            return self._mutate_context(case, application, copy_other=operator.kind is FaultOperatorKind.COPY_CONTEXT_FROM_OTHER_SCOPE)
        if operator.kind is FaultOperatorKind.DUPLICATE_EFFECT:
            return self._duplicate_effect(case, application)
        if operator.kind is FaultOperatorKind.OMIT_EFFECT:
            return self._omit_effect(case, application)
        if operator.kind is FaultOperatorKind.FAIL_AFTER_EFFECT:
            target = self._target_node(execution, application.target_ref)
            return self._replace_node(case, target.model_copy(update={"status": "error_after_effect"}))
        if operator.kind is FaultOperatorKind.DELAY_OPERATION:
            target = self._target_node(execution, application.target_ref)
            delay = int(application.parameters.get("delay_ms", 100))
            return self._replace_node(case, _shift_node(target, delay, preserve_normalized=False))
        if operator.kind is FaultOperatorKind.REORDER_OPERATIONS:
            return self._reorder(case, application)
        if operator.kind is FaultOperatorKind.SCHEMA_VERSION_SKEW:
            return self._schema_skew(case, application)
        if operator.kind is FaultOperatorKind.EXHAUST_RESOURCE:
            target = self._target_node(execution, application.target_ref)
            return self._replace_node(
                case,
                target.model_copy(
                    update={
                        "status": "resource_exhausted",
                        "attributes": {**target.attributes, "resource_capacity_exhausted": True},
                    }
                ),
            )
        if operator.kind is FaultOperatorKind.AMPLIFY_OPERATION:
            return self._amplify(case, application)
        if operator.kind is FaultOperatorKind.COLLAPSE_EXECUTION_IDENTITY:
            nodes = tuple(
                node.model_copy(
                    update={
                        "identities": node.identities.model_copy(
                            update={"workflow_id": "workflow-collided", "trace_id": "0" * 32}
                        ),
                        "attributes": {**node.attributes, "identity_collision": True},
                    }
                )
                for node in execution.nodes
            )
            return _with_execution(case, execution.model_copy(update={"nodes": nodes}))
        return case

    def _apply_observability_fault(
        self,
        case: ExecutionCase,
        application: FaultApplication,
    ) -> ExecutionCase:
        operator = self.registry.fault_operator(application.operator_ref)
        if operator.kind is FaultOperatorKind.BREAK_TRACE_LINK:
            return self._break_trace_link(case, application)
        if operator.kind is FaultOperatorKind.DROP_OBSERVATION:
            return self._drop_observation(case, application)
        if operator.kind is FaultOperatorKind.CLOCK_SKEW:
            target = self._target_node(case.evidence.execution, application.target_ref)
            skew = int(application.parameters.get("skew_ms", 500))
            return self._replace_node(case, _shift_node(target, skew, preserve_normalized=True))
        if operator.kind is FaultOperatorKind.INJECT_CONTRADICTORY_OBSERVATION:
            return self._inject_contradiction(case, application)
        if operator.kind is FaultOperatorKind.CAPTURE_PROHIBITED_FIELD:
            return self._capture_secret(case, application)
        return case

    def _apply_observability_profile(
        self,
        case: ExecutionCase,
        profile: ObservabilityProfile,
    ) -> ExecutionCase:
        execution = case.evidence.execution
        if profile is ObservabilityProfile.COMPLETE:
            return case
        if profile is ObservabilityProfile.SOURCE_ONLY:
            destination = max(execution.nodes, key=lambda item: item.timing.effective_timestamp)
            return self._drop_observation(
                case,
                FaultApplication(
                    application_id="application.profile-source-only",
                    operator_ref="fault.drop-observation.v1",
                    target_kind="role",
                    target_ref=destination.node_id,
                ),
            )
        if profile is ObservabilityProfile.DESTINATION_ONLY:
            source = min(execution.nodes, key=lambda item: item.timing.effective_timestamp)
            return self._drop_observation(
                case,
                FaultApplication(
                    application_id="application.profile-destination-only",
                    operator_ref="fault.drop-observation.v1",
                    target_kind="role",
                    target_ref=source.node_id,
                ),
            )
        if profile in {ObservabilityProfile.MISSING_BOUNDARY, ObservabilityProfile.BROKEN_TRACE}:
            return self._break_trace_link(
                case,
                FaultApplication(
                    application_id="application.profile-broken-trace",
                    operator_ref="fault.break-trace-link.v1",
                    target_kind="edge",
                ),
            )
        if profile is ObservabilityProfile.CLOCK_SKEWED:
            target = max(execution.nodes, key=lambda item: item.timing.effective_timestamp)
            return self._replace_node(case, _shift_node(target, 750, preserve_normalized=True))
        if profile is ObservabilityProfile.CONTRADICTORY:
            return self._inject_contradiction(
                case,
                FaultApplication(
                    application_id="application.profile-contradiction",
                    operator_ref="fault.contradictory-observation.v1",
                    target_kind="observation",
                ),
            )
        if profile is ObservabilityProfile.REDACTED:
            contexts = tuple(
                context.model_copy(update={"value": f"token-{_slug(context.context_id)[-8:]}"})
                if context.sensitivity
                else context
                for context in execution.contexts
            )
            return _with_execution(case, execution.model_copy(update={"contexts": contexts}))
        return case

    def _drop_context(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        candidates = list(execution.contexts)
        target_ref = application.target_ref
        removable = [
            item
            for item in candidates
            if item.context_id == target_ref
            or item.observed_at_node_ref == target_ref
            or item.qualified_name == target_ref
        ]
        if not removable:
            removable = [
                item
                for item in candidates
                if item.observed_at_node_ref != item.origin_node_ref
                and item.propagation_contract.value == "required"
            ][:1]
        removed_ids = {item.context_id for item in removable}
        contexts = tuple(item for item in candidates if item.context_id not in removed_ids)
        nodes = tuple(
            node.model_copy(
                update={"context_refs": tuple(ref for ref in node.context_refs if ref not in removed_ids)}
            )
            for node in execution.nodes
        )
        return _with_execution(case, execution.model_copy(update={"contexts": contexts, "nodes": nodes}))

    def _mutate_context(
        self,
        case: ExecutionCase,
        application: FaultApplication,
        *,
        copy_other: bool,
    ) -> ExecutionCase:
        execution = case.evidence.execution
        replacement = "tenant-other" if copy_other else application.parameters.get("replacement", "mutated")
        candidates = [
            item
            for item in execution.contexts
            if item.context_id == application.target_ref
            or item.observed_at_node_ref == application.target_ref
            or item.qualified_name == application.target_ref
        ]
        if not candidates:
            candidates = [
                item for item in execution.contexts if item.observed_at_node_ref != item.origin_node_ref
            ][:1]
        target_ids = {item.context_id for item in candidates}
        contexts = tuple(
            item.model_copy(update={"value": replacement}) if item.context_id in target_ids else item
            for item in execution.contexts
        )
        return _with_execution(case, execution.model_copy(update={"contexts": contexts}))

    def _duplicate_effect(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        target = next(
            (
                item
                for item in execution.effects
                if item.effect_id == application.target_ref
                or item.logical_effect_key == application.target_ref
            ),
            execution.effects[0] if execution.effects else None,
        )
        if target is None:
            return case
        copies = max(2, int(application.parameters.get("copies", 2)))
        producer = next(node for node in execution.nodes if node.node_id == target.producer_node_ref)
        effects = list(execution.effects)
        nodes = list(execution.nodes)
        observations = list(execution.observations)
        relations = list(execution.relations)
        previous_node = producer
        for attempt in range(2, copies + 1):
            retry_node_id = f"{producer.node_id}.retry-{attempt}"
            retry_observation_id = f"observation.synthetic.retry-{attempt}"
            retry_node = _shift_node(producer, attempt * 100, preserve_normalized=False).model_copy(
                update={
                    "node_id": retry_node_id,
                    "status": "ok",
                    "identities": producer.identities.model_copy(
                        update={
                            "span_id": f"{producer.identities.span_id}-retry-{attempt}",
                            "operation_attempt_id": f"attempt-{attempt}",
                            "task_attempt": attempt,
                        }
                    ),
                    "observation_refs": (retry_observation_id,),
                    "effect_refs": (f"{target.effect_id}.copy-{attempt}",),
                    "state_refs": (),
                    "attributes": {**producer.attributes, "synthetic_retry": True},
                }
            )
            nodes.append(retry_node)
            observations.append(
                Observation(
                    observation_id=retry_observation_id,
                    kind=ObservationKind.TASK_EVENT,
                    provenance=ProvenanceRef(
                        source_id="source.synthetic-engine",
                        source_native_id=retry_node_id,
                        payload_digest=_digest(retry_node_id),
                    ),
                    captured_at=retry_node.timing.effective_timestamp + timedelta(seconds=30),
                    event_time=retry_node.timing,
                    normalized_refs=(retry_node_id,),
                    attributes={"attempt": attempt, "redelivery": True},
                )
            )
            duplicate = target.model_copy(
                update={
                    "effect_id": f"{target.effect_id}.copy-{attempt}",
                    "producer_node_ref": retry_node_id,
                    "evidence_refs": (retry_observation_id,),
                    "attributes": {**target.attributes, "duplicate_copy": attempt},
                }
            )
            effects.append(duplicate)
            relations.extend(
                (
                    ExecutionRelation(
                        relation_id=f"relation.synthetic.retry-{attempt}",
                        kind=RelationKind.RETRIES,
                        source_ref=previous_node.node_id,
                        target_ref=retry_node_id,
                        derivation=DerivationKind.DETERMINISTIC,
                        evidence_refs=(retry_observation_id,),
                    ),
                    ExecutionRelation(
                        relation_id=f"relation.synthetic.duplicate-effect-{attempt}",
                        kind=RelationKind.PRODUCES_EFFECT,
                        source_ref=retry_node_id,
                        target_ref=duplicate.effect_id,
                        derivation=DerivationKind.DETERMINISTIC,
                        evidence_refs=(retry_observation_id,),
                    ),
                    ExecutionRelation(
                        relation_id=f"relation.synthetic.repeated-effect-{attempt}",
                        kind=RelationKind.REPEATS_EFFECT,
                        source_ref=target.effect_id,
                        target_ref=duplicate.effect_id,
                        derivation=DerivationKind.DETERMINISTIC,
                        evidence_refs=(retry_observation_id,),
                    ),
                )
            )
            previous_node = retry_node
        return _with_execution(
            case,
            execution.model_copy(
                update={
                    "nodes": tuple(nodes),
                    "effects": tuple(effects),
                    "observations": tuple(observations),
                    "relations": tuple(relations),
                }
            ),
        )

    def _omit_effect(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        target_ids = {
            item.effect_id
            for item in execution.effects
            if item.effect_id == application.target_ref
            or item.logical_effect_key == application.target_ref
        }
        if not target_ids and execution.effects:
            target_ids.add(execution.effects[0].effect_id)
        effects = tuple(item for item in execution.effects if item.effect_id not in target_ids)
        relations = tuple(
            item
            for item in execution.relations
            if item.source_ref not in target_ids and item.target_ref not in target_ids
        )
        nodes = tuple(
            node.model_copy(
                update={"effect_refs": tuple(ref for ref in node.effect_refs if ref not in target_ids)}
            )
            for node in execution.nodes
        )
        return _with_execution(
            case,
            execution.model_copy(update={"effects": effects, "relations": relations, "nodes": nodes}),
        )

    def _reorder(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        relation = next(
            (item for item in execution.relations if item.relation_id == application.target_ref),
            next((item for item in execution.relations if item.target_ref in {node.node_id for node in execution.nodes}), None),
        )
        if relation is None:
            return case
        source = next(node for node in execution.nodes if node.node_id == relation.source_ref)
        target = next(node for node in execution.nodes if node.node_id == relation.target_ref)
        new_start = source.timing.effective_timestamp - timedelta(milliseconds=20)
        clock = target.timing.clock_ref or "clock.synthetic"
        changed = target.model_copy(
            update={
                "timing": _time(new_start, clock),
                "end_time": _time(new_start + timedelta(milliseconds=10), clock),
                "attributes": {**target.attributes, "synthetic_reordered": True},
            }
        )
        return self._replace_node(case, changed)

    def _schema_skew(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        nodes = list(execution.nodes)
        if nodes:
            nodes[0] = nodes[0].model_copy(
                update={"attributes": {**nodes[0].attributes, "schema_version": "2.0"}}
            )
            nodes[-1] = nodes[-1].model_copy(
                update={"attributes": {**nodes[-1].attributes, "schema_version": "1.0"}}
            )
        return _with_execution(case, execution.model_copy(update={"nodes": tuple(nodes)}))

    def _amplify(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        target = self._target_node(execution, application.target_ref)
        factor = max(2, int(application.parameters.get("factor", 5)))
        nodes = list(execution.nodes)
        observations = list(execution.observations)
        relations = list(execution.relations)
        for index in range(2, factor + 1):
            node_id = f"{target.node_id}.amplified-{index}"
            observation_id = f"observation.synthetic.amplified-{index}"
            duplicate = _shift_node(target, index * 10, preserve_normalized=False).model_copy(
                update={
                    "node_id": node_id,
                    "observation_refs": (observation_id,),
                    "effect_refs": (),
                    "state_refs": (),
                    "identities": target.identities.model_copy(
                        update={"span_id": f"{target.identities.span_id}-amplified-{index}"}
                    ),
                    "attributes": {**target.attributes, "amplification_index": index},
                }
            )
            nodes.append(duplicate)
            observations.append(
                Observation(
                    observation_id=observation_id,
                    kind=ObservationKind.TASK_EVENT,
                    provenance=ProvenanceRef(
                        source_id="source.synthetic-engine",
                        source_native_id=node_id,
                        payload_digest=_digest(node_id),
                    ),
                    captured_at=duplicate.timing.effective_timestamp + timedelta(seconds=30),
                    event_time=duplicate.timing,
                    normalized_refs=(node_id,),
                    attributes={"amplified": True, "index": index},
                )
            )
            relations.append(
                ExecutionRelation(
                    relation_id=f"relation.synthetic.amplified-{index}",
                    kind=RelationKind.SPAWNS,
                    source_ref=target.node_id,
                    target_ref=node_id,
                    derivation=DerivationKind.DETERMINISTIC,
                    evidence_refs=(observation_id,),
                )
            )
        return _with_execution(
            case,
            execution.model_copy(
                update={
                    "nodes": tuple(nodes),
                    "observations": tuple(observations),
                    "relations": tuple(relations),
                }
            ),
        )

    def _break_trace_link(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        candidate = next(
            (item for item in execution.relations if item.relation_id == application.target_ref),
            next(
                (
                    item
                    for item in execution.relations
                    if item.kind in {RelationKind.DELIVERS, RelationKind.PUBLISHES, RelationKind.SPAWNS}
                ),
                None,
            ),
        )
        if candidate is None:
            return case
        relations = tuple(item for item in execution.relations if item.relation_id != candidate.relation_id)
        nodes = tuple(
            node.model_copy(
                update={
                    "identities": node.identities.model_copy(
                        update={
                            "trace_id": hashlib.sha256(node.node_id.encode()).hexdigest()[:32],
                            "parent_span_id": None,
                        }
                    )
                }
            )
            if node.node_id == candidate.target_ref
            else node
            for node in execution.nodes
        )
        return _with_execution(case, execution.model_copy(update={"relations": relations, "nodes": nodes}))

    def _drop_observation(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        target_ids = {
            item.observation_id
            for item in execution.observations
            if item.observation_id == application.target_ref
            or application.target_ref in item.normalized_refs
        }
        if not target_ids and execution.observations:
            target_ids.add(execution.observations[-1].observation_id)
        observations = tuple(item for item in execution.observations if item.observation_id not in target_ids)
        nodes = tuple(
            node.model_copy(
                update={"observation_refs": tuple(ref for ref in node.observation_refs if ref not in target_ids)}
            )
            for node in execution.nodes
        )
        relations = tuple(
            relation.model_copy(
                update={"evidence_refs": tuple(ref for ref in relation.evidence_refs if ref not in target_ids)}
            )
            for relation in execution.relations
        )
        effects = tuple(
            effect.model_copy(
                update={"evidence_refs": tuple(ref for ref in effect.evidence_refs if ref not in target_ids)}
            )
            for effect in execution.effects
        )
        facts = tuple(
            fact
            for fact in execution.state_facts
            if fact.observation_ref not in target_ids
        )
        return _with_execution(
            case,
            execution.model_copy(
                update={
                    "observations": observations,
                    "nodes": nodes,
                    "relations": relations,
                    "effects": effects,
                    "state_facts": facts,
                }
            ),
        )

    def _inject_contradiction(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        target = self._target_node(execution, application.target_ref)
        observation_id = "observation.synthetic.contradiction"
        observation = Observation(
            observation_id=observation_id,
            kind=ObservationKind.LOG,
            provenance=ProvenanceRef(
                source_id="source.synthetic-engine",
                source_native_id="contradiction",
                payload_digest=_digest("contradiction"),
            ),
            captured_at=target.timing.effective_timestamp + timedelta(seconds=30),
            event_time=target.timing,
            normalized_refs=(target.node_id,),
            attributes={
                "reported_status": "failed",
                "contradicts_status": target.status,
                "synthetic_contradiction": True,
            },
        )
        return _with_execution(
            case,
            execution.model_copy(update={"observations": (*execution.observations, observation)}),
        )

    def _capture_secret(self, case: ExecutionCase, application: FaultApplication) -> ExecutionCase:
        execution = case.evidence.execution
        target = execution.observations[0]
        observations = tuple(
            item.model_copy(
                update={
                    "attributes": {
                        **item.attributes,
                        "authorization": "Bearer tracecase-canary-secret",
                    },
                    "sensitivity": {*item.sensitivity, SensitivityLabel.CREDENTIAL},
                }
            )
            if item.observation_id == target.observation_id
            else item
            for item in execution.observations
        )
        return _with_execution(case, execution.model_copy(update={"observations": observations}))

    def _replace_node(self, case: ExecutionCase, changed: ExecutionNode) -> ExecutionCase:
        execution = case.evidence.execution
        nodes = tuple(changed if item.node_id == changed.node_id else item for item in execution.nodes)
        return _with_execution(case, execution.model_copy(update={"nodes": nodes}))

    @staticmethod
    def _target_node(execution: ExecutionModel, target_ref: str | None) -> ExecutionNode:
        if target_ref:
            for node in execution.nodes:
                if node.node_id == target_ref or node.attributes.get("scenario_role_ref") == target_ref:
                    return node
        return execution.nodes[-1]

    def _oracle_outcomes(
        self,
        instance: ScenarioInstance,
        has_semantic_fault: bool,
        has_observability_fault: bool,
    ) -> tuple[SyntheticOracleOutcome, ...]:
        if instance.expected_invariants:
            return tuple(
                SyntheticOracleOutcome(
                    invariant_ref=item.invariant_ref,
                    expected_status=item.expected_status,
                    basis=item.rationale or "declared by scenario definition",
                    scope_ref=item.scope_ref,
                )
                for item in instance.expected_invariants
            )
        family = self.registry.family(instance.family_ref)
        outcomes: list[SyntheticOracleOutcome] = []
        for invariant_ref in family.invariant_refs:
            if has_semantic_fault:
                status = InvariantExpectedStatus.VIOLATED
                basis = "semantic fault operator mutates ground-truth execution"
            elif has_observability_fault:
                if invariant_ref.startswith("invariant.observability") or invariant_ref.startswith("invariant.privacy"):
                    status = InvariantExpectedStatus.VIOLATED
                    basis = "observability fault directly violates the evidence contract"
                else:
                    status = InvariantExpectedStatus.INCONCLUSIVE
                    basis = "observability degradation prevents complete evaluation"
            else:
                status = InvariantExpectedStatus.SATISFIED
                basis = "unfaulted generated baseline"
            outcomes.append(
                SyntheticOracleOutcome(
                    invariant_ref=invariant_ref,
                    expected_status=status,
                    basis=basis,
                )
            )
        return tuple(outcomes)


def _with_execution(case: ExecutionCase, execution: ExecutionModel) -> ExecutionCase:
    return case.model_copy(
        update={"evidence": case.evidence.model_copy(update={"execution": execution})}
    )


def _shift_node(node: ExecutionNode, milliseconds: int, *, preserve_normalized: bool) -> ExecutionNode:
    def shift(value: TimeObservation | None) -> TimeObservation | None:
        if value is None:
            return None
        normalized = value.normalized_timestamp if preserve_normalized else (
            value.normalized_timestamp + timedelta(milliseconds=milliseconds)
            if value.normalized_timestamp
            else None
        )
        return value.model_copy(
            update={
                "raw_timestamp": value.raw_timestamp + timedelta(milliseconds=milliseconds),
                "normalized_timestamp": normalized,
                "normalization_method": (
                    "synthetic_clock_correction" if preserve_normalized else value.normalization_method
                ),
            }
        )

    return node.model_copy(update={"timing": shift(node.timing), "end_time": shift(node.end_time)})


def _time(value: datetime, clock: str) -> TimeObservation:
    return TimeObservation(
        raw_timestamp=value,
        normalized_timestamp=value,
        clock_ref=clock,
        precision_ns=1_000_000,
        normalization_method="synthetic_identity",
    )


def _observation_kind(kind: NodeKind) -> ObservationKind:
    if kind in {NodeKind.MESSAGE_PUBLISH, NodeKind.MESSAGE_DELIVERY, NodeKind.MESSAGE_CONSUME, NodeKind.TASK_ATTEMPT}:
        return ObservationKind.TASK_EVENT
    if kind in {NodeKind.QUERY, NodeKind.READ, NodeKind.WRITE, NodeKind.TRANSACTION}:
        return ObservationKind.SQL_EVENT
    if kind in {NodeKind.USER_ACTION, NodeKind.UI_EVENT, NodeKind.CLIENT_REQUEST}:
        return ObservationKind.FRONTEND_EVENT
    if kind in {NodeKind.REQUEST_HANDLER, NodeKind.EXTERNAL_REQUEST, NodeKind.EXTERNAL_RESPONSE}:
        return ObservationKind.HTTP_EVENT
    return ObservationKind.SPAN


def _slug(value: str) -> str:
    lowered = value.lower().replace("_", "-")
    lowered = re.sub(r"[^a-z0-9.-]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-.")
    return lowered or "item"


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()
