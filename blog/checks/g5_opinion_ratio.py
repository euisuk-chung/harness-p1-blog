"""G5 — 의견으로 인용 요구를 회피하지 않았는가.

지표: opinion_ratio = kind == 'opinion' 인 claim / 전체 claim
임계값: <= 0.3

막는 실패: **가드레일 우회.** G2·G3 만 있으면 모델이 전부 'opinion' 으로 라벨링해
          출처 요구를 통째로 빠져나갈 수 있다. 스키마상으로도 정상이고 G2·G3 도 통과한다.

이 층이 이 과정에서 가르치는 것:
    **가드레일을 붙이면 그 가드레일을 우회하는 실패가 새로 생긴다.**
    case f03-opinion-dodge 가 그 실물이다.

의견 자체는 막지 않는다. 블로그에 의견은 필요하다. 비율만 제한한다.
"""

from . import GuardResult

MAX_OPINION_RATIO = 0.3


def check(claims: list[dict], case) -> GuardResult:
    if not claims:
        return GuardResult("G5", "opinion_ratio", 0.0, True)

    opinions = sum(1 for c in claims if c.get("kind") == "opinion")
    metric = opinions / len(claims)
    passed = metric <= MAX_OPINION_RATIO

    detail = []
    if not passed:
        detail.append(
            f"opinion_ratio {metric:.2f} > {MAX_OPINION_RATIO} "
            f"({opinions}/{len(claims)} claims) — 출처 요구를 회피하고 있다"
        )
    return GuardResult("G5", "opinion_ratio", metric, passed, detail)
