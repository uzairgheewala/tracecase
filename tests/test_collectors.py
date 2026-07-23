from __future__ import annotations

from tracecase_collectors import (
    CollectionCoordinator,
    CollectionRequest,
    CollectionSelector,
    OtelJsonAdapter,
)


def _otel_records(tenant: str = "tenant-alpha"):
    return [
        {
            "traceId": "trace-1",
            "spanId": "span-parent",
            "name": "POST /imports",
            "kind": "SPAN_KIND_SERVER",
            "startTimeUnixNano": "1721736000000000000",
            "endTimeUnixNano": "1721736000100000000",
            "resource_attributes": {"service.name": "academic-api"},
            "attributes": {
                "workflow.id": "workflow-1",
                "tenant.id": tenant,
                "http.route": "/imports",
            },
        },
        {
            "traceId": "trace-1",
            "spanId": "span-child",
            "parentSpanId": "span-parent",
            "name": "normalize task",
            "kind": "SPAN_KIND_CONSUMER",
            "startTimeUnixNano": "1721736000200000000",
            "endTimeUnixNano": "1721736000300000000",
            "resource_attributes": {"service.name": "import-worker"},
            "attributes": {
                "workflow.id": "workflow-1",
                "tenant.id": tenant,
                "task.id": "task-1",
                "task.attempt": 1,
            },
        },
    ]


def test_otel_adapter_preserves_parentage_and_provenance() -> None:
    request = CollectionRequest(
        request_id="collection.test.otel",
        selectors=(CollectionSelector(kind="trace_id", value="trace-1"),),
        tenant_scope="tenant-alpha",
    )
    result = CollectionCoordinator([OtelJsonAdapter(_otel_records())]).collect(request)
    assert not result.partial
    assert len(result.merged.nodes) == 2
    assert len(result.merged.observations) == 2
    assert any(relation.kind.value == "parent_of" for relation in result.merged.relations)
    assert all(item.provenance.source_id == "source.otel-json" for item in result.merged.observations)


def test_tenant_scope_violation_isolated_as_partial_adapter_failure() -> None:
    request = CollectionRequest(
        request_id="collection.test.scope",
        selectors=(CollectionSelector(kind="trace_id", value="trace-1"),),
        tenant_scope="tenant-alpha",
    )
    result = CollectionCoordinator([OtelJsonAdapter(_otel_records("tenant-beta"))]).collect(request)
    assert result.partial
    assert not result.fragments
    assert result.adapter_status["adapter.otel-json"] == "failed"
    assert result.diagnostics[0].code == "adapter_failed"
