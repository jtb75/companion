# 06 — Caregiver Access Model and Privacy Architecture

> Companion is an AI-powered independence assistant for adults with developmental disabilities.
> The user is called "Sam." The AI assistant is called "Arlo."
> This document is the authoritative specification for caregiver access, privacy enforcement,
> memory model boundaries, encryption strategy, data retention, consent architecture, and
> legal compliance.

---

## 1. Core Principle

Sam is the user. The caregiver is a guest.

All access, visibility, and permissions flow from Sam. Payment does not grant access. A family member who pays the subscription has exactly the same default access as any other trusted contact: **none**, until Sam grants it.

This is **architecturally enforced**, not policy-enforced. There is no configuration flag, admin override, or backend toggle that grants a caregiver access Sam has not explicitly approved. The Caregiver API is a separate surface with its own endpoint set, its own JWT claims, and its own data-layer summarization boundary. It cannot reach user-facing endpoints.

---

## 1a. Care Model

Members (end users) operate under one of two care models, stored as `care_model` on the `users` table:

| Mode | Description | Who controls caregiver list |
|---|---|---|
| `self_directed` (default) | Member controls their own caregiver assignments. Caregiver or admin-initiated assignments require member approval. | Member |
| `managed` | Organization (group home, day program) controls the account. Admin assigns caregivers directly. | Admin/Organization |

**Important:** The care model controls only the **assignment approval flow**. It does NOT override the hard restrictions in Section 4 — even managed members retain all privacy protections. Payment does not grant access, regardless of care model.

## 1b. Invitation and Assignment Flow

Getting a caregiver connected to a member is a two-part process:

### Part 1: Platform Invitation

Two paths to get someone onto the platform:

1. **Admin invites** — Admin uses `/admin/people/{email}/invite`. A stub `User` record is created with `account_status='invited'`. Invitation email sent via Gmail SMTP.
2. **Member invites** — Member uses `/api/v1/invitations`. A `TrustedContact` is created immediately (with `invitation_status='pending'`), and a stub user is created if needed. The email includes a token-based acceptance link.

Either way, if the invitee already has an active account, no stub is created — just a notification.

### Part 2: Caregiver-to-Member Assignment

- **Member-initiated invite** — Assignment happens in Part 1 (TrustedContact created immediately, pending acceptance).
- **Admin-initiated, managed member** — TrustedContact created directly, no approval needed.
- **Admin-initiated, self-directed member** — A `CaregiverAssignmentRequest` is created with `status='pending_approval'`. The member is notified and must approve or reject.
- **Caregiver-initiated** — Caregiver requests assignment via `/api/v1/caregiver/assignments/request`. For managed members, auto-approved. For self-directed, pending member approval.

### Invitation Acceptance

Invitation emails include a link: `https://app.mydailydignity.com/invite/accept?token={token}`. The token is a 48-character URL-safe random string with a 14-day TTL. On acceptance:
1. The caregiver signs in with Google (Firebase Auth).
2. The `invitation_status` on `TrustedContact` is set to `accepted`, `is_active` is set to `true`.
3. If the user was a stub (`account_status='invited'`), they're upgraded to `active`.
4. The member is notified.

---

## 2. Caregiver Types

| Type | Legitimate Need | Typical Default Access |
|---|---|---|
| Family member | Confidence Sam is safe | Tier 1 (may request Tier 2) |
| Case worker | Periodic stability confirmation | Tier 1 or Tier 2 |
| Support coordinator | Status at a glance across clients | Tier 2 |
| Group home staff | Shift-based handoff info | Tier 2 |
| Paid support person | Task-level scoped help | Tier 3 |

**All types start at Tier 1 by default.** Elevation to Tier 2 or Tier 3 requires Sam's explicit grant.

---

## 3. Three-Tier Access Model

### Tier 1 — Safety Alerts Only (DEFAULT)

The default tier when any trusted contact is added. The caregiver receives notifications **only when something is wrong**.

