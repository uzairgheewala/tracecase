from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any

from tracecase_graph import AssembledExecutionGraph, ContextFlowStatus
from tracecase_model import (
    Effect,
    EvidenceClassification,
    ExecutionCase,
    ExecutionNode,
    PropagationContract,
    RelationKind,
    SensitivityLabel,
)
from tracecase_model.execution import EffectDurability, NodeKind

from .models import (
    EvaluationTraceStep,
    EvaluatorKind,
    InvariantDefinition,
    InvariantEvaluationReport,
    InvariantResult,
    InvariantStatus,
    ScopeKind,
)
from .registry import InvariantRegistry


Handler = Callable[[InvariantDefinition, ExecutionCase, AssembledExecutionGraph], InvariantResult]


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]
    return f"{prefix}.{digest}"


def _trace(step: str, outcome: str, message: str, refs: tuple[str, ...] = (), **attrs: Any) -> EvaluationTraceStep:
    return EvaluationTraceStep(
        step_id=_stable_id("evaluation-step", step, outcome, message, *refs),
        operation=step,
        outcome=outcome,
        message=message,
        input_refs=refs,
        attributes=attrs,
    )


def _evidence_for_nodes(case: ExecutionCase, node_refs: set[str]) -> tuple[str, ...]:
    node_by_id = {node.node_id: node for node in case.evidence.execution.nodes}
    return tuple(
        sorted(
            {
                observation_ref
                for node_id in node_refs
                if node_id in node_by_id
                for observation_ref in node_by_id[node_id].observation_refs
            }
        )
    )


def _base_result(
    definition: InvariantDefinition,
    case: ExecutionCase,
    *,
    status: InvariantStatus,
    explanation: str,
    scope_ref: str | None = None,
    evidence_refs: tuple[str, ...] = (),
    node_refs: tuple[str, ...] = (),
    relation_refs: tuple[str, ...] = (),
    context_refs: tuple[str, ...] = (),
    effect_refs: tuple[str, ...] = (),
    counterexample_refs: tuple[str, ...] = (),
    missing_evidence: tuple[str, ...] = (),
    trace: tuple[EvaluationTraceStep, ...] = (),
    confidence: float | None = None,
    attributes: dict[str, Any] | None = None,
) -> InvariantResult:
    from tracecase_model import Confidence

    classification = (
        EvidenceClassification.UNKNOWN
        if status is InvariantStatus.INCONCLUSIVE
        else EvidenceClassification.CONTRADICTED
        if status is InvariantStatus.CONTRADICTED
        else EvidenceClassification.DETERMINISTIC
    )
    score = confidence if confidence is not None else (0.5 if status is InvariantStatus.INCONCLUSIVE else 1.0)
    resolved_scope = scope_ref or case.specification.case_id
    return InvariantResult(
        result_id=_stable_id("invariant-result", definition.invariant_id, resolved_scope),
        invariant_ref=definition.invariant_id,
        invariant_version=definition.version,
        scope_kind=definition.scope.kind,
        scope_ref=resolved_scope,
        status=status,
        severity=definition.severity,
        evidence_classification=classification,
        evidence_refs=evidence_refs,
        node_refs=node_refs,
        relation_refs=relation_refs,
        context_refs=context_refs,
        effect_refs=effect_refs,
        counterexample_refs=counterexample_refs,
        missing_evidence=missing_evidence,
        confidence=Confidence(score=score, rationale="deterministic invariant evaluation"),
        explanation=explanation,
        evaluation_trace=trace,
        attributes=attributes or {},
    )


