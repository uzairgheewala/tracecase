.PHONY: test validate sample clean

PYTHONPATH := packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-cli/src

validate:
	./scripts/validate.sh

test:
	PYTHONPATH=$(PYTHONPATH) pytest

sample:
	PYTHONPATH=$(PYTHONPATH) python scripts/generate_sample_bundle.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
