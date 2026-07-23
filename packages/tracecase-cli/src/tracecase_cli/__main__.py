from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tracecase_analyzers import AnalyzerEngine
from tracecase_bundle import BundleBuilder, BundleReader
from tracecase_compare import SemanticComparisonEngine
from tracecase_compat import BundleHealthScanner, CaseQueryIndex, CompatibilityEngine
from tracecase_coverage import CoverageEngine
from tracecase_pathforge import PathforgeTraceBridge, pathforge_bindings
from tracecase_graph import AssembledExecutionGraph, GraphAssembler
from tracecase_invariants import InvariantRuntime
from tracecase_lab import LabRunRequest, ReferenceLab, lab_bindings
from tracecase_policy import PolicyEngine, ShareableBundleExporter, get_policy, policy_registry
from tracecase_scenarios import (
    FaultApplication,
    FaultTargetKind,
    ScenarioDefinition,
    ScenarioGenerator,
    build_default_registry,
)


def command_inspect(path: Path) -> int:
    reader, temporary = BundleReader.open(path)
    try:
        case = reader.load_case()
        payload = {
            "bundle_id": reader.manifest.bundle_id,
            "case_id": reader.manifest.case_id,
            "title": case.specification.title,
            "category": case.specification.category,
            "lifecycle": reader.manifest.lifecycle,
            "profiles": reader.manifest.profiles,
            "scenario": reader.manifest.scenario,
            "components": len(case.system.components),
            "nodes": len(case.evidence.execution.nodes),
            "relations": len(case.evidence.execution.relations),
            "observations": len(case.evidence.execution.observations),
            "effects": len(case.evidence.execution.effects),
            "has_assembled_graph": reader.has_artifact("analysis/assembled_graph.json"),
            "has_timeline": reader.has_artifact("analysis/timeline.json"),
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0
    finally:
        if temporary:
            temporary.cleanup()


def command_verify(path: Path) -> int:
    reader, temporary = BundleReader.open(path)
    try:
        result = reader.verify()
        print(
            json.dumps(
                {
                    "valid": result.valid,
                    "missing_paths": result.missing_paths,
                    "mismatched_paths": result.mismatched_paths,
                    "unexpected_paths": result.unexpected_paths,
                },
                indent=2,
            )
        )
        return 0 if result.valid else 2
    finally:
        if temporary:
            temporary.cleanup()


def command_pack(source: Path, destination: Path) -> int:
    reader = BundleReader(source)
    verification = reader.verify()
    if not verification.valid:
        print("Refusing to pack an invalid bundle", file=sys.stderr)
        return 2
    import zipfile

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())
    print(destination)
    return 0


def command_unpack(source: Path, destination: Path) -> int:
    BundleBuilder.unpack(source, destination)
    print(destination)
    return 0


def command_scenario_list() -> int:
    registry = build_default_registry()
    payload = [
        {
            "family_id": family.family_id,
            "title": family.title,
            "family_class": family.family_class,
            "topology_ref": family.topology_ref,
            "universe_axes": family.universe_axes,
            "fault_operators": family.allowed_fault_operator_refs,
            "invariants": family.invariant_refs,
        }
        for family in registry.families
    ]
    print(json.dumps(payload, indent=2, default=str))
    return 0


