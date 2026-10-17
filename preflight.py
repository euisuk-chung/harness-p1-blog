"""실습 전 점검 — 이 컴퓨터와 이 저장소가 실습에 필요한 것을 갖췄는지 봅니다. 모델을 부르지 않습니다.

    uv run python preflight.py
    echo $?          # 전부 OK 면 0, 하나라도 MISS 면 1

저장소 맨 위 폴더에서 실행합니다. 줄마다 왼쪽 네 글자(OK / MISS / --)를 먼저 읽고,
MISS 면 그 줄의 `—` 뒤에 적힌 할 일을 합니다. `--` 는 아직 짓지 않은 것이라 괜찮다는 뜻입니다.

두 부분으로 봅니다.
  1. 이 컴퓨터   uv 와 가상환경(.venv) · git · gh · Claude Code 와 로그인
  2. 선언         blog · alert · triage 의 .claude/ 선언이 서로 맞물리나
                  (설정에 등록한 장치 파일이 있나 · drafter 의 도구 목록 · 흐름도 단계 이름 ·
                   세 프로젝트의 공통 장치 코드가 같은가)
                  alert · triage 는 14 · 15차시 첫머리에 clone 하니, 그 전에는 없어도 MISS 가 아니라 -- 입니다

    uv run python preflight.py --project mywork
    uv run python preflight.py --project mywork --declarations   "2. 프로젝트 선언" 만 (판정 16 이 쓴다)
                  16차시에 블로그를 복사해 지은 내 업무 폴더 하나만 선언을 보고,
                  공통 장치 코드가 blog 와 같은지 본다

Claude Code 의 차단 장치(`<프로젝트>/.claude/settings.json`)는 `uv run python` 으로 파이썬을 부릅니다.
uv 는 부른 폴더에서 위로 올라가며 가상환경(`.venv`)을 찾으니, 저장소 맨 위에 `.venv` 가 있어야
프로젝트 폴더의 장치가 같은 파이썬과 라이브러리를 씁니다. 그래서 따로 봅니다.
"""
from __future__ import annotations

import filecmp
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIN = (3, 11)
INSTALL = "uv sync"
PROJECTS = ("blog", "alert", "triage")
SHARED_HOOKS = ("_state.py", "guard.py", "run_review.py", "next_step.py", "show_status.py")
WORDS = {"request", "collect", "draft", "review", "approve", "deliver"}
# 요청 하나를 처리하는 명령. 작성은 drafter 에게 맡겨야 한다. 개선 명령(improve.md)처럼
# 다른 담당에게 맡기는 명령은 이 검사에 넣지 않는다.
REQUEST_COMMANDS = ("draft.md", "handle-request.md")
# 따로 있는 저장소를 뒤 차시 첫머리에 clone 해 오는 폴더 — 그 전에는 없는 것이 정상이다
CLONED_LATER = {"alert": "14", "triage": "15"}


