# 02 — Data Model Specification

**Status:** Draft | **Last updated:** 2026-03-27

---

## 1. Database Architecture

Companion uses three storage layers, each chosen for a specific access pattern.

| Layer | Technology | Purpose |
|---|---|---|
| **Primary** | PostgreSQL 16+ | Relational data, JSONB for semi-structured fields (extracted document fields, schedules, addresses). Source of truth for all domain entities. |
| **Cache / TTL** | Redis 7+ | Contextual memory windows, conversation session state, rate limiting, short-lived section caches, distributed locks for pipeline idempotency. |
| **Object Storage** | Google Cloud Storage (GCS) | Encrypted document images and raw OCR/extracted text. Referenced by GCS path from PostgreSQL; never queried directly. All objects encrypted at rest with customer-managed encryption keys (CMEK). |

**Why this split:**

- PostgreSQL handles everything that needs ACID guarantees, foreign keys, and complex queries (user data, documents, billing, medications). JSONB columns avoid premature schema rigidity for fields like `extracted_fields` and `address` that vary by document type or user.
- Redis handles anything ephemeral or latency-sensitive. Contextual memory has a natural TTL (48 hours); session state expires after inactivity; rate-limit counters use sliding windows. None of this belongs in PostgreSQL.
- GCS holds large blobs (scanned images, multi-page PDFs, raw text dumps). Storing these in PostgreSQL would bloat WAL and backups. GCS gives us lifecycle policies, versioning, and CDN-compatible access if we ever need it.

---

## 2. Core Schemas (PostgreSQL)

All tables use `gen_random_uuid()` for primary keys. Timestamps are `TIMESTAMPTZ` (stored as UTC). Enums are defined as PostgreSQL types for compile-time safety.

### 2.1 Enum Types

```sql
-- Relationship types for trusted contacts
CREATE TYPE relationship_type AS ENUM (
    'family',
    'case_worker',
    'support_coordinator',
    'group_home_staff',
    'paid_support'
);

-- Tiered access control for caregivers
CREATE TYPE access_tier AS ENUM (
    'tier_1',   -- Alerts only (medication missed, question escalated)
    'tier_2',   -- Read-only dashboard (upcoming bills, appointments, open questions)
    'tier_3'    -- Scoped interactive sessions (e.g., help with a specific form)
);

-- How a document entered the system
CREATE TYPE source_channel AS ENUM (
    'camera_scan',
    'email',
    'mail_station'
);

-- Document classification after ML pipeline
CREATE TYPE document_classification AS ENUM (
    'bill',
    'legal',
    'government',
    'medical',
    'insurance',
    'form',
    'junk',
    'personal',
    'unknown'
);

-- Urgency as determined by classification + rule engine
CREATE TYPE urgency_level AS ENUM (
    'routine',
    'needs_attention',
    'act_today',
    'urgent'
);

-- Where a document lands in the user's home screen
CREATE TYPE routing_destination AS ENUM (
    'home',
    'my_health',
    'bills',
    'plans'
);

-- Document lifecycle
CREATE TYPE document_status AS ENUM (
    'received',
    'processing',
    'classified',
    'summarized',
    'routed',
    'acknowledged',
    'handled'
);

-- Retention lifecycle
CREATE TYPE retention_phase AS ENUM (
    'full',
    'important_only',
    'metadata_only'
);

-- Functional memory categories
CREATE TYPE memory_category AS ENUM (
    'medication',
    'provider',
    'appointment',
    'bill',
    'preference',
    'contact_info',
    'other'
);

-- How a memory entry was created
CREATE TYPE memory_source AS ENUM (
    'user_input',
    'document_extraction',
    'onboarding',
    'system'
);

-- Bill payment tracking
CREATE TYPE payment_status AS ENUM (
    'pending',
    'acknowledged',
    'paid',
    'overdue'
);

-- To-do categories
CREATE TYPE todo_category AS ENUM (
    'errand',
    'shopping',
    'task',
    'general'
);

-- Where a to-do came from
CREATE TYPE todo_source AS ENUM (
    'user',
    'arlo_suggestion',
    'document'
);

-- Context for open questions
CREATE TYPE question_context_type AS ENUM (
    'medication',
    'bill',
    'document',
    'form',
    'travel',
    'checkin'
);

-- Question lifecycle
CREATE TYPE question_status AS ENUM (
    'open',
    'answered',
    'escalated',
    'expired'
);

-- Caregiver actions for audit
CREATE TYPE caregiver_action AS ENUM (
    'viewed_dashboard',
    'received_alert',
    'tier3_session'
);

-- Deletion reasons for audit trail
CREATE TYPE deletion_reason AS ENUM (
    'user_request',
    'admin_request',
    'ttl_expiry',
    'retention_policy'
);

-- Care model for member accounts
CREATE TYPE care_model AS ENUM (
    'self_directed',  -- Member controls caregiver list (default)
    'managed'         -- Organization controls caregiver assignments
);

-- Account status
CREATE TYPE account_status AS ENUM (
    'active',
    'invited'         -- Stub account created via invitation, not yet signed in
);

-- Invitation status for trusted contacts
CREATE TYPE invitation_status AS ENUM (
    'pending',
    'accepted',
    'declined',
    'expired'
);

-- Assignment request status
CREATE TYPE assignment_request_status AS ENUM (
    'pending_approval',
    'approved',
    'rejected',
    'expired'
);
```

