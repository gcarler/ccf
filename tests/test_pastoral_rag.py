"""Tests for M2: Secure Pastoral RAG with pgvector and Row-Level Security (RLS)."""

import uuid
import pytest
from sqlalchemy import text

from backend.core.pgvector_compat import (
    VectorEmbedding,
    compute_cosine_similarity,
    generate_text_embedding,
)
from backend.models import Sede
from backend.models_knowledge_base import AgentKnowledgeBase, KnowledgeBaseArticle
from backend.models_sermones import Sermon
from backend.models_wiki import WikiPage
from backend.schemas.rag import PastoralSearchRequest, PastoralSearchResult
from backend.services.rag_service import PastoralRAGService
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def test_vector_embedding_generation_and_cosine():
    """Verify deterministic embedding generation and cosine similarity math."""
    v1 = generate_text_embedding("sermon sobre la fe y salvacion por gracia")
    v2 = generate_text_embedding("predica acerca de la fe cristiana")
    v3 = generate_text_embedding("receta culinaria y reposteria dulce")

    assert len(v1) == 1536
    assert len(v2) == 1536
    assert len(v3) == 1536

    sim_1_2 = compute_cosine_similarity(v1, v2)
    sim_1_3 = compute_cosine_similarity(v1, v3)

    assert sim_1_2 > sim_1_3, f"Expected higher similarity between religious texts ({sim_1_2} vs {sim_1_3})"
    assert 0.0 <= sim_1_2 <= 1.0
    assert 0.0 <= sim_1_3 <= 1.0


