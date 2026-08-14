'''Model registry for known context/max-token limits and estimation helpers.

This module provides a small database of common model limits plus heuristics
so that unknown OpenAI/Anthropic-compatible models can be probed with sensible
defaults.
'''
from __future__ import annotations

from typing import Dict, Optional, Tuple

DEFAULT_CONTEXT_SIZE = 8192
DEFAULT_MAX_TOKENS = 4096

MODEL_LIMITS: Dict[str, Tuple[int, int]] = {
    'gpt-3.5-turbo': (4096, 4096),
    'gpt-3.5-turbo-16k': (16384, 4096),
    'gpt-4': (8192, 8192),
    'gpt-4-32k': (32768, 8192),
    'gpt-4-turbo': (128000, 4096),
    'gpt-4o': (128000, 16384),
    'gpt-4o-mini': (128000, 16384),
    'o1': (200000, 100000),
    'o1-mini': (128000, 65536),
    'o3': (200000, 100000),
    'o3-mini': (200000, 100000),
    'claude-3-5-sonnet-20240620': (200000, 8192),
    'claude-3-5-sonnet-20241022': (200000, 8192),
    'claude-3-5-haiku-20241022': (200000, 8192),
    'claude-3-7-sonnet-20250219': (200000, 64000),
    'claude-sonnet-4-20250514': (200000, 64000),
    'claude-opus-4-20250514': (200000, 32000),
    'gemini-1.5-pro': (1048576, 8192),
    'gemini-2.5-pro': (1048576, 65536),
    'gemini-2.5-flash': (1048576, 65536),
}

ALIASES: Dict[str, str] = {
    'gpt35': 'gpt-3.5-turbo',
    'gpt-3.5': 'gpt-3.5-turbo',
    'gpt4': 'gpt-4',
    'gpt4o': 'gpt-4o',
    'claude': 'claude-3-5-sonnet-20241022',
    'gemini-pro': 'gemini-1.5-pro',
}


def _lookup_name(name: str) -> Optional[str]:
    if name in MODEL_LIMITS:
        return name
    return ALIASES.get(name)


def estimate_context_size(model_name: Optional[str]) -> int:
    name = (model_name or '').strip().lower()
    if not name:
        return DEFAULT_CONTEXT_SIZE
    canonical = _lookup_name(name)
    if canonical:
        return MODEL_LIMITS[canonical][0]

    if '1m' in name or '1048576' in name:
        return 1048576
    if '200k' in name:
        return 200000
    if '128k' in name:
        return 128000
    if '32k' in name:
        return 32768
    if '16k' in name:
        return 16384
    if 'claude' in name:
        return 200000
    if 'gemini' in name:
        return 1048576
    if 'gpt-4o' in name or 'gpt-4.1' in name:
        return 128000
    if name.startswith('gpt-4'):
        return 8192
    if name.startswith('o1') or name.startswith('o3'):
        return 128000 if 'mini' in name else 200000
    return DEFAULT_CONTEXT_SIZE


def estimate_max_tokens(model_name: Optional[str]) -> int:
    name = (model_name or '').strip().lower()
    if not name:
        return DEFAULT_MAX_TOKENS
    canonical = _lookup_name(name)
    if canonical:
        return MODEL_LIMITS[canonical][1]

    if 'gpt-4o' in name or 'gpt-4.1' in name:
        return 16384
    if 'o1' in name or 'o3' in name:
        return 65536 if 'mini' in name else 100000
    if 'claude' in name:
        return 8192
    if 'gemini' in name:
        return 8192
    if name.startswith('gpt-4'):
        return 8192
    if name.startswith('gpt-3.5'):
        return 4096
    return DEFAULT_MAX_TOKENS


def get_model_limits(model_name: Optional[str]) -> Tuple[int, int]:
    return (estimate_context_size(model_name), estimate_max_tokens(model_name))