def command_scenario_generate(args: argparse.Namespace) -> int:
    registry = build_default_registry()
    faults = ()
    if args.fault:
        faults = (
            FaultApplication(
                application_id="application.cli.v1",
                operator_ref=args.fault,
                target_kind=FaultTargetKind(args.target_kind),
                target_ref=args.target,
                parameters=_parse_assignments(args.fault_parameter),
            ),
        )
    definition = ScenarioDefinition(
        scenario_id=args.scenario_id,
        title=args.title or args.scenario_id,
        family_ref=args.family_id,
        parameter_bindings=_parse_assignments(args.parameter),
        faults=faults,
    )
    instance = ScenarioGenerator(registry).resolve(definition, seed=args.seed)
    text = json.dumps(instance.model_dump(mode="json"), indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


def command_graph_summary(path: Path) -> int:
    reader, temporary = BundleReader.open(path)
    try:
        if reader.has_artifact("analysis/assembled_graph.json"):
            graph = AssembledExecutionGraph.model_validate(
                reader.read_json("analysis/assembled_graph.json")
            )
        else:
            case = reader.load_case()
            graph = GraphAssembler().assemble(case.evidence.execution)
        payload = {
            "graph_id": graph.graph_id,
            "execution_id": graph.execution_id,
            "nodes": len(graph.nodes),
            "source_relations": graph.report.source_relation_count,
            "derived_relations": graph.report.derived_relation_count,
            "identity_groups": len(graph.identity_groups),
            "context_flows": len(graph.context_flows),
            "effect_groups": len(graph.effect_groups),
            "temporal_constraints": len(graph.temporal_constraints),
            "disconnected_components": graph.report.disconnected_components,
            "warnings": [item.model_dump(mode="json") for item in graph.report.warnings],
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0
    finally:
        if temporary:
            temporary.cleanup()



def _load_case_and_graph(path: Path):
    reader, temporary = BundleReader.open(path)
    case = reader.load_case()
    if reader.has_artifact("analysis/assembled_graph.json"):
        graph = AssembledExecutionGraph.model_validate(reader.read_json("analysis/assembled_graph.json"))
    else:
        graph = GraphAssembler().assemble(case.evidence.execution)
    return reader, temporary, case, graph


def command_invariants(path: Path) -> int:
    _reader, temporary, case, graph = _load_case_and_graph(path)
    try:
        report = InvariantRuntime().evaluate(case, graph)
        print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0
    finally:
        if temporary:
            temporary.cleanup()


def command_analyze(path: Path) -> int:
    _reader, temporary, case, graph = _load_case_and_graph(path)
    try:
        report = AnalyzerEngine().analyze(case, graph)
        print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0
    finally:
        if temporary:
            temporary.cleanup()


def command_compare(baseline_path: Path, candidate_path: Path) -> int:
    _baseline_reader, baseline_temporary, baseline_case, baseline_graph = _load_case_and_graph(baseline_path)
    _candidate_reader, candidate_temporary, candidate_case, candidate_graph = _load_case_and_graph(candidate_path)
    try:
        comparison = SemanticComparisonEngine().compare(
            baseline_case, baseline_graph, candidate_case, candidate_graph
        )
        print(json.dumps(comparison.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0
    finally:
        if baseline_temporary:
            baseline_temporary.cleanup()
        if candidate_temporary:
            candidate_temporary.cleanup()


def command_policy_list() -> int:
    print(json.dumps([item.model_dump(mode="json") for item in policy_registry()], indent=2, sort_keys=True))
    return 0


def command_privacy_inventory(path: Path, policy_id: str) -> int:
    reader, temporary = BundleReader.open(path)
    try:
        report = PolicyEngine(get_policy(policy_id)).inventory(reader.load_case())
        print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0
    finally:
        if temporary:
            temporary.cleanup()


def command_redaction_preview(path: Path, policy_id: str) -> int:
    reader, temporary = BundleReader.open(path)
    try:
        _case, report = PolicyEngine(get_policy(policy_id)).apply(reader.load_case())
        print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0 if report.valid_for_export else 2
    finally:
        if temporary:
            temporary.cleanup()


def command_export_shareable(path: Path, destination: Path, policy_id: str, archive: Path | None) -> int:
    reader, temporary = BundleReader.open(path)
    try:
        result = ShareableBundleExporter(get_policy(policy_id)).export(
            reader, destination, archive_path=archive, overwrite=True
        )
        print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0
    finally:
        if temporary:
            temporary.cleanup()


def command_lab_bindings() -> int:
    print(json.dumps([item.model_dump(mode="json") for item in lab_bindings()], indent=2, sort_keys=True))
    return 0


def _lab_request(args: argparse.Namespace) -> LabRunRequest:
    return LabRunRequest(
        binding_ref=args.binding, seed=args.seed, fault_operator_ref=args.fault,
        observability_fault_ref=args.observability_fault, tenant_id=args.tenant_id,
        principal_id=args.principal_id, include_sensitive_payload=args.include_sensitive_payload,
    )


def command_lab_run(args: argparse.Namespace) -> int:
    result = ReferenceLab().run(_lab_request(args))
    if args.output:
        builder = BundleBuilder(args.output)
        builder.build(result.case, overwrite=True, analysis_status="complete")
        if args.archive:
            builder.pack(args.archive, overwrite=True)
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def command_lab_compare(args: argparse.Namespace) -> int:
    result = ReferenceLab().compare(_lab_request(args))
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def _coverage_instances():
    registry = build_default_registry()
    generator = ScenarioGenerator(registry)
    instances = []
    for index, family in enumerate(registry.families):
        definition = ScenarioDefinition(
            scenario_id=f"scenario.cli.coverage.{index}",
            title=family.title,
            family_ref=family.family_id,
        )
        instances.append(generator.resolve(definition, seed=1000 + index))
        if family.allowed_fault_operator_refs:
            application = FaultApplication(
                application_id=f"application.cli.coverage.{index}",
                operator_ref=family.allowed_fault_operator_refs[0],
                target_kind=FaultTargetKind.SYSTEM,
            )
            instances.append(
                generator.resolve(
                    definition.model_copy(update={"faults": (application,)}),
                    seed=2000 + index,
                )
            )
    return registry, tuple(instances)


def command_coverage_report() -> int:
    registry, instances = _coverage_instances()
    report = CoverageEngine(registry).evaluate(instances)
    print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def command_bundle_compat(path: Path) -> int:
    reader, temporary = BundleReader.open(path)
    try:
        assessment = CompatibilityEngine().assess(reader)
        print(json.dumps(assessment.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0 if assessment.status.value in {"compatible", "migratable"} else 2
    finally:
        if temporary:
            temporary.cleanup()


def command_bundle_health(path: Path) -> int:
    reader, temporary = BundleReader.open(path)
    try:
        report = BundleHealthScanner().scan(reader)
        print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0 if report.valid else 2
    finally:
        if temporary:
            temporary.cleanup()


def command_neighborhood(path: Path, node_ref: str, depth: int) -> int:
    reader, temporary = BundleReader.open(path)
    try:
        case = reader.load_case()
        graph = (
            AssembledExecutionGraph.model_validate(reader.read_json("analysis/assembled_graph.json"))
            if reader.has_artifact("analysis/assembled_graph.json")
            else GraphAssembler().assemble(case.evidence.execution)
        )
        index = CaseQueryIndex(case, graph)
        result = index.neighborhood(node_ref, depth=depth)
        print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0
    finally:
        if temporary:
            temporary.cleanup()


def command_pathforge_bindings() -> int:
    print(json.dumps([item.model_dump(mode="json") for item in pathforge_bindings()], indent=2, sort_keys=True))
    return 0


def command_pathforge_run(args: argparse.Namespace) -> int:
    bridge = PathforgeTraceBridge(args.binding)
    case = bridge.demo_case(seed=args.seed, fault=args.fault)
    graph = GraphAssembler().assemble(case.evidence.execution)
    analysis = AnalyzerEngine().analyze(case, graph)
    payload = {
        "result": bridge.analyze(case).model_dump(mode="json"),
        "analysis": analysis.model_dump(mode="json"),
    }
    if args.output:
        builder = BundleBuilder(args.output)
        builder.build(case, overwrite=True, analysis_status="complete")
        if args.archive:
            builder.pack(args.archive, overwrite=True)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_pathforge_compare(args: argparse.Namespace) -> int:
    bridge = PathforgeTraceBridge(args.binding)
    _baseline, _candidate, comparison = bridge.compare_demo(seed=args.seed, fault=args.fault)
    print(json.dumps(comparison.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0

def _parse_assignments(values: list[str] | None) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in values or []:
        if "=" not in item:
            raise ValueError(f"expected NAME=VALUE, got {item!r}")
        name, raw = item.split("=", 1)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        result[name] = value
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracecase")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a bundle summary")
    inspect_parser.add_argument("path", type=Path)

    verify_parser = subparsers.add_parser("verify", help="Verify bundle integrity")
    verify_parser.add_argument("path", type=Path)

    pack_parser = subparsers.add_parser("pack", help="Pack a directory bundle")
    pack_parser.add_argument("source", type=Path)
    pack_parser.add_argument("destination", type=Path)

    unpack_parser = subparsers.add_parser("unpack", help="Unpack a bundle archive")
    unpack_parser.add_argument("source", type=Path)
    unpack_parser.add_argument("destination", type=Path)

    subparsers.add_parser("scenario-list", help="List generic scenario families")

    generate_parser = subparsers.add_parser(
        "scenario-generate", help="Resolve a deterministic scenario instance"
    )
    generate_parser.add_argument("family_id")
    generate_parser.add_argument("--scenario-id", default="scenario.cli.generated.v1")
    generate_parser.add_argument("--title")
    generate_parser.add_argument("--seed", type=int, default=0)
    generate_parser.add_argument("--parameter", action="append")
    generate_parser.add_argument("--fault")
    generate_parser.add_argument(
        "--target-kind",
        choices=[item.value for item in FaultTargetKind],
        default=FaultTargetKind.SYSTEM.value,
    )
    generate_parser.add_argument("--target")
    generate_parser.add_argument("--fault-parameter", action="append")
    generate_parser.add_argument("--output", type=Path)

    graph_parser = subparsers.add_parser(
        "graph-summary", help="Assemble or inspect a semantic graph summary"
    )
    graph_parser.add_argument("path", type=Path)

    invariant_parser = subparsers.add_parser("invariants", help="Evaluate generic invariants for a case bundle")
    invariant_parser.add_argument("path", type=Path)

    analyze_parser = subparsers.add_parser("analyze", help="Run invariant and bounded analyzer packs")
    analyze_parser.add_argument("path", type=Path)

    compare_parser = subparsers.add_parser("compare", help="Semantically align and compare two case bundles")
    compare_parser.add_argument("baseline", type=Path)
    compare_parser.add_argument("candidate", type=Path)

    subparsers.add_parser("policy-list", help="List privacy and export policies")

    inventory_parser = subparsers.add_parser("privacy-inventory", help="Classify case fields for export")
    inventory_parser.add_argument("path", type=Path)
    inventory_parser.add_argument("--policy", default="policy.shareable.v1")

    preview_parser = subparsers.add_parser("redaction-preview", help="Preview deterministic redaction transformations")
    preview_parser.add_argument("path", type=Path)
    preview_parser.add_argument("--policy", default="policy.shareable.v1")

    export_parser = subparsers.add_parser("export-shareable", help="Create a privacy-validated shareable bundle")
    export_parser.add_argument("path", type=Path)
    export_parser.add_argument("destination", type=Path)
    export_parser.add_argument("--archive", type=Path)
    export_parser.add_argument("--policy", default="policy.shareable.v1")

    subparsers.add_parser("lab-bindings", help="List concrete reference-lab bindings")
    for command in ("lab-run", "lab-compare"):
        lab_parser = subparsers.add_parser(command, help="Run the distributed reference laboratory")
        lab_parser.add_argument("--binding", default="lab.transcript-import.v1")
        lab_parser.add_argument("--seed", type=int, default=1)
        lab_parser.add_argument("--fault")
        lab_parser.add_argument("--observability-fault")
        lab_parser.add_argument("--tenant-id", default="institution-alpha")
        lab_parser.add_argument("--principal-id", default="student-1001")
        lab_parser.add_argument("--include-sensitive-payload", action="store_true")
        if command == "lab-run":
            lab_parser.add_argument("--output", type=Path)
            lab_parser.add_argument("--archive", type=Path)

    subparsers.add_parser("coverage-report", help="Build the semantic coverage ledger")

    compat_parser = subparsers.add_parser("bundle-compat", help="Assess bundle compatibility")
    compat_parser.add_argument("path", type=Path)
    health_parser = subparsers.add_parser("bundle-health", help="Scan bundle integrity and recoverability")
    health_parser.add_argument("path", type=Path)
    neighborhood_parser = subparsers.add_parser("neighborhood", help="Query a bounded graph neighborhood")
    neighborhood_parser.add_argument("path", type=Path)
    neighborhood_parser.add_argument("node_ref")
    neighborhood_parser.add_argument("--depth", type=int, default=1)

    subparsers.add_parser("pathforge-bindings", help="List Pathforge integration bindings")
    for command in ("pathforge-run", "pathforge-compare"):
        pathforge_parser = subparsers.add_parser(command, help="Run the isolated Pathforge integration")
        pathforge_parser.add_argument("--binding", default="pathforge.requirement-audit.v1")
        pathforge_parser.add_argument("--seed", type=int, default=1)
        pathforge_parser.add_argument("--fault", default="tenant-loss" if command == "pathforge-compare" else None)
        if command == "pathforge-run":
            pathforge_parser.add_argument("--output", type=Path)
            pathforge_parser.add_argument("--archive", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        return command_inspect(args.path)
    if args.command == "verify":
        return command_verify(args.path)
    if args.command == "pack":
        return command_pack(args.source, args.destination)
    if args.command == "unpack":
        return command_unpack(args.source, args.destination)
    if args.command == "scenario-list":
        return command_scenario_list()
    if args.command == "scenario-generate":
        return command_scenario_generate(args)
    if args.command == "graph-summary":
        return command_graph_summary(args.path)
    if args.command == "invariants":
        return command_invariants(args.path)
    if args.command == "analyze":
        return command_analyze(args.path)
    if args.command == "compare":
        return command_compare(args.baseline, args.candidate)

    if args.command == "policy-list":
        return command_policy_list()
    if args.command == "privacy-inventory":
        return command_privacy_inventory(args.path, args.policy)
    if args.command == "redaction-preview":
        return command_redaction_preview(args.path, args.policy)
    if args.command == "export-shareable":
        return command_export_shareable(args.path, args.destination, args.policy, args.archive)
    if args.command == "lab-bindings":
        return command_lab_bindings()
    if args.command == "lab-run":
        return command_lab_run(args)
    if args.command == "lab-compare":
        return command_lab_compare(args)
    if args.command == "coverage-report":
        return command_coverage_report()
    if args.command == "bundle-compat":
        return command_bundle_compat(args.path)
    if args.command == "bundle-health":
        return command_bundle_health(args.path)
    if args.command == "neighborhood":
        return command_neighborhood(args.path, args.node_ref, args.depth)
    if args.command == "pathforge-bindings":
        return command_pathforge_bindings()
    if args.command == "pathforge-run":
        return command_pathforge_run(args)
    if args.command == "pathforge-compare":
        return command_pathforge_compare(args)
    raise AssertionError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
