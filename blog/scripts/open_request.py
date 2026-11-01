"""요청 열기·마무리 — 모델을 부르지 않는다.

    uv run python scripts/open_request.py --slot 2026-W36 [--case case-01-standard]   주간 요청(같은 주는 한 번만)
    uv run python scripts/open_request.py --case case-01-standard                     연습 요청(열 때마다 새 번호)
    uv run python scripts/open_request.py <케이스 이름>                                 연습 요청(--case 와 같다 — 대화 창의 /draft 가 쓴다)
    uv run python scripts/open_request.py <요청 id>                                    이미 연 요청의 지금 안내
    uv run python scripts/open_request.py --finish <요청 id>                           claude 가 끝난 뒤 마무리

주간 요청의 id 는 주차(slot) 그대로다 — "2026년 36주차 블로그" 는 하나뿐이다. 이미 끝난 주차면
Claude 를 부르지 않고 건너뛴다. 끝 상태가 없으면 멈춘 요청이라 멈춘 단계부터 이어서 하는데, 상태 파일만
보면 "아직 일하는 중" 과 "멈췄다" 를 가르지 못한다. 그래서 주간 요청을 처리하는 동안에는 처리 중 표
requests/<주차>.running 을 두고, 표의 주인(request.sh 가 REQUEST_OWNER 로 넘기는 자기 번호)이 살아 있으면
둘째 실행은 건너뛴다. 주인이 사라진 표(멈춘 실행이 남긴 것)는 치우고 이어서 한다. 표는 --finish 가 치운다.

끝날 때 신호
  열기     0 작성이 필요하다(claude 를 부른다) · 10 이미 끝났거나 다른 실행이 처리하는 중(건너뜀) · 64 케이스가 없다
  마무리   0 published · 3 needs_human(승인 대기 포함) · 1 failed
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
from _state import REQ, advance, event, load, rdir, save, utf8  # noqa: E402

SKIP = 10
# 한 번 부른 Claude 는 limited.py 가 10분에 끊는다. 30분 넘은 표는 주인 번호가 살아 있어도(번호가 다른
# 프로그램에 다시 쓰였을 수 있다) 주인이 사라진 표로 본다.
STALE = 30 * 60


def running_mark(slot: str) -> Path:
    return REQ / f"{slot}.running"


def alive(pid: int) -> bool:
    if os.name == "nt":                         # 윈도우의 os.kill 은 묻지 않고 끝내 버린다 — 주간 실행은 WSL 에서만
        return False
    try:
        os.kill(pid, 0)                         # 신호 0 은 보내지 않고 "있나" 만 묻는다
    except ProcessLookupError:
        return False
    except PermissionError:                     # 있지만 남의 것
        return True
    return True


def take_mark(slot: str) -> bool:
    """처리 중 표를 만든다. 이미 있으면 실패하는 동작이라 동시에 만들어도 하나만 성공한다."""
    mark = running_mark(slot)
    owner = int(os.environ.get("REQUEST_OWNER") or os.getpid())
    for _ in range(3):
        try:
            fd = os.open(mark, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                pid = int(mark.read_text(encoding="utf-8").split()[0])
                fresh = time.time() - mark.stat().st_mtime < STALE
            except (FileNotFoundError, ValueError, IndexError):
                pid, fresh = 0, False
            if pid and fresh and alive(pid):
                return False
            mark.unlink(missing_ok=True)        # 주인이 사라진 표 — 치우고 다시
            continue
        os.write(fd, f"{owner}\n".encode())
        os.close(fd)
        return True
    return False


def new_state(rid: str, case: str, trigger: str) -> dict:
    return {"id": rid, "case": case, "trigger": trigger, "at": "collect", "visits": {}, "history": [],
            "tool_calls": 0, "terminal": None, "reason": ""}


def start(rid: str, case: str, trigger: str) -> int:
    save(rid, new_state(rid, case, trigger))
    event(rid, "triggered", trigger=trigger, case=case)
    (REQ / ".current").write_text(rid, encoding="utf-8")
    print(trigger)
    r = advance(rid, "open")
    print(r["message"])
    print(f"REQUEST_ID={rid}")
    return 0 if r["need"] else finish_code(load(rid))


def open_slot(slot: str, case: str) -> int:
    if not (ROOT / "cases" / f"{case}.yaml").is_file():
        print(f"그런 케이스가 없다: {case}")
        return 64
    REQ.mkdir(exist_ok=True)
    if not take_mark(slot):                     # 처리 중 표를 먼저 잡는 쪽 하나만 들어간다
        print(f"skip: {slot} 은 다른 실행이 처리하는 중이다")
        return SKIP
    try:
        rdir(slot).mkdir()
    except FileExistsError:
        st = load(slot)
        if st.get("terminal"):
            running_mark(slot).unlink(missing_ok=True)
            print(f"skip: already ran {slot} ({st['terminal']})")
            return SKIP
        if st:
            print(f"resume: {slot} 은 {st.get('at')} 단계에서 멈춰 있다")
            return reopen(slot)
        # 폴더만 있고 상태 파일이 없다 — 열다가 멈췄다. 처음부터 연다
    return start(slot, case, f"schedule:weekly:{slot}")


def open_practice(case: str) -> int:
    if not (ROOT / "cases" / f"{case}.yaml").is_file():
        print(f"그런 케이스가 없다: {case}")
        return 64
    REQ.mkdir(exist_ok=True)
    n = 1
    while True:
        rid = f"{case}-{n}"
        try:
            rdir(rid).mkdir()
            break
        except FileExistsError:
            n += 1
    return start(rid, case, f"manual:{case}")


def reopen(rid: str) -> int:
    if not load(rid):
        print(f"그런 요청이 없다: {rid}")
        return 64
    (REQ / ".current").write_text(rid, encoding="utf-8")
    r = advance(rid, "open")
    print(r["message"])
    print(f"REQUEST_ID={rid}")
    return 0 if r["need"] else finish_code(load(rid))


def finish_code(st: dict) -> int:
    return {"published": 0, "needs_human": 3}.get(st.get("terminal"), 1)


def path_lines(st: dict) -> list[str]:
    """지나온 길을 화면 줄로. 검수가 거부한 뒤 다시 작성한 것은 retry n/m 으로 적는다."""
    hist = st.get("history", [])
    out, first, retry, cap, i = [], [], 0, 3, 0
    while i < len(hist) and not (hist[i]["step"] == "review" and hist[i]["signal"] != 0):
        first.append(hist[i]["step"])
        i += 1
    if i >= len(hist):
        out.append(" → ".join(first + [st.get("terminal") or "?"]))
        if st.get("terminal") == "needs_human" and not st.get("reason"):
            out.append("done: needs_human — 승인 대기(PR 을 사람이 합친다)")
        elif st.get("reason"):                       # 거부 없이 끝났어도 이유가 있으면 화면에 (예: 도구 호출 상한)
            out.append(f"done: {st.get('terminal')} — {st['reason']}")
        return out
    first.append("review")
    out.append(" → ".join(first))
    out.append(f"review: {hist[i]['note'].replace('review: ', '')}")
    i += 1
    while i < len(hist):
        h = hist[i]
        if h["step"] == "draft":
            retry += 1
            nxt = hist[i + 1] if i + 1 < len(hist) else None
            tail = ""
            if nxt and nxt["step"] == "review":
                tail = " → review: " + ("pass" if nxt["signal"] == 0 else nxt["note"].replace("review: ", ""))
                i += 1
            out.append(f"draft (retry {retry}/{cap - 1}){tail}")
        else:
            out.append(h["step"])
        i += 1
    out.append(f"done: {st.get('terminal')}" + (f" — {st['reason']}" if st.get("reason") else ""))
    return out


def finish(rid: str) -> int:
    st = load(rid)
    if not st:
        print(f"그런 요청이 없다: {rid}")
        return 1
    if not st.get("terminal"):
        advance(rid, "finish")
        st = load(rid)
    for line in path_lines(st):
        print(line)
    cur = REQ / ".current"
    if cur.is_file() and cur.read_text(encoding="utf-8").strip() == rid:
        cur.unlink()
    running_mark(rid).unlink(missing_ok=True)
    return finish_code(st)


def main() -> int:
    utf8()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rid", nargs="?", help="이미 연 요청 id")
    p.add_argument("--slot", help="주간 요청의 주차, 예: 2026-W36")
    p.add_argument("--case", help="케이스 이름 (주간 요청의 기본은 case-01-standard)")
    p.add_argument("--finish", metavar="요청_ID", help="claude 가 끝난 뒤 마무리")
    a = p.parse_args()
    if a.finish:
        return finish(a.finish)
    if a.slot:
        return open_slot(a.slot, a.case or "case-01-standard")
    if a.case:
        return open_practice(a.case)
    if a.rid and (ROOT / "cases" / f"{a.rid}.yaml").is_file():
        return open_practice(a.rid)
    if a.rid:
        return reopen(a.rid)
    p.print_help()
    return 64


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Ctrl+C 로 끊으면 긴 오류 대신 한 줄 — 요청은 멈춘 단계에 남고, 같은 명령을 다시 치면 거기서 이어서 한다
        print("\nopen_request: 끊겼다 — 요청은 멈춘 단계에 남아 있고, 같은 명령을 다시 치면 거기서 이어서 한다")
        sys.exit(130)
