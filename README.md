# apiprobe

TUI-based API testing tool built with Textual and httpx.

It automatically detects OpenAI/Anthropic-compatible API endpoints, infers the model's context/max token limits, and performs connection tests without writing code.

## Installation & Usage

```bash
pip install apiprobe
apiprobe
# or, for local development:
# pip install -e .
```

Once the TUI starts:

1. Enter the **Base URL** and **API Key** in the left panel.
2. Press **Detect** — the tool probes the endpoint and identifies the API type and model.
3. Select a model from the dropdown (if multiple models are detected).
4. Press **Connection Test** to measure real latency and status.
5. Press **Clear** to clear the log and connection-test results.

- Press `L` or click the **Language** footer menu to toggle English / Korean.
- Press `Ctrl+P` or click the **Command Palette** footer menu to open the Textual command palette.
- The footer menus are always visible regardless of focus.

## Input Examples

- OpenAI: `https://api.openai.com` / API Key: `sk-...`
  - Probes `https://api.openai.com/v1/models` then `https://api.openai.com/models`.
- Anthropic: `https://api.anthropic.com` / API Key: `sk-ant-...`
  - Probes `/models` and `/messages` with `x-api-key` + `anthropic-version: 2023-06-01` headers.

## Automatic Detection Behavior

The detector (`src/api_tester/detector.py`) works as follows for a given base URL:

1. Checks for OpenAI-compatible responses with `Authorization: Bearer <key>` against `/v1/models` then `/models`.
2. On failure, checks `/models` and `/messages` with `x-api-key` + `anthropic-version: 2023-06-01`.

It distinguishes OpenAI vs Anthropic by response body structure (`data` list, `object: list`, `error.type`, ...) and header layout, then fills in `api_type`, `model`, `endpoint`, `headers`, and `payload_guide`.

## context / max token Inference Rules

The `model_registry` `MODEL_LIMITS` table matches the model name exactly or by alias; if no match is found, heuristics are used.

| Model | context size | max tokens |
| --- | --- | --- |
| gpt-4o | 128000 | 16384 |
| gpt-4-turbo | 128000 | 4096 |
| claude-3-5-sonnet-20241022 | 200000 | 8192 |
| claude-3-7-sonnet-20250219 | 200000 | 64000 |
| claude-opus-4-20250514 | 200000 | 32000 |
| unknown model | 8192 (default) | 4096 (default) |

Heuristic summary: contains `claude` → 200000/8192, `gemini` → 1048576/8192, `gpt-4o`/`gpt-4.1` → 128000/16384, `o1`/`o3` → 200000/100000 (`mini` → 128000/65536), `1m`/`1048576` → 1048576.

> When detection fails and the fallback limits (8192/4096) are used, the result panel marks them as `(default value)` so you can tell them apart from real model limits.

## Interpreting the Results

Fields shown in the detection result panel:

- `api_type`: `openai` or `anthropic` (`unknown` if detection failed)
- `base_url`: the base URL actually probed
- `model`: the first detected model, or the one you selected
- `context size`: the model's maximum input context in tokens
- `max token`: recommended maximum output tokens (the default `max_tokens`)
- `endpoint`: actual endpoint for connection tests (openai: `/chat/completions`, anthropic: `/messages`)
- `headers`: detected auth/version headers
- `payload guide`: request body guide to use for calls

Fields shown in connection test results:

- `status`: HTTP status code (`0` means a network/request error)
- `latency_ms`: round-trip delay from request start to response (ms)
- `available`: `true` on 2xx responses, otherwise `false`
- `error`: response body or exception message on 4xx/5xx

---

# apiprobe

Textual과 httpx로 만든 TUI 기반 API 테스트 도구입니다.

OpenAI/Anthropic 호환 API 엔드포인트를 자동 감지하고 모델의 context/max token 한도를 추론한 뒤 연결 테스트를 수행하는 CLI 도구입니다.

## 설치 및 실행 방법

```bash
pip install apiprobe
apiprobe
# 또는 로컬 개발 시:
# pip install -e .
```

TUI가 실행되면:

