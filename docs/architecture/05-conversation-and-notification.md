# 05 — Conversation Layer & Notification Engine

> Companion / Architecture Spec
> Status: Draft
> Last updated: 2026-03-27

---

## 1. Conversation Layer Overview

Five components collaborate to deliver Arlo's conversational interface. Each can be developed, tested, and swapped independently behind stable interfaces.

```
                          ┌──────────────────────┐
                          │   LLM Prompt Engine   │
                          │  (System Prompt Assy) │
                          └──────────┬───────────┘
                                     │
                                     ▼
┌──────────────┐    ┌──────────────────────────┐    ┌──────────────────┐
│  Wake Word   │───▶│  Conversation State Mgr   │───▶│  Voice Synthesis │
│  Detection   │    │  (session, tasks, memory) │    │  (TTS)           │
│ (Porcupine)  │    └──────────┬───────────────┘    └──────────────────┘
└──────────────┘               │
                               ▲
┌──────────────┐               │
│   Speech     │───────────────┘
│  Recognition │
│  (STT)       │
└──────────────┘
```

**Data flow for a single conversational turn:**

1. Wake Word Detection transitions state from `IDLE` to `LISTENING`.
2. STT streams audio to Google Cloud Speech-to-Text; transcript chunks arrive in real time.
3. Conversation State Manager appends the user turn, resolves memory refs, and assembles the full LLM prompt.
4. LLM Prompt Engine sends the assembled prompt to the model and streams tokens back.
5. Voice Synthesis converts streamed text to audio via Google Cloud TTS.
6. State transitions back to `IDLE` (or stays `LISTENING` if follow-up mode is active).

---

## 2. Voice Synthesis (TTS)

### 2.1 Provider

Google Cloud Text-to-Speech, using **WaveNet** and **Neural2** voice models. All audio is generated server-side and streamed to the client. Fallback: if Google Cloud TTS is unreachable for > 2 seconds, display text-only response with a banner explaining the voice is temporarily unavailable.

### 2.2 Voice Profiles

Four curated profiles. The user selects one during onboarding; it can be changed at any time in Settings.

```json
[
  {
    "voice_id": "warm",
    "label": "Warm",
    "description": "Friendly and gentle. Feels like a good friend.",
    "tts_config": {
      "voice_name": "en-US-Neural2-J",
      "pitch": 0.0,
      "speaking_rate": 0.92,
      "volume_gain_db": 0.0
    }
  },
  {
    "voice_id": "calm",
    "label": "Calm",
    "description": "Steady and reassuring. Even-keeled no matter what.",
    "tts_config": {
      "voice_name": "en-US-Neural2-D",
      "pitch": -1.0,
      "speaking_rate": 0.88,
      "volume_gain_db": 0.0
    }
  },
  {
    "voice_id": "bright",
    "label": "Bright",
    "description": "Upbeat and clear. Easy to follow along with.",
    "tts_config": {
      "voice_name": "en-US-WaveNet-F",
      "pitch": 1.5,
      "speaking_rate": 0.95,
      "volume_gain_db": 1.0
    }
  },
  {
    "voice_id": "clear",
    "label": "Clear",
    "description": "Direct and easy to hear. Gets right to the point.",
    "tts_config": {
      "voice_name": "en-US-Neural2-A",
      "pitch": 0.0,
      "speaking_rate": 0.90,
      "volume_gain_db": 2.0
    }
  }
]
```

**Schema — `VoiceProfile`:**

| Field | Type | Description |
|---|---|---|
| `voice_id` | `string` | Unique key (`warm`, `calm`, `bright`, `clear`) |
| `label` | `string` | User-facing name |
| `description` | `string` | Plain-language description shown during selection |
| `tts_config.voice_name` | `string` | Google Cloud TTS voice identifier |
| `tts_config.pitch` | `float` | Semitones adjustment (-20.0 to 20.0) |
| `tts_config.speaking_rate` | `float` | Base rate (0.25 to 4.0; 1.0 = default Google pace) |
| `tts_config.volume_gain_db` | `float` | Volume adjustment in dB (-96.0 to 16.0) |

### 2.3 Pace & Warmth Controls

**Pace** — user-adjustable multiplier applied to the profile's `speaking_rate`:

| Setting | Multiplier | Effective rate (Warm profile) |
|---|---|---|
| Slower | 0.80 | 0.736 |
| Default | 1.00 | 0.920 |
| Faster | 1.20 | 1.104 |

Stored as `user.preferences.tts_pace_multiplier` (float, range 0.8 - 1.2, default 1.0). The effective speaking rate sent to Google is always `profile.speaking_rate * pace_multiplier`.

