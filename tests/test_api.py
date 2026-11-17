from fastapi.testclient import TestClient
from jx3_combat_coach.api.app import create_app


def test_api_round_trip_and_restart(tmp_path):
    path = str(tmp_path / 'analysis.sqlite3')
    with TestClient(create_app(path)) as client:
        assert client.get('/health').json() == {'status': 'ok'}
        response = client.post('/api/v1/analyses', json={'text': '0\t1\t1700000000\t1000\t28\t{2}\ninvalid\n'})
        assert response.status_code == 201
        saved = response.json()
        assert saved['analysis']['parsed']['errors'][0]['line_number'] == 2
        assert len(saved['analysis']['findings']) == 1
        assert client.get('/api/v1/analyses/' + saved['analysis_id']).json() == saved['analysis']
        assert client.get('/api/v1/analyses/missing').status_code == 404
        assert client.post('/api/v1/analyses', json={}).status_code == 422
        assert client.post('/api/v1/analyses', json={'text': 'x' * 1_000_001}).status_code == 422
    with TestClient(create_app(path)) as client:
        assert client.get('/api/v1/analyses/' + saved['analysis_id']).json() == saved['analysis']


def test_frontend_and_original_file_upload(tmp_path):
    with TestClient(create_app(str(tmp_path / 'ui.sqlite3'))) as client:
        page = client.get('/')
        assert page.status_code == 200
        assert '开始解析' in page.text
        raw = '0\t1\t1700000000\t1000\t4\t{1,"角色"}\n'.encode('gbk')
        response = client.post('/api/v1/analyses/file?encoding=gbk', content=raw)
        assert response.status_code == 201
        parsed = response.json()['analysis']['parsed']
        assert bytes.fromhex(parsed['raw_hex']) == raw
        assert not parsed['errors']
        assert client.post('/api/v1/analyses/file?encoding=invalid', content=raw).status_code == 422
        assert client.post('/api/v1/analyses/file', content=b'x' * 10_000_001).status_code == 413