#### Alert Triggers

| Trigger | Condition | Cooldown |
|---|---|---|
| Missed medication | 2+ consecutive days missed | 48h between re-alerts |
| Urgent document | Legal, eviction, overdue, or collections notice flagged | Once per document |
| Inactivity | No app interaction for an unusual number of days (baseline learned per-user) | 72h between re-alerts |
| Form deadline | Deadline approaching, form not started | Once at 7 days, once at 3 days |
| Travel overdue | Active trip significantly longer than expected duration | Once per trip |

#### Alert Format

Minimum context only. Category + urgency level. **Never** document contents. **Never** activity logs. **Never** specific financial figures.

Example alert payloads:

```json
{
  "alert_type": "urgent_document",
  "urgency": "high",
  "message": "Sam received a legal notice 24 hours ago and hasn't acknowledged it. You may want to check in.",
  "timestamp": "2026-03-27T14:30:00Z",
  "action_hint": "check_in"
}
```

```json
{
  "alert_type": "missed_medication",
  "urgency": "medium",
  "message": "Sam has missed scheduled medication for 2 consecutive days.",
  "timestamp": "2026-03-27T09:00:00Z",
  "action_hint": "check_in"
}
```

Note: `action_hint` is for caregiver UI rendering only. No write-back action is available.

#### Tier 1 JWT Claims

```json
{
  "sub": "<contact_id>",
  "role": "caregiver",
  "tier": 1,
  "user_id": "<sam_user_id>",
  "scopes": ["alerts:read"]
}
```

The API gateway rejects any request from a Tier 1 token to endpoints outside `/caregiver/alerts/**`.

---

### Tier 2 — Read-Only Dashboard

The caregiver can view a **summary** dashboard. All data is summarized, not raw.

#### What Tier 2 Sees

| Data Point | Format | Example |
|---|---|---|
| Task completion | Summary count | "3 of 4 tasks completed today" |
| Upcoming bills | Handled/not-handled flag | "Electric bill — handled" (no amount) |
| Medication adherence | Percentage over rolling 7 days | "86% adherence this week" |
| Upcoming appointments | Date/time only | "Appointment Thursday 2:00 PM" (no provider name unless Sam shares) |
| Active urgent items | Category + age | "1 urgent document, received 2 days ago" |

#### What Tier 2 NEVER Sees

- Minute-by-minute activity logs
- Raw checklists or individual task descriptions
- Document contents (scanned mail, forms, letters)
- Financial details (amounts, balances, account numbers)
- Memory of any type (functional, contextual, or emotional)
- Provider names, medication names, or diagnosis information (unless Sam explicitly shares)

#### Implementation: Data-Layer Summarization

Summarization happens at the **data layer**, not the presentation layer. The Caregiver API returns pre-summarized response objects. A Tier 2 JWT **cannot** fetch raw data regardless of how the request is constructed.

```
┌──────────────────────┐
│   Caregiver Client    │
│   (Tier 2 JWT)        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  API Gateway          │
│  - Validates JWT tier │
│  - Routes to          │
│    Caregiver API only │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Caregiver API        │
│  /caregiver/dashboard │
│  /caregiver/alerts    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Summarization Layer  │  ← Queries raw data, returns only summaries
│  (Data Access Layer)  │     No raw data leaves this boundary
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  PostgreSQL / Redis   │
│  (Raw user data)      │
└──────────────────────┘
```

The Summarization Layer is the **only** code path between caregiver-facing endpoints and the data store. It is a separate module with its own integration tests asserting that no raw data (document text, financial amounts, memory entries) appears in its output.

#### Tier 2 JWT Claims

```json
{
  "sub": "<contact_id>",
  "role": "caregiver",
  "tier": 2,
  "user_id": "<sam_user_id>",
  "scopes": ["alerts:read", "dashboard:read"]
}
```

