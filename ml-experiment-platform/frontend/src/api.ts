import type { Artifact, CompareRow, LogEvent, MetricPoint, Run } from './types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listRuns: () => request<Run[]>('/runs'),
  startDemo: (taskType: string) => request<Run>(`/runs/demo/start?task_type=${taskType}`, { method: 'POST' }),
  startRun: (runId: string) => request<Run>(`/runs/${runId}/start`, { method: 'POST' }),
  getRun: (runId: string) => request<Run>(`/runs/${runId}`),
  getMetrics: (runId: string) => request<MetricPoint[]>(`/runs/${runId}/metrics`),
  getLogs: (runId: string) => request<LogEvent[]>(`/runs/${runId}/logs`),
  getArtifacts: (runId: string) => request<Artifact[]>(`/runs/${runId}/artifacts`),
  compare: (ids: string[]) => request<CompareRow[]>(`/compare?ids=${ids.join(',')}`),
  eventsUrl: (runId: string) => `${API_URL}/events/${runId}`,
};
