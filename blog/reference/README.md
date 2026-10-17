# 강사 실행 기록 — 실제로 실행한 요청 셋

사용량이 모자라면 실제 실행(`bash scripts/request.sh …`) 대신 이 폴더를 읽습니다. 판정(`uv run python judge.py NN`)은 저장해 둔 초안으로 실행되니, 이 기록 없이도 통과합니다.

| 폴더 | 차시 | 실행한 명령 | 끝 |
|---|---|---|---|
| `07-draft/` | 7-3 | `bash scripts/request.sh --practice case-01-standard` (7차시 끝 상태) | `published` |
| `08-three-rejects/` | 8-3 | `scripts/request.sh --slot 2026-W37 --case case-04-empty-source` | `needs_human` — 세 번 거부 |
| `11-approval/` | 11-3 | `scripts/request.sh --slot 2026-W36` | `needs_human` — 승인 대기 |

폴더마다 `STATUS.md`(진행표) · `events.jsonl`(기록) · `state.json` · `draft.json`(drafter 가 쓴 초안) · `review.json`(검수 결과), 글이 나온 요청은 `post.md` 가 있습니다.
`11-approval/` 에는 승인 단계가 요청 폴더에 남기는 승인 근거 카드(`approval-evidence.md`·`approval-evidence.json`)도 있습니다. 이 카드는 실행 기록을 남긴 뒤에 11차시 끝 상태의 `blog` 사본에서 이 폴더의 초안으로 `scripts/request_approval.py 2026-W36` 을 다시 실행해 만들었고, 모델은 부르지 않았습니다. Git 기록이 없는 사본이라 검사 코드 커밋은 `미확인` 으로 적혀 있으며, 카드의 `requests/2026-W36/draft.json`·`drafts/2026-W36.md` 는 이 폴더의 `draft.json`·`post.md` 와 같은 파일입니다.
모델이 쓴 초안 문장은 실행할 때마다 달라서, 여러분이 실행하면 다른 문장이 나옵니다. 같게 나오는 것은 진행표의 단계·신호와 끝 상태입니다.
