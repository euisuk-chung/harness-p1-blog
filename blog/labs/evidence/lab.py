"""선택 실습: 직접 만든 모의 기록만 읽으며 모델·API·파일 쓰기를 사용하지 않는다."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

FIXTURES = Path(__file__).with_name("cases.json")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_handoff(current: dict, record: dict, root: Path | None = None) -> dict:
    reasons = []
    required = ("request_id", "created_at", "next_step", "source_sha256", "code_sha256", "artifact_path", "artifact_sha256")
    missing = [key for key in required if not record.get(key)]
    if missing:
        reasons.append("필수 정보 없음: " + ", ".join(missing))
    hashes = {}
    for field, content in (("source_sha256", "source"), ("code_sha256", "code")):
        expected = digest(current[content])
        hashes[field] = {"recorded": record.get(field), "current": expected}
        if record.get(field) and record[field] != expected:
            reasons.append(field + " 불일치")
    actual = None
    if record.get("artifact_path"):
        try:
            base = (root or FIXTURES.parent).resolve()
            path = Path(record["artifact_path"])
            resolved = (base / path).resolve()
            if path.is_absolute() or not resolved.is_relative_to(base):
                reasons.append("인계 파일이 실습 폴더 밖을 가리킴")
            elif not resolved.is_file():
                reasons.append("인계 파일 없음: " + record["artifact_path"])
            else:
                actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
                if record.get("artifact_sha256") and actual != record["artifact_sha256"]:
                    reasons.append("artifact_sha256 불일치")
        except (OSError, TypeError, ValueError):
            reasons.append("인계 파일을 확인할 수 없음")
    hashes["artifact_sha256"] = {"recorded": record.get("artifact_sha256"), "current": actual}
    for key in ("request_id", "next_step"):
        if record.get(key) and record[key] != current[key]:
            reasons.append(key + " 불일치")
    if record.get("created_at"):
        try:
            now = datetime.fromisoformat(current["now"])
            created = datetime.fromisoformat(record["created_at"])
            age = (now - created).total_seconds()
            if not 0 <= age <= current["max_age_hours"] * 3600:
                reasons.append("기록 시각 허용 범위 밖")
        except (TypeError, ValueError):
            reasons.append("기록 시각을 비교할 수 없음")
    return {"decision": "STOP" if reasons else "REVIEW_ONLY", "reasons": reasons, "hashes": hashes}


def inspect_evidence(evidence: dict) -> dict:
    status = evidence["status"]
    quote = status["draft_quote"]
    benchmarks = []
    for row in evidence["benchmarks"]:
        before, after = row["before_ms"], row["after_ms"]
        usable = (len(before) == len(after) > 0 and
                  all(type(x) in (int, float) and x > 0 for x in before + after))
        change = round((mean(before) - mean(after)) / mean(before) * 100, 2) if usable else None
        benchmarks.append({"id": row["id"], "reported_percent": row["reported_percent"],
                           "sample_pairs": min(len(before), len(after)), "computed_percent": change})
    return {"status_label": status["label"], "quote_found_in_source": bool(quote) and quote in status["source"],
            "deliveries": evidence["deliveries"], "benchmarks": benchmarks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exercise", choices=("handoff", "evidence"))
    parser.add_argument("--case", choices=("all", "normal", "stale", "missing", "wrong-code-version"), default="all")
    args = parser.parse_args()
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    print(data["provenance"])
    if args.exercise == "handoff":
        results = {name: check_handoff(data["current"], record) for name, record in data["handoffs"].items()
                   if args.case in ("all", name)}
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 3 if any(r["decision"] == "STOP" for r in results.values()) else 0
    print(json.dumps(inspect_evidence(data["evidence"]), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