class InvariantRuntime:
    def __init__(self, registry: InvariantRegistry | None = None) -> None:
        self.registry = registry or InvariantRegistry()
        self.handlers: dict[EvaluatorKind, Handler] = {
            EvaluatorKind.CONTEXT_REQUIRED_CONTINUITY: self._context_required_continuity,
            EvaluatorKind.CONTEXT_FORBIDDEN_PROPAGATION: self._context_forbidden_propagation,
            EvaluatorKind.IDENTITY_EXECUTION_ISOLATION: self._identity_execution_isolation,
            EvaluatorKind.IDENTITY_WORKFLOW_CORRELATABLE: self._identity_workflow_correlatable,
            EvaluatorKind.EFFECT_AT_MOST_ONCE: self._effect_at_most_once,
            EvaluatorKind.EFFECT_REQUIRED_EVENTUALITY: self._effect_required_eventuality,
            EvaluatorKind.ORDERING_READ_AFTER_VISIBILITY: self._ordering_read_after_visibility,
            EvaluatorKind.CONSISTENCY_REQUIRED_FRESHNESS: self._consistency_required_freshness,
            EvaluatorKind.CONTRACT_SCHEMA_COMPATIBLE: self._contract_schema_compatible,
            EvaluatorKind.RESOURCE_CAPACITY_BOUNDED: self._resource_capacity_bounded,
            EvaluatorKind.PERFORMANCE_WORK_AMPLIFICATION: self._performance_work_amplification,
            EvaluatorKind.OBSERVABILITY_REQUIRED_LINKAGE: self._observability_required_linkage,
            EvaluatorKind.PRIVACY_PROHIBITED_CAPTURE: self._privacy_prohibited_capture,
        }

    def evaluate(
        self,
        case: ExecutionCase,
        graph: AssembledExecutionGraph,
        *,
        invariant_ids: tuple[str, ...] | None = None,
    ) -> InvariantEvaluationReport:
        definitions = self.registry.select(invariant_ids)
        results: list[InvariantResult] = []
        for definition in definitions:
            try:
                missing = self._missing_evidence(definition, case)
                if missing:
                    results.append(
                        _base_result(
                            definition,
                            case,
                            status=InvariantStatus.INCONCLUSIVE,
                            explanation="The invariant cannot be evaluated because required evidence is absent.",
                            missing_evidence=tuple(missing),
                            trace=(_trace("evidence-preflight", "missing", ", ".join(missing)),),
                        )
                    )
                    continue
                results.append(self.handlers[definition.evaluator_kind](definition, case, graph))
            except Exception as exc:  # The report must preserve failures without aborting sibling checks.
                results.append(
                    _base_result(
                        definition,
                        case,
                        status=InvariantStatus.EVALUATION_ERROR,
                        explanation=f"Invariant evaluator failed: {type(exc).__name__}: {exc}",
                        confidence=0.0,
                        trace=(_trace("evaluation", "error", str(exc)),),
                    )
                )
        summary = {status: sum(item.status is status for item in results) for status in InvariantStatus}
        return InvariantEvaluationReport(
            report_id=_stable_id("invariant-report", case.specification.case_id, graph.graph_id, *(item.invariant_id for item in definitions)),
            case_id=case.specification.case_id,
            execution_id=case.evidence.execution.execution_id,
            graph_id=graph.graph_id,
            definition_refs=tuple(item.invariant_id for item in definitions),
            results=tuple(results),
            summary=summary,
        )

    @staticmethod
    def _missing_evidence(definition: InvariantDefinition, case: ExecutionCase) -> list[str]:
        execution = case.evidence.execution
        counts = {
            "nodes": len(execution.nodes),
            "relations": len(execution.relations),
            "contexts": len(execution.contexts),
            "effects": len(execution.effects),
            "state_facts": len(execution.state_facts),
            "observations": len(execution.observations),
        }
        return [
            item.kind
            for item in definition.required_evidence
            if counts.get(item.kind, 0) < item.minimum_count
        ]

    @staticmethod
    def _context_required_continuity(definition: InvariantDefinition, case: ExecutionCase, graph: AssembledExecutionGraph) -> InvariantResult:
        execution = case.evidence.execution
        node_by_id = {node.node_id: node for node in execution.nodes}
        contexts_by_name: dict[str, list] = defaultdict(list)
        for context in execution.contexts:
            if context.propagation_contract in {PropagationContract.REQUIRED, PropagationContract.TRANSLATED}:
                contexts_by_name[context.qualified_name].append(context)
        if not contexts_by_name:
            return _base_result(definition, case, status=InvariantStatus.NOT_APPLICABLE, explanation="No required or translated context contracts are present.")

        violations: list[str] = []
        context_refs: set[str] = set()
        node_refs: set[str] = set()
        details: list[dict[str, Any]] = []
        for name, contexts in sorted(contexts_by_name.items()):
            source = next((item for item in contexts if item.origin_node_ref == item.observed_at_node_ref), contexts[0])
            context_refs.update(item.context_id for item in contexts)
            if source.origin_node_ref:
                node_refs.add(source.origin_node_ref)
            extension = source.extensions.get("tracecase.scenario", {})
            required_roles = set(extension.get("required_role_refs", [])) if isinstance(extension, dict) else set()
            observed_by_role = {
                node_by_id[item.observed_at_node_ref].attributes.get("scenario_role_ref")
                for item in contexts
                if item.observed_at_node_ref in node_by_id
            }
            missing_roles = sorted(required_roles - observed_by_role)
            mismatches = [item for item in contexts if item.context_id != source.context_id and item.value != source.value]
            if missing_roles or mismatches:
                violations.append(name)
                node_refs.update(item.observed_at_node_ref for item in mismatches if item.observed_at_node_ref)
                node_refs.update(
                    node.node_id
                    for node in execution.nodes
                    if node.attributes.get("scenario_role_ref") in missing_roles
                )
                details.append({
                    "qualified_name": name,
                    "missing_roles": missing_roles,
                    "mutated_context_refs": [item.context_id for item in mismatches],
                })
        if violations:
            evidence_refs = _evidence_for_nodes(case, node_refs)
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation=f"Required context continuity failed for {', '.join(violations)}.",
                evidence_refs=evidence_refs,
                node_refs=tuple(sorted(node_refs)),
                context_refs=tuple(sorted(context_refs)),
                counterexample_refs=tuple(sorted(context_refs)),
                trace=(_trace("context-continuity", "violated", "Missing or mutated required context was found.", tuple(sorted(context_refs))),),
                attributes={"violations": details},
            )
        flow_statuses = Counter(flow.status.value for flow in graph.context_flows if flow.qualified_name in contexts_by_name)
        return _base_result(
            definition,
            case,
            status=InvariantStatus.SATISFIED,
            explanation="All required context fields remain present and equivalent at declared destinations.",
            context_refs=tuple(sorted(context_refs)),
            node_refs=tuple(sorted(node_refs)),
            trace=(_trace("context-continuity", "satisfied", "All declared required destinations were observed."),),
            attributes={"flow_statuses": dict(flow_statuses)},
        )

    @staticmethod
    def _context_forbidden_propagation(definition: InvariantDefinition, case: ExecutionCase, _graph: AssembledExecutionGraph) -> InvariantResult:
        forbidden = [item for item in case.evidence.execution.contexts if item.propagation_contract is PropagationContract.FORBIDDEN]
        if not forbidden:
            return _base_result(definition, case, status=InvariantStatus.NOT_APPLICABLE, explanation="No forbidden context contracts are present.")
        leaked = [item for item in forbidden if item.observed_at_node_ref and item.observed_at_node_ref != item.origin_node_ref]
        status = InvariantStatus.VIOLATED if leaked else InvariantStatus.SATISFIED
        refs = tuple(sorted(item.context_id for item in leaked or forbidden))
        return _base_result(
            definition,
            case,
            status=status,
            explanation="Forbidden context crossed its origin boundary." if leaked else "Forbidden context remained confined to its origin scope.",
            context_refs=refs,
            node_refs=tuple(sorted({item.observed_at_node_ref for item in leaked if item.observed_at_node_ref})),
            counterexample_refs=tuple(sorted(item.context_id for item in leaked)),
            trace=(_trace("forbidden-context", status.value, "Evaluated forbidden context destinations.", refs),),
        )

    @staticmethod
    def _identity_execution_isolation(definition: InvariantDefinition, case: ExecutionCase, _graph: AssembledExecutionGraph) -> InvariantResult:
        nodes = case.evidence.execution.nodes
        collision_nodes = [node for node in nodes if node.attributes.get("identity_collision")]
        workflow_tenants: dict[str, set[str]] = defaultdict(set)
        for node in nodes:
            if node.identities.workflow_id and node.identities.tenant_id:
                workflow_tenants[node.identities.workflow_id].add(node.identities.tenant_id)
        mixed = {workflow: tenants for workflow, tenants in workflow_tenants.items() if len(tenants) > 1}
        if collision_nodes or mixed:
            refs = tuple(sorted(node.node_id for node in collision_nodes))
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation="Execution identity collision or cross-tenant identity mixing was detected.",
                node_refs=refs,
                evidence_refs=_evidence_for_nodes(case, set(refs)),
                counterexample_refs=refs,
                attributes={"mixed_workflow_tenants": {key: sorted(value) for key, value in mixed.items()}},
                trace=(_trace("identity-isolation", "violated", "Collision markers or mixed tenant identities were found.", refs),),
            )
        return _base_result(definition, case, status=InvariantStatus.SATISFIED, explanation="No execution identity collision or cross-tenant mixing was detected.")

    @staticmethod
    def _identity_workflow_correlatable(definition: InvariantDefinition, case: ExecutionCase, graph: AssembledExecutionGraph) -> InvariantResult:
        nodes = case.evidence.execution.nodes
        missing = [node.node_id for node in nodes if not node.identities.workflow_id]
        workflows = {node.identities.workflow_id for node in nodes if node.identities.workflow_id}
        if missing:
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation="One or more execution nodes lack workflow identity.",
                node_refs=tuple(sorted(missing)),
                evidence_refs=_evidence_for_nodes(case, set(missing)),
                counterexample_refs=tuple(sorted(missing)),
            )
        if len(workflows) > 1 and case.specification.category.value not in {"observed_composite", "comparison"}:
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation="A single-case execution contains multiple unlinked workflow identities.",
                node_refs=tuple(node.node_id for node in nodes),
                attributes={"workflow_ids": sorted(workflows)},
            )
        return _base_result(
            definition,
            case,
            status=InvariantStatus.SATISFIED,
            explanation="All execution nodes retain a consistent workflow identity.",
            attributes={"workflow_ids": sorted(workflows), "connected_components": len(graph.report.disconnected_components)},
        )

    @staticmethod
    def _effect_at_most_once(definition: InvariantDefinition, case: ExecutionCase, graph: AssembledExecutionGraph) -> InvariantResult:
        effect_by_id = {effect.effect_id: effect for effect in case.evidence.execution.effects}
        violations: list[dict[str, Any]] = []
        offending: set[str] = set()
        for group in graph.effect_groups:
            maxima = [
                int(effect_by_id[ref].attributes.get("maximum_durable_count", definition.parameters.get("default_maximum", 1)))
                for ref in group.member_effect_refs
                if ref in effect_by_id
            ]
            maximum = min(maxima) if maxima else int(definition.parameters.get("default_maximum", 1))
            if group.durable_count > maximum:
                offending.update(group.member_effect_refs)
                violations.append({"logical_effect_key": group.logical_effect_key, "durable_count": group.durable_count, "maximum": maximum})
        if violations:
            evidence = tuple(sorted({ref for effect_id in offending for ref in effect_by_id[effect_id].evidence_refs}))
            producers = tuple(sorted({effect_by_id[effect_id].producer_node_ref for effect_id in offending}))
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation="One or more logical effects became durable more times than allowed.",
                effect_refs=tuple(sorted(offending)),
                node_refs=producers,
                evidence_refs=evidence,
                counterexample_refs=tuple(sorted(offending)),
                attributes={"violations": violations},
                trace=(_trace("effect-cardinality", "violated", "Durable count exceeded the declared maximum.", tuple(sorted(offending))),),
            )
        if not graph.effect_groups:
            return _base_result(definition, case, status=InvariantStatus.NOT_APPLICABLE, explanation="No logical effects are present.")
        return _base_result(definition, case, status=InvariantStatus.SATISFIED, explanation="Every logical effect remains within its durable-count bound.")

    @staticmethod
    def _effect_required_eventuality(definition: InvariantDefinition, case: ExecutionCase, _graph: AssembledExecutionGraph) -> InvariantResult:
        extension = case.evidence.execution.extensions.get("tracecase.scenario", {})
        expected = extension.get("expected_effects", []) if isinstance(extension, dict) else []
        if not expected:
            required_present = [effect for effect in case.evidence.execution.effects if effect.attributes.get("required")]
            if not required_present:
                return _base_result(definition, case, status=InvariantStatus.NOT_APPLICABLE, explanation="No required logical effects are declared.")
            expected = [{"logical_effect_key": effect.logical_effect_key, "required": True} for effect in required_present]
        present = {effect.logical_effect_key for effect in case.evidence.execution.effects if effect.durability in {EffectDurability.COMMITTED, EffectDurability.DURABLE}}
        missing = sorted(item["logical_effect_key"] for item in expected if item.get("required", True) and item["logical_effect_key"] not in present)
        if missing:
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation=f"Required logical effects did not become durable: {', '.join(missing)}.",
                missing_evidence=tuple(f"effect:{item}" for item in missing),
                attributes={"missing_logical_effect_keys": missing},
                trace=(_trace("effect-eventuality", "violated", "Required effect key is absent from durable effects."),),
            )
        return _base_result(definition, case, status=InvariantStatus.SATISFIED, explanation="All declared required logical effects became durable.")

    @staticmethod
    def _ordering_read_after_visibility(definition: InvariantDefinition, case: ExecutionCase, _graph: AssembledExecutionGraph) -> InvariantResult:
        nodes = case.evidence.execution.nodes
        producers = [node for node in nodes if node.kind in {NodeKind.TRANSACTION, NodeKind.WRITE}]
        reads = [node for node in nodes if node.kind is NodeKind.READ]
        if not producers or not reads:
            return _base_result(definition, case, status=InvariantStatus.NOT_APPLICABLE, explanation="No producer/read visibility pair is present.")
        violations: list[tuple[str, str]] = []
        for read in reads:
            relevant = max((producer for producer in producers if producer.timing.effective_timestamp <= read.timing.effective_timestamp or producer.kind is NodeKind.TRANSACTION), key=lambda item: item.timing.effective_timestamp, default=None)
            if relevant and read.timing.effective_timestamp < (relevant.end_time or relevant.timing).effective_timestamp:
                violations.append((relevant.node_id, read.node_id))
        if violations:
            refs = tuple(sorted({item for pair in violations for item in pair}))
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation="A dependent read began before the producer's visibility boundary completed.",
                node_refs=refs,
                evidence_refs=_evidence_for_nodes(case, set(refs)),
                counterexample_refs=refs,
                attributes={"violating_pairs": [list(pair) for pair in violations]},
            )
        return _base_result(definition, case, status=InvariantStatus.SATISFIED, explanation="All dependent reads begin after the relevant visibility boundary.")

    @staticmethod
    def _consistency_required_freshness(definition: InvariantDefinition, case: ExecutionCase, _graph: AssembledExecutionGraph) -> InvariantResult:
        relevant = [node for node in case.evidence.execution.nodes if node.kind in {NodeKind.CACHE_READ, NodeKind.READ} or "freshness" in node.attributes or node.attributes.get("stale")]
        if not relevant:
            return _base_result(definition, case, status=InvariantStatus.NOT_APPLICABLE, explanation="No freshness-constrained observation is present.")
        stale = [node for node in relevant if node.attributes.get("stale") or node.status in {"stale", "stale_read"} or node.attributes.get("freshness_violation")]
        refs = tuple(sorted(node.node_id for node in stale))
        return _base_result(
            definition,
            case,
            status=InvariantStatus.VIOLATED if stale else InvariantStatus.SATISFIED,
            explanation="A stale state observation violated the freshness contract." if stale else "No stale state observation was detected.",
            node_refs=refs,
            evidence_refs=_evidence_for_nodes(case, set(refs)),
            counterexample_refs=refs,
        )

    @staticmethod
    def _contract_schema_compatible(definition: InvariantDefinition, case: ExecutionCase, _graph: AssembledExecutionGraph) -> InvariantResult:
        version_nodes = [(node, str(node.attributes["schema_version"])) for node in case.evidence.execution.nodes if "schema_version" in node.attributes]
        if not version_nodes:
            return _base_result(definition, case, status=InvariantStatus.NOT_APPLICABLE, explanation="No producer/consumer schema versions are recorded.")
        versions = {version for _, version in version_nodes}
        refs = tuple(sorted(node.node_id for node, _ in version_nodes))
        if len(versions) > 1:
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation="Collaborating operations report incompatible schema versions.",
                node_refs=refs,
                evidence_refs=_evidence_for_nodes(case, set(refs)),
                counterexample_refs=refs,
                attributes={"versions": sorted(versions)},
            )
        return _base_result(definition, case, status=InvariantStatus.SATISFIED, explanation="Recorded schema versions are compatible.", attributes={"versions": sorted(versions)})

    @staticmethod
    def _resource_capacity_bounded(definition: InvariantDefinition, case: ExecutionCase, _graph: AssembledExecutionGraph) -> InvariantResult:
        exhausted = [node for node in case.evidence.execution.nodes if node.attributes.get("resource_capacity_exhausted") or node.status == "resource_exhausted"]
        refs = tuple(sorted(node.node_id for node in exhausted))
        return _base_result(
            definition,
            case,
            status=InvariantStatus.VIOLATED if exhausted else InvariantStatus.SATISFIED,
            explanation="Resource capacity exhaustion was observed." if exhausted else "No resource capacity exhaustion was observed.",
            node_refs=refs,
            evidence_refs=_evidence_for_nodes(case, set(refs)),
            counterexample_refs=refs,
        )

    @staticmethod
    def _performance_work_amplification(definition: InvariantDefinition, case: ExecutionCase, _graph: AssembledExecutionGraph) -> InvariantResult:
        groups: dict[tuple[str, str], list[ExecutionNode]] = defaultdict(list)
        for node in case.evidence.execution.nodes:
            groups[(node.kind.value, node.operation)].append(node)
        violations: list[dict[str, Any]] = []
        refs: set[str] = set()
        default_maximum = int(definition.parameters.get("default_maximum", 1))
        for (kind, operation), members in groups.items():
            explicitly_amplified = [node for node in members if node.attributes.get("amplification_index") or node.attributes.get("amplified")]
            maximum = max(int(node.attributes.get("maximum_amplification", default_maximum)) for node in members)
            if explicitly_amplified or (len(members) > maximum and not all(node.identities.task_attempt for node in members)):
                refs.update(node.node_id for node in members)
                violations.append({"kind": kind, "operation": operation, "count": len(members), "maximum": maximum})
        if violations:
            ordered_refs = tuple(sorted(refs))
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation="Execution work was amplified beyond the declared semantic bound.",
                node_refs=ordered_refs,
                evidence_refs=_evidence_for_nodes(case, refs),
                counterexample_refs=ordered_refs,
                attributes={"violations": violations},
            )
        return _base_result(definition, case, status=InvariantStatus.SATISFIED, explanation="No prohibited semantic work amplification was detected.")

    @staticmethod
    def _observability_required_linkage(definition: InvariantDefinition, case: ExecutionCase, graph: AssembledExecutionGraph) -> InvariantResult:
        extension = case.evidence.execution.extensions.get("tracecase.scenario", {})
        expected_edges = extension.get("expected_edges", []) if isinstance(extension, dict) else []
        source_relations = [relation for relation in graph.relations if relation.relation_id in set(graph.source_relation_refs)]
        source_pairs = {(relation.source_ref, relation.target_ref, relation.kind.value) for relation in source_relations}
        node_by_role: dict[str, str] = {}
        for node in sorted(
            graph.nodes,
            key=lambda item: (
                item.identities.task_attempt if item.identities.task_attempt is not None else 0,
                item.timing.effective_timestamp,
                item.node_id,
            ),
        ):
            role = node.attributes.get("scenario_role_ref")
            if role and str(role) not in node_by_role:
                node_by_role[str(role)] = node.node_id
        missing: list[dict[str, str]] = []
        for edge in expected_edges:
            source = node_by_role.get(edge.get("source_role_ref"))
            target = node_by_role.get(edge.get("target_role_ref"))
            relation_kind = edge.get("relation_kind")
            if source and target and (source, target, relation_kind) not in source_pairs:
                missing.append({"source_ref": source, "target_ref": target, "relation_kind": relation_kind, "edge_id": edge.get("edge_id", "unknown")})
        # Natural incidents may not carry a scenario contract. A deterministic relation that
        # reconstructs a transport/parent edge absent from source relations is itself a generic
        # witness that source-backed linkage was lost.
        source_semantic_pairs = {(relation.source_ref, relation.target_ref, relation.kind.value) for relation in source_relations}
        for relation in graph.relations:
            if relation.relation_id not in set(graph.derived_relation_refs):
                continue
            if relation.kind not in {RelationKind.DELIVERS, RelationKind.SPAWNS}:
                continue
            source_node = next((node for node in graph.nodes if node.node_id == relation.source_ref), None)
            target_node = next((node for node in graph.nodes if node.node_id == relation.target_ref), None)
            if not source_node or not target_node:
                continue
            propagation_broken = (
                source_node.identities.trace_id != target_node.identities.trace_id
                or not target_node.identities.parent_span_id
            )
            if not propagation_broken:
                continue
            key = (relation.source_ref, relation.target_ref, relation.kind.value)
            if key not in source_semantic_pairs and not any(
                item["source_ref"] == relation.source_ref
                and item["target_ref"] == relation.target_ref
                and item["relation_kind"] == relation.kind.value
                for item in missing
            ):
                missing.append({
                    "source_ref": relation.source_ref,
                    "target_ref": relation.target_ref,
                    "relation_kind": relation.kind.value,
                    "edge_id": relation.relation_id,
                })
        contradiction_observations = [observation for observation in case.evidence.execution.observations if observation.attributes.get("synthetic_contradiction")]
        if contradiction_observations:
            return _base_result(
                definition,
                case,
                status=InvariantStatus.CONTRADICTED,
                explanation="Collected evidence contains an explicit contradiction about execution state.",
                evidence_refs=tuple(sorted(item.observation_id for item in contradiction_observations)),
                counterexample_refs=tuple(sorted(item.observation_id for item in contradiction_observations)),
            )
        if missing:
            nodes = tuple(sorted({item[side] for item in missing for side in ("source_ref", "target_ref")}))
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation="One or more expected causal boundaries lack source-backed linkage.",
                node_refs=nodes,
                counterexample_refs=nodes,
                attributes={"missing_expected_edges": missing},
                trace=(_trace("causal-linkage", "violated", "Expected topology edge is absent from source relations.", nodes),),
            )
        if graph.report.disconnected_components and len(graph.report.disconnected_components) > 1:
            refs = tuple(sorted({item for component in graph.report.disconnected_components for item in component}))
            return _base_result(
                definition,
                case,
                status=InvariantStatus.INCONCLUSIVE,
                explanation="The graph remains disconnected and available evidence cannot establish complete causal linkage.",
                node_refs=refs,
                missing_evidence=("cross-component causal relation",),
                confidence=0.6,
            )
        return _base_result(definition, case, status=InvariantStatus.SATISFIED, explanation="All declared causal boundaries retain source-backed linkage.")

    @staticmethod
    def _privacy_prohibited_capture(definition: InvariantDefinition, case: ExecutionCase, _graph: AssembledExecutionGraph) -> InvariantResult:
        suspicious_keys = {"authorization", "cookie", "set-cookie", "password", "secret", "access_token", "refresh_token"}
        violations: list[dict[str, Any]] = []
        refs: list[str] = []
        for observation in case.evidence.execution.observations:
            keys = {str(key).lower() for key in observation.attributes}
            credential = SensitivityLabel.CREDENTIAL in observation.sensitivity
            matched = sorted(keys & suspicious_keys)
            if credential or matched:
                refs.append(observation.observation_id)
                violations.append({"observation_ref": observation.observation_id, "credential_label": credential, "matched_keys": matched})
        if violations:
            return _base_result(
                definition,
                case,
                status=InvariantStatus.VIOLATED,
                explanation="Prohibited credential-bearing or secret-like fields were captured in evidence.",
                evidence_refs=tuple(sorted(refs)),
                counterexample_refs=tuple(sorted(refs)),
                attributes={"violations": violations},
            )
        return _base_result(definition, case, status=InvariantStatus.SATISFIED, explanation="No prohibited credential-bearing fields were detected in evidence.")
