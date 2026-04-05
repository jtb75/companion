"""Unit tests for pipeline/classification.py — Tier 1 rule-based classifier."""

from __future__ import annotations

import uuid

from app.pipeline.classification import _tier1_classify, classify
from app.pipeline.schemas import NormalizedDocument


def _make_doc(text: str) -> NormalizedDocument:
    """Build a NormalizedDocument with the given raw_text."""
    return NormalizedDocument(
        document_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        source_channel="email",
        raw_text=text,
    )


# ---------------------------------------------------------------------------
# Tier 1 rule-based tests
# ---------------------------------------------------------------------------


def test_tier1_classifies_bill():
    """Text with multiple bill-related patterns should classify as 'bill'."""
    text = (
        "account number: 12345. "
        "amount due: $150.00. "
        "payment due by March 15. "
        "invoice #9876."
    )
    result = _tier1_classify(text.lower())
    assert result is not None
    classification, confidence = result
    assert classification == "bill"
    assert confidence > 0.7


def test_tier1_classifies_medical():
    """Text with medical patterns should classify as 'medical'."""
    text = (
        "patient: John Doe. "
        "appointment with Dr. Smith on April 5. "
        "prescription: Lisinopril 10mg. "
        "diagnosis: hypertension."
    )
    result = _tier1_classify(text.lower())
    assert result is not None
    classification, confidence = result
    assert classification == "medical"
    assert confidence > 0.7


def test_tier1_classifies_junk():
    """Text full of spam patterns should classify as 'junk' only at high confidence."""
    text = (
        "Congratulations! You've been selected for a special offer! "
        "Act now for a limited time deal. "
        "Click here to opt out. Unsubscribe below."
    )
    result = _tier1_classify(text.lower())
    assert result is not None
    classification, confidence = result
    assert classification == "junk"
    # Junk requires >= 0.9 confidence per the safety check
    assert confidence >= 0.9


def test_tier1_unknown_falls_through():
    """Generic text with no strong patterns should return None (fall through to Tier 2)."""
    text = "Hello, here is some general information about your account."
    result = _tier1_classify(text.lower())
    # Should either return None or a low-confidence result that gets filtered
    assert result is None


def test_tier1_junk_low_confidence_falls_through():
    """A single junk pattern should not be enough — safety guard requires high confidence."""
    text = "Thank you for your order. Unsubscribe from future emails."
    result = _tier1_classify(text.lower())
    # One junk pattern alone should not confidently classify as junk
    if result is not None:
        classification, _ = result
        assert classification != "junk"


# ---------------------------------------------------------------------------
# Full classify() integration test (Tier 1 path only)
# ---------------------------------------------------------------------------


async def test_classify_bill_via_tier1():
    """classify() should return a ClassificationResult with tier=1 for obvious bills."""
    doc = _make_doc(
        "INVOICE #4321. Amount due: $250.00. "
        "Account #****1234. Pay by April 30. "
        "Total due this period: $250.00. "
        "Balance due: $250.00."
    )
    result = await classify(doc)
    assert result.classification == "bill"
    assert result.classifier_tier == 1
    assert result.confidence_score > 0.95
    assert result.document_id == doc.document_id


async def test_classify_legal():
    """Legal documents should be classified with appropriate urgency."""
    doc = _make_doc(
        "LEGAL NOTICE: Collections agency has filed a lawsuit. "
        "Court order requires response by attorney within 30 days. "
        "Failure to appear may result in judgment against you."
    )
    result = await classify(doc)
    assert result.classification == "legal"
    assert result.urgency_level == "urgent"
