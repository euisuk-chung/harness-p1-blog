"""검수 — 이 초안을 내보내도 되는지 검사 다섯(G1~G5)으로 판정한다. 모델을 부르지 않는다.

    uv run python review.py --request 2026-W36          요청 폴더의 초안(requests/<id>/draft.json)을 검수. 흐름이 부른다
    uv run python review.py --case case-01-standard    저장된 답(samples/)을 검수. 종료 코드가 곧 판정
    uv run python review.py                            보고서. 전부 보여만 준다
    uv run python review.py --fail-on-regression       회귀 게이트. 하락이 있으면 1
    uv run python review.py --save-baseline            지금 커버리지를 기준으로 저장

## 종료 코드가 뜻하는 것 — 헷갈리기 쉬운 지점

    --case 를 주면 **임계값 게이트**다.
        0  이 결과물은 내보내도 된다
        1  거부됐다

    ⚠️ 게이트는 **임계값만** 본다. 기준(baseline) 대비 하락은 보지 않는다.
    둘은 다른 질문이고, 다른 명령으로 막는다.

        임계값 게이트   이 결과물 하나가 기준을 넘는가       review.py --case X
        회귀 게이트     이번 변경이 예전보다 나빠졌는가       review.py --fail-on-regression

    --case 없이 부르면 **보고서**다. 케이스마다 다른 판정이 나오는 게 정상이고,
    일부러 실패하도록 만든 케이스도 섞여 있으므로 **종료 코드로 성패를 읽지 않는다.**
    --fail-on-regression 을 붙였을 때만 보고서가 종료 코드를 낸다.

    "검사기 자체가 옳게 동작하는가" 는 다른 질문이다. `test_checks.py` 가 답한다.
    거기서는 거부돼야 할 케이스가 거부되면 **성공**이다.

계약: 꾸러미 맨 위 PRD.md 의 "통과 기준" 절
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from _utf8 import force_utf8  # noqa: E402
from case import Case, find_cases  # noqa: E402
from checks import GuardResult  # noqa: E402
from checks import (  # noqa: E402
    g1_schema,
    g2_source_exists,
    g3_quote_verbatim,
    g4_coverage,
    g5_opinion_ratio,
)

CHECKS = [g1_schema, g2_source_exists, g3_quote_verbatim, g4_coverage, g5_opinion_ratio]
BASELINE = ROOT / "baseline.json"
COLUMNS = ("schema_valid", "source_exists", "quote_verbatim", "coverage", "opinion_ratio")


def load_result(case: Case) -> list[dict]:
    """표본 결과물을 읽는다. 실제 실행 한 번의 초안을 저장해 둔 것이다."""
    path = ROOT / "samples" / "reference" / f"{case.name}.json"
    if not path.exists():
        raise SystemExit(
            f"표본 결과물이 없다: samples/reference/{path.name}\n"
            f"  실제 실행의 requests/<id>/draft.json 을 저장한다."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return (data.get("output") or data)["claims"]


def run_case(case: Case) -> list[GuardResult]:
    claims = load_result(case)
    results = []
    for check in CHECKS:
        result = check.check(claims, case)
        results.append(result)
        if result.guard == "G1" and not result.passed:
            break  # 형식이 깨졌으면 나머지는 볼 것도 없다
    return results


def verdict(results: list[GuardResult]) -> bool:
    return all(r.passed for r in results)


def print_detail(case_name: str, results: list[GuardResult]) -> None:
    for r in results:
        for line in r.detail:
            print(f"   {case_name}  {r.guard}  {line}")


def gate(name: str) -> int:
    """케이스 하나를 게이트로 실행한다. 종료 코드가 곧 판정이다."""
    paths = [p for p in find_cases(ROOT / "cases") if p.stem == name]
    if not paths:
        raise SystemExit(f"그런 케이스가 없다: {name}")
    case = Case.load(paths[0])
    results = run_case(case)
    ok = verdict(results)

    print(f"{case.name}: {'내보내도 됨' if ok else '거부'}  (임계값 게이트)")
    if not ok:
        print()
        print_detail(case.name, results)
    return 0 if ok else 1


def report(save_baseline: bool, fail_on_regression: bool) -> int:
    """전부 훑어 표로 보여준다. --fail-on-regression 없으면 종료 코드는 항상 0."""
    paths = find_cases(ROOT / "cases")
    if not paths:
        raise SystemExit("케이스를 찾지 못했다. cases/case-*.yaml 을 확인한다.")

    header = f"{'케이스':<22} {'형식':>5} {'출처':>6} {'인용':>6} {'커버':>6} {'의견':>6}  판정  기대"
    print(header)
    print("-" * 74)

    details, coverage = [], {}
    for path in paths:
        case = Case.load(path)
        results = run_case(case)
        by_name = {r.metric_name: r for r in results}
        ok = verdict(results)

        cells = [by_name[n].format_metric() if n in by_name else "-" for n in COLUMNS]
        mark = "통과" if ok else "거부"
        expected = "통과" if case.expect == "pass" else "거부"
        print(
            f"{case.name:<22} {cells[0]:>5} {cells[1]:>6} {cells[2]:>6} "
            f"{cells[3]:>6} {cells[4]:>6}  {mark}  {expected}"
        )
        for r in results:
            for line in r.detail:
                details.append(f"   {case.name}  {r.guard}  {line}")
        if "coverage" in by_name:
            coverage[case.name] = by_name["coverage"].metric

    if details:
        print()
        for line in details:
            print(line)

    print()
    print("이 표는 보고서다. 거부가 섞여 있는 것이 정상이다 — 일부러 실패하도록 만든 케이스가 있다.")
    print("검사기가 옳게 도는지는 test_checks.py 가 판정한다.")

    if save_baseline:
        BASELINE.write_text(
            json.dumps({"schema_version": 1, "coverage": coverage}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\n기준 저장: {len(coverage)}개 케이스")
        return 0

    previous = load_baseline()
    dropped: list[str] = []
    if previous:
        dropped = [
            f"{name} {previous[name]:.2f} → {value:.2f}"
            for name, value in coverage.items()
            if name in previous and value < previous[name]
        ]
        added = [n for n in coverage if n not in previous]
        print()
        if dropped:
            print("커버리지가 기준보다 떨어진 케이스")
            for line in dropped:
                print(f"   {line}")
        else:
            print("커버리지 하락 없음")
        if added:
            print(f"   새 케이스 (비교 대상 아님): {', '.join(added)}")
        print()
        print("⚠️ 커버리지 한 지표만 비교한다. 일반적인 회귀 검출이 아니다.")
    elif fail_on_regression:
        print()
        print("⚠️ 기준이 없다. --save-baseline 을 먼저 한 번 돌린다.")
        return 1

    if fail_on_regression and dropped:
        print()
        print(f"회귀 게이트: 하락 {len(dropped)}건 — 거부")
        return 1
    return 0


def load_baseline() -> dict[str, float]:
    """케이스별 커버리지. 케이스가 늘거나 줄어도 비교가 어긋나지 않는다."""
    if not BASELINE.exists():
        return {}
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    scores = data.get("coverage")
    return scores if isinstance(scores, dict) else {}


def review_request(rid: str) -> int:
    """요청 폴더의 초안을 검수한다. 케이스는 요청을 연 스크립트가 state.json 에 적어 둔 것."""
    d = ROOT / "requests" / rid
    try:
        state = json.loads((d / "state.json").read_text(encoding="utf-8"))
        data = json.loads((d / "draft.json").read_text(encoding="utf-8"))
        claims = data["claims"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"review: 형식 위반 — draft.json 을 읽을 수 없다 ({type(e).__name__})")
        return 2
    paths = [p for p in find_cases(ROOT / "cases") if p.stem == state.get("case")]
    if not paths:
        print(f"review: 케이스가 없다: {state.get('case')}")
        return 64
    case = Case.load(paths[0])
    results = []
    for check in CHECKS:
        r = check.check(claims, case)
        results.append(r)
        if r.guard == "G1" and not r.passed:
            break
    (d / "review.json").write_text(json.dumps(
        {r.guard: {"pass": r.passed, "detail": r.detail} for r in results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(" · ".join(f"{r.guard} {'pass' if r.passed else 'rejected'}" for r in results))
    bad = [r for r in results if not r.passed]
    for r in bad:
        for line in r.detail or ["거부"]:
            print(f"review: {r.guard} rejected — {line}")
    return 1 if bad else 0


def main() -> int:
    force_utf8()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="요청 폴더의 초안을 검수한다(흐름이 부른다)")
    parser.add_argument("--case", help="케이스 하나를 임계값 게이트로 판정한다")
    parser.add_argument("--save-baseline", action="store_true", help="지금 커버리지를 기준으로 저장")
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="기준보다 떨어진 케이스가 있으면 종료 코드 1",
    )
    args = parser.parse_args()

    if args.request:
        return review_request(args.request)
    if args.case:
        return gate(args.case)
    return report(args.save_baseline, args.fail_on_regression)


if __name__ == "__main__":
    sys.exit(main())
