# 이 저장소에서 일할 때

이 저장소는 블로그 자동화 실습 저장소입니다. 계획서는 `PRD.md` 입니다. 대화 창에서 무엇을 짓든 먼저 `PRD.md` 의 해당 절을 읽습니다.

이 파일은 **대화 창에서 짓는 일**에 관한 것입니다. 자동 실행(`scripts/request.sh` 가 부른 `/handle-request` · `/draft`)에도 이 파일이 함께 실리지만, 그때는 각 프로젝트의 명령 파일(`.claude/commands/`)이 정한 대로만 움직입니다.

## 폴더

| 폴더 | 무엇 | 고쳐도 되나 |
|---|---|---|
| `blog/` | 본 과정에서 짓는 블로그 자동화 | 그 차시에 짓기로 한 파일만 |
| `alert/` · `triage/` | 뒤 차시에서 보기만 하는 완성 코드. 따로 받은 저장소라 이 저장소에는 저장되지 않습니다 | 고치지 않습니다 |
| 맨 위 `judge.py` · `hackers.yaml` · `preflight.py` | 판정과 점검 | 고치지 않습니다 |

프로젝트마다 제 `CLAUDE.md` 에 "이 프로젝트의 선언" 표가 있습니다 — 그 프로젝트에서 일할 때는 그 표를 먼저 봅니다.

## 지킬 것

- 부탁받은 파일만 새로 만들거나 고칩니다. 다른 파일은 고치지 않습니다.
- 판정 재료는 고치지 않습니다: `blog/cases/`, `blog/samples/reference/`, `blog/schema.json`, `blog/baseline.json`, `blog/review.py`, `blog/scripts/flow_check.py`, 시험 폴더 `blog/tests/`, 공통 차단 장치(`_state.py` · `guard.py` · `run_review.py` · `next_step.py` · `show_status.py`).
- **공개 실습 저장소의 태그(`h05` · `h07` …)는 열거나 받지 않습니다**(`git show` · `git restore --source` · `git checkout` 으로 태그를 보는 일). 태그마다 그 차시가 끝난 상태가 들어 있습니다. 보고 옮겨도 판정은 통과하지만, 그러면 이 실습에서 얻을 것이 없습니다. 사람이 받으라고 하면 받습니다.
- AI 를 실제로 부르는 명령(`scripts/request.sh`, `claude -p`)은 부탁받지 않았으면 실행하지 않습니다. 실행해도 되는 것은 `--dry-run`(시험 모드), `scripts/flow_check.py`(저장된 초안), 시험 파일, `uv run python judge.py` 입니다.
- 파이썬은 늘 `uv run python` 으로 부릅니다(저장소 맨 위의 `.venv`). 명령은 프로젝트 폴더(`blog/`) 안에서 실행합니다. 판정은 저장소 맨 위에서 `uv run python judge.py <차시>` 입니다.
- 대화 창에서 짓기를 마치면 무엇을 만들었는지 세 줄로 알려 줍니다(자동 실행에서는 명령 파일대로 끝냅니다).
