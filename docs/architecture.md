# D.D. Companion -- System Architecture

> Independence assistant for adults with developmental disabilities.
> D.D. is the AI persona. "Sam" is the canonical user.

Last updated: 2026-04-04

---

## 1. System Overview

Companion is a mobile-first application that helps adults with developmental disabilities manage daily life -- bills, health information, mail, and upcoming events -- through an AI persona named D.D. The system ingests documents (camera scans and email), extracts structured data via an ML pipeline, and surfaces actionable items through a conversational interface tuned for plain language. A parallel caregiver surface provides scoped visibility without undermining the user's autonomy.

```
  Mobile App (React Native)          Web Dashboard (React/Vite)
        |                          /           |          \
        |                   Caregiver       Ops         Admin
        |                   Dashboard    Dashboard     Config
        |                        \          |          /
        +----------+-------------+----------+---------+
                   |
            Cloud Run Backend (FastAPI)
                   |
     +------+------+------+-------+
     |      |      |      |       |
   App   Caregiver Pipeline Admin  Internal
   API     API      API    API   Workers API
     |      |      |      |       |
     +------+------+------+-------+
                   |
         +--------+--------+
         |        |        |
     PostgreSQL  Redis   Pub/Sub
         |                  |
         |        +---------+---------+
         |        |         |         |
       Cloud    Document  Notification Background
       Storage  Pipeline    Engine     Workers
         |
     External Services
     (Vertex AI, Document AI, TTS, STT, Firebase, Gmail)
```

All services run within a single Cloud Run deployment. API surfaces are logically separated by URL prefix and auth requirements, but share one FastAPI process, one database connection pool, and one Redis connection.

---

## 2. Technology Stack

| Concern | Choice |
|---|---|
| Language / Framework | Python 3.12 / FastAPI |
| Primary Database | PostgreSQL 16 (Cloud SQL) |
| Cache / Session Store | Redis 7 |
| Vector Store | pgvector (PostgreSQL extension) |
| Event Bus | Google Cloud Pub/Sub |
| Object Storage | Google Cloud Storage |
| Auth | Firebase Auth (separate tenants for users, caregivers, admins) |
| LLM (primary) | Gemini 2.5 Flash via Vertex AI |
| LLM (fallbacks) | Anthropic Claude, OpenAI (via abstraction layer) |
| OCR | Google Document AI |
| TTS | Google Cloud TTS (WaveNet / Neural2) |
| STT | Google Cloud Speech-to-Text v2 |
| Wake Word | Picovoice Porcupine (on-device) |
| Field Encryption | Google Cloud KMS (AES-256-GCM) |
| Mobile App | React Native 0.84 |
| Web Dashboard | React 18 / Vite / Tailwind CSS |
| Repo Layout | Monorepo (`backend/`, `web/`, `companion-app/`) |

---

## 3. Service Boundaries

The backend is a single FastAPI application exposing five API surfaces under distinct URL prefixes. Each surface has its own auth requirements and rate limits.

### 3.1 App API (`/api/v1/*`)

Serves the React Native client. Full CRUD over user data: documents, medications, appointments, bills, todos, contacts, conversation, notifications. Auth: Firebase user JWT. Rate limit: 120 req/min.

### 3.2 Caregiver API (`/api/v1/caregiver/*`)

Read-only, tier-gated access for trusted contacts. Returns pre-summarized data only -- the summarization layer sits between the API and the database, and no raw data (document text, financial amounts, memory entries) leaves that boundary. Auth: Firebase caregiver JWT with tier claims. Rate limit: 60 req/min.

See `docs/architecture/06-caregiver-access-and-privacy.md` for the full privacy model, three-tier access system, and hard restrictions.

### 3.3 Pipeline API (`/api/v1/pipeline/*`)

Write-only endpoint for document processing results. VPC-internal, authenticated via GCP service account. Called by Pub/Sub push subscriptions when pipeline stages complete.

### 3.4 Admin API (`/api/v1/admin/*`)

Serves the ops dashboard and config admin. Pipeline health, escalation monitoring, pilot metrics, system configuration CRUD. Auth: Firebase admin JWT with role-based access (viewer, editor, admin). All config mutations require a `reason` field and are audit-logged.

### 3.5 Internal Workers API (`/api/internal/workers/*`)

Endpoints invoked by Cloud Scheduler (HTTP targets) and Pub/Sub push subscriptions. Not internet-routable. Handles recurring jobs: morning check-in trigger, medication reminders, escalation checks, TTL purge, data retention enforcement, away mode monitoring, account deletion.

