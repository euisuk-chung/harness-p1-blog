# 블로그 자동화 — 한 주의 기술 소식을 블로그 초안으로

이 폴더에서 대화 창을 연다: `cd blog` 뒤 `claude --add-dir ..`(모델은 3차시에 `/model` 로 저장해 둔 본 에이전트 모델) (한 층 위 PRD.md 를 읽으려고 `--add-dir ..`).
Claude Code 는 연 폴더의 `.claude/` 만 읽는다 — 다른 폴더에서 열면 아래 장치가 걸리지 않는다.

## 이 프로젝트의 선언

| 업무 말 | 이름 | 이 프로젝트에서 |
|---|---|---|
| 요청 | `request` | cron 이 주 1회 `scripts/request.sh` 를 부른다. 요청 id 는 주차(`2026-W36`), 요청 폴더 `requests/<요청 id>/`. |
| 검수 | `review` | `review.py --request <id>` — 검사 다섯 G1~G5. 모델 없음 |

- 차단 장치(`.claude/settings.json`): `protect_sources.py`(원문 보호)
- 흐름도 `graph.yaml` · 정책 `policies.yaml`

## 지킬 것

- `cases/`·요청 폴더의 `sources/` 는 원문이라 고치지 않는다.
- `state.json`·`events.jsonl`·`STATUS.md` 는 차단 장치와 스크립트가 쓴다. 고치지 않는다.
- 판정이 다르면 고치지 말고 판정이 찍어 주는 받기 명령으로 완성 조각을 받는다.
