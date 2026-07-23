# Bounded analyzer contract

Analyzers convert invariant results and graph patterns into investigator-facing findings. A finding is an interpretation, never source evidence.

Every finding includes:

- analyzer ID and version;
- generic classification and category;
- severity and evidence classification;
- confidence with rationale;
- related invariant-result references;
- supporting and conflicting evidence references;
- node, relation, context, and effect references;
- limitations;
- recommended inspection points.

The initial analyzer pack covers context continuity, identity integrity, retry/effect behavior, transaction ordering, observability integrity, resource amplification, and contract/privacy concerns.

Analyzer output is deterministic for a frozen case, graph, registry, and configuration. Human suppression or annotation is additive workspace state and does not delete the original finding.
