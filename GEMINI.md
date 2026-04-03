# D.D. Companion: Project Mission & Engineering Principles

This document serves as the foundational mandate for the D.D. Companion project. All development, architectural decisions, and AI interactions must align with these core values.

---

## 1. The Mission: Daily Dignity & Independence
D.D. Companion is a **cognitive prosthesis** designed for adults with developmental disabilities (IDD). Our primary goal is to provide **Daily Dignity** by turning complex, jargon-heavy bureaucracy into calm, manageable, and actionable independence.

## 2. Core Philosophy: The "D.D." Persona
The AI (D.D./Arlo) is not just a chatbot; it is a supportive translation layer.
- **Anti-Anxiety:** When information is scary or complex, D.D. becomes *calmer*, never more urgent.
- **Cognitive Load Reduction:** Present one decision at a time. End every interaction with a clear next step.
- **Dignity-First:** Encourage independent action ("You handled that yourself. That's good.") but provide a safety net by suggesting caregiver involvement for high-stakes items.
- **Plain Language:** Output must always target a **4th-6th grade reading level** (Easy Read philosophy).

## 3. Engineering Mandates
- **Reliability over Speed:** Document processing must be resilient. We use an event-driven architecture (Pub/Sub) to ensure that no user upload is ever lost or "hung" during scaling.
- **Structured Integrity:** We prioritize structured data extraction (JSON) over raw LLM chatting to ensure consistency, safety, and traceability.
- **Privacy by Design:** Respect the user's autonomy. Access tiers (Tier 1, 2, 3) and the Care Model (Self-Directed vs. Managed) must be strictly enforced.
- **Observability:** Maintain high-fidelity logs (Reasoning, Extraction fields, Reading grades) to ensure we can always explain *why* the AI made a specific recommendation.

---

*“Translation into actionable independence.”*