---

## 4. Document Intelligence Pipeline

The pipeline transforms raw documents (camera scans, email attachments) into structured, actionable data surfaced through D.D. Processing is fully async -- D.D. acknowledges receipt within 2 seconds, then delivers results when the pipeline completes.

### 4.1 Pipeline Stages

```
Input (camera scan or email)
  |
  v
Stage 1: Ingest & Normalize -- store raw in GCS, produce NormalizedDocument
  |
  v
Stage 2: Classify -- Tier 1 (rule-based, conf > 0.95) or Tier 2 (LLM)
  |                  Types: bill, legal, government, medical, insurance, form, junk, personal, unknown
  |                  Urgency: routine, needs_attention, act_today, urgent
  v
Stage 3: Extract -- type-specific structured data (amounts, dates, providers)
  |                 Field-level KMS encryption for sensitive fields
  v
Stage 4: Summarize -- spoken summary (3 sentences, 4th-6th grade reading level)
  |                   card summary (title, key facts, urgency label, action button)
  |                   Flesch-Kincaid validation via text_complexity.py
  v
Stage 5: Route -- map to app section (Home, My Health, Bills, What's Coming Up)
  |               generate suggested action
  v
Stage 6: Chunk & Embed -- split into chunks, generate pgvector embeddings for RAG
  |
  v
Stage 7: Pending Review -- propose records (bills, meds, appointments)
  |                        D.D. presents to user for confirmation before creating
  v
Stage 8: Question Tracker -- log unanswered questions, set escalation timers
  |
  v
Delivered (to user via D.D.)
```

### 4.2 Classification Hard Rules

Applied after both classifier tiers -- these override model output:

- Junk classification with confidence < 0.90 is reclassified as `unknown` with urgency `needs_attention`. Missing a bill is worse than surfacing junk.
- Unknown documents always get `needs_attention`. Never silently archived.
- Legal/collections/eviction keywords force urgency to `urgent` regardless of model confidence.
- Government documents never classified below `needs_attention`.

### 4.3 Key Invariants

- Every document that enters the pipeline exits. Nothing is silently dropped.
- Extraction never fabricates missing fields. Missing data is set to `null` and flagged.
- Confidence-based hedging in summaries: high (> 90%) states facts plainly, medium (70-90%) asks for confirmation, low (< 70%) asks to look together.

### 4.4 Pipeline Status Flow

```
ingested -> classifying -> classified -> extracting -> extracted ->
summarizing -> summarized -> routing -> routed -> embedding -> embedded ->
pending_review -> delivered
```

Failed states: `ocr_failed`, `classification_failed`, `extraction_failed`, `timeout`.

---

## 5. Conversation Layer

D.D.'s conversational interface is built from seven components: wake word detection, STT, conversation state manager, LLM prompt engine, function-calling tools, RAG retrieval, and TTS.

### 5.1 Prompt Architecture

The system prompt is dynamically assembled from five components at session start:

| # | Component | Nature | Content |
|---|---|---|---|
| 1 | D.D. Persona | Fixed | Communication style, emotional boundaries, tone rules |
| 2 | Sam's Information | Dynamic | Medications, providers, bills, contacts, preferences (from functional memory) |
| 3 | Session Context | Dynamic | Trigger type, current time, current section, recent documents |
| 4 | Active Alerts | Dynamic | Priority items sorted by urgency level |
| 5 | Constraints | Fixed | Response length limits, honesty rules, scope boundaries, confirmation requirements |

See `docs/dd-assistant-guidelines.md` for the full persona specification and conversation rules.

### 5.2 Function Calling (Tools)

D.D. uses Gemini function calling to take actions. Tools are declared in `conversation/tools.py` and executed by `conversation/tool_executor.py` against backend services. Tool categories:

- **Data queries**: list medications, upcoming appointments, bills, todos
- **Actions**: mark bill as paid, add todo, confirm appointment, set reminder
- **Memory**: store/recall functional memory entries
- **Pending reviews**: present proposed records, confirm/reject

### 5.3 RAG Retrieval

During conversation, relevant document context is retrieved via pgvector cosine similarity search over `document_chunks` (`conversation/retrieval.py`). This allows D.D. to reference specific document content when answering questions.

### 5.4 Conversation State

Session state is Redis-backed with the following lifecycle:

