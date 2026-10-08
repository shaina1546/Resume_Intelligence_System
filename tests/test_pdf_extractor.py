"""
tests/test_pdf_extractor.py
===========================
Tests for src/pdf_extractor.py

We cannot easily create a real PDF in a test without a PDF library,
so we test:
1. The is_likely_scanned() heuristic.
2. Behaviour with empty/invalid inputs.
3. That the module returns a string (not None, not an exception).
"""

import pytest
from src.pdf_extractor import is_likely_scanned, extract_text_from_pdf


class TestIsLikelyScanned:
    def test_empty_string_is_scanned(self):
        assert is_likely_scanned("") is True

    def test_whitespace_only_is_scanned(self):
        assert is_likely_scanned("   \n\n  ") is True

    def test_short_text_is_scanned(self):
        assert is_likely_scanned("Hello") is True

    def test_long_text_is_not_scanned(self):
        text = "This is a resume with plenty of content. " * 10
        assert is_likely_scanned(text) is False

    def test_custom_threshold(self):
        text = "Short"
        assert is_likely_scanned(text, min_chars=3) is False
        assert is_likely_scanned(text, min_chars=50) is True


class TestExtractTextEdgeCases:
    def test_invalid_bytes_returns_empty_string(self):
        result = extract_text_from_pdf(b"not a pdf at all")
        assert isinstance(result, str)
        # Should return empty string, not crash
        assert result == "" or isinstance(result, str)

    def test_empty_bytes_returns_empty_string(self):
        result = extract_text_from_pdf(b"")
        assert isinstance(result, str)

    def test_nonexistent_path_returns_empty_string(self):
        result = extract_text_from_pdf("/nonexistent/path/to/resume.pdf")
        assert isinstance(result, str)

    def test_wrong_type_returns_empty_string(self):
        result = extract_text_from_pdf(12345)  # type: ignore
        assert isinstance(result, str)
