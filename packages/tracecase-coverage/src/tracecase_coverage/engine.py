from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Sequence

from tracecase_analyzers import AnalysisReport
from tracecase_scenarios import ScenarioInstance, ScenarioRegistry

from .models import (
    CoverageDimension, CoverageLedger, CoveragePoint, CoverageRecommendation, CoverageStatus,
    MutationAdequacyReport, MutationTrial,
)


def _id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode()).hexdigest()[:16]
    return f"{prefix}.{digest}"

class CoverageEngine:
    def __init__(self, registry: ScenarioRegistry) -> None:
        self.registry = registry

    def evaluate(
        self,
        instances: Sequence[ScenarioInstance],
        analyses: Sequence[AnalysisReport] = (),
        *,
        realizations: dict[str, str] | None = None,
    ) -> CoverageLedger:
        witnesses: dict[tuple[CoverageDimension, str], list[str]] = defaultdict(list)
        for instance in instances:
            family = self.registry.family(instance.family_ref)
            self._cover(witnesses, CoverageDimension.FAMILY, family.family_id, instance.instance_id)
            self._cover(witnesses, CoverageDimension.TOPOLOGY, family.topology_ref, instance.instance_id)
            for axis in family.universe_axes:
                self._cover(witnesses, CoverageDimension.UNIVERSE_AXIS, axis.value, instance.instance_id)
            for invariant in family.invariant_refs:
                self._cover(witnesses, CoverageDimension.INVARIANT, invariant, instance.instance_id)
            self._cover(witnesses, CoverageDimension.OBSERVABILITY, instance.observability_profile.value, instance.instance_id)
            for fault in instance.faults:
                self._cover(witnesses, CoverageDimension.FAULT_OPERATOR, fault.operator_ref, instance.instance_id)
                key = f"{family.family_id}|{fault.operator_ref}|{instance.observability_profile.value}"
                self._cover(witnesses, CoverageDimension.INTERACTION, key, instance.instance_id)
            if not instance.faults:
                key = f"{family.family_id}|baseline|{instance.observability_profile.value}"
                self._cover(witnesses, CoverageDimension.INTERACTION, key, instance.instance_id)
            if realizations and instance.instance_id in realizations:
                self._cover(witnesses, CoverageDimension.REALIZATION, realizations[instance.instance_id], instance.instance_id)
        for analysis in analyses:
            for result in analysis.invariant_report.results:
                key = f"{result.invariant_ref}|{result.status.value}"
                self._cover(witnesses, CoverageDimension.OUTCOME, key, analysis.case_id)

        expected = self._expected_points()
        points: list[CoveragePoint] = []
        for dimension, key, family_ref, attrs in expected:
            refs = tuple(sorted(witnesses.get((dimension, key), [])))
            points.append(CoveragePoint(
                point_id=_id(f"coverage.{dimension.value}", key), dimension=dimension, key=key,
                status=CoverageStatus.COVERED if refs else CoverageStatus.UNCOVERED,
                family_ref=family_ref, witness_refs=refs,
                rationale="Observed in at least one deterministic scenario instance." if refs else "No supplied instance covers this valid registry point.",
                attributes=attrs,
            ))
        covered_keys = {(p.dimension, p.key) for p in points}
        for (dimension, key), refs in sorted(witnesses.items(), key=lambda item: (item[0][0].value, item[0][1])):
            if (dimension, key) not in covered_keys:
                points.append(CoveragePoint(
                    point_id=_id(f"coverage.{dimension.value}", key), dimension=dimension, key=key,
                    status=CoverageStatus.COVERED, witness_refs=tuple(sorted(refs)),
                    rationale="Observed supplemental coverage point.",
                ))
        recommendations = self._recommend(points)
        summary = {status.value: sum(p.status is status for p in points) for status in CoverageStatus}
        summary["total"] = len(points)
        return CoverageLedger(
            ledger_id=f"coverage.registry.{self.registry.registry_version.replace('.', '-')}",
            registry_version=self.registry.registry_version,
            points=tuple(sorted(points, key=lambda p: (p.dimension.value, p.key))),
            recommendations=tuple(recommendations), summary=summary,
            attributes={"instance_count": len(instances), "analysis_count": len(analyses)},
        )

    @staticmethod
    def _cover(store, dimension, key, witness):
        if witness not in store[(dimension, str(key))]: store[(dimension, str(key))].append(witness)

    def _expected_points(self):
        values = []
        for family in self.registry.families:
            values.append((CoverageDimension.FAMILY, family.family_id, family.family_id, {}))
            values.append((CoverageDimension.TOPOLOGY, family.topology_ref, family.family_id, {}))
            for axis in family.universe_axes:
                values.append((CoverageDimension.UNIVERSE_AXIS, axis.value, family.family_id, {}))
            for invariant in family.invariant_refs:
                values.append((CoverageDimension.INVARIANT, invariant, family.family_id, {}))
            for profile in family.observability_profiles:
                values.append((CoverageDimension.OBSERVABILITY, profile.value, family.family_id, {}))
                values.append((CoverageDimension.INTERACTION, f"{family.family_id}|baseline|{profile.value}", family.family_id, {"fault":"baseline","profile":profile.value}))
                for fault in family.allowed_fault_operator_refs:
                    values.append((CoverageDimension.INTERACTION, f"{family.family_id}|{fault}|{profile.value}", family.family_id, {"fault":fault,"profile":profile.value}))
            for fault in family.allowed_fault_operator_refs:
                values.append((CoverageDimension.FAULT_OPERATOR, fault, family.family_id, {}))
        unique = {}
        for item in values: unique[(item[0], item[1])] = item
        return list(unique.values())

    def _recommend(self, points: Sequence[CoveragePoint]) -> list[CoverageRecommendation]:
        grouped: dict[str, list[CoveragePoint]] = defaultdict(list)
        for point in points:
            if point.status is CoverageStatus.UNCOVERED and point.family_ref:
                grouped[point.family_ref].append(point)
        ranked = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
        result=[]
        for index,(family_ref, missing) in enumerate(ranked,1):
            interaction = next((p for p in missing if p.dimension is CoverageDimension.INTERACTION), None)
            fault = None; profile = None
            if interaction:
                _, fault, profile = interaction.key.split("|",2)
                if fault == "baseline": fault = None
            result.append(CoverageRecommendation(
                recommendation_id=_id("recommendation", family_ref), family_ref=family_ref,
                priority=index, uncovered_point_refs=tuple(p.point_id for p in missing[:12]),
                suggested_fault_ref=fault, suggested_observability_profile=profile,
                rationale=f"Covers {len(missing)} currently uncovered semantic points.",
            ))
        return result

class MutationAdequacyEngine:
    def evaluate(self, trials: Iterable[MutationTrial]) -> MutationAdequacyReport:
        values=tuple(trials); detected=sum(t.detected for t in values)
        return MutationAdequacyReport(
            report_id="mutation-adequacy.core", trials=values,
            score=(detected/len(values) if values else 1.0), detected=detected, survived=len(values)-detected,
        )
