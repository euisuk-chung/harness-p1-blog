# 이번 주 정리 — 2026-W36

## 밝혀진 것

- staged deliberation은 계획 생성과 계획 실행을 명시적인 중간 산출물로 분리하는 방법이다.
  - 출처 `arxiv:2601.12345:abstract` — "We introduce staged deliberation, a method that separates plan generation from plan execution using an explicit intermediate artifact."

## 수치

- Lumen-3는 MMLU에서 88.2점을 기록했다.
  - 출처 `model:acme/lumen-3:card` — "Lumen-3 achieves 88.2 on MMLU and 71.4 on GPQA-Diamond."

## 할 수 있는 것

- Lumen-3는 최대 400K 토큰의 컨텍스트 윈도우를 지원한다.
  - 출처 `model:acme/lumen-3:card` — "The model supports a 400K token context window."

## 주의할 것

- vLLM v0.9.0부터 generate() 함수는 sampling_params 딕셔너리를 더 이상 받지 않아 기존 호출부가 깨질 수 있다.
  - 출처 `release:vllm:v0.9.0` — "The `generate()` entrypoint no longer accepts a `sampling_params` dict."
- 도구 스키마가 함께 공개되지 않으면 논문 간 tool-use 점수는 서로 비교할 수 없다.
  - 출처 `arxiv:2601.67890:abstract` — "We therefore caution that reported tool-use scores are not comparable across papers unless the exact tool schema is published alongside the result."

## 의견

- 벤치마크 수치만 보고 모델을 고르기보다 실제 워크로드에서 재현되는지 함께 확인하는 습관이 필요해 보인다.
