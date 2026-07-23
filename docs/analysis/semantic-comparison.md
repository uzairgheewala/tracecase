# Semantic execution comparison

The comparison engine aligns two canonical executions without relying on run-local span, trace, or workflow identifiers.

## Alignment

Candidate alignment uses topology role and ordinal attempt first, then a weighted semantic signature:

- normalized operation;
- node kind;
- component kind and role;
- logical operation identity;
- task name;
- topology stage.

Alignments are classified as aligned, baseline-only, candidate-only, or ambiguous. Confidence and reasons are retained.

## Divergence dimensions

The engine classifies structural, identity, context, timing, state, effect, error, resource, deployment, and evidence differences. Regenerated IDs and harmless timing jitter are suppressed.

## First meaningful divergence

A divergence is eligible when it is consequential, evidence-backed, and temporally rankable or structurally upstream. The selected result records uncertainty and limitations; it is not presented as unrestricted root-cause proof.
