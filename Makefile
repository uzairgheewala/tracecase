.PHONY: test validate sample milestone-b-fixtures milestone-c-fixtures milestone-d-fixtures clean

PYTHONPATH := packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-scenarios/src:packages/tracecase-collectors/src:packages/tracecase-graph/src:packages/tracecase-invariants/src:packages/tracecase-analyzers/src:packages/tracecase-compare/src:packages/tracecase-policy/src:packages/tracecase-lab/src:packages/tracecase-cli/src

validate:
	./scripts/validate.sh

test:
	PYTHONPATH=$(PYTHONPATH) pytest

sample:
	PYTHONPATH=$(PYTHONPATH) python scripts/generate_sample_bundle.py

milestone-b-fixtures:
	PYTHONPATH=$(PYTHONPATH) python scripts/generate_milestone_b_fixtures.py

milestone-c-fixtures:
	PYTHONPATH=$(PYTHONPATH) python scripts/generate_milestone_c_fixtures.py

milestone-d-fixtures:
	PYTHONPATH=$(PYTHONPATH) python scripts/generate_milestone_d_fixtures.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache apps/workbench/dist