### 2.2 users

```sql
CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email             TEXT UNIQUE NOT NULL,
    phone             TEXT UNIQUE,
    preferred_name    TEXT NOT NULL,
    display_name      TEXT NOT NULL,
    date_of_birth     DATE,
    address           JSONB,
        -- { street, unit, city, state, zip, coordinates: {lat, lng} }
    primary_language  TEXT NOT NULL DEFAULT 'en',

    -- D.D. personality preferences
    voice_id          TEXT NOT NULL DEFAULT 'arlo_default',
    pace_setting      TEXT NOT NULL DEFAULT 'normal'
                      CHECK (pace_setting IN ('slow', 'normal', 'fast')),
    warmth_level      TEXT NOT NULL DEFAULT 'warm'
                      CHECK (warmth_level IN ('direct', 'warm', 'extra_warm')),
    nickname          TEXT,

    -- Quiet hours (no proactive notifications)
    quiet_start       TIME,
    quiet_end         TIME,
    checkin_time      TIME DEFAULT '09:00',

    -- Away mode (pauses reminders, extends deadlines)
    away_mode         BOOLEAN NOT NULL DEFAULT FALSE,
    away_expires_at   TIMESTAMPTZ,

    -- Care model & account lifecycle
    care_model        TEXT NOT NULL DEFAULT 'self_directed',
    account_status    TEXT NOT NULL DEFAULT 'active',
                      -- Values: active, invited, deactivated, pending_deletion
    deactivated_at    TIMESTAMPTZ,
    deletion_scheduled_at TIMESTAMPTZ,

    -- V2 extension point: agency/organization ownership
    -- agency_id     UUID REFERENCES agencies(id),
    -- onboarded_by  UUID REFERENCES agency_staff(id),

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 2.3 trusted_contacts

```sql
CREATE TABLE trusted_contacts (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contact_name      TEXT NOT NULL,
    contact_phone     TEXT,
    contact_email     TEXT,
    relationship_type relationship_type NOT NULL,
    access_tier       access_tier NOT NULL DEFAULT 'tier_1',
    tier_3_scope      JSONB,
        -- Nullable. Only set when access_tier = 'tier_3'.
        -- Example: { "allowed_sections": ["bills"], "expires_at": "2026-04-01T00:00:00Z" }
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,

    -- Invitation tracking
    invitation_status TEXT NOT NULL DEFAULT 'accepted',
    invitation_token  TEXT UNIQUE,
    invited_at        TIMESTAMPTZ,
    invited_by_admin_id UUID REFERENCES admin_users(id),
    invited_by_user_id  UUID REFERENCES users(id) ON DELETE SET NULL,
    accepted_at       TIMESTAMPTZ,

    -- V2 extension point: link to agency staff
    -- agency_staff_id UUID REFERENCES agency_staff(id),

    added_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_viewed_at    TIMESTAMPTZ,

    CONSTRAINT chk_tier3_scope CHECK (
        access_tier != 'tier_3' OR tier_3_scope IS NOT NULL
    )
);
```

### 2.3a caregiver_assignment_requests

Tracks pending caregiver-to-member assignment requests for self-directed members.

```sql
CREATE TABLE caregiver_assignment_requests (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    caregiver_email     TEXT NOT NULL,
    caregiver_name      TEXT NOT NULL,
    relationship_type   TEXT NOT NULL,
    access_tier         TEXT NOT NULL DEFAULT 'tier_1',
    status              TEXT NOT NULL DEFAULT 'pending_approval',
    initiated_by        TEXT NOT NULL,     -- 'caregiver', 'member', or 'admin'
    initiated_by_admin_id UUID REFERENCES admin_users(id),
    requested_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at         TIMESTAMPTZ,
    resolved_by         TEXT,              -- 'member', 'admin', or 'system'
    expires_at          TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_assignment_requests_member_status
    ON caregiver_assignment_requests (member_id, status);
```

### 2.4 documents

```sql
CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_channel      source_channel NOT NULL,
    raw_text_ref        TEXT NOT NULL,
        -- GCS path: gs://companion-docs-{env}/{user_id}/{doc_id}/raw.txt.enc
    classification      document_classification,
    confidence_score    DECIMAL(4,3) CHECK (confidence_score BETWEEN 0 AND 1),
    urgency_level       urgency_level,
    extracted_fields    JSONB,
        -- Schema varies by classification. Examples:
        -- bill:    { "sender", "amount", "due_date", "account_number_masked" }
        -- medical: { "provider", "date_of_service", "diagnosis_codes" }
        -- legal:   { "case_number", "court", "hearing_date", "parties" }
    spoken_summary      TEXT,
        -- Plain-language summary D.D. reads aloud
    card_summary        TEXT,
        -- Short text for the document card in the UI
    routing_destination routing_destination,
    status              document_status NOT NULL DEFAULT 'received',
    source_metadata     JSONB,
        -- Channel-specific metadata:
        -- camera_scan: { "image_refs": ["gs://..."], "scan_quality": 0.92 }
        -- email:       { "from", "subject", "received_at", "message_id" }
        -- mail_station: { "station_id", "scanned_by", "batch_id" }
    received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at        TIMESTAMPTZ,
    acknowledged_at     TIMESTAMPTZ,
    retention_phase     retention_phase NOT NULL DEFAULT 'full',

    -- V2 extension point: agency-scoped document routing
    -- agency_routing_rule_id UUID REFERENCES agency_routing_rules(id),

    CONSTRAINT chk_processing_order CHECK (
        processed_at IS NULL OR processed_at >= received_at
    ),
    CONSTRAINT chk_acknowledged_order CHECK (
        acknowledged_at IS NULL OR acknowledged_at >= received_at
    )
);
```

### 2.5 functional_memory

```sql
CREATE TABLE functional_memory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category    memory_category NOT NULL,
    key         TEXT NOT NULL,
        -- Examples: "primary_care_doctor", "pharmacy_phone", "preferred_grocery_store"
    value       JSONB NOT NULL,
        -- Structured value. Examples:
        -- { "name": "Dr. Patel", "phone": "555-0142", "address": "..." }
        -- { "store": "Safeway", "location": "Main St" }
    source      memory_source NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, category, key)
);

