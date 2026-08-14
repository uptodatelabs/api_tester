import httpx

from api_tester.detector import ApiProfile
from api_tester.tester import test_connection


def _openai_profile() -> ApiProfile:
    return ApiProfile(
        api_type='openai',
        base_url='https://example.com/v1',
        model='gpt-4o-mini',
        endpoint='https://example.com/v1/chat/completions',
        headers={'Authorization': 'Bearer test-key'},
    )


def _anthropic_profile() -> ApiProfile:
    return ApiProfile(
        api_type='anthropic',
        base_url='https://example.com',
        model='claude-3-5-sonnet-20241022',
        endpoint='https://example.com/messages',
        headers={'x-api-key': 'test-key', 'anthropic-version': '2023-06-01'},
    )


def test_openai_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/v1/chat/completions'
        assert request.headers['Authorization'] == 'Bearer test-key'
        body = request.read()
        assert b'"max_tokens": 1' in body
        assert b'"content": "ping"' in body
        return httpx.Response(200, json={'id': 'test', 'choices': []})

    transport = httpx.MockTransport(handler)
    profile = _openai_profile()
    with httpx.Client(transport=transport) as client:
        result = test_connection(profile, client=client)

    assert result['status'] == 200
    assert result['available'] is True
    assert result['error'] == ''
    assert result['latency_ms'] >= 0


def test_openai_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={'error': {'message': 'Invalid API key'}})

    transport = httpx.MockTransport(handler)
    profile = _openai_profile()
    with httpx.Client(transport=transport) as client:
        result = test_connection(profile, client=client)

    assert result['status'] == 401
    assert result['available'] is False
    assert 'Invalid API key' in result['error']


def test_anthropic_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/messages'
        assert request.headers['x-api-key'] == 'test-key'
        assert request.headers['anthropic-version'] == '2023-06-01'
        return httpx.Response(200, json={'id': 'msg_test', 'content': []})

    transport = httpx.MockTransport(handler)
    profile = _anthropic_profile()
    with httpx.Client(transport=transport) as client:
        result = test_connection(profile, client=client)

    assert result['status'] == 200
    assert result['available'] is True
    assert result['error'] == ''


def test_anthropic_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={'error': {'type': 'invalid_request_error', 'message': 'bad request'}},
        )

    transport = httpx.MockTransport(handler)
    profile = _anthropic_profile()
    with httpx.Client(transport=transport) as client:
        result = test_connection(profile, client=client)

    assert result['status'] == 400
    assert result['available'] is False
    assert 'invalid_request_error' in result['error']


def test_unknown_profile():
    profile = ApiProfile(api_type='unknown', base_url='https://example.com', model='x')
    result = test_connection(profile)

    assert result['available'] is False
    assert 'Unsupported' in result['error']