The API gateway rejects any request from a Tier 2 token to endpoints outside `/caregiver/alerts/**` and `/caregiver/dashboard/**`.

---

### Tier 3 — Scoped Collaboration

Sam explicitly invites a trusted contact to help with a **specific** task. Each permission grant is:

- **Narrow** — scoped to one specific resource
- **Time-limited** — auto-expires when the session ends or after a configured duration (default: 1 hour, max: 24 hours)
- **Revocable** — Sam can end it at any time, effective immediately

#### Examples

| Sam Says | Resource Type | Permissions Granted | Default Expiry |
|---|---|---|---|
| "Help me fill out this form" | `form` | `read`, `comment` | Session end |
| "Review this before I submit" | `document` | `read` | 30 minutes |
| "Add items to my shopping list" | `list` | `read`, `write` | 1 hour |
| "Check my appointments this week" | `calendar` | `read` | 30 minutes |

#### Implementation: `collaboration_scope` Record

Each Tier 3 grant creates a `collaboration_scope` record:

```sql
CREATE TABLE collaboration_scopes (
  scope_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id      UUID NOT NULL REFERENCES trusted_contacts(id),
  user_id         UUID NOT NULL REFERENCES users(id),
  resource_type   TEXT NOT NULL CHECK (resource_type IN ('form', 'document', 'list', 'calendar')),
  resource_id     UUID NOT NULL,
  permissions     TEXT[] NOT NULL CHECK (permissions <@ ARRAY['read', 'write', 'comment']),
  granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at      TIMESTAMPTZ NOT NULL,
  revoked_at      TIMESTAMPTZ,
  revocation_reason TEXT,  -- 'user_revoked', 'expired', 'session_ended'
  CONSTRAINT valid_expiry CHECK (expires_at > granted_at),
  CONSTRAINT max_duration CHECK (expires_at <= granted_at + INTERVAL '24 hours')
);

CREATE INDEX idx_collab_scope_contact ON collaboration_scopes(contact_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_collab_scope_expiry ON collaboration_scopes(expires_at) WHERE revoked_at IS NULL;
```

Example record:

```json
{
  "scope_id": "a1b2c3d4-...",
  "contact_id": "e5f6g7h8-...",
  "resource_type": "form",
  "resource_id": "i9j0k1l2-...",
  "permissions": ["read", "comment"],
  "granted_at": "2026-03-27T14:00:00Z",
  "expires_at": "2026-03-27T15:00:00Z",
  "revoked_at": null,
  "revocation_reason": null
}
```

#### Tier 3 Middleware Enforcement

Every request to a Tier 3 resource endpoint must pass through the scope validation middleware:

```
1. Extract contact_id and resource_id from request
2. Query collaboration_scopes WHERE:
   - contact_id = request.contact_id
   - resource_id = request.resource_id
   - revoked_at IS NULL
   - expires_at > now()
3. If no matching scope: return 403
4. If matching scope exists: verify requested action is in scope.permissions
5. If action not in permissions: return 403
6. Allow request, log to caregiver_activity_log
```

#### Tier 3 JWT Claims

```json
{
  "sub": "<contact_id>",
  "role": "caregiver",
  "tier": 3,
  "user_id": "<sam_user_id>",
  "scopes": ["alerts:read", "dashboard:read", "collaboration:active"],
  "active_scope_ids": ["<scope_id_1>"]
}
```

Note: Tier 3 is additive. A caregiver granted Tier 3 also retains Tier 2 and Tier 1 capabilities. The `active_scope_ids` claim is a convenience for client rendering; the server always re-validates against the database.

#### Expiry Enforcement

A background job runs every 5 minutes to set `revoked_at = now()` and `revocation_reason = 'expired'` on any `collaboration_scope` where `expires_at < now()` and `revoked_at IS NULL`. This is belt-and-suspenders with the per-request check in the middleware.

---

## 4. Hard Restrictions (Non-Configurable)

