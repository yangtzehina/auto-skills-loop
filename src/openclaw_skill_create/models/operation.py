from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OperationInputSpec(BaseModel):
    name: str
    kind: str = "string"
    required: bool = False
    source: str = "arg"
    description: str = ""


class OperationSpec(BaseModel):
    name: str
    summary: str = ""
    inputs: list[OperationInputSpec] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    error_modes: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class OperationGroup(BaseModel):
    name: str
    description: str = ""
    operations: list[OperationSpec] = Field(default_factory=list)


class SafetyProfile(BaseModel):
    credential_scope: list[str] = Field(default_factory=list)
    network_scope: list[str] = Field(default_factory=list)
    filesystem_scope: list[str] = Field(default_factory=list)
    external_process_usage: list[str] = Field(default_factory=list)
    confirmation_required: bool = False


class OperationContract(BaseModel):
    name: str
    backend_kind: str = "python_backend"
    supports_json: bool = False
    session_model: str = "stateless"
    mutability: str = "read_only"
    operations: list[OperationGroup] = Field(default_factory=list)
    safety_profile: SafetyProfile = Field(default_factory=SafetyProfile)
    entrypoint_hint: Optional[str] = None
    install_prerequisites: list[str] = Field(default_factory=list)
    runtime_dependencies: list[str] = Field(default_factory=list)