def test_models_rag_entities_and_vector_column(db_session):
    """Verify KnowledgeBaseArticle, Sermon, and WikiPage models support vector embeddings."""
    sede = Sede(id=uuid.uuid4(), nombre="Sede Central", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.flush()

    emb = generate_text_embedding("Test content embedding")

    # KnowledgeBaseArticle
    art = KnowledgeBaseArticle(
        id=uuid.uuid4(),
        title="Articulo de Fundamentos",
        content="Contenido sobre doctrina biblica y teologia pastoral.",
        summary="Resumen de teologia",
        category="teologia",
        sede_id=sede.id,
        embedding=emb,
    )
    db_session.add(art)

    # Sermon
    srm = Sermon(
        id=uuid.uuid4(),
        title="El Poder de la Gracia",
        preacher="Pastor Juan",
        passage="Efesios 2:8-9",
        content="La gracia no es una recompensa sino un regalo inmerecido de Dios.",
        summary="Predica sobre gracia",
        category="gracia",
        sede_id=sede.id,
        embedding=emb,
    )
    db_session.add(srm)

    # WikiPage
    wiki = WikiPage(
        id=uuid.uuid4(),
        page_key="wiki_pastoral_guide",
        title="Guia Pastoral de Discipulado",
        content="Procedimiento ministerial y teologico para el discipulado.",
        category="ministerial",
        sede_id=sede.id,
        embedding=emb,
    )
    db_session.add(wiki)
    db_session.commit()

    # Query back
    fetched_art = db_session.query(KnowledgeBaseArticle).filter_by(id=art.id).first()
    assert fetched_art is not None
    assert fetched_art.title == "Articulo de Fundamentos"
    assert fetched_art.embedding is not None

    fetched_srm = db_session.query(Sermon).filter_by(id=srm.id).first()
    assert fetched_srm is not None
    assert fetched_srm.preacher == "Pastor Juan"
    assert fetched_srm.embedding is not None

    fetched_wiki = db_session.query(WikiPage).filter_by(id=wiki.id).first()
    assert fetched_wiki is not None
    assert fetched_wiki.page_key == "wiki_pastoral_guide"
    assert fetched_wiki.embedding is not None


def test_pastoral_rag_service_hybrid_search(db_session):
    """Verify hybrid search scoring with alpha variations (FTS vs Vector)."""
    sede = Sede(id=uuid.uuid4(), nombre="Sede Norte", ciudad="Medellin", es_activa=True)
    db_session.add(sede)
    db_session.flush()

    service = PastoralRAGService(db=db_session, user_sede_id=sede.id, user_role="pastor")

    art = service.index_knowledge_article(
        title="La Teologia de la Esperanza Cristiana",
        content="Exposicion detallada sobre la escatologia y la bienaventurada esperanza en Cristo.",
        summary="Escatologia y esperanza",
        category="teologia",
        sede_id=sede.id,
    )

    srm = service.index_sermon(
        title="Caminando por Fe en Tiempos Dificiles",
        content="Mensaje pastoral sobre Hebreos 11 y la perseverancia de los santos.",
        preacher="Pastor Andres",
        passage="Hebreos 11:1",
        category="fe",
        sede_id=sede.id,
    )

    wiki = service.index_wiki_page(
        page_key="wiki_manual_oracion",
        title="Manual de Intercesion y Oracion",
        content="Principios de oracion eficaz y guerra espiritual ministerial.",
        category="oracion",
        sede_id=sede.id,
    )
    db_session.commit()

    # Search with alpha=0.5 (Hybrid)
    results_hybrid = service.search(query="esperanza cristiana", limit=5, alpha=0.5)
    assert len(results_hybrid) > 0
    assert results_hybrid[0].title == "La Teologia de la Esperanza Cristiana"
    assert results_hybrid[0].source == "knowledge_base"
    assert results_hybrid[0].score > 0.0

    # Search with alpha=0.0 (Pure FTS)
    results_fts = service.search(query="intercesion y oracion", limit=5, alpha=0.0)
    assert len(results_fts) > 0
    assert any(r.source == "wiki" and "Manual de Intercesion" in r.title for r in results_fts)

    # Search with alpha=1.0 (Pure Vector)
    results_vec = service.search(query="perseverancia y fe biblica", limit=5, alpha=1.0)
    assert len(results_vec) > 0
    assert any(r.source == "sermon" for r in results_vec)


def test_pastoral_rag_multi_tenant_rls_isolation(db_session):
    """Verify strict multi-tenant isolation preventing cross-tenant leakage."""
    sede_a = Sede(id=uuid.uuid4(), nombre="Sede Bogota", ciudad="Bogota", es_activa=True)
    sede_b = Sede(id=uuid.uuid4(), nombre="Sede Cali", ciudad="Cali", es_activa=True)
    db_session.add_all([sede_a, sede_b])
    db_session.flush()

    service_a = PastoralRAGService(db=db_session, user_sede_id=sede_a.id, user_role="pastor")
    service_b = PastoralRAGService(db=db_session, user_sede_id=sede_b.id, user_role="pastor")
    service_admin = PastoralRAGService(db=db_session, user_sede_id=None, user_role="admin")

    # Document in Sede A
    service_a.index_sermon(
        title="Confidencial Sede Bogota: Plan Financiero Pastoral",
        content="Detalles privados del presupuesto de la sede Bogota.",
        sede_id=sede_a.id,
    )

    # Document in Sede B
    service_b.index_sermon(
        title="Confidencial Sede Cali: Estrategia Local",
        content="Detalles privados del proyecto evangelistico en Cali.",
        sede_id=sede_b.id,
    )

    # Global document (sede_id=None)
    service_admin.index_knowledge_article(
        title="Doctrina General de la Iglesia Global",
        content="Declaracion de fe comun para todas las sedes de CCF.",
        category="general",
        sede_id=None,
    )
    db_session.commit()

    # User in Sede A searches: should see Sede A + Global, but NEVER Sede B
    results_user_a = service_a.search(query="Confidencial", limit=10)
    titles_a = [r.title for r in results_user_a]
    assert any("Bogota" in t for t in titles_a)
    assert not any("Cali" in t for t in titles_a), "Cross-tenant leakage detected! Sede A saw Sede B document"

    # User in Sede B searches: should see Sede B + Global, but NEVER Sede A
    results_user_b = service_b.search(query="Confidencial", limit=10)
    titles_b = [r.title for r in results_user_b]
    assert any("Cali" in t for t in titles_b)
    assert not any("Bogota" in t for t in titles_b), "Cross-tenant leakage detected! Sede B saw Sede A document"

    # Global search for both users returns global document
    global_a = service_a.search(query="Doctrina General", limit=10)
    assert any("Doctrina General" in r.title for r in global_a)
    global_b = service_b.search(query="Doctrina General", limit=10)
    assert any("Doctrina General" in r.title for r in global_b)

    # Admin user can see all
    results_admin = service_admin.search(query="Confidencial", limit=10)
    titles_admin = [r.title for r in results_admin]
    assert any("Bogota" in t for t in titles_admin)
    assert any("Cali" in t for t in titles_admin)


def test_api_rag_pastoral_health(client):
    """Verify GET /api/rag/pastoral/health endpoint."""
    resp = client.get("/api/rag/pastoral/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert data["service"] == "Pastoral RAG"
    assert "pgvector_installed" in data


def test_api_rag_pastoral_search_endpoint(client, db_session):
    """Verify POST /api/rag/pastoral/search endpoint execution."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    service = PastoralRAGService(db=db_session, user_sede_id=sede.id, user_role="admin")
    service.index_sermon(
        title="La Parabola del Sembrador y el Fruto",
        content="Explicacion sobre la semilla que cae en buena tierra y da fruto al ciento por uno.",
        preacher="Pastor Principal",
        passage="Mateo 13:1-23",
        category="evangelio",
        sede_id=sede.id,
    )
    db_session.commit()

    payload = {
        "query": "sembrador y buena tierra",
        "limit": 5,
        "category": "evangelio",
        "alpha": 0.5,
    }
    resp = client.post("/api/rag/pastoral/search", json=payload, headers=headers)
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert len(results) >= 1
    top = results[0]
    assert "sembrador" in top["title"].lower()
    assert top["source"] == "sermon"
    assert top["score"] > 0.0
    assert "metadata" in top
