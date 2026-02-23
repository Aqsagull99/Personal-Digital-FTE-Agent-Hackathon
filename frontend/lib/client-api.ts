"use client";

import { API_BASE_URL } from "@/lib/runtime";
import { getCurrentRole } from "@/lib/auth-client";
import type {
  AccountingSummaryResponse,
  ActionResponse,
  ApprovalItem,
  BriefingDetail,
  BriefingFile,
  CompliancePanelResponse,
  DraftHistoryItem,
  ExecutionMonitorResponse,
  ExecutiveSummary,
  LogRecord,
  OversightQueueResponse,
  AiLoopStatus,
  SystemHealthResponse,
  SystemMonitor,
  TaskDetail,
  TaskItem,
  WatcherControlItem,
  WatcherControlResponse
} from "@/lib/types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const roleHeader = getCurrentRole();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": roleHeader,
      ...(init?.headers || {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function fetchHealthz(): Promise<{ status: string }> {
  return request<{ status: string }>("/healthz");
}

export async function fetchExecutiveSummary(): Promise<ExecutiveSummary> {
  return request<ExecutiveSummary>("/api/executive/summary");
}

export async function fetchSystemMonitor(): Promise<SystemMonitor> {
  return request<SystemMonitor>("/api/system/monitor");
}

export async function fetchAccountingSummary(): Promise<AccountingSummaryResponse> {
  return request<AccountingSummaryResponse>("/api/accounting/summary");
}

export async function fetchExecutionMonitor(): Promise<ExecutionMonitorResponse> {
  return request<ExecutionMonitorResponse>("/api/execution/monitor");
}

export async function fetchOversightQueue(): Promise<OversightQueueResponse> {
  return request<OversightQueueResponse>("/api/oversight/queue");
}

export async function fetchCompliancePanel(): Promise<CompliancePanelResponse> {
  return request<CompliancePanelResponse>("/api/compliance/panel?limit=400");
}

export async function fetchSystemHealth(): Promise<SystemHealthResponse> {
  return request<SystemHealthResponse>("/api/system/health");
}

export async function fetchTasks(): Promise<TaskItem[]> {
  return request<TaskItem[]>("/api/tasks?limit=300");
}

export async function fetchTaskDetail(taskId: string): Promise<TaskDetail> {
  return request<TaskDetail>(`/api/tasks/${encodeURIComponent(taskId)}`);
}

export async function fetchApprovals(): Promise<ApprovalItem[]> {
  return request<ApprovalItem[]>("/api/approvals?limit=300");
}

export async function fetchApprovalDetail(id: string): Promise<ApprovalItem> {
  return request<ApprovalItem>(`/api/approvals/${encodeURIComponent(id)}`);
}

export async function approveItem(id: string): Promise<ActionResponse> {
  return request<ActionResponse>(`/api/approvals/${encodeURIComponent(id)}/approve`, { method: "POST" });
}

export async function rejectItem(id: string): Promise<ActionResponse> {
  return request<ActionResponse>(`/api/approvals/${encodeURIComponent(id)}/reject`, { method: "POST" });
}

export async function fetchWatchers(): Promise<WatcherControlItem[]> {
  return request<WatcherControlItem[]>("/api/watchers");
}

export async function startWatcher(name: string): Promise<WatcherControlResponse> {
  return request<WatcherControlResponse>(`/api/watchers/start?name=${encodeURIComponent(name)}`, { method: "POST" });
}

export async function stopWatcher(name: string): Promise<WatcherControlResponse> {
  return request<WatcherControlResponse>(`/api/watchers/stop?name=${encodeURIComponent(name)}`, { method: "POST" });
}

export async function restartWatcher(name: string): Promise<WatcherControlResponse> {
  return request<WatcherControlResponse>(`/api/watchers/${encodeURIComponent(name)}/restart`, { method: "POST" });
}

export async function fetchLogs(params: {
  channel?: "email" | "payment" | "social" | "system" | "file" | "other";
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}): Promise<LogRecord[]> {
  const query = new URLSearchParams();
  if (params.channel) query.set("channel", params.channel);
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);
  query.set("limit", String(params.limit ?? 300));
  return request<LogRecord[]>(`/api/logs?${query.toString()}`);
}

export async function fetchBriefings(): Promise<BriefingFile[]> {
  return request<BriefingFile[]>("/api/briefings");
}

export async function fetchBriefingDetail(id: string): Promise<BriefingDetail> {
  return request<BriefingDetail>(`/api/briefings/${encodeURIComponent(id)}`);
}

export async function runAiTask(payload: {
  prompt: string;
  title?: string;
  priority?: "low" | "medium" | "high";
  source?: string;
}): Promise<ActionResponse> {
  return request<ActionResponse>("/api/ai/run-task", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function createEmailDraft(payload: {
  to: string;
  subject: string;
  body: string;
}): Promise<ActionResponse> {
  return request<ActionResponse>("/api/ai/create-draft", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function requestEmailApproval(payload: {
  to: string;
  subject: string;
  body: string;
}): Promise<ActionResponse> {
  return request<ActionResponse>("/api/ai/email/request-approval", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function fetchDraftHistory(limit = 20): Promise<DraftHistoryItem[]> {
  return request<DraftHistoryItem[]>(`/api/ai/drafts?limit=${limit}`);
}

export async function fetchAiLoopStatus(): Promise<AiLoopStatus> {
  return request<AiLoopStatus>("/api/ai/loop/status");
}

export async function startAiLoop(params?: { task?: string; maxIterations?: number }): Promise<ActionResponse> {
  const query = new URLSearchParams();
  if (params?.task) query.set("task", params.task);
  if (params?.maxIterations) query.set("max_iterations", String(params.maxIterations));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<ActionResponse>(`/api/ai/loop/start${suffix}`, { method: "POST" });
}

export async function stopAiLoop(): Promise<ActionResponse> {
  return request<ActionResponse>("/api/ai/loop/stop", { method: "POST" });
}

export async function processApprovedNow(): Promise<ActionResponse> {
  return request<ActionResponse>("/api/ai/process-approved", { method: "POST" });
}

export async function processAllNow(): Promise<ActionResponse> {
  return request<ActionResponse>("/api/ai/process-all", { method: "POST" });
}

export async function cleanupNeedsAction(pattern: string, dryRun = false): Promise<{
  status: "success" | "error";
  message: string;
  deletedCount: number;
  matchedCount: number;
  pattern: string;
}> {
  return request(`/api/maintenance/cleanup-needs-action?pattern=${encodeURIComponent(pattern)}&dry_run=${String(dryRun)}`, {
    method: "POST"
  });
}
