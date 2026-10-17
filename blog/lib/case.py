"""검사 케이스 — 자료와 기준을 읽는다.

검사 5층이 요구하는 것은 이 클래스가 아니라 **멤버 세 개**다.

    .sources                  dict[출처 id, 파일 경로]
    .required                 list[dict]   (운영에서는 [] — 커버리지 검사가 자동 통과)
    .source_text(출처 id)      str | None

그래서 파이프라인의 수집 단계가 이 세 멤버를 가진 객체를 만들면
`checks/` 의 검사 다섯은 한 줄도 바뀌지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Case:
    """검사 케이스 하나. 자료 목록과 필수 항목 목록을 갖는다."""

    name: str
    root: Path
    sources: dict[str, str] = field(default_factory=dict)
    required: list[dict] = field(default_factory=list)
    expect: str = "pass"   # pass | reject — 이 케이스에 기대하는 판정

    @classmethod
    def load(cls, path: Path) -> Case:
        """`cases/case-01-standard.yaml` 처럼 파일 하나가 케이스 하나다."""
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            name=path.stem,
            root=path.parent,
            sources=data.get("sources") or {},
            required=data.get("required") or [],
            expect=(data.get("expect") or "pass").strip(),
        )

    def source_text(self, source_id: str) -> str | None:
        """출처 원문. 목록에 없는 id 면 None — 출처 존재 검사가 그걸 잡는다."""
        rel = self.sources.get(source_id)
        if rel is None:
            return None
        return (self.root / rel).read_text(encoding="utf-8")


def find_cases(directory: Path) -> list[Path]:
    """`cases/` 안의 `case-*.yaml` 만 케이스다. `sources/` 같은 자료 폴더는 건너뛴다."""
    if not directory.is_dir():
        return []
    return sorted(directory.glob("case-*.yaml"))