**Warmth** — user-adjustable modifier that shifts pitch and rate slightly:

| Warmth Level | Pitch Offset | Rate Offset |
|---|---|---|
| Low | -0.5 | +0.02 |
| Medium (default) | 0.0 | 0.0 |
| High | +0.5 | -0.02 |

Stored as `user.preferences.tts_warmth` (`low` | `medium` | `high`).

### 2.4 SSML Markup

All responses sent to TTS are wrapped in SSML. The LLM output is post-processed before synthesis:

```xml
<speak>
  <prosody rate="0.92" pitch="+0st">
    Your rent payment of
    <emphasis level="moderate">
      <say-as interpret-as="currency">$850</say-as>
    </emphasis>
    is due on
    <emphasis level="moderate">
      <say-as interpret-as="date" format="mdy">04/01/2026</say-as>
    </emphasis>.
    <break time="600ms"/>
    Do you want to pay it now?
  </prosody>
</speak>
```

**SSML post-processing rules:**

| Pattern | SSML Treatment |
|---|---|
| Dollar amounts | `<say-as interpret-as="currency">` + `<emphasis level="moderate">` |
| Dates | `<say-as interpret-as="date">` + `<emphasis level="moderate">` |
| Proper names (people, providers) | `<emphasis level="moderate">` |
| Medication names | `<emphasis level="moderate">` + `<break time="200ms"/>` before |
| Sentence boundaries | `<break time="600ms"/>` (vs. default ~300ms) |
| Paragraph/topic shifts | `<break time="900ms"/>` |

The wider-than-default pauses between sentences are deliberate. They give Sam processing time without requiring explicit "slow mode."

---

## 3. Wake Word Detection

### 3.1 Provider

**Picovoice Porcupine** — on-device wake word engine. All audio processing happens locally. No audio data is transmitted to any server until the wake word fires and the user begins speaking.

**Wake word:** `"Hey Arlo"`

A custom Porcupine model is trained for this phrase. Sensitivity is set to `0.7` (range 0.0 - 1.0) by default, tunable per-device if false-positive/negative rates require adjustment.

### 3.2 Platform Behavior

| Platform | Default Mode | Wake Word Available | Notes |
|---|---|---|---|
| Mail Station (dedicated device) | Always-on listening | Yes, always active | Expected UX for a countertop device |
| Mobile app (iOS/Android) | Tap-to-talk | Opt-in via Settings | Battery and privacy considerations |

On mobile, enabling wake word requires explicit microphone background permission and displays a persistent notification indicating the mic is active.

### 3.3 Listening State Indicators

**Hard requirement:** The active listening state must ALWAYS be visible to the user. Sam must never wonder whether Arlo is listening.

| State | Mail Station Indicator | Mobile Indicator |
|---|---|---|
| `IDLE` | Soft ambient glow (device LED) | No indicator; mic icon shows "tap to talk" |
| `LISTENING` | Pulsing blue ring + on-screen "Listening..." | Pulsing mic icon + "Listening..." text |
| `PROCESSING` | Steady blue ring + on-screen "Thinking..." | Spinner + "Thinking..." text |
| `SPEAKING` | Green ring + audio waveform | Speaker icon + audio waveform + captions |

### 3.4 State Machine

```
         wake word / tap
  ┌─────────────────────────┐
  │                         ▼
IDLE ──────────────────► LISTENING
  ▲                         │
  │                         │ end of speech detected
  │                         ▼
  │                     PROCESSING
  │                         │
  │                         │ LLM response ready
  │                         ▼
  └─────────────────── SPEAKING
        audio complete
```

**Timeouts:**

| Transition | Timeout | Behavior |
|---|---|---|
| `LISTENING` with no speech | 8 seconds | Arlo says "I'm still here if you need me." Returns to `IDLE`. |
| `LISTENING` with partial speech then silence | 3 seconds | End-of-utterance detected, transition to `PROCESSING`. |
| `PROCESSING` exceeds limit | 10 seconds | Arlo says "Give me one more moment." Timer extends 10 seconds. If exceeded again, returns error and `IDLE`. |
| `SPEAKING` interrupted by wake word | Immediate | Stop audio playback, transition to `LISTENING`. (Barge-in support.) |

---

## 4. Speech Recognition (STT)

### 4.1 Provider

Google Cloud Speech-to-Text v2 API, streaming recognition mode.

### 4.2 Configuration

