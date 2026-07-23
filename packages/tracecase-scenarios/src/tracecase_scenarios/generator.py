from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, JsonValue

from .models import (
    AdmissibilityConstraint,
    BooleanParameterDomain,
    ConstraintOperator,
    EnumParameterDomain,
    IntegerRangeParameterDomain,
    ParameterDomain,
    ScenarioDefinition,
    ScenarioFamily,
    ScenarioInstance,
    ScenarioRegistry,
)


class ScenarioGenerationError(ValueError):
    pass


@dataclass(frozen=True)
class RejectedCombination:
    parameters: dict[str, JsonValue]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class GenerationBatch:
    instances: tuple[ScenarioInstance, ...]
    rejected: tuple[RejectedCombination, ...]
    coverage_points: tuple[str, ...]


class ScenarioGenerator:
    def __init__(self, registry: ScenarioRegistry) -> None:
        self.registry = registry

    def resolve(
        self,
        definition: ScenarioDefinition,
        *,
        seed: int = 0,
        parameter_overrides: Mapping[str, JsonValue] | None = None,
        ordinal: int = 0,
    ) -> ScenarioInstance:
        family = self.registry.family(definition.family_ref)
        parameters = self._resolve_parameters(
            family,
            definition.parameter_bindings,
            parameter_overrides or {},
            random.Random(seed + ordinal),
        )
        reasons = self._constraint_failures(family.admissibility_constraints, parameters)
        if reasons:
            raise ScenarioGenerationError("; ".join(reasons))
        topology = self.registry.topology(family.topology_ref)
        expected = definition.expected_invariants
        if not expected:
            expected = tuple()
        pre_digest_payload = {
            "scenario_ref": definition.scenario_id,
            "family_ref": family.family_id,
            "registry_version": self.registry.registry_version,
            "seed": seed,
            "ordinal": ordinal,
            "parameters": parameters,
            "topology": topology,
            "faults": definition.faults,
            "observability_profile": definition.observability_profile,
            "expected_invariants": expected,
        }
        digest = "sha256:" + hashlib.sha256(_canonical_json_bytes(pre_digest_payload)).hexdigest()
        instance_suffix = digest.split(":", 1)[1][:16]
        coverage_points = tuple(sorted(self._coverage_points(family, topology.motif.value, parameters, definition)))
        return ScenarioInstance(
            instance_id=f"instance.{definition.scenario_id}.{instance_suffix}",
            scenario_ref=definition.scenario_id,
            family_ref=family.family_id,
            registry_version=self.registry.registry_version,
            seed=seed,
            resolved_parameters=parameters,
            topology=topology,
            faults=definition.faults,
            observability_profile=definition.observability_profile,
            expected_invariants=expected,
            coverage_points=coverage_points,
            instance_digest=digest,
        )

    def sample(
        self,
        definition: ScenarioDefinition,
        *,
        count: int,
        seed: int = 0,
    ) -> GenerationBatch:
        if count < 1:
            raise ValueError("count must be positive")
        family = self.registry.family(definition.family_ref)
        rng = random.Random(seed)
        instances: list[ScenarioInstance] = []
        rejected: list[RejectedCombination] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        attempts = 0
        max_attempts = max(count * 20, 100)
        while len(instances) < count and attempts < max_attempts:
            attempts += 1
            overrides = {
                domain.parameter: rng.choice(self._domain_values(domain))
                for domain in family.parameter_domains
            }
            key = tuple(sorted((name, repr(value)) for name, value in overrides.items()))
            if key in seen:
                continue
            seen.add(key)
            reasons = self._constraint_failures(family.admissibility_constraints, overrides)
            if reasons:
                rejected.append(RejectedCombination(dict(overrides), tuple(reasons)))
                continue
            instances.append(
                self.resolve(
                    definition,
                    seed=seed,
                    parameter_overrides=overrides,
                    ordinal=len(instances),
                )
            )
        if len(instances) < count:
            raise ScenarioGenerationError(
                f"could only generate {len(instances)} unique admissible instances out of requested {count}"
            )
        return GenerationBatch(
            instances=tuple(instances),
            rejected=tuple(rejected),
            coverage_points=tuple(sorted({point for item in instances for point in item.coverage_points})),
        )

    def constrained_exhaustive(
        self,
        definition: ScenarioDefinition,
        *,
        limit: int = 10_000,
        seed: int = 0,
    ) -> GenerationBatch:
        family = self.registry.family(definition.family_ref)
        domains = tuple(family.parameter_domains)
        value_sets = [self._domain_values(domain) for domain in domains]
        instances: list[ScenarioInstance] = []
        rejected: list[RejectedCombination] = []
        for ordinal, values in enumerate(itertools.product(*value_sets)):
            if ordinal >= limit:
                raise ScenarioGenerationError(f"combination limit of {limit} exceeded")
            parameters = {domain.parameter: value for domain, value in zip(domains, values, strict=True)}
            reasons = self._constraint_failures(family.admissibility_constraints, parameters)
            if reasons:
                rejected.append(RejectedCombination(parameters, tuple(reasons)))
                continue
            instances.append(
                self.resolve(
                    definition,
                    seed=seed,
                    parameter_overrides=parameters,
                    ordinal=len(instances),
                )
            )
        return GenerationBatch(
            instances=tuple(instances),
            rejected=tuple(rejected),
            coverage_points=tuple(sorted({point for item in instances for point in item.coverage_points})),
        )

    def pairwise(
        self,
        definition: ScenarioDefinition,
        *,
        seed: int = 0,
        candidate_limit: int = 20_000,
    ) -> GenerationBatch:
        family = self.registry.family(definition.family_ref)
        exhaustive = self.constrained_exhaustive(definition, limit=candidate_limit, seed=seed)
        candidates = list(exhaustive.instances)
        if len(family.parameter_domains) < 2:
            return exhaustive

        uncovered = self._all_admissible_pairs(candidates)
        selected: list[ScenarioInstance] = []
        while uncovered:
            best = max(
                candidates,
                key=lambda item: len(self._instance_pairs(item) & uncovered),
                default=None,
            )
            if best is None:
                break
            covered = self._instance_pairs(best) & uncovered
            if not covered:
                break
            selected.append(best)
            uncovered -= covered
            candidates.remove(best)
        return GenerationBatch(
            instances=tuple(selected),
            rejected=exhaustive.rejected,
            coverage_points=tuple(sorted({point for item in selected for point in item.coverage_points})),
        )

    def _resolve_parameters(
        self,
        family: ScenarioFamily,
        bindings: Mapping[str, JsonValue],
        overrides: Mapping[str, JsonValue],
        rng: random.Random,
    ) -> dict[str, JsonValue]:
        known = {domain.parameter: domain for domain in family.parameter_domains}
        unknown = (set(bindings) | set(overrides)) - set(known)
        if unknown:
            raise ScenarioGenerationError(f"unknown parameters: {sorted(unknown)}")
        resolved: dict[str, JsonValue] = {}
        for domain in family.parameter_domains:
            if domain.parameter in overrides:
                value = overrides[domain.parameter]
            elif domain.parameter in bindings:
                value = bindings[domain.parameter]
            else:
                value = self._default_value(domain, rng)
            if value not in self._domain_values(domain):
                raise ScenarioGenerationError(
                    f"value {value!r} is not allowed for parameter {domain.parameter}"
                )
            resolved[domain.parameter] = value
        return resolved

    @staticmethod
    def _default_value(domain: ParameterDomain, rng: random.Random) -> JsonValue:
        if isinstance(domain, EnumParameterDomain):
            return domain.default if domain.default is not None else domain.values[0]
        if isinstance(domain, IntegerRangeParameterDomain):
            return domain.default if domain.default is not None else domain.minimum
        if isinstance(domain, BooleanParameterDomain):
            return domain.default
        raise TypeError(domain)

    @staticmethod
    def _domain_values(domain: ParameterDomain) -> tuple[JsonValue, ...]:
        if isinstance(domain, EnumParameterDomain):
            return domain.values
        if isinstance(domain, IntegerRangeParameterDomain):
            return domain.values()
        if isinstance(domain, BooleanParameterDomain):
            return (False, True)
        raise TypeError(domain)

    @classmethod
    def _constraint_failures(
        cls,
        constraints: Sequence[AdmissibilityConstraint],
        parameters: Mapping[str, JsonValue],
    ) -> list[str]:
        failures: list[str] = []
        for constraint in constraints:
            left = parameters.get(constraint.left_parameter)
            right = (
                parameters.get(constraint.right_parameter)
                if constraint.right_parameter
                else constraint.right_value
            )
            valid = True
            if constraint.operator is ConstraintOperator.EQ:
                valid = left == right
            elif constraint.operator is ConstraintOperator.NE:
                valid = left != right
            elif constraint.operator is ConstraintOperator.IN:
                valid = left in constraint.right_values
            elif constraint.operator is ConstraintOperator.NOT_IN:
                valid = left not in constraint.right_values
            elif constraint.operator is ConstraintOperator.REQUIRES:
                valid = not bool(left) or bool(right)
            elif constraint.operator is ConstraintOperator.EXCLUDES:
                valid = not (bool(left) and bool(right))
            if not valid:
                failures.append(
                    constraint.message
                    or f"constraint {constraint.constraint_id} rejected {constraint.left_parameter}={left!r}"
                )
        return failures

    @staticmethod
    def _coverage_points(
        family: ScenarioFamily,
        motif: str,
        parameters: Mapping[str, JsonValue],
        definition: ScenarioDefinition,
    ) -> set[str]:
        points = {
            f"family:{family.family_id}",
            f"class:{family.family_class.value}",
            f"topology:{motif}",
            f"observability:{definition.observability_profile.value}",
        }
        points.update(f"axis:{axis.value}" for axis in family.universe_axes)
        points.update(f"parameter:{name}={value!r}" for name, value in sorted(parameters.items()))
        points.update(f"fault:{fault.operator_ref}" for fault in definition.faults)
        points.update(f"invariant:{ref}" for ref in family.invariant_refs)
        return points

    @staticmethod
    def _instance_pairs(instance: ScenarioInstance) -> set[tuple[str, str]]:
        entries = [f"{name}={value!r}" for name, value in sorted(instance.resolved_parameters.items())]
        return {tuple(sorted(pair)) for pair in itertools.combinations(entries, 2)}

    @classmethod
    def _all_admissible_pairs(cls, instances: Iterable[ScenarioInstance]) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for instance in instances:
            pairs.update(cls._instance_pairs(instance))
        return pairs


def _canonical_json_bytes(value: object) -> bytes:
    def normalize(item: object) -> object:
        if isinstance(item, BaseModel):
            return normalize(item.model_dump(mode="json", by_alias=True, exclude_none=True))
        if isinstance(item, dict):
            return {str(key): normalize(val) for key, val in item.items()}
        if isinstance(item, (list, tuple, set, frozenset)):
            return [normalize(val) for val in item]
        return item

    return json.dumps(
        normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