These restrictions apply to **all caregivers**, **all tiers**, **all circumstances**. They are enforced architecturally. There is no override, no admin flag, no emergency bypass that changes these.

| Never Allowed | Enforcement Mechanism |
|---|---|
| Override, dismiss, or modify Sam's tasks or decisions | No write endpoints for user data exist in the Caregiver API |
| View bank balance without per-session Tier 3 grant | Balance is excluded from the Tier 2 summarization layer; Tier 3 requires explicit `financial_balance` resource grant |
| Read scanned mail or document contents | Documents are not in the Caregiver API scope; the summarization layer strips all raw text |
| Receive notifications Sam hasn't approved | Alert trigger configuration is stored on Sam's user record; caregiver cannot modify it |
| Change Sam's settings, preferences, or access tiers | No settings write endpoints exist in the Caregiver API |
| Access data because they pay for the subscription | Payment relationship is a separate data model (`subscriptions` table) with no foreign key to `trusted_contacts` or `caregiver_access` |
| View any memory (functional, contextual, or emotional) | The memory store has **no caregiver read path in code**. No endpoint, no query, no summarization path. Architectural. |

### Enforcement Verification

For each hard restriction, the codebase must include:

1. An integration test that attempts the forbidden action via the Caregiver API and asserts a 403 or 404 response.
2. A comment in the relevant middleware referencing this document section (e.g., `// Ref: 06-caregiver-access-and-privacy.md §4 — Hard Restrictions`).

---

## 5. Transparency — Sam Always Knows

### Caregiver Activity Logging

Every caregiver interaction with Sam's data is logged. This log is append-only and immutable.

```sql
CREATE TABLE caregiver_activity_log (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trusted_contact_id  UUID NOT NULL REFERENCES trusted_contacts(id),
  user_id             UUID NOT NULL REFERENCES users(id),
  action              TEXT NOT NULL,  -- 'viewed_dashboard', 'received_alert', 'tier3_session_start',
                                      -- 'tier3_session_end', 'tier3_resource_read', 'tier3_resource_comment'
  details             JSONB,          -- structured metadata, never raw user data
  ip_address          INET,
  user_agent          TEXT,
  occurred_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_caregiver_activity_user ON caregiver_activity_log(user_id, occurred_at DESC);
CREATE INDEX idx_caregiver_activity_contact ON caregiver_activity_log(trusted_contact_id, occurred_at DESC);
```

The `details` JSONB column stores structured metadata about the action (e.g., which dashboard section was viewed, which alert was received). It **never** contains raw user data, document contents, or financial figures.

### Sam's Visibility

- Sam is notified **every time** a caregiver views the Tier 2 dashboard. Notification is batched if multiple views occur within a 1-hour window.
- Sam can view the full activity log: what action, when, by whom.
- **Monthly prompt** (via Arlo): "You have 2 trusted contacts who can see your status. Want to review their access?"
  - Prompt is conversational, not a modal or settings screen.
  - Sam can review, modify, or revoke access directly in the conversation.

### Sam's Controls

| Control | Mechanism | Effect |
|---|---|---|
| Revoke access | One tap / one Arlo command | Caregiver's JWT is invalidated. All active `collaboration_scope` records are revoked. Immediate. |
| Pause access | Temporary suspension without removal | Caregiver remains in `trusted_contacts` but a `paused_at` timestamp is set. API gateway rejects all requests from paused contacts. |
| Resume access | One tap / one Arlo command | `paused_at` is cleared. Access resumes at previously granted tier. |
| Tier 3 auto-expire | Automatic | All `collaboration_scope` records expire per their `expires_at`. No persistent elevated access. |

---

## 6. Memory Model — Privacy Enforcement

### Three Memory Types

| Type | Storage | Retention | Caregiver Visibility |
|---|---|---|---|
| Functional | PostgreSQL | Permanent (until Sam deletes) | **NEVER** — no read path exists |
| Contextual | Redis (TTL) | 48 hours, then hard deleted | **NEVER** — no read path exists |
| Emotional | Not stored | Never written to any system | N/A — nothing to access |

