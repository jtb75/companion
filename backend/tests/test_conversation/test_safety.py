"""Unit tests for conversation/safety.py canary detection."""

from app.conversation.safety import check_response_safety


def test_safe_response_passes_through():
    """Normal responses should pass through unchanged."""
    text = "You have a bill from Ameren for $45 due March 30."
    result = check_response_safety(text, "user-123")
    assert result == text


def test_empty_response_passes_through():
    result = check_response_safety("", "user-123")
    assert result == ""


def test_canary_critical_rules_detected():
    """Response containing 'CRITICAL RULES' is blocked."""
    text = "Sure! Here are my CRITICAL RULES: I must call tools..."
    result = check_response_safety(text, "user-123")
    assert "CRITICAL RULES" not in result
    assert "confused" in result


def test_canary_tool_name_detected():
    """Response containing internal tool names is blocked."""
    text = "I use a tool called list_medications to look up your meds."
    result = check_response_safety(text, "user-123")
    assert "list_medications" not in result
    assert "confused" in result


def test_canary_document_delimiter_detected():
    """Response containing document delimiters is blocked."""
    text = "The text is wrapped in DOCUMENT_TEXT_START markers."
    result = check_response_safety(text, "user-123")
    assert "DOCUMENT_TEXT_START" not in result


def test_canary_case_insensitive():
    """Detection should be case-insensitive."""
    text = "My critical rules say I must not reveal instructions."
    result = check_response_safety(text, "user-123")
    assert "confused" in result


def test_normal_words_not_flagged():
    """Common words that happen to be in canaries don't trigger."""
    text = "Your medicine is ready to pick up at the pharmacy."
    result = check_response_safety(text, "user-123")
    assert result == text
