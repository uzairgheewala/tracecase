from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from tracecase_graph import AssembledExecutionGraph
from tracecase_model import Confidence, EvidenceClassification, ExecutionCase, ExecutionNode
from tracecase_model.execution import EffectDurability

from .models import (
    AlignmentStatus,
    CaseRole,
    ComparisonCaseRef,
    ComparisonDimension,
    ComparisonSummary,
    Divergence,
    DivergenceConsequence,
    DivergenceSeverity,
    NodeAlignment,
    NodeSignature,
    SemanticComparison,
)


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]
    return f"{prefix}.{digest}"


def _normalize_operation(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\b[0-9a-f]{8,}\b", "<id>", value)
    value = re.sub(r"\b\d+\b", "<n>", value)
    value = re.sub(r"\s+", " ", value)
    return value


@dataclass(frozen=True)
class _PreparedCase:
    case: ExecutionCase
    graph: AssembledExecutionGraph
    node_by_id: dict[str, ExecutionNode]
    signature_by_node: dict[str, NodeSignature]
    contexts_by_node: dict[str, dict[str, object]]
    effects_by_node: dict[str, tuple]
    origin_ms: float


class SemanticComparisonEngine:
    def __init__(
        self,
        *,
        minimum_alignment_score: float = 0.55,
        timing_absolute_threshold_ms: float = 25.0,
        timing_ratio_threshold: float = 1.5,
    ) -> None:
        self.minimum_alignment_score = minimum_alignment_score
        self.timing_absolute_threshold_ms = timing_absolute_threshold_ms
        self.timing_ratio_threshold = timing_ratio_threshold

    def compare(
        self,
        baseline_case: ExecutionCase,
        baseline_graph: AssembledExecutionGraph,
        candidate_case: ExecutionCase,
        candidate_graph: AssembledExecutionGraph,
        *,
        baseline_role: CaseRole = CaseRole.BASELINE,
        candidate_role: CaseRole = CaseRole.CANDIDATE,
    ) -> SemanticComparison:
        baseline = self._prepare(baseline_case, baseline_graph)
        candidate = self._prepare(candidate_case, candidate_graph)
        alignments = self._align(baseline, candidate)
        divergences = self._divergences(baseline, candidate, alignments)
        ordered = tuple(sorted(divergences, key=self._divergence_sort_key))
        first = next((item for item in ordered if item.consequential and item.consequence in {DivergenceConsequence.SEMANTIC, DivergenceConsequence.OUTCOME_RELEVANT}), None)
        status_counts = Counter(item.status for item in alignments)
        dimension_counts = Counter(item.dimension for item in ordered)
        summary = ComparisonSummary(
            aligned_nodes=status_counts[AlignmentStatus.ALIGNED],
            baseline_only_nodes=status_counts[AlignmentStatus.BASELINE_ONLY],
            candidate_only_nodes=status_counts[AlignmentStatus.CANDIDATE_ONLY],
            ambiguous_alignments=status_counts[AlignmentStatus.AMBIGUOUS],
            divergence_count=len(ordered),
            consequential_divergence_count=sum(item.consequential for item in ordered),
            by_dimension=dict(dimension_counts),
            first_meaningful_divergence_ref=first.divergence_id if first else None,
        )
        comparison_id = _stable_id(
            "comparison",
            baseline_case.specification.case_id,
            candidate_case.specification.case_id,
            baseline_graph.graph_id,
            candidate_graph.graph_id,
        )
        return SemanticComparison(
            comparison_id=comparison_id,
            baseline=ComparisonCaseRef(role=baseline_role, case_id=baseline_case.specification.case_id, graph_id=baseline_graph.graph_id),
            candidate=ComparisonCaseRef(role=candidate_role, case_id=candidate_case.specification.case_id, graph_id=candidate_graph.graph_id),
            alignments=alignments,
            divergences=ordered,
            first_meaningful_divergence_ref=first.divergence_id if first else None,
            summary=summary,
            configuration={
                "minimum_alignment_score": self.minimum_alignment_score,
                "timing_absolute_threshold_ms": self.timing_absolute_threshold_ms,
                "timing_ratio_threshold": self.timing_ratio_threshold,
            },
            limitations=tuple(sorted({limitation for item in ordered for limitation in item.limitations})),
        )

    @staticmethod
    def _prepare(case: ExecutionCase, graph: AssembledExecutionGraph) -> _PreparedCase:
        component_by_id = {item.component_id: item for item in case.system.components}
        node_by_id = {item.node_id: item for item in graph.nodes}
        signatures: dict[str, NodeSignature] = {}
        for node in graph.nodes:
            component = component_by_id.get(node.component_ref)
            signatures[node.node_id] = NodeSignature(
                node_ref=node.node_id,
                node_kind=node.kind.value,
                normalized_operation=_normalize_operation(node.operation),
                component_kind=component.kind.value if component else "unknown",
                component_role=component.role if component else None,
                topology_role=str(node.attributes.get("scenario_role_ref")) if node.attributes.get("scenario_role_ref") else None,
                logical_operation_id=node.identities.logical_operation_id,
                task_name=str(node.attributes.get("task_name")) if node.attributes.get("task_name") else None,
                stage=int(node.attributes["stage"]) if isinstance(node.attributes.get("stage"), int) else None,
            )
        context_by_id = {item.context_id: item for item in case.evidence.execution.contexts}
        contexts_by_node: dict[str, dict[str, object]] = {}
        for node in graph.nodes:
            contexts_by_node[node.node_id] = {
                context_by_id[ref].qualified_name: context_by_id[ref].value
                for ref in node.context_refs
                if ref in context_by_id
            }
        effects_by_node: dict[str, list] = defaultdict(list)
        for effect in case.evidence.execution.effects:
            effects_by_node[effect.producer_node_ref].append(effect)
        origin = min(node.timing.effective_timestamp for node in graph.nodes) if graph.nodes else case.specification.created_at
        return _PreparedCase(
            case=case,
            graph=graph,
            node_by_id=node_by_id,
            signature_by_node=signatures,
            contexts_by_node=contexts_by_node,
            effects_by_node={key: tuple(value) for key, value in effects_by_node.items()},
            origin_ms=origin.timestamp() * 1000,
        )

    def _align(self, baseline: _PreparedCase, candidate: _PreparedCase) -> tuple[NodeAlignment, ...]:
        remaining_baseline = set(baseline.node_by_id)
        remaining_candidate = set(candidate.node_by_id)
        alignments: list[NodeAlignment] = []

        baseline_roles: dict[str, list[str]] = defaultdict(list)
        candidate_roles: dict[str, list[str]] = defaultdict(list)
        for node_id, signature in baseline.signature_by_node.items():
            if signature.topology_role:
                baseline_roles[signature.topology_role].append(node_id)
        for node_id, signature in candidate.signature_by_node.items():
            if signature.topology_role:
                candidate_roles[signature.topology_role].append(node_id)
        for role in sorted(set(baseline_roles) & set(candidate_roles)):
            left_members = sorted(
                baseline_roles[role],
                key=lambda node_id: (
                    baseline.node_by_id[node_id].identities.task_attempt
                    if baseline.node_by_id[node_id].identities.task_attempt is not None
                    else 0,
                    baseline.node_by_id[node_id].timing.effective_timestamp,
                    node_id,
                ),
            )
            right_members = sorted(
                candidate_roles[role],
                key=lambda node_id: (
                    candidate.node_by_id[node_id].identities.task_attempt
                    if candidate.node_by_id[node_id].identities.task_attempt is not None
                    else 0,
                    candidate.node_by_id[node_id].timing.effective_timestamp,
                    node_id,
                ),
            )
            for left, right in zip(left_members, right_members):
                alignments.append(self._alignment(baseline, candidate, left, right, 1.0, ("same topology role and ordinal attempt",)))
                remaining_baseline.remove(left)
                remaining_candidate.remove(right)

        candidates: list[tuple[float, str, str, tuple[str, ...]]] = []
        for left in remaining_baseline:
            for right in remaining_candidate:
                score, reasons = self._score(baseline.signature_by_node[left], candidate.signature_by_node[right])
                if score >= self.minimum_alignment_score:
                    candidates.append((score, left, right, reasons))
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        for score, left, right, reasons in candidates:
            if left not in remaining_baseline or right not in remaining_candidate:
                continue
            alternative_rights = [item[2] for item in candidates if item[1] == left and item[2] in remaining_candidate and abs(item[0] - score) < 0.03]
            if len(alternative_rights) > 1:
                alignments.append(
                    NodeAlignment(
                        alignment_id=_stable_id("alignment.ambiguous", left, *sorted(alternative_rights)),
                        baseline_node_ref=left,
                        status=AlignmentStatus.AMBIGUOUS,
                        score=score,
                        confidence=Confidence(score=max(0.0, score - 0.2), rationale="multiple candidate nodes have near-equal semantic scores"),
                        reasons=reasons,
                        baseline_signature=baseline.signature_by_node[left],
                        ambiguous_candidate_refs=tuple(sorted(alternative_rights)),
                    )
                )
                remaining_baseline.remove(left)
                continue
            alignments.append(self._alignment(baseline, candidate, left, right, score, reasons))
            remaining_baseline.remove(left)
            remaining_candidate.remove(right)

        for left in sorted(remaining_baseline):
            alignments.append(
                NodeAlignment(
                    alignment_id=_stable_id("alignment.baseline-only", left),
                    baseline_node_ref=left,
                    status=AlignmentStatus.BASELINE_ONLY,
                    score=0.0,
                    confidence=Confidence(score=1.0, rationale="no candidate exceeded the alignment threshold"),
                    baseline_signature=baseline.signature_by_node[left],
                )
            )
        for right in sorted(remaining_candidate):
            alignments.append(
                NodeAlignment(
                    alignment_id=_stable_id("alignment.candidate-only", right),
                    candidate_node_ref=right,
                    status=AlignmentStatus.CANDIDATE_ONLY,
                    score=0.0,
                    confidence=Confidence(score=1.0, rationale="no baseline node exceeded the alignment threshold"),
                    candidate_signature=candidate.signature_by_node[right],
                )
            )
        return tuple(sorted(alignments, key=lambda item: item.alignment_id))

    @staticmethod
    def _score(left: NodeSignature, right: NodeSignature) -> tuple[float, tuple[str, ...]]:
        weighted = 0.0
        possible = 0.0
        reasons: list[str] = []
        checks = (
            (left.node_kind == right.node_kind, 4.0, "same node kind"),
            (left.normalized_operation == right.normalized_operation, 6.0, "same normalized operation"),
            (left.component_kind == right.component_kind, 3.0, "same component kind"),
            (bool(left.component_role and left.component_role == right.component_role), 1.5, "same component role"),
            (bool(left.logical_operation_id and left.logical_operation_id == right.logical_operation_id), 2.0, "same logical operation identity"),
            (bool(left.task_name and left.task_name == right.task_name), 2.0, "same task name"),
            (left.stage is not None and left.stage == right.stage, 1.0, "same topology stage"),
        )
        for matched, weight, reason in checks:
            possible += weight
            if matched:
                weighted += weight
                reasons.append(reason)
        return weighted / possible, tuple(reasons)

    @staticmethod
    def _alignment(baseline: _PreparedCase, candidate: _PreparedCase, left: str, right: str, score: float, reasons: tuple[str, ...]) -> NodeAlignment:
        return NodeAlignment(
            alignment_id=_stable_id("alignment", left, right),
            baseline_node_ref=left,
            candidate_node_ref=right,
            status=AlignmentStatus.ALIGNED,
            score=score,
            confidence=Confidence(score=score, rationale="weighted semantic signature alignment"),
            reasons=reasons,
            baseline_signature=baseline.signature_by_node[left],
            candidate_signature=candidate.signature_by_node[right],
        )

    def _divergences(self, baseline: _PreparedCase, candidate: _PreparedCase, alignments: tuple[NodeAlignment, ...]) -> list[Divergence]:
        divergences: list[Divergence] = []
        for alignment in alignments:
            if alignment.status is AlignmentStatus.BASELINE_ONLY:
                node = baseline.node_by_id[alignment.baseline_node_ref]
                divergences.append(self._structural_divergence(alignment, node, None, baseline, candidate))
                continue
            if alignment.status is AlignmentStatus.CANDIDATE_ONLY:
                node = candidate.node_by_id[alignment.candidate_node_ref]
                divergences.append(self._structural_divergence(alignment, None, node, baseline, candidate))
                continue
            if alignment.status is AlignmentStatus.AMBIGUOUS:
                divergences.append(
                    Divergence(
                        divergence_id=_stable_id("divergence.ambiguous", alignment.alignment_id),
                        dimension=ComparisonDimension.STRUCTURE,
                        classification="alignment.ambiguous",
                        title="Operation alignment is ambiguous",
                        summary="Several candidate operations are semantically indistinguishable with available evidence.",
                        severity=DivergenceSeverity.LOW,
                        consequence=DivergenceConsequence.OBSERVATIONAL,
                        evidence_classification=EvidenceClassification.UNKNOWN,
                        confidence=alignment.confidence,
                        alignment_ref=alignment.alignment_id,
                        baseline_refs=((alignment.baseline_node_ref,) if alignment.baseline_node_ref else ()),
                        candidate_refs=alignment.ambiguous_candidate_refs,
                        consequential=False,
                        limitations=("A stronger domain identity or ancestry signature is required for a unique alignment.",),
                    )
                )
                continue
            left = baseline.node_by_id[alignment.baseline_node_ref]
            right = candidate.node_by_id[alignment.candidate_node_ref]
            divergences.extend(self._aligned_divergences(alignment, left, right, baseline, candidate))
        divergences.extend(self._global_effect_divergences(baseline, candidate))
        return self._deduplicate(divergences)

    def _aligned_divergences(self, alignment: NodeAlignment, left: ExecutionNode, right: ExecutionNode, baseline: _PreparedCase, candidate: _PreparedCase) -> list[Divergence]:
        result: list[Divergence] = []
        rank = min(self._offset_ms(left, baseline), self._offset_ms(right, candidate))
        if left.status != right.status:
            result.append(
                self._divergence(
                    alignment,
                    ComparisonDimension.ERROR,
                    "status.changed",
                    "Operation status changed",
                    f"{left.operation} changed from {left.status!r} to {right.status!r}.",
                    DivergenceSeverity.HIGH if right.status not in {"ok", "committed", "completed"} else DivergenceSeverity.MEDIUM,
                    DivergenceConsequence.OUTCOME_RELEVANT,
                    baseline,
                    candidate,
                    left,
                    right,
                    rank,
                    attributes={"baseline_status": left.status, "candidate_status": right.status},
                )
            )
        left_context = baseline.contexts_by_node[left.node_id]
        right_context = candidate.contexts_by_node[right.node_id]
        missing = sorted(set(left_context) - set(right_context))
        added = sorted(set(right_context) - set(left_context))
        mutated = sorted(key for key in set(left_context) & set(right_context) if left_context[key] != right_context[key])
        if missing or added or mutated:
            result.append(
                self._divergence(
                    alignment,
                    ComparisonDimension.CONTEXT,
                    "context.changed",
                    "Execution context diverged",
                    f"Context differs at {left.operation}: missing={missing}, added={added}, mutated={mutated}.",
                    DivergenceSeverity.HIGH if missing or mutated else DivergenceSeverity.MEDIUM,
                    DivergenceConsequence.OUTCOME_RELEVANT if missing or mutated else DivergenceConsequence.SEMANTIC,
                    baseline,
                    candidate,
                    left,
                    right,
                    rank,
                    attributes={"missing": missing, "added": added, "mutated": mutated},
                )
            )
        identity_fields = ("tenant_id", "principal_id", "idempotency_key", "task_attempt", "message_id")
        identity_changes = {
            field: [getattr(left.identities, field), getattr(right.identities, field)]
            for field in identity_fields
            if getattr(left.identities, field) != getattr(right.identities, field)
            and not (field == "message_id" and left.identities.message_id and right.identities.message_id)
        }
        if identity_changes:
            result.append(
                self._divergence(
                    alignment,
                    ComparisonDimension.IDENTITY,
                    "identity.changed",
                    "Execution identity changed",
                    f"Identity dimensions changed at {left.operation}: {', '.join(identity_changes)}.",
                    DivergenceSeverity.HIGH if "tenant_id" in identity_changes else DivergenceSeverity.MEDIUM,
                    DivergenceConsequence.OUTCOME_RELEVANT if "tenant_id" in identity_changes else DivergenceConsequence.SEMANTIC,
                    baseline,
                    candidate,
                    left,
                    right,
                    rank,
                    attributes={"changes": identity_changes},
                )
            )
        left_duration = self._duration_ms(left)
        right_duration = self._duration_ms(right)
        absolute_delta = abs(right_duration - left_duration)
        ratio = max(left_duration, right_duration) / max(1.0, min(left_duration, right_duration))
        if absolute_delta >= self.timing_absolute_threshold_ms and ratio >= self.timing_ratio_threshold:
            result.append(
                self._divergence(
                    alignment,
                    ComparisonDimension.TIMING,
                    "timing.duration-regression",
                    "Operation duration diverged",
                    f"Duration changed from {left_duration:.1f} ms to {right_duration:.1f} ms.",
                    DivergenceSeverity.MEDIUM,
                    DivergenceConsequence.SEMANTIC,
                    baseline,
                    candidate,
                    left,
                    right,
                    rank,
                    attributes={"baseline_ms": left_duration, "candidate_ms": right_duration, "ratio": ratio},
                )
            )
        left_observations = set(left.observation_refs)
        right_observations = set(right.observation_refs)
        if bool(left_observations) != bool(right_observations):
            result.append(
                self._divergence(
                    alignment,
                    ComparisonDimension.EVIDENCE,
                    "evidence.node-coverage-changed",
                    "Node evidence coverage changed",
                    "One execution contains source observations for this operation while the other does not.",
                    DivergenceSeverity.LOW,
                    DivergenceConsequence.OBSERVATIONAL,
                    baseline,
                    candidate,
                    left,
                    right,
                    rank,
                    consequential=False,
                )
            )
        return result

    def _structural_divergence(self, alignment: NodeAlignment, left: ExecutionNode | None, right: ExecutionNode | None, baseline: _PreparedCase, candidate: _PreparedCase) -> Divergence:
        node = left or right
        assert node is not None
        candidate_only = right is not None
        role = "candidate" if candidate_only else "baseline"
        rank = self._offset_ms(node, candidate if candidate_only else baseline)
        is_retry = node.identities.task_attempt is not None and node.identities.task_attempt > 1
        return Divergence(
            divergence_id=_stable_id("divergence.structure", alignment.alignment_id),
            dimension=ComparisonDimension.STRUCTURE,
            classification="structure.additional-operation" if candidate_only else "structure.missing-operation",
            title="Additional operation" if candidate_only else "Missing operation",
            summary=f"{node.operation} appears only in the {role} execution." + (" It is a later task attempt." if is_retry else ""),
            severity=DivergenceSeverity.HIGH if is_retry else DivergenceSeverity.MEDIUM,
            consequence=DivergenceConsequence.OUTCOME_RELEVANT if is_retry else DivergenceConsequence.SEMANTIC,
            evidence_classification=EvidenceClassification.DETERMINISTIC,
            confidence=alignment.confidence,
            alignment_ref=alignment.alignment_id,
            baseline_refs=((node.node_id,) if left else ()),
            candidate_refs=((node.node_id,) if right else ()),
            baseline_evidence_refs=(left.observation_refs if left else ()),
            candidate_evidence_refs=(right.observation_refs if right else ()),
            temporal_rank_ms=rank,
            attributes={"task_attempt": node.identities.task_attempt, "operation": node.operation},
        )

    def _global_effect_divergences(self, baseline: _PreparedCase, candidate: _PreparedCase) -> list[Divergence]:
        def summarize(prepared: _PreparedCase) -> dict[str, dict[str, object]]:
            groups: dict[str, list] = defaultdict(list)
            for effect in prepared.case.evidence.execution.effects:
                groups[effect.logical_effect_key].append(effect)
            return {
                key: {
                    "effects": tuple(items),
                    "durable": sum(item.durability in {EffectDurability.COMMITTED, EffectDurability.DURABLE} for item in items),
                }
                for key, items in groups.items()
            }
        left_groups = summarize(baseline)
        right_groups = summarize(candidate)
        result: list[Divergence] = []
        for key in sorted(set(left_groups) | set(right_groups)):
            left = left_groups.get(key, {"effects": (), "durable": 0})
            right = right_groups.get(key, {"effects": (), "durable": 0})
            if left["durable"] == right["durable"]:
                continue
            left_effects = tuple(item.effect_id for item in left["effects"])
            right_effects = tuple(item.effect_id for item in right["effects"])
            candidate_nodes = [item.producer_node_ref for item in right["effects"]]
            rank = min((self._offset_ms(candidate.node_by_id[node_id], candidate) for node_id in candidate_nodes if node_id in candidate.node_by_id), default=0.0)
            result.append(
                Divergence(
                    divergence_id=_stable_id("divergence.effect", key, str(left["durable"]), str(right["durable"])),
                    dimension=ComparisonDimension.EFFECT,
                    classification="effect.durable-count-changed",
                    title="Durable effect count changed",
                    summary=f"Logical effect {key!r} changed from {left['durable']} to {right['durable']} durable occurrence(s).",
                    severity=DivergenceSeverity.CRITICAL if right["durable"] > 1 else DivergenceSeverity.HIGH,
                    consequence=DivergenceConsequence.OUTCOME_RELEVANT,
                    evidence_classification=EvidenceClassification.DETERMINISTIC,
                    confidence=Confidence(score=1.0, rationale="canonical effects share a logical_effect_key"),
                    baseline_refs=left_effects,
                    candidate_refs=right_effects,
                    baseline_evidence_refs=tuple(sorted({ref for item in left["effects"] for ref in item.evidence_refs})),
                    candidate_evidence_refs=tuple(sorted({ref for item in right["effects"] for ref in item.evidence_refs})),
                    temporal_rank_ms=rank,
                    attributes={"logical_effect_key": key, "baseline_durable": left["durable"], "candidate_durable": right["durable"]},
                )
            )
        return result

    @staticmethod
    def _divergence(
        alignment: NodeAlignment,
        dimension: ComparisonDimension,
        classification: str,
        title: str,
        summary: str,
        severity: DivergenceSeverity,
        consequence: DivergenceConsequence,
        baseline: _PreparedCase,
        candidate: _PreparedCase,
        left: ExecutionNode,
        right: ExecutionNode,
        rank: float,
        *,
        consequential: bool = True,
        attributes: dict[str, object] | None = None,
    ) -> Divergence:
        return Divergence(
            divergence_id=_stable_id("divergence", alignment.alignment_id, classification),
            dimension=dimension,
            classification=classification,
            title=title,
            summary=summary,
            severity=severity,
            consequence=consequence,
            evidence_classification=EvidenceClassification.DETERMINISTIC,
            confidence=alignment.confidence,
            alignment_ref=alignment.alignment_id,
            baseline_refs=(left.node_id,),
            candidate_refs=(right.node_id,),
            baseline_evidence_refs=left.observation_refs,
            candidate_evidence_refs=right.observation_refs,
            temporal_rank_ms=rank,
            consequential=consequential,
            attributes=attributes or {},
        )

    @staticmethod
    def _duration_ms(node: ExecutionNode) -> float:
        end = (node.end_time or node.timing).effective_timestamp
        return max(0.0, (end - node.timing.effective_timestamp).total_seconds() * 1000)

    @staticmethod
    def _offset_ms(node: ExecutionNode, prepared: _PreparedCase) -> float:
        return node.timing.effective_timestamp.timestamp() * 1000 - prepared.origin_ms

    @staticmethod
    def _divergence_sort_key(item: Divergence) -> tuple[float, int, str]:
        severity_rank = {
            DivergenceSeverity.CRITICAL: 0,
            DivergenceSeverity.HIGH: 1,
            DivergenceSeverity.MEDIUM: 2,
            DivergenceSeverity.LOW: 3,
            DivergenceSeverity.INFO: 4,
        }[item.severity]
        return (item.temporal_rank_ms if item.temporal_rank_ms is not None else float("inf"), severity_rank, item.divergence_id)

    @staticmethod
    def _deduplicate(items: list[Divergence]) -> list[Divergence]:
        seen: set[tuple[str, tuple[str, ...], tuple[str, ...]]] = set()
        result: list[Divergence] = []
        for item in items:
            key = (item.classification, item.baseline_refs, item.candidate_refs)
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result
