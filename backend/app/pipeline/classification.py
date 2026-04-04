"""Stage 2 — Two-tier classification. Tier 1 is rule-based, Tier 2 uses LLM."""

import json
import logging
import re

from app.pipeline.schemas import ClassificationResult, NormalizedDocument

logger = logging.getLogger(__name__)

# Tier 1: Rule-based patterns for obvious classifications
BILL_PATTERNS = [
    r"amount\s+due", r"payment\s+due", r"balance\s+due",
    r"total\s+due", r"\$\d+\.\d{2}", r"account\s+(number|#|no)",
    r"due\s+date", r"pay\s+by", r"invoice",
]

JUNK_PATTERNS = [
    r"unsubscribe", r"click\s+here\s+to\s+opt", r"special\s+offer",
    r"limited\s+time", r"act\s+now", r"you\'ve\s+been\s+selected",
    r"dear\s+valued\s+customer", r"congratulations",
]

LEGAL_PATTERNS = [
    r"legal\s+notice", r"collections?", r"eviction",
    r"court\s+order", r"subpoena", r"attorney",
    r"lawsuit", r"judgment", r"lien",
]

MEDICAL_PATTERNS = [
    r"appointment", r"patient", r"doctor|dr\.",
    r"prescription", r"diagnosis", r"medical\s+record",
    r"explanation\s+of\s+benefits", r"eob",
]

GOVERNMENT_PATTERNS = [
    r"social\s+security", r"ssi", r"medicaid",
    r"medicare", r"irs", r"internal\s+revenue",
    r"department\s+of", r"dmv",
]


async def classify(doc: NormalizedDocument) -> ClassificationResult:
    """Classify a document using two-tier approach."""
    text_lower = doc.raw_text.lower()

    # Tier 1: Fast rule-based classification
    tier1_result = _tier1_classify(text_lower)
    if tier1_result and tier1_result[1] > 0.95:
        classification, confidence = tier1_result
        return ClassificationResult(
            document_id=doc.document_id,
            classification=classification,
            urgency_level=_infer_urgency(classification, text_lower),
            confidence_score=confidence,
            classifier_tier=1,
        )

    # Tier 2: LLM classification (stubbed)
    return await _tier2_classify(doc)


def _tier1_classify(text: str) -> tuple[str, float] | None:
    """Fast rule-based classifier. Returns (classification, confidence) or None."""
    scores: dict[str, float] = {}

    for classification, patterns in [
        ("junk", JUNK_PATTERNS),
        ("bill", BILL_PATTERNS),
        ("legal", LEGAL_PATTERNS),
        ("medical", MEDICAL_PATTERNS),
        ("government", GOVERNMENT_PATTERNS),
    ]:
        matches = sum(1 for p in patterns if re.search(p, text))
        if matches > 0:
            # Confidence scales with pattern matches
            scores[classification] = min(0.5 + (matches * 0.12), 1.0)

    if not scores:
        return None

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    confidence = scores[best]

    # Safety: junk classification must be very confident (conservative)
    if best == "junk" and confidence < 0.9:
        return None

    # Only return if confident enough for tier 1
    return (best, confidence) if confidence > 0.7 else None


def _infer_urgency(classification: str, text: str) -> str:
    """Determine urgency level based on classification and text content."""
    # Legal/collections/eviction always urgent
    if classification == "legal":
        return "urgent"

    # Junk is always routine
    if classification == "junk":
        return "routine"

    # Check for time-sensitive language
    urgent_patterns = [
        r"immediate", r"urgent", r"overdue", r"past\s+due",
        r"final\s+notice", r"disconnect", r"termination",
    ]
    if any(re.search(p, text) for p in urgent_patterns):
        return "act_today"

    soon_patterns = [r"due\s+in\s+\d+\s+days", r"reminder", r"upcoming"]
    if any(re.search(p, text) for p in soon_patterns):
        return "needs_attention"

    return "routine"


_CLASSIFY_PROMPT = """Classify this document into exactly one category.

Categories: bill, legal, government, medical, insurance, form, junk, personal, unknown
Urgency: routine, needs_attention, act_today, urgent

Respond with JSON only, no other text:
{"classification": "...", "urgency": "...", "confidence": 0.0-1.0}

Document text:
"""


async def _tier2_classify(doc: NormalizedDocument) -> ClassificationResult:
    """LLM-based classification for documents that Tier 1 couldn't classify."""
    from app.conversation.llm import get_llm_client

    # Try LLM classification
    try:
        llm = get_llm_client()
        text_snippet = doc.raw_text[:3000]
        response = await llm.generate(
            system_prompt="You are a document classifier. Respond with valid JSON only.",
            messages=[{"role": "user", "content": _CLASSIFY_PROMPT + text_snippet}],
            max_tokens=1000,
            temperature=0.2,
            response_json=True,
            disable_thinking=True,
        )

        from app.conversation.llm import extract_json

        try:
            parsed = extract_json(response)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "Classification raw LLM response: %s",
                response[:500],
            )
            raise
        classification = parsed.get("classification", "unknown")
        urgency = parsed.get("urgency", "needs_attention")
        confidence = min(max(float(parsed.get("confidence", 0.7)), 0.0), 1.0)

        valid_classes = {
            "bill", "legal", "government", "medical",
            "insurance", "form", "junk", "personal", "unknown",
        }
        valid_urgencies = {"routine", "needs_attention", "act_today", "urgent"}

        if classification not in valid_classes:
            classification = "unknown"
        if urgency not in valid_urgencies:
            urgency = "needs_attention"

        return ClassificationResult(
            document_id=doc.document_id,
            classification=classification,
            urgency_level=urgency,
            confidence_score=confidence,
            classifier_tier=2,
        )
    except Exception:
        logger.warning("Tier 2 LLM classification failed, falling back to heuristics")

    # Fallback: heuristic retry
    text_lower = doc.raw_text.lower()
    tier1 = _tier1_classify(text_lower)
    if tier1:
        classification, confidence = tier1
        return ClassificationResult(
            document_id=doc.document_id,
            classification=classification,
            urgency_level=_infer_urgency(classification, text_lower),
            confidence_score=min(confidence + 0.1, 0.95),
            classifier_tier=2,
        )

    return ClassificationResult(
        document_id=doc.document_id,
        classification="unknown",
        urgency_level="needs_attention",
        confidence_score=0.3,
        classifier_tier=2,
    )
