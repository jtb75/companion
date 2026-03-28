# 03 — Document Intelligence Pipeline

Technical specification for the Document Intelligence Pipeline. This pipeline reads physical mail (via phone camera) and email (via Gmail API), normalizes both into a single processing path, and transforms raw documents into structured, actionable intelligence surfaced through the Arlo AI persona.

---

## 1. Pipeline Overview

Two input channels converge into one unified processing path of six stages. Processing is fully async. Arlo acknowledges receipt immediately ("Got it, I'm reading this now") and delivers results when the pipeline completes.

```
                         INGESTION
                             |
              +--------------+--------------+
              |                             |
        Camera Scan                      Email
        (phone camera)               (Gmail OAuth)
              |                             |
         Image Capture               Fetch + Filter
              |                             |
         Auto-Crop &                 HTML Strip &
         Enhance                     Attachment Extract
              |                             |
         OCR (Doc AI)               Pre-Filter Noise
              |                             |
              +----------- MERGE -----------+
                             |
                    Normalized Document
                      (common schema)
                             |
                    STAGE 2: CLASSIFY
                             |
                  +----------+----------+
                  |                     |
            Tier 1: Fast            Tier 2: LLM
            (rule-based)           (full classifier)
            conf > 0.95            conf <= 0.95
                  |                     |
                  +----------+----------+
                             |
                    STAGE 3: EXTRACT
                      structured data
                      per doc type
                             |
                    STAGE 4: SUMMARIZE
                      spoken + card
                             |
                    STAGE 5: ROUTE
                      section assignment
                      + action generation
                             |
                    STAGE 6: QUESTION TRACKER
                      log questions,
                      track responses,
                      escalation timers
                             |
                         DELIVERED
                        (to user via Arlo)
```

**Key invariants:**
- Every document that enters the pipeline exits the pipeline. Nothing is silently dropped.
- Arlo acknowledges receipt within 2 seconds of ingestion, before any classification.
- Every stage has a defined input schema and output schema. Stages are independently deployable.

---

## 2. Stage 1: Ingestion & Normalization

### 2.1 Camera Scan Input

**Trigger:** User taps "Scan Mail" in the Companion app.

**Processing steps:**

1. **Image capture** — Phone camera captures one or more images. Front-and-back scanning supported via sequential capture with an interstitial prompt ("Flip it over and scan the back").
2. **Auto-crop** — Edge detection crops the document from the background. Tuned for home lighting conditions (warm overhead, uneven, shadows from hands).
3. **Image enhancement** — Adaptive contrast, de-skew, noise reduction. Target: legible OCR input from a kitchen-table photo.
4. **OCR** — Google Document AI `processors.document` endpoint. Returns structured text blocks with bounding boxes.
5. **Quality assessment** — Score 0-1 based on OCR confidence aggregated across text blocks. Threshold: score < 0.6 triggers a re-scan prompt to the user.

**Input:**
```
CameraScanInput {
  images: Image[]          // 1-4 images (front, back, additional pages)
  capture_device: string   // device model for tuning enhancement
  captured_at: timestamp
}

Image {
  data: bytes
  dimensions: { width: int, height: int }
  orientation: int         // EXIF orientation
}
```

**Output:**
```
CameraScanOutput {
  raw_text: string
  metadata: {
    page_count: int
    dimensions: { width: int, height: int }[]
    quality_score: float   // 0-1, aggregated OCR confidence
    ocr_provider: "google_document_ai"
    ocr_model_version: string
    image_enhancements_applied: string[]
  }
}
```

### 2.2 Email Input

**Trigger:** Periodic poll (every 5 minutes) or push notification via Gmail API watch.

**Processing steps:**

1. **Fetch** — OAuth 2.0 connection, scope `gmail.readonly`. Fetch unread messages from inbox.
2. **Pre-filter** — Discard obvious noise BEFORE any LLM processing to control cost:
   - Gmail category: `promotions`, `social`, `forums` -> archive, skip pipeline
   - Sender on user's exclusion list -> archive, skip pipeline
   - Unsubscribe header present AND no dollar amounts in body -> archive, skip pipeline
3. **HTML strip** — Extract plain text from HTML body. Preserve table structures as delimited text.
4. **Attachment extraction** — Detect PDF/image attachments. PDFs run through the OCR sub-pipeline (same as camera scan, starting at step 4). Non-document attachments (images without text, .ics files) handled by type-specific handlers.