CREATE TRIGGER trg_functional_memory_updated_at
    BEFORE UPDATE ON functional_memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 2.6 medications

```sql
CREATE TABLE medications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    dosage      TEXT NOT NULL,
    frequency   TEXT NOT NULL,
        -- Human-readable: "twice daily", "every 8 hours", "as needed"
    schedule    JSONB NOT NULL,
        -- Array of times: ["08:00", "20:00"]
        -- For PRN/as-needed: { "type": "prn", "max_daily": 3 }
    pharmacy    TEXT,
    prescriber  TEXT,
    refill_due_at DATE,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_medications_updated_at
    BEFORE UPDATE ON medications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 2.7 medication_confirmations

```sql
CREATE TABLE medication_confirmations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    medication_id   UUID NOT NULL REFERENCES medications(id) ON DELETE CASCADE,
    scheduled_at    TIMESTAMPTZ NOT NULL,
    confirmed_at    TIMESTAMPTZ,
    missed          BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT chk_confirmed_or_missed CHECK (
        NOT (confirmed_at IS NOT NULL AND missed = TRUE)
    )
);
```

### 2.8 appointments

```sql
CREATE TABLE appointments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider_name       TEXT NOT NULL,
    location            JSONB,
        -- { "name", "address", "phone", "coordinates": { "lat", "lng" } }
    appointment_at      TIMESTAMPTZ NOT NULL,
    travel_plan         JSONB,
        -- Nullable. Populated when transit directions are resolved.
        -- { "mode": "bus", "depart_at": "...", "route_summary": "Take #12 to...",
        --   "estimated_minutes": 35, "backup_plan": "Call Lyft" }
    reminder_sent       BOOLEAN NOT NULL DEFAULT FALSE,
    preparation_notes   TEXT,
        -- "Bring insurance card. Fasting required — no food after midnight."
    source_document_id  UUID REFERENCES documents(id) ON DELETE SET NULL,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 2.9 bills

