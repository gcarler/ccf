"""Unit tests for backend/services/mention_parser.py

These tests cover the regex-based extraction of @mentions. The
resolve_mentions() function is exercised indirectly by the project/agenda
comment endpoint tests.
"""

from backend.services.mention_parser import extract_mentions


def test_extract_mentions_uuid():
    uuid_str = "123e4567-e89b-12d3-a456-426614174000"
    content = f"Hola @[Juan]({uuid_str}) y <@{uuid_str}> duplicado"
    uuid_tokens, username_tokens, fullname_tokens = extract_mentions(content)
    assert uuid_tokens == {uuid_str}
    assert username_tokens == set()
    assert fullname_tokens == set()


def test_extract_mentions_username():
    content = "@juan.perez revisa esto por favor"
    uuid_tokens, username_tokens, fullname_tokens = extract_mentions(content)
    assert uuid_tokens == set()
    assert username_tokens == {"juan.perez"}
    assert fullname_tokens == set()


def test_extract_mentions_email():
    content = "@juan@example.com revisa esto"
    uuid_tokens, username_tokens, fullname_tokens = extract_mentions(content)
    assert uuid_tokens == set()
    assert username_tokens == {"juan@example.com"}
    assert fullname_tokens == set()


def test_extract_mentions_fullname():
    content = "@Juan Pérez revisa esto y @María García también"
    uuid_tokens, username_tokens, fullname_tokens = extract_mentions(content)
    assert uuid_tokens == set()
    assert username_tokens == set()
    assert fullname_tokens == {"Juan Pérez", "María García"}


def test_extract_does_not_swallow_sentence():
    content = "@Juan Pérez revisa esto mañana"
    _, _, fullname_tokens = extract_mentions(content)
    assert fullname_tokens == {"Juan Pérez"}


def test_extract_fullname_case_insensitive():
    content = "@juan pérez revisa esto"
    _, _, fullname_tokens = extract_mentions(content)
    assert fullname_tokens == {"juan pérez"}


def test_extract_fullname_three_words():
    content = "@Juan Antonio Pérez revisa esto"
    _, _, fullname_tokens = extract_mentions(content)
    assert fullname_tokens == {"Juan Antonio Pérez"}


def test_extract_ignores_email_in_text():
    # "foo@bar.com" should not match because @ is preceded by a word char.
    content = "escríbeme a foo@bar.com"
    uuid_tokens, username_tokens, fullname_tokens = extract_mentions(content)
    assert username_tokens == set()
    assert fullname_tokens == set()


def test_extract_combined_mentions():
    uuid_str = "123e4567-e89b-12d3-a456-426614174000"
    content = f"@admin @Juan Pérez y @[Ana]({uuid_str}) revisen esto"
    uuid_tokens, username_tokens, fullname_tokens = extract_mentions(content)
    assert uuid_tokens == {uuid_str}
    assert username_tokens == {"admin"}
    assert fullname_tokens == {"Juan Pérez"}
