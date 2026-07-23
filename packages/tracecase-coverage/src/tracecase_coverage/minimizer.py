from __future__ import annotations

import hashlib
from collections.abc import Callable
from tracecase_scenarios import ScenarioDefinition, ScenarioInstance
from .models import MinimizationReport, MinimizationStep


def _digest(value) -> str:
    return "sha256:" + hashlib.sha256(value.model_dump_json(exclude_none=True).encode()).hexdigest()

class ScenarioMinimizer:
    """Deterministic delta debugger over declarative scenario inputs.

    The caller supplies the preservation oracle, allowing the minimizer to remain independent
    of any particular invariant or analyzer implementation.
    """
    def minimize_definition(
        self,
        definition: ScenarioDefinition,
        *,
        target_ref: str,
        preserves: Callable[[ScenarioDefinition], bool],
    ) -> tuple[ScenarioDefinition, MinimizationReport]:
        current=definition; steps=[]; original_size=self._size(current); ordinal=0
        candidates=[]
        for name in sorted(current.parameter_bindings):
            candidates.append(("parameter_bindings", (name,)))
        for index in range(len(current.faults)-1, -1, -1):
            candidates.append(("faults", (str(index),)))
        for index in range(len(current.expected_invariants)-1, -1, -1):
            candidates.append(("expected_invariants", (str(index),)))
        for dimension, removed in candidates:
            candidate=self._remove(current, dimension, removed)
            ordinal += 1
            preserved=False
            try: preserved=preserves(candidate)
            except Exception: preserved=False
            steps.append(MinimizationStep(
                step_id=f"min-step.{ordinal}", dimension=dimension, removed=removed,
                preserved=preserved, candidate_digest=_digest(candidate),
            ))
            if preserved: current=candidate
        minimized_size=self._size(current)
        report=MinimizationReport(
            report_id=f"minimization.{definition.scenario_id}", original_ref=definition.scenario_id,
            minimized_ref=current.scenario_id, target_ref=target_ref, steps=tuple(steps),
            original_size=original_size, minimized_size=minimized_size,
            reduction_ratio=((original_size-minimized_size)/original_size if original_size else 0.0),
        )
        return current, report

    @staticmethod
    def _size(value: ScenarioDefinition) -> int:
        return len(value.parameter_bindings)+len(value.faults)+len(value.expected_invariants)

    @staticmethod
    def _remove(value: ScenarioDefinition, dimension: str, removed: tuple[str,...]) -> ScenarioDefinition:
        if dimension == "parameter_bindings":
            data=dict(value.parameter_bindings); data.pop(removed[0],None)
            return value.model_copy(update={"parameter_bindings":data})
        index=int(removed[0])
        if dimension == "faults":
            return value.model_copy(update={"faults":tuple(v for i,v in enumerate(value.faults) if i!=index)})
        return value.model_copy(update={"expected_invariants":tuple(v for i,v in enumerate(value.expected_invariants) if i!=index)})

class InstanceMinimizer:
    def minimize_coverage_points(self, instance: ScenarioInstance, required_prefixes: tuple[str,...]) -> ScenarioInstance:
        retained=tuple(point for point in instance.coverage_points if point.startswith(required_prefixes))
        return instance.model_copy(update={"coverage_points":retained})