```json
{
  "config": {
    "model": "latest_long",
    "language_codes": ["en-US"],
    "features": {
      "enable_automatic_punctuation": true,
      "enable_word_time_offsets": true,
      "enable_word_confidence": true
    },
    "adaptation": {
      "phrase_sets": [
        {
          "name": "medications",
          "phrases": [],
          "boost": 15.0
        },
        {
          "name": "providers",
          "phrases": [],
          "boost": 12.0
        },
        {
          "name": "contacts",
          "phrases": [],
          "boost": 10.0
        }
      ]
    }
  },
  "streaming_config": {
    "interim_results": true
  }
}
```

**Phrase set population:** At session start, the backend loads the user's functional memory and populates `adaptation.phrase_sets` with:

- `medications` — all medication names from `user.medications[].name` (e.g., "Lexapro", "metformin")
- `providers` — all provider names from `user.providers[].name` (e.g., "Dr. Patel", "Dr. Wen")
- `contacts` — all trusted contact names from `user.contacts[].name`

Boost values are intentionally high because these terms are critical to accurate recognition and are drawn from verified user data.

### 4.3 Confidence Handling

| Confidence Score | Behavior |
|---|---|
| >= 0.80 | Accept transcript, proceed normally |
| 0.60 - 0.79 | Accept transcript but flag internally; if response seems off, Arlo confirms: "I heard [X]. Is that right?" |
| < 0.60 | Arlo says: "I didn't quite catch that. Could you say that again?" |

**Language rule (enforced in all STT-related responses):** Never say "I didn't understand you." Always say "I didn't quite catch that." The phrasing must always frame recognition failures as a limitation of the technology, never of the user.

### 4.4 Streaming Behavior

- Interim results are displayed as live captions on screen while the user speaks.
- Final results trigger the transition from `LISTENING` to `PROCESSING`.
- If streaming connection drops mid-utterance, buffer the last interim result and attempt reconnection once. If reconnection fails within 2 seconds, use the buffered interim as the final result (with low-confidence flag).

### 4.5 Text Input Fallback

Text input is always available as an alternative to voice:

- Mobile: text field visible below the conversation view at all times.
- Mail Station: on-screen keyboard accessible via a "Type instead" button.
- Text input bypasses STT entirely and feeds directly into the Conversation State Manager.
- No functional difference in Arlo's response between voice and text input.

---

## 5. Conversation State Manager

### 5.1 Session State Schema

```typescript
interface ConversationState {
  session_id: UUID;
  user_id: UUID;
  current_topic: string | null;
  conversation_history: Message[];       // rolling window, token-budget managed
  active_task: GuidedTask | null;        // current guided flow step
  task_stack: GuidedTask[];              // paused tasks (interruption support)
  pending_questions: Question[];         // unanswered Arlo questions
  memory_refs: MemoryRef[];             // active functional/contextual memory
  started_at: ISO8601Timestamp;
  last_activity: ISO8601Timestamp;
}

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: ISO8601Timestamp;
  token_count: number;                   // pre-computed for budget tracking
  metadata: {
    source: "voice" | "text";
    stt_confidence?: number;             // voice-only
    compressed: boolean;                 // true if this is a summary of older turns
  };
}

interface GuidedTask {
  task_id: UUID;
  task_type: "forms_assistant" | "travel_assistant" | "medication_setup";
  current_step: number;
  total_steps: number;
  step_data: Record<string, any>;        // task-specific state
  paused_at?: ISO8601Timestamp;
}

interface Question {
  question_id: UUID;
  text: string;
  context: string;                       // why Arlo asked this
  asked_at: ISO8601Timestamp;
  answered: boolean;
}

interface MemoryRef {
  ref_type: "medication" | "provider" | "bill" | "contact" | "preference";
  ref_id: UUID;
  label: string;                         // human-readable, e.g., "Lexapro 10mg"
  loaded_at: ISO8601Timestamp;
}
```

### 5.2 Token Budget Management

The conversation history operates within a **dynamic rolling window**. The system does not use a fixed turn count. Instead, it manages a token budget derived from the model's context limit minus the space required for the system prompt and response generation.

**Budget allocation:**

| Component | Token Allocation |
|---|---|
| System prompt (persona + memory + context + alerts + constraints) | Measured at session start; typically 1,500 - 3,000 tokens |
| Reserved for model response | 1,024 tokens |
| Conversation history | Remainder of context window |

**Compression protocol:**

When conversation history reaches 80% of its allocated budget:

