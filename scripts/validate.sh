#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-scenarios/src:packages/tracecase-collectors/src:packages/tracecase-graph/src:packages/tracecase-invariants/src:packages/tracecase-analyzers/src:packages/tracecase-compare/src:packages/tracecase-cli/src"

python scripts/check_architecture.py
python scripts/generate_sample_bundle.py
python scripts/generate_milestone_b_fixtures.py
python scripts/generate_milestone_c_fixtures.py
pytest -q

bundles=(
  fixtures/bundles/minimal-success.tracecase
  fixtures/bundles/context-continuity-baseline.tracecase
  fixtures/bundles/context-continuity-failure.tracecase
  fixtures/bundles/duplicate-effect-failure.tracecase
  fixtures/bundles/causal-gap-observed.tracecase
  fixtures/bundles/context-analysis-baseline.tracecase
  fixtures/bundles/context-analysis-failure.tracecase
  fixtures/bundles/duplicate-effect-analysis.tracecase
  fixtures/bundles/causal-gap-analysis.tracecase
  fixtures/bundles/semantic-context-comparison.tracecase
)

for bundle in "${bundles[@]}"; do
  python -m tracecase_cli verify "$bundle" >/dev/null
done

python -m tracecase_cli invariants fixtures/bundles/context-analysis-failure.tracecase >/dev/null
python -m tracecase_cli analyze fixtures/bundles/duplicate-effect-analysis.tracecase >/dev/null
python -m tracecase_cli compare \
  fixtures/bundles/context-analysis-baseline.tracecase \
  fixtures/bundles/context-analysis-failure.tracecase >/dev/null
python -m compileall -q packages apps/api scripts
node scripts/check_workbench_syntax.cjs

if [[ -d apps/workbench/node_modules ]]; then
  (cd apps/workbench && npm run build)
else
  echo "Workbench dependency tree unavailable; full npm build deferred to CI."
fi

echo "Milestone C validation passed."
