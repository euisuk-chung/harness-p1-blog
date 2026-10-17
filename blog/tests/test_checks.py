"""검사기가 옳게 도는가 — 이게 이 파일의 질문이다.

    uv run python tests/test_checks.py

`review.py` 와 헷갈리기 쉬우니 구분해 둔다.

    review.py --case X   이 결과물을 내보내도 되나        (게이트)
    test_checks.py      검사기가 제대로 잡고 제대로 통과시키나  (검사기 테스트)

**거부돼야 할 케이스가 거부되면 이 테스트는 성공이다.** 반대로 그런 케이스가
통과해 버리면 실패다. 두 가지를 본다.

    1. 각 케이스가 `expect:` 대로 판정되는가
    2. 각 검사에 자기 실패를 먹였을 때 실제로 잡는가 — 통과만 확인하면 의미가 없다
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from _utf8 import force_utf8  # noqa: E402
from case import Case, find_cases  # noqa: E402
from review import run_case, verdict  # noqa: E402
from checks import (  # noqa: E402
    g1_schema,
    g2_source_exists,
    g3_quote_verbatim,
    g4_coverage,
    g5_opinion_ratio,
)

failures: list[str] = []


def expect_verdicts() -> None:
    """케이스마다 적어 둔 기대 판정과 실제가 맞는가."""
    print("1. 케이스가 기대대로 판정되는가")
    for path in find_cases(ROOT / "cases"):
        case = Case.load(path)
        actual = "pass" if verdict(run_case(case)) else "reject"
        ok = actual == case.expect
        if not ok:
            failures.append(f"{case.name}: 기대 {case.expect}, 실제 {actual}")
        print(f"   {'OK  ' if ok else 'FAIL'} {case.name:<22} 기대 {case.expect:<7} 실제 {actual}")


def expect_check(label: str, module, claims: list[dict], case: Case, should_pass: bool) -> None:
    """검사 하나에 입력을 먹여 기대한 대로 통과/거부하는가."""
    r = module.check(claims, case)
    ok = r.passed == should_pass
    if not ok:
        failures.append(f"{label}: {r.guard} 기대 {'통과' if should_pass else '거부'}, 실제 반대")
    want = "통과해야" if should_pass else "잡아야"
    print(f"   {'OK  ' if ok else 'FAIL'} {r.guard} {r.metric_name:<15} {r.format_metric():>5}  {want} | {label}")


def injected_failures() -> None:
    """각 검사에 자기 실패를 먹인다. 통과만 확인하는 테스트는 의미가 없다."""
    print("\n2. 각 검사가 자기 실패를 잡는가")
    case = Case.load(ROOT / "cases" / "case-01-standard.yaml")
    good = json.loads((ROOT / "samples" / "reference" / "case-01-standard.json").read_text(encoding="utf-8"))["claims"]

    def variant(fn):
        c = json.loads(json.dumps(good))
        fn(c)
        return c

    expect_check("정상 입력", g1_schema, good, case, True)
    expect_check("kind 오타", g1_schema,
                 variant(lambda c: c[0].__setitem__("kind", "benchmarkk")), case, False)
    expect_check("의견에 출처를 달았다", g1_schema,
                 variant(lambda c: c[-1].__setitem__("source_id", "model:acme/lumen-3:card")), case, False)
    expect_check("출처 날조", g2_source_exists,
                 variant(lambda c: c[0].__setitem__("source_id", "arxiv:9999.99999:abstract")), case, False)
    expect_check("원문에 없는 문장 인용", g3_quote_verbatim,
                 variant(lambda c: c[0].__setitem__("quote", "achieves 99.9 on MMLU")), case, False)
    expect_check("줄바꿈 섞인 인용", g3_quote_verbatim,
                 variant(lambda c: c[2].__setitem__(
                     "quote",
                     "staged deliberation, a method that separates\n  plan generation from plan execution"
                     "\n  using an explicit intermediate artifact")), case, True)
    expect_check("대소문자 변경", g3_quote_verbatim,
                 variant(lambda c: c[0].__setitem__("quote", "lumen-3 achieves 88.2 on mmlu")), case, False)
    expect_check("필수 항목 누락", g4_coverage, good[:3], case, False)

    dodge = [{"text": f"의견 {i}", "kind": "opinion", "source_id": None, "quote": None}
             for i in range(8)] + [good[0]]
    expect_check("의견으로 회피", g5_opinion_ratio, dodge, case, False)
    expect_check("의견으로 회피 — 출처 검사는 통과해 버린다", g2_source_exists, dodge, case, True)


def main() -> int:
    force_utf8()
    expect_verdicts()
    injected_failures()

    print()
    if failures:
        print(f"실패 {len(failures)}건")
        for line in failures:
            print(f"   {line}")
        return 1
    print("검사기가 기대대로 동작한다.")
    print("마지막 두 줄에 주목 — 출처 검사만으로는 의견 회피를 못 잡는다. 그래서 의견 비율 검사가 있다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
