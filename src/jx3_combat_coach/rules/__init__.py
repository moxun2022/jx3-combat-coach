"""Deterministic registry with evidence validation; no speculative PvP mechanics."""
from typing import Protocol
from jx3_combat_coach.models import BattleState, Certainty, Event, EventKind, Finding


class Rule(Protocol):
    rule_id: str
    def evaluate(self, events: list[Event], state: BattleState) -> list[Finding]: ...


class RuleEngine:
    def __init__(self):
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if rule.rule_id in self._rules:
            raise ValueError(f"duplicate rule: {rule.rule_id}")
        self._rules[rule.rule_id] = rule

    def run(self, events: list[Event], state: BattleState) -> list[Finding]:
        known = {event.event_id for event in events}
        findings = []
        for rule in self._rules.values():
            for finding in rule.evaluate(events, state):
                if finding.rule_id != rule.rule_id or not set(finding.evidence_event_ids) <= known:
                    raise ValueError("finding has invalid rule or evidence references")
                findings.append(finding)
        return findings


class DeathObservedRule:
    rule_id = "death_observed"

    def evaluate(self, events: list[Event], state: BattleState) -> list[Finding]:
        return [Finding(rule_id=self.rule_id, summary="日志记录死亡；原因尚未推导。",
                        certainty=Certainty.OBSERVED, evidence_event_ids=[e.event_id],
                        details={"target_id": e.target_id, "killer_id": e.actor_id})
                for e in events if e.kind == EventKind.DEATH]
