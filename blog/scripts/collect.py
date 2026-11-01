"""수집 — 케이스에 적힌 원문을 요청 폴더로 모은다. 모델을 부르지 않는다.

    uv run python scripts/collect.py <요청 id>

실습에서는 케이스(cases/*.yaml)에 적힌 고정 원문을 읽는다. 실무라면 여기가 RSS·API·크롤러다.
바뀌는 것은 이 스크립트 하나이고, 뒤의 작성·검수는 그대로다.

만드는 것: requests/<id>/sources/<파일> (원문 사본) · requests/<id>/brief.json (꼭 다룰 항목 · 원문 목록)
원문이 하나도 없거나 빠진 파일이 있으면 64(실행 환경 문제)로 끝난다.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
from case import Case  # noqa: E402


def main() -> int:
    rid = sys.argv[1]
    d = ROOT / "requests" / rid
    state = json.loads((d / "state.json").read_text(encoding="utf-8"))
    case = Case.load(ROOT / "cases" / f"{state['case']}.yaml")
    if not case.sources:
        print("collect: 원문이 하나도 없다 — cases/*.yaml 의 sources 를 본다")
        return 64
    out = d / "sources"
    out.mkdir(exist_ok=True)
    names, missing = {}, []
    for sid, rel in case.sources.items():
        src = case.root / rel
        if not src.is_file():
            missing.append(sid)
            continue
        shutil.copyfile(src, out / src.name)
        names[sid] = src.name
    if missing:
        print(f"collect: 원문 파일이 없다: {', '.join(missing)}")
        return 64
    brief = {"sources": names,
             "required": [{"id": r["id"], "kind": r["kind"], "cite": r.get("cite"), "about": r.get("find")}
                          for r in case.required]}
    (d / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"collect: 원문 {len(names)}건, 꼭 다룰 항목 {len(case.required)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
