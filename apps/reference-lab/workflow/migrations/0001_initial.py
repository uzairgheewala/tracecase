from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="ImportRun", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("workflow_id", models.CharField(max_length=128, unique=True)),
            ("tenant_id", models.CharField(max_length=128)),
            ("principal_id", models.CharField(max_length=128)),
            ("status", models.CharField(default="accepted", max_length=32)),
            ("schema_version", models.CharField(default="1.0", max_length=16)),
            ("fault_operator", models.CharField(blank=True, max_length=160)),
            ("course_count", models.PositiveIntegerField(default=0)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("completed_at", models.DateTimeField(blank=True, null=True)),
        ]),
        migrations.CreateModel(name="Enrollment", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("course_code", models.CharField(max_length=32)),
            ("grade", models.CharField(blank=True, max_length=8)),
            ("idempotency_key", models.CharField(max_length=160)),
            ("import_run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="workflow.importrun")),
        ]),
        migrations.AddConstraint(model_name="enrollment", constraint=models.UniqueConstraint(fields=("import_run", "course_code", "idempotency_key"), name="unique_import_course_effect")),
    ]