**Input:**
```
EmailInput {
  gmail_message_id: string
  thread_id: string
  from: string
  to: string
  subject: string
  date: timestamp
  body_html: string | null
  body_plain: string | null
  attachments: Attachment[]
  gmail_labels: string[]
  gmail_category: string   // primary, promotions, social, updates, forums
}

Attachment {
  filename: string
  mime_type: string
  size_bytes: int
  data: bytes
}
```

**Output:**
```
EmailOutput {
  raw_text: string           // combined body + attachment text
  metadata: {
    sender: string
    sender_domain: string
    subject: string
    date: timestamp
    has_attachments: bool
    attachment_count: int
    gmail_message_id: string
    thread_id: string
  }
}
```

**Sender exclusion list:**
- User-configurable via Settings > Mail > Blocked Senders.
- Stored as a list of email addresses and domains.
- Permanent until user removes. No auto-expiry.
- Arlo can suggest additions: "You've gotten 5 emails from retailer.com this month and ignored all of them. Want me to stop showing those?"

### 2.3 Normalized Document Schema

Both input channels produce a single `NormalizedDocument` for downstream stages.

```json
{
  "document_id": "uuid-v4",
  "user_id": "uuid-v4",
  "source_channel": "camera_scan | email",
  "raw_text": "string — full extracted text",
  "metadata": {
    "source_channel": "camera_scan | email",
    "ingested_at": "ISO-8601 timestamp",
    "quality_score": 0.87,
    "page_count": 1,
    "sender": "string | null",
    "sender_domain": "string | null",
    "subject": "string | null",
    "gmail_message_id": "string | null",
    "has_attachments": false,
    "ocr_provider": "string | null"
  },
  "ingested_at": "ISO-8601 timestamp",
  "quality_score": 0.87,
  "pipeline_status": "ingested",
  "pipeline_started_at": "ISO-8601 timestamp"
}
```

**At this point, Arlo acknowledges receipt.** The user sees a brief message ("Got it, I'm looking at this now") and a processing indicator. The pipeline continues async.

---

## 3. Stage 2: Classification

### 3.1 Contract

**Input:** `NormalizedDocument`

**Output:**
```json
{
  "document_id": "uuid",
  "classification": {
    "document_type": "bill | legal | government | medical | insurance | form | junk | personal | unknown",
    "urgency": "routine | needs_attention | act_today | urgent",
    "confidence": 0.94,
    "classifier_tier": "tier_1_rules | tier_2_llm",
    "classification_reasoning": "string — short explanation for debugging"
  },
  "classified_at": "ISO-8601 timestamp"
}
```

### 3.2 Tier 1 — Fast Pre-Filter

Rule-based classifier plus a lightweight model (distilled, runs on-device or edge). Handles the obvious cases cheaply.

**Rules engine checks (in order):**

| Rule | Condition | Classification | Urgency |
|------|-----------|---------------|---------|
| Known bill format | Sender domain in `known_billers` table AND amount pattern detected | `bill` | `needs_attention` |
| Known junk pattern | Sender domain in `known_junk` table OR coupon/promo keyword density > 40% | `junk` | `routine` |
| Government sender | Sender domain ends in `.gov` | `government` | `needs_attention` |
| Medical sender | Sender domain in `known_medical` table | `medical` | `needs_attention` |
| Legal keywords | Contains "court", "summons", "eviction", "collections", "lawsuit" | `legal` | `urgent` |

If the Tier 1 classifier produces confidence > 0.95, the result is accepted and processing skips to Stage 3.

If confidence <= 0.95, the full document is passed to Tier 2.

### 3.3 Tier 2 — Full LLM Classifier

Prompt-based classification using the primary LLM. Receives the full `raw_text` and metadata.

**LLM is instructed to return:**
- `document_type` (from the enum)
- `urgency` (from the enum)
- `confidence` (0-1)
- `reasoning` (1-2 sentences)

### 3.4 Classification Rules (Hard-Coded Overrides)

These rules apply AFTER both tiers and cannot be overridden by model output:

