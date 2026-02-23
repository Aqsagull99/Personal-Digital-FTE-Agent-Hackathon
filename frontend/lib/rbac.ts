export type UserRole = "admin" | "finance" | "ops_reviewer" | "observer";

export type Permission =
  | "read_console"
  | "approve_actions"
  | "manual_override"
  | "watcher_control"
  | "finance_write";

export const DEFAULT_ROLE: UserRole = "observer";

export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  admin: ["read_console", "approve_actions", "manual_override", "watcher_control", "finance_write"],
  finance: ["read_console", "approve_actions", "finance_write"],
  ops_reviewer: ["read_console", "approve_actions"],
  observer: ["read_console"]
};

const PATH_RULES: Array<{ pattern: RegExp; allowed: UserRole[] }> = [
  { pattern: /^\/$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/dashboard(?:\/.*)?$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/tiers(?:\/.*)?$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/watchers-status(?:\/.*)?$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/auth$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/unauthorized$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/accounting(?:\/.*)?$/, allowed: ["admin", "finance", "observer"] },
  { pattern: /^\/execution(?:\/.*)?$/, allowed: ["admin", "ops_reviewer", "observer"] },
  { pattern: /^\/oversight(?:\/.*)?$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/approvals(?:\/.*)?$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/compliance(?:\/.*)?$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/health(?:\/.*)?$/, allowed: ["admin", "ops_reviewer", "observer"] },
  { pattern: /^\/monitor(?:\/.*)?$/, allowed: ["admin", "ops_reviewer", "observer"] },
  { pattern: /^\/briefings(?:\/.*)?$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/logs(?:\/.*)?$/, allowed: ["admin", "finance", "ops_reviewer", "observer"] },
  { pattern: /^\/inbox(?:\/.*)?$/, allowed: ["admin", "ops_reviewer", "observer"] }
];

export function isValidRole(value: string | null | undefined): value is UserRole {
  return value === "admin" || value === "finance" || value === "ops_reviewer" || value === "observer";
}

export function canAccessPath(role: UserRole, pathname: string): boolean {
  const rule = PATH_RULES.find((item) => item.pattern.test(pathname));
  if (!rule) return true;
  return rule.allowed.includes(role);
}

export function hasPermission(role: UserRole, permission: Permission): boolean {
  return ROLE_PERMISSIONS[role].includes(permission);
}
