# 04 — API Design

> Companion v1 API specification. Four API surfaces serve four consumer types
> with distinct authentication, authorization, and rate-limiting profiles.
> This document is intended to be machine-translatable to an OpenAPI 3.1 spec.

---

## 1. API Architecture Overview

All APIs are RESTful JSON over HTTPS. Authentication is handled by Firebase Auth
(JWT bearer tokens) for external surfaces, Google Cloud IAM service accounts
for the internal pipeline surface, and Firebase Auth (admin tenant) for the
admin surface. Every request returns a `request_id` for tracing.

- **App API** — serves Sam via mobile app. Full CRUD over user data.
- **Caregiver API** — serves trusted contacts. Read-only, tier-gated.
- **Pipeline API** — serves document processing jobs. Write-only, VPC-internal.
- **Admin API** — serves internal team via web dashboard. Config management, pipeline health, pilot metrics. Role-based access (viewer/editor/admin).

```
                        ┌──────────────────────────────────────────────┐
                        │              Cloud Run Backend               │
                        │                                              │
  ┌───────────┐         │  ┌────────────┐  ┌──────────┐  ┌─────────┐  │
  │  Sam's    │─────────┼─▶│  App API   │  │ Caregiver│  │Pipeline │  │
  │  Mobile   │  HTTPS  │  │ /api/v1/*  │  │   API    │  │   API   │  │
  │  App      │         │  │            │  │/api/v1/  │  │/api/v1/ │  │
  └───────────┘         │  │ Full CRUD  │  │caregiver/│  │pipeline/│  │
                        │  │ 100 req/m  │  │*         │  │*        │  │
  ┌───────────┐         │  └─────┬──────┘  │Read-only │  │Write-   │  │
  │ Caregiver │─────────┼───────────────▶  │Tier-gated│  │only     │  │
  │  Web /    │  HTTPS  │  │     │      │  │ 30 req/m │  │Internal │  │
  │  Mobile   │         │  │     │      │  └────┬─────┘  │500 req/m│  │
  └───────────┘         │  │     │      │       │        └────┬────┘  │
                        │  │     ▼      ▼       ▼             │       │
  ┌───────────┐         │  │  ┌──────────────────────────┐    │       │
  │ Document  │─────────┼──┼──│   Shared Service Layer   │◀───┘       │
  │ Processing│ internal│  │  │  (Firestore, Cloud SQL,  │            │
  │ Pipeline  │  gRPC/  │  │  │   Storage, Vertex AI)    │            │
  │ (Cloud    │  REST   │  │  └──────────────────────────┘            │
  │  Run Jobs)│         │  │                                          │
  └───────────┘         │  └──────────────────────────────────────────┘
```

**Base URLs**

| Surface      | Base URL                                  | Transport        |
|--------------|-------------------------------------------|------------------|
| App API      | `https://api.companion.app/api/v1`        | HTTPS (public)   |
| Caregiver API| `https://api.companion.app/api/v1/caregiver` | HTTPS (public)|
| Pipeline API | `https://pipeline.companion.internal/api/v1/pipeline` | HTTPS (VPC-internal) |
| Admin API    | `https://api.companion.app/api/v1/admin`              | HTTPS (same-domain)  |

---

## 2. Authentication & Authorization

### 2.1 Sam (App API)

| Property          | Value                                           |
|-------------------|-------------------------------------------------|
| Provider          | Firebase Auth                                   |
| Primary method    | Biometric (Face ID / fingerprint)               |
| Fallback          | 6-digit PIN                                     |
| Token lifetime    | 24 hours (refresh via Firebase SDK)             |
| New device        | Email/SMS verification required before first use|
| JWT claims        | `{ sub, role: "user", user_id }`                |

**Header format:**
```
Authorization: Bearer <firebase_id_token>
```

### 2.2 Caregiver (Caregiver API)

| Property          | Value                                           |
|-------------------|-------------------------------------------------|
| Provider          | Firebase Auth (separate project / tenant)        |
| Token lifetime    | 8 hours (Tier 1-2), session-scoped (Tier 3)    |
| JWT claims        | `{ sub, role: "caregiver", contact_id, user_id, tier: 1\|2\|3, scopes: [...] }` |

**Tier enforcement** is applied at the middleware layer. If a caregiver with
`tier: 1` requests `/api/v1/caregiver/dashboard`, the middleware returns:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": {
    "code": "TIER_INSUFFICIENT",
    "message": "Your access level does not include dashboard data. Contact Sam to request upgraded access.",
    "request_id": "req_abc123"
  }
}
```

All caregiver sessions are logged and visible to Sam via
`GET /api/v1/me/activity`.

### 2.3 Pipeline (Pipeline API)

| Property          | Value                                           |
|-------------------|-------------------------------------------------|
| Provider          | Google Cloud IAM service account                |
| Network           | VPC-internal only (not internet-routable)       |
| Access pattern    | Write-only for document processing results      |
| Auth header       | `Authorization: Bearer <gcloud_access_token>`   |

---

## 3. App API — Resource Design

All App API endpoints require `Authorization: Bearer <firebase_id_token>` with
`role: "user"`.

### 3.1 Users

#### `GET /api/v1/me`

Returns current user profile.

**Response `200 OK`:**
```json
{
  "data": {
    "user_id": "usr_abc123",
    "display_name": "Sam",
    "email": "sam@example.com",
    "avatar_url": "https://storage.companion.app/avatars/usr_abc123.jpg",
    "preferences": {
      "check_in_time": "08:00",
      "quiet_hours_start": "21:00",
      "quiet_hours_end": "07:00",
      "timezone": "America/Chicago",
      "voice_preference": "arlo_default"
    },
    "created_at": "2026-01-15T10:30:00Z"
  },
  "meta": {
    "request_id": "req_xyz789",
    "timestamp": "2026-03-27T14:22:00Z"
  }
}
```

#### `PATCH /api/v1/me`

Update profile fields and preferences.

**Request body:**
```json
{
  "display_name": "Sam",
  "preferences": {
    "check_in_time": "09:00",
    "quiet_hours_start": "22:00"
  }
}
```

**Response `200 OK`:** Returns the full updated user object (same shape as
`GET /api/v1/me`).

#### `GET /api/v1/me/memory`

Returns what the AI assistant knows about the user ("What do you know about
me?"). Used to give Sam transparency into stored context.

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "mem_001",
      "category": "preference",
      "content": "Prefers reminders 30 minutes before appointments",
      "source": "conversation",
      "created_at": "2026-02-10T11:00:00Z"
    },
    {
      "id": "mem_002",
      "category": "medical",
      "content": "Takes metformin with breakfast",
      "source": "document_extraction",
      "created_at": "2026-02-12T09:15:00Z"
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "per_page": 20,
    "has_more": false,
    "request_id": "req_mem001",
    "timestamp": "2026-03-27T14:22:00Z"
  }
}
```

#### `DELETE /api/v1/me/memory/:id`

Delete a specific memory entry. Returns `204 No Content`.

#### `DELETE /api/v1/me/memory?category=all`

Clear all memory. Pass `category=all` or a specific category
(`preference`, `medical`, `routine`, `social`). Returns `204 No Content`.

#### `GET /api/v1/me/activity`

Caregiver activity log — shows Sam who accessed their data, when, and what they
viewed.

**Query parameters:**

