# Pathforge integration

## Boundary

The Pathforge integration is delivered in `tracecase-pathforge`; it is not compiled into the Tracecase core. All Pathforge-specific values live under the `pathforge.academic` namespace.

## Initial bindings

- `pathforge.requirement-audit.v1`
- `pathforge.integration-reconciliation.v1`

The requirement-audit demo maps Pathforge stages to generic request, domain-operation, and write nodes. Tenant continuity and durable audit persistence are represented with ordinary Tracecase contexts and effects.

## Deep links

`PathforgeTraceBridge.deep_link` produces URL-addressable investigation links that can identify a case and optionally a selected node or finding.

## Generic analysis

The tenant-loss demonstration is detected through the existing context-continuity invariant and analyzer. Baseline and candidate runs align through the existing semantic comparison engine. No Pathforge-specific condition is added to those engines.
