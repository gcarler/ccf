from backend.core.config import get_settings


def is_enabled(flag: str, default: bool = False) -> bool:
    settings = get_settings()
    return bool(settings.feature_flags.get(flag, default))