### Functional Memory

Long-term facts about Sam: medications, providers, address, preferences, upcoming events, routines.

- Sam can view and edit any item at any time ("What do you know about me?")
- Read/write for Sam's own API endpoints
- Read-only for the conversation pipeline and Arlo's reasoning layer
- **Caregiver read path does not exist in code.** There is no endpoint, no query method, no summarization path that exposes functional memory to any caregiver tier.

Storage:

```sql
CREATE TABLE functional_memory (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id),
  category    TEXT NOT NULL,  -- 'medication', 'provider', 'preference', 'routine', 'event', 'address'
  key         TEXT NOT NULL,
  value       JSONB NOT NULL, -- encrypted at rest (AES-256, see §7)
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at  TIMESTAMPTZ,
  UNIQUE (user_id, category, key)
);
```

### Contextual Memory

Short-term context that helps Arlo follow up: "I'm nervous about tomorrow," "I argued with my roommate."

- Stored in Redis with a **48-hour TTL** set at write time.
- A background job runs hourly to purge any expired entries that Redis TTL missed (belt and suspenders).
- **Not archived.** Not summarized. Not written to PostgreSQL. Hard deleted after TTL.
- Used for at most one follow-up conversation, then released.
- No caregiver read path exists. Redis keys for contextual memory are namespaced (`ctx:{user_id}:*`) and the Caregiver API has no access to this namespace.

### Emotional Memory

Deeper personal disclosures: relationships, feelings, fears, hopes.

- Arlo responds warmly and empathetically **in real time** during the conversation.
- **Nothing is written** to any database, any log, any cache, any queue, any analytics pipeline.
- The conversation turn is processed in memory and discarded.
- There is nothing to breach because nothing exists.

Implementation note: The conversation pipeline must explicitly filter emotional content from any persistence path. This is enforced by a classification step that tags emotional disclosures and routes them to a no-persist handler.

### "What Do You Know About Me?"

A first-class feature, always accessible. Sam says "What do you know about me?" and Arlo responds with:

1. A plain-language list of all functional memory, organized by category.
2. An indication of whether any contextual memory exists (not its content — Sam can ask to see it).
3. An explicit statement that no emotional memory is stored.

Sam can:
- Delete any individual item with one tap or one Arlo command.
- Clear entire categories ("Forget all my provider information").
- Arlo confirms: "Done. I've forgotten that."
- **Monthly opt-in prompt** (via Arlo): "Want to review what I know about you? You can always ask me anytime."

---

## 7. Encryption Strategy

### At Rest

| Data Category | Encryption | Key Source |
|---|---|---|
| Document raw text | AES-256-GCM | Google Cloud KMS (per-tenant key) |
| Extracted document fields | AES-256-GCM | Google Cloud KMS (per-tenant key) |
| User profile data | AES-256-GCM | Google Cloud KMS (per-tenant key) |
| Functional memory values | AES-256-GCM | Google Cloud KMS (per-tenant key) |
| SSI/SSN numbers | AES-256-GCM | Google Cloud KMS (**separate field-level key**) |
| Bank account numbers | AES-256-GCM | Google Cloud KMS (**separate field-level key**) |
| Medical record numbers | AES-256-GCM | Google Cloud KMS (**separate field-level key**) |

Encryption keys are **never** stored alongside data. They are fetched from KMS at request time and held in memory only for the duration of the operation.

### In Transit

- **TLS 1.3 minimum** for all connections (API, database, inter-service).
- **Certificate pinning** on mobile app to prevent MITM attacks.
- Internal service-to-service communication uses mTLS.

### Key Management

| Key Type | Rotation Schedule | Scope |
|---|---|---|
| Standard encryption key | 90 days | Per-tenant |
| Field-level encryption key | 30 days | Per-field-type (SSN, account, medical) |
| JWT signing key | 90 days | Global |

