import pytest

from backend.schemas.cms_v2_sections import validate_section_props


def test_edge_case_empty_strings():
    """Verify that empty strings in section props pass validation cleanly."""
    types_to_test = ["hero", "cta_banner", "rich_text", "cards", "stats", "faq", "team", "testimonials"]
    for stype in types_to_test:
        props = {
            "title": "",
            "subtitle": "",
            "body": "",
            "cta_text": "",
            "cta_url": "",
            "headline": "",
            "subtext": "",
        }
        res = validate_section_props(stype, props)
        assert isinstance(res, dict)
        assert res.get("title") == "" or res.get("headline") == "" or res.get("title") is None


def test_edge_case_special_characters_and_xss_sanitization():
    """Verify HTML sanitization and safe handling of special characters (quotes, unicode, script tags)."""
    xss_payload = "<script>alert('xss')</script><a href=\"javascript:alert('xss')\">link</a>"
    special_chars = "Special chars: ' \" \\ / < > & | ñ á é 🚀 特 💥 \n\t"

    props = {
        "title": special_chars,
        "body": xss_payload,
        "cta_label": "Click & Save 'test'",
    }
    res = validate_section_props("rich_text", props)
    # <script> should be sanitized out
    assert "<script>" not in res.get("body", "")
    assert "javascript:" not in res.get("body", "")
    # Special characters like unicode should be preserved
    assert "🚀" in res.get("title", "")
    assert "ñ" in res.get("title", "")


def test_edge_case_missing_fields_in_props_json():
    """Verify handling when props_json is empty or missing fields."""
    # Test with empty dict (missing fields inherit schema defaults)
    res_empty = validate_section_props("hero", {})
    assert isinstance(res_empty, dict)
    assert res_empty.get("title") == "" or res_empty.get("title") is None


def test_edge_case_explicit_null_fields_raises_valueerror():
    """Empirical verification: explicit null values for str fields trigger Pydantic validation error in backend."""
    with pytest.raises(ValueError) as exc_info:
        validate_section_props("cta_banner", {"title": None, "body": None})
    assert "Invalid props for section type 'cta_banner'" in str(exc_info.value)
    assert "Input should be a valid string" in str(exc_info.value)


def test_edge_case_rapid_edits_simulation():
    """Simulate rapid sequential edits on a section props object."""
    initial_props = {"title": "Initial", "body": "First text"}

    # Rapid update 1
    props_1 = {**initial_props, "title": "Initi"}
    res_1 = validate_section_props("hero", props_1)
    assert res_1["title"] == "Initi"

    # Rapid update 2
    props_2 = {**props_1, "title": "Initial Title Updated"}
    res_2 = validate_section_props("hero", props_2)
    assert res_2["title"] == "Initial Title Updated"

    # Rapid update 3 with special characters
    props_3 = {**props_2, "body": "Updated text with ⚡ special icons"}
    res_3 = validate_section_props("hero", props_3)
    assert res_3["body"] == "Updated text with ⚡ special icons"
