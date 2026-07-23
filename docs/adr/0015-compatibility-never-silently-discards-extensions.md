# ADR 0015 — Compatibility never silently discards extensions

Unknown namespaced extensions are preserved through reading, migration, and reserialization. A migration that cannot preserve data must declare the loss and cannot be represented as lossless.
