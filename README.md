# 블로그 자동화 실습 저장소

AI 에이전트를 업무의 한 단계로 넣는 실습 저장소입니다. 매주 자료 넷을 읽고 근거 있는 주장 목록을 만든 뒤, 검수를 통과하면 **사람 승인 앞에서 멈추는** 블로그 자동화를 차시마다 한 조각씩 짓습니다. 흐름은 Claude Code 가 실행하고, 차단 장치와 스크립트가 순서·검수·상한을 정합니다. 매주 시작시키는 것은 cron 입니다.

순서는 늘 같습니다.

1. **계획서(`PRD.md`)** 의 한 절을 읽거나 채웁니다.
2. Claude Code 에게 그 절에 맞는 조각을 짓게 합니다.
3. **판정 명령**(`uv run python judge.py <차시>`)으로 작동하는지 봅니다. 판정 명령과 시험 파일은 받은 그대로 둡니다.
4. 막히면 고치지 않고 그 차시의 **완성 조각**(공개 실습 저장소에서 그 차시 끝 태그의 파일)을 받아 다음으로 갑니다.

## 들어 있는 것

| 폴더·파일 | 무엇 |
|---|---|
| `PRD.md` | 블로그 자동화 계획서. 3차시에 쓰기 시작해 5·9차시에 고정 칸이 붙습니다 |
| `blog/` | 짓는 곳. 처음에는 몇 조각이 비어 있고, 흐름도(`graph.yaml`)는 한 줄로만 가는 첫 판입니다 |
| `alert/` · `triage/` | 14·15차시에 보기만 하는 완성 코드 (주가 알림 · 문의 분류). 블로그와 같은 뼈대입니다. 처음에는 없고, 따로 있는 저장소 둘을 14·15차시 첫머리에 이 자리로 clone 합니다(아래 "14 · 15차시 첫머리"). `.gitignore` 가 빼 두어 이 저장소에는 저장되지 않습니다 |
| `judge.py` · `hackers.yaml` | 차시 판정 명령과 기대하는 신호. 모델을 부르지 않습니다 |
| `preflight.py` | 실습 전 점검 — 이 컴퓨터와 세 프로젝트의 선언 |
| `github-checks.yml.example` | GitHub 자동 검사(Actions) 예시 — 시험 셋만, 비밀 값 없음. `.github/workflows/checks.yml` 로 복사하면 켜진다 |
| `CLAUDE.md` | Claude Code 가 이 저장소에서 지킬 것 |

프로젝트 폴더(`blog/` · `alert/` · `triage/`)마다 같은 이름의 뼈대가 있습니다.

| 업무 말 | 이름 | 무엇 |
|---|---|---|
| 요청 | `scripts/request.sh` | cron 이 부른다. 요청 폴더 `requests/<요청 id>/` 를 먼저 만들고 Claude Code 를 부른다 |
| 수집 | `scripts/collect.py` | 자료를 요청 폴더로 모은다. 모델 없음 |
| 작성 | `.claude/agents/drafter.md` | 하위 에이전트 drafter(작성 담당)가 초안(`draft.json`)을 쓴다. 흐름 안에서 초안을 쓰는 곳은 여기 하나 |
| 검수 | `review.py` | 검사 스크립트. 모델 없음 |
| 승인 | 사람 | 블로그는 PR 합치기, 알림은 문구 승인, 문의 분류는 사람 큐 |
| 전달 | 스크립트 | 되돌릴 수 없는 일은 Claude 가 아니라 스크립트가 한다 |

흐름도는 `graph.yaml`, 막는 규칙은 `policies.yaml` 에 있습니다. 이 둘을 읽고 따르는 것이 `.claude/hooks/` 의 차단 장치입니다. 세 프로젝트 폴더는 아래 지도대로 같은 자리에 같은 것을 둡니다(프로젝트마다 `README.md` 첫 화면에도 같은 표가 있습니다).

| 역할 | 파일 (프로젝트 폴더 안) |
|---|---|
| Claude 를 부르는 곳 | `scripts/request.sh` — `claude -p "/handle-request <요청 id>"` 를 부르는 곳은 여기 한 곳 |
| 시작 계기 | `scripts/cron.example`(정해진 때) · `scripts/watch.sh`(폴더에 파일이 생길 때, 문의 분류) |
| 지시 | `CLAUDE.md` · `.claude/commands/`(본 세션) · `.claude/agents/`(작성 담당) · `.claude/skills/`(늘 같은 규칙) · `graph.yaml` 의 `ask`·`retry_hint` |
| 차단 장치 | `.claude/hooks/` — 등록은 `.claude/settings.json` |
| 막는 규칙 | `policies.yaml` · `.claude/settings.json` 의 `permissions.deny` |
| 흐름 단계 (모델 없음) | `scripts/` 의 요청 열기·수집·승인·전달 · `review.py` 와 `checks/` |
| 업무 모듈 · 시험 | `lib/` · `tests/` |