#### Break-Glass Procedure

Emergency access to encrypted data (e.g., for a critical production incident) requires:

1. Manager approval (logged in access management system).
2. Time-limited access token (max 4 hours).
3. Full audit trail of every record accessed.
4. Post-incident review within 48 hours.

---

## 8. Data Retention Policy

### Configurable Phases

| Phase | Default Duration | Configurable Range | What Is Kept |
|---|---|---|---|
| Full retention | 0-30 days | 7-90 days | Everything: raw text, extracted fields, summary, source image |
| Important only | 31-90 days | 30 days - 1 year | Non-junk items: raw text, extracted fields, summary |
| Metadata only | 91+ days | 90 days - forever | Extracted fields + summary card only. **Raw text is hard deleted.** |
| Junk | Deleted at 30 days | Not configurable | Nothing retained. Hard deleted. |
| Legal/Government | Never below metadata | Not configurable | Always retained at minimum metadata phase. Never fully deleted. |

### Enforcement

A background job runs **daily** and performs the following for every document in the system:

1. Evaluate the document's age and classification against the user's retention policy.
2. Transition the document to the appropriate phase.
3. When moving to metadata-only: **hard delete** raw text and source images. This is an irreversible `DELETE` + `VACUUM`, not a soft delete.
4. Write a deletion audit trail entry for every deletion. The audit entry contains document ID, deletion timestamp, and retention phase — **never** document content.

```sql
CREATE TABLE retention_audit_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  document_id     UUID NOT NULL,
  previous_phase  TEXT NOT NULL,
  new_phase       TEXT NOT NULL,
  fields_deleted  TEXT[],  -- e.g., ['raw_text', 'source_image']
  executed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### User Configuration

Retention settings are configured **via Arlo conversation**, not a settings screen:

> "How long do you want me to keep your mail? Most people keep important mail for about 3 months."

Three named options are presented:
1. **"Keep it short"** — Full: 7 days, Important: 30 days, Metadata: 90 days
2. **"Standard"** — Full: 30 days, Important: 90 days, Metadata: forever (default)
3. **"Keep everything longer"** — Full: 90 days, Important: 1 year, Metadata: forever

Advanced day-range configuration is available for power users or caregivers assisting with setup.

---

## 9. Consent Architecture

### Plain-Language Consent

Every permission Companion requests is:

- **Granular** — each permission is separate and independently revocable.
- **Plain language** — one sentence, spoken by Arlo in conversation. No legalese.
- **Revisable** — revocable at any time via Arlo conversation ("Stop reading my email").
- **Supported** — a trusted contact may assist Sam during onboarding, but **consent is still Sam's**. The trusted contact cannot consent on Sam's behalf.

#### Consent Prompts (Examples)

| Permission | Arlo's Prompt |
|---|---|
| Camera/mail scanning | "I'd like to read your mail so I can explain it to you. Is that okay?" |
| Email access | "I'd like to connect to your email for the same reason. Is that okay?" |
| Memory | "I'd like to remember things about you so I can help better. You can see and delete anything I remember. Is that okay?" |
| Location | "I'd like to know your location so I can help with travel. Is that okay?" |
| Financial (Plaid) | "I'd like to connect to your bank so I can help you track bills. Is that okay?" |

Each consent prompt includes:
1. What the permission does (one sentence).
2. Why it helps Sam (one sentence).
3. That it can be revoked anytime.

### Consent Storage

```sql
CREATE TABLE user_consents (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id),
  consent_type  TEXT NOT NULL,  -- 'camera_scan', 'email_read', 'memory', 'location', 'plaid'
  granted       BOOLEAN NOT NULL,
  granted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at    TIMESTAMPTZ,
  granted_via   TEXT NOT NULL,  -- 'onboarding', 'conversation', 'settings'
  UNIQUE (user_id, consent_type) -- only one active consent record per type
);

