import type {
  AnalysisReport,
  AssembledGraph,
  CaseDetail,
  CaseSummary,
  GeneratedScenario,
  ScenarioFamily,
  SemanticComparison,
  PrivacyPolicy,
  FieldInventory,
  RedactionReport,
  ShareableExportResult,
  LabBinding,
  LabRunResult,
  LabComparisonResult,
  TimelineModel,
  CoverageLedger,
  BundleHealthResponse,
  PathforgeBinding,
  PathforgeRunPayload,
  PathforgeComparisonPayload,
} from "./types";

const API_BASE = import.meta.env.VITE_TRACECASE_API_BASE ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => undefined) as { detail?: string } | undefined;
    throw new Error(payload?.detail ?? `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function listCases(): Promise<CaseSummary[]> {
  const payload = await request<{ items: CaseSummary[] }>("/cases");
  return payload.items;
}

export function getCase(caseId: string): Promise<CaseDetail> {
  return request<CaseDetail>(`/cases/${encodeURIComponent(caseId)}`);
}

export function getAssembledGraph(caseId: string): Promise<AssembledGraph> {
  return request<AssembledGraph>(`/cases/${encodeURIComponent(caseId)}/assembled-graph`);
}

export function getTimeline(caseId: string): Promise<TimelineModel> {
  return request<TimelineModel>(`/cases/${encodeURIComponent(caseId)}/timeline`);
}

export function getValidation(caseId: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/cases/${encodeURIComponent(caseId)}/validation`);
}

export async function listScenarioFamilies(): Promise<ScenarioFamily[]> {
  const payload = await request<{ items: ScenarioFamily[] }>("/scenario-families");
  return payload.items;
}

export function generateScenario(payload: Record<string, unknown>): Promise<GeneratedScenario> {
  return request<GeneratedScenario>("/scenario-generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function getAnalysis(caseId: string): Promise<AnalysisReport> {
  return request<AnalysisReport>(`/cases/${encodeURIComponent(caseId)}/analysis`);
}

export function compareCases(baselineCaseId: string, candidateCaseId: string): Promise<SemanticComparison> {
  return request<SemanticComparison>("/comparisons", {
    method: "POST",
    body: JSON.stringify({ baseline_case_id: baselineCaseId, candidate_case_id: candidateCaseId }),
  });
}


export async function listPrivacyPolicies(): Promise<PrivacyPolicy[]> {
  const payload = await request<{ items: PrivacyPolicy[] }>("/privacy-policies");
  return payload.items;
}

export function getPrivacyInventory(caseId: string, policyId: string): Promise<FieldInventory> {
  return request<FieldInventory>(`/cases/${encodeURIComponent(caseId)}/privacy-inventory`, {
    method: "POST", body: JSON.stringify({ policy_id: policyId }),
  });
}

export function previewRedaction(caseId: string, policyId: string): Promise<RedactionReport> {
  return request<RedactionReport>(`/cases/${encodeURIComponent(caseId)}/redaction-preview`, {
    method: "POST", body: JSON.stringify({ policy_id: policyId }),
  });
}

export function exportShareable(caseId: string, policyId: string): Promise<ShareableExportResult> {
  return request<ShareableExportResult>(`/cases/${encodeURIComponent(caseId)}/shareable-export`, {
    method: "POST", body: JSON.stringify({ policy_id: policyId }),
  });
}

export async function listLabBindings(): Promise<LabBinding[]> {
  const payload = await request<{ items: LabBinding[] }>("/lab-bindings");
  return payload.items;
}

export function runLab(payload: Record<string, unknown>): Promise<LabRunResult> {
  return request<LabRunResult>("/lab-runs", { method: "POST", body: JSON.stringify(payload) });
}

export function compareLab(payload: Record<string, unknown>): Promise<LabComparisonResult> {
  return request<LabComparisonResult>("/lab-comparisons", { method: "POST", body: JSON.stringify(payload) });
}

export function persistLab(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/lab-runs/persist", { method: "POST", body: JSON.stringify(payload) });
}


export function getCoverageReport(): Promise<CoverageLedger> {
  return request<CoverageLedger>("/coverage");
}

export function getBundleHealth(caseId: string): Promise<BundleHealthResponse> {
  return request<BundleHealthResponse>(`/cases/${encodeURIComponent(caseId)}/health`);
}

export async function listPathforgeBindings(): Promise<PathforgeBinding[]> {
  const payload = await request<{ items: PathforgeBinding[] }>("/pathforge-bindings");
  return payload.items;
}

export function runPathforge(payload: Record<string, unknown>): Promise<PathforgeRunPayload> {
  return request<PathforgeRunPayload>("/pathforge-runs", { method: "POST", body: JSON.stringify(payload) });
}

export function comparePathforge(payload: Record<string, unknown>): Promise<PathforgeComparisonPayload> {
  return request<PathforgeComparisonPayload>("/pathforge-comparisons", { method: "POST", body: JSON.stringify(payload) });
}