## 처음 한 번 (3차시)

이 저장소의 재료(꾸러미)는 공개 실습 저장소(`https://github.com/euisuk-chung/harness-p1-blog.git`)의 태그 `h03` 에서 받습니다. 내 빈 저장소를 만들고, 공개 실습 저장소 주소에서 `h03` 을 받은 뒤, 뒤 차시의 태그도 한 번에 받아 두고 내 GitHub 저장소에 처음으로 올립니다. 공개 실습 저장소는 원격으로 이어 두지 않고 주소로만 받습니다.

```bash
gh repo create my-blog-agent --private --clone
cd my-blog-agent
git pull https://github.com/euisuk-chung/harness-p1-blog.git h03
git fetch https://github.com/euisuk-chung/harness-p1-blog.git --tags
git branch -M main
git push -u origin main
```

`git pull … h03` 은 태그를 내 저장소에 남기지 않아서, 같은 주소로 `git fetch … --tags` 를 한 번 해 두어야 뒤 차시에 `git restore --source h05 …` 처럼 태그에서 받을 수 있습니다. 새로 만든 GitHub 저장소에는 아직 가지가 없으니 `git push -u origin main` 으로 첫 기록을 올려 둡니다. `git branch -M main` 은 내 가지 이름이 `main` 이 아닐 때(옛 git 은 `master` 로 만들기도 합니다) 맞춰 주고, 이미 `main` 이면 아무 일도 하지 않습니다. 공개 실습 저장소를 원격으로 이어 두지 않는 까닭은, 원격이 둘이면 `gh pr create` 가 어느 저장소에 PR 을 열지 묻거나 공개 실습 저장소 쪽으로 열 수 있고, 완성본 가지까지 내 저장소로 따라오기 때문입니다. `git remote` 를 치면 `origin` 하나만 나오면 됩니다.

그다음 파이썬을 갖추고 점검합니다.

```bash
uv sync
uv run python preflight.py
echo $?
uv run python judge.py 03
```

파이썬은 모두 uv 로 씁니다. `uv sync` 가 이 폴더에 가상환경(`.venv`)을 만들고(파이썬이 없으면 uv 가 받아 옵니다), `pyproject.toml` 에 적힌 라이브러리를 `uv.lock` 의 판 그대로 넣습니다. 그 뒤로는 어느 하위 폴더에서든 `uv run python …` 이 이 `.venv` 를 찾아 씁니다. 차단 장치와 시작 스크립트도 같은 방법으로 파이썬을 부르니, 가상환경을 켜는(`activate`) 단계는 없습니다.

`preflight.py` 는 "1. 이 컴퓨터" 줄이 전부 `OK` 이면 됩니다. "2. 프로젝트 선언" 의 `--` 줄은 아직 짓지 않은 조각이거나 아직 clone 하지 않은 `alert` · `triage` 라 괜찮습니다. `judge.py 03` 은 꾸러미 파일과 첫 저장(커밋)에 `PRD.md` 가 들어 있는지 봅니다.

## 차시마다

| 차시 | 짓는 것 (`blog/` 안) | 판정 |
|---|---|---|
| 4 | 짓지 않습니다. 같은 검수에 두 초안을 넣어 봅니다 | `uv run python judge.py 04` |
| 5 | 원문 보호 장치 · 강화 형식 | `uv run python judge.py 05` |
| 6 | 짓지 않습니다. 5차시에 지은 보호 장치에 깨진 입력을 넣어 봅니다 | `uv run python judge.py 06` |
| 7 | 작성 명령(`/draft`) · 작성 담당(drafter) · 자료 모으기 | `uv run python judge.py 07` |
| 8 | 흐름도에 "거부면 다시, 세 번이면 사람에게" | `uv run python judge.py 08` |
| 9 | 검사 다섯을 내 것으로 | `uv run python judge.py 09` |
| 10 | 짓지 않습니다. 주간 요청을 시험 모드로 실행합니다 | `uv run python judge.py 10` |
| 11 | 내보내기 전 사람 승인(흐름도 한 칸 · `/handle-request` · 막는 규칙 두 줄) | `uv run python judge.py 11` |
| 12 | 원문 보호 장치에 규칙 스킬을 잠그는 한 줄 · 운영 점검 | `uv run python judge.py 12` |
| 14 · 15 | 짓지 않습니다. 완성 코드를 clone 해 보고 계획서와 대 봅니다 | `uv run python judge.py 14` · `uv run python judge.py 15` |

