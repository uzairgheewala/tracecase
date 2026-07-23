from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from tracecase_bundle import BundleReader
from tracecase_graph import AssembledExecutionGraph, GraphAssembler, TimelineModel


@dataclass(frozen=True)
class CaseSummary:
    case_id: str
    bundle_id: str
    title: str
    category: str
    lifecycle: str
    path: str
    valid: bool
    node_count: int
    relation_count: int
    effect_count: int
    warning_count: int
    scenario_family: str | None


class CaseRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or settings.TRACECASE_BUNDLE_ROOT)

    def list(self) -> list[CaseSummary]:
        if not self.root.exists():
            return []
        summaries: list[CaseSummary] = []
        for path in sorted(self.root.glob("*.tracecase")):
            if path.is_dir():
                try:
                    summaries.append(self._summarize(path))
                except Exception:
                    continue
        return summaries

    def get_reader(self, case_id: str) -> BundleReader:
        for path in self.root.glob("*.tracecase"):
            if path.is_dir():
                reader = BundleReader(path)
                if reader.manifest.case_id == case_id:
                    return reader
        raise FileNotFoundError(case_id)

    def get_assembled_graph(self, case_id: str) -> AssembledExecutionGraph:
        reader = self.get_reader(case_id)
        if reader.has_artifact("analysis/assembled_graph.json"):
            return AssembledExecutionGraph.model_validate(
                reader.read_json("analysis/assembled_graph.json")
            )
        case = reader.load_case()
        return GraphAssembler().assemble(case.evidence.execution)

    def get_timeline(self, case_id: str) -> TimelineModel:
        reader = self.get_reader(case_id)
        if reader.has_artifact("analysis/timeline.json"):
            return TimelineModel.model_validate(reader.read_json("analysis/timeline.json"))
        case = reader.load_case()
        graph = self.get_assembled_graph(case_id)
        return GraphAssembler().timeline(graph, case.system)

    def _summarize(self, path: Path) -> CaseSummary:
        reader = BundleReader(path)
        case = reader.load_case()
        graph = (
            AssembledExecutionGraph.model_validate(reader.read_json("analysis/assembled_graph.json"))
            if reader.has_artifact("analysis/assembled_graph.json")
            else GraphAssembler().assemble(case.evidence.execution)
        )
        return CaseSummary(
            case_id=reader.manifest.case_id,
            bundle_id=reader.manifest.bundle_id,
            title=case.specification.title,
            category=case.specification.category.value,
            lifecycle=reader.manifest.lifecycle.value,
            path=str(path),
            valid=reader.verify().valid,
            node_count=len(case.evidence.execution.nodes),
            relation_count=len(graph.relations),
            effect_count=len(case.evidence.execution.effects),
            warning_count=len(graph.report.warnings),
            scenario_family=(reader.manifest.scenario.family_ref if reader.manifest.scenario else None),
        )
