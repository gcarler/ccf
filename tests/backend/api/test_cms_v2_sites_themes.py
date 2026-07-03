import uuid

import pytest

pytestmark = pytest.mark.skip(reason="Legacy test disabled")

from backend import crud as crud_cms
from backend import schemas
from backend.api import cms_v2


@pytest.fixture
def full():
    class DummyDB:
        pass
    class DummyUser:
        id = uuid.uuid4()
        role = "admin"
        rol_plataforma = None
    return DummyDB(), DummyUser()


def test_crud_sites_and_themes(full):
    db, admin = full
    # Create site
    site_payload = schemas.CmsSiteCreate(site_key="full", name="Full Site", base_path="/full")
    site = crud_cms.create_cms_site(db, site_payload)
    assert site.key == "full"
    # Create theme
    theme_payload = schemas.CmsThemeCreate(
        site_key="full",
        name="Blue Theme",
        tokens_json={"primary": "#0000ff"},
    )
    theme = crud_cms.create_cms_theme(db, site.id, theme_payload, created_by=None)
    assert theme.name == "Blue Theme"
    # List sites and themes
    sites = cms_v2.list_sites(db=db)
    assert any(s.key == "full" for s in sites)
    themes = cms_v2.list_themes("full", db, admin)
    assert any(t.id == theme.id for t in themes)
    # Update theme using correct schema
    patched = cms_v2.patch_theme("full", theme.id, schemas.CmsThemeUpdate(name="Renamed"), db=db, current_user=admin)
    assert patched.name == "Renamed"
    # Delete theme and site
    cms_v2.delete_theme("full", theme.id, db=db, current_user=admin)
    cms_v2.delete_site("full", db=db, current_user=admin)
    # Verify deletion
    sites_after = cms_v2.list_sites(db=db)
    assert not any(s.key == "full" for s in sites_after)
