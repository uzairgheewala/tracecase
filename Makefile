.PHONY: test validate sample milestone-b-fixtures clean

PYTHONPATH := packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-scenarios/src:packages/tracecase-collectors/src:packages/tracecase-graph/src:packages/tracecase-cli/src

validate:
	./scripts/validate.sh

test:
	PYTHONPATH=$(PYTHONPATH) pytest

sample:
	PYTHONPATH=$(PYTHONPATH) python scripts/generate_sample_bundle.py

milestone-b-fixtures:
	PYTHONPATH=$(PYTHONPATH) python scripts/generate_milestone_b_fixtures.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