1. Identify the oldest N turns that would free 30% of the budget if removed.
2. Send those turns to a secondary LLM call with the prompt: "Summarize this conversation segment. Preserve: all decisions made, user preferences expressed, any commitments or follow-ups mentioned, and the current topic trajectory."
3. Replace the N oldest turns with a single `Message` where `metadata.compressed = true`.
4. Continue the conversation with the compressed history seamlessly.

**What compression preserves:**

- Decisions Sam made ("I'll pay that bill tomorrow")
- Preferences Sam expressed ("I don't like morning appointments")
- Active context (what Arlo and Sam are currently discussing)
- Any pending follow-ups or unanswered questions

**What compression discards:**

- Filler turns ("Okay", "Got it")
- Repeated confirmations
- Intermediate guided-flow steps that are already recorded in `GuidedTask.step_data`

**Target:** Maintain full coherence across conversations lasting up to 30 minutes. In practice, this means 40-60 turns before first compression, and the ability to sustain another 30-40 turns after each compression cycle.

### 5.3 Interruption Handling

Guided flows (Forms Assistant, Travel Assistant, Medication Setup) support full interruption and resumption via the task stack.

**Flow:**

```
Sam is on step 4 of a 7-step form.
Sam: "Hey Arlo, what time is my appointment tomorrow?"
  → active_task (form, step 4) is pushed onto task_stack
  → Arlo answers the appointment question
  → Arlo: "Want to keep going with the form?"
    → Sam says yes: pop task_stack, restore form at step 4
    → Sam says no: task saved to DB, resumable later via "Arlo, let's finish that form"
    → Sam says nothing (8s timeout): task saved, Arlo says "No worries. We can finish the form whenever you're ready."
```

**Stack rules:**

| Rule | Detail |
|---|---|
| Max stack depth | 3 tasks. If a 4th interruption occurs, Arlo says: "We have a few things going. Let's finish [current] first, then come back to the rest." |
| Stack persistence | Tasks remain on the stack for the duration of the session. If the session ends, all stacked tasks are saved to the database with their current step. |
| Resumption prompt | When a session starts and saved tasks exist: "Last time we were working on [task]. Want to pick up where we left off?" |
| Task expiration | Saved tasks expire after 7 days. After expiration, data is archived but the flow must restart if resumed. |

### 5.4 Session Lifecycle

| Event | Behavior |
|---|---|
| Session start | Generate `session_id`. Load functional memory into `memory_refs`. Load active alerts. Check for saved tasks. |
| Inactivity (5 min, mid-conversation) | Arlo: "I'm still here if you need anything." |
| Inactivity (15 min) | Session ends gracefully. State serialized to DB. |
| App backgrounded (mobile) | Session paused. Resumes on foreground if < 15 min elapsed. |
| Explicit close | "See you later, Sam." State serialized. |

---

## 6. LLM Prompt Architecture

This is the most important engineering surface in the product. Arlo's behavior, tone, boundaries, and capabilities are defined entirely by how the system prompt is assembled.

### 6.1 Component Assembly

The system prompt is dynamically assembled from five components at the start of each session and refreshed when context changes mid-session (e.g., a new alert arrives).

```
System Prompt = [
  1. Arlo Persona Definition        // FIXED  — never changes between deploys
  2. Sam's Functional Memory         // DYNAMIC — loaded from backend at session start
  3. Session Context                 // DYNAMIC — trigger, section, recent docs
  4. Active Alerts & Pending Items   // DYNAMIC — cross-section priority items
  5. Conversation Constraints        // FIXED  — language rules, behavioral rules
]
```

Each component is separated by a clear delimiter in the prompt so that updates to one do not destabilize others:

```
===== ARLO PERSONA =====
[component 1]

===== SAM'S INFORMATION =====
[component 2]

===== SESSION CONTEXT =====
[component 3]

===== ACTIVE ALERTS =====
[component 4]

===== RULES =====
[component 5]
```

### 6.2 Component 1: Arlo Persona Definition (Fixed)

