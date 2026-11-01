"""초안(JSON)을 사람이 읽는 글(drafts/<id>.md)로 만든다. 모델을 부르지 않는다.

    uv run python scripts/render.py <요청 id>

모델은 JSON 만 낸다. 글은 이 틀이 만든다 — 그래야 검수가 부분 문자열 대조로 끝나고, 글은 공짜로 나온다.
같은 요청이면 덮어쓴다(두 번 해도 같다).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADING = {"finding": "밝혀진 것", "benchmark": "수치", "capability": "할 수 있는 것",
           "limitation": "주의할 것", "opinion": "의견"}
ORDER = ["finding", "benchmark", "capability", "limitation", "opinion"]


def render(rid: str) -> Path:
    claims = json.loads((ROOT / "requests" / rid / "draft.json").read_text(encoding="utf-8"))["claims"]
    lines = [f"# 이번 주 정리 — {rid}", ""]
    for kind in ORDER:
        picked = [c for c in claims if c.get("kind") == kind]
        if not picked:
            continue
        lines += [f"## {HEADING[kind]}", ""]
        for c in picked:
            lines.append(f"- {c['text']}")
            if c.get("source_id"):
                lines.append(f"  - 출처 `{c['source_id']}` — \"{c['quote']}\"")
        lines.append("")
    out = ROOT / "drafts" / f"{rid}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    try:
        out = render(sys.argv[1])
    except (OSError, ValueError, KeyError) as e:
        print(f"render: 초안을 글로 만들 수 없다 ({type(e).__name__})")
        return 64
    print(f"render: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
