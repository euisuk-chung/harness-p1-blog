"""시작 스크립트 시험 — 가짜 claude 로, 모델을 부르지 않는다.

    uv run python tests/test_scripts.py

  1. --dry-run 은 부를 claude -p 줄만 찍고 요청을 열지 않는다
  2. 같은 주차를 두 번 실행하면 둘째는 Claude 를 부르지 않고 건너뛴다(이미 끝난 주차)
     두 실행이 겹치면 처리 중 표를 먼저 잡은 쪽만 Claude 를 부르고, 주인이 사라진 표는 치우고 이어서 한다
  3. request.sh 에 --bare 가 없다(붙이면 차단 장치가 모두 꺼진다)
  4. request.sh 가 이 프로젝트 폴더로 들어가고 --setting-sources project 로 개인 설정을, --strict-mcp-config 로 계정의 커넥터를 뺀다
전부 맞으면 0.
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
fails = []


def ok(cond: bool, what: str) -> None:
    print(f"{'OK  ' if cond else 'FAIL'} {what}")
    if not cond:
        fails.append(what)


def main() -> int:
    for s in (sys.stdout,):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sh = (SRC / "scripts" / "request.sh").read_text(encoding="utf-8")
    code_lines = [l for l in sh.splitlines() if not l.lstrip().startswith("#")]
    ok(not any("--bare" in l for l in code_lines), "request.sh 에 --bare 가 없다")
    ok('cd "$(dirname "$0")/.."' in sh, "request.sh 가 이 프로젝트 폴더로 들어간다")
    ok("--setting-sources project" in sh, "request.sh 가 개인 설정을 뺀다(--setting-sources project)")
    ok("--strict-mcp-config" in sh, "request.sh 가 계정의 커넥터를 싣지 않는다(--strict-mcp-config)")
    with tempfile.TemporaryDirectory(prefix="scripts-") as t:
        root = Path(t) / "blog"
        shutil.copytree(SRC, root, ignore=shutil.ignore_patterns("requests", "drafts", "logs", "__pycache__"))
        log = Path(t) / "claude-calls.log"
        fake = Path(t) / "claude"
        fake.write_text(f"#!/bin/sh\necho \"$@\" >> {log}\necho '{{}}'\n", encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        # 임시 폴더는 꾸러미 밖이라 uv 가 .venv 를 못 찾는다 — 지금 이 시험을 실행한 가상환경을 알려 준다
        env = dict(os.environ, CLAUDE_BIN=str(fake), PYTHONUTF8="1", VIRTUAL_ENV=sys.prefix)
        run = lambda *a: subprocess.run(["bash", "scripts/request.sh", *a], cwd=root, env=env,
                                        capture_output=True, text=True, encoding="utf-8")
        p = run("--dry-run", "--slot", "2026-W36")
        ok(p.returncode == 0 and "claude" in p.stdout and " 2026-W36 " in p.stdout and "-p /" in p.stdout,
           "--dry-run 은 부를 줄만 찍는다 (11차시 전에는 /draft, 뒤에는 /handle-request)")
        ok(not (root / "requests" / "2026-W36").exists(), "--dry-run 은 요청을 열지 않는다")
        run("--slot", "2026-W36")
        calls1 = log.read_text(encoding="utf-8").count("-p /") if log.exists() else 0
        p2 = run("--slot", "2026-W36")
        calls2 = log.read_text(encoding="utf-8").count("-p /") if log.exists() else 0
        ok(calls1 == 1, "첫 실행은 claude 를 한 번 부른다")
        ok(calls2 == 1 and "skip: already ran 2026-W36" in p2.stdout,
           "같은 주차 둘째 실행은 부르지 않고 건너뛴다 (skip: already ran 2026-W36)")
        ok(not (root / "requests" / "2026-W36.running").exists(), "끝난 실행은 처리 중 표를 남기지 않는다")

        # 첫 실행이 Claude 를 기다리는 동안 둘째가 시작된다 — 느린 가짜 claude 로 겹치게 한다
        slow = Path(t) / "slow-claude"
        slow.write_text(f"#!/bin/sh\necho \"$@\" >> {log}\nsleep 3\necho '{{}}'\n", encoding="utf-8")
        slow.chmod(slow.stat().st_mode | stat.S_IEXEC)
        senv = dict(env, CLAUDE_BIN=str(slow))
        start = lambda: subprocess.Popen(["bash", "scripts/request.sh", "--slot", "2026-W37"], cwd=root, env=senv,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        a = start()
        time.sleep(1.5)
        b = start()
        outs = [x.communicate()[0] for x in (a, b)]
        calls3 = log.read_text(encoding="utf-8").count("-p /") - calls2
        ok(calls3 == 1 and any("skip: 2026-W37 은 다른 실행이 처리하는 중이다" in o for o in outs)
           and a.returncode in (0, 1, 3) and b.returncode == 0,
           "겹친 둘째 실행은 부르지 않고 건너뛴다 (skip: 2026-W37 은 다른 실행이 처리하는 중이다)")

        # 멈춘 실행이 남긴 표 — 주인 번호가 이미 끝난 프로그램이면 치우고 이어서 한다
        gone = subprocess.Popen([sys.executable, "-c", "pass"])
        gone.wait()
        p = subprocess.run([sys.executable, "scripts/open_request.py", "--slot", "2026-W38"], cwd=root, env=env,
                           capture_output=True, text=True, encoding="utf-8")
        (root / "requests" / "2026-W38.running").write_text(f"{gone.pid}\n", encoding="utf-8")
        p = run("--slot", "2026-W38")
        calls4 = log.read_text(encoding="utf-8").count("-p /") - calls2 - calls3
        ok(calls4 == 1 and "resume: 2026-W38" in p.stdout and not (root / "requests" / "2026-W38.running").exists(),
           "주인이 사라진 표는 치우고 멈춘 단계부터 이어서 한다 (resume: 2026-W38)")
    print("\n스크립트 시험: " + ("통과" if not fails else f"{len(fails)}건 다름"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