- **Session start**: generate session ID, load functional memory, load active alerts, check for saved guided tasks
- **Token budget**: system prompt + reserved response tokens are subtracted from context window; remainder is conversation history
- **Compression**: at 80% of history budget, oldest turns are summarized by a secondary LLM call, preserving decisions and commitments
- **Guided flows**: Forms Assistant, Travel Assistant, Medication Setup -- support interruption via a task stack (max depth 3)
- **Inactivity**: 5 min warning, 15 min graceful end with state serialization

### 5.5 Response Safety Layer

Every LLM response passes through `conversation/safety.py` before reaching the member. This provides defense-in-depth against prompt injection and system prompt leakage.

**Canary token detection:** A set of 20+ unique phrases from the constitution, persona, and internal tool names are checked against every response. If any appear, the response is blocked, a `CRITICAL` log alert fires, and the member sees a safe fallback ("I got confused, could you say that again?").

**Wired into:** All response paths in `api/v1/conversation.py` — greeting generation, tool loop results, and exhausted-iteration fallbacks.

**Not a security boundary:** The canary check is a detection mechanism. The real security is backend-enforced (tool access scoped by user_id, action authorization). See [D.D. Assistant Guidelines Section 11](dd-assistant-guidelines.md) for the full security model.

**Exploitation indicator detection:** User messages are scanned for patterns suggesting financial exploitation (someone new managing money, pressure to act quickly, sharing account info, signing unknown documents, etc.). When detected:
- The system prompt is augmented with the exploitation response protocol (pause, express concern, suggest verification, delay financial actions)
- A `WARNING`-level log fires with the matched indicators
- Caregivers are notified immediately (safety-tier — no member opt-out)
- D.D. does not accuse anyone, but slows down and encourages verification

See [D.D. Assistant Guidelines Section 7](dd-assistant-guidelines.md) for the full exploitation playbook.

### 5.6 Voice

- **TTS**: four curated voice profiles (Warm, Calm, Bright, Clear) with user-adjustable pace and warmth. SSML markup for emphasis on amounts, dates, names, and wider pauses between sentences.
- **STT**: Google Cloud Speech-to-Text v2, streaming mode. Per-user phrase hints for medication names, providers, contacts. Confidence < 0.60 triggers re-prompt ("I didn't quite catch that").
- **Wake word**: Picovoice Porcupine, on-device, custom "D.D." model. Opt-in on mobile, always-on on dedicated devices.

---

## 6. Notification Engine

### 6.1 Priority Levels

| Level | Label | Examples | Delivery |
|---|---|---|---|
| 1 - Urgent | Today | Legal notices, escalated items | Breaks quiet hours, immediate |
| 2 - Act Today | Today | Bills due < 48h, appointments tomorrow, missed meds | Active hours, morning check-in + 1 standalone |
| 3 - Needs Attention | Soon | Bills due < 7 days, appointments this week | Morning check-in + 1 follow-up |
| 4 - Routine | Can Wait | Supply reminders, memory review prompts | Morning check-in only |

### 6.2 Morning Check-In

The most important notification. Daily at user's configured time. Structure:

1. Greeting
2. Most important thing (Level 1-2 items only)
3. Today (appointments, medications, errands)
4. This week (upcoming bills, appointments, deadlines -- max 5 items)
5. Close

Items are presented one at a time. D.D. waits for acknowledgment before proceeding. Max 90 seconds spoken.

### 6.3 Delivery Rules

- **One at a time**: notifications queue by priority, each delivered after the previous is acknowledged or 60s elapses
- **Quiet hours**: Level 1 breaks through with apology prefix; Level 2-4 queued until morning
- **Diminishing repetition**: max 2 standalone deliveries, then folds into morning check-in. D.D. never nags.
- **Channels**: voice (app open), push notification (background), in-app card (persistent record), caregiver alert (escalations only)

### 6.4 Escalation

Unanswered questions are tracked with type-specific escalation timers:

| Question Type | Escalation Window |
|---|---|
| Medication confirmation | 2 missed in a row |
| Bill action | 5 days before due date |
| Incomplete document (routine) | 24 hours |
| Incomplete document (urgent) | 4 hours |
| Legal unacknowledged | 24 hours |
| Form deadline | 72 hours before deadline |

Escalation alerts go to Tier 1 caregivers with minimum context (category + urgency, never raw data).

---

## 7. Data Model (High Level)

### 7.1 Storage Layers

