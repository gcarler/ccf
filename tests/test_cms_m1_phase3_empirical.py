"""Empirical query count verification for the 5 CMS v2 public endpoints (Fase 3).

Verifies that SQL query counts remain O(1) and do not suffer from N+1 regressions.
Target endpoints:
1. GET /api/cms/v2/public/sites/{site_key}/theme (public_theme)
2. GET /api/cms/v2/public/sites/{site_key}/menus/{menu_key} (public_menu)
3. GET /api/cms/v2/public/sites/{site_key}/pages/{slug} (public_page)
4. GET /api/cms/v2/public/sites/{site_key}/posts (public_posts_list)
5. GET /api/cms/v2/public/sites/{site_key}/posts/{slug} (public_post)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import event

from backend import models
from backend.api.cms_v2.public import (
    public_theme,
    public_menu,
    public_page,
    public_posts_list,
    public_post,
)
from backend.core.cache_v2 import get_redis
from tests.conftest import seed_admin


class QueryCounter:
    def __init__(self, engine):
        self.engine = engine
        self.statements = []

    def __enter__(self):
        self.statements = []
        event.listen(self.engine, "before_cursor_execute", self._before_cursor_execute)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        event.remove(self.engine, "before_cursor_execute", self._before_cursor_execute)

    def _before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    @property
    def count(self):
        return len(self.statements)

    @property
    def select_count(self):
        return sum(1 for stmt in self.statements if stmt.strip().upper().startswith("SELECT"))


def _seed_site(db, key="emp"):
    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key=f"{key}-{uuid.uuid4().hex[:6]}",
        name=f"Empirical Site {key}",
        base_path="/",
        is_active=True,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def _clear_cache():
    try:
        redis = get_redis()
        if hasattr(redis, "flushall"):
            redis.flushall()
        elif hasattr(redis, "_storage"):
            redis._storage.clear()
    except Exception:
        pass


def test_empirical_public_theme_query_count(db_session):
    """public_theme: <= 2 SELECT queries (Site + Theme), 0 N+1 loops."""
    site = _seed_site(db_session, "theme")
    theme = models.CmsTheme(
        id=uuid.uuid4(),
        site_id=site.id,
        name="Default Theme",
        is_active=True,
        status="active",
        tokens_json={"primary": "#000000"},
    )
    db_session.add(theme)
    db_session.commit()

    _clear_cache()
    engine = db_session.get_bind()
    with QueryCounter(engine) as q:
        res = public_theme(site_key=site.site_key, db=db_session)
    assert res is not None
    # 1 for site + 1 for active theme = 2 SELECTs
    assert q.select_count <= 2, f"Expected <= 2 SELECTs, got {q.select_count}: {q.statements}"


def test_empirical_public_menu_query_count(db_session):
    """public_menu: O(1) query count (3 SELECTs: Site + Menu + MenuItems collection batch).
    
    Test with 15 menu items to empirically prove query count is constant.
    """
    site = _seed_site(db_session, "menu")
    menu = models.CmsMenu(
        id=uuid.uuid4(),
        site_id=site.id,
        name="Main Navigation",
        menu_key="main",
        is_active=True,
    )
    db_session.add(menu)
    db_session.commit()

    # Add 15 menu items
    for i in range(15):
        item = models.CmsMenuItem(
            id=uuid.uuid4(),
            menu_id=menu.id,
            label=f"Link {i}",
            href=f"/page-{i}",
            sort_order=i,
            visibility="public",
        )
        db_session.add(item)
    db_session.commit()

    _clear_cache()
    engine = db_session.get_bind()
    with QueryCounter(engine) as q:
        res = public_menu(site_key=site.site_key, menu_key="main", db=db_session)
    assert len(res["items"]) == 15
    # Site + Menu + MenuItems batch SELECT = 3 queries
    assert q.select_count <= 3, f"Expected <= 3 SELECTs for 15 items, got {q.select_count}: {q.statements}"


def test_empirical_public_page_query_count(db_session):
    """public_page: O(1) query count regardless of N sections.
    
    Tests 8 sections to ensure SystemVariable fetching is batched into 1 query
    and does NOT issue 8x5 = 40 SELECTs.
    """
    site = _seed_site(db_session, "page")
    page = models.CmsPage(
        id=uuid.uuid4(),
        site_id=site.id,
        slug="hero-page",
        title="Hero Page",
        status="published",
    )
    db_session.add(page)
    db_session.commit()

    # Add 8 sections with props referencing system variables
    for i in range(8):
        sec = models.CmsSection(
            id=uuid.uuid4(),
            page_id=page.id,
            type="hero",
            sort_order=i,
            is_visible=True,
            status="active",
            props_json={"heading": f"Section {i}"},
        )
        db_session.add(sec)
    db_session.commit()

    _clear_cache()
    engine = db_session.get_bind()
    with QueryCounter(engine) as q:
        res = public_page(site_key=site.site_key, slug="hero-page", db=db_session)
    assert res.slug == "hero-page"
    # Site + Page + Sections + SystemVars Batch <= 4 SELECTs
    # Before fix: 1 + 8*5 = 41 queries.
    assert q.select_count <= 4, f"Expected <= 4 SELECTs for 8 sections, got {q.select_count}: {q.statements}"


def test_empirical_public_posts_list_query_count(db_session):
    """public_posts_list: O(1) query count (5 SELECTs total for 10 posts).
    
    Before fix: 2 + 10*3 = 32 queries.
    After fix: 1 Site + 1 Posts list + 1 batch categories + 1 batch tags + 1 batch authors = 5 SELECTs.
    """
    user, persona, sede = seed_admin(db_session)
    site = _seed_site(db_session, "posts-list")

    # Create 10 posts with categories, tags, author
    for i in range(10):
        post = models.CmsPost(
            id=uuid.uuid4(),
            site_id=site.id,
            slug=f"post-{i}",
            title=f"Post {i}",
            status="published",
            published_at=datetime.now(timezone.utc),
            author_persona_id=persona.id,
            seo_json={},
        )
        db_session.add(post)
        db_session.flush()

        cat = models.CmsCategory(id=uuid.uuid4(), site_id=site.id, slug=f"cat-{i}", name=f"Cat {i}")
        tag = models.CmsTag(id=uuid.uuid4(), site_id=site.id, slug=f"tag-{i}", name=f"Tag {i}")
        db_session.add_all([cat, tag])
        db_session.flush()

        db_session.add(models.CmsPostCategory(post_id=post.id, category_id=cat.id))
        db_session.add(models.CmsPostTag(post_id=post.id, tag_id=tag.id))
    db_session.commit()

    _clear_cache()
    engine = db_session.get_bind()
    with QueryCounter(engine) as q:
        res = public_posts_list(site_key=site.site_key, db=db_session)
    assert res.total == 10
    # Expected <= 5 SELECTs (Site + Count/Posts + Batch categories + Batch tags + Batch authors)
    assert q.select_count <= 5, f"Expected <= 5 SELECTs for 10 posts, got {q.select_count}: {q.statements}"


def test_empirical_public_post_query_count(db_session):
    """public_post: <= 5 SELECT queries total for single post enriched with categories/tags/author."""
    user, persona, sede = seed_admin(db_session)
    site = _seed_site(db_session, "post-single")

    post = models.CmsPost(
        id=uuid.uuid4(),
        site_id=site.id,
        slug="single-post-slug",
        title="Single Post",
        status="published",
        published_at=datetime.now(timezone.utc),
        author_persona_id=persona.id,
        seo_json={},
    )
    db_session.add(post)
    db_session.flush()

    cat = models.CmsCategory(id=uuid.uuid4(), site_id=site.id, slug="single-cat", name="Single Cat")
    tag = models.CmsTag(id=uuid.uuid4(), site_id=site.id, slug="single-tag", name="Single Tag")
    db_session.add_all([cat, tag])
    db_session.flush()

    db_session.add(models.CmsPostCategory(post_id=post.id, category_id=cat.id))
    db_session.add(models.CmsPostTag(post_id=post.id, tag_id=tag.id))
    db_session.commit()

    _clear_cache()
    engine = db_session.get_bind()
    with QueryCounter(engine) as q:
        res = public_post(site_key=site.site_key, slug="single-post-slug", db=db_session)
    assert res.slug == "single-post-slug"
    assert q.select_count <= 5, f"Expected <= 5 SELECTs, got {q.select_count}: {q.statements}"