1. **Junk classification is conservative.** If the model classifies as `junk` with confidence < 0.90, reclassify as `unknown` with urgency `needs_attention`. A missed bill is catastrophic; surfacing junk is a minor annoyance.
2. **Unknown defaults to `needs_attention`.** Unknown documents are never silently archived. The user always sees them.
3. **Legal/collections/eviction is always `urgent`.** If the document contains keywords matching legal action (eviction, collections, court summons, lawsuit, garnishment), urgency is forced to `urgent` regardless of model confidence or classification tier.
4. **Government documents default to `needs_attention` minimum.** Never classified as `routine`.

---

## 4. Stage 3: Extraction

### 4.1 Contract

**Input:** `NormalizedDocument` + `ClassificationResult`

**Output:**
```json
{
  "document_id": "uuid",
  "document_type": "string — from classification",
  "extracted_data": { },
  "extraction_completeness": "complete | partial",
  "missing_fields": ["field_name_1", "field_name_2"],
  "questions_generated": [
    {
      "question_id": "uuid",
      "field": "due_date",
      "question_text": "I can see the amount but not the due date. Is there a due date on the back?",
      "priority": "high"
    }
  ],
  "extracted_at": "ISO-8601 timestamp"
}
```

### 4.2 Extraction Schemas by Document Type

#### Bill
```json
{
  "sender": "string — company name",
  "account_number_masked": "string — last 4 digits only, e.g. '**4821'",
  "amount_due": "decimal",
  "currency": "USD",
  "due_date": "ISO-8601 date",
  "minimum_payment": "decimal | null",
  "late_fee": "decimal | null",
  "payment_methods": ["online", "phone", "mail"],
  "payment_url": "string | null",
  "phone_number": "string | null",
  "billing_period": "string | null",
  "previous_balance": "decimal | null",
  "is_past_due": "bool"
}
```

#### Medical Appointment
```json
{
  "provider": "string — doctor or facility name",
  "date_time": "ISO-8601 datetime",
  "location": {
    "name": "string",
    "address": "string",
    "phone": "string | null"
  },
  "preparation_instructions": "string | null — e.g. 'fasting required'",
  "contact_number": "string",
  "appointment_type": "string | null — e.g. 'annual checkup'",
  "bring_items": ["string — e.g. 'insurance card', 'photo ID'"],
  "cancellation_policy": "string | null"
}
```

#### Legal
```json
{
  "sender": "string — law firm, court, or agency",
  "nature_of_notice": "string — e.g. 'debt collection', 'eviction notice', 'court summons'",
  "response_deadline": "ISO-8601 date | null",
  "required_action": "string — what the recipient must do",
  "case_number": "string | null",
  "amount_claimed": "decimal | null",
  "contact_info": {
    "name": "string | null",
    "phone": "string | null",
    "address": "string | null"
  }
}
```

#### Form
```json
{
  "title": "string — form title",
  "issuing_org": "string — organization that issued the form",
  "purpose": "string — plain language description of what this form is for",
  "submission_deadline": "ISO-8601 date | null",
  "submission_method": "string | null — e.g. 'mail to address', 'online portal'",
  "required_fields": ["string — list of fields the user needs to fill in"],
  "supporting_docs_needed": ["string — e.g. 'proof of income', 'photo ID'"],
  "reference_number": "string | null"
}
```

#### Government
```json
{
  "agency": "string — e.g. 'Social Security Administration'",
  "document_type": "string — e.g. 'benefit determination', 'recertification notice'",
  "action_required": "string | null",
  "deadline": "ISO-8601 date | null",
  "reference_number": "string | null",
  "contact_info": {
    "phone": "string | null",
    "office_address": "string | null",
    "website": "string | null"
  },
  "benefit_amount": "decimal | null",
  "effective_date": "ISO-8601 date | null"
}
```

#### Insurance
```json
{
  "provider": "string",
  "document_type": "string — e.g. 'EOB', 'premium notice', 'coverage change'",
  "policy_number_masked": "string — last 4 only",
  "amount_due": "decimal | null",
  "due_date": "ISO-8601 date | null",
  "coverage_details": "string | null",
  "action_required": "string | null"
}
```

### 4.3 Extraction Rules

