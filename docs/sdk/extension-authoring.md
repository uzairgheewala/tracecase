# SDK and extension authoring

## Minimal instrumentation

```python
from tracecase_sdk import EffectRecord, InMemorySink, TracecaseSDK

sink = InMemorySink()
sdk = TracecaseSDK("audit-service", sink)

with sdk.bind_context(
    trace_id="trace-123",
    workflow_id="audit-456",
    tenant_id="institution-alpha",
):
    with sdk.operation("audit.solve"):
        sdk.domain_event("audit.candidates.generated", count=42)
        sdk.effect(
            EffectRecord(
                logical_effect_key="audit-result/456",
                operation="persist audit",
                durability="durable",
            )
        )
```

Operation contexts use `contextvars`, so nested and asynchronous Python execution can inherit the current Tracecase context without global mutable state.

## Plugin contracts

Adapter and analyzer plugins declare stable `plugin_id` and `plugin_version` values. `PluginRegistry` rejects duplicate `(id, version)` registrations.

Plugins should emit or consume canonical contracts and keep technology-specific values under a namespaced extension. They must not mutate frozen source evidence.
