export interface CaseSummary {
  case_id: string;
  bundle_id: string;
  title: string;
  category: string;
  lifecycle: string;
  path: string;
  valid: boolean;
  node_count: number;
  relation_count: number;
  effect_count: number;
  warning_count: number;
  finding_count: number;
  violated_invariant_count: number;
  scenario_family?: string;
}

export interface CaseDetail {
  manifest: Record<string, unknown> & {
    scenario?: { family_ref?: string };
  };
  specification: {
    case_id: string;
    title: string;
    category: string;
    description?: string;
  };
  system: SystemModel;
  summary: Record<string, number>;
  scenario?: ScenarioInstance;
  oracle?: OracleOutcome[];
  ground_truth_available: boolean;
}

export interface SystemModel {
  system_id?: string;
  name: string;
  components: Array<{
    component_id: string;
    name: string;
    kind: string;
    role?: string;
  }>;
  boundaries: Array<Record<string, unknown>>;
  resources: Array<Record<string, unknown>>;
}

export interface TimeObservation {
  raw_timestamp: string;
  normalized_timestamp?: string;
  clock_ref?: string;
  uncertainty?: string;
}

export interface GraphNode {
  node_id: string;
  kind: string;
  operation: string;
  component_ref: string;
  status: string;
  boundary_refs: string[];
  context_refs: string[];
  state_refs: string[];
  effect_refs: string[];
  observation_refs: string[];
  timing: TimeObservation;
  end_time?: TimeObservation;
  identities: Record<string, unknown>;
  attributes: Record<string, unknown>;
}

export interface GraphRelation {
  relation_id: string;
  kind: string;
  source_ref: string;
  target_ref: string;
  derivation: string;
  confidence?: { score: number; rationale?: string };
  evidence_refs: string[];
}

export interface ContextFlow {
  flow_id: string;
  qualified_name: string;
  source_context_ref: string;
  target_context_ref: string;
  source_node_ref: string;
  target_node_ref: string;
  status: string;
  derivation: string;
}

export interface EffectGroup {
  group_id: string;
  logical_effect_key: string;
  member_effect_refs: string[];
  durable_count: number;
  idempotency_keys: string[];
}

export interface GraphWarning {
  warning_id: string;
  code: string;
  message: string;
  node_refs: string[];
  relation_refs: string[];
}

export interface AssembledGraph {
  graph_id: string;
  execution_id: string;
  nodes: GraphNode[];
  relations: GraphRelation[];
  source_relation_refs: string[];
  derived_relation_refs: string[];
  identity_groups: Array<{
    group_id: string;
    kind: string;
    identity_value: string;
    member_node_refs: string[];
  }>;
  context_flows: ContextFlow[];
  effect_groups: EffectGroup[];
  temporal_constraints: Array<Record<string, unknown>>;
  report: {
    source_relation_count: number;
    derived_relation_count: number;
    disconnected_components: string[][];
    warnings: GraphWarning[];
  };
}

export interface TimelineEntry {
  entry_id: string;
  node_ref: string;
  component_ref: string;
  operation: string;
  node_kind: string;
  status: string;
  start_offset_ms: number;
  duration_ms: number;
  uncertainty_ms: number;
  attempt?: number;
}

export interface TimelineModel {
  timeline_id: string;
  execution_id: string;
  origin_timestamp: string;
  total_duration_ms: number;
  lanes: Array<{
    lane_id: string;
    component_ref: string;
    label: string;
    entries: TimelineEntry[];
  }>;
  connectors: Array<{
    connector_id: string;
    relation_ref: string;
    source_entry_ref: string;
    target_entry_ref: string;
    relation_kind: string;
    derivation: string;
  }>;
  warnings: GraphWarning[];
}

export interface ScenarioFamily {
  family_id: string;
  title: string;
  description: string;
  family_class: string;
  universe_axes: string[];
  topology_ref: string;
  parameter_domains: Array<Record<string, unknown>>;
  fault_operators: string[];
  invariants: string[];
  observability_profiles: string[];
}