```sql
CREATE TABLE bills (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sender                  TEXT NOT NULL,
    description             TEXT,
    amount                  DECIMAL(10,2) NOT NULL,
    due_date                DATE NOT NULL,
    account_number_masked   TEXT,
        -- Last 4 digits only: "••••3847"
    payment_status          payment_status NOT NULL DEFAULT 'pending',
    source_document_id      UUID REFERENCES documents(id) ON DELETE SET NULL,
    reminder_set            BOOLEAN NOT NULL DEFAULT FALSE,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_bills_updated_at
    BEFORE UPDATE ON bills
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 2.10 todos

```sql
CREATE TABLE todos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    category        todo_category NOT NULL DEFAULT 'general',
    source          todo_source NOT NULL DEFAULT 'user',
    due_date        DATE,
    completed_at    TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_todos_updated_at
    BEFORE UPDATE ON todos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 2.11 questions_tracker

```sql
CREATE TABLE questions_tracker (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_text               TEXT NOT NULL,
    context_type                question_context_type NOT NULL,
    context_ref_id              UUID,
        -- Polymorphic FK: points to medication, bill, document, etc.
        -- Not enforced by DB constraint; validated at application layer.
    urgency_level               urgency_level NOT NULL DEFAULT 'routine',
    escalation_threshold_hours  INT NOT NULL DEFAULT 24,
    asked_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    responded_at                TIMESTAMPTZ,
    escalated_at                TIMESTAMPTZ,
    status                      question_status NOT NULL DEFAULT 'open',

    CONSTRAINT chk_escalation_after_ask CHECK (
        escalated_at IS NULL OR escalated_at >= asked_at
    )
);
```

### 2.12 caregiver_activity_log

```sql
CREATE TABLE caregiver_activity_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trusted_contact_id  UUID NOT NULL REFERENCES trusted_contacts(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action              caregiver_action NOT NULL,
    details             JSONB,
        -- { "section": "bills", "items_viewed": 3 }
        -- { "alert_type": "medication_missed", "medication_id": "..." }
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.13 deletion_audit_log

```sql
CREATE TABLE deletion_audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
        -- No FK: user row may itself be deleted
    entity_type TEXT NOT NULL,
        -- Table name: 'documents', 'functional_memory', 'medications', etc.
    entity_id   UUID NOT NULL,
    reason      deletion_reason NOT NULL,
    deleted_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.14 System Configuration & Admin Schemas

```sql
-- ── System Configuration ─────────────────────────────────────────────
-- Stores runtime configuration that can be changed without redeployment.
-- Used by Config Admin UI. Changes emit config.updated events.

CREATE TYPE config_category AS ENUM (
    'dd_persona',             -- D.D. persona prompt, constraints
    'dd_voice',               -- TTS voice profile configurations
    'pipeline_threshold',     -- Classification confidence, junk cutoff
    'escalation_threshold',   -- Per-question-type escalation windows
    'notification_default',   -- Quiet hours, check-in time defaults
    'email_prefilter',        -- Email pre-filter rules (junk patterns)
    'summarization_prompt',   -- Summarization prompt templates per doc type
    'feature_flag'            -- V1 feature toggles
);

CREATE TABLE system_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category        config_category NOT NULL,
    key             TEXT NOT NULL,
    value           JSONB NOT NULL,
    description     TEXT,                    -- human-readable explanation
    is_active       BOOLEAN NOT NULL DEFAULT true,
    version         INTEGER NOT NULL DEFAULT 1,
    updated_by      TEXT NOT NULL,           -- admin user identifier
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (category, key)
);

-- Audit trail for config changes — every change is tracked
CREATE TABLE config_audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id       UUID NOT NULL REFERENCES system_config(id),
    category        config_category NOT NULL,
    key             TEXT NOT NULL,
    old_value       JSONB,
    new_value       JSONB NOT NULL,
    changed_by      TEXT NOT NULL,
    reason          TEXT,                    -- why the change was made
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Pipeline health metrics — written by pipeline, read by ops dashboard
CREATE TABLE pipeline_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID REFERENCES documents(id),
    stage           TEXT NOT NULL,           -- 'ingestion', 'classification', etc.
    status          TEXT NOT NULL,           -- 'started', 'completed', 'failed'
    duration_ms     INTEGER,
    error_message   TEXT,
    metadata        JSONB,                   -- stage-specific metrics (confidence scores, etc.)
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pipeline_metrics_stage_status ON pipeline_metrics (stage, status, recorded_at);
CREATE INDEX idx_pipeline_metrics_recorded_at ON pipeline_metrics (recorded_at);

-- Admin users — separate from Sam users, for internal team only
CREATE TABLE admin_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'viewer',  -- 'viewer', 'editor', 'admin'
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);
```

