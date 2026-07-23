from tracecase_sdk import EffectRecord, InMemorySink, SDKEventKind, TracecaseSDK

def test_sdk_context_operations_and_effects():
    sink=InMemorySink(); sdk=TracecaseSDK("test-service",sink)
    with sdk.bind_context(trace_id="trace-1",workflow_id="workflow-1",tenant_id="tenant-a"):
        with sdk.operation("student.audit"):
            sdk.domain_event("audit.generated",count=3)
            sdk.effect(EffectRecord(logical_effect_key="audit/1",operation="persist audit",durability="durable"))
    assert [event.kind for event in sink.events]==[SDKEventKind.OPERATION_START,SDKEventKind.DOMAIN_EVENT,SDKEventKind.EFFECT,SDKEventKind.OPERATION_END]
    assert all(event.context.tenant_id=="tenant-a" for event in sink.events)
    assert sink.events[1].parent_event_id==sink.events[0].event_id
