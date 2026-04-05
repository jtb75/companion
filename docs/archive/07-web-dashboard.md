# 07 — Web Dashboard

> Companion is an AI-powered independence assistant for adults with developmental disabilities.
> The user is called "Sam." The AI assistant is called "D.D."
> This document is the authoritative specification for the web dashboard — a React SPA
> serving the Caregiver Dashboard, Ops Dashboard, and Config Admin under a single deployment.

---

## 1. Overview

The web dashboard is a React (Vite) single-page application deployed alongside the backend. It serves three audiences through three sub-applications that share auth, layout, and API client code:

1. **Caregiver Dashboard** — for trusted contacts (family, case workers, agency staff). Consumes the existing Caregiver API defined in `04-api-design.md` and the privacy model defined in `06-caregiver-access-and-privacy.md`.
2. **Ops Dashboard** — for the internal Companion team. Pipeline health, escalation monitoring, pilot metrics.
3. **Config Admin** — for the internal team. Runtime configuration management for D.D. prompts, pipeline thresholds, notification settings, voice profiles.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Web Dashboard (Vite SPA)                      │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │ Caregiver Dash   │  │ Ops Dashboard    │  │ Config Admin      │  │
│  │ /caregiver/*     │  │ /ops/*           │  │ /admin/*          │  │
│  │                  │  │                  │  │                   │  │
│  │ - Alerts         │  │ - Pipeline       │  │ - Prompts         │  │
│  │ - Dashboard      │  │ - Escalations    │  │ - Thresholds      │  │
│  │ - Activity Log   │  │ - Metrics        │  │ - Voices          │  │
│  │                  │  │                  │  │ - Notifications   │  │
│  │                  │  │                  │  │ - Settings        │  │
│  │                  │  │                  │  │ - Audit Log       │  │
│  │                  │  │                  │  │ - Admin Users     │  │
│  │                  │  │                  │  │ - Users           │  │
│  │                  │  │                  │  │ - People          │  │
│  │                  │  │                  │  │ - Contacts        │  │
│  │                  │  │                  │  │ - Conversations   │  │
│  │                  │  │                  │  │ - Workers         │  │
│  └───────┬──────────┘  └───────┬──────────┘  └────────┬──────────┘  │
│          │                     │                      │              │
│  ┌───────┴──────────────────────┴──────────────────────┴──────────┐  │
│  │                    Shared Infrastructure                       │  │
│  │  Auth (Firebase)  ·  API Client  ·  Layout  ·  React Query    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTPS
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
  ┌────────────────┐ ┌──────────┐ ┌───────────────────┐
  │ Caregiver API  │ │ Admin API│ │ Cloud Monitoring   │
  │ /api/v1/       │ │ /api/v1/ │ │ API                │
  │ caregiver/*    │ │ admin/*  │ │                    │
  └────────────────┘ └──────────┘ └───────────────────┘
```

---

## 2. Technology Stack

| Component    | Choice                                      | Rationale                                                                                  |
|--------------|---------------------------------------------|--------------------------------------------------------------------------------------------|
| Framework    | React 18+ with Vite                         | Fast builds, same component model as React Native (share design tokens), lightweight       |
| Routing      | React Router v6                             | Sub-app routing under `/caregiver`, `/ops`, `/admin`                                       |
| State        | React Query (TanStack Query)                | Server-state caching, auto-refresh for dashboard polling, optimistic updates for config    |
| Styling      | Tailwind CSS                                | Utility-first, fast iteration, responsive by default                                       |
| Charts       | Recharts or Tremor                          | Lightweight charting for ops metrics                                                       |
| Auth         | Firebase Auth JS SDK                        | Same auth provider as mobile; separate tenants for caregiver vs admin                      |
| Build/Deploy | Vite build → Cloud Run (static) or CDN      | Static assets served from the same Cloud Run service or Cloud Storage + Cloud CDN          |

---

## 3. Caregiver Dashboard

### 3.1 Auth Flow

- Firebase Auth (**caregiver tenant**)
- Login via email/password or magic link
- JWT includes `tier`, `user_id`, `contact_id`, `scopes`
- Tier determines which pages and components render
- A caregiver JWT **cannot** access `/ops/*` or `/admin/*` routes — enforced by separate Firebase tenants

### 3.2 Page Inventory

#### Tier 1 — Alerts Page (`/caregiver/alerts`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET /api/v1/caregiver/alerts`                                         |
| Access          | Tier 1+                                                                |
| Refresh         | Auto-refresh every 60 seconds via React Query `refetchInterval`        |

Content:

- List of active safety alerts
- Each alert shows: type icon, plain-language message, timestamp, suggested action
- **Read-only** — no dismiss or acknowledge capability
- Empty state: *"No alerts. Sam is managing well."*

#### Tier 2 — Dashboard Page (`/caregiver/dashboard`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET /api/v1/caregiver/dashboard`                                      |
| Access          | Tier 2+                                                                |
| Refresh         | Auto-refresh every 5 minutes                                           |

Summary cards rendered directly from API response (no client-side aggregation):

| Card                  | Example rendering                                         |
|-----------------------|-----------------------------------------------------------|
| Status                | "Sam is managing well this week" or "2 items need attention" |
| Today's tasks         | Completed count / total (e.g., "3 of 4 completed") — **not** a raw checklist |
| Medication adherence  | Percentage bar (e.g., "92% this week")                    |
| Upcoming bills        | Count handled vs pending — no dollar amounts unless Sam shared |
| Upcoming appointments | Date/time list — no provider details unless Sam shared    |
| Active urgent items   | Count + category                                          |

All data is **pre-summarized by the API**. The dashboard renders exactly what the API returns. No raw data. No client-side aggregation.

#### Tier 2 — Activity Log (`/caregiver/activity`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET /api/v1/caregiver/activity` (reads `caregiver_activity_log`)      |
| Access          | Tier 2+                                                                |
| Refresh         | On page load                                                           |

Content:

- The caregiver's **own** activity log — what they have viewed and when
- Example entry: *"You viewed the dashboard on March 27 at 2:15 PM"*
- Purpose: transparency. The caregiver knows their access is logged.

### 3.3 Design Principles

> **Note:** The Collaboration View (`/caregiver/collaborate/:scope_id`, `CollaboratePage.tsx`) described in the original spec has not been implemented in the current build. The caregiver sub-app currently has three pages: Alerts, Dashboard, and Activity.

- **Mobile-first responsive** — case workers use phones and tablets
- **Large text, high contrast** — accessible by default (WCAG AA minimum)
- **No raw data** — only API-summarized views. Ever.
- **Calm, professional tone** — not the warm D.D. tone. This UI is for professionals.
- Every page shows the footer banner: *"Sam controls what you can see. Contact Sam to change your access level."*

---

## 4. Ops Dashboard

### 4.1 Auth Flow

- Firebase Auth (**admin tenant**) — completely separate from caregiver tenant
- Roles: `viewer`, `editor`, `admin`
- All roles can view all ops pages
- No caregiver JWT can reach these routes

### 4.2 Page Inventory

#### Pipeline Health (`/ops/pipeline`)

| Attribute       | Detail                                                                  |
|-----------------|-------------------------------------------------------------------------|
| Data source     | `GET /api/v1/admin/pipeline/health`, `/metrics`, `/failures`            |
| Access          | Admin JWT (any role)                                                    |
| Refresh         | Every 15 seconds                                                        |

Content:

- **Status board**: documents in flight (count per stage)
- **Success rate**: per stage, bar chart with 24h / 7d / 30d toggle
- **Processing time**: average per stage, line chart over time
- **Failed documents**: list with error details and a **Retry** button
- **Classification confidence**: distribution histogram
- **Alerts panel**: stuck documents (in stage > 5 min), failure rate spike, confidence drop

#### Escalation Monitor (`/ops/escalations`)

| Attribute       | Detail                                                                  |
|-----------------|-------------------------------------------------------------------------|
| Data source     | `GET /api/v1/admin/escalations`, `/history`, `/stats`                   |
| Access          | Admin JWT (any role)                                                    |
| Refresh         | Every 30 seconds                                                        |

Content:

- Open questions grouped by urgency level (card layout)
- Questions approaching escalation threshold (countdown timers)
- Escalation history timeline (last 30 days)
- Stats: escalation rate by type, avg time to resolution, most common trigger categories

#### Pilot Metrics (`/ops/metrics`)

| Attribute       | Detail                                                                  |
|-----------------|-------------------------------------------------------------------------|
| Data source     | `GET /api/v1/admin/metrics/*`                                           |
| Access          | Admin JWT (any role)                                                    |
| Refresh         | Every 5 minutes                                                         |

Content (maps directly to the pilot outcome package):

| Metric Group         | Visualizations                                                       |
|----------------------|----------------------------------------------------------------------|
| Engagement           | DAU / WAU / MAU, session frequency histogram, section usage breakdown |
| Onboarding funnel    | started -> voice selected -> priority chosen -> first win -> complete (funnel chart) |
| Retention cohorts    | 48h return rate, 7d, 30d (cohort table)                              |
| Morning check-in     | Acknowledgment rate over time, skip rate, avg response time          |
| Document intelligence| Total processed, classification distribution (pie), confidence trend |

> **Note:** The System Health page (`/ops/system`, `SystemPage.tsx`) described in the original spec has not been implemented in the current build. The ops sub-app currently has three pages: Pipeline, Escalations, and Metrics.

### 4.3 Design Principles

- **Desktop-optimized** — ops team works on laptops
- **Dense layout** — more data per screen than the caregiver dashboard
- **Color-coded status**: green / yellow / red for all health indicators
- Auto-refresh intervals are per-page (see table above), implemented via React Query `refetchInterval`
- **No PII** — all user data is aggregated. No individual user records appear anywhere in the ops dashboard.

---

## 5. Config Admin

### 5.1 Auth Flow

- Same admin tenant as Ops Dashboard
- Requires `editor` or `admin` role — `viewer` can see all pages but cannot save changes
- All mutations require the `reason` field (enforced in UI and API)
- All changes are audit-logged

### 5.2 Page Inventory

#### Prompt Management (`/admin/prompts`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET/PATCH /api/v1/admin/config` (category: `arlo_persona`, `summarization_prompt`) |
| Access          | Editor or Admin                                                        |

Content:

- List all `arlo_persona` and `summarization_prompt` configs
- Editor with syntax highlighting for prompt text
- Side-by-side diff view when editing (old value vs new value)
- **"Test prompt"** button: sends a test input through the conversation service, displays D.D.'s response inline
- Version history with rollback capability
- Every save requires a `reason` field (free-text, minimum 10 characters)
- Confirmation dialog before save: *"Changing the D.D. persona prompt affects all active users. Are you sure?"*

#### Pipeline Thresholds (`/admin/thresholds`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET/PATCH /api/v1/admin/config` (category: `pipeline_threshold`)      |
| Access          | Editor or Admin                                                        |

Content:

- Classification confidence thresholds (slider inputs, range 0.0 - 1.0):
  - Junk cutoff
  - "Unknown" threshold
  - Tier 1 vs Tier 2 classifier boundary
- Each slider shows the **current value** alongside a chart of the **last 7 days of classification distribution**, so the operator can see the impact before changing
- Every save requires a `reason` field

> **Note:** The Escalation Rules page (`/admin/escalation`, `EscalationRulesPage.tsx`) described in the original spec has been removed. Escalation configuration is now managed through the Settings page.

#### ~~Escalation Rules (`/admin/escalation`)~~ — Removed

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET/PATCH /api/v1/admin/config` (category: `escalation_threshold`)    |
| Access          | Editor or Admin                                                        |

Content — editable table:

| Question Type            | Escalation Rule                             |
|--------------------------|---------------------------------------------|
| Routine check-in         | No escalation                               |
| Medication confirmation  | X missed confirmations -> alert             |
| Bill action needed       | X days before due date -> alert             |
| Appointment reminder     | X missed acknowledgments -> alert           |
| Safety concern           | Immediate escalation                        |

- Every save requires a `reason` field
- Confirmation dialog: *"Changing escalation thresholds affects when caregivers are notified. Are you sure?"*

#### Voice Profiles (`/admin/voices`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET/PATCH /api/v1/admin/config` (category: `arlo_voice`)             |
| Access          | Editor or Admin                                                        |

Content:

- Four voice profile cards: **Warm**, **Calm**, **Bright**, **Clear**
- Editable TTS parameters per profile:
  - `voice_name` (dropdown from available TTS voices)
  - `pitch` (slider)
  - `speaking_rate` (slider)
  - `volume_gain_db` (slider)
- **"Preview"** button: generates sample TTS audio via the TTS service and plays it in the browser
- Every save requires a `reason` field

#### Notification Defaults (`/admin/notifications`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET/PATCH /api/v1/admin/config` (category: `notification_default`)    |
| Access          | Editor or Admin                                                        |

Content:

- Default quiet hours: start time picker, end time picker
- Default morning check-in time
- Notification batching rules (e.g., batch non-urgent notifications every N minutes)
- Every save requires a `reason` field

> **Note:** The Email Pre-filter Rules page (`/admin/email-rules`, `EmailRulesPage.tsx`) described in the original spec has been removed. Email filtering configuration is now managed through the Settings page.

#### ~~Email Pre-filter Rules (`/admin/email-rules`)~~ — Removed

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET/PATCH /api/v1/admin/config` (category: `email_prefilter`)         |
| Access          | Editor or Admin                                                        |

Content:

- Table of sender/domain patterns classified as junk
- Add / remove rules
- Each rule shows its **hit count** (how many emails the rule filtered in the last 30 days)
- Every save requires a `reason` field

#### Audit Log (`/admin/audit`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET /api/v1/admin/config/audit`                                       |
| Access          | Any admin role (viewer, editor, admin)                                 |

Content:

- Full config change history across all categories
- Filterable by: category, user, date range
- Each entry shows: **who** changed **what**, old value, new value, reason, timestamp
- Read-only — no edits

#### Settings (`/admin/settings`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET/PATCH /api/v1/admin/config` (various categories)                  |
| Access          | Editor or Admin                                                        |

Content: Consolidated configuration page for escalation thresholds, email pre-filter rules, and other system settings that were originally separate pages.

#### Admin Users (`/admin/admin-users`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET/POST/PATCH/DELETE /api/v1/admin/users`                            |
| Access          | Admin only                                                             |

Content: Manage internal admin accounts — create, update roles, deactivate.

#### Member Users (`/admin/users`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET /api/v1/admin/users-management`                                   |
| Access          | Editor or Admin                                                        |

Content: List and manage member (Sam) accounts — view account status, deactivation, scheduled deletion.

#### People (`/admin/people`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET /api/v1/admin/people`                                             |
| Access          | Editor or Admin                                                        |

Content: Unified view of all people in the system (members and their contacts/caregivers).

#### Contacts (`/admin/contacts`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET /api/v1/admin/contacts`                                           |
| Access          | Editor or Admin                                                        |

Content: List all trusted contacts across all members. View invitation status, access tiers.

#### Conversations (`/admin/conversations`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET /api/v1/admin/conversations`                                      |
| Access          | Editor or Admin                                                        |

Content: View conversation sessions across members — session counts, durations, message counts. No PII/transcript content.

#### Workers (`/admin/workers`)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| Data source     | `GET /api/v1/admin/workers`, `POST /api/v1/admin/workers/:name/trigger`|
| Access          | Editor or Admin                                                        |

Content: Background worker dashboard showing all registered workers, their last run time, status, and a manual trigger button. Workers include: morning_trigger, medication_reminder, escalation_check, ttl_purge, retention, away_monitor, deletion.

### 5.3 Design Principles

- **Desktop-optimized**
- **Every change requires a reason** — enforced in UI (required field) and API (400 if missing)
- **All changes are audited** — visible in the audit log immediately
- **Dangerous changes** (escalation thresholds, persona prompt) show a confirmation dialog with an impact warning
- Config changes emit events via the event bus — consuming services reload configuration without restart

---

## 6. Shared Infrastructure

### 6.1 Directory Structure

```
web/
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── .env.example                  — documents required env vars
├── src/
│   ├── main.tsx                  — app entry, router setup
│   ├── shared/
│   │   ├── api/
│   │   │   ├── client.ts         — fetch wrapper, base URL, error handling
│   │   │   ├── caregiver-api.ts  — typed functions for /api/v1/caregiver/*
│   │   │   └── admin-api.ts      — typed functions for /api/v1/admin/*
│   │   ├── auth/
│   │   │   ├── firebase.ts       — Firebase init (reads tenant from env)
│   │   │   ├── AuthProvider.tsx   — React context: current user, token, role/tier
│   │   │   └── guards.ts         — route guards: requireTier(n), requireAdminRole(role)
│   │   ├── components/           — shared UI: Shell, Nav, StatusBadge, Card, EmptyState
│   │   └── hooks/                — shared React Query hooks (useAutoRefresh, etc.)
│   ├── caregiver/
│   │   ├── CaregiverLayout.tsx   — nav, footer banner, tier-aware menu
│   │   ├── pages/
│   │   │   ├── AlertsPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   └── ActivityPage.tsx
│   │   └── components/           — SummaryCard, AlertCard
│   ├── ops/
│   │   ├── OpsLayout.tsx         — dense nav, status indicator bar
│   │   ├── pages/
│   │   │   ├── PipelinePage.tsx
│   │   │   ├── EscalationsPage.tsx
│   │   │   └── MetricsPage.tsx
│   │   └── components/           — charts, status boards, countdown timers
│   └── admin/
│       ├── AdminLayout.tsx       — nav with category links, role indicator
│       ├── pages/
│       │   ├── PromptsPage.tsx
│       │   ├── ThresholdsPage.tsx
│       │   ├── VoicesPage.tsx
│       │   ├── NotificationsPage.tsx
│       │   ├── SettingsPage.tsx
│       │   ├── AuditPage.tsx
│       │   ├── AdminUsersPage.tsx
│       │   ├── UsersPage.tsx
│       │   ├── PeoplePage.tsx
│       │   ├── ContactsPage.tsx
│       │   ├── ConversationsPage.tsx
│       │   └── WorkersPage.tsx
│       └── components/           — ConfigEditor, DiffView, AudioPreview, ReasonDialog
└── public/
    └── favicon.svg
```

### 6.2 Routing

Router setup in `main.tsx` using React Router v6 with layout routes:

```tsx
<Routes>
  {/* Caregiver sub-app — requires caregiver JWT */}
  <Route element={<RequireAuth tenant="caregiver" />}>
    <Route path="/caregiver" element={<CaregiverLayout />}>
      <Route path="alerts" element={<RequireTier min={1}><AlertsPage /></RequireTier>} />
      <Route path="dashboard" element={<RequireTier min={2}><DashboardPage /></RequireTier>} />
      <Route path="activity" element={<RequireTier min={2}><ActivityPage /></RequireTier>} />
    </Route>
  </Route>

  {/* Ops sub-app — requires admin JWT (any role) */}
  <Route element={<RequireAuth tenant="admin" />}>
    <Route path="/ops" element={<OpsLayout />}>
      <Route path="pipeline" element={<PipelinePage />} />
      <Route path="escalations" element={<EscalationsPage />} />
      <Route path="metrics" element={<MetricsPage />} />
    </Route>
  </Route>

  {/* Admin sub-app — requires admin JWT with editor or admin role */}
  <Route element={<RequireAuth tenant="admin" requiredRole={["editor", "admin"]} />}>
    <Route path="/admin" element={<AdminLayout />}>
      <Route path="prompts" element={<PromptsPage />} />
      <Route path="thresholds" element={<ThresholdsPage />} />
      <Route path="voices" element={<VoicesPage />} />
      <Route path="notifications" element={<NotificationsPage />} />
      <Route path="settings" element={<SettingsPage />} />
      <Route path="audit" element={<AuditPage />} />
      <Route path="admin-users" element={<AdminUsersPage />} />
      <Route path="users" element={<UsersPage />} />
      <Route path="people" element={<PeoplePage />} />
      <Route path="contacts" element={<ContactsPage />} />
      <Route path="conversations" element={<ConversationsPage />} />
      <Route path="workers" element={<WorkersPage />} />
    </Route>
  </Route>