### 2.15 Additional Tables and Columns (Migrations 002–019)

The following tables and schema changes were added after the initial schema via Alembic migrations:

**New tables:**

| Table | Migration | Purpose |
|---|---|---|
| `device_tokens` | 009 | FCM push notification tokens per user/device. Columns: `user_id`, `fcm_token` (unique), `device_platform`, `device_name`, `is_active`, `created_at`, `last_used_at`. |
| `chat_sessions` | 010 | Persistent conversation session records. Columns: `user_id`, `session_id` (unique), `started_at`, `ended_at`, `message_count`, `firestore_path`. |
| `document_chunks` | 011 | pgvector-backed RAG embeddings. Columns: `document_id`, `user_id`, `chunk_index`, `chunk_text`, `source_field`, `embedding` (vector), `created_at`. Uses cosine similarity for retrieval. |
| `pending_reviews` | 013 + 015 | Document review queue — pipeline proposes records (bills, appointments, medications) and the user confirms or rejects. Columns: `user_id`, `document_id`, `review_status`, `recommended_action`, `proposed_record_data` (KMS-encrypted JSONB), `target_table`, `target_record_id`, `short_id`, `spoken_summary` (KMS-encrypted), `card_summary` (KMS-encrypted), `presented_at`, `resolved_at`. |
| `caregiver_assignment_requests` | (initial schema extension) | Tracks pending caregiver-to-member assignment requests for self-directed members. |

**Column additions to existing tables:**

| Table | Column(s) | Migration | Purpose |
|---|---|---|---|
| `users` | `first_name`, `last_name` | 002 | Split name fields for formal documents |
| `users` | `deactivated_at`, `deletion_scheduled_at` | 004 | Account deactivation and scheduled deletion lifecycle |
| `trusted_contacts` | `invitation_status`, `invitation_token`, `invited_at`, `invited_by_admin_id`, `invited_by_user_id`, `accepted_at` | 003 | Caregiver invitation flow (pending/accepted/declined/expired) |
| `documents` | `reading_grade` | 016 | Flesch-Kincaid reading grade level of spoken summaries |
| `documents` | `page_count` | 018 | Number of pages in scanned document |
| `documents` | `spoken_summary`, `card_summary`, `extracted_fields` | 017 | Migrated to KMS-encrypted columns (`EncryptedText`, `EncryptedJSON`) |
| `todos` | `related_bill_id` | 019 | Links auto-generated bill payment to-dos to their source bill |

**Enum additions:**

| Enum | Values Added | Migration |
|---|---|---|
| `config_category` | `dd_persona`, `dd_voice`, `deletion_settings` | 006, 007 |
| `document_status` | `pending_review` | 014 |
| `deletion_reason` | `admin_request` | 008 |

---

## 3. Redis Namespace Design

All Redis keys are prefixed by namespace for isolation. TTLs are enforced at write time. All values are JSON-serialized unless noted.

### 3.1 Key Patterns

| Key Pattern | Value Type | TTL | Purpose |
|---|---|---|---|
| `ctx:{user_id}:{memory_id}` | JSON | 48 hours | Contextual memory window. Short-lived facts D.D. uses mid-conversation (e.g., "user just mentioned they have a headache"). Evicts automatically; not persisted to PostgreSQL. |
| `session:{user_id}:{session_id}` | JSON | 2 hours | Conversation session state. Holds current topic, slot-filling progress, pending confirmations. Renewed on each interaction; expires after inactivity. |
| `rate:{api_surface}:{user_id}` | Sorted set | Sliding window (varies) | Rate limiting. Members are timestamps; scored by epoch ms. Surface examples: `sms`, `voice`, `document_upload`, `caregiver_api`. |
| `cache:section:{user_id}:{section}` | JSON | 5 minutes | Pre-rendered section data for the home screen (e.g., bills summary, medication schedule). Invalidated on write; TTL is a safety net. Section values: `home`, `my_health`, `bills`, `plans`. |
| `lock:pipeline:{document_id}` | String (worker ID) | 10 minutes | Distributed lock for document processing pipeline. Prevents duplicate classification when the same document arrives via multiple channels. Uses `SET NX EX`. |
| `config:{category}:{key}` | JSON | 5 minutes | Cached active config values. Invalidated on `config.updated` event. |

### 3.2 Rate Limiting Detail

Rate limits use a sorted-set sliding window pattern:

