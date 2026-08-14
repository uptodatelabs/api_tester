'''Connection tester for detected API profiles.

Sends a minimal chat completion request to the detected endpoint and
measures the latency until the first response.
'''
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import httpx

from .detector import ApiProfile


def test_connection(
    profile: ApiProfile,
    timeout: float = 10.0,
    client: Optional[httpx.Client] = None,
) -> Dict[str, Any]:
    '''Send a minimal ping request to the profile's endpoint.

    Args:
        profile: Detected ApiProfile. Must be ``openai`` or ``anthropic``.
        timeout: Request timeout in seconds when ``client`` is not given.
        client: Optional httpx.Client (e.g. with MockTransport) to use.

    Returns:
        Dict with keys: status, latency_ms, error, available.
    '''
    if profile.api_type not in ('openai', 'anthropic'):
        return {
            'status': 0,
            'latency_ms': 0.0,
            'error': f'Unsupported api_type: {profile.api_type}',
            'available': False,
        }

    url = profile.endpoint
    if not url:
        path = 'chat/completions' if profile.api_type == 'openai' else 'messages'
        url = profile.base_url.rstrip('/') + '/' + path.lstrip('/')

    payload = {
        'model': profile.model or 'unknown',
        'max_tokens': 1,
        'messages': [{'role': 'user', 'content': 'ping'}],
    }
    headers = dict(profile.headers)

    start = time.monotonic()
    try:
        if client is not None:
            response = client.post(url, json=payload, headers=headers)
        else:
            with httpx.Client(timeout=timeout) as new_client:
                response = new_client.post(url, json=payload, headers=headers)
        latency_ms = (time.monotonic() - start) * 1000.0
        return {
            'status': response.status_code,
            'latency_ms': round(latency_ms, 2),
            'error': response.text if response.status_code >= 400 else '',
            'available': 200 <= response.status_code < 300,
        }
    except httpx.HTTPError as exc:
        latency_ms = (time.monotonic() - start) * 1000.0
        return {
            'status': 0,
            'latency_ms': round(latency_ms, 2),
            'error': str(exc),
            'available': False,
        }


__all__ = ['test_connection']