</Routes>
```

Route summary:

```
/caregiver/alerts              Tier 1+
/caregiver/dashboard           Tier 2+
/caregiver/activity            Tier 2+

/ops/pipeline                  Admin JWT (any role)
/ops/escalations               Admin JWT (any role)
/ops/metrics                   Admin JWT (any role)

/admin/prompts                 Admin JWT (editor | admin)
/admin/thresholds              Admin JWT (editor | admin)
/admin/voices                  Admin JWT (editor | admin)
/admin/notifications           Admin JWT (editor | admin)
/admin/settings                Admin JWT (editor | admin)
/admin/audit                   Admin JWT (viewer | editor | admin)
/admin/admin-users             Admin JWT (editor | admin)
/admin/users                   Admin JWT (editor | admin)
/admin/people                  Admin JWT (editor | admin)
/admin/contacts                Admin JWT (editor | admin)
/admin/conversations           Admin JWT (editor | admin)
/admin/workers                 Admin JWT (editor | admin)
```

### 6.3 API Client

`shared/api/client.ts` provides:

```typescript
// Thin fetch wrapper — all API calls go through this
async function apiClient<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getFirebaseIdToken();
  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (!res.ok) throw new ApiError(res.status, await res.json());
  return res.json();
}
```

Typed wrappers in `caregiver-api.ts` and `admin-api.ts`:

```typescript
// caregiver-api.ts
export const caregiverApi = {
  getAlerts: () => apiClient<Alert[]>("/api/v1/caregiver/alerts"),
  getDashboard: () => apiClient<DashboardSummary>("/api/v1/caregiver/dashboard"),
  getActivity: () => apiClient<ActivityEntry[]>("/api/v1/caregiver/activity"),
  getScopedResource: (scopeId: string) =>
    apiClient<ScopedResource>(`/api/v1/caregiver/scopes/${scopeId}/resource`),
};