```
ZADD rate:sms:{user_id} {now_ms} {request_id}
ZREMRANGEBYSCORE rate:sms:{user_id} 0 {now_ms - window_ms}
ZCARD rate:sms:{user_id}
EXPIRE rate:sms:{user_id} {window_seconds}
```

Default limits:

| Surface | Window | Max Requests |
|---|---|---|
| `sms` | 1 minute | 10 |
| `voice` | 1 minute | 5 |
| `document_upload` | 1 hour | 50 |
| `caregiver_api` | 1 minute | 30 |

### 3.3 Cache Invalidation

Section caches are invalidated by publishing to a Redis Pub/Sub channel:

```
PUBLISH cache:invalidate:{user_id} '{"section": "bills"}'
```

Subscribers delete the matching key. The 5-minute TTL ensures stale data self-heals even if a Pub/Sub message is lost.

---

## 4. Event Bus Catalog

Events are published to a message broker (Google Cloud Pub/Sub or NATS, TBD based on API framework). All payloads include a standard envelope:

```json
{
  "event_id": "uuid",
  "event_name": "document.received",
  "user_id": "uuid",
  "occurred_at": "ISO-8601",
  "payload": { }
}
```

### 4.1 Event Table

| Event Name | Payload Schema | Publishers | Subscribers |
|---|---|---|---|
| `document.received` | `{ document_id, source_channel, raw_text_ref }` | Ingest API, Email Watcher, Mail Station Agent | Document Pipeline |
| `document.processed` | `{ document_id, classification, confidence_score, urgency_level, extracted_fields }` | Document Pipeline | Routing Engine, Notification Service |
| `document.routed` | `{ document_id, routing_destination, card_summary, spoken_summary }` | Routing Engine | Home Screen Cache, Notification Service |
| `question.asked` | `{ question_id, question_text, context_type, context_ref_id, urgency_level }` | D.D. Conversation Engine | Questions Tracker, Notification Service |
| `question.answered` | `{ question_id, answer_source }` | D.D. Conversation Engine, User Input | Questions Tracker |
| `question.threshold_crossed` | `{ question_id, hours_open, escalation_threshold_hours, trusted_contact_ids }` | Escalation Scheduler | Caregiver Alert Service, Notification Service |
| `medication.confirmed` | `{ confirmation_id, medication_id, scheduled_at, confirmed_at }` | User Input (SMS/Voice/App) | Medication Tracker, Home Screen Cache |
| `medication.missed` | `{ confirmation_id, medication_id, scheduled_at }` | Medication Scheduler | Caregiver Alert Service, Notification Service |
| `bill.acknowledged` | `{ bill_id, user_id }` | User Input | Bills Tracker, Home Screen Cache |
| `bill.overdue` | `{ bill_id, sender, amount, due_date, days_overdue }` | Bill Scheduler | Notification Service, Caregiver Alert Service |
| `trip.started` | `{ appointment_id, travel_plan, depart_at }` | Travel Service | Notification Service, Home Screen Cache |
| `trip.completed` | `{ appointment_id, arrived_at }` | Travel Service | Home Screen Cache |
| `away.mode.set` | `{ user_id, away_expires_at }` | User Input, Caregiver Input | Notification Service, All Schedulers |
| `away.mode.extended` | `{ user_id, previous_expires_at, new_expires_at }` | User Input | Notification Service, All Schedulers |
| `memory.updated` | `{ memory_id, category, key, source }` | D.D. Conversation Engine, Document Pipeline, Onboarding | Functional Memory Store, Home Screen Cache |
| `memory.deleted` | `{ memory_id, category, key, reason }` | User Input, Retention Worker | Deletion Audit Logger, Home Screen Cache |
| `caregiver.alert.triggered` | `{ trusted_contact_id, alert_type, context }` | Caregiver Alert Service | Notification Service (SMS/Email to caregiver) |
| `caregiver.dashboard.viewed` | `{ trusted_contact_id, user_id, sections_viewed }` | Caregiver API | Caregiver Activity Logger |
| `notification.delivered` | `{ notification_id, channel, user_id, content_type }` | Notification Service | Analytics |
| `notification.dismissed` | `{ notification_id, user_id, dismissed_at }` | User Input | Analytics |
| `checkin.morning.triggered` | `{ user_id, checkin_time, items_count }` | Morning Checkin Scheduler | Notification Service, D.D. Conversation Engine |
| `checkin.morning.acknowledged` | `{ user_id, acknowledged_at, items_reviewed }` | User Input | Home Screen Cache, Analytics |
| `config.updated` | `{ config_id, category, key, old_value, new_value, changed_by }` | Admin Service | Conversation Service (reload prompts), Pipeline Service (reload thresholds), Notification Service (reload defaults) |

