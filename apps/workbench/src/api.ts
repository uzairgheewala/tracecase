import type {
  AssembledGraph,
  CaseDetail,
  CaseSummary,
  GeneratedScenario,
  ScenarioFamily,
  TimelineModel,
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
