#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-scenarios/src:packages/tracecase-collectors/src:packages/tracecase-graph/src:packages/tracecase-cli/src"

python scripts/check_architecture.py
python scripts/generate_sample_bundle.py
python scripts/generate_milestone_b_fixtures.py
pytest -q

bundles=(
  fixtures/bundles/minimal-success.tracecase
  fixtures/bundles/context-continuity-baseline.tracecase
  fixtures/bundles/context-continuity-failure.tracecase
  fixtures/bundles/duplicate-effect-failure.tracecase
  fixtures/bundles/causal-gap-observed.tracecase
)

for bundle in "${bundles[@]}"; do
  python -m tracecase_cli verify "$bundle"
done

python -m tracecase_cli scenario-list >/dev/null
python -m tracecase_cli graph-summary fixtures/bundles/context-continuity-baseline.tracecase >/dev/null
python -m tracecase_cli graph-summary fixtures/bundles/duplicate-effect-failure.tracecase >/dev/null
python -m compileall -q packages apps/api scripts

echo "Milestone B validation passed."
