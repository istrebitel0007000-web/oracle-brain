"""tests/test_i18n.py — i18n module tests"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_all_languages_have_core_keys():
    from oracle_brain.i18n import TRANSLATIONS, SUPPORTED_LANGUAGES
    for lang in SUPPORTED_LANGUAGES:
        for key in ["welcome", "sign_in", "send", "error", "success", "logout"]:
            assert key in TRANSLATIONS[lang], f"Missing '{key}' in lang '{lang}'"


def test_english_translation():
    from oracle_brain.i18n import t
    assert t("send", "en") == "Send"
    assert t("error", "en") == "Error"


def test_arabic_translation():
    from oracle_brain.i18n import t
    assert t("send", "ar") == "إرسال"


def test_russian_translation():
    from oracle_brain.i18n import t
    assert t("send", "ru") == "Отправить"


def test_uzbek_translation():
    from oracle_brain.i18n import t
    assert t("send", "uz") == "Yuborish"


def test_fallback_unknown_lang_to_english():
    from oracle_brain.i18n import t
    assert t("send", "xx") == "Send"


def test_fallback_missing_key_returns_key():
    from oracle_brain.i18n import t
    assert t("nonexistent_key_xyz", "en") == "nonexistent_key_xyz"


def test_format_kwargs():
    from oracle_brain.i18n import t
    result = t("file_too_large", "en", max=20)
    assert "20" in result
    result_ar = t("file_too_large", "ar", max=10)
    assert "10" in result_ar


def test_rtl_detection():
    from oracle_brain.i18n import is_rtl
    assert is_rtl("ar") is True
    assert is_rtl("en") is False
    assert is_rtl("ru") is False
    assert is_rtl("uz") is False


def test_html_dir():
    from oracle_brain.i18n import get_html_dir
    assert get_html_dir("ar") == "rtl"
    assert get_html_dir("en") == "ltr"


def test_language_names_complete():
    from oracle_brain.i18n import LANGUAGE_NAMES, SUPPORTED_LANGUAGES
    for lang in SUPPORTED_LANGUAGES:
        assert lang in LANGUAGE_NAMES, f"Missing name for '{lang}'"
