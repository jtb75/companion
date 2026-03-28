# System Architecture Overview

**Companion** — Independence Assistant for Adults with Developmental Disabilities

| | |
|---|---|
| **Status** | Draft |
| **Last Updated** | 2026-03-27 |
| **Audience** | Engineering team |

---

## 1. System Context

Companion is a mobile application that helps adults with developmental disabilities manage daily life tasks — bills, health information, mail, and upcoming events — with guidance from an AI persona named Arlo. The system ingests documents (physical mail via camera, email via Gmail), extracts structured data, and surfaces actionable items through a conversational interface tuned for plain language. A parallel caregiver surface provides scoped visibility without undermining the user's autonomy.

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MOBILE APP (React Native)                     │
│  ┌──────────┐ ┌────────────┐ ┌──────────────────┐ ┌────────────────┐  │
│  │   Home   │ │ My Health  │ │ Bills I Need to  │ │ What's Coming  │  │
│  │          │ │            │ │      Pay         │ │      Up        │  │
│  └──────────┘ └────────────┘ └──────────────────┘ └────────────────┘  │
│                    Picovoice Porcupine (wake word)                      │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ HTTPS / WSS
                             │
┌────────────────────────────────────────────────────────────────────────┐
│                        WEB DASHBOARD (React/Vite)                       │
│  ┌───────────────────┐  ┌───────────────┐  ┌────────────────────────┐ │
│  │ Caregiver Dashboard│  │ Ops Dashboard │  │     Config Admin      │ │
│  └─────────┬─────────┘  └───────┬───────┘  └───────────┬───────────┘ │
│            │ (Caregiver API)    │ (Admin API)           │ (Admin API) │
└────────────┼────────────────────┼───────────────────────┼─────────────┘
             │                    │                       │
             │        HTTPS       │                       │
             └────────┬───────────┴───────────────────────┘
                      │
                      ▼
                  ┌─────────────────────┐
                  │    API Gateway       │
                  │  (rate limit, auth)  │
                  └──┬───────┬───────┬──┘
                     │       │       │
          ┌──────────┘       │       └──────────┐
          ▼                  ▼                   ▼
  ┌──────────────┐  ┌──────────────┐   ┌──────────────────┐  ┌──────────────┐
  │   App API    │  │ Caregiver API│   │  Pipeline API    │  │  Admin API   │
  │              │  │              │   │                  │  │              │
  └──────┬───────┘  └──────┬───────┘   └────────┬─────────┘  └──────┬───────┘
         │                 │                     │                   │
         └────────┬────────┴─────────────────────┼───────────────────┘
                  ▼                              │
  ┌───────────────────────────────┐              │
  │       Unified Backend         │              │
  │  ┌────────────┐ ┌──────────┐ │              │
  │  │ PostgreSQL │ │  Redis   │ │              │
  │  └────────────┘ └──────────┘ │              │
  └───────────────┬───────────────┘              │
                  │                              │
                  ▼                              ▼
  ┌───────────────────────────────────────────────────────┐
  │              Event Bus (Google Cloud Pub/Sub)          │
  └───┬──────────┬──────────────┬──────────────┬──────────┘
      │          │              │              │
      ▼          ▼              ▼              ▼
┌──────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐
│ Document │ │Conversation│ │Notification│ │  Background  │
│Intelligence│ │   Layer   │ │  Engine    │ │   Worker     │
│ Pipeline │ │            │ │            │ │              │
└─────┬────┘ └─────┬──────┘ └────────────┘ └──────────────┘
      │             │
      ▼             ▼