CREATE INDEX idx_user_consents_user ON user_consents(user_id);
```

When Sam revokes a consent:
1. `revoked_at` is set to `now()`.
2. The corresponding feature is **immediately disabled**. No grace period.
3. If the consent was for data collection (e.g., email), no new data is collected. Existing data follows the retention policy.

---

## 10. Legal and Compliance

### HIPAA-Adjacent

Companion is **not a covered entity** under HIPAA. However, it operates to HIPAA-equivalent standards for all health-related data (medication schedules, provider information, medical documents).

If EHR or prescription database integration is added (V2+), formal HIPAA compliance and a Business Associate Agreement (BAA) are required before launch.

Current HIPAA-equivalent measures:
- Encryption at rest and in transit (see section 7)
- Access logging for all data access (see section 5)
- Minimum necessary principle (summarization layer, see section 3)
- Employee access controls and training

### CCPA Compliance

| CCPA Right | Implementation |
|---|---|
| Right to know | "What do you know about me?" feature (see section 6) |
| Right to delete | Hard deletes via Arlo conversation + full account deletion with 30-day purge |
| Right to opt out of sale | Companion does not sell data. Ever. This is technically enforced: no data export pipeline to third parties exists in the codebase. |
| Right to non-discrimination | Service functionality is identical regardless of privacy choices |

### SSI/Medicaid Data

Data related to Supplemental Security Income (SSI) and Medicaid is treated as the **most sensitive category**:

- Field-level encryption with dedicated keys (see section 7)
- Strictest retention policy (never below metadata phase)
- No third-party sharing under any circumstances
- Audit logging for every access

### Law Enforcement

1. Sam is notified of any legal demand for their data **unless legally prohibited** from doing so (e.g., a gag order).
2. Minimum data is provided per the specific terms of the order. No bulk disclosure.
3. Overbroad demands are challenged by legal counsel before compliance.
4. An annual transparency report is published disclosing the number and type of demands received.

---

## 11. The "Who Pays" Problem

The payment relationship is a **separate data model** from the access relationship. These two concerns share no foreign keys and no business logic coupling.

```
┌────────────────────────┐     ┌────────────────────────┐
│  subscriptions          │     │  trusted_contacts       │
│  ───────────────────    │     │  ───────────────────    │
│  id                     │     │  id                     │
│  user_id (Sam)          │     │  user_id (Sam)          │
│  payer_id               │     │  contact_user_id        │
│  plan                   │     │  tier                   │
│  status                 │     │  granted_at             │
│  ...                    │     │  paused_at              │
│                         │     │  revoked_at             │
│  NO FK to               │     │  NO FK to               │
│  trusted_contacts       │     │  subscriptions          │
└────────────────────────┘     └────────────────────────┘
```

### Rules

1. **Sam owns the account** regardless of who pays.
2. A paying family member has the same caregiver access as any other trusted contact — only what Sam grants.
3. If Sam revokes a caregiver's access, it is revoked immediately and completely, regardless of whether that caregiver pays for the subscription.
4. Payment status changes (cancellation, lapse) affect the **subscription**, not caregiver access grants. These are independent state machines.
5. Agency accounts (V2) will have bounded, role-specific access that is scoped by the agency's contract. Even agency access **never overrides** Sam's per-contact access controls.

### Implementation Note

The subscription service and the caregiver access service must be separate modules with no shared state. A payment webhook must never trigger an access change. An access revocation must never trigger a payment change. If business logic ever needs to reference both (e.g., "show Sam who is paying"), it does so via read-only queries to both services, never via a join or shared transaction.

---

## Appendix A: Caregiver API Endpoint Summary

| Method | Endpoint | Required Tier | Description |
|---|---|---|---|
| `GET` | `/caregiver/alerts` | 1+ | List active alerts for the linked user |
| `GET` | `/caregiver/alerts/:id` | 1+ | Get single alert detail |
| `GET` | `/caregiver/dashboard` | 2+ | Get summarized dashboard |
| `GET` | `/caregiver/dashboard/tasks` | 2+ | Task completion summary |
| `GET` | `/caregiver/dashboard/bills` | 2+ | Bill status summary (no amounts) |
| `GET` | `/caregiver/dashboard/medication` | 2+ | Medication adherence percentage |
| `GET` | `/caregiver/dashboard/appointments` | 2+ | Upcoming appointments (date/time only) |
| `GET` | `/caregiver/dashboard/urgent` | 2+ | Active urgent items |
| `GET` | `/caregiver/collaboration/:scope_id/:resource_id` | 3 (scoped) | Access a specific shared resource |
| `POST` | `/caregiver/collaboration/:scope_id/:resource_id/comment` | 3 (scoped, `comment` permission) | Add comment to shared resource |

No `PUT`, `PATCH`, or `DELETE` endpoints exist in the Caregiver API for any user data.

---

## Appendix B: Tier Enforcement Middleware (Pseudocode)

```python
def caregiver_tier_middleware(request, required_tier):
    token = decode_jwt(request.headers["Authorization"])

    # 1. Validate this is a caregiver token
    if token.role != "caregiver":
        return 403

    # 2. Validate the caregiver is still an active trusted contact
    contact = db.query(
        "SELECT * FROM trusted_contacts WHERE id = %s AND user_id = %s AND revoked_at IS NULL AND paused_at IS NULL",
        token.sub, token.user_id
    )
    if not contact:
        return 403

    # 3. Validate tier
    if contact.tier < required_tier:
        return 403

    # 4. For Tier 3 scoped requests, validate collaboration scope
    if required_tier == 3:
        scope_id = request.params.get("scope_id")
        resource_id = request.params.get("resource_id")
        scope = db.query(
            """SELECT * FROM collaboration_scopes
               WHERE scope_id = %s AND contact_id = %s AND resource_id = %s
               AND revoked_at IS NULL AND expires_at > now()""",
            scope_id, token.sub, resource_id
        )
        if not scope:
            return 403
        if request.action not in scope.permissions:
            return 403

    # 5. Log the access
    db.insert("caregiver_activity_log", {
        "trusted_contact_id": token.sub,
        "user_id": token.user_id,
        "action": determine_action(request),
        "details": sanitized_request_metadata(request),
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent"),
    })

    # 6. Allow the request
    return proceed(request)
