from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[1]
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "reference-lab-only")
DEBUG = True
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = ["django.contrib.contenttypes", "rest_framework", "workflow"]
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "tracecase_lab",
        "USER": "tracecase",
        "PASSWORD": "tracecase",
        "HOST": "postgres",
        "PORT": "5432",
    }
}
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "0") == "1"
MOCK_SIS_URL = os.environ.get("MOCK_SIS_URL", "http://localhost:8020")
TRACECASE_EVENT_LOG = os.environ.get("TRACECASE_EVENT_LOG", str(BASE_DIR / "events.jsonl"))
TRACECASE_LAB_FAULTS_ENABLED = os.environ.get("TRACECASE_LAB_FAULTS_ENABLED", "0") == "1"
