# api_tester

TUI-based API testing tool built with Textual and httpx.

OpenAI/Anthropic 호환 API 엔드포인트를 자동 감지하고 모델의 context/max token 한도를 추론한 뒤 연결 테스트를 수행하는 CLI 도구입니다.

## 설치 및 실행 방법

pip install -e .
api_tester
# 또는
python -m api_tester

TUI가 실행되면 Base URL과 API Key를 입력하고 감지 버튼을 누릅니다. 감지 완료 후 모델을 선택하면 연결 테스트 버튼을 사용할 수 있습니다.

## 입력 예시

- OpenAI: https://api.openai.com / API Key: sk-...
  - 자동으로 https://api.openai.com/v1/models -> https://api.openai.com/models 순서로 프로브합니다.
- Anthropic: https://api.anthropic.com / API Key: sk-ant-...
  - x-api-key + anthropic-version: 2023-06-01 헤더로 /models, /messages를 프로브합니다.

## 자동 감지 동작

detector(src/api_tester/detector.py)는 입력된 base_url에 대해:

1. Authorization: Bearer <key> 헤더로 /v1/models -> /models 순서로 OpenAI 호환 응답을 확인합니다.
2. 실패하면 x-api-key + anthropic-version: 2023-06-01 헤더로 /models, /messages 응답을 확인합니다.

응답 본문 구조(data 리스트, object: list, error.type 등)와 헤더 구성으로 OpenAI/Anthropic을 구분하고, api_type, model, endpoint, headers, payload_guide를 채웁니다.

## context/max token 추론 규칙

model_registry의 MODEL_LIMITS 테이블에서 모델명을 정확히 또는 별칭으로 매칭하고, 매칭되지 않으면 휴리스틱으로 추론합니다.

| 모델 | context size | max tokens |
| --- | --- | --- |
| gpt-4o | 128000 | 16384 |
| gpt-4-turbo | 128000 | 4096 |
| claude-3-5-sonnet-20241022 | 200000 | 8192 |
| claude-3-7-sonnet-20250219 | 200000 | 64000 |
| claude-opus-4-20250514 | 200000 | 32000 |
| 알 수 없는 모델 | 8192 (기본) | 4096 (기본) |

휴리스틱 요약: claude 포함 -> 200000/8192, gemini 포함 -> 1048576/8192, gpt-4o/gpt-4.1 포함 -> 128000/16384, o1/o3 포함 -> 200000/100000 (mini는 128000/65536), 1m/1048576 포함 -> 1048576 등.

## 결과 해석 방법

감지 결과 화면에 표시되는 필드:

- api_type: openai 또는 anthropic (감지 실패 시 unknown)
- base_url: 실측 요청에 사용된 기본 URL
- model: 감지된 첫 모델 또는 직접 선택한 모델
- context size: 모델의 최대 입력 컨텍스트 토큰 수
- max token: 권장 최대 응답 토큰 수 (max_tokens 기본값)
- endpoint: 연결 테스트 시 호출하는 실제 엔드포인트 (openai: /chat/completions, anthropic: /messages)
- headers: 감지된 인증/버전 헤더
- payload guide: 호출 시 사용할 요청 본문 가이드

연결 테스트 결과:

- status: HTTP 상태 코드 (0이면 네트워크/요청 오류)
- latency_ms: 요청 시작부터 응답 수신까지의 왕복 지연 (ms)
- available: true면 2xx 응답, false면 실패
- error: 4xx/5xx일 때 응답 본문 또는 예외 메시지