1. **Never fabricate missing fields.** If a field cannot be extracted from the document text, set it to `null` and add it to `missing_fields`. Under no circumstances should the model infer, guess, or fill in data that is not explicitly present.
2. **Partial extraction is valid.** A document with 3 of 8 fields extracted is still useful. Surface what was found and flag what is missing.
3. **Generate questions for critical missing fields.** If `amount_due` or `due_date` is missing from a bill, generate a question for Stage 6 (e.g., "I can read who this is from but I can't make out the amount. Can you check the bill for me?").
4. **Field-level encryption for sensitive data.** Account numbers, SSN fragments, medical record numbers, and policy numbers are extracted but stored with field-level encryption (AES-256-GCM). These fields are decrypted only at render time and never logged in plaintext.

---

## 5. Stage 4: Summarization

### 5.1 Contract

**Input:** `NormalizedDocument` + `ClassificationResult` + `ExtractionResult`

**Output:**
```json
{
  "document_id": "uuid",
  "spoken_summary": "string — plain language, max 3 sentences",
  "card_summary": {
    "title": "string — document type + sender",
    "key_facts": [
      { "label": "string", "value": "string" }
    ],
    "urgency_label": "Today | Soon | Can Wait",
    "action_button_text": "string",
    "action_button_target": "string — deep link or action ID"
  },
  "summarized_at": "ISO-8601 timestamp"
}
```

### 5.2 Spoken Summary Rules

Target audience: adults with developmental disabilities. The summary is delivered via Arlo's TTS voice.

- **Reading level:** 4th-6th grade. Short sentences. Common words.
- **Structure:** What it IS, then what it MEANS, then what to DO.
- **Bills:** Lead with amount and due date in the first sentence. Always.
- **Legal:** Calm but honest. Do not minimize seriousness. Do not panic the user.
- **Junk:** Briefly dismissive. One sentence max.
- **Tone:** Direct, warm, no filler. Never say "please", "it appears that", "it seems like", "I wanted to let you know", or any bureaucratic hedging.
- **Max length:** 3 sentences for spoken delivery.

### 5.3 Card Summary Rules

Displayed on-screen alongside the spoken summary. Structured for quick scanning.

**Urgency label mapping** (internal 4-level to user-facing 3-level):

| Internal Urgency | User-Facing Label |
|-------------------|-------------------|
| `urgent` | **Today** |
| `act_today` | **Today** |
| `needs_attention` | **Soon** |
| `routine` | **Can Wait** |

### 5.4 Example Outputs

#### Bill — Electric Company

**Spoken summary:**
> "Your electric bill from City Power is $142.50, due March 15th. That's about normal for you. You can pay it online."

**Card summary:**
```
Title:        Electric Bill — City Power
Key Facts:    Amount: $142.50
              Due: March 15
              Status: Current
Urgency:      Soon
Action:       "Pay this bill" -> payment flow
```

#### Legal — Collections Notice

**Spoken summary:**
> "You got a letter from a collections company called Midland Credit about a $340 debt. This is serious and you might need help with it. I'd suggest talking to your support person about this one."

**Card summary:**
```
Title:        Collections Notice — Midland Credit
Key Facts:    Amount Claimed: $340.00
              Response By: April 2
              Type: Debt Collection
Urgency:      Today
Action:       "Get help with this" -> caregiver escalation
```

#### Medical Appointment

**Spoken summary:**
> "You have a doctor's appointment with Dr. Patel on Tuesday, March 18th at 10:30 AM. It's at the Riverside Clinic on Oak Street. Don't eat anything after midnight the night before."

**Card summary:**
```
Title:        Appointment — Dr. Patel
Key Facts:    Date: Tue, March 18 at 10:30 AM
              Location: Riverside Clinic, Oak St
              Prep: No food after midnight
Urgency:      Soon
Action:       "Add to calendar" -> calendar integration
```

#### Government — SSI Recertification

**Spoken summary:**
> "The Social Security office sent you a recertification form. You need to fill it out and send it back by April 30th. You'll need proof of your income and your living situation."

**Card summary:**
```
Title:        Recertification — Social Security
Key Facts:    Deadline: April 30
              Action: Complete and return form
              Docs Needed: Proof of income, housing
Urgency:      Soon
Action:       "Start this form" -> Forms Assistant
```

#### Junk — Retail Promotion

**Spoken summary:**
> "Just an ad from Target. Nothing you need to do."

**Card summary:**
```
(Archived — not displayed to user)
```

---

## 6. Stage 5: Routing & Action

### 6.1 Contract

**Input:** `ClassificationResult` + `ExtractionResult` + `SummarizationResult`

