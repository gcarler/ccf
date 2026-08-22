import os
os.environ["PYTEST_CURRENT_TEST"] = "1"

import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient
from backend.main import app
from backend.core.database import get_db, Base
from backend import models

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

query_counter = []

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    statement_str = statement.strip()
    if statement_str.upper().startswith("SELECT"):
        query_counter.append(statement_str)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def run_test():
    client = TestClient(app)
    db = TestingSessionLocal()
    
    site_key = "emp-site"
    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key=site_key,
        name="Empirical Test Site",
        base_path="/emp",
        is_active=True,
    )
    db.add(site)
    
    # Page WITH published_version_id (Versioned Published Page)
    page_versioned = models.CmsPage(
        id=uuid.uuid4(),
        site_id=site.id,
        slug="home-versioned",
        title="Versioned Home",
        status="published",
        seo_json={},
    )
    db.add(page_versioned)
    db.flush()
    
    # Create version
    version_id = uuid.uuid4()
    version = models.CmsPageVersion(
        id=version_id,
        page_id=page_versioned.id,
        version_number=1,
        snapshot_json={
            "page": {"slug": "home-versioned", "title": "Versioned Home"},
            "sections": [
                {"id": str(uuid.uuid4()), "type": "hero", "props_json": {}, "sort_order": 0, "is_visible": True, "status": "active"},
                {"id": str(uuid.uuid4()), "type": "cta_banner", "props_json": {}, "sort_order": 1, "is_visible": True, "status": "active"},
                {"id": str(uuid.uuid4()), "type": "stats", "props_json": {}, "sort_order": 2, "is_visible": True, "status": "active"},
                {"id": str(uuid.uuid4()), "type": "team", "props_json": {}, "sort_order": 3, "is_visible": True, "status": "active"},
                {"id": str(uuid.uuid4()), "type": "testimonials", "props_json": {}, "sort_order": 4, "is_visible": True, "status": "active"},
                {"id": str(uuid.uuid4()), "type": "faq", "props_json": {}, "sort_order": 5, "is_visible": True, "status": "active"},
                {"id": str(uuid.uuid4()), "type": "embed", "props_json": {}, "sort_order": 6, "is_visible": True, "status": "active"},
                {"id": str(uuid.uuid4()), "type": "rich_text", "props_json": {}, "sort_order": 7, "is_visible": True, "status": "active"},
            ]
        }
    )
    db.add(version)
    page_versioned.published_version_id = version.id
    
    # Page WITHOUT published_version_id (Direct ORM Sections Page)
    page_direct = models.CmsPage(
        id=uuid.uuid4(),
        site_id=site.id,
        slug="home-direct",
        title="Direct Home",
        status="published",
        seo_json={},
    )
    db.add(page_direct)
    db.flush()
    
    section_types = ["hero", "cta_banner", "stats", "team", "testimonials", "faq", "embed", "rich_text"]
    for idx, stype in enumerate(section_types):
        db.add(models.CmsSection(
            id=uuid.uuid4(),
            page_id=page_direct.id,
            section_key=f"sec-dir-{idx}",
            type=stype,
            props_json={},
            sort_order=idx,
            is_visible=True,
            status="active",
        ))

    sys_vars = [
        ("church_name", "Iglesia Faro"),
        ("mission_statement", "Nuestra Misión"),
        ("service_time", "Domingos 10 AM"),
        ("address", "Calle Principal 123"),
        ("map_embed_url", "https://maps.example.com"),
        ("welcome_title", "Bienvenido"),
        ("cta_text", "Únete"),
        ("cta_link", "/join"),
        ("cta_title", "Únete Hoy"),
        ("cta_description", "Descripción de CTA"),
    ]
    for key, val in sys_vars:
        db.add(models.SystemVariable(
            id=uuid.uuid4(),
            key=f"{site_key}_{key}",
            value=val,
        ))
        
    db.commit()
    
    # 1. Test Versioned Page
    query_counter.clear()
    res1 = client.get(f"/api/cms/v2/public/sites/{site_key}/pages/home-versioned")
    print(f"\n1. Versioned Page: HTTP {res1.status_code} | Queries count: {len(query_counter)}")
    for i, q in enumerate(query_counter, 1):
        print(f"  {i}. {q[:140]}")
        
    # 2. Test Direct ORM Page
    query_counter.clear()
    res2 = client.get(f"/api/cms/v2/public/sites/{site_key}/pages/home-direct")
    print(f"\n2. Direct Page: HTTP {res2.status_code} | Queries count: {len(query_counter)}")
    for i, q in enumerate(query_counter, 1):
        print(f"  {i}. {q[:140]}")

if __name__ == "__main__":
    run_test()
