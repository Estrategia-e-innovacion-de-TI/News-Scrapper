"""Simple capability registry with metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class CapabilityDef:
    """Capability definition with contract."""
    name: str
    purpose: str
    inputs_schema: dict[str, str]
    outputs_schema: dict[str, str]
    callable: Callable[..., Any]
    version: str = "1.0"
    tags: list[str] = field(default_factory=list)


# Global registry
CAPABILITY_REGISTRY: dict[str, CapabilityDef] = {}


def register_capability(cap: CapabilityDef) -> None:
    """Register a capability in the global registry."""
    CAPABILITY_REGISTRY[cap.name] = cap


def get_capability(name: str) -> CapabilityDef | None:
    """Get a capability by name."""
    return CAPABILITY_REGISTRY.get(name)


def list_capabilities() -> list[CapabilityDef]:
    """List all registered capabilities."""
    return list(CAPABILITY_REGISTRY.values())
