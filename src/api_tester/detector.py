'''Automatic detection of OpenAI/Anthropic-compatible API endpoints.

The detector tries the OpenAI ``/models`` endpoint first and falls back to
the Anthropic headers and schema probes on ``/models`` and ``/messages``.
'''
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from .model_registry import estimate_context_size, estimate_max_tokens


@dataclass
class ApiProfile:
    '''Describes a detected API endpoint and the model limits to use.'''

    api_type: str
    base_url: str
    model: Optional[str] = None
    context_size: int = 0
    max_tokens: int = 0
    endpoint: str = ''
    headers: Dict[str, str] = field(default_factory=dict)
    payload_guide: Dict[str, Any] = field(default_factory=dict)


def _join_url(base: str, path: str) -> str:
    return base.rstrip('/') + '/' + path.lstrip('/')


def _candidate_base_urls(base_url: str) -> List[str]:
    base_url = base_url.strip()
    if not base_url:
        return []
    if '://' not in base_url:
        base_url = 'https://' + base_url
    base_url = base_url.rstrip('/')
    if base_url.endswith('/v1'):
        candidates = [base_url]
    else:
        candidates = [base_url + '/v1', base_url]
    unique = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


def _parse_json(response: httpx.Response) -> Optional[Dict[str, Any]]:
    try:
        data = response.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _looks_like_openai(response: httpx.Response) -> bool:
    data = _parse_json(response)
    if data is None:
        return False
    if data.get('type') == 'error':
        return False
    if isinstance(data.get('data'), list):
        return True
    if data.get('object') == 'list':
        return True
    error = data.get('error')
    if isinstance(error, dict):
        error_type = error.get('type') or error.get('code')
        if isinstance(error_type, str) and error_type in (
            'invalid_request_error',
            'authentication_error',
            'permission_error',
            'not_found_error',
            'invalid_api_key',
        ):
            return True
    return False


def _looks_like_anthropic(response: httpx.Response) -> bool:
    data = _parse_json(response)
    if data is None:
        return False
    if data.get('type') == 'error':
        return True
    items = data.get('data')
    if isinstance(items, list) and items and isinstance(items[0], dict) and 'id' in items[0]:
        return True
    error = data.get('error')
    if isinstance(error, dict):
        error_type = error.get('type')
        if isinstance(error_type, str) and error_type in (
            'authentication_error',
            'permission_error',
            'not_found_error',
            'invalid_request_error',
            'api_error',
            'overloaded_error',
            'rate_limit_error',
        ):
            return True
    return False


def _extract_model_id(data: Optional[Dict[str, Any]], preferred_model: Optional[str]) -> str:
    if preferred_model and preferred_model.strip():
        return preferred_model.strip()
    if data:
        items = data.get('data')
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    model_id = item.get('id') or item.get('name')
                    if model_id:
                        return str(model_id)
    return 'unknown'


def _openai_profile(
    base_url: str,
    api_key: Optional[str],
    preferred_model: Optional[str],
    response: httpx.Response,
) -> ApiProfile:
    data = _parse_json(response)
    model = _extract_model_id(data, preferred_model)
    context_size = estimate_context_size(model)
    max_tokens = estimate_max_tokens(model)
    auth_header = 'Bearer ' + (api_key or '')
    headers = {'Authorization': auth_header}
    payload_guide = {
        'model': model,
        'messages': [{'role': 'user', 'content': '...'}],
    }
    return ApiProfile(
        api_type='openai',
        base_url=base_url,
        model=model,
        context_size=context_size,
        max_tokens=max_tokens,
        endpoint=_join_url(base_url, 'chat/completions'),
        headers=headers,
        payload_guide=payload_guide,
    )


def _anthropic_profile(
    base_url: str,
    api_key: Optional[str],
    preferred_model: Optional[str],
    response: Optional[httpx.Response] = None,
) -> ApiProfile:
    data = _parse_json(response) if response is not None else None
    model = _extract_model_id(data, preferred_model)
    context_size = estimate_context_size(model)
    max_tokens = estimate_max_tokens(model)
    headers = {
        'x-api-key': api_key or '',
        'anthropic-version': '2023-06-01',
    }
    payload_guide = {
        'model': model,
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': '...'}],
    }
    return ApiProfile(
        api_type='anthropic',
        base_url=base_url,
        model=model,
        context_size=context_size,
        max_tokens=max_tokens,
        endpoint=_join_url(base_url, 'messages'),
        headers=headers,
        payload_guide=payload_guide,
    )


def detect(
    base_url: str,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
    timeout: float = 10.0,
) -> ApiProfile:
    base_candidates = _candidate_base_urls(base_url)
    if not base_candidates:
        return ApiProfile(
            api_type='unknown',
            base_url=base_url,
            model=preferred_model if preferred_model and preferred_model.strip() else 'unknown',
        )

    with httpx.Client(timeout=timeout) as client:
        # OpenAI-compatible probe
        for base in base_candidates:
            try:
                openai_headers = {'Authorization': 'Bearer ' + (api_key or '')}
                response = client.get(_join_url(base, 'models'), headers=openai_headers)
            except httpx.HTTPError:
                continue
            if _looks_like_openai(response):
                return _openai_profile(base, api_key, preferred_model, response)

        # Anthropic-compatible probe
        anthropic_headers = {
            'x-api-key': api_key or '',
            'anthropic-version': '2023-06-01',
        }
        for base in base_candidates:
            models_response = None
            messages_response = None
            try:
                models_response = client.get(_join_url(base, 'models'), headers=anthropic_headers)
            except httpx.HTTPError:
                pass
            try:
                messages_response = client.get(_join_url(base, 'messages'), headers=anthropic_headers)
            except httpx.HTTPError:
                pass

            if models_response is not None and _looks_like_anthropic(models_response):
                return _anthropic_profile(base, api_key, preferred_model, models_response)
            if messages_response is not None and _looks_like_anthropic(messages_response):
                return _anthropic_profile(base, api_key, preferred_model, messages_response)

    model = preferred_model if preferred_model and preferred_model.strip() else 'unknown'
    return ApiProfile(
        api_type='unknown',
        base_url=base_url,
        model=model,
        context_size=0,
        max_tokens=0,
        endpoint='',
        headers={},
        payload_guide={},
    )


__all__ = ['ApiProfile', 'detect']
