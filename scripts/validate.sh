#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-scenarios/src:packages/tracecase-collectors/src:packages/tracecase-graph/src:packages/tracecase-invariants/src:packages/tracecase-analyzers/src:packages/tracecase-compare/src:packages/tracecase-policy/src:packages/tracecase-lab/src:packages/tracecase-coverage/src:packages/tracecase-compat/src:packages/tracecase-sdk/src:packages/tracecase-pathforge/src:packages/tracecase-cli/src"

python scripts/check_architecture.py
python scripts/generate_sample_bundle.py
python scripts/generate_milestone_b_fixtures.py
python scripts/generate_milestone_c_fixtures.py
python scripts/generate_milestone_d_fixtures.py
python scripts/generate_milestone_e_fixtures.py
pytest -q

python - <<'PY_VALIDATE'
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from tracecase_bundle import BundleReader
from tracecase_cli.__main__ import main as cli_main

bundle_paths = sorted(Path("fixtures/bundles").glob("*.tracecase"))
archive_paths = sorted(Path("fixtures/bundles").glob("*.tracecase.zip"))

for path in (*bundle_paths, *archive_paths):
    reader, temporary = BundleReader.open(path)
    try:
        result = reader.verify()
        if not result.valid:
            raise SystemExit(
                f"bundle verification failed for {path}: "
                f"missing={result.missing_paths}, "
                f"mismatched={result.mismatched_paths}, "
                f"unexpected={result.unexpected_paths}"
            )
    finally:
        if temporary:
            temporary.cleanup()

commands = [
    ["invariants", "fixtures/bundles/reference-lab-context-loss.tracecase"],
    ["analyze", "fixtures/bundles/reference-lab-duplicate-effect.tracecase"],
    [
        "compare",
        "fixtures/bundles/reference-lab-baseline.tracecase",
        "fixtures/bundles/reference-lab-context-loss.tracecase",
    ],
    ["policy-list"],
    [
        "privacy-inventory",
        "fixtures/bundles/reference-lab-privacy-capture.tracecase",
        "--policy",
        "policy.shareable.v1",
    ],
    [
        "redaction-preview",
        "fixtures/bundles/reference-lab-privacy-capture.tracecase",
        "--policy",
        "policy.shareable.v1",
    ],
    ["lab-bindings"],
    ["lab-run", "--seed", "901", "--fault", "fault.effect.duplicate.v1"],
    ["lab-compare", "--seed", "902", "--fault", "fault.context.drop.v1"],
    ["coverage-report"],
    ["bundle-compat", "fixtures/bundles/pathforge-audit-baseline.tracecase"],
    ["bundle-health", "fixtures/bundles/pathforge-audit-baseline.tracecase"],
    [
        "neighborhood",
        "fixtures/bundles/pathforge-audit-baseline.tracecase",
        "node.pathforge.request",
        "--depth",
        "2",
    ],
    ["pathforge-bindings"],
    ["pathforge-run", "--seed", "903"],
    ["pathforge-compare", "--seed", "904", "--fault", "tenant-loss"],
]

for command in commands:
    output = StringIO()
    with redirect_stdout(output), redirect_stderr(output):
        code = cli_main(command)
    if code != 0:
        raise SystemExit(
            f"CLI smoke command failed ({code}): {' '.join(command)}\n{output.getvalue()}"
        )

with TemporaryDirectory(prefix="tracecase-validation-") as temporary_root:
    root = Path(temporary_root)
    directory = root / "shareable.tracecase"
    archive = root / "shareable.tracecase.zip"
    export_command = [
        "export-shareable",
        "fixtures/bundles/reference-lab-privacy-capture.tracecase",
        str(directory),
        "--archive",
        str(archive),
        "--policy",
        "policy.shareable.v1",
    ]
    output = StringIO()
    with redirect_stdout(output), redirect_stderr(output):
        code = cli_main(export_command)
    if code != 0:
        raise SystemExit(f"shareable export failed ({code}): {output.getvalue()}")

    for path in (directory, archive):
        reader, temporary = BundleReader.open(path)
        try:
            result = reader.verify()
            if not result.valid:
                raise SystemExit(f"exported bundle verification failed for {path}")
        finally:
            if temporary:
                temporary.cleanup()

print(
    f"Verified {len(bundle_paths)} directory bundles, "
    f"{len(archive_paths)} archive bundles, and {len(commands)} CLI smoke commands."
)
PY_VALIDATE

python -m compileall -q packages apps/api apps/reference-lab scripts
node scripts/check_workbench_syntax.cjs

if [[ -d apps/workbench/node_modules ]]; then
  (cd apps/workbench && npm run build)
else
  echo "Workbench dependency tree unavailable; full npm build deferred to CI."
fi

echo "Milestone E validation passed."
