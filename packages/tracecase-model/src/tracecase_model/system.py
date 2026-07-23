from __future__ import annotations

from enum import StrEnum

from pydantic import Field, JsonValue, model_validator

from .base import TracecaseModel
from .types import CanonicalId, Namespace, SensitivityLabel


class ComponentKind(StrEnum):
    CLIENT = "client"
    FRONTEND = "frontend"
    API = "api"
    SERVICE = "service"
    WORKER = "worker"
    SCHEDULER = "scheduler"
    DATABASE = "database"
    CACHE = "cache"
    BROKER = "broker"
    EXTERNAL_SERVICE = "external_service"
    FILESYSTEM = "filesystem"
    OBJECT_STORE = "object_store"
    IDENTITY_PROVIDER = "identity_provider"
    UNKNOWN = "unknown"


class BoundaryKind(StrEnum):
    FUNCTION_CALL = "function_call"
    PROCESS = "process"
    THREAD = "thread"
    NETWORK = "network"
    HTTP = "http"
    RPC = "rpc"
    MESSAGE_PUBLISH = "message_publish"
    MESSAGE_CONSUME = "message_consume"
    DATABASE = "database"
    TRANSACTION = "transaction"
    CACHE = "cache"
    FILESYSTEM = "filesystem"
    EXTERNAL_DEPENDENCY = "external_dependency"
    TRUST = "trust"
    TENANT = "tenant"
    DEPLOYMENT_VERSION = "deployment_version"
    HUMAN = "human"
    UNKNOWN = "unknown"


class Component(TracecaseModel):
    component_id: CanonicalId
    name: str
    kind: ComponentKind
    role: str | None = None
    version: str | None = None
    environment: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class Boundary(TracecaseModel):
    boundary_id: CanonicalId
    kind: BoundaryKind
    source_component_ref: CanonicalId
    target_component_ref: CanonicalId
    name: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class Resource(TracecaseModel):
    resource_id: CanonicalId
    kind: str
    name: str
    owner_component_ref: CanonicalId | None = None
    sensitivity: set[SensitivityLabel] = Field(default_factory=set)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class SystemModel(TracecaseModel):
    system_id: CanonicalId
    name: str
    components: tuple[Component, ...] = ()
    boundaries: tuple[Boundary, ...] = ()
    resources: tuple[Resource, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def references_must_resolve(self) -> "SystemModel":
        component_ids = {item.component_id for item in self.components}
        if len(component_ids) != len(self.components):
            raise ValueError("component IDs must be unique")

        boundary_ids = {item.boundary_id for item in self.boundaries}
        if len(boundary_ids) != len(self.boundaries):
            raise ValueError("boundary IDs must be unique")

        resource_ids = {item.resource_id for item in self.resources}
        if len(resource_ids) != len(self.resources):
            raise ValueError("resource IDs must be unique")

        for boundary in self.boundaries:
            if boundary.source_component_ref not in component_ids:
                raise ValueError(f"unknown boundary source: {boundary.source_component_ref}")
            if boundary.target_component_ref not in component_ids:
                raise ValueError(f"unknown boundary target: {boundary.target_component_ref}")

        for resource in self.resources:
            if resource.owner_component_ref and resource.owner_component_ref not in component_ids:
                raise ValueError(f"unknown resource owner: {resource.owner_component_ref}")
        return self
