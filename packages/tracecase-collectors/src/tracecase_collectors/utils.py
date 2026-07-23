from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any


def stable_id(prefix: str, *parts: object, length: int = 16) -> str:
    payload = "\x1f".join(str(item) for item in parts)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:length]
    clean_prefix = re.sub(r"[^a-z0-9._:-]+", "-", prefix.lower()).strip("-.")
    return f"{clean_prefix}.{digest}"


def parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        if value > 10_000_000_000_000:
            return datetime.fromtimestamp(float(value) / 1_000_000_000, tz=timezone.utc)
        if value > 10_000_000_000:
            return datetime.fromtimestamp(float(value) / 1_000, tz=timezone.utc)
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            return parse_timestamp(int(value))
        text = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    raise ValueError(f"unsupported timestamp: {value!r}")
