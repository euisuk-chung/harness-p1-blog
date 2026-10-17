"""승인 화면에 붙일 근거. 저장된 초안을 규칙으로 다시 검사하며 모델·GitHub를 부르지 않는다.

기존 승인 신호나 권한은 바꾸지 않는다. 이 카드는 서명·승인 장치가 아니며,
기록 뒤의 변경, 실행 환경, 주장의 의미와 실제 발행 여부를 보증하지 않는다.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

GUARDS = ("G1", "G2", "G3", "G4", "G5")
LIMITS = [
    "저장된 초안의 규칙 검사만 실행했다. 새 모델 출력·실제 발행·외부 서비스는 확인하지 않았다.",
    "인용과 주장의 의미 일치, 정보의 사실성·최신성은 사람이 확인해야 한다.",
    "파일 지문은 변화를 찾는 값이며 서명이나 승인 기록이 아니다. 실행 환경·의존성 전체는 고정하지 않았다.",
]


def digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def snapshot(root: Path, paths: list[Path]) -> dict:
    # 꾸러미 밖의 파일이나 절대 경로는 카드에 담지 않는다.
    result = {}
    for path in sorted(set(paths)):
        resolved = path.resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise ValueError("검사 입력이 프로젝트 폴더 밖을 가리킨다")
        result[path.relative_to(root).as_posix()] = digest(path)
    return result


def build(root: Path, rid: str, out: Path) -> dict:
    d = root / "requests" / rid
    command = [sys.executable, "review.py", "--request", rid]
    card = {"schema_version": 1, "request": rid, "scope": "saved-draft-rule-check",
            "command": shlex.join(["python", *command[1:]]), "exit": None,
            "expected": "G1~G5 모두 pass, 신호 0", "observed": "미확인",
            "checks": {}, "limits": LIMITS.copy()}
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                  text=True, timeout=10)
        card["code_revision"] = revision.stdout.strip() if revision.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        card["code_revision"] = None
    if not card["code_revision"]:
        card["limits"].append("Git 커밋을 읽지 못했다. 아래 파일 지문만 남긴다.")
    try:
        state = json.loads((d / "state.json").read_text(encoding="utf-8"))
        name = state["case"]
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("케이스 이름 형식")
        case_path = root / "cases" / f"{name}.yaml"
        case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
        if not isinstance(case, dict) or not isinstance(case.get("sources") or {}, dict):
            raise ValueError("케이스 자료 목록 형식")
        inputs = [d / "draft.json", d / "state.json", case_path]
        inputs += [case_path.parent / p for p in (case.get("sources") or {}).values()]
        code = [root / p for p in ("review.py", "lib/case.py", "lib/_utf8.py", "lib/schema_contract.py", "schema.json",
                                   "schema.strict.json", "scripts/render.py", "scripts/approval_evidence.py")]
        code += list((root / "checks").glob("*.py"))
        dirty = subprocess.run(["git", "status", "--porcelain", "--",
                                *[p.relative_to(root).as_posix() for p in code]],
                               cwd=root, capture_output=True, text=True, timeout=10)
        card["code_worktree_changed"] = bool(dirty.stdout.strip()) if dirty.returncode == 0 else None
        before = snapshot(root, inputs + code + [out])
        card.update(case=name, files=before, input_sha256=before[(d / "draft.json").relative_to(root).as_posix()],
                    artifact=out.relative_to(root).as_posix(), artifact_sha256=digest(out))
        # 원래 요청의 review.json을 건드리지 않고, 지금 파일의 사본만 검사한다.
        # 사본에 예전 review.json은 넣지 않으므로 오래된 pass를 새 실행 결과로 읽지 않는다.
        with tempfile.TemporaryDirectory(prefix="approval-evidence-") as t:
            copied = Path(t)
            for path in inputs + code:
                target = copied / path.relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            card["checked_files"] = snapshot(copied, [copied / p.relative_to(root) for p in inputs + code])
            card["snapshot_matches_inputs"] = all(before[p] == value for p, value in card["checked_files"].items())
            run = subprocess.run(command, cwd=copied, capture_output=True, text=True, encoding="utf-8", timeout=30)
            card["exit"] = run.returncode
            result_path = copied / "requests" / rid / "review.json"
            if result_path.exists():
                checks = json.loads(result_path.read_text(encoding="utf-8"))
                if not isinstance(checks, dict) or not all(isinstance(v, dict) for v in checks.values()):
                    raise ValueError("검사 결과 형식")
                card["checks"] = checks
            # 검사한 초안으로 만든 글이 승인 대상 글과 같은지도 확인한다.
            rendered = subprocess.run([sys.executable, "scripts/render.py", rid], cwd=copied,
                                      capture_output=True, text=True, encoding="utf-8", timeout=30)
            card["render_exit"] = rendered.returncode
            card["checked_artifact_sha256"] = digest(copied / out.relative_to(root))
            card["render_matches_artifact"] = (rendered.returncode == 0 and
                                                card["checked_artifact_sha256"] == card["artifact_sha256"])
        after = snapshot(root, inputs + code + [out])
        card["files_unchanged"] = before == after and all(v is not None for v in before.values())
        checks = card["checks"]
        complete = set(checks) == set(GUARDS) and all(isinstance(checks[g].get("pass"), bool) for g in GUARDS)
        if not card["files_unchanged"] or not card["snapshot_matches_inputs"]:
            card["observed"] = "미확인: 검사 사본과 원래 파일이 다르거나 검사 중 파일이 바뀌었다"
        elif not card["render_matches_artifact"]:
            card["observed"] = "미확인: 검사한 초안으로 만든 글과 승인 대상 글이 다르다"
        elif run.returncode == 0 and complete and all(checks[g]["pass"] for g in GUARDS):
            card["observed"] = "일치: G1~G5 모두 pass, 신호 0"
        elif run.returncode == 1 and checks:
            card["observed"] = "불일치: 규칙 검사 거부"
        else:
            card["observed"] = "미확인: 검사 실패 또는 결과 누락"
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, subprocess.TimeoutExpired) as e:
        card["limits"].append(f"근거를 완성하지 못했다 ({type(e).__name__}). 통과로 읽지 않는다.")
    return card


def markdown(card: dict) -> str:
    changed = {True: "있음", False: "없음", None: "미확인"}[card.get("code_worktree_changed")]
    lines = ["## 승인 전 확인 근거", "", f"- 요청: {card['request']}",
             f"- 검사 코드 커밋: {card.get('code_revision') or '미확인'} (작업 파일의 지문은 아래에 별도 기록)",
             f"- 커밋 뒤 검사 코드 변경: {changed}",
             f"- 실행: `{card['command']}` (현재 파일의 임시 사본) / 신호: {card['exit'] if card['exit'] is not None else '미확인'}",
             f"- 기대: {card['expected']}", f"- 관찰: {card['observed']}",
             f"- 입력 SHA-256: {card.get('input_sha256') or '미확인'}",
             f"- 글 파일: {card.get('artifact') or '미확인'}",
             f"- 글 SHA-256: {card.get('artifact_sha256') or '미확인'}", "",
             f"- 검사 사본 지문 일치: {card.get('snapshot_matches_inputs', '미확인')}",
             f"- 검사 초안으로 만든 글 일치: {card.get('render_matches_artifact', '미확인')}", "",
             "| 검사 | 이번 판정 |", "|---|---|"]
    for guard in GUARDS:
        result = card["checks"].get(guard, {}).get("pass")
        lines.append(f"| {guard} | {'pass' if result is True else 'rejected' if result is False else '미실행·미확인'} |")
    lines += ["", "### 확인하지 못한 것", "", *[f"- {x}" for x in card["limits"]],
              "", "### 대조할 파일 지문 (SHA-256)", ""]
    lines += [f"- `{path}`: {value or '없음'}" for path, value in card.get("files", {}).items()]
    return "\n".join(lines) + "\n"


def write(root: Path, rid: str, out: Path) -> str:
    card = build(root, rid, out)
    body = markdown(card)
    d = root / "requests" / rid
    (d / "approval-evidence.json").write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (d / "approval-evidence.md").write_text(body, encoding="utf-8")
    return body
