from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, default=str, separators=(",", ":"))


def loads(data: str | None) -> dict[str, Any]:
    if not data:
        return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {}


def duration_seconds(start: datetime | None, end: datetime | None) -> float | None:
    if not start or not end:
        return None
    return round((end - start).total_seconds(), 2)
