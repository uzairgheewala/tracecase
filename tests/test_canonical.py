from datetime import datetime, timezone

from tracecase_bundle import canonical_json_bytes
from tracecase_model import TimeObservation


def test_canonical_json_is_order_independent() -> None:
    left = canonical_json_bytes({"b": 2, "a": 1})
    right = canonical_json_bytes({"a": 1, "b": 2})
    assert left == right == b'{"a":1,"b":2}\n'


def test_pydantic_serialization_is_stable() -> None:
    value = TimeObservation(raw_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert canonical_json_bytes(value) == canonical_json_bytes(value.model_dump(mode="json", exclude_none=True))
