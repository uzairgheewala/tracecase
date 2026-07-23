from django.db import models

class ImportRun(models.Model):
    workflow_id = models.CharField(max_length=128, unique=True)
    tenant_id = models.CharField(max_length=128)
    principal_id = models.CharField(max_length=128)
    status = models.CharField(max_length=32, default="accepted")
    schema_version = models.CharField(max_length=16, default="1.0")
    fault_operator = models.CharField(max_length=160, blank=True)
    course_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

class Enrollment(models.Model):
    import_run = models.ForeignKey(ImportRun, on_delete=models.CASCADE, related_name="enrollments")
    course_code = models.CharField(max_length=32)
    grade = models.CharField(max_length=8, blank=True)
    idempotency_key = models.CharField(max_length=160)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["import_run", "course_code", "idempotency_key"], name="unique_import_course_effect")]
