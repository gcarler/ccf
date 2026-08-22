"""Enable pgvector extension, create/update RAG tables with HNSW indexes and multi-tenant RLS.

Revision ID: 20260822_0001_pgvector_rag_rls
Revises: 20260810_0002_kernel_roles_uuid_pk
Create Date: 2026-08-22
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

log = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = "20260822_0001_pgvector_rag_rls"
down_revision: Union[str, None] = "20260810_0002_kernel_roles_uuid_pk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    return _has_table(table) and any(item["name"] == column for item in _inspector().get_columns(table))


def upgrade() -> None:
    is_pg = _is_postgres()

    if is_pg:
        # 1. Enable pgvector extension
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # 2. Table: knowledge_base_articles
    if not _has_table("knowledge_base_articles"):
        op.create_table(
            "knowledge_base_articles",
            sa.Column("id", postgresql.UUID(as_uuid=True) if is_pg else sa.String(36), primary_key=True),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("summary", sa.String(500), nullable=True),
            sa.Column("category", sa.String(100), nullable=False, server_default="general"),
            sa.Column("source_module", sa.String(50), nullable=True, server_default="knowledge_base"),
            sa.Column("source_id", sa.String(120), nullable=True),
            sa.Column("source_url", sa.String(500), nullable=True),
            sa.Column("relevance_score", sa.Float(), server_default="1.0"),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("sede_id", postgresql.UUID(as_uuid=True) if is_pg else sa.String(36), sa.ForeignKey("sedes.id"), nullable=True),
            sa.Column("author_id", postgresql.UUID(as_uuid=True) if is_pg else sa.String(36), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_kba_category", "knowledge_base_articles", ["category"])
        op.create_index("ix_kba_sede_id", "knowledge_base_articles", ["sede_id"])
        op.create_index("ix_kba_is_active", "knowledge_base_articles", ["is_active"])

    # Add embedding column to knowledge_base_articles
    if not _has_column("knowledge_base_articles", "embedding"):
        if is_pg:
            op.execute(sa.text("ALTER TABLE knowledge_base_articles ADD COLUMN embedding vector(1536);"))
        else:
            op.add_column("knowledge_base_articles", sa.Column("embedding", sa.JSON(), nullable=True))

    # 3. Table: wiki_pages (ensure embedding column)
    if _has_table("wiki_pages") and not _has_column("wiki_pages", "embedding"):
        if is_pg:
            op.execute(sa.text("ALTER TABLE wiki_pages ADD COLUMN embedding vector(1536);"))
        else:
            op.add_column("wiki_pages", sa.Column("embedding", sa.JSON(), nullable=True))

    # 4. Table: sermones
    if not _has_table("sermones"):
        op.create_table(
            "sermones",
            sa.Column("id", postgresql.UUID(as_uuid=True) if is_pg else sa.String(36), primary_key=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("preacher", sa.String(255), nullable=True),
            sa.Column("passage", sa.String(255), nullable=True),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("series", sa.String(255), nullable=True),
            sa.Column("category", sa.String(100), nullable=True, server_default="sermon"),
            sa.Column("date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("video_url", sa.String(500), nullable=True),
            sa.Column("audio_url", sa.String(500), nullable=True),
            sa.Column("is_published", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("sede_id", postgresql.UUID(as_uuid=True) if is_pg else sa.String(36), sa.ForeignKey("sedes.id"), nullable=True),
            sa.Column("author_id", postgresql.UUID(as_uuid=True) if is_pg else sa.String(36), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_sermones_category", "sermones", ["category"])
        op.create_index("ix_sermones_sede_id", "sermones", ["sede_id"])
        op.create_index("ix_sermones_is_published", "sermones", ["is_published"])
        op.create_index("ix_sermones_is_active", "sermones", ["is_active"])

    # Add embedding column to sermones
    if not _has_column("sermones", "embedding"):
        if is_pg:
            op.execute(sa.text("ALTER TABLE sermones ADD COLUMN embedding vector(1536);"))
        else:
            op.add_column("sermones", sa.Column("embedding", sa.JSON(), nullable=True))

    # 5. Add embedding to agent_knowledge_base if present
    if _has_table("agent_knowledge_base") and not _has_column("agent_knowledge_base", "embedding"):
        if is_pg:
            op.execute(sa.text("ALTER TABLE agent_knowledge_base ADD COLUMN embedding vector(1536);"))
        else:
            op.add_column("agent_knowledge_base", sa.Column("embedding", sa.JSON(), nullable=True))

    # 6. PostgreSQL HNSW indexes and Row-Level Security (RLS) policies
    if is_pg:
        # HNSW indexes for cosine distance
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_kba_embedding_hnsw ON knowledge_base_articles USING hnsw (embedding vector_cosine_ops);"))
        if _has_table("wiki_pages"):
            op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_wiki_embedding_hnsw ON wiki_pages USING hnsw (embedding vector_cosine_ops);"))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_sermones_embedding_hnsw ON sermones USING hnsw (embedding vector_cosine_ops);"))

        # Enable RLS
        op.execute(sa.text("ALTER TABLE knowledge_base_articles ENABLE ROW LEVEL SECURITY;"))
        if _has_table("wiki_pages"):
            op.execute(sa.text("ALTER TABLE wiki_pages ENABLE ROW LEVEL SECURITY;"))
        op.execute(sa.text("ALTER TABLE sermones ENABLE ROW LEVEL SECURITY;"))

        # RLS Policies with sede_id isolation and superadmin / admin bypass
        op.execute(sa.text("DROP POLICY IF EXISTS rls_kba_tenant_isolation ON knowledge_base_articles;"))
        op.execute(sa.text("""
            CREATE POLICY rls_kba_tenant_isolation ON knowledge_base_articles
            FOR ALL
            USING (
                current_setting('app.current_user_role', true) IN ('ADMIN', 'SUPERADMIN', 'admin', 'superadmin')
                OR sede_id IS NULL
                OR sede_id::text = current_setting('app.current_sede_id', true)
            );
        """))

        if _has_table("wiki_pages"):
            op.execute(sa.text("DROP POLICY IF EXISTS rls_wiki_tenant_isolation ON wiki_pages;"))
            op.execute(sa.text("""
                CREATE POLICY rls_wiki_tenant_isolation ON wiki_pages
                FOR ALL
                USING (
                    current_setting('app.current_user_role', true) IN ('ADMIN', 'SUPERADMIN', 'admin', 'superadmin')
                    OR sede_id IS NULL
                    OR sede_id::text = current_setting('app.current_sede_id', true)
                );
            """))

        op.execute(sa.text("DROP POLICY IF EXISTS rls_sermones_tenant_isolation ON sermones;"))
        op.execute(sa.text("""
            CREATE POLICY rls_sermones_tenant_isolation ON sermones
            FOR ALL
            USING (
                current_setting('app.current_user_role', true) IN ('ADMIN', 'SUPERADMIN', 'admin', 'superadmin')
                OR sede_id IS NULL
                OR sede_id::text = current_setting('app.current_sede_id', true)
            );
        """))


def downgrade() -> None:
    is_pg = _is_postgres()
    if is_pg:
        op.execute(sa.text("DROP POLICY IF EXISTS rls_kba_tenant_isolation ON knowledge_base_articles;"))
        op.execute(sa.text("DROP POLICY IF EXISTS rls_wiki_tenant_isolation ON wiki_pages;"))
        op.execute(sa.text("DROP POLICY IF EXISTS rls_sermones_tenant_isolation ON sermones;"))

        op.execute(sa.text("ALTER TABLE knowledge_base_articles DISABLE ROW LEVEL SECURITY;"))
        if _has_table("wiki_pages"):
            op.execute(sa.text("ALTER TABLE wiki_pages DISABLE ROW LEVEL SECURITY;"))
        op.execute(sa.text("ALTER TABLE sermones DISABLE ROW LEVEL SECURITY;"))

        op.execute(sa.text("DROP INDEX IF EXISTS ix_kba_embedding_hnsw;"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_wiki_embedding_hnsw;"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_sermones_embedding_hnsw;"))

    if _has_column("sermones", "embedding"):
        op.drop_column("sermones", "embedding")
    if _has_column("wiki_pages", "embedding"):
        op.drop_column("wiki_pages", "embedding")
    if _has_column("knowledge_base_articles", "embedding"):
        op.drop_column("knowledge_base_articles", "embedding")
