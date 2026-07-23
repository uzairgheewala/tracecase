# ADR 0014 — Minimization uses an external preservation oracle

The minimizer does not embed invariant, analyzer, or domain logic. Callers supply a deterministic preservation predicate, and the minimizer records every accepted and rejected reduction.
