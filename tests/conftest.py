from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def generated_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from tracecase_bundle import BundleBuilder

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_sample_bundle.py"
    spec = importlib.util.spec_from_file_location("sample_bundle", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path_factory.mktemp("bundles") / "sample.tracecase"
    builder = BundleBuilder(output)
    builder.build(module.build_case())
    return output
