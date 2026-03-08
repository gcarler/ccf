from backend.core import feature_flags
from backend.core.config import get_settings


def test_feature_flag_toggle():
    settings = get_settings()
    previous = dict(settings.feature_flags)
    try:
        settings.feature_flags = {"diagnostics": True}
        assert feature_flags.is_enabled("diagnostics") is True
        assert feature_flags.is_enabled("unknown", default=True) is True
        settings.feature_flags["diagnostics"] = False
        assert feature_flags.is_enabled("diagnostics") is False
    finally:
        settings.feature_flags = previous