| Layer | Technology | Purpose |
|---|---|---|
| Primary | PostgreSQL 16 | All domain entities. JSONB for semi-structured fields (extracted document data, schedules). pgvector extension for RAG embeddings. |
| Cache / TTL | Redis 7 | Conversation session state, contextual memory (48h TTL), rate limiting, distributed locks. |
| Object Storage | GCS | Raw document images, audio recordings. Referenced by GCS path from PostgreSQL. CMEK encryption. |

### 7.2 Core Tables

| Table | Purpose |
|---|---|
| `users` | Member accounts. Care model (self_directed / managed), preferences, account status. |
| `documents` | Ingested documents. Classification, extraction, summaries, pipeline status. Encrypted fields. |
| `document_chunks` | pgvector embeddings for RAG retrieval during conversation. |
| `medications` | Medication records with schedules. |
| `appointments` | Provider appointments with prep instructions. |
| `bills` | Bill tracking: amount, due date, payment status, autopay flag. |
| `todos` | User and system-generated tasks. |
| `trusted_contacts` | Caregiver relationships. Tier assignment, invitation status, pause/revoke state. |
| `collaboration_scopes` | Time-limited Tier 3 resource grants. Max 24h, auto-expire. |
| `functional_memory` | Long-term user facts (meds, providers, preferences). KMS-encrypted values. |
| `question_tracker` | Unanswered questions with escalation timers. |
| `pending_reviews` | Pipeline-proposed records awaiting user confirmation. |
| `chat_sessions` | Conversation session persistence. |
| `device_tokens` | FCM push token storage. |
| `system_config` | Runtime configuration (prompts, thresholds, voice profiles). |
| `pipeline_metrics` | Per-stage timing and success/failure counts. |
| `admin_users` | Internal admin accounts with roles. |
| `caregiver_activity_log` | Append-only audit log of all caregiver data access. |
| `assignment_requests` | Caregiver-to-member assignment approval flow. |
| `audit_log` | Config change audit trail. |

### 7.3 Redis Key Namespaces

| Namespace | Purpose | TTL |
|---|---|---|
| `session:{user_id}:{session_id}` | Conversation state | 15 min inactivity |
| `ctx:{user_id}:*` | Contextual memory (short-term emotional/situational) | 48 hours |
| `ratelimit:{user_id}:*` | Sliding window rate limit counters | Per-window |
| `lock:pipeline:{document_id}` | Pipeline idempotency locks | 5 min |

---

## 8. Event System & Communication Patterns

The backend uses two communication patterns. The choice depends on whether the work crosses a service boundary or is self-contained.

### 8.1 Pattern Selection Guide

| Pattern | When to Use | Retry? | Example |
|---------|-------------|--------|---------|
| **Pub/Sub Push** | Work crosses service boundaries, is long-running, needs retry/durability, or has multiple consumers | Yes (Pub/Sub retries failed deliveries) | Document received → pipeline processes asynchronously |
| **Direct Call** | Worker already has full context and the notification is a side-effect of the work it just completed | No (caller handles errors) | Morning briefing: worker generates briefing → sends push in same request |

**Decision criteria:**

Use **Pub/Sub Push** when:
- The publisher doesn't need to wait for the result (fire-and-forget)
- The consumer might fail and needs automatic retry
- Multiple consumers need to react to the same event
- The work is long-running (> 30 seconds) and could outlive the request
- The publisher and consumer may be in different services in the future

Use **Direct Call** when:
- The caller already has the database session, user context, and computed result
- The notification is a simple side-effect (one FCM push, one email)
- Failure is acceptable and can be logged without retry
- Adding Pub/Sub infrastructure would add complexity without value
- Everything runs in the same backend process

**Anti-pattern:** Publishing to Pub/Sub when no push subscription exists for the topic. The event goes to Pub/Sub and is never delivered. If the only consumer is in the same process, call it directly.

### 8.2 Pub/Sub Topics and Subscriptions

Events that use the Pub/Sub push pattern:

| Event | Published By | Push Subscription | Endpoint |
|---|---|---|---|
| `document.received` | App API (camera scan) | `document-received-push` | `/api/pipeline/document-received` |
| `document.processed` | Pipeline | Local handler (in-process) | — |
| `config.updated` | Admin API | Local handler (Redis cache invalidation) | — |

Events published for audit/logging only (no active consumer required):

