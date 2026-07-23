from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from tracecase_model import TimeObservation, build_core_schema_catalog


def test_time_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        TimeObservation(raw_timestamp=datetime(2026, 1, 1))


def test_uncertainty_must_be_nonnegative() -> None:
    with pytest.raises(ValidationError):
        TimeObservation(
            raw_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            uncertainty=timedelta(milliseconds=-1),
        )


def test_schema_catalog_contains_core_case() -> None:
    catalog = build_core_schema_catalog()
    names = {entry.model_name for entry in catalog.entries}
    assert "ExecutionCase" in names
    assert "ExecutionNode" in names
    assert "Effect" in names