| Param       | Type   | Default | Description                        |
|-------------|--------|---------|------------------------------------|
| `page`      | int    | 1       | Page number                        |
| `per_page`  | int    | 20      | Items per page (max 100)           |
| `since`     | string | —       | ISO 8601 datetime filter           |
| `contact_id`| string | —       | Filter to specific caregiver       |

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "act_001",
      "contact_id": "ctc_mom",
      "contact_name": "Mom",
      "action": "viewed_dashboard",
      "timestamp": "2026-03-27T10:00:00Z",
      "ip_address": "192.168.1.x"
    }
  ],
  "meta": {
    "total": 1,
    "page": 1,
    "per_page": 20,
    "has_more": false,
    "request_id": "req_act001",
    "timestamp": "2026-03-27T14:22:00Z"
  }
}
```

---

### 3.2 Documents

#### `POST /api/v1/documents/scan`

Submit a camera scan. Accepts multipart form data with the image file and
optional metadata. The document enters the processing pipeline asynchronously.

**Request:** `Content-Type: multipart/form-data`

| Field          | Type   | Required | Description                          |
|----------------|--------|----------|--------------------------------------|
| `image`        | file   | yes      | JPEG/PNG/HEIC, max 10 MB            |
| `source`       | string | no       | `camera`, `gallery`, `share_sheet`   |
| `notes`        | string | no       | Sam's note about the document        |

**Response `202 Accepted`:**
```json
{
  "data": {
    "document_id": "doc_abc123",
    "status": "processing",
    "created_at": "2026-03-27T14:25:00Z"
  },
  "meta": {
    "request_id": "req_scan001",
    "timestamp": "2026-03-27T14:25:00Z"
  }
}
```

#### `GET /api/v1/documents`

List documents with optional filters.

**Query parameters:**

| Param            | Type   | Default    | Description                          |
|------------------|--------|------------|--------------------------------------|
| `status`         | string | —          | `processing`, `ready`, `acknowledged`, `handled` |
| `classification` | string | —          | `medical`, `bill`, `legal`, `insurance`, `other` |
| `urgency`        | string | —          | `urgent`, `soon`, `informational`    |
| `date_from`      | string | —          | ISO 8601 date                        |
| `date_to`        | string | —          | ISO 8601 date                        |
| `page`           | int    | 1          | Page number                          |
| `per_page`       | int    | 20         | Items per page (max 100)             |

**Response `200 OK`:**
```json
{
  "data": [
    {
      "document_id": "doc_abc123",
      "status": "ready",
      "classification": "bill",
      "urgency": "soon",
      "title": "Electric Bill - March 2026",
      "summary_short": "Electric bill for $142.50, due April 10",
      "created_at": "2026-03-27T14:25:00Z",
      "updated_at": "2026-03-27T14:26:30Z"
    }
  ],
  "meta": {
    "total": 1,
    "page": 1,
    "per_page": 20,
    "has_more": false,
    "request_id": "req_doclist001",
    "timestamp": "2026-03-27T14:30:00Z"
  }
}
```

#### `GET /api/v1/documents/:id`

Full document detail including AI-generated summary and extracted fields.

**Response `200 OK`:**
```json
{
  "data": {
    "document_id": "doc_abc123",
    "status": "ready",
    "classification": "bill",
    "urgency": "soon",
    "title": "Electric Bill - March 2026",
    "summary": "Your electric bill from City Power is $142.50. It's due on April 10, 2026. This is about the same as last month.",
    "extracted_fields": {
      "provider": "City Power",
      "amount": 142.50,
      "currency": "USD",
      "due_date": "2026-04-10",
      "account_number": "****4821"
    },
    "image_url": "https://storage.companion.app/documents/doc_abc123.jpg",
    "source": "camera",
    "notes": null,
    "routed_to": ["bills"],
    "questions": [
      {
        "question_id": "q_001",
        "text": "Do you want me to add this to your bills?",
        "status": "pending"
      }
    ],
    "created_at": "2026-03-27T14:25:00Z",
    "updated_at": "2026-03-27T14:26:30Z"
  },
  "meta": {
    "request_id": "req_docdet001",
    "timestamp": "2026-03-27T14:30:00Z"
  }
}
```

#### `PATCH /api/v1/documents/:id`

Update document status.

**Request body:**
```json
{
  "status": "acknowledged"
}
```

Valid status transitions: `ready` -> `acknowledged` -> `handled`.

**Response `200 OK`:** Returns updated document object.

#### `DELETE /api/v1/documents/:id`

Delete a document. Triggers a retention audit log entry before removal.

**Response `204 No Content`.**

---

### 3.3 Sections (Unified Views)

Sections are read-only composite views that aggregate data from multiple
resource types into the shapes the mobile app needs. They are not CRUD
resources — they are precomputed or query-time aggregations.

#### `GET /api/v1/sections/home`

Home section: recent mail, daily snapshot, supply reminders.

**Response `200 OK`:**
```json
{
  "data": {
    "greeting": "Good morning, Sam",
    "recent_mail": [
      {
        "document_id": "doc_abc123",
        "title": "Electric Bill - March 2026",
        "urgency": "soon",
        "summary_short": "Electric bill for $142.50, due April 10"
      }
    ],
    "daily_snapshot": {
      "medications_due": 2,
      "appointments_today": 1,
      "bills_due_soon": 1,
      "todos_active": 3
    },
    "supply_reminders": [
      {
        "item": "Metformin",
        "message": "You have about 5 days of Metformin left"
      }
    ]
  },
  "meta": {
    "request_id": "req_home001",
    "timestamp": "2026-03-27T08:00:00Z"
  }
}
```

#### `GET /api/v1/sections/health`

My Health: medications, upcoming appointments, pharmacy info.

**Response `200 OK`:**
```json
{
  "data": {
    "medications": [
      {
        "medication_id": "med_001",
        "name": "Metformin",
        "dosage": "500mg",
        "schedule": "daily with breakfast",
        "next_due": "2026-03-28T08:00:00Z",
        "confirmed_today": false
      }
    ],
    "appointments": [
      {
        "appointment_id": "apt_001",
        "title": "Dr. Chen — Annual checkup",
        "datetime": "2026-04-02T10:00:00Z",
        "location": "123 Medical Plaza",
        "travel_plan": null
      }
    ],
    "pharmacy": {
      "name": "Walgreens #4521",
      "phone": "+15551234567",
      "address": "456 Main St"
    }
  },
  "meta": {
    "request_id": "req_health001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

#### `GET /api/v1/sections/bills`

Bills I Need to Pay: outstanding bills, payment calendar, optional balance.

**Response `200 OK`:**
```json
{
  "data": {
    "outstanding": [
      {
        "bill_id": "bill_001",
        "title": "Electric Bill",
        "amount": 142.50,
        "currency": "USD",
        "due_date": "2026-04-10",
        "status": "unpaid",
        "source_document_id": "doc_abc123"
      }
    ],
    "calendar": [
      {
        "date": "2026-04-10",
        "bills": ["bill_001"]
      }
    ],
    "balance": {
      "available": true,
      "amount": 1250.00,
      "currency": "USD",
      "as_of": "2026-03-27T06:00:00Z",
      "source": "plaid"
    }
  },
  "meta": {
    "request_id": "req_bills001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

#### `GET /api/v1/sections/plans`

What's Coming Up: todos, errands, events.

**Response `200 OK`:**
```json
{
  "data": {
    "todos": [
      {
        "todo_id": "todo_001",
        "title": "Call dentist to reschedule",
        "priority": "normal",
        "due_date": "2026-03-28",
        "completed": false
      }
    ],
    "errands": [
      {
        "title": "Pick up prescription",
        "location": "Walgreens #4521",
        "suggested_date": "2026-03-28"
      }
    ],
    "events": [
      {
        "title": "Movie night with Alex",
        "datetime": "2026-03-29T19:00:00Z",
        "location": "AMC Theater"
      }
    ]
  },
  "meta": {
    "request_id": "req_plans001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

#### `GET /api/v1/sections/today`

Cross-section priority view used by the morning check-in flow.

**Response `200 OK`:**
```json
{
  "data": {
    "priorities": [
      {
        "type": "medication",
        "title": "Take Metformin with breakfast",
        "urgency": "now",
        "action_url": "/api/v1/medications/med_001/confirm"
      },
      {
        "type": "bill",
        "title": "Electric bill due in 14 days ($142.50)",
        "urgency": "soon",
        "action_url": "/api/v1/bills/bill_001"
      },
      {
        "type": "appointment",
        "title": "Dr. Chen on April 2 — want me to plan your trip?",
        "urgency": "upcoming",
        "action_url": "/api/v1/appointments/apt_001/travel"
      }
    ],
    "check_in_message": "Good morning, Sam! You have a pretty normal day. Let's start with your meds."
  },
  "meta": {
    "request_id": "req_today001",
    "timestamp": "2026-03-27T08:00:00Z"
  }
}
```

---

### 3.4 Medications

#### `GET /api/v1/medications`

**Query parameters:**

| Param    | Type   | Default | Description                |
|----------|--------|---------|----------------------------|
| `active` | bool   | true    | Filter by active status    |
| `page`   | int    | 1       | Page number                |
| `per_page`| int   | 20      | Items per page (max 100)   |

**Response `200 OK`:**
```json
{
  "data": [
    {
      "medication_id": "med_001",
      "name": "Metformin",
      "dosage": "500mg",
      "frequency": "daily",
      "schedule": "with breakfast",
      "prescriber": "Dr. Chen",
      "pharmacy": "Walgreens #4521",
      "refill_due": "2026-04-15",
      "active": true,
      "created_at": "2026-01-20T10:00:00Z"
    }
  ],
  "meta": { "total": 1, "page": 1, "per_page": 20, "has_more": false }
}
```

#### `POST /api/v1/medications`

**Request body:**
```json
{
  "name": "Metformin",
  "dosage": "500mg",
  "frequency": "daily",
  "schedule": "with breakfast",
  "prescriber": "Dr. Chen",
  "pharmacy": "Walgreens #4521",
  "refill_due": "2026-04-15"
}
```

**Response `201 Created`:** Returns created medication object.

#### `PATCH /api/v1/medications/:id`

Partial update. Any subset of fields from the `POST` body.

**Response `200 OK`:** Returns updated medication object.

#### `DELETE /api/v1/medications/:id`

Soft-delete (marks inactive, retains for history).

**Response `204 No Content`.

#### `POST /api/v1/medications/:id/confirm`

Confirm that a dose has been taken.

**Request body:**
```json
{
  "taken_at": "2026-03-27T08:15:00Z",
  "notes": "Took with orange juice"
}
```

`taken_at` is optional — defaults to server time.

**Response `201 Created`:**
```json
{
  "data": {
    "confirmation_id": "conf_001",
    "medication_id": "med_001",
    "taken_at": "2026-03-27T08:15:00Z",
    "notes": "Took with orange juice"
  },
  "meta": {
    "request_id": "req_conf001",
    "timestamp": "2026-03-27T08:15:00Z"
  }
}
```

#### `GET /api/v1/medications/:id/history`

**Query parameters:**

| Param      | Type   | Default | Description              |
|------------|--------|---------|--------------------------|
| `date_from`| string | —       | ISO 8601 date            |
| `date_to`  | string | —       | ISO 8601 date            |
| `page`     | int    | 1       | Page number              |
| `per_page` | int    | 20      | Items per page (max 100) |

**Response `200 OK`:** Paginated list of confirmation records.

---

### 3.5 Appointments

#### `GET /api/v1/appointments`

**Query parameters:**

| Param       | Type   | Default | Description              |
|-------------|--------|---------|--------------------------|
| `upcoming`  | bool   | true    | Only future appointments |
| `date_from` | string | —       | ISO 8601 date            |
| `date_to`   | string | —       | ISO 8601 date            |
| `page`      | int    | 1       | Page number              |
| `per_page`  | int    | 20      | Items per page (max 100) |

**Response `200 OK`:**
```json
{
  "data": [
    {
      "appointment_id": "apt_001",
      "title": "Dr. Chen — Annual checkup",
      "datetime": "2026-04-02T10:00:00Z",
      "duration_minutes": 60,
      "location": "123 Medical Plaza, Suite 200",
      "provider": "Dr. Chen",
      "notes": "Bring insurance card",
      "travel_plan": null,
      "reminder_sent": false,
      "source": "manual",
      "created_at": "2026-03-15T09:00:00Z"
    }
  ],
  "meta": { "total": 1, "page": 1, "per_page": 20, "has_more": false }
}
```

#### `POST /api/v1/appointments`

**Request body:**
```json
{
  "title": "Dr. Chen — Annual checkup",
  "datetime": "2026-04-02T10:00:00Z",
  "duration_minutes": 60,
  "location": "123 Medical Plaza, Suite 200",
  "provider": "Dr. Chen",
  "notes": "Bring insurance card"
}
```

**Response `201 Created`:** Returns created appointment object.

#### `PATCH /api/v1/appointments/:id`

Partial update. **Response `200 OK`.**

#### `DELETE /api/v1/appointments/:id`

**Response `204 No Content`.**

#### `POST /api/v1/appointments/:id/travel`

Request D.D. to generate a travel plan for this appointment.

**Request body (optional):**
```json
{
  "departure_from": "home",
  "mode": "transit"
}
```

`mode` options: `transit`, `rideshare`, `drive`, `walk`.

**Response `202 Accepted`:**
```json
{
  "data": {
    "travel_plan_id": "tp_001",
    "appointment_id": "apt_001",
    "status": "generating",
    "estimated_ready_seconds": 10
  },
  "meta": {
    "request_id": "req_travel001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

The travel plan is delivered via push notification or can be polled via
`GET /api/v1/appointments/:id` once ready.

---

### 3.6 Bills

#### `GET /api/v1/bills`

**Query parameters:**

| Param       | Type   | Default | Description                      |
|-------------|--------|---------|----------------------------------|
| `status`    | string | —       | `unpaid`, `paid`, `overdue`      |
| `due_from`  | string | —       | ISO 8601 date                    |
| `due_to`    | string | —       | ISO 8601 date                    |
| `page`      | int    | 1       | Page number                      |
| `per_page`  | int    | 20      | Items per page (max 100)         |

**Response `200 OK`:** Paginated list of bill objects.

```json
{
  "data": [
    {
      "bill_id": "bill_001",
      "title": "Electric Bill",
      "provider": "City Power",
      "amount": 142.50,
      "currency": "USD",
      "due_date": "2026-04-10",
      "status": "unpaid",
      "recurrence": "monthly",
      "source_document_id": "doc_abc123",
      "created_at": "2026-03-27T14:26:30Z"
    }
  ],
  "meta": { "total": 1, "page": 1, "per_page": 20, "has_more": false }
}
```

#### `POST /api/v1/bills`

**Request body:**
```json
{
  "title": "Internet",
  "provider": "Spectrum",
  "amount": 65.00,
  "currency": "USD",
  "due_date": "2026-04-15",
  "recurrence": "monthly"
}
```

**Response `201 Created`:** Returns created bill object.

#### `PATCH /api/v1/bills/:id`

Update bill status or amount. Common use: mark as `paid`.

**Request body:**
```json
{
  "status": "paid",
  "paid_date": "2026-04-08"
}
```

**Response `200 OK`:** Returns updated bill object.

#### `GET /api/v1/bills/summary`

Monthly summary with optional balance context.

**Query parameters:**

| Param   | Type   | Default       | Description              |
|---------|--------|---------------|--------------------------|
| `month` | string | current month | `YYYY-MM` format         |

**Response `200 OK`:**
```json
{
  "data": {
    "month": "2026-04",
    "total_due": 207.50,
    "total_paid": 0.00,
    "bills_count": 2,
    "paid_count": 0,
    "overdue_count": 0,
    "balance": {
      "available": true,
      "amount": 1250.00,
      "currency": "USD",
      "as_of": "2026-03-27T06:00:00Z",
      "source": "plaid"
    }
  },
  "meta": {
    "request_id": "req_billsum001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

---

### 3.7 Todos

#### `GET /api/v1/todos`

**Query parameters:**

| Param       | Type   | Default | Description                    |
|-------------|--------|---------|--------------------------------|
| `completed` | bool   | —       | Filter by completion           |
| `priority`  | string | —       | `high`, `normal`, `low`        |
| `page`      | int    | 1       | Page number                    |
| `per_page`  | int    | 20      | Items per page (max 100)       |

**Response `200 OK`:** Paginated list of todo objects.

```json
{
  "data": [
    {
      "todo_id": "todo_001",
      "title": "Call dentist to reschedule",
      "priority": "normal",
      "due_date": "2026-03-28",
      "completed": false,
      "completed_at": null,
      "source": "conversation",
      "created_at": "2026-03-26T16:00:00Z"
    }
  ],
  "meta": { "total": 1, "page": 1, "per_page": 20, "has_more": false }
}
```

#### `POST /api/v1/todos`

**Request body:**
```json
{
  "title": "Call dentist to reschedule",
  "priority": "normal",
  "due_date": "2026-03-28"
}
```

**Response `201 Created`:** Returns created todo object.

#### `PATCH /api/v1/todos/:id`

Partial update. **Response `200 OK`.**

#### `DELETE /api/v1/todos/:id`

**Response `204 No Content`.**

#### `POST /api/v1/todos/:id/complete`

Mark a todo as complete.

**Request body (optional):**
```json
{
  "completed_at": "2026-03-27T15:00:00Z"
}
```

**Response `200 OK`:** Returns updated todo object with `completed: true`.

---

### 3.8 Trusted Contacts

#### `GET /api/v1/contacts`

**Response `200 OK`:**
```json
{
  "data": [
    {
      "contact_id": "ctc_mom",
      "name": "Mom",
      "email": "mom@example.com",
      "tier": 2,
      "scopes": [],
      "status": "active",
      "last_active": "2026-03-27T10:00:00Z",
      "added_at": "2026-01-20T10:00:00Z"
    }
  ],
  "meta": { "total": 1, "page": 1, "per_page": 20, "has_more": false }
}
```

#### `POST /api/v1/contacts`

**Request body:**
```json
{
  "name": "Mom",
  "email": "mom@example.com",
  "tier": 2,
  "scopes": []
}
```

Triggers an invitation email to the contact. **Response `201 Created`.**

#### `PATCH /api/v1/contacts/:id`

Change tier, update scopes, or modify name.

**Request body:**
```json
{
  "tier": 3,
  "scopes": ["apt_001", "bill_001"]
}
```

**Response `200 OK`:** Returns updated contact object.

#### `DELETE /api/v1/contacts/:id`

Revoke all access immediately. Firebase caregiver token is invalidated server-side.

**Response `204 No Content`.**

#### `POST /api/v1/contacts/:id/pause`

Temporarily suspend a caregiver's access without revoking.

**Request body (optional):**
```json
{
  "reason": "Taking a break",
  "resume_at": "2026-04-01T00:00:00Z"
}
```

**Response `200 OK`:** Returns contact object with `status: "paused"`.

#### `POST /api/v1/contacts/:id/resume`

Re-enable a paused caregiver's access.

**Response `200 OK`:** Returns contact object with `status: "active"`.

#### `POST /api/v1/invitations`

Member invites a caregiver. Creates a TrustedContact (pending) and a stub user if needed. Sends invitation email with acceptance link.

**Request body:**
```json
{
  "email": "caregiver@example.com",
  "contact_name": "Jane Doe",
  "relationship_type": "family",
  "access_tier": "tier_1"
}
```

**Response `201 Created`:**
```json
{
  "contact_id": "uuid",
  "invitation_status": "pending",
  "email_sent": true
}
```

#### `GET /api/v1/invitations/validate?token={token}`

Public endpoint (no auth). Validates an invitation token and returns invitation details for the frontend landing page. Returns 404 if invalid or expired.

#### `POST /api/v1/invitations/accept`

Caregiver accepts an invitation. Requires Firebase auth. Activates the TrustedContact and upgrades stub user to active.

**Request body:** `{ "token": "abc123..." }`

#### `POST /api/v1/invitations/decline`

Caregiver declines an invitation. Same auth and body as accept.

#### `GET /api/v1/assignments/pending`

List pending caregiver assignment requests for the authenticated member.

#### `POST /api/v1/assignments/:id/approve`

Member approves a pending assignment request. Creates the TrustedContact. Returns 403 for managed accounts (they cannot reject, only approve is available via admin).

#### `POST /api/v1/assignments/:id/reject`

Member rejects a pending assignment request. Returns 403 for managed accounts.

---

### 3.9 Conversation

#### `POST /api/v1/conversation/start`

Start a new D.D. conversation session.

**Request body:**
```json
{
  "context": "morning_check_in",
  "input_mode": "voice"
}
```

`context` options: `morning_check_in`, `document_question`, `general`, `help`.
`input_mode` options: `voice`, `text`.

**Response `201 Created`:**
```json
{
  "data": {
    "session_id": "sess_abc123",
    "greeting": "Good morning, Sam! Ready for your check-in?",
    "audio_url": "https://storage.companion.app/audio/sess_abc123_greeting.mp3",
    "state": "active"
  },
  "meta": {
    "request_id": "req_conv001",
    "timestamp": "2026-03-27T08:00:00Z"
  }
}
```

#### `POST /api/v1/conversation/message`

Send a message to D.D. within an active session.

**Request (text):** `Content-Type: application/json`
```json
{
  "session_id": "sess_abc123",
  "type": "text",
  "content": "Did I get any mail today?"
}
```

**Request (audio):** `Content-Type: multipart/form-data`

| Field        | Type   | Required | Description                   |
|--------------|--------|----------|-------------------------------|
| `session_id` | string | yes      | Active session ID             |
| `type`       | string | yes      | `audio`                       |
| `audio`      | file   | yes      | WAV/M4A, max 60 seconds      |

**Response `200 OK`:**
```json
{
  "data": {
    "session_id": "sess_abc123",
    "response": "You got one piece of mail today — an electric bill from City Power for $142.50, due April 10. Want me to add it to your bills?",
    "audio_url": "https://storage.companion.app/audio/sess_abc123_resp_001.mp3",
    "actions": [
      {
        "type": "confirm",
        "label": "Yes, add to bills",
        "action_url": "/api/v1/bills",
        "method": "POST",
        "payload": {
          "title": "Electric Bill",
          "provider": "City Power",
          "amount": 142.50,
          "due_date": "2026-04-10"
        }
      },
      {
        "type": "dismiss",
        "label": "Not right now"
      }
    ],
    "state": "active"
  },
  "meta": {
    "request_id": "req_conv002",
    "timestamp": "2026-03-27T08:01:00Z"
  }
}
```

#### `GET /api/v1/conversation/state`

**Query parameters:**

| Param        | Type   | Required | Description     |
|--------------|--------|----------|-----------------|
| `session_id` | string | yes      | Active session  |

**Response `200 OK`:**
```json
{
  "data": {
    "session_id": "sess_abc123",
    "state": "active",
    "started_at": "2026-03-27T08:00:00Z",
    "message_count": 3,
    "context": "morning_check_in"
  }
}
```

#### `POST /api/v1/conversation/end`

**Request body:**
```json
{
  "session_id": "sess_abc123"
}
```

**Response `200 OK`:**
```json
{
  "data": {
    "session_id": "sess_abc123",
    "state": "ended",
    "duration_seconds": 180,
    "message_count": 5
  }
}
```

---

### 3.10 Notifications

#### `GET /api/v1/notifications`

**Query parameters:**

| Param      | Type   | Default | Description                         |
|------------|--------|---------|-------------------------------------|
| `status`   | string | —       | `unread`, `read`, `dismissed`       |
| `type`     | string | —       | `medication`, `bill`, `appointment`, `document`, `safety`, `system` |
| `page`     | int    | 1       | Page number                         |
| `per_page` | int    | 20      | Items per page (max 100)            |

**Response `200 OK`:** Paginated list of notification objects.

```json
{
  "data": [
    {
      "notification_id": "notif_001",
      "type": "medication",
      "title": "Time to take Metformin",
      "body": "It's 8:00 AM — take your Metformin with breakfast",
      "status": "unread",
      "action_url": "/api/v1/medications/med_001/confirm",
      "created_at": "2026-03-27T08:00:00Z"
    }
  ],
  "meta": { "total": 1, "page": 1, "per_page": 20, "has_more": false }
}
```

#### `PATCH /api/v1/notifications/:id`

**Request body:**
```json
{
  "status": "dismissed"
}
```

**Response `200 OK`:** Returns updated notification object.

#### `GET /api/v1/notifications/preferences`

**Response `200 OK`:**
```json
{
  "data": {
    "check_in_time": "08:00",
    "quiet_hours_start": "21:00",
    "quiet_hours_end": "07:00",
    "channels": {
      "medication_reminders": { "push": true, "in_app": true },
      "bill_reminders": { "push": true, "in_app": true },
      "appointment_reminders": { "push": true, "in_app": true },
      "document_ready": { "push": true, "in_app": true },
      "safety_alerts": { "push": true, "in_app": true },
      "caregiver_activity": { "push": false, "in_app": true }
    }
  },
  "meta": {
    "request_id": "req_notifpref001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

#### `PATCH /api/v1/notifications/preferences`

**Request body (partial update):**
```json
{
  "check_in_time": "09:00",
  "channels": {
    "caregiver_activity": { "push": true }
  }
}
```

**Response `200 OK`:** Returns full updated preferences object.

---

### 3.11 Integrations

#### `POST /api/v1/integrations/gmail/connect`

Initiate Gmail OAuth flow.

**Response `200 OK`:**
```json
{
  "data": {
    "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
    "state": "oauth_state_token"
  }
}
```

The client opens `auth_url` in a webview. On callback, the backend exchanges
the code and stores the refresh token.

#### `DELETE /api/v1/integrations/gmail`

Disconnect Gmail. Revokes stored tokens and stops mail ingestion.

**Response `204 No Content`.**

#### `POST /api/v1/integrations/plaid/connect`

Initiate Plaid Link session.

**Response `200 OK`:**
```json
{
  "data": {
    "link_token": "link-sandbox-abc123"
  }
}
```

The client uses the Plaid SDK with this `link_token`. On success, the client
sends the `public_token` back to the backend for exchange.

#### `DELETE /api/v1/integrations/plaid`

Disconnect Plaid. Revokes access token.

**Response `204 No Content`.**

#### `GET /api/v1/integrations/status`

**Response `200 OK`:**
```json
{
  "data": {
    "gmail": {
      "connected": true,
      "email": "sam@gmail.com",
      "last_sync": "2026-03-27T06:00:00Z"
    },
    "plaid": {
      "connected": true,
      "institution": "Chase",
      "last_sync": "2026-03-27T06:00:00Z"
    }
  },
  "meta": {
    "request_id": "req_intstatus001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

---

## 4. Caregiver API — Scoped Resources

All endpoints below require `Authorization: Bearer <caregiver_jwt>`.
The caregiver JWT contains `tier`, `contact_id`, `user_id`, and `scopes`.

Middleware enforces tier access. Requests beyond the caregiver's tier return
`403 TIER_INSUFFICIENT`.

**Path prefix:** `/api/v1/caregiver`

### 4.1 Tier 1 — Safety Alerts Only

Tier 1 caregivers receive only safety-critical information.

#### `GET /api/v1/caregiver/alerts`

**Response `200 OK`:**
```json
{
  "data": [
    {
      "alert_id": "alert_001",
      "type": "medication_missed",
      "severity": "high",
      "message": "Sam has not confirmed morning medication for 2 consecutive days",
      "created_at": "2026-03-27T12:00:00Z",
      "acknowledged": false
    }
  ],
  "meta": {
    "request_id": "req_cg_alert001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

**All other caregiver paths return `403` for Tier 1.**

### 4.2 Tier 2 — Read-Only Dashboard (includes Tier 1)

Tier 2 caregivers see summarized data only. No raw records, no detailed logs.

#### `GET /api/v1/caregiver/dashboard`

**Response `200 OK`:**
```json
{
  "data": {
    "summary": "Sam is managing well this week.",
    "generated_at": "2026-03-27T14:00:00Z",
    "sections": {
      "tasks": {
        "summary": "3 of 5 tasks completed today",
        "status": "on_track"
      },
      "bills": {
        "summary": "1 bill upcoming (Electric, due April 10)",
        "status": "handled"
      },
      "medications": {
        "adherence_percentage": 92,
        "summary": "Taking medications consistently"
      },
      "appointments": {
        "summary": "1 upcoming appointment (Dr. Chen, April 2)",
        "next": "2026-04-02T10:00:00Z"
      },
      "urgent_items": []
    }
  },
  "meta": {
    "request_id": "req_cg_dash001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

Note: The dashboard intentionally provides summaries, not raw data. A Tier 2
caregiver sees "92% medication adherence" but not a log of every dose.

### 4.3 Tier 3 — Scoped Collaboration (includes Tier 1 + 2)

Tier 3 caregivers have time-limited, item-specific access. Each scope is a
specific resource that Sam has shared with the caregiver.

#### `GET /api/v1/caregiver/collaboration/:scope_id`

View a specifically shared item. The `scope_id` must be present in the
caregiver's JWT `scopes` array.

**Response `200 OK`:**
```json
{
  "data": {
    "scope_id": "apt_001",
    "type": "appointment",
    "item": {
      "appointment_id": "apt_001",
      "title": "Dr. Chen — Annual checkup",
      "datetime": "2026-04-02T10:00:00Z",
      "location": "123 Medical Plaza, Suite 200",
      "notes": "Bring insurance card"
    },
    "comments": [
      {
        "comment_id": "cmt_001",
        "author": "Mom",
        "content": "I can drive you to this one!",
        "created_at": "2026-03-26T18:00:00Z"
      }
    ],
    "expires_at": "2026-04-03T00:00:00Z"
  },
  "meta": {
    "request_id": "req_cg_collab001",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

If the `scope_id` is not in the caregiver's scopes, or has expired:

```http
HTTP/1.1 403 Forbidden

{
  "error": {
    "code": "SCOPE_EXPIRED",
    "message": "This shared item is no longer available.",
    "request_id": "req_cg_collab002"
  }
}
```

#### `POST /api/v1/caregiver/collaboration/:scope_id/comment`

Add a comment to a shared item.

**Request body:**
```json
{
  "content": "I can drive you to this one!"
}
```

**Response `201 Created`:** Returns created comment object.

Comments are visible to Sam in the app and to other Tier 3 caregivers who share
the same scope.

---

## 5. Pipeline API — Internal Write

All endpoints below require a Google Cloud IAM service account token.
These endpoints are not exposed to the public internet. They are called by
the document processing pipeline running within the Cloud Run backend.

**Path prefix:** `/api/v1/pipeline`

#### `POST /api/v1/pipeline/documents/:id/classification`

Write the document classification result.

**Request body:**
```json
{
  "classification": "bill",
  "confidence": 0.94,
  "model_version": "classify-v2.1",
  "processing_ms": 1200
}
```

**Response `200 OK`.**

#### `POST /api/v1/pipeline/documents/:id/extraction`

Write extracted fields from the document.

**Request body:**
```json
{
  "fields": {
    "provider": "City Power",
    "amount": 142.50,
    "currency": "USD",
    "due_date": "2026-04-10",
    "account_number_masked": "****4821"
  },
  "raw_text": "...",
  "model_version": "extract-v1.3",
  "processing_ms": 3400
}
```

**Response `200 OK`.**

#### `POST /api/v1/pipeline/documents/:id/summary`

Write the plain-language summary.

**Request body:**
```json
{
  "summary": "Your electric bill from City Power is $142.50. It's due on April 10, 2026. This is about the same as last month.",
  "summary_short": "Electric bill for $142.50, due April 10",
  "reading_level": "grade_5",
  "model_version": "summarize-v1.2",
  "processing_ms": 2100
}
```

**Response `200 OK`.**

#### `POST /api/v1/pipeline/documents/:id/route`

Write the routing decision (which sections/resources this document maps to).

**Request body:**
```json
{
  "routes": [
    {
      "target": "bills",
      "action": "create",
      "confidence": 0.91
    }
  ],
  "model_version": "route-v1.0",
  "processing_ms": 800
}
```

**Response `200 OK`.**

#### `POST /api/v1/pipeline/documents/:id/status`

Update the document's processing status.

**Request body:**
```json
{
  "status": "ready",
  "stage": "complete",
  "error": null
}
```

Valid `status` values: `processing`, `ready`, `error`.
Valid `stage` values: `classification`, `extraction`, `summarization`,
`routing`, `complete`.

On `status: "error"`:
```json
{
  "status": "error",
  "stage": "extraction",
  "error": {
    "code": "EXTRACTION_FAILED",
    "message": "Could not extract structured fields from image",
    "retryable": true
  }
}
```

**Response `200 OK`.**

#### `POST /api/v1/pipeline/questions`

Create a tracked question that D.D. will ask Sam about a processed document.

**Request body:**
```json
{
  "document_id": "doc_abc123",
  "question": "Do you want me to add this electric bill to your bills?",
  "question_type": "yes_no",
  "suggested_action": {
    "on_yes": {
      "method": "POST",
      "url": "/api/v1/bills",
      "payload": {
        "title": "Electric Bill",
        "provider": "City Power",
        "amount": 142.50,
        "due_date": "2026-04-10",
        "source_document_id": "doc_abc123"
      }
    }
  },
  "priority": "normal"
}
```

**Response `201 Created`:**
```json
{
  "data": {
    "question_id": "q_001",
    "document_id": "doc_abc123",
    "status": "pending",
    "created_at": "2026-03-27T14:27:00Z"
  }
}
```

---

## 6. Admin API — Internal Operations

All endpoints prefixed with `/api/v1/admin`. Requires admin JWT (Firebase Auth, separate tenant). Not exposed publicly — accessible only from the web dashboard deployed on the same domain.

### Authentication

| Property | Value |
|---|---|
| Provider | Firebase Auth (admin tenant) |
| Roles | `viewer` (read-only), `editor` (config changes), `admin` (user management) |
| JWT claims | `{ sub, role: "admin", admin_role: "viewer\|editor\|admin", email }` |

### Config Management (requires: editor or admin)

```
GET    /api/v1/admin/config                          — list all active config entries (filterable by category)
GET    /api/v1/admin/config/:id                      — get config entry with version history
POST   /api/v1/admin/config                          — create config entry
PATCH  /api/v1/admin/config/:id                      — update config value (emits config.updated event)
GET    /api/v1/admin/config/:id/history               — audit log for specific config entry
GET    /api/v1/admin/config/audit                     — full config audit log (paginated)
```

#### Example: Update D.D. Persona Prompt

**Request:**
```
PATCH /api/v1/admin/config/dd-persona-base
```
```json
{
  "value": { "prompt": "You are D.D...." },
  "reason": "Adjusted tone per pilot feedback week 3"
}
```

**Response:**
```json
{
  "data": {
    "id": "uuid",
    "category": "dd_persona",
    "key": "dd-persona-base",
    "value": { "prompt": "You are D.D...." },
    "version": 4,
    "updated_by": "joe@companion.app",
    "updated_at": "2026-03-28T..."
  }
}
```

### Pipeline Health (requires: viewer or above)

```
GET    /api/v1/admin/pipeline/health                  — current pipeline status summary
GET    /api/v1/admin/pipeline/metrics                 — stage-level metrics (filterable by stage, time range)
GET    /api/v1/admin/pipeline/failures                — failed documents with error details (paginated)
GET    /api/v1/admin/pipeline/documents/:id/stages     — per-document stage history
```

#### Health Response Shape

```json
{
  "data": {
    "documents_in_flight": 3,
    "avg_processing_time_ms": 12400,
    "stages": {
      "ingestion":      { "success_rate": 0.99, "avg_ms": 1200, "in_progress": 1 },
      "classification": { "success_rate": 0.96, "avg_ms": 3400, "in_progress": 0 },
      "extraction":     { "success_rate": 0.94, "avg_ms": 2800, "in_progress": 1 },
      "summarization":  { "success_rate": 0.98, "avg_ms": 2200, "in_progress": 0 },
      "routing":        { "success_rate": 0.99, "avg_ms": 800,  "in_progress": 1 },
      "tracking":       { "success_rate": 1.00, "avg_ms": 200,  "in_progress": 0 }
    },
    "last_24h": {
      "total_processed": 142,
      "total_failed": 4,
      "avg_confidence": 0.87
    }
  }
}
```

### Escalation Monitor (requires: viewer or above)

```
GET    /api/v1/admin/escalations                      — open questions approaching thresholds
GET    /api/v1/admin/escalations/history               — escalation history (time range filter)
GET    /api/v1/admin/escalations/stats                 — escalation rate by type, avg time to resolution
```

### Pilot Metrics (requires: viewer or above)

```
GET    /api/v1/admin/metrics/engagement                — active users, session frequency, section usage
GET    /api/v1/admin/metrics/onboarding                — funnel: started → voice → question → first-win → complete
GET    /api/v1/admin/metrics/retention                  — 48h return, 7d, 30d retention cohorts
GET    /api/v1/admin/metrics/checkin                    — morning check-in acknowledgment rates
GET    /api/v1/admin/metrics/documents                  — classification distribution, confidence histogram
```

### Admin User Management (requires: admin)

```
GET    /api/v1/admin/users                             — list admin users
POST   /api/v1/admin/users                             — create admin user
PATCH  /api/v1/admin/users/:id                         — update admin role
DELETE /api/v1/admin/users/:id                         — deactivate admin user
```

### Admin Member/People Management (requires: editor or admin)

```
GET    /api/v1/admin/people                            — list all members (users)
GET    /api/v1/admin/people/:id                        — member detail
GET    /api/v1/admin/contacts                          — list all trusted contacts across members
GET    /api/v1/admin/conversations                     — list conversation sessions across members
GET    /api/v1/admin/documents                         — list documents across members
GET    /api/v1/admin/users-management                  — member account management (deactivation, deletion)
```

### Admin Workers Dashboard (requires: editor or admin)

Worker endpoints power the admin Workers page and allow manual triggering of background jobs.

```
GET    /api/v1/admin/workers                           — list all workers with status and last run time
POST   /api/v1/admin/workers/:name/trigger             — manually trigger a specific worker
```

### Internal Worker Endpoints (API-key auth, not public)

These endpoints are called by Cloud Scheduler HTTP targets and Pub/Sub push subscriptions. They run background jobs within the same Cloud Run backend process.

```
POST   /api/internal/workers/morning-trigger           — fire morning check-in for eligible users
POST   /api/internal/workers/medication-reminder       — send medication reminder push notifications
POST   /api/internal/workers/escalation-check          — check escalation thresholds
POST   /api/internal/workers/ttl-purge                 — purge expired data
POST   /api/internal/workers/retention                 — enforce data retention policies
POST   /api/internal/workers/away-monitor              — check away mode expirations
POST   /api/internal/workers/deletion                  — process scheduled account deletions
```

### App API — Additional Endpoint Groups

The following endpoint groups were added post-initial-design:

**Invitations** (`/api/v1/invitations`):
```
POST   /api/v1/invitations                            — member invites a caregiver
GET    /api/v1/invitations/validate?token={token}      — validate invitation token (public, no auth)
POST   /api/v1/invitations/accept                      — caregiver accepts invitation
POST   /api/v1/invitations/decline                     — caregiver declines invitation
```

**Assignments** (`/api/v1/assignments`):
```
GET    /api/v1/assignments/pending                     — list pending assignment requests for member
POST   /api/v1/assignments/:id/approve                 — member approves assignment
POST   /api/v1/assignments/:id/reject                  — member rejects assignment
```

**Pending Reviews** (`/api/v1/reviews`):
```
GET    /api/v1/reviews                                 — list pending document reviews for user
GET    /api/v1/reviews/:id                             — get review detail
POST   /api/v1/reviews/:id/confirm                     — confirm proposed record
POST   /api/v1/reviews/:id/reject                      — reject proposed record
```

**Device Tokens** (`/api/v1/device-tokens`):
```
POST   /api/v1/device-tokens                           — register FCM push token
DELETE /api/v1/device-tokens/:id                       — unregister token
```

**Conversations** (`/api/v1/conversation`):
Additional endpoints beyond start/message/end:
```
GET    /api/v1/conversation/sessions                   — list user's conversation sessions
```

---

## 7. Common Response Formats

### 7.1 Success — Single Resource

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_uuid",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

### 7.2 Success — Collection

```json
{
  "data": [ ... ],
  "meta": {
    "total": 42,
    "page": 1,
    "per_page": 20,
    "has_more": true,
    "request_id": "req_uuid",
    "timestamp": "2026-03-27T14:00:00Z"
  }
}
```

### 7.3 Error

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "We couldn't find that document. It may have been deleted.",
    "request_id": "req_uuid"
  }
}
```

### 7.4 Standard Error Codes

| HTTP Status | Code                    | Description                              |
|-------------|-------------------------|------------------------------------------|
| 400         | `VALIDATION_ERROR`      | Request body failed validation           |
| 401         | `AUTHENTICATION_REQUIRED` | Missing or invalid JWT                 |
| 403         | `TIER_INSUFFICIENT`     | Caregiver tier too low for this resource |
| 403         | `SCOPE_EXPIRED`         | Tier 3 scope has expired                 |
| 403         | `ACCESS_PAUSED`         | Caregiver access is paused by Sam        |
| 404         | `NOT_FOUND`             | Resource does not exist                  |
| 409         | `CONFLICT`              | Duplicate or invalid state transition    |
| 413         | `PAYLOAD_TOO_LARGE`     | Image exceeds 10 MB limit               |
| 429         | `RATE_LIMITED`           | Too many requests                        |
| 500         | `INTERNAL_ERROR`        | Server error (logged, alerted)           |
| 503         | `SERVICE_UNAVAILABLE`   | Temporary outage (retry with backoff)    |

---

## 8. Rate Limits

Rate limits are enforced per authenticated identity per surface.

| Surface              | Limit          | Window     | Scope           |
|----------------------|----------------|------------|-----------------|
| App API              | 100 requests   | per minute | per user        |
| Caregiver API        | 30 requests    | per minute | per caregiver   |
| Pipeline API         | 500 requests   | per minute | per service acct|
| Admin API            | 60 requests    | per minute | per admin user  |
| Conversation (audio) | 10 requests    | per minute | per user        |
| Document scan        | 5 requests     | per minute | per user        |

Rate-limited responses include headers:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 32
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1711548000
```

---

## 9. Versioning

The API is versioned via URL path (`/api/v1/`). Breaking changes will
increment the version. Non-breaking additions (new fields, new endpoints)
are added to the current version.

Deprecation policy: deprecated endpoints return a `Sunset` header and
continue to function for 6 months after the replacement is available.

---

## 10. Webhook Events (V2 — Planned)

V1 uses push notifications (Firebase Cloud Messaging) and in-app notifications
only. V2 will add outbound webhook support for agency and service provider
integrations.

**Planned webhook event types:**

| Event                          | Trigger                                    |
|--------------------------------|--------------------------------------------|
| `safety.alert.created`         | New safety alert generated                 |
| `document.processed`           | Document pipeline completed                |
| `medication.missed`            | Medication not confirmed within window     |
| `appointment.upcoming`         | Appointment within 24 hours                |
| `bill.overdue`                 | Bill past due date                         |

Webhook payloads will follow the same `{ data, meta }` envelope format.
Delivery will use HTTPS POST with HMAC-SHA256 signature verification.

---

## Appendix A: Quick Reference — All Endpoints

### App API (`/api/v1`)

| Method | Path                                   | Description                     |
|--------|----------------------------------------|---------------------------------|
| GET    | `/me`                                  | Current user profile            |
| PATCH  | `/me`                                  | Update profile/preferences      |
| GET    | `/me/memory`                           | List stored memories            |
| DELETE | `/me/memory/:id`                       | Delete specific memory          |
| DELETE | `/me/memory?category=all`              | Clear all memory                |
| GET    | `/me/activity`                         | Caregiver activity log          |
| POST   | `/me/deactivate`                       | Deactivate own account          |
| POST   | `/me/reactivate`                       | Reactivate own account          |
| POST   | `/me/request-deletion`                 | Request deletion (30-day grace) |
| POST   | `/me/cancel-deletion`                  | Cancel pending deletion         |
| POST   | `/documents/scan`                      | Submit camera scan              |
| GET    | `/documents`                           | List documents                  |
| GET    | `/documents/:id`                       | Document detail                 |
| PATCH  | `/documents/:id`                       | Update document status          |
| DELETE | `/documents/:id`                       | Delete document                 |
| GET    | `/sections/home`                       | Home section view               |
| GET    | `/sections/health`                     | Health section view             |
| GET    | `/sections/bills`                      | Bills section view              |
| GET    | `/sections/plans`                      | Plans section view              |
| GET    | `/sections/today`                      | Today priority view             |
| GET    | `/medications`                         | List medications                |
| POST   | `/medications`                         | Add medication                  |
| PATCH  | `/medications/:id`                     | Update medication               |
| DELETE | `/medications/:id`                     | Remove medication               |
| POST   | `/medications/:id/confirm`             | Confirm dose taken              |
| GET    | `/medications/:id/history`             | Dose confirmation history       |
| GET    | `/appointments`                        | List appointments               |
| POST   | `/appointments`                        | Add appointment                 |
| PATCH  | `/appointments/:id`                    | Update appointment              |
| DELETE | `/appointments/:id`                    | Remove appointment              |
| POST   | `/appointments/:id/travel`             | Request travel plan             |
| GET    | `/bills`                               | List bills                      |
| POST   | `/bills`                               | Add bill                        |
| PATCH  | `/bills/:id`                           | Update bill                     |
| GET    | `/bills/summary`                       | Monthly bill summary            |
| GET    | `/todos`                               | List todos                      |
| POST   | `/todos`                               | Add todo                        |
| PATCH  | `/todos/:id`                           | Update todo                     |
| DELETE | `/todos/:id`                           | Remove todo                     |
| POST   | `/todos/:id/complete`                  | Mark todo complete              |
| GET    | `/contacts`                            | List trusted contacts           |
| POST   | `/contacts`                            | Add trusted contact             |
| PATCH  | `/contacts/:id`                        | Update contact                  |
| DELETE | `/contacts/:id`                        | Remove contact                  |
| POST   | `/contacts/:id/pause`                  | Pause caregiver access          |
| POST   | `/contacts/:id/resume`                 | Resume caregiver access         |
| POST   | `/conversation/start`                  | Start D.D. session              |
| POST   | `/conversation/message`                | Send message to D.D.            |
| GET    | `/conversation/state`                  | Get conversation state          |
| POST   | `/conversation/end`                    | End session                     |
| GET    | `/notifications`                       | List notifications              |
| PATCH  | `/notifications/:id`                   | Dismiss/acknowledge             |
| GET    | `/notifications/preferences`           | Get notification preferences    |
| PATCH  | `/notifications/preferences`           | Update notification preferences |
| POST   | `/integrations/gmail/connect`          | Connect Gmail                   |
| DELETE | `/integrations/gmail`                  | Disconnect Gmail                |
| POST   | `/integrations/plaid/connect`          | Connect Plaid                   |
| DELETE | `/integrations/plaid`                  | Disconnect Plaid                |
| GET    | `/integrations/status`                 | Integration status              |

### Caregiver API (`/api/v1/caregiver`)

| Method | Path                                   | Tier | Description                |
|--------|----------------------------------------|------|----------------------------|
| GET    | `/alerts`                              | 1+   | Safety alerts              |
| GET    | `/dashboard`                           | 2+   | Summary dashboard          |
| GET    | `/collaboration/:scope_id`             | 3    | View shared item           |
| POST   | `/collaboration/:scope_id/comment`     | 3    | Comment on shared item     |

### Pipeline API (`/api/v1/pipeline`)

| Method | Path                                   | Description                     |
|--------|----------------------------------------|---------------------------------|
| POST   | `/documents/:id/classification`        | Write classification result     |
| POST   | `/documents/:id/extraction`            | Write extraction result         |
| POST   | `/documents/:id/summary`               | Write summarization result      |
| POST   | `/documents/:id/route`                 | Write routing decision          |
| POST   | `/documents/:id/status`                | Update processing status        |
| POST   | `/questions`                           | Create tracked question         |

### Admin API (`/api/v1/admin`)

| Method | Path                                   | Role     | Description                     |
|--------|----------------------------------------|----------|---------------------------------|
| GET    | `/config`                              | editor+  | List config entries             |
| GET    | `/config/:id`                          | editor+  | Get config entry with history   |
| POST   | `/config`                              | editor+  | Create config entry             |
| PATCH  | `/config/:id`                          | editor+  | Update config value             |
| GET    | `/config/:id/history`                  | editor+  | Config entry audit log          |
| GET    | `/config/audit`                        | editor+  | Full config audit log           |
| GET    | `/pipeline/health`                     | viewer+  | Pipeline status summary         |
| GET    | `/pipeline/metrics`                    | viewer+  | Stage-level metrics             |
| GET    | `/pipeline/failures`                   | viewer+  | Failed documents                |
| GET    | `/pipeline/documents/:id/stages`       | viewer+  | Per-document stage history      |
| GET    | `/escalations`                         | viewer+  | Open escalations                |
| GET    | `/escalations/history`                 | viewer+  | Escalation history              |
| GET    | `/escalations/stats`                   | viewer+  | Escalation statistics           |
| GET    | `/metrics/engagement`                  | viewer+  | User engagement metrics         |
| GET    | `/metrics/onboarding`                  | viewer+  | Onboarding funnel               |
| GET    | `/metrics/retention`                   | viewer+  | Retention cohorts               |
| GET    | `/metrics/checkin`                     | viewer+  | Check-in acknowledgment rates   |
| GET    | `/metrics/documents`                   | viewer+  | Document classification stats   |
| GET    | `/users`                               | admin    | List admin users                |
| POST   | `/users`                               | admin    | Create admin user               |
| PATCH  | `/users/:id`                           | admin    | Update admin role               |
| DELETE | `/users/:id`                           | admin    | Deactivate admin user           |
| POST   | `/people/:email/invite`                | editor+  | Invite to platform (Part 1)     |
| POST   | `/people/:email/caregiver`             | editor+  | Assign caregiver (respects care_model) |
| PATCH  | `/people/:email`                       | editor+  | Update person (incl. care_model)|
| POST   | `/companion-users/:id/deactivate`      | editor+  | Deactivate user account         |
| POST   | `/companion-users/:id/reactivate`      | editor+  | Reactivate user account         |
| POST   | `/companion-users/:id/request-deletion`| editor+  | Request deletion (30-day grace) |
| POST   | `/companion-users/:id/cancel-deletion` | editor+  | Cancel pending deletion         |
