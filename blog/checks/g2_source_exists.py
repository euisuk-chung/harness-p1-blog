"""G2 — 인용한 source_id 가 이번 수집분에 실재하는가.

지표: source_exists = source_id 가 bundle 에 있는 claim / 출처가 필요한 claim
임계값: 1.0 (불변식)

막는 실패: **출처 날조.** 그럴듯한 arxiv id 를 지어내는 것.

집합 포함 하나로 끝난다. 이게 가드레일이 싼 이유다.
"""

from . import NEEDS_SOURCE, GuardResult


def check(claims: list[dict], case) -> GuardResult:
    sourced = [c for c in claims if c.get("kind") in NEEDS_SOURCE]
    if not sourced:
        return GuardResult("G2", "source_exists", 1.0, True)

    hits, detail = 0, []
    for i, claim in enumerate(claims):
        if claim.get("kind") not in NEEDS_SOURCE:
            continue
        # null 이면 "" 로 본다 — 어차피 bundle 에 없어서 실패한다. (G3 와 같은 이유)
        source_id = claim.get("source_id") or ""
        if source_id in case.sources:
            hits += 1
        else:
            detail.append(f"claim[{i}] source_id not in bundle: {source_id!r}")

    metric = hits / len(sourced)
    return GuardResult("G2", "source_exists", metric, metric == 1.0, detail)