```
You are Arlo, Sam's personal assistant in the Companion app. You help Sam manage
daily life — bills, medications, appointments, mail, and travel.

YOUR COMMUNICATION STYLE:
- Use plain language. Aim for a 4th to 6th grade reading level.
- Present one thing at a time. Never give Sam multiple decisions at once.
- Be warm but never patronizing. Sam is an adult. Respect that always.
- Stay calm, especially when things are hard. If a bill is overdue or a letter
  is confusing, be steady and clear. Never convey alarm.
- Be specific, never vague. Say "Your Xfinity bill of $89.50 is due Friday"
  not "You have a bill coming up."
- Celebrate accomplishments simply. Say "Done. That's handled." or "Nice, that's
  taken care of." Do not say "Great job!" or "Amazing work!" — be genuine, not
  performative.
- Never rush Sam. Do not create time pressure unless a deadline is genuinely
  imminent (less than 24 hours).
- When you are confident about information, state it plainly. When you are not
  sure, say so: "I'm not sure about that. Want me to check?" Never guess.

YOUR EMOTIONAL BOUNDARIES:
- Be warm and present. You care about Sam's day going well.
- Never pretend to be human. If Sam asks, be honest: "I'm Arlo, your assistant
  in the Companion app."
- Encourage Sam's capability. Frame things as Sam's accomplishments, not yours.
  "You got that done" not "I helped you do that."
- Never foster dependency. If Sam can do something independently, encourage it.
  Offer help only when it adds genuine value.
- If Sam is upset, acknowledge it simply: "That sounds frustrating." Do not
  over-empathize or try to fix feelings. Be present, then offer a concrete
  next step if there is one.
```

This block is version-controlled and deployed as part of the application config. Changes require product and clinical review.

### 6.3 Component 2: Sam's Functional Memory (Dynamic)

Loaded from the backend at session start. Structured as a prompt-friendly block:

```
SAM'S INFORMATION (loaded at session start — treat as ground truth):

Name: Sam Rivera
Preferred name: Sam

MEDICATIONS:
- Lexapro 10mg — every morning
- Metformin 500mg — with breakfast and dinner
- Vitamin D 2000 IU — every morning

PROVIDERS:
- Dr. Patel (primary care) — Valley Health Clinic, next appointment April 14
- Dr. Wen (psychiatrist) — Behavioral Health Associates, next appointment April 28

BILLS:
- Rent: $850/month, due 1st, payee: Oakwood Apartments, auto-pay: NO
- Xfinity: ~$89/month, due 15th, auto-pay: YES
- T-Mobile: $45/month, due 22nd, auto-pay: YES

TRUSTED CONTACTS:
- Maria (sister) — Tier 1 access
- James (case manager) — Tier 1 access
- Coach Devon — Tier 2 access

PREFERENCES:
- Voice: Warm
- Pace: Default
- Warmth: Medium
- Morning check-in: 8:30 AM
- Quiet hours: 10:00 PM – 8:00 AM
```

This block is refreshed at session start and when the user modifies any data mid-session. It is never cached across sessions.

### 6.4 Component 3: Session Context (Dynamic)

Describes what triggered the current session so Arlo can open appropriately:

```
SESSION CONTEXT:
- Trigger: morning_check_in
- Current time: Tuesday, April 1, 2026, 8:30 AM
- Current section: Home (dashboard)
- Recent documents: Electric bill (arrived March 30, processed, $67.20, due April 18)
```

**Trigger values and expected Arlo opening behavior:**

| Trigger | Arlo Opens With |
|---|---|
| `user_initiated` | "Hey, Sam. What's up?" |
| `morning_check_in` | Morning check-in flow (see Section 7) |
| `document_arrived` | "A new piece of mail came in. It's [description]. Want to take a look?" |
| `notification_tapped` | Context-specific: "About your [item]..." |
| `guided_flow_resumed` | "Let's pick up where we left off with [task]. You were on step [N]." |

### 6.5 Component 4: Active Alerts (Dynamic)

```
ACTIVE ALERTS (mention proactively when relevant):
- [LEVEL 1] Rent ($850) due tomorrow, April 1. Not on auto-pay. Sam has not acknowledged.
- [LEVEL 2] Dr. Patel appointment in 2 weeks (April 14). No action needed yet.
- [LEVEL 3] Vitamin D refill — pharmacy shows 5 days remaining.
```

Sorted by urgency level. Arlo integrates these naturally into conversation rather than reading them as a list. For example, if Sam asks "What do I need to do today?", Arlo starts with the Level 1 item.

### 6.6 Component 5: Conversation Constraints (Fixed)

```
RULES YOU MUST FOLLOW:
1. RESPONSE LENGTH: When responding by voice, use a maximum of 3 sentences. When
   responding by text, use a maximum of 5 sentences. If more detail is needed,
   offer it: "Want me to tell you more about that?"
2. NEXT ACTION: Always end with one clear next action or question. Never leave
   Sam without a path forward.
3. OPTIONS: Never present more than 3 options. If there are more, curate the
   top 3 and say "There are a few more if none of these work."
4. HONESTY: If you do not have information, say "I don't have that information
   right now." Never fabricate details — especially dollar amounts, dates, or
   provider names.
5. SCOPE: You help with bills, medications, appointments, mail, and daily
   logistics. If Sam asks about something outside your scope, say so kindly:
   "That's not something I can help with, but [trusted contact] might be a
   good person to ask."
6. CONFIRMATION: Before taking any action that involves money, sending a
   message, or changing a schedule, always confirm with Sam first.
7. ONE AT A TIME: Present one piece of information or one decision at a time.
   Wait for Sam's response before moving to the next item.
```