// admin-api.ts
export const adminApi = {
  getPipelineHealth: () => apiClient<PipelineHealth>("/api/v1/admin/pipeline/health"),
  getConfig: (category: string) => apiClient<ConfigEntry[]>(`/api/v1/admin/config?category=${category}`),
  patchConfig: (id: string, body: ConfigPatch) =>
    apiClient<ConfigEntry>(`/api/v1/admin/config/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  // ... etc
};
```

### 6.4 Deployment

- `vite build` produces static assets in `dist/`
- **Option A**: Serve from Cloud Run alongside the backend. The backend serves `dist/` at `/web/*`, with a catch-all to `index.html` for client-side routing.
- **Option B**: Upload `dist/` to Cloud Storage, serve via Cloud CDN. API calls go to the Cloud Run backend directly (CORS configured).
- Environment-specific config via build-time env vars:
  - `VITE_API_BASE_URL` — backend API base
  - `VITE_FIREBASE_CONFIG` — JSON string of Firebase config
  - `VITE_FIREBASE_TENANT_CAREGIVER` — caregiver tenant ID
  - `VITE_FIREBASE_TENANT_ADMIN` — admin tenant ID

---

## 7. Security Considerations

| Concern                          | Mitigation                                                                      |
|----------------------------------|---------------------------------------------------------------------------------|
| Caregiver accesses admin routes  | Separate Firebase tenants. A caregiver JWT is rejected by admin route guards before any API call. |
| Admin routes exposed publicly    | Production: IP-restricted or VPN-gated via Cloud Run ingress settings.          |
| PII in ops dashboard             | Ops endpoints return only aggregated data. No individual user records.          |
| Config change without accountability | Every mutation requires a `reason` field. All changes are audit-logged with admin user identity. |
| Stale auth                       | Firebase ID tokens expire after 1 hour. `getFirebaseIdToken()` auto-refreshes. Token revocation is immediate on role change. |
| XSS / injection                  | React's default escaping. CSP headers set by the serving layer. No `dangerouslySetInnerHTML` outside the prompt editor (which sanitizes input). |
| Caregiver sees raw data          | Architecturally impossible. The Caregiver API returns only pre-summarized data. The dashboard renders what the API returns — no additional endpoints are called. |

---

## 8. Getting Started

For a frontend engineer picking this up:

```bash
# 1. Scaffold the project
npm create vite@latest web -- --template react-ts
cd web

# 2. Install dependencies
npm install react-router-dom @tanstack/react-query firebase recharts
npm install -D tailwindcss @tailwindcss/vite

# 3. Set up env vars (copy from .env.example)
cp .env.example .env.local

# 4. Start dev server
npm run dev
```

Build order recommendation:

1. **Shared infra first**: `client.ts`, `firebase.ts`, `AuthProvider.tsx`, `guards.ts`, shell layout
2. **Caregiver Alerts page**: simplest page, proves auth flow end-to-end
3. **Caregiver Dashboard page**: proves summary card rendering
4. **Ops Pipeline page**: proves chart rendering and auto-refresh
5. **Config Admin Prompts page**: proves config CRUD, diff view, reason enforcement
6. **Remaining pages**: fill in from page inventory above

Each page maps 1:1 to API endpoints already defined. No client-side aggregation logic is needed — the API does the work.