**Output:**
```json
{
  "document_id": "uuid",
  "primary_route": {
    "section": "string — app section ID",
    "display_priority": "int — sort order within section"
  },
  "secondary_route": {
    "section": "string | null",
    "integration": "string | null — e.g. 'calendar', 'reminder'"
  },
  "suggested_action": {
    "verb": "string",
    "object": "string",
    "reason": "string",
    "time_estimate": "string",
    "action_id": "string — links to action handler",
    "deep_link": "string | null"
  },
  "caregiver_escalation": "bool — whether to evaluate Tier 1 alert",
  "routed_at": "ISO-8601 timestamp"
}
```

### 6.2 Routing Table

| Document Type | Primary Route | Secondary Route |
|---------------|---------------|-----------------|
| Bill | Bills I Need to Pay | What's Coming Up (reminder at due_date - 3 days) |
| Medical Appointment | My Health | What's Coming Up (calendar entry) |
| Legal | Home (urgent flag) | Caregiver escalation evaluation |
| Government | Home | Relevant section based on content (e.g., benefits -> My Money) |
| Medical Document | My Health | -- |
| Insurance | My Health OR Bills (if premium/amount due) | -- |
| Form | Relevant section by issuing org | Forms Assistant activated |
| Junk | Archived | Not surfaced to user |
| Personal | Home | -- |
| Unknown | Home (needs_attention flag) | -- |

### 6.3 Action Generation Rules

1. **One action at a time.** Never present a list of actions. The user sees one clear next step.
2. **Action format:** verb + object + reason + time estimate.
3. **Time estimates are honest.** "Takes about 2 minutes online" is good. Don't say "quick" for something that requires a phone call.
4. **Actions are contextual.** If the user has previously paid this biller online, suggest online payment. If they always pay by phone, suggest phone.

**Action examples:**

| Scenario | Action Text |
|----------|-------------|
| Electric bill, due in 5 days | "Pay your electric bill -- it's due Friday. Takes about 2 minutes online." |
| Medical appointment in 3 days | "Confirm your appointment with Dr. Patel -- it's this Tuesday." |
| SSI form, due in 30 days | "Start filling out your SSI form -- it's due April 30th. I can help you through it." |
| Collections letter | "Talk to your support person about this collections letter. It's important." |
| Junk mail | (no action -- archived) |

---

## 7. Stage 6: Question & Response Tracker

### 7.1 Contract

**Input:** Questions generated by any pipeline stage OR any other Companion module.

**Output:**
```json
{
  "question_id": "uuid",
  "user_id": "uuid",
  "source": "string — pipeline stage or module that generated the question",
  "source_document_id": "uuid | null",
  "question_text": "string",
  "question_type": "routine_checkin | medication_confirmation | bill_action | incomplete_doc_routine | incomplete_doc_urgent | legal_acknowledgment | form_deadline | general",
  "asked_at": "ISO-8601 timestamp",
  "response": "string | null",
  "responded_at": "ISO-8601 timestamp | null",
  "status": "pending | answered | escalated | expired",
  "escalation_timer": {
    "escalation_threshold": "ISO-8601 timestamp | null",
    "escalated": false,
    "escalated_at": "ISO-8601 timestamp | null"
  }
}
```

### 7.2 Escalation Thresholds

Every unanswered question has an escalation timer. When the timer fires, a Tier 1 alert is sent to the designated caregiver or support contact.

| Question Type | Escalation Window | Trigger Condition |
|---------------|-------------------|-------------------|
| Routine check-in | No escalation | Never escalates |
| Medication confirmation | Per occurrence | 2 missed confirmations in a row -> Tier 1 alert |
| Bill action needed | Relative to due date | 5 days before due date -> Tier 1 alert |
| Incomplete document (routine) | 24 hours after asked | No response in 24h -> Tier 1 alert |
| Incomplete document (urgent) | 4 hours after asked | No response in 4h -> Tier 1 alert |
| Legal/eviction unacknowledged | 24 hours after surfaced | No acknowledgment in 24h -> Tier 1 alert |
| Form deadline approaching | Relative to deadline | 72 hours before deadline -> Tier 1 alert |

### 7.3 Tracker Rules