### 6.7 Guided Flow Sub-Prompts

When a guided flow is active, an additional prompt block is injected between Component 4 (Alerts) and Component 5 (Constraints):

**Forms Assistant:**

```
ACTIVE GUIDED FLOW: Forms Assistant
Form: Medicaid Renewal (DHS Form 1171)
Total fields: 12
Completed: 5
Current field: "Monthly income" (field 6 of 12)
Pre-filled value: $1,240 (from last submission, March 2025)
Instruction: Ask Sam to confirm or update this value. If Sam is unsure, suggest
they check with James (case manager).
Fields remaining: Monthly income, Employer, Housing cost, Medical expenses,
Other income, Assets, Signature
```

**Travel Assistant:**

```
ACTIVE GUIDED FLOW: Travel Assistant
Destination: Valley Health Clinic (1200 Oak Street)
Mode: Bus (Route 15)
Departure constraint: Appointment at 2:00 PM, estimated travel time 35 min
Current step: Confirming departure time
Suggested departure: 1:10 PM (includes 15 min buffer)
Next step: Walking directions to bus stop (0.3 miles, ~7 min walk)
```

**Medication Setup:**

```
ACTIVE GUIDED FLOW: Medication Setup
Action: Adding new medication
Medication: Lisinopril 10mg
Schedule being configured: Once daily, morning
Confirmation pending: Time (suggested 8:00 AM with existing morning meds)
Next step: Confirm time, then set reminder preferences
```

Each guided flow sub-prompt is discarded when the flow completes or is explicitly abandoned. If the flow is paused (pushed to the task stack), the sub-prompt is removed from the active system prompt and restored when the task is popped.

---

## 7. Notification Engine

### 7.1 Priority Model

Four internal priority levels drive all notification delivery, timing, and escalation behavior.

| Level | Label | Examples | Delivery | Escalation |
|---|---|---|---|---|
| 1 | **Urgent** | Legal notices, eviction threats, collections letters, any item unacknowledged past its escalation threshold | Breaks quiet hours. Immediate delivery. Distinct alert sound. | Tracker activated from first delivery. |
| 2 | **Act Today** | Bills due < 48 hours, appointments tomorrow, missed medication today | Active hours only. Included in morning check-in + 1 standalone notification. | End-of-day follow-up if unacknowledged. |
| 3 | **Needs Attention** | Bills due < 7 days, upcoming appointments this week, prescription refill reminders | Active hours only. Included in morning check-in. 1 follow-up during the day. | None. |
| 4 | **Routine** | Supply reminders, weekly check-ins, memory review prompts | Morning check-in or in-app card only. | None. |

**Level assignment** is rule-based, defined by item type and temporal proximity. The rules engine evaluates every item nightly and on item creation/update:

```typescript
function assignLevel(item: NotificationItem): PriorityLevel {
  if (item.category === "legal" || item.category === "eviction" || item.category === "collections") {
    return 1;
  }
  if (item.escalated) {
    return 1; // any item past its escalation threshold promotes to Level 1
  }
  if (item.type === "bill" && item.due_date && hoursUntil(item.due_date) < 48) {
    return 2;
  }
  if (item.type === "appointment" && hoursUntil(item.datetime) < 36) {
    return 2;
  }
  if (item.type === "medication" && item.missed_today) {
    return 2;
  }
  if (item.type === "bill" && item.due_date && daysUntil(item.due_date) < 7) {
    return 3;
  }
  if (item.type === "appointment" && daysUntil(item.datetime) < 7) {
    return 3;
  }
  if (item.type === "medication" && item.refill_days_remaining < 7) {
    return 3;
  }
  return 4;
}
```

### 7.2 Morning Check-In

The single most important notification. Delivered daily at the user's configured time (stored as `user.preferences.morning_checkin_time`, default `08:00`).

**Structure (max 90 seconds spoken):**

