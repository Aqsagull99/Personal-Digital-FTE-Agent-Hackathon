"use client";

import { DEFAULT_ROLE, isValidRole, type UserRole } from "@/lib/rbac";

const ROLE_COOKIE = "ae_role";

function getCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }
  const target = `${name}=`;
  const parts = document.cookie.split(";").map((item) => item.trim());
  const found = parts.find((item) => item.startsWith(target));
  if (!found) return null;
  return decodeURIComponent(found.slice(target.length));
}

export function getCurrentRole(): UserRole {
  const raw = getCookie(ROLE_COOKIE);
  return isValidRole(raw) ? raw : DEFAULT_ROLE;
}

export function setRoleCookie(role: UserRole): void {
  if (typeof document === "undefined") {
    return;
  }
  document.cookie = `${ROLE_COOKIE}=${encodeURIComponent(role)}; path=/; max-age=2592000; samesite=lax`;
}