---

## 5. Data Retention Policy

Retention is enforced by a nightly batch job (`retention_worker`) that transitions documents through phases and purges expired data. Users can configure retention windows within the allowed ranges via settings.

### 5.1 Retention Phases

| Phase | Default Window | Configurable Range | What Is Kept | What Is Purged |
|---|---|---|---|---|
| **Full** | 0 -- 30 days | 7 -- 90 days | Everything: raw text in GCS, extracted fields, summaries, source metadata, all linked records | Nothing |
| **Important Only** | 31 -- 90 days | 30 days -- 1 year | Documents classified as `bill`, `legal`, `government`, `medical`, `insurance`, `form`, `personal`. Extracted fields and summaries retained. | Raw text deleted from GCS. `junk` and `unknown` documents deleted entirely. Source images deleted. |
| **Metadata Only** | 91+ days | 90 days -- forever | Document row with: `id`, `user_id`, `classification`, `urgency_level`, `routing_destination`, `received_at`, `status`. All other fields nulled. | Extracted fields, summaries, source metadata, GCS references. |

### 5.2 Special Rules

| Document Type | Rule |
|---|---|
| **Junk** (`classification = 'junk'`) | Hard-deleted at 30 days regardless of user settings. No metadata retained. Deletion logged to `deletion_audit_log`. |
| **Legal / Government** | Never drops below `metadata_only`. These rows are retained indefinitely even if the user's metadata window would otherwise expire them. |
| **User-pinned documents** | Documents the user explicitly marks as "keep" skip all automatic retention transitions. (Tracked via a `pinned` boolean, added in a future migration.) |

### 5.3 Retention Transition SQL

```sql
-- Phase 1 -> Phase 2: Delete raw text, purge junk
UPDATE documents
SET retention_phase = 'important_only',
    raw_text_ref = NULL
WHERE retention_phase = 'full'
  AND received_at < now() - (
      SELECT COALESCE(
          (settings->>'full_retention_days')::int,
          30
      ) * INTERVAL '1 day'
      FROM users WHERE id = documents.user_id
  );

DELETE FROM documents
WHERE classification IN ('junk', 'unknown')
  AND received_at < now() - INTERVAL '30 days';

-- Phase 2 -> Phase 3: Strip to metadata
UPDATE documents
SET retention_phase = 'metadata_only',
    extracted_fields = NULL,
    spoken_summary = NULL,
    card_summary = NULL,
    source_metadata = NULL
WHERE retention_phase = 'important_only'
  AND received_at < now() - (
      SELECT COALESCE(
          (settings->>'important_retention_days')::int,
          90
      ) * INTERVAL '1 day'
      FROM users WHERE id = documents.user_id
  );
```

---

## 6. Indexes and Performance

### 6.1 Primary Query Indexes

```sql
-- User's documents by urgency and status (home screen, document inbox)
CREATE INDEX idx_documents_user_urgency_status
    ON documents (user_id, urgency_level DESC, status)
    WHERE status NOT IN ('handled');

-- User's open questions ordered by escalation deadline
CREATE INDEX idx_questions_user_open_escalation
    ON questions_tracker (user_id, (asked_at + escalation_threshold_hours * INTERVAL '1 hour'))
    WHERE status = 'open';

-- Bills by due date for overdue detection and reminders
CREATE INDEX idx_bills_user_due_date
    ON bills (user_id, due_date)
    WHERE payment_status IN ('pending', 'acknowledged');

-- Medication confirmations by schedule date (daily check-in, missed detection)
CREATE INDEX idx_med_confirmations_schedule
    ON medication_confirmations (medication_id, scheduled_at DESC);

-- Active medications for a user (medication schedule screen)
CREATE INDEX idx_medications_user_active
    ON medications (user_id)
    WHERE is_active = TRUE;

-- Caregiver access log by user and tier (audit, dashboard)
CREATE INDEX idx_caregiver_log_user
    ON caregiver_activity_log (user_id, occurred_at DESC);

-- Trusted contacts by user and active status
CREATE INDEX idx_trusted_contacts_user_active
    ON trusted_contacts (user_id, access_tier)
    WHERE is_active = TRUE;

-- Functional memory lookup (D.D. conversation context)
CREATE INDEX idx_functional_memory_user_category
    ON functional_memory (user_id, category);

-- Document retention worker (nightly batch)
CREATE INDEX idx_documents_retention
    ON documents (retention_phase, received_at);

-- Appointments upcoming (travel planning, reminders)
CREATE INDEX idx_appointments_user_upcoming
    ON appointments (user_id, appointment_at)
    WHERE appointment_at > now();

-- Active to-dos for a user
CREATE INDEX idx_todos_user_active
    ON todos (user_id, due_date NULLS LAST)
    WHERE is_active = TRUE AND completed_at IS NULL;

-- Deletion audit log by user (GDPR/compliance queries)
CREATE INDEX idx_deletion_audit_user
    ON deletion_audit_log (user_id, deleted_at DESC);
```