┌─────────────────────────────────────────────────────────┐
│               External Integrations                      │
│                                                          │
│  Gmail API    Google Cloud TTS/STT    Google Document AI │
│  Plaid        Uber/Lyft APIs          Picovoice          │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| Primary DB | PostgreSQL 15+ | JSONB for semi-structured document data, row-level security for caregiver scoping, mature ecosystem |
| Cache / TTL Store | Redis 7+ | Session state, conversation context window, TTL-based expiry for sensitive data purges |
| Event Bus | Google Cloud Pub/Sub | Decouples pipeline from API surface, at-least-once delivery, dead-letter support, native GCP integration |
| Object Storage | Google Cloud Storage | Raw document images, audio recordings (temporary), pipeline artifacts |
| API Framework | **Decision pending** | *Option A: Node.js/Express* — team familiarity, large middleware ecosystem, straightforward WebSocket support for streaming TTS/STT. *Option B: Python FastAPI* — async-native, better ML/NLP library ecosystem, Pydantic validation. **Recommendation**: evaluate based on team composition. If team skews frontend-heavy, Node. If pipeline work dominates early sprints, Python. A split (Node for App/Caregiver API, Python for Pipeline API) is acceptable but adds operational cost. |
| Auth | Firebase Auth | Biometric/PIN support on mobile, anonymous-to-authenticated upgrade path, integrates with GCP IAM |
| Background Jobs | Cloud Scheduler + Cloud Functions | Cron-triggered jobs (morning check-in, TTL purge) without managing a scheduler process |
| OCR / Document AI | Google Document AI | Form parsing, entity extraction, handles poor-quality camera scans, pre-trained processors for invoices/receipts |
| TTS | Google Cloud TTS (WaveNet / Neural2) | Natural-sounding voice for Arlo persona, SSML support for pacing and emphasis, multiple voice options |
| STT | Google Cloud Speech-to-Text | Streaming recognition for real-time conversation, phrase hints for domain vocabulary (medication names, bill types) |
| Wake Word | Picovoice Porcupine | On-device processing (no audio sent until wake word detected), custom wake word ("Hey Arlo"), low power consumption |
| LLM | **Decision pending** | *Requirements*: (1) plain language output at 5th-grade reading level, (2) consistent Arlo persona across sessions, (3) guided action responses (not open-ended), (4) structured output for UI rendering. *Candidates*: Claude (strong instruction following, longer context window for conversation history) vs GPT-4 (function calling maturity, wider deployment precedent). **Evaluate on**: persona consistency over 100+ turns, cost per conversation, latency at P95, ability to refuse off-topic requests gracefully. |
| Mobile | React Native 0.73+ | Cross-platform from single codebase, accessibility APIs on both platforms, Expo for faster iteration |
| Web Dashboard | React (Vite) | Lightweight SPA, shared component library potential with React Native, Vite for fast builds. Three sub-apps under one deployment. |
| Monitoring | **To be selected** | Evaluate: Datadog, Google Cloud Operations Suite, Grafana Cloud. Must support structured log queries, distributed tracing, and custom SLO dashboards. |

---

## 3. Service Boundaries

### 3.1 App Service

Serves the React Native client. Owns authentication, session lifecycle, and API routing for the four app sections.

| | |
|---|---|
| **Inputs** | HTTP requests from mobile client (REST + WebSocket for streaming audio) |
| **Outputs** | JSON responses (section data, conversation payloads), WebSocket frames (TTS audio chunks) |
| **Subscribes to** | `document.processed`, `notification.ready`, `section.updated` |
| **Emits** | `user.action` (taps, confirmations), `conversation.started`, `document.uploaded` |

