from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def normalize_payload(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return {str(key): normalize_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_payload(item) for item in value]
    if isinstance(value, set):
        return sorted(normalize_payload(item) for item in value)
    if isinstance(value, Enum):
        return normalize_payload(value.value)
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Path):
        return value.as_posix()
    return value


def canonical_json_text(value: Any) -> str:
    return json.dumps(
        normalize_payload(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"


def canonical_json_bytes(value: Any) -> bytes:
    return canonical_json_text(value).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