| Event | Published By | Purpose |
|---|---|---|
| `medication.confirmed` | App API | Audit trail |
| `medication.missed` | Medication worker | Audit trail |
| `bill.overdue` | Document review | Audit trail |
| `question.threshold.crossed` | Question tracker | Audit trail |

### 8.3 Direct Call Flows

Workers that send notifications directly (no Pub/Sub):

| Worker | Generates | Then Calls | Rationale |
|---|---|---|---|
| `morning_trigger` | LLM briefing | `notify_morning_briefing()` | Worker has DB session, user context, and briefing text — push is a one-line call |
| `medication_reminder` | Confirmation records | `notify_medication_reminder()` | Same — worker already queried meds and user |
| `escalation_check` | Escalation evaluation | `notify_caregiver_status_change()` | Evaluation and notification are one logical unit |
| Document pipeline (post-process) | Pipeline result | `notify_document_processed()` | Called at end of pipeline handler, has summary text |
| Admin alert | User-specified message | `send_push()` | Admin action, immediate delivery expected |

### 8.4 Worker Schedule

| Worker | Trigger | Frequency | Purpose |
|---|---|---|---|
| `morning_trigger` | Cloud Scheduler | Every minute (checks user's configured time) | Generate LLM briefing, send push via FCM |
| `medication_reminder` | Cloud Scheduler | Every minute (checks medication schedules) | Create confirmation records, send push |
| `escalation_check` | Cloud Scheduler | Every 15 min | Evaluate question tracker thresholds |
| `ttl_purge` | Cloud Scheduler | Hourly | Clean expired Redis keys, temp audio files |
| `retention` | Cloud Scheduler | Daily | Enforce data retention phases (full -> metadata-only -> delete) |
| `away_monitor` | Cloud Scheduler | Daily | Check for extended inactivity, alert caregivers |
| `deletion_worker` | Cloud Scheduler | Daily | Enforce account deletion (30-day purge) |

---

## 9. Deployment Topology

### 9.1 Infrastructure

```
Cloud Run (single service, min 1 instance)
  |-- FastAPI backend (all API surfaces + worker endpoints)
  |-- Serves web dashboard static assets
  |
Cloud SQL (PostgreSQL 16)
  |-- pgvector extension
  |-- Automated backups
  |
Memorystore (Redis 7)
  |-- Session state, contextual memory, rate limits
  |
Cloud Storage
  |-- Raw document images (CMEK encrypted)
  |-- Pipeline artifacts
  |
Cloud Pub/Sub
  |-- Push subscriptions to Cloud Run endpoints
  |-- Dead-letter topics for failed messages
  |
Cloud Scheduler
  |-- HTTP targets to /api/internal/workers/* endpoints
  |
Firebase
  |-- Auth (user, caregiver, admin tenants)
  |-- Cloud Messaging (push notifications)
  |-- Firestore (real-time pipeline status sync)
```

### 9.2 Environments

| Environment | Purpose |
|---|---|
| `dev` | Local development via docker-compose (Postgres, Redis, Pub/Sub emulator) |
| `staging` | Pre-production on GCP. Full infrastructure. |
| `prod` | Production on GCP. Blue-green deploys for API, canary for pipeline changes. |

### 9.3 Security

- **Encryption at rest**: AES-256 for all PostgreSQL data, GCS objects, Redis snapshots
- **Encryption in transit**: TLS 1.3 for all connections
- **Field-level encryption**: KMS-managed keys for SSN fragments, bank account numbers, medical record numbers (separate keys from standard encryption, 30-day rotation)
- **PII log masking**: `PIIMaskingFilter` redacts sensitive keys from Cloud Logging
- **Auth bypass blocked in prod**: `dev_auth_bypass` raises `RuntimeError` if enabled in production

---

## 10. Cross-References

| Document | Covers |
|---|---|
| `docs/dd-assistant-guidelines.md` | D.D. persona rules, conversation constraints, tone guidelines |
| `docs/architecture/06-caregiver-access-and-privacy.md` | Three-tier access model, hard restrictions, encryption strategy, consent architecture, data retention policy, CCPA compliance |
| `docs/deployment-runbook.md` | Operational procedures, deploy steps, rollback, monitoring |
| `docs/mobile-app-architecture.md` | React Native app structure, navigation, Firebase integration |
| `docs/developer-setup.md` | Local development environment setup |
| `docs/architecture/archive/` | Original architecture docs (00-07) and comprehensive analysis, preserved for reference |
