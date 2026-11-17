from jx3_combat_coach.models import Analysis
from jx3_combat_coach.parser import JCLParser
from jx3_combat_coach.normalizer import JCLNormalizer
from jx3_combat_coach.state import BattleStateEngine
from jx3_combat_coach.rules import DeathObservedRule, RuleEngine


def analyze(data: bytes, encoding: str = "utf-8-sig") -> Analysis:
    parsed = JCLParser().parse(data, encoding)
    events = JCLNormalizer().normalize(parsed.events)
    state = BattleStateEngine().rebuild(events)
    rules = RuleEngine()
    rules.register(DeathObservedRule())
    return Analysis(parsed=parsed, events=events, state=state, findings=rules.run(events, state))
