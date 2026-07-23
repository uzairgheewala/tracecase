# Privacy policy and shareable export

## Policy structure

A `RedactionPolicy` declares:

- an export profile: internal, shareable or public;
- ordered rules selected by sensitivity label, key pattern or path pattern;
- a default action;
- prohibited post-transform patterns;
- referential-integrity requirements.

Supported deterministic actions are:

- retain;
- tokenize;
- digest;
- mask;
- truncate;
- remove;
- summarize;
- reject.

Rules are deliberately schema-aware. Canonical IDs and reference fields remain structurally stable unless a future migration explicitly changes the bundle graph. Data-bearing values can be transformed while their owning records and relationships remain valid.

## Three controls

### Capture minimization

Instrumentation should avoid collecting arbitrary bodies, headers, query parameters and free text. Policy export is a second boundary, not permission to overcollect.

### Classification and transformation

`PolicyEngine.inventory()` reports every traversed field, its sensitivity labels, selected action and structural status. `PolicyEngine.apply()` returns a new immutable case plus a complete transformation report.

### Export validation

`ShareableBundleExporter`:

1. loads a frozen case;
2. applies the policy;
3. rejects prohibited residual values;
4. rebuilds graph, timeline, invariants and findings from sanitized evidence;
5. copies only allowlisted safe supplements;
6. writes policy, redaction and validation artifacts;
7. verifies bundle integrity.

## Stable pseudonyms

Tokenization uses an HMAC-like keyed digest scoped to the export key. The same source value maps to the same token within exports sharing that key, permitting correlation without exposing the original value. Deployments should inject a managed key rather than use the development default.

## Shareable-bundle guarantees

A valid shareable bundle:

- contains a new case identity;
- declares the redaction policy in the specification and manifest;
- contains a transformation report and export validation report;
- contains no configured prohibited patterns;
- preserves canonical references;
- includes recomputed, integrity-covered derived artifacts;
- records supplements deliberately omitted from disclosure.
