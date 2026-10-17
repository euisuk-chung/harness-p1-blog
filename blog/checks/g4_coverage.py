"""G4 — 반드시 다뤄야 할 항목을 놓치지 않았는가.

지표: coverage = 다룬 required / len(required)
임계값: >= 0.8

막는 실패: **핵심 누락.** 통과하기 쉬운 얘기만 골라 쓰고 어려운 걸 건너뛰는 것.

판정: required 하나가 '다뤄졌다'는 것은
      (1) 그 항목이 요구한 출처를 인용한 claim 이 있고
      (2) 그 claim 의 kind 가 일치하며
      (3) find 문자열이 claim.text 또는 quote 에 나타난다
      셋을 모두 만족하는 것이다. 전부 문자열·집합 연산이다.

주의: required 개수가 임계값의 의미를 결정한다. 5개일 때만 0.8 = 4/5 다.
      PRD.md "통과 기준" 절 참조.
"""

import re

from . import GuardResult

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def check(claims: list[dict], case) -> GuardResult:
    required = case.required
    if not required:
        return GuardResult("G4", "coverage", 1.0, True)

    covered, missed = 0, []
    for item in required:
        needle = _norm(item["find"])
        hit = any(
            c.get("source_id") == item["cite"]
            and c.get("kind") == item["kind"]
            and (needle in _norm(c.get("text", "")) or needle in _norm(c.get("quote", "")))
            for c in claims
        )
        if hit:
            covered += 1
        else:
            missed.append(item["id"])

    metric = covered / len(required)
    detail = [f"missed: {', '.join(missed)}"] if missed else []
    return GuardResult("G4", "coverage", metric, metric >= 0.8, detail)