Claude Code 는 **`blog` 폴더에서** 엽니다(`cd blog` 뒤 `claude --add-dir ..`). 차단 장치 설정이 `blog/.claude/` 에 있어서, 다른 폴더에서 열면 그 장치가 켜지지 않습니다. `--add-dir ..` 은 한 층 위(저장소 맨 위)의 `PRD.md` 를 읽을 수 있게 합니다 — 없으면 계획서를 읽지 못합니다.

## 14 · 15차시 첫머리

프로젝트 2·3 의 완성 코드를 저장소 맨 위에서 `alert` · `triage` 폴더로 clone 합니다.

```bash
git clone https://github.com/euisuk-chung/harness-p2-stock-alert.git alert
git clone https://github.com/euisuk-chung/harness-p3-support-triage.git triage
```

두 폴더는 저마다 `pyproject.toml` 을 가진 따로 된 저장소라, 그 폴더에서 처음 `uv run` 하면 그 안에 제 `.venv` 가 생깁니다. clone 하기 전에 `judge.py 14` · `15` 를 실행하면 "폴더가 없습니다" 로 끝납니다.

앞 차시에 지은 조각이 뒤 차시를 깨뜨리지 않았는지는 `uv run python judge.py 11 --all` 처럼 `--all` 을 붙여 한 번에 다시 봅니다.

## 막히면 — 완성 조각 받기

완성 조각은 공개 실습 저장소의 태그에 있습니다. 그 저장소는 `main` 한 줄에 차시마다 커밋 하나를 쌓고, 커밋마다 태그를 달아 두었습니다.

| 태그 | 상태 |
|---|---|
| `h03` | 3차시 시작 — 이 저장소의 재료(꾸러미)와 계획서 양식 |
| `h05` · `h07` · `h08` · `h09` · `h11` · `h12` | 그 차시가 끝났을 때 (`h12` 가 `main`, 완성본) |

판정이 다르면 `judge.py` 가 받는 명령을 화면 끝에 찍어 줍니다. 예를 들어 7차시라면 저장소 맨 위에서:

```bash
git restore --source h07 -- blog/.claude/commands/draft.md blog/.claude/agents/drafter.md blog/.claude/skills/drafter-rules/SKILL.md blog/.claude/settings.json blog/scripts/collect.py
uv run python judge.py 07
```

3차시에 `git fetch https://github.com/euisuk-chung/harness-p1-blog.git --tags` 를 하지 않아 태그가 없으면, 판정이 그 줄을 먼저 찍어 줍니다. `git restore --source h07 -- <파일>` 은 태그 `h07` 의 같은 경로 파일로 내 파일을 덮어씁니다. 되돌리려면 git 으로 — 받기 전에 저장(커밋)해 두면 안전합니다.

계획서의 고정 칸은 따로 된 파일 `prd/05.md` · `prd/09.md` 로 받아(`git restore --source h05 -- prd/05.md`) 그 내용을 `PRD.md` 의 같은 제목 절에 붙여 넣습니다. `PRD.md` 를 태그에서 통째로 받으면 내가 쓴 1~6절이 지워지니 받지 않습니다.

## 선택 연습 — 인계와 승인 근거 읽기

[선택 연습 안내](blog/labs/evidence/README.md)에서 8차시의 불완전한 인계, 9·15차시의 검증·성능 주장, 11·12차시의 승인 근거 카드를 더 살펴볼 수 있습니다. 모의 기록이나 저장된 초안을 사본에서 다루며 모델·API 호출은 없습니다. 기존 차시 판정과 필수 실습에는 포함되지 않습니다.

## 판정이 보장하지 않는 것

- 판정은 **작동하는가**만 봅니다. 직접 지었는지, 태그에서 받아 옮겼는지는 가리지 못합니다.
- 판정은 저장해 둔 초안과 정해 둔 입력으로 실행됩니다(AI 를 부르지 않습니다). 실제로 부를 때 모델이 무엇을 쓸지는 매번 다릅니다 — 그래서 실제 실행은 결과가 정해지는 케이스(8차시의 "통과할 수 없는 케이스")로 봅니다.
- 차단 장치는 Claude Code 안에서의 도구 호출만 막습니다. 다른 편집기로 고치는 것은 막지 못합니다.
