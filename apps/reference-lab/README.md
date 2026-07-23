# Tracecase distributed reference laboratory

This application realizes the generic Tracecase scenario families through a concrete transcript-import workflow using React-compatible HTTP calls, Django, PostgreSQL, Celery/Redis, a mock external SIS/OCR service, audit recomputation, and notification effects.

```bash
docker compose up --build
curl -X POST http://localhost:8010/api/imports \
  -H 'Content-Type: application/json' \
  -d '{"fault_operator":"fault.context.drop.v1"}'
```

Structured evidence is written to the shared `lab-evidence` volume as JSONL. Fault injection is disabled unless `TRACECASE_LAB_FAULTS_ENABLED=1`; the provided Compose file enables it only for the isolated laboratory.
