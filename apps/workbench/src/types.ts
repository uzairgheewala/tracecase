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
