"""Language detection utilities."""

from langdetect import detect, LangDetectException


def detect_language(text: str) -> str:
    """
    Detect language of text.

    Args:
        text: Text to analyze

    Returns:
        ISO 639-1 language code (e.g., 'en', 'cs', 'de')
    """
    try:
        if not text or len(text.strip()) < 10:
            return "en"  # Default to English for short texts
        return detect(text)
    except LangDetectException:
        return "en"  # Default to English on detection failure