export interface ScenarioInstance {
  instance_id: string;
  scenario_ref: string;
  family_ref: string;
  seed: number;
  resolved_parameters: Record<string, unknown>;
  faults: Array<Record<string, unknown>>;
  observability_profile: string;
  coverage_points: string[];
  instance_digest: string;
}

export interface OracleOutcome {
  invariant_ref: string;
  expected_status: string;
  basis: string;
  scope_ref?: string;
}

export interface GeneratedScenario {
  definition: Record<string, unknown>;
  instance: ScenarioInstance;
  oracle: OracleOutcome[];
  ground_truth_summary: Record<string, number>;
  observed_case: {
    specification: CaseDetail["specification"];
    system: SystemModel;
    execution: Record<string, unknown>;
  };
  graph: AssembledGraph;
  timeline: TimelineModel;
}

export interface InvariantResult {
  result_id: string;
  invariant_ref: string;
  scope_kind: string;
  scope_ref: string;
  status: string;
  severity: string;
  evidence_classification: string;
  evidence_refs: string[];
  node_refs: string[];
  relation_refs: string[];
  context_refs: string[];
  effect_refs: string[];
  counterexample_refs: string[];
  missing_evidence: string[];
  confidence: { score: number; rationale?: string };
  explanation: string;
  attributes: Record<string, unknown>;
}

export interface InvariantReport {
  report_id: string;
  case_id: string;
  graph_id: string;
  results: InvariantResult[];
  summary: Record<string, number>;
}

export interface Finding {
  finding_id: string;
  analyzer_ref: string;
  category: string;
  classification: string;
  title: string;
  summary: string;
  severity: string;
  evidence_classification: string;
  confidence: { score: number; rationale?: string };
  related_invariant_result_refs: string[];
  evidence_refs: string[];
  node_refs: string[];
  relation_refs: string[];
  context_refs: string[];
  effect_refs: string[];
  conflicting_evidence_refs: string[];
  limitations: string[];
  recommended_inspection_points: string[];
  attributes: Record<string, unknown>;
}

export interface AnalysisReport {
  report_id: string;
  case_id: string;
  graph_id: string;
  invariant_report: InvariantReport;
  findings: Finding[];
  summary: Record<string, number>;
  limitations: string[];
}

export interface NodeAlignment {
  alignment_id: string;
  baseline_node_ref?: string;
  candidate_node_ref?: string;
  status: string;
  score: number;
  confidence: { score: number; rationale?: string };
  reasons: string[];
  baseline_signature?: { node_ref: string; node_kind: string; normalized_operation: string; component_kind: string; topology_role?: string; stage?: number };
  candidate_signature?: { node_ref: string; node_kind: string; normalized_operation: string; component_kind: string; topology_role?: string; stage?: number };
  ambiguous_candidate_refs: string[];
}

export interface Divergence {
  divergence_id: string;
  dimension: string;
  classification: string;
  title: string;
  summary: string;
  severity: string;
  consequence: string;
  evidence_classification: string;
  confidence: { score: number; rationale?: string };
  alignment_ref?: string;
  baseline_refs: string[];
  candidate_refs: string[];
  baseline_evidence_refs: string[];
  candidate_evidence_refs: string[];
  temporal_rank_ms?: number;
  consequential: boolean;
  limitations: string[];
  attributes: Record<string, unknown>;
}

export interface SemanticComparison {
  comparison_id: string;
  baseline: { role: string; case_id: string; graph_id: string };
  candidate: { role: string; case_id: string; graph_id: string };
  alignments: NodeAlignment[];
  divergences: Divergence[];
  first_meaningful_divergence_ref?: string;
  summary: {
    aligned_nodes: number;
    baseline_only_nodes: number;
    candidate_only_nodes: number;
    ambiguous_alignments: number;
    divergence_count: number;
    consequential_divergence_count: number;
    by_dimension: Record<string, number>;
    first_meaningful_divergence_ref?: string;
  };
  limitations: string[];
}

export interface PrivacyPolicy {
  policy_id: string;
  version: string;
  title: string;
  profile: string;
  default_action: string;
  rules: Array<{ rule_id: string; action: string; path_glob: string; priority: number; description: string }>;
  prohibited_patterns: string[];
}

