import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PREFIXES = ["/_next", "/favicon.ico", "/robots.txt"];
const DEFAULT_ROLE = "observer";
const VALID_ROLES = new Set(["admin", "finance", "ops_reviewer", "observer"]);

const PATH_RULES: Array<{ pattern: RegExp; allowed: Set<string> }> = [
  { pattern: /^\/$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/dashboard(?:\/.*)?$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/tiers(?:\/.*)?$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/watchers-status(?:\/.*)?$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/auth$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/unauthorized$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/accounting(?:\/.*)?$/, allowed: new Set(["admin", "finance", "observer"]) },
  { pattern: /^\/execution(?:\/.*)?$/, allowed: new Set(["admin", "ops_reviewer", "observer"]) },
  { pattern: /^\/oversight(?:\/.*)?$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/approvals(?:\/.*)?$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/compliance(?:\/.*)?$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/health(?:\/.*)?$/, allowed: new Set(["admin", "ops_reviewer", "observer"]) },
  { pattern: /^\/monitor(?:\/.*)?$/, allowed: new Set(["admin", "ops_reviewer", "observer"]) },
  { pattern: /^\/briefings(?:\/.*)?$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/logs(?:\/.*)?$/, allowed: new Set(["admin", "finance", "ops_reviewer", "observer"]) },
  { pattern: /^\/inbox(?:\/.*)?$/, allowed: new Set(["admin", "ops_reviewer", "observer"]) }
];

function resolveRole(req: NextRequest): string {
  const raw = req.cookies.get("ae_role")?.value;
  return raw && VALID_ROLES.has(raw) ? raw : DEFAULT_ROLE;
}

function canAccessPath(role: string, pathname: string): boolean {
  const rule = PATH_RULES.find((item) => item.pattern.test(pathname));
  if (!rule) return true;
  return rule.allowed.has(role);
}

export function middleware(req: NextRequest): NextResponse {
  const { pathname } = req.nextUrl;

  if (PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }

  const role = resolveRole(req);

  if (!canAccessPath(role, pathname)) {
    const url = req.nextUrl.clone();
    url.pathname = "/unauthorized";
    url.searchParams.set("from", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api).*)"]
};
