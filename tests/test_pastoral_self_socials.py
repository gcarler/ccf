"""Tests for pastoral self-service of social media and biography (TKT-CRM-PASTORAL-SELF-SOCIALS-01)."""

from __future__ import annotations

from tests.conftest import auth_headers, seed_admin


def test_update_my_profile_social_instagram_at_handle(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    payload = {
        "social_instagram": "@pastor_carlos",
    }
    response = client.patch("/api/crm/personas/me/profile", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["social_instagram"] == "https://instagram.com/pastor_carlos"


def test_update_my_profile_social_facebook_and_twitter_handles(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    payload = {
        "social_facebook": "@pastor.carlos.ccf",
        "social_twitter": "@pastorcarlos",
    }
    response = client.patch("/api/crm/personas/me/profile", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["social_facebook"] == "https://facebook.com/pastor.carlos.ccf"
    assert data["social_twitter"] == "https://x.com/pastorcarlos"


def test_update_my_profile_plain_handle_and_full_url(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    payload = {
        "social_instagram": "pastor_david",
        "social_facebook": "https://facebook.com/pastordavidoficial",
        "social_twitter": "https://x.com/pastordavid",
    }
    response = client.patch("/api/crm/personas/me/profile", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["social_instagram"] == "https://instagram.com/pastor_david"
    assert data["social_facebook"] == "https://facebook.com/pastordavidoficial"
    assert data["social_twitter"] == "https://x.com/pastordavid"


def test_update_my_profile_bio_short(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    bio = "Pastor principal apasionado por la predicación expositiva y el cuidado pastoral."
    payload = {
        "bio_short": f"  {bio}  ",
    }
    response = client.patch("/api/crm/personas/me/profile", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["bio_short"] == bio


def test_get_my_ministry_profile_reflects_updated_socials_and_bio(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    # 1. Update profile with socials and bio
    update_payload = {
        "bio_short": "Líder de jóvenes y adoración en CCF.",
        "social_instagram": "@lider_ccf",
        "social_facebook": "@liderccfoficial",
        "social_twitter": "@lider_ccf",
    }
    patch_res = client.patch("/api/crm/personas/me/profile", json=update_payload, headers=headers)
    assert patch_res.status_code == 200

    # 2. Fetch profile via GET /crm/personas/me/profile
    get_res = client.get("/api/crm/personas/me/profile", headers=headers)
    assert get_res.status_code == 200
    profile = get_res.json()
    assert profile["bio_short"] == "Líder de jóvenes y adoración en CCF."
    assert profile["social_instagram"] == "https://instagram.com/lider_ccf"
    assert profile["social_facebook"] == "https://facebook.com/liderccfoficial"
    assert profile["social_twitter"] == "https://x.com/lider_ccf"
