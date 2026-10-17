---
description: 기대와 다르게 판정된 케이스 하나를 개선 담당(improver)에게 맡긴다 (9차시)
argument-hint: <케이스 이름, 예: case-06-korean-notes>
allowed-tools: Read, Agent, Task, Bash(uv run python tests/test_checks.py), Bash(uv run python review.py:*)
---

## 할 일

당신은 이 개선의 진행을 맡습니다. 파일을 직접 고치지 않습니다.

1. 먼저 `uv run python review.py --case $ARGUMENTS` 를 실행해 거부 줄을 봅니다.
2. 하위 에이전트 **improver** 에게 케이스 이름 `$ARGUMENTS` 를 넘겨 맡깁니다. 백그라운드로 띄우지 말고 끝날 때까지 기다립니다.
3. improver 가 끝나면 아래 셋을 직접 실행해 신호를 적습니다. improver 의 보고에 기대지 않습니다.
   - `uv run python tests/test_checks.py`
   - `uv run python review.py --case $ARGUMENTS`
   - `uv run python review.py --fail-on-regression`
4. improver 의 보고와 세 신호를 그대로 보여 주고 멈춥니다. 저장(git commit)과 기준 저장은 사람이 합니다.
