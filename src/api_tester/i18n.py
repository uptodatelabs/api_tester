"""Internationalization (i18n) for the api_tester TUI.

The default language is English. Set the ``API_TESTER_LANG`` environment
variable to ``ko`` to use Korean strings::

    API_TESTER_LANG=ko api-tester

Press ``L`` inside the TUI to toggle between English and Korean.
"""
from __future__ import annotations

import os
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    'en': {
        'detect_button': 'Detect',
        'test_button': 'Connection Test',
        'clear_button': 'Clear',
        'model_select_prompt': 'Select a model after detection',
        'result_placeholder': 'Result will be displayed here.',
        'ready': 'Ready',
        'base_url_required': 'Please enter a Base URL.',
        'detecting': 'Detecting...',
        'detect_first_required': 'Please run detection first.',
        'detect_started': 'Detection started...',
        'detect_failed': 'Detection failed:',
        'detect_complete': 'Detection complete:',
        'detect_success_notify': 'Detection complete',
        'detect_failure_notify': 'Detection failed',
        'test_started': 'Connection test started...',
        'test_failed': 'Connection test failed:',
        'test_result': 'Connection test:',
        'test_success_notify': 'Connection success',
        'test_failure_notify': 'Connection failed',
        'results_cleared': 'Log and results cleared.',
        'language_changed': 'Language changed:',
        'language': 'Language',
        'command_palette': 'Command Palette',
        'action_failed': 'Action failed',
        'default_value': 'default value',
    },
    'ko': {
        'detect_button': '감지',
        'test_button': '연결 테스트',
        'clear_button': '지우기',
        'model_select_prompt': '감지 후 모델 선택',
        'result_placeholder': '결과가 여기에 표시됩니다.',
        'ready': '준비 완료',
        'base_url_required': 'Base URL을 입력해주세요.',
        'detecting': '감지 중...',
        'detect_first_required': '먼저 감지를 실행해주세요.',
        'detect_started': '감지 시작...',
        'detect_failed': '감지 실패:',
        'detect_complete': '감지 완료:',
        'detect_success_notify': '감지 완료',
        'detect_failure_notify': '감지 실패',
        'test_started': '연결 테스트 시작...',
        'test_failed': '연결 테스트 실패:',
        'test_result': '연결 테스트:',
        'test_success_notify': '연결 성공',
        'test_failure_notify': '연결 실패',
        'results_cleared': '로그와 결과를 지웠습니다.',
        'language_changed': '언어 변경:',
        'language': '언어',
        'command_palette': '명령 팔레트',
        'action_failed': '동작 실패',
        'default_value': '기본값',
    },
}

DEFAULT_LANGUAGE = 'en'


def _resolve_language(lang: str) -> str:
    lang = (lang or '').strip().lower()
    return lang if lang in MESSAGES else DEFAULT_LANGUAGE


_language = _resolve_language(os.environ.get('API_TESTER_LANG'))


def get_language() -> str:
    """Return the active language code (e.g. ``'en'`` or ``'ko'``)."""
    return _language


def set_language(language: str) -> None:
    """Set the active language code. Falls back to English if unknown."""
    global _language
    _language = _resolve_language(language)


def t(key: str) -> str:
    """Translate a message key for the active language."""
    return MESSAGES[_language].get(key, key)


__all__ = ['get_language', 'set_language', 't']
