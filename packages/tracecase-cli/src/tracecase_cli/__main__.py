from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tracecase_bundle import BundleBuilder, BundleReader


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
            "components": len(case.system.components),
            "nodes": len(case.evidence.execution.nodes),
            "relations": len(case.evidence.execution.relations),
            "observations": len(case.evidence.execution.observations),
            "effects": len(case.evidence.execution.effects),
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
        print(json.dumps({
            "valid": result.valid,
            "missing_paths": result.missing_paths,
            "mismatched_paths": result.mismatched_paths,
            "unexpected_paths": result.unexpected_paths,
        }, indent=2))
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
    raise AssertionError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
