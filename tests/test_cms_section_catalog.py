"""Regression tests for the shared CMS section-type fallback catalog."""

from backend.api.cms.section_catalog import FALLBACK_SECTION_TYPES
from backend.api.cms.section_types import get_allowed_section_types as get_v1_types
from backend.api.cms_v2.section_types import get_allowed_section_types as get_v2_types
from scripts.seed_cms_section_types import EXPECTED_SECTION_TYPES


class _BrokenSession:
    def query(self, *_args, **_kwargs):
        raise RuntimeError("catalog unavailable")


def test_v1_and_v2_share_the_same_complete_fallback():
    expected_m1_types = {
        "animated_counter",
        "video_embed",
        "gallery_masonry",
        "map_embed",
    }

    assert expected_m1_types <= FALLBACK_SECTION_TYPES
    assert {name for name, _ in EXPECTED_SECTION_TYPES} == FALLBACK_SECTION_TYPES
    assert get_v1_types(_BrokenSession()) == set(FALLBACK_SECTION_TYPES)
    assert get_v2_types(_BrokenSession()) == set(FALLBACK_SECTION_TYPES)
    assert get_v1_types(_BrokenSession()) == get_v2_types(_BrokenSession())
