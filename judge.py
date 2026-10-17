"""차시 판정 — 이번 차시에 지은 것이 작동하는지 봅니다.

    uv run python judge.py 05            5차시 판정
    uv run python judge.py 11 --all      11차시까지 앞 차시 판정을 한 번에 다시
    uv run python judge.py 05 --before   짓기 전에 보여야 하는 신호가 나오는지
    uv run python judge.py --list        차시와 명령 목록

저장소 맨 위 폴더에서 실행합니다. 판정할 명령과 기대하는 신호는 `hackers.yaml` 에 있습니다.
전부 기대대로면 0, 하나라도 다르면 1 로 끝납니다.

이 판정은 "작동하는가" 만 봅니다. "직접 지었나" 는 보지 않습니다.
AI 를 부르지 않습니다 — 모든 명령이 저장해 둔 초안이나 정해 둔 입력(차단 장치 JSON)으로 실행됩니다.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "hackers.yaml"
PLACEHOLDER = "(여기에 씁니다)"
UNFILLED = "차시에 채웁니다."
REFERENCE = "https://github.com/euisuk-chung/harness-p1-blog.git"   # 공개 실습 저장소 — 태그 h03 … 를 여기서 받는다


def _utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def load() -> dict:
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML 이 없습니다. 먼저 설치합니다:\n"
                         "  uv sync   (저장소 맨 위에서)")
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def key(n: str) -> str:
    return f"{int(n):02d}"


def env_for(tmp: Path) -> dict[str, str]:
    env = dict(os.environ)
    for name in ("REQUEST_ID", "HACKERS_PR", "CLAUDE_PROJECT_DIR", "ALERT_CRASH_AFTER_SEND"):
        env.pop(name, None)
    env["PYTHONUTF8"] = "1"
    env["HARNESS_CLAIMS_DIR"] = str(tmp / "claims")
    return env


def run(cmd: str, cwd: Path, env: dict[str, str], stdin: str | None) -> tuple[int, str]:
    argv = shlex.split(cmd)
    if argv[:2] == ["uv", "run"]:               # uv run python … — 판정이 이미 그 가상환경의 파이썬이다
        argv = argv[2:]
    if argv and argv[0] in ("python", "python3", "py"):
        argv[0] = sys.executable
    try:
        proc = subprocess.run(argv, cwd=str(cwd), env=env, text=True, capture_output=True,
                              encoding="utf-8", errors="replace",
                              input=stdin if stdin is not None else "", timeout=600)
    except subprocess.TimeoutExpired:
        return -1, "시간 안에 끝나지 않았습니다"
    return proc.returncode, proc.stdout + proc.stderr


def prd_filled(title: str) -> tuple[int, str]:
    """PRD.md 에서 제목에 title 이 든 절이 채워졌나. 채움 0, 빈 채 1."""
    path = ROOT / "PRD.md"
    if not path.is_file():
        return 1, "PRD.md 가 없습니다"
    body, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = title in line
            continue
        if inside:
            body.append(line)
    if not inside and not body:
        return 1, f"'{title}' 절이 없습니다"
    text = "\n".join(body)
    if UNFILLED in text or not text.strip():
        return 1, "아직 비어 있습니다"
    return 0, "채워져 있습니다"


def table_filled(spec: dict) -> tuple[int, str]:
    """다른 계획서 파일(spec['file'])에서 제목에 spec['title'] 이 든 절의 표가 줄마다 둘째 칸까지 찼나. 참 0, 빈 칸 1.
    16차시의 내 업무 계획서(my-work-PRD.md) 끝에 붙이는 표 셋을 본다 — 내용이 맞는지는 사람이 읽는다."""
    path = ROOT / spec["file"]
    if not path.is_file():
        return 1, f"{spec['file']} 가 없습니다"
    rows, inside, found = [], False, False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = spec["title"] in line
            found = found or inside
            continue
        if inside and line.lstrip().startswith("|"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    if not found:
        return 1, f"'{spec['title']}' 절이 없습니다"
    body = [r for r in rows[1:] if not all(set(c) <= set("-: ") for c in r)]  # 머리 줄과 --- 줄은 뺀다
    if not body:
        return 1, "표가 없습니다"
    empty = [r[0] for r in body if len(r) < 2 or not r[1]]
    if empty:
        return 1, "빈 줄: " + ", ".join(empty[:4])
    return 0, f"{len(body)}줄 모두 채워져 있습니다"


def empty_sections() -> list[str]:
    path = ROOT / "PRD.md"
    if not path.is_file():
        return []
    empty, title = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
        elif title and PLACEHOLDER in line and title not in empty:
            empty.append(title)
    return empty


def git_ok(args: list[str]) -> bool:
    try:
        return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def judge_files(lesson: dict) -> int:
    failed = 0
    for rel in lesson.get("files", []):
        ok = (ROOT / rel).is_file()
        failed += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAIL'} 03  있어야 하는 파일: {rel}")
    if lesson.get("first_commit"):
        ok = git_ok(["rev-parse", "--verify", "--quiet", "HEAD"]) and git_ok(["ls-files", "--error-unmatch", "PRD.md"])
        failed += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAIL'} 03  첫 저장(커밋)에 PRD.md 가 들어 있다")
    empty = empty_sections()
    if empty:
        print(f"     참고 — 아직 빈 내 칸: {', '.join(empty)}")
    return failed


def judge_check(n: str, lesson: dict, check: dict, mode: str, tmp: Path) -> int | None:
    """한 줄 판정. 맞으면 0, 다르면 1, 이 모드에서 볼 것이 없으면 None."""
    want = check.get("before") if mode == "before" else check.get("expect", 0)
    if want is None:
        return None
    cwd = ROOT / lesson.get("dir", "blog")
    if "prd_filled" in check:
        got, note = prd_filled(check["prd_filled"])
        label = f"PRD.md '{check['prd_filled']}' 절"
    elif "table_filled" in check:
        got, note = table_filled(check["table_filled"])
        label = f"{check['table_filled']['file']} '{check['table_filled']['title']}' 표"
    else:
        got, out = run(check["run"], cwd, env_for(tmp), check.get("stdin"))
        label = check["run"] + (f"   (입력: {check['stdin']})" if "stdin" in check else "")
        note = ""
        if mode != "before" and got == want:
            note = extra(check, cwd, out)
    ok = got == want and not note.startswith("다름")
    where = lesson.get("dir", "blog")
    print(f"{'OK  ' if ok else 'FAIL'} {n}  [{where}] {label} → {got} (기대 {want})" + (f"  — {note}" if note else ""))
    return 0 if ok else 1


def extra(check: dict, cwd: Path, out: str) -> str:
    """신호 말고 더 볼 것: 결과 파일의 칸, 화면의 글."""
    problems = []
    if "output_has" in check and check["output_has"] not in out:
        problems.append(f"화면에 '{check['output_has']}' 가 없습니다")
    result_path = None
    argv = shlex.split(check.get("run", ""))
    if "--result-json" in argv:
        result_path = cwd / argv[argv.index("--result-json") + 1]
    if ("result" in check or "no_file_in_run" in check) and result_path is not None:
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return f"다름 — 결과 파일을 읽을 수 없습니다: {result_path.name}"
        for field, value in (check.get("result") or {}).items():
            if result.get(field) != value:
                problems.append(f"{field} 가 {result.get(field)!r} (기대 {value!r})")
        name = check.get("no_file_in_run")
        if name and result.get("run_dir") and (Path(result["run_dir"]) / name).exists():
            problems.append(f"실행 기록 폴더에 {name} 가 있습니다")
    if problems:
        return "다름 — " + " · ".join(problems)
    shown = []
    if "result" in check:
        shown.append(" · ".join(f"{k}={v!r}" for k, v in check["result"].items()))
    if "no_file_in_run" in check:
        shown.append(f"{check['no_file_in_run']} 없음")
    return ", ".join(shown)


def restore_hint(lesson: dict) -> None:
    """막히면 — 이번 차시 끝 상태를 공개 실습 저장소의 태그(h05 …)에서 받는 명령을 찍는다."""
    tag = lesson.get("tag")
    if not tag:
        return
    where = lesson.get("dir", "blog")
    files = " ".join(f"{where}/{f}" for f in lesson.get("builds", []))
    print(f"\n막히면 고치지 않고 이번 차시의 완성 조각을 공개 실습 저장소의 태그 {tag} 에서 받습니다 (저장소 맨 위에서):")
    if not git_ok(["rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"]):
        print(f"  git fetch {REFERENCE} --tags")
    print(f"  git restore --source {tag} -- {files}")
    if lesson.get("prd"):
        print(f"계획서 고정 칸은 따로 된 파일로 받아, 그 내용을 PRD.md 의 같은 제목 절에 붙여 넣습니다"
              f" (PRD.md 를 통째로 받으면 내가 쓴 칸이 지워집니다):\n"
              f"  git restore --source {tag} -- {lesson['prd']}")


def main() -> int:
    _utf8()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lesson", nargs="?", help="차시 번호 (예: 05)")
    p.add_argument("--all", action="store_true", help="이번 차시까지 앞 차시 판정도 한 번에")
    p.add_argument("--before", action="store_true", help="짓기 전 신호를 본다")
    p.add_argument("--list", action="store_true", help="차시와 명령 목록")
    a = p.parse_args()
    spec = load()
    lessons = {key(k): v for k, v in spec["lessons"].items()}

    if a.list or not a.lesson:
        for n, lesson in sorted(lessons.items()):
            print(f"{n}  {lesson['title']}")
            for c in lesson.get("checks", []):
                what = c.get("run") or (f"PRD.md '{c['prd_filled']}' 절" if "prd_filled" in c
                                        else f"{c['table_filled']['file']} '{c['table_filled']['title']}' 표")
                print(f"      [{lesson.get('dir', 'blog')}] {what} → {c.get('expect', 0)}"
                      + (f" (짓기 전 {c['before']})" if "before" in c else ""))
        return 0

    target = key(a.lesson)
    if target not in lessons:
        print(f"판정이 없는 차시입니다: {target}. 있는 것: {', '.join(sorted(lessons))}")
        return 1
    if a.all and a.before:
        print("--all 과 --before 는 같이 쓰지 않습니다.")
        return 1
    order = [n for n in sorted(lessons) if n <= target] if a.all else [target]
    mode = "before" if a.before else "after"

    failed = 0
    with tempfile.TemporaryDirectory(prefix=f"judge-{target}-") as tmp:
        for n in order:
            lesson = lessons[n]
            if "files" in lesson or "first_commit" in lesson:
                if mode == "after":
                    failed += judge_files(lesson)
                continue
            where = lesson.get("dir", "blog")
            if not (ROOT / where).is_dir():
                failed += 1
                later = {"alert": "14", "triage": "15"}.get(where)
                print(f"FAIL {n}  [{where}] 폴더가 없습니다" + (f" — {later}차시 첫머리에서 clone 합니다" if later else ""))
                continue
            for check in lesson.get("checks", []):
                if a.all and n != target and "until" in check and key(check["until"]) < target:
                    continue
                r = judge_check(n, lesson, check, mode, Path(tmp))
                failed += r or 0
    label = "짓기 전 모습" if mode == "before" else "판정"
    print(f"\n{target}차시 {label}: " + ("통과" if not failed else f"{failed}건이 기대와 다릅니다"))
    if failed and mode == "after" and not a.all:
        restore_hint(lessons[target])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
