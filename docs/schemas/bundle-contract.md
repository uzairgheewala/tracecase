# Portable bundle contract v1

A directory-form bundle uses the `.tracecase` suffix. A ZIP transport may use `.tracecase.zip`; unpacking restores the same directory contract.

## Entry points

- `manifest.json`
- `integrity/content_index.json`
- `integrity/checksums.json`
- `specification/case.json`
- `schemas/schema_catalog.json`

## Digest design

The manifest is intentionally excluded from its own digest graph. `content_index.json`, `checksums.json`, and the validation report are also excluded from payload indexing to avoid recursive hashes.

The content index covers semantic payload files beneath:

- specification;
- provenance;
- evidence;
- model;
- analysis;
- comparison;
- policy;
- reports;
- schemas.

`evidence_digest` hashes the canonical list of specification, provenance, evidence, and model content entries. `bundle_digest` hashes all indexed content entries.

## Freeze semantics

After build:

- the manifest lifecycle is `frozen`;
- evidence files are not editable by contract;
- mutation is detected by verification;
- later analysis will be additive and identify its input evidence digest;
- corrected evidence requires a new case version or bundle revision.