export interface InventoryItem {
  path: string;
  value_type: string;
  labels: string[];
  matched_rule_ref?: string;
  proposed_action: string;
  preview: string;
  structural: boolean;
}

export interface FieldInventory {
  inventory_id: string;
  case_id: string;
  policy_ref: string;
  items: InventoryItem[];
  by_label: Record<string, number>;
  by_action: Record<string, number>;
}

export interface RedactionReport {
  report_id: string;
  case_id: string;
  policy_ref: string;
  profile: string;
  transformations: Array<{
    transformation_id: string;
    path: string;
    action: string;
    rule_ref?: string;
    labels: string[];
    replacement_preview?: string;
    removed: boolean;
  }>;
  violations: Array<{ violation_id: string; code: string; severity: string; path: string; message: string; preview?: string }>;
  removed_paths: string[];
  token_count: number;
  valid_for_export: boolean;
  summary: Record<string, number>;
}

export interface ShareableExportResult {
  source_case_id: string;
  exported_case_id: string;
  bundle_path: string;
  archive_path?: string;
  policy_ref: string;
  redaction_report: RedactionReport;
  validation_report: {
    valid: boolean;
    violations: Array<Record<string, unknown>>;
    scanned_values: number;
    prohibited_matches: number;
    integrity_valid?: boolean;
  };
}

export interface LabBinding {
  binding_id: string;
  family_ref: string;
  title: string;
  description: string;
  supported_faults: string[];
  topology_roles: string[];
  invariant_refs: string[];
  runtime_modes: string[];
}

export interface LabRunResult {
  receipt: {
    run_id: string;
    binding_ref: string;
    mode: string;
    status: string;
    fault_operator_ref?: string;
    observability_fault_ref?: string;
    event_count: number;
    case_id: string;
  };
  case: {
    specification: CaseDetail["specification"];
    system: SystemModel;
    evidence: { execution: Record<string, unknown> };
  };
  graph: AssembledGraph;
  timeline: TimelineModel;
  analysis: AnalysisReport;
  events: Array<Record<string, unknown>>;
}

export interface LabComparisonResult {
  baseline: LabRunResult;
  candidate: LabRunResult;
  comparison: SemanticComparison;
}

export interface CoveragePoint {
  point_id: string;
  dimension: string;
  key: string;
  status: string;
  family_ref?: string;
  witness_refs: string[];
  rationale?: string;
}

export interface CoverageLedger {
  ledger_id: string;
  registry_version: string;
  points: CoveragePoint[];
  recommendations: Array<{
    recommendation_id: string;
    family_ref: string;
    priority: number;
    uncovered_point_refs: string[];
    suggested_fault_ref?: string;
    suggested_observability_profile?: string;
    rationale: string;
  }>;
  summary: Record<string, number>;
  attributes: Record<string, unknown>;
}

export interface BundleHealthResponse {
  compatibility: {
    assessment_id: string;
    bundle_ref: string;
    status: string;
    format_version: string;
    supported_format_versions: string[];
    issues: Array<{ code: string; severity: string; message: string; path?: string }>;
    extension_namespaces: string[];
    recommended_actions: string[];
  };
  health: {
    report_id: string;
    bundle_ref: string;
    valid: boolean;
    missing_paths: string[];
    mismatched_paths: string[];
    unexpected_paths: string[];
    malformed_jsonl: string[];
    record_counts: Record<string, number>;
    recoverable: boolean;
    recommendations: string[];
  };
}

export interface PathforgeBinding {
  binding_id: string;
  workflow_kind: string;
  title: string;
  extension_namespace: string;
  generic_invariants: string[];
  domain_event_types: string[];
}

export interface PathforgeRunPayload {
  result: {
    binding: PathforgeBinding;
    case_id: string;
    graph_id: string;
    invariant_summary: Record<string, number>;
    finding_count: number;
    deep_link: string;
    attributes: Record<string, unknown>;
  };
  case: Record<string, unknown>;
}

export interface PathforgeComparisonPayload {
  baseline: Record<string, unknown>;
  candidate: Record<string, unknown>;
  comparison: SemanticComparison;
}
