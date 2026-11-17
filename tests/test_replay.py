import json
import httpx
import pytest
from fastapi.testclient import TestClient
from jx3_combat_coach.api.app import create_app
from jx3_combat_coach.service import analyze
from jx3_combat_coach.replay import replay, evidence_report
from jx3_combat_coach.agent.report import generate_report, ReportUnavailable


def row(code, payload, time):
    return f'0\t1\t1700000000\t{time}\t{code}\t{payload}\n'


def fixture():
    return (row(4,'{1,"测试人物",1,999}',1000)+row(5,'{1,true,100,200}',1000)
        +row(19,'{2,777,1}',1100)+row(13,'{1,false,3,false,888,1,999,false,1,2}',1200)
        +row(21,'{2,1,0,1,777,1,false,2,{[13]=80,[14]=0}}',1300)
        +row(13,'{1,true,3,false,888,1,999,false,1,2}',1400)+row(28,'{1,2}',1500)).encode()


def test_replay_values_and_exact_reference(tmp_path, monkeypatch):
    path=tmp_path/'catalog.json'
    path.write_text(json.dumps({'client':'std','game_version':'fixture','entries':{'buff.888_1':{'name':'合成标签','tags':['眩晕'],'verified':False}}}))
    monkeypatch.setenv('JX3_CATALOG_PATH',str(path))
    view=replay(analyze(fixture()))
    assert view['players'][0]['name']=='测试人物'
    assert view['events'][3]['reference']['verified'] is False
    assert view['events'][4]['values']['effective_damage']==80
    assert view['events'][5]['kind']=='buff_remove'
    report=evidence_report(view)
    assert '有效伤害 80' in report['deaths'][0]['summary']
    assert len(report['deaths'][0]['evidence_event_ids'])==6
    assert view['events'][0]['time_ms']==0


def test_replay_and_reports_api(tmp_path, monkeypatch):
    monkeypatch.delenv('JX3_LLM_API_KEY',raising=False)
    with TestClient(create_app(str(tmp_path/'db'))) as client:
        result=client.post('/api/v1/analyses/file',content=fixture()).json()
        prefix='/api/v1/analyses/'+result['analysis_id']
        assert client.get(prefix+'/replay').status_code==200
        assert client.get(prefix+'/report').json()['mode']=='evidence'
        assert client.post(prefix+'/report/ai').status_code==503
        assert client.get('/api/v1/analyses/missing/replay').status_code==404


def test_ai_payload_and_errors(monkeypatch):
    monkeypatch.setenv('JX3_LLM_API_KEY','synthetic-test-key')
    monkeypatch.setenv('JX3_LLM_MODEL','synthetic-model')
    real_client=httpx.Client
    def handler(request):
        data=json.loads(request.content)
        assert '测试人物' not in data['messages'][1]['content']
        return httpx.Response(200,json={'choices':[{'message':{'content':'证据报告'}}]})
    monkeypatch.setattr('jx3_combat_coach.agent.report.httpx.Client',lambda **kwargs:real_client(transport=httpx.MockTransport(handler)))
    assert generate_report(replay(analyze(fixture())))['text']=='证据报告'
