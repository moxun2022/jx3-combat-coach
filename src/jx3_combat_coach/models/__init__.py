"""Shared contracts; raw evidence remains separate from semantic interpretation."""
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RawEvent(Model):
    event_id: str
    line_number: int
    raw_line: str
    crc: int
    logic_frame: int
    unix_seconds: int
    client_ms: int
    event_code: int
    payload: dict[str, Any]


class ParseError(Model):
    line_number: int
    raw_hex: str
    message: str


class ParseResult(Model):
    source_sha256: str
    encoding: str
    raw_hex: str
    crc_verified: bool = False
    events: list[RawEvent] = Field(default_factory=list)
    errors: list[ParseError] = Field(default_factory=list)


class EventKind(str, Enum):
    UNKNOWN = "unknown"
    PLAYER_INFO = "player_info"
    HEALTH = "health"
    CAST = "cast"
    DEATH = "death"


class Event(Model):
    event_id: str
    raw_event_id: str
    sequence: int
    timestamp_ms: int
    kind: EventKind
    actor_id: str | None = None
    target_id: str | None = None
    skill_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Certainty(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class StateValue(Model):
    value: Any = None
    certainty: Certainty = Certainty.UNKNOWN
    evidence_event_ids: list[str] = Field(default_factory=list)
    as_of_ms: int | None = None


class PlayerState(Model):
    player_id: str
    name: StateValue = Field(default_factory=StateValue)
    health: StateValue = Field(default_factory=StateValue)
    alive: StateValue = Field(default_factory=StateValue)


class BattleState(Model):
    players: dict[str, PlayerState] = Field(default_factory=dict)
    last_sequence: int = 0


class Finding(Model):
    rule_id: str
    summary: str
    severity: str = "info"
    certainty: Certainty
    evidence_event_ids: list[str] = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)


class Analysis(Model):
    parsed: ParseResult
    events: list[Event]
    state: BattleState
    findings: list[Finding]
