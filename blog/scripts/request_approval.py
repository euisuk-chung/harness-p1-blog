"""승인 요청 — 검수를 통과한 초안을 글로 만들고, 사람이 합칠 PR 을 연다. 모델을 부르지 않는다.

    uv run python scripts/request_approval.py <요청 id>

늘 3(사람 차례)으로 끝난다 — 발행은 사람이 PR 을 합칠 때 일어난다. 실패하면 64.
PR 은 환경 변수 HACKERS_PR=1 일 때만 연다(scripts/request.sh --pr). 없으면 글만 만들고 멈춘다.

PR 을 열 때
  브랜치 draft/<요청 id> 에 drafts/<id>.md 하나만 올리고, 본문에 요청 id·초안 지문과 규칙 검사 근거를 적는다.
  작업 트리에 다른 변경이 있으면 열지 않는다 — 남의 변경이 PR 에 섞이지 않게.
  끝나면 원래 브랜치로 돌아온다 — 안 돌아오면 다음 주 요청이 이번 주 초안 위에 브랜치를 만든다.
  도중에 실패하거나 끊겨도(Ctrl+C·종료 신호) 돌아오고, 이번에 만들었는데 PR 을 못 연 초안 브랜치는 지운다.
  못 열었으면 올리려던 파일을 다시 만들어 두고, 스테이징도 풀어 둔다 — 다음 주 커밋에 섞이지 않게.
  Claude 가 통째로 끝나 돌아오지 못한 채 초안 브랜치에 남았으면, 다음에 불릴 때 먼저 원래 브랜치로 돌아간다.
  git 이 아이디·비밀번호나 ssh 암호를 물으며 멈추지 않게 한다 — 로그인이 없으면 바로 실패한다.
  올리기는 됐는데 PR 을 못 열면 GitHub 쪽 초안 브랜치는 남는다(지우지 않는다 — 사람이 보고 PR 을 열거나 지운다).
"""

import hashlib
import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render import render  # noqa: E402
from approval_evidence import write as write_evidence  # noqa: E402

WAIT = 3


GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")
GIT_ENV.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")  # ssh 주소여도 암호를 묻지 않고 바로 실패한다


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, env=GIT_ENV, capture_output=True, text=True, encoding="utf-8")


def main() -> int:
    rid = sys.argv[1]
    try:
        out = render(rid)
    except (OSError, ValueError, KeyError) as e:
        print(f"approve: 초안을 글로 만들 수 없다 ({type(e).__name__})")
        return 64
    rel = out.relative_to(ROOT).as_posix()
    fp = hashlib.sha256(out.read_bytes()).hexdigest()[:12]
    # 지난번 승인 단계가 끊겨 초안 브랜치에 남아 있으면(Claude 가 차단 장치째 끝나면 finally 도 못 돈다) 먼저 돌아간다
    here = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    prev = git("rev-parse", "--abbrev-ref", "@{-1}").stdout.strip()
    if here.startswith("draft/") and prev and not prev.startswith("draft/"):
        git("reset", "-q")
        git("restore", "--", rel)              # 방금 만든 글이 그 브랜치에 올라간 같은 파일을 고쳐 두었으면 되돌린다
        if git("switch", prev).returncode == 0:
            git("branch", "-D", here)
            print(f"approve: 지난번에 끊긴 초안 브랜치 {here} 를 지우고 {prev} 브랜치로 돌아왔다")
            out = render(rid)
    fp = hashlib.sha256(out.read_bytes()).hexdigest()[:12]
    # 사람이 보는 근거를 덧붙인다. 기존 승인 신호·권한은 바꾸지 않는다.
    try:
        evidence = write_evidence(ROOT, rid, out)
        print(f"approve: 확인 근거 requests/{rid}/approval-evidence.md")
    except OSError as e:
        evidence = f"검사 근거 미확인 ({type(e).__name__}). 통과로 읽지 말고 요청 기록을 확인하세요.\n"
        print("approve: 확인 근거를 저장하지 못했다 — 요청 기록을 확인하세요")
    if os.environ.get("HACKERS_PR") != "1":
        print(f"approve: {rel} 를 만들고 승인을 기다린다 (PR 은 --pr 일 때 연다)")
        return WAIT
    top = git("rev-parse", "--show-toplevel").stdout.strip()
    # 초안 폴더(drafts/)와 요청 폴더(requests/)는 "다른 변경" 으로 세지 않는다 — 처음에는 drafts/ 가 통째로 새 폴더로 보인다
    dirty = [l for l in git("status", "--porcelain").stdout.splitlines()
             if not l.endswith(rel) and "requests/" not in l and "drafts/" not in l]
    if not top or dirty:
        print(f"approve: 작업 트리가 깨끗하지 않아 PR 을 열지 않는다 — {rel} 만 만들었다")
        return WAIT
    back = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    branch = f"draft/{rid}"
    steps = [("switch", "-c", branch), ("add", "--", rel),
             ("commit", "-m", f"{rid} 블로그 초안 (지문 {fp})"), ("push", "-u", "origin", branch)]
    created = opened = False
    # 종료 신호(Claude 가 차단 장치를 끝낼 때)도 Ctrl+C 처럼 finally 를 거쳐 끝나게 한다
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda n, _f: sys.exit(128 + n))
    try:
        for s in steps:
            r = git(*s)
            created = created or (s[0] == "switch" and r.returncode == 0)
            if r.returncode != 0:
                print(f"approve: git {' '.join(s)} 실패 — {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ''}")
                return 64
        body = f"요청 {rid} 의 초안입니다. 합치면 발행을 승인하는 것입니다.\n\n- 파일: {rel}\n- 초안 지문: {fp}\n\n{evidence}"
        try:
            pr = subprocess.run(["gh", "pr", "create", "--title", f"{rid} 블로그 초안", "--body", body, "--head", branch],
                                cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        except OSError as e:
            print(f"approve: gh 를 실행하지 못했다 — {e}")
            return 64
        if pr.returncode != 0:
            print(f"approve: PR 을 열지 못했다 — {pr.stderr.strip()[:200]}")
            return 64
        opened = True
    finally:
        # 어디서 끝나든(실패·Ctrl+C) 원래 브랜치로 돌아온다. 이번에 만든 브랜치로 PR 을 못 열었으면 그 브랜치도 지운다
        git("switch", back)
        if not opened:
            git("reset", "-q", "--", rel)          # 커밋 전에 멈췄으면 스테이징이 원래 브랜치로 따라온다
            if created:
                git("branch", "-D", branch)
            render(rid)                            # 초안 브랜치와 함께 사라진 글을 다시 만들어 둔다
    print(f"approve: PR {pr.stdout.strip()} — 사람이 합치면 발행된다")
    return WAIT


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # 되돌리기는 main 의 finally 가 이미 했다 — 긴 오류 대신 한 줄
        print("approve: 끊겼다 — 원래 브랜치로 돌아왔다")
        sys.exit(130)
