import os
os.environ["PYTEST_CURRENT_TEST"] = "1"

import sys
import uuid
from datetime import datetime, timezone
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient
from backend.main import app
from backend.core.database import get_db, Base
from backend import models

# Create isolated SQLite database with StaticPool so all connections share the memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)

# Query counter
query_counter = []

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    statement_str = statement.strip()
    if statement_str.upper().startswith("SELECT"):
        query_counter.append(statement_str)

def reset_counter():
    query_counter.clear()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def run_verification():
    client = TestClient(app)
    db = TestingSessionLocal()
    
    try:
        print("=== EMPIRICAL QUERY COUNT VERIFICATION (SQLite StaticPool) ===")
        
        # Seed Site
        site_key = "emp-site"
        site = models.CmsSite(
            id=uuid.uuid4(),
            site_key=site_key,
            name="Empirical Test Site",
            base_path="/emp",
            is_active=True,
        )
        db.add(site)
        
        # 1. Seed Page with 8 sections + SystemVariables
        page = models.CmsPage(
            id=uuid.uuid4(),
            site_id=site.id,
            slug="emp-page",
            title="Empirical Page",
            status="published",
            seo_json={},
        )
        db.add(page)
        
        # SystemVariables for site
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
            
        section_types = ["hero", "cta_banner", "stats", "team", "testimonials", "faq", "embed", "rich_text"]
        for idx, stype in enumerate(section_types):
            db.add(models.CmsSection(
                id=uuid.uuid4(),
                page_id=page.id,
                section_key=f"sec-{idx}",
                type=stype,
                props_json={},
                sort_order=idx,
                is_visible=True,
                status="active",
            ))
            
        # 2. Seed Theme
        theme = models.CmsTheme(
            id=uuid.uuid4(),
            site_id=site.id,
            name="Empirical Theme",
            tokens_json={},
            is_active=True,
            status="active",
            version=1,
        )
        db.add(theme)
        
        # 3. Seed Menu with 10 items
        menu = models.CmsMenu(
            id=uuid.uuid4(),
            site_id=site.id,
            menu_key="main",
            name="Main Menu",
            is_active=True,
        )
        db.add(menu)
        db.flush()
        
        for idx in range(10):
            db.add(models.CmsMenuItem(
                id=uuid.uuid4(),
                menu_id=menu.id,
                label=f"Item {idx}",
                href=f"/link-{idx}",
                visibility="public",
                sort_order=idx,
            ))
            
        # 4. Seed 20 Posts with Categories, Tags, and Authors
        persona1 = models.Persona(
            id=uuid.uuid4(),
            first_name="Juan",
            last_name="Perez",
            estado_vital="ACTIVO",
        )
        persona2 = models.Persona(
            id=uuid.uuid4(),
            first_name="Maria",
            last_name="Gomez",
            estado_vital="ACTIVO",
        )
        db.add(persona1)
        db.add(persona2)
        db.flush()
        
        cat1 = models.CmsCategory(id=uuid.uuid4(), site_id=site.id, slug="noticias", name="Noticias")
        cat2 = models.CmsCategory(id=uuid.uuid4(), site_id=site.id, slug="eventos", name="Eventos")
        tag1 = models.CmsTag(id=uuid.uuid4(), site_id=site.id, slug="general", name="General")
        tag2 = models.CmsTag(id=uuid.uuid4(), site_id=site.id, slug="destacado", name="Destacado")
        db.add_all([cat1, cat2, tag1, tag2])
        db.flush()
        
        posts = []
        for i in range(20):
            p = models.CmsPost(
                id=uuid.uuid4(),
                site_id=site.id,
                slug=f"post-{i}",
                title=f"Post {i}",
                status="published",
                published_at=datetime.now(timezone.utc),
                author_persona_id=persona1.id if i % 2 == 0 else persona2.id,
                seo_json={},
            )
            db.add(p)
            db.flush()
            posts.append(p)
            
            db.add(models.CmsPostCategory(post_id=p.id, category_id=cat1.id if i % 2 == 0 else cat2.id))
            db.add(models.CmsPostTag(post_id=p.id, tag_id=tag1.id if i % 3 == 0 else tag2.id))
            
        db.commit()
        print("Database seeded successfully in SQLite StaticPool.")
        
        # Test 1: public_theme
        reset_counter()
        res = client.get(f"/api/cms/v2/public/sites/{site_key}/theme")
        count_theme = len(query_counter)
        print(f"\n1. public_theme: HTTP {res.status_code} | Queries emitted: {count_theme}")
        for q in query_counter:
            print("   ->", q.replace("\n", " ")[:120])
            
        # Test 2: public_menu
        reset_counter()
        res = client.get(f"/api/cms/v2/public/sites/{site_key}/menus/main")
        count_menu = len(query_counter)
        print(f"\n2. public_menu: HTTP {res.status_code} | Queries emitted: {count_menu}")
        for q in query_counter:
            print("   ->", q.replace("\n", " ")[:120])
            
        # Test 3: public_page (N=8 sections)
        reset_counter()
        res = client.get(f"/api/cms/v2/public/sites/{site_key}/pages/emp-page")
        count_page = len(query_counter)
        print(f"\n3. public_page (8 sections): HTTP {res.status_code} | Queries emitted: {count_page}")
        for q in query_counter:
            print("   ->", q.replace("\n", " ")[:120])

        # Test 4: public_post (single)
        reset_counter()
        res = client.get(f"/api/cms/v2/public/sites/{site_key}/posts/post-0")
        count_post = len(query_counter)
        print(f"\n4. public_post (single): HTTP {res.status_code} | Queries emitted: {count_post}")
        for q in query_counter:
            print("   ->", q.replace("\n", " ")[:120])

        # Test 5: public_posts_list (N=20 posts)
        reset_counter()
        res = client.get(f"/api/cms/v2/public/sites/{site_key}/posts")
        count_posts = len(query_counter)
        print(f"\n5. public_posts_list (20 posts): HTTP {res.status_code} | Queries emitted: {count_posts}")
        for q in query_counter:
            print("   ->", q.replace("\n", " ")[:120])

    finally:
        db.close()

if __name__ == "__main__":
    run_verification()
