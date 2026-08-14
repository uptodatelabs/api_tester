'''Textual TUI for API detection and connection testing.'''
from __future__ import annotations

from typing import List, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, RichLog, Select, Static

from .detector import ApiProfile, detect
from .model_registry import estimate_context_size, estimate_max_tokens
from .tester import check_connection


class ApiTesterApp(App):
    '''Textual TUI main app.'''

    TITLE = 'api_tester'
    CSS = '''
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
    }

    #form-panel {
        width: 42;
        min-width: 38;
        padding: 1;
        border-right: solid $primary;
    }

    #form-panel Input {
        margin-bottom: 1;
    }

    #buttons {
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
    }

    #buttons Button {
        margin-right: 1;
    }

    #result-panel {
        width: 1fr;
        padding: 1 2;
        border-right: solid $primary;
    }

    #log-panel {
        width: 40;
        padding: 1;
    }

    RichLog {
        height: 1fr;
        border: round $primary;
        padding: 1;
    }

    #result {
        height: 1fr;
        border: round $primary;
        padding: 1;
        overflow-y: auto;
    }
    '''

    def __init__(self) -> None:
        super().__init__()
        self._profile: Optional[ApiProfile] = None
        self._last_test: dict = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id='body'):
            with Vertical(id='form-panel'):
                yield Input(
                    placeholder='https://api.example.com',
                    id='base-url',
                )
                yield Input(
                    placeholder='API Key',
                    password=True,
                    id='api-key',
                )
                with Horizontal(id='buttons'):
                    yield Button('감지', id='detect', variant='primary')
                    yield Button('연결 테스트', id='test', variant='success')
                yield Static('', id='model-label')
                yield Select(
                    options=[],
                    prompt='감지 후 모델 선택',
                    id='model-select',
                    disabled=True,
                )
            with VerticalScroll(id='result-panel'):
                yield Static('결과가 여기에 표시됩니다.', id='result', expand=True)
            with VerticalScroll(id='log-panel'):
                yield RichLog(highlight=True, markup=True, id='log')
        yield Footer()

    def _log(self, message: str) -> None:
        self.query_one('#log', RichLog).write(message)

    def on_mount(self) -> None:
        self.query_one('#log', RichLog).write('[bold blue]준비 완료[/]')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == 'detect':
            self._run_detect()
        elif button_id == 'test':
            self._run_test()

    def _run_detect(self) -> None:
        base_url = self.query_one('#base-url', Input).value.strip()
        if not base_url:
            self._log('[bold red]Base URL을 입력해주세요.[/]')
            self.notify('Base URL을 입력해주세요.', severity='error')
            return
        api_key = self.query_one('#api-key', Input).value.strip()
        self.query_one('#result', Static).update('감지 중...')
        self.log_detect(base_url, api_key)

    def _run_test(self) -> None:
        if self._profile is None:
            self._log('[bold red]먼저 감지를 실행해주세요.[/]')
            self.notify('먼저 감지를 실행해주세요.', severity='error')
            return
        self.log_test()

    @work(thread=True, exclusive=True, group='network')
    def log_detect(self, base_url: str, api_key: str) -> None:
        self._log('[yellow]감지 시작...[/]')
        try:
            profile = detect(base_url, api_key or None, timeout=10.0)
        except Exception as exc:
            self.call_from_thread(self._on_detect_error, str(exc))
            return
        self.call_from_thread(self._on_detect_result, profile)

    def _on_detect_error(self, error: str) -> None:
        self.query_one('#result', Static).update(f'[bold red]감지 실패:[/] {error}')
        self._log(f'[bold red]감지 실패:[/] {error}')
        self.notify('감지 실패', severity='error')

    def _on_detect_result(self, profile: ApiProfile) -> None:
        self._profile = profile
        models = profile.models or ([profile.model] if profile.model and profile.model != 'unknown' else [])
        select = self.query_one('#model-select', Select)
        options = [(model, model) for model in models]
        select.set_options(options)
        if options:
            select.value = options[0][1]
            select.disabled = False
        else:
            select.disabled = True
        self._update_result(profile)
        self._log(f'[bold green]감지 완료:[/] {profile.api_type} / {profile.model}')
        self.notify('감지 완료' if profile.api_type != 'unknown' else '감지 실패', severity='information' if profile.api_type != 'unknown' else 'warning')

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != 'model-select':
            return
        if self._profile is None:
            return
        model = str(event.value) if event.value is not None else 'unknown'
        profile = self._profile
        if model != profile.model:
            profile = ApiProfile(
                api_type=profile.api_type,
                base_url=profile.base_url,
                model=model,
                context_size=estimate_context_size(model),
                max_tokens=estimate_max_tokens(model),
                endpoint=profile.endpoint,
                headers=dict(profile.headers),
                payload_guide=dict(profile.payload_guide),
                models=list(profile.models),
            )
            profile.payload_guide['model'] = model
            if profile.api_type == 'anthropic':
                profile.payload_guide['max_tokens'] = profile.max_tokens
            self._profile = profile
            self._update_result(profile)

    def _update_result(self, profile: ApiProfile) -> None:
        lines: List[str] = []
        lines.append(f'[bold]api_type:[/] {profile.api_type}')
        lines.append(f'[bold]base_url:[/] {profile.base_url}')
        lines.append(f'[bold]model:[/] {profile.model}')
        lines.append(f'[bold]context size:[/] {profile.context_size}')
        lines.append(f'[bold]max token:[/] {profile.max_tokens}')
        lines.append(f'[bold]endpoint:[/] {profile.endpoint}')
        lines.append('[bold]headers:[/]')
        for key, value in profile.headers.items():
            lines.append(f'  {key}: {value}')
        lines.append('[bold]payload guide:[/]')
        for key, value in profile.payload_guide.items():
            lines.append(f'  {key}: {value}')
        if self._last_test:
            test = self._last_test
            lines.append(f'[bold]응답 속도:[/] {test.get("latency_ms", 0):.2f} ms')
            lines.append(f'[bold]상태:[/] {test.get("status", 0)}')
        self.query_one('#result', Static).update('\n'.join(lines))

    @work(thread=True, exclusive=True, group='network')
    def log_test(self) -> None:
        assert self._profile is not None
        self._log('[yellow]연결 테스트 시작...[/]')
        try:
            result = check_connection(self._profile, timeout=10.0)
        except Exception as exc:
            self.call_from_thread(self._on_test_error, str(exc))
            return
        self.call_from_thread(self._on_test_result, result)

    def _on_test_error(self, error: str) -> None:
        self._log(f'[bold red]연결 테스트 실패:[/] {error}')
        self.notify('연결 테스트 실패', severity='error')

    def _on_test_result(self, result: dict) -> None:
        self._last_test = result
        self._log(
            f'[bold]연결 테스트:[/] status={result["status"]} '
            f'latency={result["latency_ms"]:.2f} ms '
            f'available={result["available"]}'
        )
        if result.get('error'):
            self._log(f'[red]{result["error"]}[/]')
        if self._profile is not None:
            self._update_result(self._profile)
        if result['available']:
            self.notify('연결 성공', severity='information')
        else:
            self.notify('연결 실패', severity='error')


def main() -> None:
    '''Run the api_tester TUI.'''
    ApiTesterApp().run()


if __name__ == '__main__':
    main()
