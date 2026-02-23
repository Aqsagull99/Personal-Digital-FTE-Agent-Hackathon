export type TaskPriority = "low" | "medium" | "high";
export type TaskStatus = "pending" | "in_progress" | "approved" | "done";

export type TaskItem = {
  id: string;
  type: string;
  title: string;
  source: string;
  received: string;
  priority: TaskPriority;
  status: TaskStatus;
  preview: string;
};

export type TaskDetail = TaskItem & {
  body: string;
  metadata: Record<string, string>;
  filePath: string;
};

export type ApprovalItem = {
  id: string;
  action: string;
  target: string;
  amount?: number;
  reason: string;
  requestedAt: string;
  riskLevel: "low" | "medium" | "high";
};

export type AuditItem = {
  id: string;
  actionType: string;
  actor: string;
  target: string;
  status: "success" | "failed";
  timestamp: string;
};

export type HealthItem = {
  name: string;
  status: "healthy" | "degraded" | "offline";
  lastSeen: string;
  interval: string;
};

export type WatcherControlItem = {
  name: string;
  script: string;
  running: boolean;
  pid?: number;
  logFile: string;
  lastActivity?: string;
};

export type WatcherControlResponse = {
  status: "success" | "error";
  message: string;
  watcher?: WatcherControlItem;
};

export type ActionResponse = {
  status: "success" | "error";
  message: string;
  fromPath?: string;
  toPath?: string;
};

export type AiLoopStatus = {
  running: boolean;
  pid?: number;
  startedAt?: string;
  task?: string;
  logFile: string;
};

export type DraftHistoryItem = {
  timestamp: string;
  to: string;
  subject: string;
  draftId?: string;
  status: "success" | "failed";
};

export type RevenuePoint = {
  date: string;
  value: number;
};

export type ExecutiveSummary = {
  revenueTotal: number;
  revenueSeries: RevenuePoint[];
  activeTaskCount: number;
  pendingApprovals: number;
  completedTaskCount: number;
  watchersRunning: number;
  watchersStopped: number;
  watcherHealth: HealthItem[];
  recentActivity: AuditItem[];
};

export type LogRecord = {
  id: string;
  timestamp: string;
  actionType: string;
  channel: "email" | "payment" | "social" | "system" | "file" | "other";
  actor: string;
  status: "success" | "failed";
  raw: Record<string, unknown>;
};

export type SystemMonitor = {
  claudeStatus: "running" | "idle" | "unknown";
  watcherStatus: WatcherControlItem[];
  watcherHealth: HealthItem[];
  lastExecutionTime?: string;
  loopIterationCount: number;
  errorAlerts: LogRecord[];
};

export type SystemHealthResponse = {
  watchdogStatus: "healthy" | "degraded" | "offline";
  cpuLoadPercent: number;
  processStatus: WatcherControlItem[];
  queueSize: Record<string, number>;
};

export type AccountingSummaryResponse = {
  monthlyRevenue: RevenuePoint[];
  currentMonthRevenue: number;
  subscriptionRevenue: number;
  flaggedCosts: LogRecord[];
  erpSyncStatus: "healthy" | "degraded" | "offline";
};

export type ExecutionTask = {
  id: string;
  title: string;
  status: string;
  source: string;
  progress: number;
};

export type ExecutionMonitorResponse = {
  runningTasks: ExecutionTask[];
  planVisualization: PlanItem[];
  loopIterationCount: number;
  completionPromisesDetected: number;
};

export type OversightQueueResponse = {
  highRiskActions: ApprovalItem[];
  financialApprovals: ApprovalItem[];
  socialApprovals: ApprovalItem[];
  totalPending: number;
};

export type CompliancePanelResponse = {
  actionLogs: LogRecord[];
  approvalHistory: LogRecord[];
  failureRecoveryLogs: LogRecord[];
  retryAttempts: number;
};

export type TaskLifecycleState =
  | "detected"
  | "triaged"
  | "planned"
  | "awaiting_approval"
  | "approved"
  | "executing"
  | "completed"
  | "failed";

export const TASK_STATE_TRANSITIONS: Record<TaskLifecycleState, TaskLifecycleState[]> = {
  detected: ["triaged", "failed"],
  triaged: ["planned", "awaiting_approval", "failed"],
  planned: ["executing", "awaiting_approval", "failed"],
  awaiting_approval: ["approved", "failed"],
  approved: ["executing", "failed"],
  executing: ["completed", "failed"],
  completed: [],
  failed: ["triaged", "planned", "executing"]
};

export type BriefingFile = {
  id: string;
  title: string;
  date: string;
  weekLabel: string;
  filePath: string;
};

export type BriefingDetail = {
  id: string;
  title: string;
  date: string;
  weekLabel: string;
  markdown: string;
  filePath: string;
};

export type PlanItem = {
  id: string;
  title: string;
  progress: number;
  owner: string;
  dueDate: string;
  steps: { label: string; done: boolean }[];
};
