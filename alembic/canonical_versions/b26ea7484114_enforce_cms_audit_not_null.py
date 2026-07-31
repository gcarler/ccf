"""enforce_cms_audit_not_null

Revision ID: b26ea7484114
Revises: 575eec15ec67
Create Date: 2026-07-31 13:55:08.607152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b26ea7484114'
down_revision: Union[str, None] = '575eec15ec67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cms_tables_both = [
        "cms_categories", "cms_forms", "cms_media_items", "cms_menus", 
        "cms_menu_items", "cms_newsletters", "cms_pages", "cms_popups", 
        "cms_posts", "cms_post_comments", "cms_sections", "cms_section_types", 
        "cms_sites", "cms_tags", "cms_themes"
    ]
    cms_tables_created_only = [
        "cms_ab_tests", "cms_ab_test_events", "cms_page_versions", 
        "cms_page_views", "cms_publish_logs"
    ]
    
    for table in cms_tables_both + cms_tables_created_only:
        op.execute(f"UPDATE {table} SET created_at = NOW() WHERE created_at IS NULL")
        op.alter_column(table, 'created_at', existing_type=sa.DateTime(timezone=True), nullable=False)
        
    for table in cms_tables_both:
        op.execute(f"UPDATE {table} SET updated_at = NOW() WHERE updated_at IS NULL")
        op.alter_column(table, 'updated_at', existing_type=sa.DateTime(timezone=True), nullable=False)


def downgrade() -> None:
    pass
