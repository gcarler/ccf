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
    
    site_key = "emp-posts-site"
    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key=site_key,
        name="Empirical Posts Site",
        base_path="/emp-posts",
        is_active=True,
    )
    db.add(site)
    
    persona1 = models.Persona(id=uuid.uuid4(), first_name="Juan", last_name="Perez", estado_vital="ACTIVO")
    persona2 = models.Persona(id=uuid.uuid4(), first_name="Maria", last_name="Gomez", estado_vital="ACTIVO")
    db.add_all([persona1, persona2])
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
    
    # 1. Test public_post (single post)
    query_counter.clear()
    res1 = client.get(f"/api/cms/v2/public/sites/{site_key}/posts/post-0")
    print(f"\n1. public_post (single): HTTP {res1.status_code} | Queries count: {len(query_counter)}")
    for i, q in enumerate(query_counter, 1):
        print(f"  {i}. {q[:140]}")

    # 2. Test public_posts_list (20 posts)
    query_counter.clear()
    res2 = client.get(f"/api/cms/v2/public/sites/{site_key}/posts")
    print(f"\n2. public_posts_list (20 posts): HTTP {res2.status_code} | Queries count: {len(query_counter)}")
    for i, q in enumerate(query_counter, 1):
        print(f"  {i}. {q[:140]}")

if __name__ == "__main__":
    run_test()
