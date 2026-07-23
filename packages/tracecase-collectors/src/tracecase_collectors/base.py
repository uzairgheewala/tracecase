from __future__ import annotations

from typing import Protocol, runtime_checkable

from tracecase_model.types import CanonicalId

from .models import CandidateRecord, CollectionFragment, CollectionRequest, RawRecord


@runtime_checkable
class SourceAdapter(Protocol):
    adapter_id: CanonicalId

    def discover(self, request: CollectionRequest) -> tuple[CandidateRecord, ...]: ...

    def collect(
        self,
        request: CollectionRequest,
        candidates: tuple[CandidateRecord, ...],
    ) -> tuple[RawRecord, ...]: ...

    def normalize(
        self,
        request: CollectionRequest,
        records: tuple[RawRecord, ...],
    ) -> CollectionFragment: ...
