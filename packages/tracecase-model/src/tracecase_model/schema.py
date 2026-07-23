from __future__ import annotations

from datetime import datetime, timezone
from typing import TypeAlias

from pydantic import Field, JsonValue

from .base import TracecaseModel
from .case import ExecutionCase
from .execution import (
    ContextField,
    Effect,
    ExecutionIdentitySet,
    ExecutionModel,
    ExecutionNode,
    ExecutionRelation,
    Observation,
    StateFact,
)
from .system import Boundary, Component, Resource, SystemModel

ModelClass: TypeAlias = type[TracecaseModel]


class SchemaCatalogEntry(TracecaseModel):
    schema_id: str
    version: str
    model_name: str
    schema_document: dict[str, JsonValue] = Field(alias="schema")


class SchemaCatalog(TracecaseModel):
    catalog_id: str
    catalog_version: str
    generated_at: datetime
    entries: tuple[SchemaCatalogEntry, ...]
    reserved_namespaces: tuple[str, ...] = ("tracecase.core",)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


def build_core_schema_catalog() -> SchemaCatalog:
    models: tuple[ModelClass, ...] = (
        Component,
        Boundary,
        Resource,
        SystemModel,
        ExecutionIdentitySet,
        ContextField,
        Observation,
        StateFact,
        Effect,
        ExecutionNode,
        ExecutionRelation,
        ExecutionModel,
        ExecutionCase,
    )
    entries = tuple(
        SchemaCatalogEntry(
            schema_id=f"tracecase.core.{model.__name__}",
            version="1.0.0",
            model_name=model.__name__,
            schema_document=model.model_json_schema(mode="serialization"),
        )
        for model in models
    )
    return SchemaCatalog(
        catalog_id="tracecase.core.catalog",
        catalog_version="1.0.0",
        generated_at=datetime.now(timezone.utc),
        entries=entries,
    )
