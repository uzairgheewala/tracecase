# ADR 0010: Minimize at capture, classify before export

## Status

Accepted.

## Decision

Tracecase treats collection minimization and export redaction as separate mandatory controls. Sensitive capture is never justified solely because a later redaction engine exists.

## Consequences

Adapters and SDKs should use allowlists. Bundles retain sensitivity labels. Shareable export inventories every field and rejects residual prohibited values.
