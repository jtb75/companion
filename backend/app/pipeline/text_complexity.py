import re


def count_syllables(word: str) -> int:
    """Heuristic to count syllables in an English word."""
    word = word.lower()
    if not word:
        return 0
    # Basic rule: count vowel groups, but ignore trailing 'e'
    count = len(re.findall(r'[aeiouy]+', word))
    if word.endswith('e'):
        count -= 1
    if count == 0:
        count = 1
    return count

def get_flesch_kincaid_grade(text: str) -> float:
    """Calculate Flesch-Kincaid Grade Level score.
    Formula: 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
    """
    if not text:
        return 0.0

    # Clean text (remove markdown, etc.)
    text = re.sub(r'[*_#]', '', text)

    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    num_sentences = len(sentences) or 1

    words = re.findall(r'\w+', text)
    num_words = len(words) or 1

    num_syllables = sum(count_syllables(w) for w in words)

    grade = 0.39 * (num_words / num_sentences) + 11.8 * (num_syllables / num_words) - 15.59
    return round(max(0.0, grade), 1)
