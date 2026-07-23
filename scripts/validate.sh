#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-scenarios/src:packages/tracecase-collectors/src:packages/tracecase-graph/src:packages/tracecase-invariants/src:packages/tracecase-analyzers/src:packages/tracecase-compare/src:packages/tracecase-policy/src:packages/tracecase-lab/src:packages/tracecase-cli/src"

python scripts/check_architecture.py
python scripts/generate_sample_bundle.py
python scripts/generate_milestone_b_fixtures.py
python scripts/generate_milestone_c_fixtures.py
python scripts/generate_milestone_d_fixtures.py
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
  fixtures/bundles/reference-lab-baseline.tracecase
  fixtures/bundles/reference-lab-context-loss.tracecase
  fixtures/bundles/reference-lab-duplicate-effect.tracecase
  fixtures/bundles/reference-lab-publish-before-commit.tracecase
  fixtures/bundles/reference-lab-privacy-capture.tracecase
  fixtures/bundles/reference-lab-observability-gap.tracecase
  fixtures/bundles/reference-lab-context-comparison.tracecase
  fixtures/bundles/reference-lab-shareable.tracecase
)

for bundle in "${bundles[@]}"; do
  python -m tracecase_cli verify "$bundle" >/dev/null
done

archives=(
  fixtures/bundles/reference-lab-baseline.tracecase.zip
  fixtures/bundles/reference-lab-context-loss.tracecase.zip
  fixtures/bundles/reference-lab-duplicate-effect.tracecase.zip
  fixtures/bundles/reference-lab-publish-before-commit.tracecase.zip
  fixtures/bundles/reference-lab-privacy-capture.tracecase.zip
  fixtures/bundles/reference-lab-observability-gap.tracecase.zip
  fixtures/bundles/reference-lab-context-comparison.tracecase.zip
  fixtures/bundles/reference-lab-shareable.tracecase.zip
)
for archive in "${archives[@]}"; do
  python -m tracecase_cli verify "$archive" >/dev/null
done

python -m tracecase_cli invariants fixtures/bundles/reference-lab-context-loss.tracecase >/dev/null
python -m tracecase_cli analyze fixtures/bundles/reference-lab-duplicate-effect.tracecase >/dev/null
python -m tracecase_cli compare \
  fixtures/bundles/reference-lab-baseline.tracecase \
  fixtures/bundles/reference-lab-context-loss.tracecase >/dev/null
python -m tracecase_cli policy-list >/dev/null
python -m tracecase_cli privacy-inventory fixtures/bundles/reference-lab-privacy-capture.tracecase --policy policy.shareable.v1 >/dev/null
python -m tracecase_cli redaction-preview fixtures/bundles/reference-lab-privacy-capture.tracecase --policy policy.shareable.v1 >/dev/null
python -m tracecase_cli lab-bindings >/dev/null
python -m tracecase_cli lab-run --seed 901 --fault fault.effect.duplicate.v1 >/dev/null
python -m tracecase_cli lab-compare --seed 902 --fault fault.context.drop.v1 >/dev/null

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
python -m tracecase_cli export-shareable \
  fixtures/bundles/reference-lab-privacy-capture.tracecase \
  "$TMP_ROOT/shareable.tracecase" \
  --archive "$TMP_ROOT/shareable.tracecase.zip" \
  --policy policy.shareable.v1 >/dev/null
python -m tracecase_cli verify "$TMP_ROOT/shareable.tracecase" >/dev/null
python -m tracecase_cli verify "$TMP_ROOT/shareable.tracecase.zip" >/dev/null

python -m compileall -q packages apps/api apps/reference-lab scripts
node scripts/check_workbench_syntax.cjs

if [[ -d apps/workbench/node_modules ]]; then
  (cd apps/workbench && npm run build)
else
  echo "Workbench dependency tree unavailable; full npm build deferred to CI."
fi

echo "Milestone D validation passed."
