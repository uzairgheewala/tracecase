from __future__ import annotations

from collections.abc import Iterable

from .base import SourceAdapter
from .models import (
    AdapterDiagnostic,
    CollectionFragment,
    CollectionRequest,
    CollectionResult,
    DiagnosticSeverity,
)
from .utils import stable_id


class CollectionCoordinator:
    def __init__(self, adapters: Iterable[SourceAdapter]) -> None:
        self.adapters = tuple(adapters)
        adapter_ids = [adapter.adapter_id for adapter in self.adapters]
        if len(set(adapter_ids)) != len(adapter_ids):
            raise ValueError("adapter IDs must be unique")

    def collect(self, request: CollectionRequest) -> CollectionResult:
        fragments: list[CollectionFragment] = []
        diagnostics: list[AdapterDiagnostic] = []
        adapter_status: dict[str, str] = {}
        partial = False
        for adapter in self.adapters:
            try:
                candidates = adapter.discover(request)
                records = adapter.collect(request, candidates)
                fragment = adapter.normalize(request, records)
                self._enforce_tenant_scope(request, fragment)
                fragments.append(fragment)
                diagnostics.extend(fragment.diagnostics)
                adapter_status[adapter.adapter_id] = "complete"
            except Exception as exc:
                partial = True
                adapter_status[adapter.adapter_id] = "failed"
                diagnostics.append(
                    AdapterDiagnostic(
                        diagnostic_id=stable_id("diagnostic.collection", adapter.adapter_id, type(exc).__name__, str(exc)),
                        adapter_id=adapter.adapter_id,
                        severity=DiagnosticSeverity.ERROR,
                        code="adapter_failed",
                        message=str(exc),
                        details={"exception_type": type(exc).__name__},
                    )
                )
        merged, merge_diagnostics = self._merge(request, fragments)
        diagnostics.extend(merge_diagnostics)
        partial = partial or any(item.severity is DiagnosticSeverity.ERROR for item in diagnostics)
        return CollectionResult(
            request=request,
            fragments=tuple(fragments),
            merged=merged,
            diagnostics=tuple(diagnostics),
            partial=partial,
            adapter_status=adapter_status,
            attributes={
                "adapter_count": len(self.adapters),
                "successful_adapter_count": len(fragments),
            },
        )

    @staticmethod
    def _enforce_tenant_scope(request: CollectionRequest, fragment: CollectionFragment) -> None:
        if not request.tenant_scope:
            return
        violating = sorted(
            {
                node.identities.tenant_id
                for node in fragment.nodes
                if node.identities.tenant_id
                and node.identities.tenant_id != request.tenant_scope
            }
        )
        if violating:
            raise ValueError(
                f"adapter {fragment.adapter_id} returned evidence outside tenant scope "
                f"{request.tenant_scope!r}: {violating}"
            )

    @staticmethod
    def _merge(
        request: CollectionRequest,
        fragments: list[CollectionFragment],
    ) -> tuple[CollectionFragment, tuple[AdapterDiagnostic, ...]]:
        diagnostics: list[AdapterDiagnostic] = []

        def merge_unique(attribute: str, id_attribute: str):
            merged: dict[str, object] = {}
            for fragment in fragments:
                for item in getattr(fragment, attribute):
                    item_id = getattr(item, id_attribute)
                    previous = merged.get(item_id)
                    if previous is None:
                        merged[item_id] = item
                    elif previous != item:
                        diagnostics.append(
                            AdapterDiagnostic(
                                diagnostic_id=stable_id("diagnostic.merge", attribute, item_id),
                                adapter_id="adapter.collection-coordinator",
                                severity=DiagnosticSeverity.ERROR,
                                code="canonical_id_collision",
                                message=f"Conflicting {attribute} records share ID {item_id}",
                                details={"category": attribute, "canonical_id": item_id},
                            )
                        )
            return tuple(merged[key] for key in sorted(merged))

        merged = CollectionFragment(
            fragment_id=stable_id("fragment.merged", request.request_id, *(item.fragment_id for item in fragments)),
            adapter_id="adapter.collection-coordinator",
            sources=merge_unique("sources", "source_id"),
            components=merge_unique("components", "component_id"),
            boundaries=merge_unique("boundaries", "boundary_id"),
            resources=merge_unique("resources", "resource_id"),
            nodes=merge_unique("nodes", "node_id"),
            relations=merge_unique("relations", "relation_id"),
            contexts=merge_unique("contexts", "context_id"),
            state_facts=merge_unique("state_facts", "fact_id"),
            effects=merge_unique("effects", "effect_id"),
            observations=merge_unique("observations", "observation_id"),
            diagnostics=tuple(diagnostics),
            extensions={
                "tracecase.collection": {
                    "fragment_refs": [item.fragment_id for item in fragments],
                }
            },
        )
        return merged, tuple(diagnostics)
