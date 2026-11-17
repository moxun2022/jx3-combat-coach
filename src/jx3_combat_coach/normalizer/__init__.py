"""Conservative projection of documented event fields; raw records stay intact."""
from typing import Protocol
from jx3_combat_coach.models import Event, EventKind, RawEvent


class Normalizer(Protocol):
    def normalize(self, records: list[RawEvent]) -> list[Event]: ...


def identifier(value) -> str | None:
    return str(value) if type(value) is int and value >= 0 else None


class JCLNormalizer:
    def normalize(self, records: list[RawEvent]) -> list[Event]:
        events = []
        for raw in records:
            fields = {k: v for k, v in raw.payload["$table"] if type(k) is int}
            event = Event(event_id=raw.event_id, raw_event_id=raw.event_id,
                          sequence=raw.line_number, timestamp_ms=raw.client_ms, kind=EventKind.UNKNOWN)
            actor = identifier(fields.get(1))
            if raw.event_code == 4 and actor is not None:
                event.kind, event.actor_id = EventKind.PLAYER_INFO, actor
                if isinstance(fields.get(2), str):
                    event.attributes["name"] = fields[2]
            elif raw.event_code == 5 and actor is not None:
                event.kind, event.target_id = EventKind.HEALTH, actor
                health = fields.get(3)
                if type(health) in (int, float) and health >= 0:
                    event.attributes["health"] = health
            elif raw.event_code == 19 and actor is not None:
                event.kind, event.actor_id = EventKind.CAST, actor
                event.skill_id = identifier(fields.get(2))
            elif raw.event_code == 28 and actor is not None:
                event.kind, event.target_id = EventKind.DEATH, actor
                event.actor_id = identifier(fields.get(2))
            events.append(event)
        return events