```

---

## Appendix C: Security Audit Checklist

A security auditor verifying this architecture should confirm:

- [ ] No Caregiver API endpoint returns raw document text, financial amounts, or memory entries.
- [ ] Tier 1 JWT tokens cannot access `/caregiver/dashboard/**` endpoints.
- [ ] Tier 2 JWT tokens cannot access `/caregiver/collaboration/**` endpoints.
- [ ] The summarization layer has integration tests asserting no raw data leakage.
- [ ] `collaboration_scopes` records cannot exceed 24-hour duration.
- [ ] Expired `collaboration_scopes` are revoked by background job within 10 minutes.
- [ ] The memory store (`functional_memory` table, `ctx:*` Redis keys) has no read path accessible from any Caregiver API endpoint.
- [ ] Emotional content is classified and routed to the no-persist handler; no database write occurs.
- [ ] Contextual memory Redis keys have TTL set at write time; background purge job runs hourly.
- [ ] `caregiver_activity_log` is append-only (no `UPDATE` or `DELETE` grants on the table).
- [ ] `subscriptions` and `trusted_contacts` tables share no foreign keys.
- [ ] Payment webhooks do not trigger access changes.
- [ ] Field-level encryption keys for SSN, account numbers, and medical record numbers are separate from standard encryption keys.
- [ ] All Caregiver API responses include `Cache-Control: no-store` header.
- [ ] Sam is notified of every Tier 2 dashboard view within the batching window.
