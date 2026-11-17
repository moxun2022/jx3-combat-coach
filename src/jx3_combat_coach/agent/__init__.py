"""Tool-calling contracts only; no model provider, network call or LangGraph yet."""
from typing import Any, Protocol
from pydantic import Field
from jx3_combat_coach.models import Model


class ToolDefinition(Model):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class ToolCall(Model):
    call_id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(Model):
    call_id: str
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    evidence_event_ids: list[str] = Field(default_factory=list)


class CombatTool(Protocol):
    definition: ToolDefinition
    def invoke(self, call: ToolCall) -> ToolResult: ...
