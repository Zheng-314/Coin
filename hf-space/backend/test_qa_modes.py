import services
import routes.qa as qa_routes
from app_new import app, register_blueprints


def _ensure_blueprints_registered():
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    if '/api/ask' not in rules:
        register_blueprints()


def _client():
    _ensure_blueprints_registered()
    return app.test_client()


def test_local_mode_falls_back_when_local_engine_unavailable(monkeypatch):
    monkeypatch.setattr(services, 'local_search_chain', None)
    monkeypatch.setattr(
        qa_routes,
        'execute_keyword_fallback_payload',
        lambda question: ('fallback-local', [{'type': 'artifact', 'pid': 1}]),
    )

    response = _client().post('/api/ask', json={
        'question': 'hubei coin',
        'searchType': 'local',
        'history': [],
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['answer'] == 'fallback-local'
    assert payload['sources'][0]['type'] == 'artifact'
    assert payload['searchType'] == 'local'


def test_global_mode_uses_global_engine_when_available(monkeypatch):
    monkeypatch.setattr(services, 'global_search_engine', object())
    monkeypatch.setattr(qa_routes, 'execute_global_search', lambda question, engine: 'global-answer')

    response = _client().post('/api/ask', json={
        'question': 'sichuan silver coin',
        'searchType': 'global',
        'history': [],
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['answer'] == 'global-answer'
    assert payload['sources'] == [{'type': 'engine', 'name': 'GraphRAG Global'}]


def test_web_mode_appends_fallback_when_online_search_fails(monkeypatch):
    monkeypatch.setattr(
        qa_routes,
        'execute_web_search',
        lambda question: 'web search unavailable, using local fallback',
    )
    monkeypatch.setattr(
        qa_routes,
        'execute_keyword_fallback_payload',
        lambda question: ('fallback-web', [{'type': 'artifact', 'pid': 2}]),
    )

    response = _client().post('/api/ask', json={
        'question': 'market price trend',
        'searchType': 'web',
        'history': [],
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert 'fallback-web' in payload['answer']
    assert {'type': 'artifact', 'pid': 2} in payload['sources']
    assert payload['sources'][0] == {'type': 'engine', 'name': 'Web Search Summary'}


def test_capabilities_keep_three_modes_available_with_engine_flags(monkeypatch):
    monkeypatch.setattr(services, 'local_search_chain', None)
    monkeypatch.setattr(services, 'global_search_engine', object())
    monkeypatch.setattr(services, 'llm', object())
    monkeypatch.setattr(services, 'local_search_reason', 'local vector store is empty')
    monkeypatch.setattr(services, 'global_search_reason', '')

    response = _client().get('/api/ask/capabilities')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['local']['available'] is True
    assert payload['local']['engineAvailable'] is False
    assert payload['local']['reason'] == 'local vector store is empty'
    assert payload['global']['available'] is True
    assert payload['global']['engineAvailable'] is True
    assert payload['web']['available'] is True
    assert payload['web']['engineAvailable'] is True
