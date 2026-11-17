import pytest
from jx3_combat_coach.models import Certainty, EventKind, Finding
from jx3_combat_coach.parser import JCLParser
from jx3_combat_coach.parser.lua import LuaReader
from jx3_combat_coach.service import analyze
from jx3_combat_coach.state import BattleStateEngine
from jx3_combat_coach.rules import RuleEngine, DeathObservedRule
from jx3_combat_coach.knowledge import SkillDictionary, SkillSemantics
from jx3_combat_coach.agent import ToolCall, ToolResult


def row(code, payload, time=1000):
    return f'0\t100\t1700000000\t{time}\t{code}\t{payload}\n'


def test_sparse_keys_unknown_and_lossless_input():
    raw = row(999, '{1,[8]="中文",[0]=false,["1"]=nil,[8]="last",{}}').encode()
    result = JCLParser().parse(raw)
    assert not result.errors
    assert bytes.fromhex(result.raw_hex) == raw
    assert result.events[0].payload['$table'] == [[1, 1], [8, '中文'], [0, False], ['1', None], [8, 'last'], [2, {'$table': []}]]
    assert result.events[0].client_ms == 1000
    assert result.events[0].unix_seconds == 1700000000
    assert not result.crc_verified
    assert analyze(raw).events[0].kind == EventKind.UNKNOWN
    assert result.events[0].event_id == JCLParser().parse(raw).events[0].event_id


@pytest.mark.parametrize('payload', ['{', '{1 2}', '{os.execute("bad")}', '{[nil]=1}', '{} trailing', '{"\\q"}', '{1e999}', '{"unterminated}', '{' * 70 + '}' * 70])
def test_invalid_lua_recovery(payload):
    parsed = JCLParser().parse((row(4, payload) + row(28, '{2}')).encode())
    assert parsed.errors[0].line_number == 1
    assert parsed.errors[0].raw_hex
    assert len(parsed.events) == 1
    assert parsed.events[0].line_number == 2


@pytest.mark.parametrize('encoding', ['utf-8-sig', 'gbk', 'gb18030'])
def test_encodings_and_crlf(encoding):
    parsed = JCLParser().parse(row(4, '{1,"角色"}').replace('\n', '\r\n').encode(encoding), encoding)
    assert not parsed.errors
    assert parsed.events[0].payload['$table'][1][1] == '角色'


def test_errors_and_empty_input():
    parsed = JCLParser().parse(b'\xff\n\n' + row(28, '{2}').encode())
    assert [e.line_number for e in parsed.errors] == [1, 2]
    assert len(parsed.events) == 1
    assert not JCLParser().parse(b'').events
    with pytest.raises(ValueError):
        JCLParser().parse(b'', 'utf-16')


def test_string_escapes():
    assert LuaReader(r'{"a,{}=\n\"\\",nil,false,0,"",{}}', 'utf-8').parse()['$table'][0][1] == 'a,{}=\n"\\'
    assert LuaReader(r'{"\228\184\173"}', 'utf-8').parse()['$table'][0][1] == '中'


def test_state_evidence_and_historical_replay():
    result = analyze((row(4, '{1,"甲"}') + row(4, '{1}') + row(5, '{1,true,90}', 1100) + row(28, '{1}', 1200)).encode())
    engine = BattleStateEngine()
    initial = engine.rebuild(result.events, through_sequence=2).players['1']
    assert initial.name.value == '甲'
    assert initial.alive.certainty == Certainty.UNKNOWN
    before = engine.rebuild(result.events, through_sequence=3).players['1']
    assert before.health.certainty == Certainty.OBSERVED
    assert before.alive.certainty == Certainty.INFERRED
    assert before.alive.value is True
    after = result.state.players['1']
    assert after.alive.value is False
    assert after.alive.certainty == Certainty.OBSERVED
    assert after.health.certainty == Certainty.UNKNOWN
    assert after.alive.evidence_event_ids == [result.events[-1].event_id]
    assert result.findings[0].details['killer_id'] is None
    with pytest.raises(ValueError):
        engine.rebuild([result.events[0], result.events[0]])


def test_unknown_health_and_leave():
    result = analyze((row(5, '{1,true,-1}') + row(3, '{1}')).encode())
    assert result.state.players['1'].health.certainty == Certainty.UNKNOWN
    assert result.state.players['1'].alive.certainty == Certainty.UNKNOWN
    assert not result.findings


def test_rule_registry_and_evidence():
    engine = RuleEngine()
    engine.register(DeathObservedRule())
    with pytest.raises(ValueError):
        engine.register(DeathObservedRule())
    class BadRule:
        rule_id = 'bad'
        def evaluate(self, events, state):
            return [Finding(rule_id='bad', summary='bad', certainty=Certainty.INFERRED, evidence_event_ids=['missing'])]
    engine.register(BadRule())
    result = analyze(row(28, '{1}').encode())
    with pytest.raises(ValueError):
        engine.run(result.events, result.state)


def test_knowledge_and_tool_contracts():
    dictionary = SkillDictionary([SkillSemantics(skill_id='synthetic', game_version='test', name='fixture', source='test-only')])
    assert dictionary.get('other', 'synthetic') is None
    assert dictionary.get('test', 'synthetic').cooldown_ms is None
    assert not dictionary.get('test', 'synthetic').verified
    call = ToolCall(call_id='1', name='query_events')
    assert ToolResult(call_id=call.call_id, error='not implemented').error