1. **Unified tracker.** All questions from all modules (pipeline, medication reminders, calendar, finances) flow through the same tracker. One table, one escalation engine.
2. **No duplicate questions.** If a question about the same document field is already pending, do not ask again. Nudge instead ("I still need to know the due date on that bill from earlier").
3. **Questions respect user context.** Do not ask questions while the user is clearly busy (e.g., in the middle of another flow). Queue and surface at the next natural break.
4. **Answered questions update extraction.** When the user answers a question about a missing field, the extraction result for that document is updated. The card summary and routing may change as a result.

---

## 8. Error Handling & Recovery

Every failure mode has a defined recovery path. The user should never see a dead end.

| Failure | Detection | Recovery | User-Facing Message |
|---------|-----------|----------|---------------------|
| OCR failure (unreadable image) | Quality score < 0.3 | Retry once with enhanced preprocessing (increased contrast, sharpen, de-noise). If still < 0.3, prompt re-scan. | "I'm having trouble reading that. Could you try scanning it again with more light?" |
| OCR partial failure | Quality score 0.3-0.6 | Process what was extracted. Flag low-confidence sections. Generate questions for unreadable parts. | "I got most of it but some parts were hard to read. Let me tell you what I found." |
| Classification low confidence | Confidence < 0.7 after both tiers | Surface with hedge language. Classify as `unknown`, urgency `needs_attention`. | "This looks like it might be [type]. Let me know if that's wrong." |
| Extraction partial | `extraction_completeness` = `partial` | Surface extracted fields. Generate questions for missing critical fields. | (Included naturally in summary: "I can see the amount but not the due date.") |
| Pipeline timeout | Stage exceeds 60s wall clock | Arlo acknowledges delay. Retry full pipeline async. Notify user on completion. | "This one's taking me a bit longer. I'll let you know when I've figured it out." |
| Gmail API rate limit | HTTP 429 response | Exponential backoff: 1s, 2s, 4s, 8s, 16s. Max 5 retries. Fall back to batch window (next 5-min poll). | (Silent -- user is not aware of polling schedule) |
| Gmail OAuth token expired | HTTP 401 response | Attempt silent token refresh. If refresh fails, prompt user to re-authorize. | "I need you to reconnect your email. It'll just take a sec." |
| Attachment too large | Attachment > 25MB | Skip attachment. Process email body only. Log skipped attachment. | "There was a big file attached that I couldn't read. The email itself says [summary]." |
| Duplicate document | Hash match on raw_text + sender + date | Deduplicate silently. Do not re-process. | (Silent) |

---

## 9. Performance Targets

| Metric | Target | Measurement Point |
|--------|--------|-------------------|
| Ingestion to acknowledgment | < 2 seconds | Time from scan/email arrival to Arlo's "Got it" message |
| Full pipeline completion (simple doc) | < 15 seconds | Junk, clear bills, known formats -- Tier 1 classification path |
| Full pipeline completion (complex doc) | < 45 seconds | Legal, multi-page, unknown type -- Tier 2 classification path |
| Email pre-filter throughput | 100 emails/minute per user | Tier 1 rule-based filter only (no LLM) |
| OCR accuracy (printed text) | > 98% character accuracy | Measured against Google Document AI benchmarks on home-scanned docs |
| OCR accuracy (handwritten text) | > 85% character accuracy | Best-effort; always flagged as lower confidence |
| Classification accuracy | > 92% | Measured as correct type + correct urgency on labeled test set |
| Extraction accuracy (critical fields) | > 95% | amount_due, due_date, deadline fields specifically |
| False negative rate (junk filter) | < 0.5% | Non-junk documents incorrectly classified as junk |

---

## Appendix A: Pipeline Status Enum

Every document carries a `pipeline_status` field updated as it progresses:

```
ingested -> classifying -> classified -> extracting -> extracted ->
summarizing -> summarized -> routing -> routed -> delivered
```

Failed states: `ocr_failed`, `classification_failed`, `extraction_failed`, `timeout`.

Any consumer can query a document's current status. The UI uses this to show progress indicators.

## Appendix B: Data Retention

| Data | Retention |
|------|-----------|
| Raw scanned images | 30 days, then deleted |
| Raw email text | 90 days, then deleted |
| Extracted structured data | Retained indefinitely (encrypted at rest) |
| Summaries | Retained indefinitely |
| Pipeline logs (debug) | 14 days |
| Question tracker history | Retained indefinitely |
