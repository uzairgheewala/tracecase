#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-cli/src"

python scripts/check_architecture.py
python scripts/generate_sample_bundle.py
pytest
python -m tracecase_cli verify fixtures/bundles/minimal-success.tracecase
python -m tracecase_cli inspect fixtures/bundles/minimal-success.tracecase
python -m compileall -q packages apps/api scripts

echo "Milestone A validation passed."
