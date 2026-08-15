"""CMS CRUD package — split from monolithic cms.py.

All public names are re-exported here for backward compatibility.
External callers continue using `from backend.crud.cms import name`.
"""

from __future__ import annotations

from backend.crud.cms._shared import (
    _actor_sede_or_none_cms,
    _commit_or_conflict,
    _crud_scope_re_check_cms_content_create,
    _crud_scope_re_check_cms_content_update,
    _crud_scope_re_check_cms_site_content,
    _crud_scope_re_check_pastoral_profile,
    _now_utc,
    _resolve_persona_sede,
    _resolve_site_sede,
)
from backend.crud.cms.ab_tests import (
    apply_cms_ab_test_winner,
    create_cms_ab_test,
    delete_cms_ab_test,
    get_cms_ab_test,
    get_cms_ab_test_by_id,
    get_cms_ab_test_results,
    list_cms_ab_tests,
    record_cms_ab_test_event,
    update_cms_ab_test,
)
from backend.crud.cms.cleanup import (
    cleanup_old_publish_logs,
)
from backend.crud.cms.forms import (
    create_cms_form,
    create_cms_form_submission,
    delete_cms_form,
    get_cms_form,
    get_cms_form_by_id,
    list_cms_form_submissions,
    list_cms_forms,
    update_cms_form,
)
from backend.crud.cms.media import (
    _apply_cleanup_orphan_cms_media,
    cleanup_orphan_cms_media,
    cleanup_orphan_cms_media_scheduled,
    create_cms_media_item,
    delete_cms_media_item,
    get_cms_media_item,
    list_cms_media_items,
    update_cms_media_item,
)
from backend.crud.cms.newsletters import (
    create_cms_newsletter,
    create_cms_subscriber,
    delete_cms_newsletter,
    delete_cms_subscriber,
    get_cms_newsletter,
    get_cms_subscriber,
    import_cms_subscribers,
    list_cms_newsletters,
    list_cms_subscribers,
    public_subscribe,
    public_unsubscribe,
    send_cms_newsletter,
    update_cms_newsletter,
    update_cms_subscriber,
)
from backend.crud.cms.pages import (
    _build_page_snapshot,
    archive_cms_section,
    clone_cms_page,
    create_cms_page,
    create_cms_page_version,
    create_cms_section,
    delete_cms_page,
    delete_cms_section,
    get_cms_page,
    get_cms_page_version,
    get_cms_section,
    get_public_cms_page,
    list_cms_page_versions,
    list_cms_pages,
    list_cms_publish_logs,
    list_cms_sections,
    reorder_cms_sections,
    restore_cms_page_version,
    transition_cms_page_status,
    update_cms_page,
    update_cms_section,
)
from backend.crud.cms.pastoral import (
    list_pastoral_team,
    update_pastoral_profile,
)
from backend.crud.cms.popups import (
    create_cms_popup,
    delete_cms_popup,
    get_cms_popup,
    list_cms_popups,
    update_cms_popup,
)
from backend.crud.cms.posts import (
    _assert_post_published_before_expires,
    _set_post_categories,
    _set_post_tags,
    create_cms_post,
    delete_cms_post,
    get_cms_post,
    get_cms_post_by_id,
    get_cms_post_by_slug_and_category,
    get_post_categories,
    get_post_tags,
    get_posts_categories_batch,
    get_posts_tags_batch,
    get_public_cms_post,
    get_public_cms_posts,
    list_cms_posts,
    list_cms_posts_by_category,
    update_cms_post,
)
from backend.crud.cms.scheduling import (
    _archive_post_with_audit,
    capture_daily_seo_snapshots,
    find_pages_due_for_archive,
    find_pages_due_for_publish,
    find_posts_due_for_archive,
    get_seo_trend,
    list_seo_snapshots,
    process_due_content,
)
from backend.crud.cms.sites import (
    activate_cms_theme,
    archive_cms_site,
    archive_cms_theme,
    create_cms_menu,
    create_cms_menu_item,
    create_cms_site,
    create_cms_theme,
    delete_cms_menu,
    delete_cms_menu_item,
    get_active_cms_theme,
    get_cms_menu,
    get_cms_menu_item,
    get_cms_site_by_key,
    get_cms_theme,
    list_cms_menu_items,
    list_cms_menus,
    list_cms_sites,
    list_cms_themes,
    reorder_cms_menu_items,
    update_cms_menu,
    update_cms_menu_item,
    update_cms_site,
    update_cms_theme,
)
from backend.crud.cms.taxonomy import (
    _assert_canonical_category_unchanged,
    _assert_parent_category_same_site,
    create_cms_category,
    create_cms_tag,
    delete_cms_category,
    delete_cms_tag,
    get_cms_category,
    get_cms_tag,
    get_or_create_canonical_category,
    list_cms_categories,
    list_cms_tags,
    update_cms_category,
    update_cms_tag,
)
from backend.crud.cms.ugc import (
    create_announcement,
    create_testimonial,
    delete_announcement,
    delete_testimonial,
    get_announcement,
    get_testimonial,
    list_announcements,
    list_testimonials,
    update_announcement,
    update_testimonial,
)

