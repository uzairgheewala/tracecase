from __future__ import annotations
import uuid
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .faults import SUPPORTED_FAULTS, FaultContext
from .models import ImportRun
from .tasks import normalize_transcript
from .telemetry import emit

@api_view(["POST"])
def import_transcript(request):
    fault_operator = request.data.get("fault_operator")
    if fault_operator and fault_operator not in SUPPORTED_FAULTS:
        return Response({"detail": "unsupported fault"}, status=status.HTTP_400_BAD_REQUEST)
    workflow_id = request.data.get("workflow_id") or f"workflow-{uuid.uuid4()}"
    tenant_id = request.data.get("tenant_id", "institution-alpha")
    principal_id = request.data.get("principal_id", "student-1001")
    courses = request.data.get("courses", ["DSC100", "DSC180A", "DSC180B"])
    trace_id = uuid.uuid4().hex
    context = {"workflow_id": workflow_id, "trace_id": trace_id, "tenant_id": tenant_id, "principal_id": principal_id, "request_id": uuid.uuid4().hex}
    sensitive = {"student_email": request.data.get("student_email", "student@example.edu")}
    if FaultContext(fault_operator).enabled("fault.privacy.capture-secret.v1"):
        sensitive["authorization"] = request.headers.get("Authorization", "Bearer injected-secret")
    emit("browser.upload", component="browser", operation="transcript.upload", node_kind="user_action", identities=context)
    emit("api.request", component="django-api", operation="transcript_import.request", node_kind="request_handler", parent_event_id="browser.upload", identities=context, sensitive_attributes=sensitive)
    with transaction.atomic():
        run = ImportRun.objects.create(workflow_id=workflow_id, tenant_id=tenant_id, principal_id=principal_id, fault_operator=fault_operator or "")
        emit("db.transaction", component="postgres", operation="import_run.transaction", node_kind="transaction", parent_event_id="api.request", identities={**context, "transaction_id": f"tx-{run.pk}"})
        def publish():
            result = normalize_transcript.delay(run.pk, context, courses, fault_operator)
            emit("api.publish", component="django-api", operation="transcript_import.publish", node_kind="message_publish", parent_event_id="db.transaction", identities={**context, "task_id": result.id, "message_id": result.id})
        if FaultContext(fault_operator).enabled("fault.ordering.publish-before-commit.v1"):
            publish()
        else:
            transaction.on_commit(publish)
    return Response({"import_run_id": run.pk, "workflow_id": workflow_id, "status": run.status}, status=status.HTTP_202_ACCEPTED)

@api_view(["GET"])
def import_status(_request, import_run_id: int):
    run = ImportRun.objects.get(pk=import_run_id)
    return Response({"id": run.pk, "workflow_id": run.workflow_id, "status": run.status, "course_count": run.course_count, "fault_operator": run.fault_operator})
