from __future__ import annotations

from pydantic import ConfigDict

orm_config: ConfigDict = ConfigDict(from_attributes=True)
