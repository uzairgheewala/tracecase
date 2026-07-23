from __future__ import annotations

import hashlib
from collections import Counter

from tracecase_graph import AssembledExecutionGraph
from tracecase_invariants import InvariantResult, InvariantRuntime, InvariantStatus
from tracecase_model import Confidence, DerivationKind, EvidenceClassification, ExecutionCase, RelationKind

from .models import (
    AnalysisReport,
    AnalyzerDefinition,
    AnalyzerRunRecord,
    Finding,
    FindingCategory,
    FindingSeverity,
)
from .registry import build_default_analyzer_registry


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]
    return f"{prefix}.{digest}"


def _severity(result: InvariantResult) -> FindingSeverity:
    if result.severity.value == "critical":
        return FindingSeverity.CRITICAL
    if result.status is InvariantStatus.CONTRADICTED:
        return FindingSeverity.HIGH
    if result.severity.value == "high":
        return FindingSeverity.HIGH
    if result.severity.value == "medium":
        return FindingSeverity.MEDIUM
    return FindingSeverity.LOW


class AnalyzerEngine:
    def __init__(
        self,
        *,
        invariant_runtime: InvariantRuntime | None = None,
        definitions: tuple[AnalyzerDefinition, ...] | None = None,
    ) -> None:
        self.invariant_runtime = invariant_runtime or InvariantRuntime()
        self.definitions = definitions or build_default_analyzer_registry()

    def analyze(
        self,
        case: ExecutionCase,
        graph: AssembledExecutionGraph,
        *,
        invariant_ids: tuple[str, ...] | None = None,
    ) -> AnalysisReport:
        invariant_report = self.invariant_runtime.evaluate(case, graph, invariant_ids=invariant_ids)
        by_invariant = {item.invariant_ref: item for item in invariant_report.results}
        findings: list[Finding] = []
        runs: list[AnalyzerRunRecord] = []
        for definition in self.definitions:
            selected = tuple(by_invariant[item] for item in definition.invariant_refs if item in by_invariant)
            emitted = list(self._findings_for(definition, selected, case, graph))
            findings.extend(emitted)
            runs.append(
                AnalyzerRunRecord(
                    run_id=_stable_id("analyzer-run", definition.analyzer_id, case.specification.case_id, graph.graph_id),
                    analyzer_ref=definition.analyzer_id,
                    analyzer_version=definition.version,
                    input_case_ref=case.specification.case_id,
                    input_graph_ref=graph.graph_id,
                    invariant_result_refs=tuple(item.result_id for item in selected),
                    finding_refs=tuple(item.finding_id for item in emitted),
                    attributes={"evaluated_invariants": len(selected)},
                )
            )
        findings = sorted(findings, key=lambda item: (self._severity_rank(item.severity), item.finding_id), reverse=True)
        summary_counter = Counter(item.severity.value for item in findings)
        summary_counter.update({f"invariant_{key.value}": value for key, value in invariant_report.summary.items()})
        limitations = tuple(
            sorted(
                {
                    missing
                    for result in invariant_report.results
                    for missing in result.missing_evidence
                }
            )
        )
        return AnalysisReport(
            report_id=_stable_id("analysis-report", case.specification.case_id, graph.graph_id),
            case_id=case.specification.case_id,
            graph_id=graph.graph_id,
            invariant_report=invariant_report,
            analyzer_runs=tuple(runs),
            findings=tuple(findings),
            summary=dict(summary_counter),
            limitations=limitations,
        )

    def _findings_for(
        self,
        definition: AnalyzerDefinition,
        results: tuple[InvariantResult, ...],
        case: ExecutionCase,
        graph: AssembledExecutionGraph,
    ) -> tuple[Finding, ...]:
        findings: list[Finding] = []
        for result in results:
            if result.status not in {InvariantStatus.VIOLATED, InvariantStatus.CONTRADICTED, InvariantStatus.INCONCLUSIVE}:
                continue
            finding = self._finding_from_result(definition, result)
            findings.append(finding)

        if definition.category is FindingCategory.RETRY_EFFECT:
            findings.extend(self._retry_specific_findings(definition, case, graph, results))
        if definition.category is FindingCategory.TRANSACTION_ORDERING:
            findings.extend(self._transaction_specific_findings(definition, graph, results))
        if definition.category is FindingCategory.OBSERVABILITY:
            findings.extend(self._observability_specific_findings(definition, case, graph, results))
        return tuple(self._deduplicate(findings))

    @staticmethod
    def _finding_from_result(definition: AnalyzerDefinition, result: InvariantResult) -> Finding:
        classification = result.invariant_ref.removeprefix("invariant.").removesuffix(".v1")
        limitations = tuple(result.missing_evidence)
        if result.status is InvariantStatus.INCONCLUSIVE:
            limitations = (*limitations, "Available evidence does not support a definitive satisfied/violated result.")
        return Finding(
            finding_id=_stable_id("finding", definition.analyzer_id, result.result_id),
            analyzer_ref=definition.analyzer_id,
            analyzer_version=definition.version,
            category=definition.category,
            classification=classification,
            title=classification.replace(".", " ").replace("-", " ").title(),
            summary=result.explanation,
            severity=_severity(result),
            evidence_classification=result.evidence_classification,
            confidence=result.confidence,
            related_invariant_result_refs=(result.result_id,),
            evidence_refs=result.evidence_refs,
            node_refs=result.node_refs,
            relation_refs=result.relation_refs,
            context_refs=result.context_refs,
            effect_refs=result.effect_refs,
            conflicting_evidence_refs=(result.evidence_refs if result.status is InvariantStatus.CONTRADICTED else ()),
            limitations=limitations,
            recommended_inspection_points=AnalyzerEngine._inspection_points(definition.category),
            attributes={"invariant_status": result.status.value, **result.attributes},
        )

    @staticmethod
    def _retry_specific_findings(
        definition: AnalyzerDefinition,
        case: ExecutionCase,
        graph: AssembledExecutionGraph,
        results: tuple[InvariantResult, ...],
    ) -> list[Finding]:
        findings: list[Finding] = []
        effect_by_id = {effect.effect_id: effect for effect in case.evidence.execution.effects}
        for group in graph.effect_groups:
            if group.durable_count <= 1:
                continue
            members = [effect_by_id[ref] for ref in group.member_effect_refs if ref in effect_by_id]
            attempts = sorted(
                {
                    next(
                        (
                            node.identities.task_attempt
                            for node in case.evidence.execution.nodes
                            if node.node_id == effect.producer_node_ref
                        ),
                        None,
                    )
                    for effect in members
                }
                - {None}
            )
            findings.append(
                Finding(
                    finding_id=_stable_id("finding.retry-duplicate", definition.analyzer_id, group.group_id),
                    analyzer_ref=definition.analyzer_id,
                    analyzer_version=definition.version,
                    category=FindingCategory.RETRY_EFFECT,
                    classification="retry.duplicate-durable-effect",
                    title="Retry repeated a durable effect",
                    summary=f"Logical effect {group.logical_effect_key!r} became durable {group.durable_count} times across attempts {attempts}.",
                    severity=FindingSeverity.HIGH,
                    evidence_classification=EvidenceClassification.DETERMINISTIC,
                    confidence=Confidence(score=1.0, rationale="effect group uses identical logical_effect_key"),
                    related_invariant_result_refs=tuple(item.result_id for item in results if item.invariant_ref.endswith("at-most-once.v1")),
                    evidence_refs=tuple(sorted({ref for effect in members for ref in effect.evidence_refs})),
                    node_refs=tuple(sorted({effect.producer_node_ref for effect in members})),
                    effect_refs=group.member_effect_refs,
                    recommended_inspection_points=(
                        "Inspect the exception or timeout that triggered the later attempt.",
                        "Inspect idempotency-key enforcement around the durable side effect.",
                    ),
                    attributes={"logical_effect_key": group.logical_effect_key, "attempts": attempts, "durable_count": group.durable_count},
                )
            )
        return findings

    @staticmethod
    def _transaction_specific_findings(
        definition: AnalyzerDefinition,
        graph: AssembledExecutionGraph,
        results: tuple[InvariantResult, ...],
    ) -> list[Finding]:
        conflicts = [item for item in graph.temporal_constraints if item.kind.value == "timestamp_conflict"]
        if not conflicts:
            return []
        node_refs = tuple(sorted({ref for item in conflicts for ref in (item.source_node_ref, item.target_node_ref)}))
        relation_refs = tuple(sorted({item.relation_ref for item in conflicts if item.relation_ref}))
        return [
            Finding(
                finding_id=_stable_id("finding.transaction-conflict", definition.analyzer_id, *node_refs),
                analyzer_ref=definition.analyzer_id,
                analyzer_version=definition.version,
                category=FindingCategory.TRANSACTION_ORDERING,
                classification="ordering.causal-timestamp-conflict",
                title="Causal order conflicts with recorded timestamps",
                summary="A source-backed causal edge points forward while normalized timestamps place its target earlier.",
                severity=FindingSeverity.HIGH,
                evidence_classification=EvidenceClassification.CONTRADICTED,
                confidence=Confidence(score=1.0, rationale="causal relationship conflicts with normalized timestamps"),
                related_invariant_result_refs=tuple(item.result_id for item in results),
                node_refs=node_refs,
                relation_refs=relation_refs,
                conflicting_evidence_refs=relation_refs,
                limitations=("Clock normalization may be wrong; inspect clock-source uncertainty before assigning product causality.",),
                recommended_inspection_points=("Inspect transaction commit timing and source clock normalization.",),
            )
        ]

    @staticmethod
    def _observability_specific_findings(
        definition: AnalyzerDefinition,
        case: ExecutionCase,
        graph: AssembledExecutionGraph,
        results: tuple[InvariantResult, ...],
    ) -> list[Finding]:
        findings: list[Finding] = []
        source_relation_refs = set(graph.source_relation_refs)
        node_by_id = {node.node_id: node for node in graph.nodes}
        recovered = [
            relation
            for relation in graph.relations
            if relation.relation_id in set(graph.derived_relation_refs)
            and relation.kind in {RelationKind.DELIVERS, RelationKind.SPAWNS}
            and relation.derivation in {DerivationKind.DETERMINISTIC, DerivationKind.SOURCE_NATIVE}
            and relation.source_ref in node_by_id
            and relation.target_ref in node_by_id
            and (
                node_by_id[relation.source_ref].identities.trace_id
                != node_by_id[relation.target_ref].identities.trace_id
                or not node_by_id[relation.target_ref].identities.parent_span_id
            )
        ]
        if recovered and any(item.status is InvariantStatus.VIOLATED for item in results):
            node_refs = tuple(sorted({ref for relation in recovered for ref in (relation.source_ref, relation.target_ref)}))
            findings.append(
                Finding(
                    finding_id=_stable_id("finding.recovered-link", definition.analyzer_id, *node_refs),
                    analyzer_ref=definition.analyzer_id,
                    analyzer_version=definition.version,
                    category=FindingCategory.OBSERVABILITY,
                    classification="observability.link-reconstructed",
                    title="Causal link required reconstruction",
                    summary="The canonical graph could reconnect part of the workflow only through derived identity evidence; the original source-backed boundary link is absent.",
                    severity=FindingSeverity.MEDIUM,
                    evidence_classification=EvidenceClassification.DETERMINISTIC,
                    confidence=Confidence(score=0.95, rationale="derived relation reconstructed from stable execution identity"),
                    related_invariant_result_refs=tuple(item.result_id for item in results),
                    node_refs=node_refs,
                    relation_refs=tuple(sorted(relation.relation_id for relation in recovered)),
                    limitations=("The reconstructed edge proves correlatability, not the exact transport-level parent relationship.",),
                    recommended_inspection_points=("Inspect context injection/extraction at the asynchronous boundary.",),
                    attributes={"source_relation_count": len(source_relation_refs), "reconstructed_relations": len(recovered)},
                )
            )
        empty_observation_nodes = [node for node in case.evidence.execution.nodes if not node.observation_refs]
        if empty_observation_nodes:
            node_refs = tuple(sorted(node.node_id for node in empty_observation_nodes))
            findings.append(
                Finding(
                    finding_id=_stable_id("finding.missing-node-evidence", definition.analyzer_id, *node_refs),
                    analyzer_ref=definition.analyzer_id,
                    analyzer_version=definition.version,
                    category=FindingCategory.OBSERVABILITY,
                    classification="observability.node-without-source-evidence",
                    title="Execution node lacks source observations",
                    summary=f"{len(node_refs)} canonical execution node(s) have no attached source observation after collection.",
                    severity=FindingSeverity.MEDIUM,
                    evidence_classification=EvidenceClassification.UNKNOWN,
                    confidence=Confidence(score=1.0, rationale="observation_refs is empty"),
                    node_refs=node_refs,
                    limitations=("The operation may still have occurred; this finding describes evidence completeness only.",),
                    recommended_inspection_points=("Inspect collector diagnostics and sampling configuration.",),
                )
            )
        return findings

    @staticmethod
    def _inspection_points(category: FindingCategory) -> tuple[str, ...]:
        return {
            FindingCategory.CONTEXT: ("Inspect context serialization, transport, and destination initialization.",),
            FindingCategory.IDENTITY: ("Inspect workflow, task, tenant, and idempotency identity creation.",),
            FindingCategory.RETRY_EFFECT: ("Inspect retry trigger, effect durability, and idempotency enforcement.",),
            FindingCategory.TRANSACTION_ORDERING: ("Inspect publication relative to commit and dependent read visibility.",),
            FindingCategory.OBSERVABILITY: ("Inspect instrumentation and propagation at the implicated boundary.",),
            FindingCategory.RESOURCE_PERFORMANCE: ("Inspect repeated operation families and resource wait spans.",),
            FindingCategory.PRIVACY: ("Inspect capture allowlists and export policy.",),
            FindingCategory.CONTRACT: ("Inspect producer/consumer contract versions and sensitive fields.",),
        }[category]

    @staticmethod
    def _deduplicate(findings: list[Finding]) -> list[Finding]:
        seen: set[tuple[str, tuple[str, ...], tuple[str, ...]]] = set()
        result: list[Finding] = []
        for finding in findings:
            key = (finding.classification, finding.node_refs, finding.effect_refs)
            if key in seen:
                continue
            seen.add(key)
            result.append(finding)
        return result

    @staticmethod
    def _severity_rank(severity: FindingSeverity) -> int:
        return {
            FindingSeverity.INFO: 0,
            FindingSeverity.LOW: 1,
            FindingSeverity.MEDIUM: 2,
            FindingSeverity.HIGH: 3,
            FindingSeverity.CRITICAL: 4,
        }[severity]
