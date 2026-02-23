"use client";

import { getCurrentRole } from "@/lib/auth-client";
import { hasPermission, type Permission } from "@/lib/rbac";

export function PermissionGuard({
  permission,
  fallback,
  children
}: {
  permission: Permission;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}): JSX.Element {
  const role = getCurrentRole();
  if (!hasPermission(role, permission)) {
    return <>{fallback ?? null}</>;
  }
  return <>{children}</>;
}
