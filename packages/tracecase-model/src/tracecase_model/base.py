from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class TracecaseModel(BaseModel):
    """Immutable base model used by all canonical Tracecase contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        validate_default=True,
        str_strip_whitespace=True,
    )

    def canonical_payload(self, *, exclude_none: bool = True) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=exclude_none)