```
1. GREETING
   "Good morning, Sam. It's Tuesday."

2. MOST IMPORTANT THING (only if Level 1 or Level 2 items exist)
   "First — your rent is due tomorrow. That's $850 to Oakwood Apartments.
    It's not on auto-pay, so you'll need to send it. Want to do that now?"

3. TODAY
   Appointments, medications, errands happening today.
   "You also have Dr. Patel at 2:00 this afternoon."

4. THIS WEEK (next 7 days)
   Upcoming bills, appointments, deadlines.
   "Later this week, your Xfinity bill comes out on the 15th. That one's
    on auto-pay, so nothing to do there."

5. CLOSE
   "That's everything for now. I'm here if you need me."
```

**Batching rule:** When multiple Level 2 items exist, Arlo groups them:

```
"You have 3 things that need attention today. Let's go through them one at a time."
[Presents item 1, waits for acknowledgment]
[Presents item 2, waits for acknowledgment]
[Presents item 3, waits for acknowledgment]
```

Each item is presented individually. Arlo waits for an acknowledgment (verbal "okay", "got it", "next", or tap) before proceeding to the next item.

**Assembly logic:**

```typescript
async function assembleMorningCheckIn(userId: UUID): Promise<CheckInScript> {
  const now = new Date();
  const alerts = await getActiveAlerts(userId);
  const today = alerts.filter(a => isToday(a.relevant_date));
  const thisWeek = alerts.filter(a => isWithinDays(a.relevant_date, 7) && !isToday(a.relevant_date));

  const level1and2 = alerts.filter(a => a.level <= 2);
  const todayItems = today.filter(a => a.level > 2);
  const weekItems = thisWeek.filter(a => a.level >= 3);

  return {
    greeting: buildGreeting(now),
    urgent: level1and2.map(formatAlertForSpeech),       // section 2
    today: todayItems.map(formatAlertForSpeech),         // section 3
    this_week: weekItems.slice(0, 5).map(formatAlertForSpeech),  // section 4, cap at 5
    close: "That's everything for now. I'm here if you need me.",
    estimated_duration_seconds: estimateDuration(level1and2, todayItems, weekItems),
  };
}
```

**Performance target:** Morning check-in assembly must complete in < 2 seconds (see Section 9).

### 7.3 Delivery Rules

**One at a time.** Notifications are never delivered simultaneously. If multiple notifications are pending, they enter a FIFO queue sorted by priority level (Level 1 first). Each notification is delivered, and the next is held until the previous is acknowledged or 60 seconds elapse.

**Quiet hours.** Default 9:00 PM to 8:00 AM (configurable via `user.preferences.quiet_hours_start` and `user.preferences.quiet_hours_end`). During quiet hours:

| Level | Behavior |
|---|---|
| 1 (Urgent) | Delivered immediately. Distinct alert sound. Prefixed with: "Sorry to bother you late — this is important." |
| 2-4 | Queued. Delivered at quiet hours end or next morning check-in, whichever comes first. |

**Context sensitivity.** Non-urgent notifications are deferred when:

- Sam is mid-conversation with Arlo (active session, last turn < 2 minutes ago)
- Sam is in a guided flow (Forms, Travel, Medication)
- A Level 1 notification is currently being presented

Deferred notifications are delivered after the current interaction ends or during the next natural break.

**Diminishing repetition.** If a notification is delivered and not acknowledged:

| Attempt | Timing | Action |
|---|---|---|
| 1st delivery | Scheduled time | Normal delivery |
| 2nd delivery (Level 1-2 only) | 4 hours later or end of day | "Just a reminder — [item]" |
| 3rd delivery | None as standalone | Rolls into next morning check-in |

After the 2nd standalone delivery, the item is not delivered again as a standalone notification. It appears in morning check-ins until acknowledged or resolved. Arlo never nags.

### 7.4 Notification Channels

| Channel | When Used | Format |
|---|---|---|
| **Voice (Arlo speaks)** | App is open and active | Full conversational delivery with SSML |
| **Push notification** | App is in background | Plain language, max 2 sentences. Calm tone. No urgency theater. |
| **In-app card** | Always | Persistent record in the notification center. Reviewable anytime. Shows item, status, and actions. |
| **Caregiver alert** | Escalations only | Sent to Tier 1 contacts only. Contains: category, urgency label, and days since last acknowledgment. Never contains dollar amounts, document contents, or medical details. |

**Push notification examples:**

- Level 2: "Your rent is due tomorrow. Tap to take care of it."
- Level 3: "You have an appointment with Dr. Patel on Monday. Tap for details."
- Level 4 items never generate push notifications.

### 7.5 User-Facing Urgency Labels

The internal 4-level model is simplified to 3 user-facing labels. Sam never sees "Level 1" or "Priority 2."

