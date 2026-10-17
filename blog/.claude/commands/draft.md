---
description: 작성 한 단계 — 케이스 하나로 요청을 열고 drafter 에게 초안을 쓰게 한다 (7차시)
argument-hint: <케이스 이름(새 연습 요청) 또는 요청 id>
allowed-tools: Read, Agent, Task, Bash(uv run python scripts/open_request.py:*)
---

## 요청을 연 결과

!`uv run python scripts/open_request.py $ARGUMENTS`

## 할 일

당신은 이 요청의 진행을 맡습니다. 초안을 직접 쓰지 않습니다.

1. 위 결과가 "작성" 을 요구하면, 하위 에이전트 **drafter** 에게 맡깁니다. 백그라운드로 띄우지 말고 끝날 때까지 기다립니다. 요청 id 와 쓸 곳(`requests/<요청 id>/draft.json`)을 그대로 넘깁니다.
2. drafter 가 끝나면 멈춥니다. 검수와 그 뒤 단계는 차단 장치가 합니다.
3. 그 밖의 일(다른 파일 고치기, 다른 명령 실행, 결과를 말로 요약하기)은 하지 않습니다.
