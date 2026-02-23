# AI Employee Frontend (Gold Tier)

Production-grade operations console for an autonomous AI Employee platform.

## Stack

- Next.js App Router (v14)
- TypeScript
- Tailwind CSS
- SWR (live data synchronization)
- Zustand (global real-time state)
- WebSocket stream (`/ws/events`)
- Recharts (analytics)
- react-markdown + remark-gfm (vault markdown rendering)

## Theme System

- Tailwind dark mode strategy: `class`
- Theme provider: `frontend/components/theme-provider.tsx`
- Theme toggle: `frontend/components/theme-toggle.tsx`
- Header integration: `frontend/components/app-header.tsx`
- Persistent preference key: `localStorage['ai_employee_theme']`
- First-load behavior: follows `prefers-color-scheme` if no saved preference
- FOUC prevention: inline theme boot script in `frontend/app/layout.tsx`

## Core Modules

- `/` Autonomous Dashboard
- `/accounting` Accounting Panel
- `/execution` Autonomous Execution Monitor
- `/oversight` Human Oversight Center
- `/compliance` Audit & Compliance Panel
- `/health` System Health
- `/briefings` CEO Briefing Viewer
- `/logs` Activity Logs Viewer
- `/inbox` Needs Action (support module)

## Auth + RBAC (Scaffold)

- Route guard middleware: `frontend/middleware.ts`
- Role model and permissions: `frontend/lib/rbac.ts`
- Role selection page: `/auth`
- Unauthorized page: `/unauthorized`
- UI action gating: `frontend/components/permission-guard.tsx`
- Current role badge/switcher: `frontend/components/role-status.tsx`

Roles:
- `admin`
- `finance`
- `ops_reviewer`
- `observer`

Role is stored in cookie: `ae_role`.

## Backend API Contract

- `GET /healthz`
- `GET /api/executive/summary`
- `GET /api/accounting/summary`
- `GET /api/execution/monitor`
- `GET /api/oversight/queue`
- `GET /api/compliance/panel`
- `GET /api/system/monitor`
- `GET /api/system/health`
- `GET /api/logs`
- `GET /api/briefings`
- `GET /api/briefings/{id}`
- `GET /api/tasks`
- `GET /api/tasks/{id}`
- `GET /api/approvals`
- `GET /api/approvals/{id}`
- `POST /api/approvals/{id}/approve`
- `POST /api/approvals/{id}/reject`
- `GET /api/watchers`
- `POST /api/watchers/{name}/start`
- `POST /api/watchers/{name}/stop`
- `POST /api/watchers/{name}/restart`
- `WS /ws/events`

## Runtime

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

`.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

No runtime mock data is used.
