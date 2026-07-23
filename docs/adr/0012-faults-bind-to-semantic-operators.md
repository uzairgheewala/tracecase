# ADR 0012: Concrete lab faults bind to generic semantic operators

## Status

Accepted.

## Decision

The reference application exposes concrete injection points through a `LabBinding`, while faults retain generic registry identities and expected invariants.

## Consequences

The lab can resemble a realistic application without coupling canonical models or analyzers to Django, Celery or academic-planning terminology. New applications can supply alternative bindings for the same fault families.