Responsibilities:
- Firebase Auth token validation and session management
- Biometric/PIN challenge orchestration
- Section data aggregation (Home, My Health, Bills, What's Coming Up)
- WebSocket lifecycle for streaming audio (TTS/STT relay)
- Request validation and rate limiting enforcement

### 3.2 Document Pipeline Service

Async document processing. Accepts raw inputs (camera images, email attachments) and produces structured, classified, section-routed data.

| | |
|---|---|
| **Inputs** | `document.uploaded` events (GCS object references), Gmail API webhook payloads |
| **Outputs** | Structured document records in PostgreSQL, extracted entities, GCS-stored originals |
| **Subscribes to** | `document.uploaded`, `email.received` |
| **Emits** | `document.processed`, `document.classification.failed`, `section.updated`, `notification.evaluate` |

6-stage pipeline:

```
Stage 1: Ingest         — normalize input (image/PDF/email), store raw in GCS
Stage 2: OCR/Extract    — Document AI processing, raw text extraction
Stage 3: Classify       — document type (bill, medical, appointment, general)
Stage 4: Parse          — type-specific entity extraction (due dates, amounts,
                          provider names, medication names, appointment times)
Stage 5: Route          — map to app section, link to existing records
Stage 6: Finalize       — write structured data, emit events, queue notifications
```

### 3.3 Conversation Service

Manages all Arlo interactions. Owns prompt assembly, conversation state, and LLM orchestration.

| | |
|---|---|
| **Inputs** | Transcribed user speech (from STT), tap-based selections from UI, scheduled triggers (morning check-in) |
| **Outputs** | LLM-generated responses (text + SSML for TTS), structured action payloads (e.g., "mark bill as paid") |
| **Subscribes to** | `conversation.started`, `user.action`, `checkin.trigger` |
| **Emits** | `conversation.completed`, `action.requested`, `question.logged` (feeds escalation tracker) |

Responsibilities:
- Arlo persona prompt management (system prompt, few-shot examples, guardrails)
- Conversation context window management (Redis-backed, sliding window)
- Multi-turn state tracking (e.g., bill payment confirmation flow)
- Plain-language response enforcement (reading level checks)
- Question logging for caregiver escalation tracking
- Action extraction and validation before execution

### 3.4 Notification Service

Evaluates, prioritizes, schedules, and delivers notifications. Respects user context (time of day, away mode, recent interactions).

| | |
|---|---|
| **Inputs** | `notification.evaluate` events from other services |
| **Outputs** | Push notifications, in-app banners, Arlo-spoken alerts, caregiver alerts |
| **Subscribes to** | `notification.evaluate`, `user.preference.updated`, `away_mode.changed` |
| **Emits** | `notification.delivered`, `notification.escalated`, `notification.suppressed` |

Responsibilities:
- Priority scoring (urgency x recency x section)
- Deduplication (same bill reminder within 24h window)
- Scheduling (respect quiet hours, batch low-priority items for morning check-in)
- Delivery channel selection (push vs. in-app vs. Arlo voice)
- Away mode suppression with caregiver forwarding
- Escalation handoff to Caregiver Service when thresholds are met

### 3.5 Caregiver Service

Enforces scoped access for caregivers. Provides dashboard data and alert delivery without exposing raw documents or full conversation history.

| | |
|---|---|
| **Inputs** | HTTP requests from caregiver web/mobile client, escalation events |
| **Subscribes to** | `notification.escalated`, `question.threshold.crossed`, `away_mode.changed` |
| **Emits** | `caregiver.acknowledged`, `caregiver.action` (e.g., "marked as handled") |

Responsibilities:
- Scoped JWT validation (caregiver sees only what permissions allow)
- Dashboard data aggregation (upcoming bills, health summary, calendar)
- Alert composition with minimum necessary context (no raw documents unless explicitly shared)
- Caregiver action relay (e.g., "I'll handle this bill" propagates back to user's view)
- Access audit logging (every caregiver data access is recorded)

### 3.6 Background Worker

Handles recurring maintenance, enforcement, and monitoring tasks that do not need to run in the request path.

| | |
|---|---|
| **Inputs** | Cloud Scheduler cron triggers, event-driven invocations |
| **Subscribes to** | `schedule.tick`, `retention.check` |
| **Emits** | `checkin.trigger`, `data.purged`, `escalation.check.completed`, `away_mode.alert` |

Responsibilities:
- TTL-based data purges (conversation logs, temporary audio files, expired cached data)
- Data retention policy enforcement (configurable per data type)
- Escalation threshold checks (aggregate unanswered question counts, trigger caregiver alerts)
- Away mode monitoring (if no user activity beyond threshold, notify caregiver)
- Morning check-in trigger assembly
- Stale document cleanup (pipeline failures older than N hours)

### 3.7 Admin Service

Serves the Ops Dashboard and Config Admin. Provides pipeline health visibility, pilot metrics, and system configuration management for the internal team.

| | |
|---|---|
| **Inputs** | HTTP requests from authenticated admin users (internal team only) |
| **Outputs** | Pipeline health metrics, user engagement aggregates, system configuration reads/writes |
| **Subscribes to** | `pipeline.stage.completed`, `pipeline.stage.failed`, `notification.delivered`, `notification.dismissed`, `checkin.morning.acknowledged` |
| **Emits** | `config.updated` (triggers reload in consuming services) |

Responsibilities:
- Pipeline health aggregation
- Pilot metrics computation
- system_config CRUD
- Config change audit logging
- Arlo prompt version management

---

## 4. Data Flow Diagrams

### 4.1 Document Processing Flow

```
    Physical Mail                         Email
         │                                  │
         ▼                                  ▼
  ┌──────────────┐                  ┌──────────────┐
  │ Camera Scan  │                  │  Gmail API   │
  │ (React Native│                  │  Webhook     │
  │  ImagePicker)│                  │              │
  └──────┬───────┘                  └──────┬───────┘
         │                                  │
         │     ┌──────────────────┐         │
         └────►│  GCS Raw Bucket  │◄────────┘
               └────────┬─────────┘
                        │
                        ▼
               emit: document.uploaded
                        │
                        ▼
               ┌────────────────┐
               │ Stage 1: Ingest│ ── normalize format, assign tracking ID
               └────────┬───────┘
                        ▼
               ┌────────────────┐
               │ Stage 2: OCR   │ ── Google Document AI
               └────────┬───────┘
                        ▼
               ┌─────────────────┐
               │ Stage 3: Classify│ ── bill / medical / appointment / other
               └────────┬────────┘
                        ▼
               ┌────────────────┐
               │ Stage 4: Parse │ ── extract due date, amount, provider, etc.
               └────────┬───────┘
                        ▼
               ┌────────────────┐
               │ Stage 5: Route │ ── map to section (Bills / Health / Calendar)
               └────────┬───────┘
                        ▼
               ┌──────────────────┐
               │ Stage 6: Finalize│ ── write to PostgreSQL
               └────────┬─────────┘
                        │
                ┌───────┼───────┐
                ▼       ▼       ▼
         emit:       emit:     emit:
     document.   section.   notification.
     processed   updated    evaluate
```

### 4.2 Morning Check-in Flow

```
  Cloud Scheduler (cron: 0 8 * * *)
         │
         ▼
  emit: checkin.trigger
         │
         ▼
  ┌──────────────────────────────────────────┐
  │         Priority Aggregation              │
  │                                           │
  │  Bills section ──► overdue? due today?    │
  │  Health section ──► medication reminders? │
  │  Calendar section ──► events today?       │
  │  Home section ──► unread documents?       │
  │                                           │
  │  Sort by urgency, cap at 3-5 items        │
  └──────────────────┬───────────────────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   Prompt Assembly    │
          │                      │
          │  System prompt (Arlo │
          │  persona + rules)    │
          │  + aggregated items  │
          │  + user history      │
          │  + time-of-day ctx   │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   LLM Generation     │ ── plain language, 5th-grade level
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   TTS Conversion     │ ── Google Cloud TTS (SSML)
          └──────────┬──────────┘
                     │
                     ▼
          Push notification: "Arlo has your morning update"
                     │
                     ▼
          ┌─────────────────────┐
          │   User Opens App     │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  Audio Playback +    │
          │  Visual Card Display │
          │                      │
          │  User can:           │
          │  - Tap to act        │
          │  - Voice respond     │
          │  - Dismiss           │
          └──────────┬──────────┘
                     │
                     ▼
          emit: user.action
                     │
              ┌──────┴──────┐
              ▼              ▼
        State updates    Conversation
        (mark seen,      continues if
         snooze,         user asks
         confirm)        follow-up
```

### 4.3 Caregiver Escalation Flow

```
  Conversation Service
         │
         ▼
  emit: question.logged
  (each time Sam asks a question Arlo can't resolve)
         │
         ▼
  ┌──────────────────────────────────┐
  │     Question Tracker (Redis)      │
  │                                   │
  │  key: user:{id}:unresolved_questions │
  │  - increment counter              │
  │  - store question summaries       │
  │  - track timestamps               │
  └──────────────┬───────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────┐
  │     Threshold Check               │
  │                                   │
  │  Tier 1: 2 similar questions     │
  │          within 48h              │
  │          → in-app flag only       │
  │                                   │
  │  Tier 2: 3+ questions OR         │
  │          bill/health urgency     │
  │          → caregiver push alert   │
  │                                   │
  │  Tier 3: question + missed       │
  │          action deadline          │
  │          → caregiver push +       │
  │            SMS/email              │
  └──────────────┬───────────────────┘
                 │
                 ▼
  emit: question.threshold.crossed (tier: N)
                 │
                 ▼
  ┌──────────────────────────────────┐
  │     Alert Composition             │
  │                                   │
  │  Principle: MINIMUM CONTEXT       │
  │                                   │
  │  Include:                         │
  │  - Category (bills, health, etc.) │
  │  - Number of unresolved questions │
  │  - Suggested action for caregiver │
  │                                   │
  │  Exclude:                         │
  │  - Raw conversation transcripts   │
  │  - Specific dollar amounts        │
  │    (unless permission granted)    │
  │  - Medical details                │
  │    (unless permission granted)    │
  └──────────────┬───────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────┐
  │     Delivery to Caregiver         │
  │                                   │
  │  Channel based on tier:           │
  │  Tier 1 → in-app badge           │
  │  Tier 2 → push notification       │
  │  Tier 3 → push + SMS + email      │
  └──────────────┬───────────────────┘
                 │
                 ▼
  emit: notification.escalated
                 │
                 ▼
  Caregiver acknowledges
                 │
                 ▼
  emit: caregiver.acknowledged
         │
         ▼
  Reset question counter
  Optionally: Arlo tells Sam
  "Your caregiver is looking into this"
```

---

## 5. Cross-Cutting Concerns

### 5.1 Authentication

| Actor | Method | Details |
|---|---|---|
| Sam (primary user) | Biometric + PIN | Firebase Auth with device biometric binding. PIN fallback (6-digit). Session token stored in secure enclave. Auto-lock after 5 min inactivity. |
| Caregiver | Scoped JWT | Firebase Auth with custom claims encoding permission scopes. Tokens include: `sections[]`, `actions[]`, `canViewAmounts`, `canViewMedical`. Short-lived (1h) with refresh. |
| Internal / Break-glass | Service account + audit | For support scenarios only. Requires two-person approval. Every access logged with reason field. Auto-expires after 30 min. |

### 5.2 Encryption

| Layer | Standard | Scope |
|---|---|---|
| At rest | AES-256 (GCM) | All PostgreSQL data, GCS objects, Redis RDB snapshots |
| In transit | TLS 1.3 | All API communication, WebSocket streams, inter-service calls |
| Field-level | AES-256 with per-user key | SSN fragments, bank account numbers, routing numbers. Decrypted only at point of use, never logged. |

Key management via Google Cloud KMS. Key rotation every 90 days. Per-user field-level keys derived from master key + user ID.

### 5.3 Observability

| Concern | Approach |
|---|---|
| Structured logging | JSON logs with correlation IDs. Every request tagged with `traceId`, `userId` (hashed), `service`, `section`. PII fields excluded from logs. |
| Distributed tracing | OpenTelemetry spans across all services. Trace pipeline: upload → OCR → classify → parse → route → finalize. |
| Error budgets | Per-service SLOs. Target: 99.5% success rate for App API, 99% for Pipeline (allows for OCR failures). Alert when burn rate exceeds 2x over 1h window. |
| Alerting | Page on: auth failures > 10/min, pipeline backlog > 100 items, escalation delivery failure. Warn on: P95 latency > 2s (API), > 30s (pipeline stage). |

### 5.4 Rate Limiting

| Surface | Limit | Rationale |
|---|---|---|
| App API (per user) | 120 req/min | Normal usage is ~20 req/min. 6x headroom for bursts. |
| Conversation API (per user) | 20 req/min | LLM calls are expensive. Prevents runaway loops. |
| Caregiver API (per user) | 60 req/min | Dashboard polling + actions. |
| Pipeline API (per user) | 10 uploads/min | Prevents accidental rapid-fire camera captures. |
| Gmail webhook (global) | 1000 req/min | Upstream rate limit alignment. |

Implemented at API Gateway layer. 429 responses include `Retry-After` header. Redis-backed sliding window counters.

### 5.5 Deployment

| Option | Pros | Cons |
|---|---|---|
| **Cloud Run** | Simpler ops, scale-to-zero, lower cost at low traffic, no cluster management | Cold start latency (mitigated with min instances), less control over networking, WebSocket support requires careful configuration |
| **GKE (Autopilot)** | Full Kubernetes ecosystem, better for WebSocket/streaming workloads, more mature service mesh options | Higher baseline cost, more operational overhead, overkill for V1 scale |

**V1 recommendation**: Cloud Run for all HTTP services. Evaluate GKE migration if WebSocket latency or scaling patterns require it post-launch.

All services containerized (Docker). CI/CD via Cloud Build. Environments: `dev`, `staging`, `prod`. Blue-green deploys for API services. Canary deploys for pipeline changes.

---

## 6. V1 Scope Boundaries

| Capability | V1 (Build) | V2+ (Deferred) |
|---|---|---|
| **Mail input** | Camera scan via app (phone camera) | Dedicated Mail Station hardware, auto-feed scanner |
| **Email integration** | Gmail only | Outlook, Yahoo, other providers |
| **Document types** | Bills, medical documents, appointment letters, general mail | Tax documents, legal documents, benefit statements with complex tables |
| **Agency enrollment** | Basic: single agency, manual setup by caregiver | Full agency account model, multi-agency, self-service onboarding |
| **User model** | Individual accounts (1 user : 1-3 caregivers) | Multi-client dashboards for professional caregivers / agency staff |
| **Bill payment** | Detection + reminders + "mark as paid" | In-app payment via Plaid, auto-pay setup |
| **Transportation** | Calendar-linked reminders ("you have a ride at 2pm") | In-app Uber/Lyft booking, ride status tracking |
| **Health tracking** | Medication reminders, appointment tracking, provider contact list | Vitals logging, pharmacy integration, telehealth links |
| **Conversation** | Structured flows (check-in, bill review, calendar review) | Open-ended conversation, multi-topic, proactive suggestions |
| **Arlo voice** | Pre-selected voice, fixed pacing | User-selectable voice, adjustable speed, emotion modulation |
| **Notifications** | Push + in-app + Arlo voice | SMS, email to user directly, smart speaker integration |
| **Caregiver access** | Web dashboard (Tier 1/2 views, responsive), push alerts | Native caregiver app, shared calendar editing, direct messaging |
| **Admin tooling** | Ops dashboard (pipeline health, escalation monitor, pilot metrics) + Config admin (Arlo prompts, thresholds, voice profiles) | Agency admin panel, multi-tenant config, A/B testing for prompts |
| **Offline support** | None (requires connectivity) | Cached section data, queued actions, offline voice playback |
| **Localization** | English only | Spanish, other languages (TTS/STT + LLM prompt localization) |
| **Monitoring** | Basic structured logging + alerting | Full observability stack, SLO dashboards, cost attribution |

### V1 Non-Goals

These are explicitly out of scope and should not influence V1 architecture decisions:

- Multi-tenancy / white-labeling for agencies
- HIPAA compliance certification (design for it, do not certify at V1)
- Real-time collaboration between caregiver and user
- Third-party developer API / integrations platform
- Data export / portability tooling
