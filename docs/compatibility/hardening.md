# Compatibility and hardening

## Format support

The initial support policy reads Tracecase bundle format `1.0.0` directly and declares a lossless migration path from the seeded `0.9.0` manifest shape. Unknown versions are reported as unknown rather than optimistically accepted.

## Health scanning

A health report combines:

- missing indexed paths;
- checksum mismatches;
- unexpected files;
- malformed JSONL streams;
- per-stream record counts;
- recoverability classification;
- recommended next action.

Integrity failures never trigger in-place repair. Recovery creates a new evidence revision.

## Archive safety

Archive extraction verifies destination paths and configurable limits for:

- file count;
- total uncompressed bytes;
- individual member bytes;
- compression ratio.

## Progressive access

`BundleReader.read_jsonl_page` and `CaseQueryIndex` allow a UI or API to load bounded records and graph neighborhoods rather than materializing every visualization at once.
