from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tracecase_bundle import BundleBuilder, BundleReader
from tracecase_graph import AssembledExecutionGraph, GraphAssembler
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
    raise AssertionError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