def _utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def _run(argv: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, text=True, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def uv_ok() -> tuple[bool, str]:
    """uv 가 PATH 에 있나. 차단 장치·시작 스크립트·cron 이 모두 `uv run python` 으로 파이썬을 부른다."""
    if not shutil.which("uv"):
        return False, "uv 가 PATH 에 없습니다. 설치: curl -LsSf https://astral.sh/uv/install.sh | sh  (설치 뒤 터미널을 새로 엽니다)"
    code, out = _run(["uv", "--version"])
    return code == 0, out.splitlines()[0] if out else ""


def venv_ok() -> tuple[bool, str]:
    """저장소 맨 위에 .venv 가 있고, 프로젝트 폴더에서 `uv run python` 이 그 파이썬을 쓰나."""
    venv = ROOT / ".venv"
    if not venv.is_dir():
        return False, f"저장소 맨 위에 .venv 가 없습니다 — {INSTALL}"
    if not shutil.which("uv"):
        return False, "uv 가 없어 확인하지 못했습니다"
    try:
        proc = subprocess.run(["uv", "run", "python", "-c", "import sys; print(sys.prefix)"],
                              cwd=str(ROOT / "blog") if (ROOT / "blog").is_dir() else str(ROOT),
                              text=True, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    got = proc.stdout.strip()
    if proc.returncode != 0 or Path(got).resolve() != venv.resolve():
        return False, f"blog 폴더의 uv run python 이 이 .venv 를 쓰지 않습니다: {got or proc.stderr.strip()[:80]}"
    return True, ".venv"


def front(path: Path) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    meta: dict[str, str] = {}
    key = None
    for line in (m.group(1).splitlines() if m else []):
        item = line.strip()
        if item.startswith("- ") and key and line[:1].isspace():   # skills:\n  - drafter-rules 같은 목록
            meta[key] = ", ".join(x for x in (meta[key], item[2:].strip()) if x)
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            key = k.strip()
            meta[key] = v.strip()
    return meta


def declarations(project: str) -> list[tuple[str, bool | None, str]]:
    """한 프로젝트의 선언 점검. (이름, 통과 여부 — None 이면 아직 짓지 않음, 메모)"""
    base = ROOT / project
    out: list[tuple[str, bool | None, str]] = []
    if not base.is_dir() and project in CLONED_LATER:
        return [(f"{project}: 폴더", None, f"아직 없습니다({CLONED_LATER[project]}차시 첫머리에 clone 합니다)")]
    settings = base / ".claude" / "settings.json"
    if not settings.is_file():
        return [(f"{project}: .claude/settings.json", None, "아직 없습니다(원문 보호 장치를 지으면 생깁니다)")]
    try:
        hooks = json.loads(settings.read_text(encoding="utf-8")).get("hooks", {})
    except ValueError as e:
        return [(f"{project}: .claude/settings.json 을 읽는다", False, f"JSON 이 깨졌습니다 — {e}")]
    missing = []
    for event, entries in hooks.items():
        for e in entries:
            for h in e.get("hooks", []):
                argv = [h.get("command", ""), *h.get("args", [])]
                for a in argv:
                    if a.endswith(".py"):
                        rel = a.replace("${CLAUDE_PROJECT_DIR}/", "").replace("$CLAUDE_PROJECT_DIR/", "").strip('"')
                        if not (base / rel).is_file():
                            missing.append(f"{event} → {rel}")
                    if "$CLAUDE_PROJECT_DIR" in a and "${CLAUDE_PROJECT_DIR}" not in a and "args" in h:
                        missing.append(f"{event}: exec 형식에서는 ${{CLAUDE_PROJECT_DIR}} 로 적어야 풀립니다")
    out.append((f"{project}: 설정에 등록한 장치 파일이 모두 있다", not missing, ", ".join(missing)))
    agent = base / ".claude" / "agents" / "drafter.md"
    if agent.is_file():
        tools = [t.strip() for t in front(agent).get("tools", "").split(",") if t.strip()]
        ok = bool(tools) and "Bash" not in tools
        why = "tools 가 비었습니다(도구를 전부 물려받습니다)" if not tools else ("drafter 에게 Bash 가 있습니다" if "Bash" in tools else "")
        out.append((f"{project}: drafter 의 도구 목록(비어 있지 않고 Bash 없음)", ok, why))
        # 늘 지킬 규칙은 스킬 drafter-rules 로 떼어 drafter 에만 미리 싣는다. 본 대화와 다른 하위 에이전트가
        # 이 스킬을 불러 쓰지 못하게 settings.json 의 거부 규칙 Skill(drafter-rules) 가 막는다(미리 싣기는 막지 않는다).
        skills = front(agent).get("skills", "")
        skill_file = (base / ".claude" / "skills" / "drafter-rules" / "SKILL.md").is_file()
        denied = "Skill(drafter-rules)" in json.loads(settings.read_text(encoding="utf-8")).get("permissions", {}).get("deny", [])
        miss = [w for w, bad in (("skills: 에 drafter-rules 가 없습니다", "drafter-rules" not in skills),
                                  ("스킬 파일이 없습니다", not skill_file),
                                  ("settings.json 에 거부 규칙 Skill(drafter-rules) 가 없습니다", not denied)) if bad]
        out.append((f"{project}: drafter 만 규칙 스킬을 싣는다(미리 싣기 · 거부 규칙)", not miss, ", ".join(miss)))
    else:
        out.append((f"{project}: .claude/agents/drafter.md", None, "아직 없습니다(작성 단계를 지으면 생깁니다)"))
    cmds = [base / ".claude" / "commands" / n for n in REQUEST_COMMANDS if (base / ".claude" / "commands" / n).is_file()]
    bad = [c.name for c in cmds if "drafter" not in c.read_text(encoding="utf-8")]
    if cmds:
        out.append((f"{project}: 명령이 drafter 에게 맡긴다", not bad, ", ".join(bad)))
    graph = base / "graph.yaml"
    if graph.is_file():
        try:
            import yaml
            steps = set((yaml.safe_load(graph.read_text(encoding="utf-8")) or {}).get("steps", {}))
            odd = sorted(steps - WORDS)
            out.append((f"{project}: 흐름도 단계 이름이 업무 말(수집·작성·검수·승인·전달) 안에 있다", not odd, ", ".join(odd)))
        except Exception as e:  # noqa: BLE001 — 점검은 멈추지 않고 적는다
            out.append((f"{project}: graph.yaml 을 읽는다", False, str(e)[:80]))
    return out


def shared_hooks_same(projects: tuple[str, ...] = PROJECTS) -> tuple[bool, str]:
    """세 프로젝트의 공통 장치 코드는 바이트까지 같아야 한다 — 다른 것은 graph.yaml·policies.yaml 뿐."""
    diff = []
    for name in SHARED_HOOKS:
        paths = [ROOT / p / ".claude" / "hooks" / name for p in projects]
        present = [p for p in paths if p.is_file()]
        for p in present[1:]:
            if not filecmp.cmp(present[0], p, shallow=False):
                diff.append(f"{p.parts[-4]}/{name}")
    return not diff, ("다름: " + ", ".join(diff)) if diff else ""


def main() -> int:
    _utf8()
    projects = PROJECTS
    args = sys.argv[1:]
    # --declarations: "2. 프로젝트 선언" 만 보고 그 결과로 끝난다(판정 judge.py 16 이 쓴다 — 로그인 같은 컴퓨터 쪽은 보지 않는다)
    only_decl = "--declarations" in args
    args = [a for a in args if a != "--declarations"]
    if len(args) == 2 and args[0] == "--project":
        name = args[1].strip("/")
        if not (ROOT / name).is_dir():
            print(f"폴더가 없습니다: {name} — 저장소 맨 위에서 실행합니다")
            return 64
        projects = (name,)
    elif args:
        print("쓰는 법: uv run python preflight.py [--project 폴더] [--declarations]")
        return 64
    if only_decl:
        return 0 if print_declarations(projects) else 1
    checks: dict[str, tuple[bool, str]] = {
        "uv": uv_ok(),
        "가상환경 .venv (차단 장치가 쓰는 파이썬)": venv_ok(),
        "Python 3.11+ (이 인터프리터)": (sys.version_info >= MIN, sys.version.split()[0]),
        "PyYAML · jsonschema": (importlib.util.find_spec("yaml") is not None and importlib.util.find_spec("jsonschema") is not None,
                                "" if importlib.util.find_spec("yaml") and importlib.util.find_spec("jsonschema") else f"설치: {INSTALL}"),
        "git": (bool(shutil.which("git")), ""),
        "gh": (bool(shutil.which("gh")), ""),
        "Claude Code": (bool(shutil.which("claude")), ""),
    }
    if checks["Claude Code"][0]:
        code, out = _run(["claude", "--version"])
        checks["Claude Code version"] = (code == 0, out.splitlines()[0] if out else "")
        code, _ = _run(["claude", "auth", "status"])
        checks["Claude Code login"] = (code == 0, "" if code == 0 else "claude 에 로그인합니다 (구독)")
    if checks["gh"][0]:
        code, _ = _run(["gh", "auth", "status"])
        checks["gh login"] = (code == 0, "" if code == 0 else "gh auth login — 내 저장소에 올리고 PR 을 만들 때 씁니다")

    print("1. 이 컴퓨터")
    for name, (passed, note) in checks.items():
        print(f"{'OK  ' if passed else 'MISS'} {name}" + (f"  — {note}" if note else ""))
    print()
    decl_ok = print_declarations(projects)
    return 0 if all(p for p, _ in checks.values()) and decl_ok else 1


def print_declarations(projects: tuple[str, ...]) -> bool:
    """"2. 프로젝트 선언" 을 찍고, 모두 맞으면 True."""
    print("2. 프로젝트 선언")
    decl_ok = True
    for project in projects:
        for name, passed, note in declarations(project):
            mark = "--  " if passed is None else ("OK  " if passed else "MISS")
            decl_ok &= passed is not False
            print(f"{mark} {name}" + (f"  — {note}" if note else ""))
    later = [p for p in projects if p in CLONED_LATER and not (ROOT / p).is_dir()]
    if projects == PROJECTS:
        same, note = shared_hooks_same(tuple(p for p in PROJECTS if p not in later))
        label = "세 프로젝트의 공통 장치 코드가 같다"
        if same and later:
            note = f"{' · '.join(later)} 가 아직 없어서 있는 것끼리만 봤습니다"
    else:
        same, note = shared_hooks_same(("blog", *projects))
        label = f"{projects[0]} 의 공통 장치 코드가 blog 와 같다(고치지 않았다)"
    decl_ok &= same
    mark = "MISS" if not same else ("--  " if later and projects == PROJECTS else "OK  ")
    print(f"{mark} {label}" + (f"  — {note}" if note else ""))
    return decl_ok


if __name__ == "__main__":
    raise SystemExit(main())