### 6.2 JSONB Indexes

```sql
-- GIN index on extracted_fields for ad-hoc queries during support/debugging
CREATE INDEX idx_documents_extracted_fields
    ON documents USING GIN (extracted_fields jsonb_path_ops);

-- GIN index on functional memory values for search
CREATE INDEX idx_functional_memory_value
    ON functional_memory USING GIN (value jsonb_path_ops);
```

### 6.3 Performance Notes

- **Partial indexes** are used aggressively (e.g., `WHERE is_active = TRUE`, `WHERE status = 'open'`) to keep index sizes small. Most queries filter on active/open state.
- **Composite indexes** are ordered by selectivity: `user_id` first (high cardinality across the table, but each query targets one user), then the sort/filter column.
- **The retention worker** uses `idx_documents_retention` and processes documents in batches of 1,000 with `FOR UPDATE SKIP LOCKED` to avoid contention.
- **Connection pooling** via PgBouncer in transaction mode. Target: 20 connections per API instance, max 100 total.

---

## 7. Migration Strategy

### 7.1 Tool Choice

The migration tool will be selected based on the API framework:

| Framework | Migration Tool | Notes |
|---|---|---|
| Node.js / TypeScript | Prisma Migrate | Schema-first, generates typed client. Good fit if we use a TypeScript API. |
| Python / FastAPI | Alembic | Pairs with SQLAlchemy. Auto-generates diffs from model changes. |
| JVM / Kotlin | Flyway | SQL-based migrations. Framework-agnostic. |

Regardless of tool, migrations are SQL-first. The DDL in this document should be directly usable as the V1 migration with minimal adaptation.

### 7.2 Migration Conventions

- Migrations are numbered sequentially: `V001__create_enum_types.sql`, `V002__create_users.sql`, etc.
- Every migration is idempotent where possible (`CREATE TYPE IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`).
- Destructive migrations (column drops, type changes) require a two-phase approach: (1) deploy code that handles both old and new schema, (2) run the migration, (3) deploy code that only handles new schema.
- All migrations run inside a transaction. DDL that cannot run in a transaction (e.g., `CREATE INDEX CONCURRENTLY`) is flagged and run separately.

### 7.3 V2 Extension Points

The schema is designed with the following V2 additions in mind. Commented-out columns in the V1 tables mark these extension points.

| V2 Feature | Schema Changes | V1 Preparation |
|---|---|---|
| **Agency accounts** | New tables: `agencies`, `agency_staff`, `agency_routing_rules`. FK from `users.agency_id` to `agencies.id`. | `users` has a commented `agency_id` column. All queries already scope by `user_id`, so adding an agency layer is additive. |
| **Multi-user caregiver dashboard** | `trusted_contacts` gains an `agency_staff_id` FK. New composite indexes on `(agency_staff_id, user_id)`. | `trusted_contacts` has a commented `agency_staff_id` column. The `caregiver_activity_log` already tracks `trusted_contact_id` and `user_id` separately. |
| **Custom classification models** | New table: `classification_models` with `agency_id` scope. `documents.classification` becomes a TEXT column (dropping the enum) or the enum is extended. | Using PostgreSQL enums means adding values is a non-blocking `ALTER TYPE ... ADD VALUE`. No structural change needed. |
| **Pinned documents** | `documents` gains a `pinned BOOLEAN DEFAULT FALSE` column. Retention worker skips pinned documents. | Retention SQL already uses `WHERE` clauses that can be extended with `AND NOT pinned`. |
| **Shared to-do lists** | New table: `shared_todos` linking `todos` to multiple `trusted_contacts`. | `todos` is self-contained; sharing is additive via a join table. |

### 7.4 Seed Data

The V1 migration includes seed data for:

- Default D.D. voice/personality settings
- Enum values (handled by the `CREATE TYPE` statements above)
- A test user for development environments (gated behind `COMPANION_ENV = 'development'`)

No production seed data beyond the enum types.
