"""가드레일 5층. 지표 하나에 가드레일 하나가 1:1로 붙는다.

계약: 각 가드는 `check(claims, case) -> GuardResult` 하나만 노출한다.
      LLM 판정은 어느 층에도 없다. 전부 집합·문자열·산술이다.

계약: 꾸러미 맨 위 PRD.md 의 "통과 기준" 절
"""

from dataclasses import dataclass, field


@dataclass
class GuardResult:
    """한 가드의 판정.

    metric  지표 값 (bool 또는 0.0~1.0)
    passed  임계값을 통과했는가
    detail  실패했을 때 어디를 고칠지 — claim 번호와 이유
    """

    guard: str
    metric_name: str
    metric: float | bool
    passed: bool
    detail: list[str] = field(default_factory=list)

    def format_metric(self) -> str:
        if isinstance(self.metric, bool):
            return "ok" if self.metric else "fail"
        return f"{self.metric:.2f}"


NEEDS_SOURCE = {"finding", "benchmark", "capability", "limitation"}