| Internal Level | User-Facing Label | Color | Icon |
|---|---|---|---|
| Level 1 + Level 2 | **Today** | Amber | Clock |
| Level 3 | **Soon** | Blue | Calendar |
| Level 4 | **Can Wait** | Gray | Info circle |

These labels appear on in-app notification cards and are used in Arlo's speech: "This is a 'today' item" or "This can wait — no rush."

---

## 8. Silence & Safety Protocol

Arlo monitors engagement patterns and responds to prolonged silence with a graduated escalation model. The core principle: Sam is always in control. Arlo asks before escalating. Sam is never bypassed except at the extreme end of the Away mode threshold.

### 8.1 Engagement Monitoring

| Scenario | Arlo Response |
|---|---|
| Misses a single morning check-in | No action. Try one more check-in 2 hours later. This is normal. |
| No interaction for 2 days | Warm check-in: "I haven't heard from you in a couple of days. Everything okay? No rush — just checking in." |
| No response to any check-in for 12 hours after the 2-day message | Notify Tier 1 trusted contact(s). Message is calm and factual: "Sam hasn't responded to check-ins for about 3 days. You may want to check in." |
| Away mode set by Sam | All silence-based alerts suppressed. Arlo asks for expected duration. Auto-expires after the stated duration. |
| Away mode active 7+ days with no check-in | Tier 1 alert: "Sam set away status 7 days ago and hasn't checked in since. You may want to reach out." |

### 8.2 Away Mode

```typescript
interface AwayMode {
  active: boolean;
  set_at: ISO8601Timestamp;
  expected_return: ISO8601Timestamp | null;  // null = indefinite
  reason?: string;                           // optional, Sam's words
  auto_expire: boolean;                      // true if expected_return is set
  check_in_threshold_days: 7;                // hard-coded safety net
}
```

**Activation flow:**

```
Sam: "Arlo, I'm going to be away for a few days."
Arlo: "Got it. How long do you think you'll be away?"
Sam: "Until Sunday."
Arlo: "Okay, I'll keep things quiet until Sunday. If anything urgent comes in
       I'll still let you know when you're back. Have a good time, Sam."
```

During Away mode:

- Morning check-ins are suspended.
- All notifications queue silently (except Level 1, which queues but is delivered immediately when Sam returns).
- The 2-day silence protocol is suspended.
- The 7-day safety threshold is NOT suspended. This is the only case where Arlo escalates without Sam's explicit permission, and it is documented clearly during onboarding.

### 8.3 Escalation Message Format (Caregiver Alerts)

All caregiver alerts follow this template:

```
To: [Contact name]
From: Companion (Arlo)
Subject: Check-in about Sam

Hi [Contact first name],

Sam hasn't responded to check-ins for [duration]. This is an automated message
from Companion. You may want to reach out.

— Arlo (Sam's Companion assistant)
```

The message never includes:

- Financial details (amounts, account numbers)
- Medical details (medications, diagnoses)
- Document contents
- Location data
- Conversation history

---

## 9. Performance Targets

All latency targets measured at P95 (95th percentile) under normal operating conditions.

| Metric | Target | Measurement Point |
|---|---|---|
| TTS latency (first audio byte) | < 500ms | From TTS API call to first audio chunk received by client |
| STT recognition latency | < 1 second | From end of user speech to final transcript available |
| LLM response generation | < 3 seconds | From prompt sent to first token received (streaming) |
| Wake word detection | < 300ms | From utterance completion to callback fired |
| Full turn latency (user stops speaking to Arlo starts speaking) | < 5 seconds | End-to-end, includes STT + LLM + TTS first byte |
| Morning check-in assembly | < 2 seconds | From scheduler trigger to complete script ready for TTS |
| Notification delivery (push) | < 10 seconds | From event firing to push notification received on device |
| Conversation state serialization | < 200ms | Session save to database on pause/end |

**Monitoring and alerting:**

- All latency metrics are tracked per-request and reported to the observability stack.
- Alerts fire when P95 exceeds 2x the target for any 5-minute window.
- Wake word detection is measured on-device; all other metrics are measured server-side with client-reported timestamps for end-to-end validation.

**Degradation strategy:**

| Component | If Target Exceeded | Fallback |
|---|---|---|
| TTS | > 2 seconds | Deliver text-only response with "Voice is slow right now" banner |
| STT | > 3 seconds | Prompt user to type instead |
| LLM | > 8 seconds | "Give me a moment..." indicator; no timeout until 15 seconds, then generic error |
| Morning check-in assembly | > 5 seconds | Deliver partial check-in (greeting + Level 1/2 items only) |
