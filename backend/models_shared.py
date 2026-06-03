from __future__ import annotations

import datetime as dt




def _utcnow() -> dt.datetime:
    """Return timezone-aware UTC now. Use this for all DateTime columns."""
    return dt.datetime.now(dt.timezone.utc)
