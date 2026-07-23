from __future__ import annotations
import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from django.conf import settings


def emit(event_id: str, *, component: str, operation: str, node_kind: str, status: str = "ok", parent_event_id: str | None = None, identities: dict | None = None, attributes: dict | None = None, sensitive_attributes: dict | None = None) -> None:
    record = {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "operation": operation,
        "node_kind": node_kind,
        "status": status,
        "parent_event_id": parent_event_id,
        "identities": identities or {},
        "attributes": attributes or {},
        "sensitive_attributes": sensitive_attributes or {},
    }
    path = Path(settings.TRACECASE_EVENT_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
