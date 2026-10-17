#!/usr/bin/env bash
# 주간 요청 하나를 처리한다 — cron 이 부른다(주 1회).
#
#   scripts/request.sh                         이번 주 요청
#   scripts/request.sh --slot 2026-W36         주차를 직접
#   scripts/request.sh --pr                    검수를 통과하면 PR 까지 연다
#   scripts/request.sh --dry-run               부를 명령만 찍는다(요청도 열지 않는다)
#   scripts/request.sh --practice case-01-standard   연습 요청 하나 — 작성 한 단계만(/draft), 열 때마다 새 번호 (7차시)
#
# 순서: 요청 열기(같은 주가 이미 끝났거나 다른 실행이 처리하는 중이면 건너뜀) → claude -p "/handle-request <주차>" → 마무리.
# 끝날 때 신호: 0 발행됨 · 3 사람 차례(승인 대기 또는 세 번 거부) · 1 실패 · 건너뛰면 0.
#
# cron 에는 터미널도 로그인한 사람의 PATH 도 없다. 그래서 첫 줄에서 이 프로젝트 폴더로 들어가고
# (이 폴더의 .claude/ 만 걸리게), claude 를 찾을 곳을 PATH 에 채운다.
# --bare 는 붙이지 않는다 — 차단 장치(보호·검수·다음 단계)가 모두 꺼진다. tests/test_scripts.py 가 본다.
set -u
cd "$(dirname "$0")/.." || exit 64
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
# -p 실행에서는 하위 에이전트가 기본으로 백그라운드에서 돈다(공식 문서). 끝날 때까지 기다리게 끈다 — guard.py 도 막는다.
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
# 한 번 부른 Claude 가 10분을 넘기면 끊는다. 운영체제마다 다른 timeout 명령 대신 파이썬으로 건다(scripts/limited.py).

DRY=0; SLOT="$(date +%G-W%V)"; CASE="case-01-standard"; PRACTICE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --pr) export HACKERS_PR=1 ;;
    --slot) SLOT="$2"; shift ;;
    --case) CASE="$2"; shift ;;
    --practice) PRACTICE="$2"; shift ;;
    *) echo "쓰는 법: scripts/request.sh [--dry-run] [--pr] [--slot 2026-W36] [--case 케이스]"; exit 64 ;;
  esac
  shift
done

# 요청 하나를 끝까지 처리하는 명령은 11차시에 짓는다. 그 전에는 작성 한 단계 명령(/draft)이 요청을 받는다.
CMD=handle-request
[ -f .claude/commands/handle-request.md ] || CMD=draft
# Claude 를 부르는 옵션은 이 함수 한 곳에 둔다(네 프로젝트가 같은 모양). CMD 는 부를 명령 이름이다.
claude_args() {
  # 본 에이전트의 모델: 구독에 맞춰 환경 변수 ANTHROPIC_MODEL 로 고른다(Pro 는 sonnet, Max 는 opus). 없으면 sonnet.
  # 자동 실행은 --setting-sources project 라 대화 창에서 /model 로 저장한 값을 읽지 않는다 — 그래서 여기서 따로 받는다.
  # 하위 에이전트 drafter 는 .claude/agents/drafter.md 의 model: sonnet(가벼운 일은 가벼운 모델)을 그대로 쓴다.
  MODEL="${ANTHROPIC_MODEL:-sonnet}"
  # 계정에 연결한 커넥터(MCP — 메일·캘린더 같은)는 설정 파일이 아니라 계정에 붙어 있어 --setting-sources 로 빠지지 않는다.
  # 이 실행은 쓰지 않는데 도구 목록이 부를 때마다 문맥에 통째로 실리니 --strict-mcp-config 로 뺀다.
  CLAUDE_ARGS=(-p "/$CMD $1" --model "$MODEL" --setting-sources project --strict-mcp-config --permission-mode dontAsk
    --tools "Read,Write,Agent,Bash"
    --allowedTools "Read,Write,Agent,Task,Bash(uv run python scripts/open_request.py:*)"
    --output-format json)
}

if [ -n "$PRACTICE" ]; then                    # 연습 요청: 작성 한 단계(/draft)
  out=$(uv run python scripts/open_request.py --case "$PRACTICE"); code=$?
  echo "$out" | head -1
  rid=$(echo "$out" | sed -n 's/^REQUEST_ID=//p')
  [ -n "$rid" ] || exit "$code"
  if [ $code -eq 0 ]; then
    CMD=draft; claude_args "$rid"
    REQUEST_ID="$rid" uv run python scripts/limited.py 600 "$CLAUDE_BIN" "${CLAUDE_ARGS[@]}" > "requests/$rid/claude.json" 2> "requests/$rid/claude.err"
  fi
  uv run python scripts/open_request.py --finish "$rid"
  exit $?
fi

if [ $DRY -eq 1 ]; then
  echo "(dry-run) 요청 열기: uv run python scripts/open_request.py --slot $SLOT --case $CASE"
  claude_args "$SLOT"
  echo "(dry-run) 작성이 필요하면: REQUEST_ID=$SLOT uv run python scripts/limited.py 600 $CLAUDE_BIN ${CLAUDE_ARGS[*]}"
  echo "(dry-run) 마무리: uv run python scripts/open_request.py --finish $SLOT"
  exit 0
fi

# REQUEST_OWNER: 처리 중 표에 이 스크립트의 번호를 적는다. 이 스크립트가 살아 있는 동안 같은 주의 둘째 실행은 건너뛴다.
out=$(REQUEST_OWNER=$$ uv run python scripts/open_request.py --slot "$SLOT" --case "$CASE"); code=$?
echo "$out" | grep -v '^REQUEST_ID=' | head -1
[ $code -eq 10 ] && exit 0                     # 이미 끝났거나 다른 실행이 처리하는 중
echo "$out" | grep -q '^REQUEST_ID=' || exit "$code"

if [ $code -eq 0 ]; then
  claude_args "$SLOT"
  REQUEST_ID="$SLOT" uv run python scripts/limited.py 600 "$CLAUDE_BIN" "${CLAUDE_ARGS[@]}" \
    > "requests/$SLOT/claude.json" 2> "requests/$SLOT/claude.err"
fi
uv run python scripts/open_request.py --finish "$SLOT"