1. 왼쪽 패널에 **Base URL**과 **API Key**를 입력합니다.
2. **감지** 버튼을 누르면 엔드포인트를 프로브하여 API 유형과 모델을 식별합니다.
3. 감지된 모델이 여러 개면 드롭다운에서 모델을 선택합니다.
4. **연결 테스트** 버튼을 누르면 실제 지연 시간과 상태를 측정합니다.
5. **지우기** 버튼을 누르면 로그와 연결 테스트 결과가 지워집니다.

- `L` 키를 누르거나 footer의 **언어** 메뉴를 클릭하면 영어/한국어가 전환됩니다.
- `Ctrl+P`를 누르거나 footer의 **명령 팔레트** 메뉴를 클릭하면 Textual 명령 팔레트가 열립니다.
- footer 메뉴는 포커스 위치와 관계없이 항상 표시됩니다.

## 입력 예시

- OpenAI: `https://api.openai.com` / API Key: `sk-...`
  - `https://api.openai.com/v1/models` → `https://api.openai.com/models` 순서로 프로브합니다.
- Anthropic: `https://api.anthropic.com` / API Key: `sk-ant-...`
  - `x-api-key` + `anthropic-version: 2023-06-01` 헤더로 `/models`, `/messages`를 프로브합니다.

## 자동 감지 동작

detector(`src/api_tester/detector.py`)는 입력된 base_url에 대해:

1. `Authorization: Bearer <key>` 헤더로 `/v1/models` → `/models` 순서로 OpenAI 호환 응답을 확인합니다.
2. 실패하면 `x-api-key` + `anthropic-version: 2023-06-01` 헤더로 `/models`, `/messages` 응답을 확인합니다.

응답 본문 구조(`data` 리스트, `object: list`, `error.type` 등)와 헤더 구성으로 OpenAI/Anthropic을 구분하고, `api_type`, `model`, `endpoint`, `headers`, `payload_guide`를 채웁니다.

## context/max token 추론 규칙

`model_registry`의 `MODEL_LIMITS` 테이블에서 모델명을 정확히 또는 별칭으로 매칭하고, 매칭되지 않으면 휴리스틱으로 추론합니다.

| 모델 | context size | max tokens |
| --- | --- | --- |
| gpt-4o | 128000 | 16384 |
| gpt-4-turbo | 128000 | 4096 |
| claude-3-5-sonnet-20241022 | 200000 | 8192 |
| claude-3-7-sonnet-20250219 | 200000 | 64000 |
| claude-opus-4-20250514 | 200000 | 32000 |
| 알 수 없는 모델 | 8192 (기본) | 4096 (기본) |

휴리스틱 요약: `claude` 포함 → 200000/8192, `gemini` 포함 → 1048576/8192, `gpt-4o`/`gpt-4.1` 포함 → 128000/16384, `o1`/`o3` 포함 → 200000/100000 (`mini`는 128000/65536), `1m`/`1048576` 포함 → 1048576 등.

> 감지에 실패하여 기본 한도(8192/4096)가 사용되면 결과 패널에 `(기본값)`으로 표시되어 실제 모델 한도와 구분할 수 있습니다.

## 결과 해석 방법

감지 결과 화면에 표시되는 필드:

- `api_type`: `openai` 또는 `anthropic` (감지 실패 시 `unknown`)
- `base_url`: 실측 요청에 사용된 기본 URL
- `model`: 감지된 첫 모델 또는 직접 선택한 모델
- `context size`: 모델의 최대 입력 컨텍스트 토큰 수
- `max token`: 권장 최대 응답 토큰 수 (`max_tokens` 기본값)
- `endpoint`: 연결 테스트 시 호출하는 실제 엔드포인트 (openai: `/chat/completions`, anthropic: `/messages`)
- `headers`: 감지된 인증/버전 헤더
- `payload guide`: 호출 시 사용할 요청 본문 가이드

연결 테스트 결과:

- `status`: HTTP 상태 코드 (`0`이면 네트워크/요청 오류)
- `latency_ms`: 요청 시작부터 응답 수신까지의 왕복 지연 (ms)
- `available`: 2xx 응답이면 `true`, 아니면 `false`
- `error`: 4xx/5xx일 때 응답 본문 또는 예외 메시지
