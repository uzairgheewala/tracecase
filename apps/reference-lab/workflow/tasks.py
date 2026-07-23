from __future__ import annotations
import requests
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .faults import FaultContext
from .models import Enrollment, ImportRun
from .telemetry import emit

@shared_task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=2)
def normalize_transcript(self, import_run_id: int, context: dict, courses: list[str], fault_operator: str | None = None):
    fault = FaultContext(fault_operator)
    tenant_id = None if fault.enabled("fault.context.drop.v1") else context.get("tenant_id")
    identities = {**context, "tenant_id": tenant_id, "task_id": self.request.id, "task_attempt": self.request.retries + 1}
    if fault.enabled("fault.observability.break-link.v1"):
        identities.pop("trace_id", None)
        identities.pop("parent_span_id", None)
    emit("worker.normalize", component="celery-worker", operation="transcript.normalize", node_kind="task_attempt", parent_event_id="api.publish", identities=identities)
    run = ImportRun.objects.get(pk=import_run_id)
    schema = "2.0" if fault.enabled("fault.contract.schema-skew.v1") else run.schema_version
    emit("external.extract", component="mock-sis", operation="transcript.extract", node_kind="external_request", parent_event_id="worker.normalize", identities=identities, attributes={"schema_version": schema})
    response = requests.post(f"{settings.MOCK_SIS_URL}/extract", json={"courses": courses, "schema_version": schema}, timeout=5)
    response.raise_for_status()
    extracted = response.json()["courses"]
    with transaction.atomic():
        for course in extracted:
            Enrollment.objects.get_or_create(import_run=run, course_code=course["course_code"], idempotency_key=f"import-{run.pk}", defaults={"grade": course.get("grade", "")})
        run.course_count = len(extracted)
        run.status = "completed"
        run.completed_at = timezone.now()
        run.save(update_fields=["course_count", "status", "completed_at"])
    emit("projection.write", component="postgres", operation="enrollment_projection.write", node_kind="write", parent_event_id="external.extract", identities=identities, attributes={"rows": len(extracted), "idempotency_key": f"import-{run.pk}"})
    emit("audit.recompute", component="audit-service", operation="degree_audit.recompute", node_kind="domain_operation", parent_event_id="projection.write", identities=identities, attributes={"stale_read": fault.enabled("fault.consistency.stale-cache.v1")})
    emit("notification.send", component="notification-service", operation="import.completed.notify", node_kind="notification", parent_event_id="audit.recompute", identities=identities)
    if fault.enabled("fault.effect.duplicate.v1") and self.request.retries == 0:
        normalize_transcript.apply_async(args=[import_run_id, context, courses, fault_operator], countdown=0)
    if fault.enabled("fault.external.timeout-after-effect.v1") and self.request.retries == 0:
        raise requests.Timeout("injected timeout after durable projection")
    return {"import_run_id": run.pk, "status": run.status, "course_count": run.course_count}
