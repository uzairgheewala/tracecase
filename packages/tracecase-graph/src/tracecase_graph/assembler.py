from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Iterable

from tracecase_model import (
    Confidence,
    DerivationKind,
    ExecutionModel,
    ExecutionNode,
    ExecutionRelation,
    RelationKind,
    TemporalRelationKind,
)
from tracecase_model.execution import EffectDurability
from tracecase_model.system import SystemModel

from .models import (
    AssembledExecutionGraph,
    ContextFlow,
    ContextFlowStatus,
    EffectGroup,
    GraphAssemblyReport,
    GraphAssemblyWarning,
    IdentityGroup,
    IdentityGroupKind,
    TemporalConstraint,
    TimelineConnector,
    TimelineEntry,
    TimelineLane,
    TimelineModel,
)


class GraphAssembler:
    """Deterministically assembles execution semantics without mutating source evidence."""

    VERSION = "0.3.0"

    def assemble(self, execution: ExecutionModel) -> AssembledExecutionGraph:
        nodes = tuple(sorted(execution.nodes, key=_node_sort_key))
        source_relations = tuple(sorted(execution.relations, key=lambda item: item.relation_id))
        derived: list[ExecutionRelation] = []
        warnings: list[GraphAssemblyWarning] = []
        existing_keys = {
            (relation.kind, relation.source_ref, relation.target_ref)
            for relation in source_relations
        }
        node_by_id = {node.node_id: node for node in nodes}

        derived.extend(self._parent_span_relations(nodes, existing_keys))
        existing_keys.update((item.kind, item.source_ref, item.target_ref) for item in derived)
        derived.extend(self._message_relations(nodes, existing_keys))
        existing_keys.update((item.kind, item.source_ref, item.target_ref) for item in derived)
        derived.extend(self._retry_relations(nodes, existing_keys))
        existing_keys.update((item.kind, item.source_ref, item.target_ref) for item in derived)
        derived.extend(self._effect_relations(execution, existing_keys))

        all_relations = tuple(sorted((*source_relations, *derived), key=lambda item: item.relation_id))
        identity_groups = self._identity_groups(nodes)
        context_flows = self._context_flows(execution, node_by_id)
        effect_groups = self._effect_groups(execution)
        temporal_constraints, temporal_warnings = self._temporal_constraints(all_relations, node_by_id)
        warnings.extend(temporal_warnings)
        disconnected = self._disconnected_components(nodes, all_relations)
        if len(disconnected) > 1:
            warnings.append(
                GraphAssemblyWarning(
                    warning_id=_stable_id("warning.disconnected", execution.execution_id),
                    code="disconnected_execution_fragments",
                    message=f"Execution graph contains {len(disconnected)} disconnected node components.",
                    node_refs=tuple(node_id for component in disconnected for node_id in component),
                )
            )
        report = GraphAssemblyReport(
            source_relation_count=len(source_relations),
            derived_relation_count=len(derived),
            identity_group_count=len(identity_groups),
            context_flow_count=len(context_flows),
            effect_group_count=len(effect_groups),
            temporal_constraint_count=len(temporal_constraints),
            disconnected_components=disconnected,
            warnings=tuple(sorted(warnings, key=lambda item: item.warning_id)),
            attributes={
                "node_count": len(nodes),
                "explicit_relation_count": sum(
                    1 for item in all_relations if item.derivation is DerivationKind.EXPLICIT
                ),
                "heuristic_relation_count": sum(
                    1 for item in all_relations if item.derivation is DerivationKind.HEURISTIC
                ),
            },
        )
        return AssembledExecutionGraph(
            graph_id=_stable_id("graph.assembled", execution.execution_id),
            execution_id=execution.execution_id,
            nodes=nodes,
            relations=all_relations,
            source_relation_refs=tuple(item.relation_id for item in source_relations),
            derived_relation_refs=tuple(item.relation_id for item in sorted(derived, key=lambda item: item.relation_id)),
            identity_groups=identity_groups,
            context_flows=context_flows,
            effect_groups=effect_groups,
            temporal_constraints=temporal_constraints,
            report=report,
        )

    def timeline(self, graph: AssembledExecutionGraph, system: SystemModel) -> TimelineModel:
        if not graph.nodes:
            origin = datetime.fromtimestamp(0).astimezone()
            return TimelineModel(
                timeline_id=_stable_id("timeline", graph.execution_id),
                execution_id=graph.execution_id,
                origin_timestamp=origin.isoformat(),
                total_duration_ms=0,
                lanes=(),
                connectors=(),
                warnings=graph.report.warnings,
            )
        origin = min(node.timing.effective_timestamp for node in graph.nodes)
        final = max(
            (node.end_time or node.timing).effective_timestamp
            for node in graph.nodes
        )
        components = {component.component_id: component for component in system.components}
        entries_by_component: dict[str, list[TimelineEntry]] = defaultdict(list)
        entry_by_node: dict[str, str] = {}
        for node in graph.nodes:
            start = node.timing.effective_timestamp
            end = (node.end_time or node.timing).effective_timestamp
            entry_id = _stable_id("timeline-entry", node.node_id)
            entry_by_node[node.node_id] = entry_id
            entries_by_component[node.component_ref].append(
                TimelineEntry(
                    entry_id=entry_id,
                    node_ref=node.node_id,
                    component_ref=node.component_ref,
                    operation=node.operation,
                    node_kind=node.kind.value,
                    status=node.status,
                    start_offset_ms=(start - origin).total_seconds() * 1000,
                    duration_ms=max(0.0, (end - start).total_seconds() * 1000),
                    uncertainty_ms=node.timing.uncertainty.total_seconds() * 1000,
                    attempt=node.identities.task_attempt,
                    attributes={
                        "workflow_id": node.identities.workflow_id,
                        "trace_id": node.identities.trace_id,
                    },
                )
            )
        lanes = tuple(
            TimelineLane(
                lane_id=_stable_id("timeline-lane", component_ref),
                component_ref=component_ref,
                label=components.get(component_ref).name if component_ref in components else component_ref,
                entries=tuple(sorted(entries, key=lambda item: (item.start_offset_ms, item.entry_id))),
            )
            for component_ref, entries in sorted(entries_by_component.items())
        )
        connectors = tuple(
            TimelineConnector(
                connector_id=_stable_id("timeline-connector", relation.relation_id),
                relation_ref=relation.relation_id,
                source_entry_ref=entry_by_node[relation.source_ref],
                target_entry_ref=entry_by_node[relation.target_ref],
                relation_kind=relation.kind.value,
                derivation=relation.derivation,
            )
            for relation in graph.relations
            if relation.source_ref in entry_by_node and relation.target_ref in entry_by_node
        )
        return TimelineModel(
            timeline_id=_stable_id("timeline", graph.execution_id),
            execution_id=graph.execution_id,
            origin_timestamp=origin.isoformat(),
            total_duration_ms=max(0.0, (final - origin).total_seconds() * 1000),
            lanes=lanes,
            connectors=connectors,
            warnings=graph.report.warnings,
        )

    @staticmethod
    def _parent_span_relations(
        nodes: tuple[ExecutionNode, ...],
        existing: set[tuple[RelationKind, str, str]],
    ) -> list[ExecutionRelation]:
        node_by_span = {
            node.identities.span_id: node
            for node in nodes
            if node.identities.span_id
        }
        result: list[ExecutionRelation] = []
        for child in nodes:
            parent_span = child.identities.parent_span_id
            if not parent_span or parent_span not in node_by_span:
                continue
            parent = node_by_span[parent_span]
            key = (RelationKind.PARENT_OF, parent.node_id, child.node_id)
            if key in existing:
                continue
            result.append(
                ExecutionRelation(
                    relation_id=_stable_id("relation.parent-span", parent.node_id, child.node_id),
                    kind=RelationKind.PARENT_OF,
                    source_ref=parent.node_id,
                    target_ref=child.node_id,
                    derivation=DerivationKind.SOURCE_NATIVE,
                    evidence_refs=tuple(sorted({*parent.observation_refs, *child.observation_refs})),
                    confidence=Confidence(score=1.0, rationale="parent_span_id matched source span_id"),
                )
            )
        return result

    @staticmethod
    def _message_relations(
        nodes: tuple[ExecutionNode, ...],
        existing: set[tuple[RelationKind, str, str]],
    ) -> list[ExecutionRelation]:
        grouped: dict[str, list[ExecutionNode]] = defaultdict(list)
        for node in nodes:
            if node.identities.message_id:
                grouped[node.identities.message_id].append(node)
        result: list[ExecutionRelation] = []
        for message_id, members in grouped.items():
            ordered = sorted(members, key=_node_sort_key)
            publishers = [node for node in ordered if node.kind.value == "message_publish"]
            consumers = [
                node for node in ordered
                if node.kind.value in {"message_delivery", "message_consume", "task_attempt"}
            ]
            if not publishers or not consumers:
                continue
            publisher = publishers[0]
            for consumer in consumers:
                key = (RelationKind.DELIVERS, publisher.node_id, consumer.node_id)
                if key in existing:
                    continue
                result.append(
                    ExecutionRelation(
                        relation_id=_stable_id("relation.message", message_id, publisher.node_id, consumer.node_id),
                        kind=RelationKind.DELIVERS,
                        source_ref=publisher.node_id,
                        target_ref=consumer.node_id,
                        derivation=DerivationKind.DETERMINISTIC,
                        evidence_refs=tuple(sorted({*publisher.observation_refs, *consumer.observation_refs})),
                        confidence=Confidence(score=0.98, rationale="matching message_id"),
                        attributes={"message_id": message_id},
                    )
                )
        return result

    @staticmethod
    def _retry_relations(
        nodes: tuple[ExecutionNode, ...],
        existing: set[tuple[RelationKind, str, str]],
    ) -> list[ExecutionRelation]:
        grouped: dict[str, list[ExecutionNode]] = defaultdict(list)
        for node in nodes:
            if node.identities.task_id:
                grouped[node.identities.task_id].append(node)
        result: list[ExecutionRelation] = []
        for task_id, members in grouped.items():
            ordered = sorted(
                members,
                key=lambda item: (
                    item.identities.task_attempt if item.identities.task_attempt is not None else 10**9,
                    *_node_sort_key(item),
                ),
            )
            for previous, current in zip(ordered, ordered[1:]):
                previous_attempt = previous.identities.task_attempt
                current_attempt = current.identities.task_attempt
                if previous_attempt is None or current_attempt is None or current_attempt <= previous_attempt:
                    continue
                key = (RelationKind.RETRIES, previous.node_id, current.node_id)
                if key in existing:
                    continue
                result.append(
                    ExecutionRelation(
                        relation_id=_stable_id("relation.retry", task_id, previous.node_id, current.node_id),
                        kind=RelationKind.RETRIES,
                        source_ref=previous.node_id,
                        target_ref=current.node_id,
                        derivation=DerivationKind.DETERMINISTIC,
                        evidence_refs=tuple(sorted({*previous.observation_refs, *current.observation_refs})),
                        confidence=Confidence(score=1.0, rationale="same task_id with increasing attempt"),
                        attributes={"task_id": task_id},
                    )
                )
        return result

    @staticmethod
    def _effect_relations(
        execution: ExecutionModel,
        existing: set[tuple[RelationKind, str, str]],
    ) -> list[ExecutionRelation]:
        grouped: dict[str, list[str]] = defaultdict(list)
        evidence_by_effect = {effect.effect_id: effect.evidence_refs for effect in execution.effects}
        for effect in execution.effects:
            grouped[effect.logical_effect_key].append(effect.effect_id)
        result: list[ExecutionRelation] = []
        for logical_key, members in grouped.items():
            ordered = sorted(members)
            if len(ordered) < 2:
                continue
            first = ordered[0]
            for duplicate in ordered[1:]:
                key = (RelationKind.REPEATS_EFFECT, first, duplicate)
                if key in existing:
                    continue
                result.append(
                    ExecutionRelation(
                        relation_id=_stable_id("relation.repeated-effect", logical_key, first, duplicate),
                        kind=RelationKind.REPEATS_EFFECT,
                        source_ref=first,
                        target_ref=duplicate,
                        derivation=DerivationKind.DETERMINISTIC,
                        evidence_refs=tuple(sorted({*evidence_by_effect[first], *evidence_by_effect[duplicate]})),
                        confidence=Confidence(score=1.0, rationale="matching logical_effect_key"),
                        attributes={"logical_effect_key": logical_key},
                    )
                )
        return result

    @staticmethod
    def _identity_groups(nodes: tuple[ExecutionNode, ...]) -> tuple[IdentityGroup, ...]:
        fields = (
            (IdentityGroupKind.TRACE, "trace_id"),
            (IdentityGroupKind.WORKFLOW, "workflow_id"),
            (IdentityGroupKind.LOGICAL_OPERATION, "logical_operation_id"),
            (IdentityGroupKind.TASK, "task_id"),
            (IdentityGroupKind.MESSAGE, "message_id"),
            (IdentityGroupKind.TRANSACTION, "transaction_id"),
            (IdentityGroupKind.TENANT, "tenant_id"),
            (IdentityGroupKind.IDEMPOTENCY_SCOPE, "idempotency_key"),
        )
        groups: list[IdentityGroup] = []
        for kind, field in fields:
            values: dict[str, list[str]] = defaultdict(list)
            for node in nodes:
                value = getattr(node.identities, field)
                if value:
                    values[value].append(node.node_id)
            for value, members in values.items():
                if len(members) < 2:
                    continue
                groups.append(
                    IdentityGroup(
                        group_id=_stable_id("identity-group", kind.value, value),
                        kind=kind,
                        identity_value=value,
                        member_node_refs=tuple(sorted(members)),
                    )
                )
        return tuple(sorted(groups, key=lambda item: item.group_id))

    @staticmethod
    def _context_flows(
        execution: ExecutionModel,
        node_by_id: dict[str, ExecutionNode],
    ) -> tuple[ContextFlow, ...]:
        groups: dict[str, list] = defaultdict(list)
        for context in execution.contexts:
            groups[context.qualified_name].append(context)
        flows: list[ContextFlow] = []
        for qualified_name, contexts in groups.items():
            ordered = sorted(
                contexts,
                key=lambda item: (
                    node_by_id[item.observed_at_node_ref].timing.effective_timestamp
                    if item.observed_at_node_ref in node_by_id
                    else datetime.max.replace(tzinfo=timezone.utc),
                    item.context_id,
                ),
            )
            for source, target in zip(ordered, ordered[1:]):
                if not source.observed_at_node_ref or not target.observed_at_node_ref:
                    continue
                if source.value == target.value:
                    status = ContextFlowStatus.PRESERVED
                elif target.propagation_contract.value == "regenerated":
                    status = ContextFlowStatus.REGENERATED
                else:
                    status = ContextFlowStatus.MUTATED
                flows.append(
                    ContextFlow(
                        flow_id=_stable_id("context-flow", qualified_name, source.context_id, target.context_id),
                        qualified_name=qualified_name,
                        source_context_ref=source.context_id,
                        target_context_ref=target.context_id,
                        source_node_ref=source.observed_at_node_ref,
                        target_node_ref=target.observed_at_node_ref,
                        status=status,
                        derivation=DerivationKind.DETERMINISTIC,
                        confidence=Confidence(score=1.0, rationale="same qualified context name"),
                    )
                )
        return tuple(sorted(flows, key=lambda item: item.flow_id))

    @staticmethod
    def _effect_groups(execution: ExecutionModel) -> tuple[EffectGroup, ...]:
        groups: dict[str, list] = defaultdict(list)
        for effect in execution.effects:
            groups[effect.logical_effect_key].append(effect)
        result: list[EffectGroup] = []
        for logical_key, effects in groups.items():
            durable_count = sum(
                effect.durability in {EffectDurability.COMMITTED, EffectDurability.DURABLE}
                for effect in effects
            )
            result.append(
                EffectGroup(
                    group_id=_stable_id("effect-group", logical_key),
                    logical_effect_key=logical_key,
                    member_effect_refs=tuple(sorted(effect.effect_id for effect in effects)),
                    durable_count=durable_count,
                    idempotency_keys=tuple(sorted({effect.idempotency_key for effect in effects if effect.idempotency_key})),
                )
            )
        return tuple(sorted(result, key=lambda item: item.group_id))

    @staticmethod
    def _temporal_constraints(
        relations: tuple[ExecutionRelation, ...],
        node_by_id: dict[str, ExecutionNode],
    ) -> tuple[tuple[TemporalConstraint, ...], list[GraphAssemblyWarning]]:
        constraints: list[TemporalConstraint] = []
        warnings: list[GraphAssemblyWarning] = []
        causal_kinds = {
            RelationKind.PARENT_OF,
            RelationKind.INVOKES,
            RelationKind.SPAWNS,
            RelationKind.SCHEDULES,
            RelationKind.PUBLISHES,
            RelationKind.DELIVERS,
            RelationKind.CONSUMES,
            RelationKind.RETRIES,
            RelationKind.CONTAINS,
            RelationKind.WRITES_TO,
            RelationKind.READS_FROM,
        }
        for relation in relations:
            source = node_by_id.get(relation.source_ref)
            target = node_by_id.get(relation.target_ref)
            if not source or not target:
                continue
            source_start = source.timing.effective_timestamp
            source_end = (source.end_time or source.timing).effective_timestamp
            target_start = target.timing.effective_timestamp
            if relation.kind in causal_kinds and target_start < source_start:
                kind = TemporalRelationKind.TIMESTAMP_CONFLICT
                confidence = Confidence(score=1.0, rationale="causal relation conflicts with normalized timestamps")
                rationale = "Target timestamp precedes the source despite a causal relationship."
                warnings.append(
                    GraphAssemblyWarning(
                        warning_id=_stable_id("warning.timestamp-conflict", relation.relation_id),
                        code="timestamp_conflict",
                        message=rationale,
                        node_refs=(source.node_id, target.node_id),
                        relation_refs=(relation.relation_id,),
                    )
                )
            elif source_end <= target_start:
                kind = TemporalRelationKind.HAPPENS_BEFORE
                confidence = Confidence(score=1.0, rationale="non-overlapping normalized intervals")
                rationale = "Source completes before target begins."
            elif source_start <= target_start:
                kind = TemporalRelationKind.OVERLAPS
                confidence = Confidence(score=0.95, rationale="normalized intervals overlap")
                rationale = "Source and target intervals overlap."
            else:
                kind = TemporalRelationKind.ORDERING_UNKNOWN
                confidence = Confidence(score=0.5, rationale="available timestamps do not establish order")
                rationale = "Ordering cannot be established from the available evidence."
            constraints.append(
                TemporalConstraint(
                    constraint_id=_stable_id("temporal-constraint", relation.relation_id),
                    source_node_ref=source.node_id,
                    target_node_ref=target.node_id,
                    kind=kind,
                    derivation=(
                        DerivationKind.DETERMINISTIC
                        if relation.derivation is not DerivationKind.HEURISTIC
                        else DerivationKind.HEURISTIC
                    ),
                    confidence=confidence,
                    rationale=rationale,
                    relation_ref=relation.relation_id,
                )
            )
        return tuple(sorted(constraints, key=lambda item: item.constraint_id)), warnings

    @staticmethod
    def _disconnected_components(
        nodes: tuple[ExecutionNode, ...],
        relations: tuple[ExecutionRelation, ...],
    ) -> tuple[tuple[str, ...], ...]:
        node_ids = {node.node_id for node in nodes}
        adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
        for relation in relations:
            if relation.source_ref in node_ids and relation.target_ref in node_ids:
                adjacency[relation.source_ref].add(relation.target_ref)
                adjacency[relation.target_ref].add(relation.source_ref)
        unseen = set(node_ids)
        components: list[tuple[str, ...]] = []
        while unseen:
            root = min(unseen)
            queue = deque([root])
            unseen.remove(root)
            members: list[str] = []
            while queue:
                current = queue.popleft()
                members.append(current)
                for neighbor in sorted(adjacency[current]):
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        queue.append(neighbor)
            components.append(tuple(sorted(members)))
        return tuple(sorted(components, key=lambda item: item[0] if item else ""))


def _node_sort_key(node: ExecutionNode) -> tuple[datetime, str]:
    return node.timing.effective_timestamp, node.node_id


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(item) for item in parts)
    return f"{prefix}.{hashlib.sha256(payload.encode()).hexdigest()[:16]}"
