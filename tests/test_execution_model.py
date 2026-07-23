from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from tracecase_model import (
    ExecutionModel,
    ExecutionNode,
    NodeKind,
    TimeObservation,
)


def test_unknown_node_reference_is_rejected() -> None:
    node = ExecutionNode(
        node_id="node.one",
        kind=NodeKind.SERVICE_OPERATION,
        operation="test",
        component_ref="component.test",
        context_refs=("context.missing",),
        timing=TimeObservation(raw_timestamp=datetime.now(timezone.utc)),
    )
    with pytest.raises(ValidationError, match="unknown node node.one context"):
        ExecutionModel(execution_id="execution.invalid", nodes=(node,))


def test_canonical_ids_are_globally_unique() -> None:
    node = ExecutionNode(
        node_id="shared.id",
        kind=NodeKind.SERVICE_OPERATION,
        operation="test",
        component_ref="component.test",
        timing=TimeObservation(raw_timestamp=datetime.now(timezone.utc)),
    )
    from tracecase_model import Observation, ObservationKind, ProvenanceRef

    observation = Observation(
        observation_id="shared.id",
        kind=ObservationKind.LOG,
        provenance=ProvenanceRef(source_id="source.test"),
        captured_at=datetime.now(timezone.utc),
    )
    with pytest.raises(ValidationError, match="globally unique"):
        ExecutionModel(
            execution_id="execution.invalid",
            nodes=(node,),
            observations=(observation,),
        )
