"""Versioned skill semantics supplied only from verified external knowledge."""
from pydantic import Field
from jx3_combat_coach.models import Model


class SkillSemantics(Model):
    skill_id: str
    game_version: str
    name: str
    source: str
    verified: bool = False
    tags: set[str] = Field(default_factory=set)
    cooldown_ms: int | None = Field(default=None, ge=0)


class SkillDictionary:
    def __init__(self, entries: list[SkillSemantics] | None = None):
        self._entries: dict[tuple[str, str], SkillSemantics] = {}
        for entry in entries or []:
            key = (entry.game_version, entry.skill_id)
            if key in self._entries:
                raise ValueError("duplicate versioned skill")
            self._entries[key] = entry

    def get(self, game_version: str, skill_id: str) -> SkillSemantics | None:
        return self._entries.get((game_version, skill_id))
