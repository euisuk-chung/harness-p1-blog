"""G3 — quote 가 출처 원문에 그대로 있는가.

지표: quote_verbatim = quote 가 원문에 있는 claim / 출처가 있는 claim
임계값: 1.0 (불변식)

막는 실패: 실재하는 출처를 붙여 놓고 **그 출처가 하지 않은 말**을 인용하는 것.

정규화 범위 (결정 E4):
  - 연속 공백과 줄바꿈을 단일 공백으로 접는다.
    PDF/HTML 에서 긁어온 초록은 줄바꿈이 섞여 있어, 이걸 안 하면 정답인데 실패한다.
  - **대소문자는 유지한다.** 벤치마크명·고유명사가 중요하다.
    'MMLU 88.2' 와 'mmlu 88.2' 를 같다고 보면 가드레일이 약해진다.
  - 유니코드를 NFC 로 모은다. 맥에서 저장한 한글은 자모가 나뉜(NFD) 채로 남기도 해서,
    눈에는 같은 문장인데 글자 코드가 달라 정답인데 실패한다. (case-06-korean-notes)
"""

import re
import unicodedata

from . import NEEDS_SOURCE, GuardResult

_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """글자 코드를 NFC 로 모으고 공백만 접는다. 대소문자·구두점은 건드리지 않는다."""
    return _WS.sub(" ", unicodedata.normalize("NFC", text)).strip()


def check(claims: list[dict], case) -> GuardResult:
    sourced = [c for c in claims if c.get("kind") in NEEDS_SOURCE]
    if not sourced:
        return GuardResult("G3", "quote_verbatim", 1.0, True)

    hits, detail = 0, []
    for i, claim in enumerate(claims):
        if claim.get("kind") not in NEEDS_SOURCE:
            continue
        # ⚠️ 보내는 계약이 null 을 허용한다. `.get(k, "")` 는 **키가 있고 값이 None** 이면
        #    None 을 돌려준다 — 기본값이 안 먹는다. `or ""` 로 받아야 한다.
        source_id = claim.get("source_id") or ""
        quote = normalize(claim.get("quote") or "")
        body = case.source_text(source_id)

        if body is None:
            # G2 가 이미 잡는다. 여기서 중복 보고하지 않는다.
            detail.append(f"claim[{i}] source not in bundle (see G2): {source_id}")
            continue
        if quote and quote in normalize(body):
            hits += 1
        else:
            detail.append(f"claim[{i}] quote not found in {source_id}: {quote[:60]!r}")

    metric = hits / len(sourced)
    return GuardResult("G3", "quote_verbatim", metric, metric == 1.0, detail)
