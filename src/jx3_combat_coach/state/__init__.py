"""Replay in source order; values are last observations, not continuous truth."""
from jx3_combat_coach.models import BattleState, Certainty, Event, EventKind, PlayerState, StateValue


class BattleStateEngine:
    def rebuild(self, events: list[Event], through_sequence: int | None = None) -> BattleState:
        state = BattleState()
        for event in sorted(events, key=lambda e: e.sequence):
            if through_sequence is not None and event.sequence > through_sequence:
                break
            if event.sequence <= state.last_sequence:
                raise ValueError("event sequence must be unique and positive")
            state.last_sequence = event.sequence
            player_id = event.target_id if event.kind in (EventKind.HEALTH, EventKind.DEATH) else event.actor_id
            if player_id is None or event.kind == EventKind.UNKNOWN:
                continue
            player = state.players.setdefault(player_id, PlayerState(player_id=player_id))
            def value(data, certainty=Certainty.OBSERVED):
                return StateValue(value=data, certainty=certainty,
                                  evidence_event_ids=[event.event_id], as_of_ms=event.timestamp_ms)
            if event.kind == EventKind.PLAYER_INFO and "name" in event.attributes:
                player.name = value(event.attributes["name"])
            elif event.kind == EventKind.HEALTH and "health" in event.attributes:
                player.health = value(event.attributes["health"])
                player.alive = value(event.attributes["health"] > 0, Certainty.INFERRED)
            elif event.kind == EventKind.DEATH:
                player.alive = value(False)
                player.health = StateValue()  # A death record does not measure HP.
        return state
