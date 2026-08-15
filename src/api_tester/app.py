'''Textual TUI for API detection and connection testing.'''
from __future__ import annotations

from typing import List, Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Input, RichLog, Select, Static

from .detector import ApiProfile, detect
from .i18n import get_language, set_language, t
from .model_registry import DEFAULT_CONTEXT_SIZE, DEFAULT_MAX_TOKENS, estimate_context_size, estimate_max_tokens
from .tester import check_connection

APP_NAME = 'api_tester'
APP_VERSION = '1.0.0'
COMPANY_NAME = 'uptodatelabs'


def uses_default_limits(context_size: int, max_tokens: int) -> bool:
    '''Return True when both values are the registry defaults (model not detected).'''
    return context_size == DEFAULT_CONTEXT_SIZE and max_tokens == DEFAULT_MAX_TOKENS


class FooterKeyHint(Static):
    '''Clickable key hint in the footer that runs a named app action.'''

    def __init__(self, text: str, action_name: str, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(text, id=id, classes=classes)
        self.action_name = action_name

    def on_click(self, event) -> None:
        # Run the action after the click event finishes dispatching to avoid
        # mutating the widget tree while Textual is still handling the event.
        self.app.call_after_refresh(self._run_action)

    def _run_action(self) -> None:
        action = getattr(self.app, f'action_{self.action_name}', None)
        if action is None:
            self.app.notify(t('action_failed'), severity='error')
            return
        try:
            action()
        except Exception as exc:
            self.app.notify(f'{t("action_failed")}: {exc}', severity='error')


class BrandFooter(Widget):
    '''Always-visible footer: brand info on the left, menus on the right.'''

    DEFAULT_CSS = '''
    BrandFooter {
        dock: bottom;
        height: 1;
        width: 100%;
        layout: horizontal;
        background: $footer-background;
        color: $footer-foreground;
    }

    #footer-brand {
        height: 1;
        width: auto;
        content-align: left middle;
        padding: 0 0 0 1;
    }

    #footer-menus {
        height: 1;
        width: 1fr;
        layout: horizontal;
        align-horizontal: right;
        align-vertical: middle;
    }

    .footer-menu {
        width: auto;
        height: 1;
        padding: 0 1 0 0;
        content-align: right middle;
    }

    .footer-menu:hover {
        background: $block-hover-background;
        text-style: bold;
    }
    '''

    def compose(self) -> ComposeResult:
        yield Static(
            f'{COMPANY_NAME}  [bold]{APP_NAME}[/bold] v{APP_VERSION}',
            id='footer-brand',
        )
        with Horizontal(id='footer-menus'):
            yield FooterKeyHint(
                f'L  {t("language_menu")}',
                'toggle_language',
                id='footer-key',
                classes='footer-menu',
            )
            yield Static('|', id='footer-sep', classes='footer-menu')
            yield FooterKeyHint(
                f'Ctrl+P  {t("command_palette")}',
                'command_palette',
                id='footer-palette',
                classes='footer-menu',
            )


class MainScreen(Screen):
    '''Main screen for the API tester UI.'''

    def on_mount(self) -> None:
        self.log_line(f'[bold blue]{t("ready")}[/]')

    def compose(self) -> ComposeResult:
        with Horizontal(id='body'):
            with Vertical(id='form-panel'):
                yield Input(placeholder='https://api.example.com', id='base-url')
                yield Input(placeholder='API Key', password=True, id='api-key')
                with Vertical(id='buttons'):
                    with Horizontal(id='main-buttons'):
                        yield Button(t('detect_button'), id='detect', variant='primary')
                        yield Button(t('test_button'), id='test', variant='success')
                    yield Button(t('clear_button'), id='clear', variant='error')
                yield Static('', id='model-label')
                yield Select(
                    options=[],
                    prompt=t('model_select_prompt'),
                    id='model-select',
                    disabled=True,
                )
            with VerticalScroll(id='result-panel'):
                yield Static(t('result_placeholder'), id='result', expand=True)
            with VerticalScroll(id='log-panel'):
                yield RichLog(highlight=True, markup=True, id='log')
        yield BrandFooter()

    def refresh_ui(self) -> None:
        '''Re-render all language-dependent widgets with the active language.'''
        self.query_one('#detect', Button).label = t('detect_button')
        self.query_one('#test', Button).label = t('test_button')
        self.query_one('#clear', Button).label = t('clear_button')
        select = self.query_one('#model-select', Select)
        select.prompt = t('model_select_prompt')
        self.query_one('#footer-key', FooterKeyHint).update(f'L  {t("language_menu")}')
        self.query_one('#footer-palette', FooterKeyHint).update(f'Ctrl+P  {t("command_palette")}')
        if self.app._profile is None:
            self.query_one('#result', Static).update(t('result_placeholder'))
        else:
            self.app._update_result(self.app._profile)

    def log_line(self, message: str) -> None:
        self.query_one('#log', RichLog).write(message)

    def clear_log(self) -> None:
        self.query_one('#log', RichLog).clear()


class ApiTesterApp(App):
    '''Textual TUI main app.'''

    VERSION = APP_VERSION
    TITLE = COMPANY_NAME
    SUB_TITLE = f'{APP_NAME} v{VERSION}'
    SCREENS = {'main': MainScreen}
    BINDINGS = [
        ('l', 'toggle_language', 'Language'),
    ]
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

    #main-buttons {
        height: auto;
    }

    #main-buttons Button {
        margin-right: 1;
    }

    #clear {
        width: 100%;
        margin-top: 1;
    }

    #result-panel {
        width: 1fr;
        padding: 1 2;
        border-right: solid $primary;
    }

    #log-panel {
        width: 50;
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

    def on_mount(self) -> None:
        self.push_screen('main')

    def _main_screen(self) -> MainScreen | None:
        return self.screen if isinstance(self.screen, MainScreen) else None

    def _log(self, message: str) -> None:
        screen = self._main_screen()
        if screen is not None:
            screen.log_line(message)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == 'detect':
            self._run_detect()
        elif button_id == 'test':
            self._run_test()
        elif button_id == 'clear':
            self._clear_results()

    def action_toggle_language(self) -> None:
        '''Toggle the UI language between English and Korean (L key / footer click).'''
        current = get_language()
        new_lang = 'ko' if current == 'en' else 'en'
        set_language(new_lang)
        screen = self._main_screen()
        if screen is not None:
            screen.refresh_ui()
        self._log(f'[bold]{t("language_changed")}[/] {new_lang}')
        self.notify(f'{t("language_changed")} {new_lang}', severity='information')

    def refresh_ui(self) -> None:
        screen = self._main_screen()
        if screen is not None:
            screen.refresh_ui()

    def _clear_results(self) -> None:
        self._last_test = {}
        screen = self._main_screen()
        if screen is not None:
            screen.clear_log()
            if self._profile is None:
                screen.query_one('#result', Static).update(t('result_placeholder'))
            else:
                self._update_result(self._profile)
        self._log(f'[bold]{t("results_cleared")}[/] {t("log_cleared")}')
        self.notify(t('results_cleared'), severity='information')

    def _run_detect(self) -> None:
        screen = self._main_screen()
        if screen is None:
            return
        base_url = screen.query_one('#base-url', Input).value.strip()
        if not base_url:
            self._log(f'[bold red]{t("base_url_required")}[/]')
            self.notify(t('base_url_required'), severity='error')
            return
        api_key = screen.query_one('#api-key', Input).value.strip()
        screen.query_one('#result', Static).update(t('detecting'))
        self.log_detect(base_url, api_key)

    def _run_test(self) -> None:
        if self._profile is None:
            self._log(f'[bold red]{t("detect_first_required")}[/]')
            self.notify(t('detect_first_required'), severity='error')
            return
        self.log_test()

    @work(thread=True, exclusive=True, group='network')
    def log_detect(self, base_url: str, api_key: str) -> None:
        self._log(f'[yellow]{t("detect_started")}[/]')
        try:
            profile = detect(base_url, api_key or None, timeout=10.0)
        except Exception as exc:
            self.call_from_thread(self._on_detect_error, str(exc))
            return
        self.call_from_thread(self._on_detect_result, profile)

    def _on_detect_error(self, error: str) -> None:
        screen = self._main_screen()
        if screen is not None:
            screen.query_one('#result', Static).update(f'[bold red]{t("detect_failed")}[/] {error}')
        self._log(f'[bold red]{t("detect_failed")}[/] {error}')
        self.notify(t('detect_failure_notify'), severity='error')

    def _on_detect_result(self, profile: ApiProfile) -> None:
        self._profile = profile
        models = profile.models or ([profile.model] if profile.model and profile.model != 'unknown' else [])
        screen = self._main_screen()
        if screen is not None:
            select = screen.query_one('#model-select', Select)
            options = [(model, model) for model in models]
            select.set_options(options)
            if options:
                select.value = options[0][1]
                select.disabled = False
            else:
                select.disabled = True
            self._update_result(profile)
        self._log(f'[bold green]{t("detect_complete")}[/] {profile.api_type} / {profile.model}')
        self.notify(
            t('detect_success_notify') if profile.api_type != 'unknown' else t('detect_failure_notify'),
            severity='information' if profile.api_type != 'unknown' else 'warning',
        )

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
        screen = self._main_screen()
        if screen is None:
            return
        lines: List[str] = []
        lines.append(f'[bold]api_type:[/] {profile.api_type}')
        lines.append(f'[bold]base_url:[/] {profile.base_url}')
        lines.append(f'[bold]model:[/] {profile.model}')
        default_suffix = f' ({t("default_value")})' if uses_default_limits(profile.context_size, profile.max_tokens) else ''
        lines.append(f'[bold]context size:[/] {profile.context_size}{default_suffix}')
        lines.append(f'[bold]max token:[/] {profile.max_tokens}{default_suffix}')
        lines.append(f'[bold]endpoint:[/] {profile.endpoint}')
        lines.append('[bold]headers:[/]')
        for key, value in profile.headers.items():
            lines.append(f'  {key}: {value}')
        lines.append('[bold]payload guide:[/]')
        for key, value in profile.payload_guide.items():
            lines.append(f'  {key}: {value}')
        if self._last_test:
            test = self._last_test
            lines.append(f'[bold]latency:[/] {test.get("latency_ms", 0):.2f} ms')
            lines.append(f'[bold]status:[/] {test.get("status", 0)}')
        screen.query_one('#result', Static).update('\n'.join(lines))

    @work(thread=True, exclusive=True, group='network')
    def log_test(self) -> None:
        assert self._profile is not None
        self._log(f'[yellow]{t("test_started")}[/]')
        try:
            result = check_connection(self._profile, timeout=10.0)
        except Exception as exc:
            self.call_from_thread(self._on_test_error, str(exc))
            return
        self.call_from_thread(self._on_test_result, result)

    def _on_test_error(self, error: str) -> None:
        self._log(f'[bold red]{t("test_failed")}[/] {error}')
        self.notify(t('test_failed'), severity='error')

    def _on_test_result(self, result: dict) -> None:
        self._last_test = result
        self._log(
            f'[bold]{t("test_result")}[/] status={result["status"]} '
            f'latency={result["latency_ms"]:.2f} ms '
            f'available={result["available"]}'
        )
        if result.get('error'):
            self._log(f'[red]{result["error"]}[/]')
        if self._profile is not None:
            self._update_result(self._profile)
        if result['available']:
            self.notify(t('test_success_notify'), severity='information')
        else:
            self.notify(t('test_failure_notify'), severity='error')


def main() -> None:
    '''Run the api_tester TUI.'''
    ApiTesterApp().run()


if __name__ == '__main__':
    main()
