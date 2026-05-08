"""Tests for utility helpers."""

from ytrag.utils import extract_base_name, get_language_from_filename


class TestExtractBaseName:
    """Tests for base transcript filename extraction."""

    def test_removes_regional_language_suffixes(self):
        """Should remove arbitrary regional language suffixes."""
        assert extract_base_name("20240101_Video.es-419.vtt") == "20240101_Video"


class TestGetLanguageFromFilename:
    """Tests for subtitle language extraction."""

    def test_extracts_regional_language_suffixes(self):
        """Should extract arbitrary regional language suffixes."""
        assert get_language_from_filename("20240101_Video.es-419.vtt") == "ES-419"
