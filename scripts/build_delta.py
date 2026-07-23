from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "dist",
    "node_modules",
}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".tsbuildinfo"}


@dataclass(frozen=True)
class FileRecord:
    path: Path
    sha256: str
    size: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(root: Path) -> dict[Path, FileRecord]:
    records: dict[Path, FileRecord] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRECTORY_NAMES for part in relative.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        records[relative] = FileRecord(
            path=relative,
            sha256=sha256_file(path),
            size=path.stat().st_size,
        )
    return records


def build_delta(
    *,
    base: Path,
    target: Path,
    output_directory: Path,
    archive_path: Path,
    base_label: str,
    target_label: str,
) -> dict[str, object]:
    base_files = inventory(base)
    target_files = inventory(target)

    added = sorted(set(target_files) - set(base_files))
    modified = sorted(
        path
        for path in set(target_files) & set(base_files)
        if target_files[path].sha256 != base_files[path].sha256
    )
    deleted = sorted(set(base_files) - set(target_files))
    payload_paths = [*added, *modified]

    if output_directory.exists():
        shutil.rmtree(output_directory)
    output_directory.mkdir(parents=True)

    for relative in payload_paths:
        source = target / relative
        destination = output_directory / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    manifest = {
        "format": "tracecase.repository-delta",
        "format_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base": {
            "label": base_label,
            "file_count": len(base_files),
        },
        "target": {
            "label": target_label,
            "file_count": len(target_files),
        },
        "summary": {
            "added": len(added),
            "modified": len(modified),
            "deleted": len(deleted),
            "payload_files": len(payload_paths),
            "payload_bytes": sum(target_files[path].size for path in payload_paths),
        },
        "apply": {
            "instruction": "Extract the archive over the repository root represented by base.label.",
            "deletion_policy": (
                "Delete paths listed in deleted after extraction. The current delta has no deletions."
            ),
        },
        "added": [
            {
                "path": path.as_posix(),
                "sha256": target_files[path].sha256,
                "size": target_files[path].size,
            }
            for path in added
        ],
        "modified": [
            {
                "path": path.as_posix(),
                "base_sha256": base_files[path].sha256,
                "sha256": target_files[path].sha256,
                "size": target_files[path].size,
            }
            for path in modified
        ],
        "deleted": [
            {
                "path": path.as_posix(),
                "base_sha256": base_files[path].sha256,
                "size": base_files[path].size,
            }
            for path in deleted
        ],
    }
    manifest_path = output_directory / "DELTA_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_directory.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output_directory).as_posix())

    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a repo-relative milestone delta archive")
    parser.add_argument("base", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--base-label", required=True)
    parser.add_argument("--target-label", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_delta(
        base=args.base.resolve(),
        target=args.target.resolve(),
        output_directory=args.output_directory.resolve(),
        archive_path=args.archive.resolve(),
        base_label=args.base_label,
        target_label=args.target_label,
    )
    print(json.dumps(manifest["summary"], indent=2))


if __name__ == "__main__":
    main()
