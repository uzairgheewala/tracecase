export interface CaseSummary {
  case_id: string;
  bundle_id: string;
  title: string;
  category: string;
  lifecycle: string;
  path: string;
  valid: boolean;
  node_count: number;
  effect_count: number;
}

export interface CaseDetail {
  manifest: Record<string, unknown>;
  specification: {
    case_id: string;
    title: string;
    category: string;
    description?: string;
  };
  system: {
    name: string;
    components: Array<{ component_id: string; name: string; kind: string }>;
    boundaries: Array<Record<string, unknown>>;
    resources: Array<Record<string, unknown>>;
  };
  summary: Record<string, number>;
}

export interface GraphNode {
  node_id: string;
  kind: string;
  operation: string;
  component_ref: string;
  status: string;
  context_refs: string[];
  effect_refs: string[];
  observation_refs: string[];
  timing: { raw_timestamp: string; normalized_timestamp?: string };
}

export interface GraphRelation {
  relation_id: string;
  kind: string;
  source_ref: string;
  target_ref: string;
  derivation: string;
}

export interface GraphPayload {
  nodes: GraphNode[];
  relations: GraphRelation[];
  contexts: Array<Record<string, unknown>>;
  state_facts: Array<Record<string, unknown>>;
  effects: Array<Record<string, unknown>>;
}
