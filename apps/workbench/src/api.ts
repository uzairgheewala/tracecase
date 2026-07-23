import type { CaseDetail, CaseSummary, GraphPayload } from "./types";

const API_BASE = import.meta.env.VITE_TRACECASE_API_BASE ?? "http://localhost:8000/api";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
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

export function getGraph(caseId: string): Promise<GraphPayload> {
  return request<GraphPayload>(`/cases/${encodeURIComponent(caseId)}/graph`);
}

export function getValidation(caseId: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/cases/${encodeURIComponent(caseId)}/validation`);
}
