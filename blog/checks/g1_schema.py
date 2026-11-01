"""G1 — 출력이 스키마를 지키는가.

지표: schema_valid (bool)
임계값: true (불변식)

막는 실패: 형식 붕괴. 여기서 실패하면 나머지 층은 볼 것도 없다.

실전에서는 CLI 가 호출 단계에서 같은 계약을 강제한다.
이 층은 그 계약이 실제로 지켜졌는지 확인하는 마지막 방어선이다.

## ⚠️ **보내는 계약보다 엄격한 것으로 본다**

    schema.json          기본 형식. drafter 에게 알려 주는 형식(두 CLI 가 다 받는 부분집합)
    schema.strict.json   **여기서 쓴다.** 조건부 규칙까지

Codex 가 `allOf`·`if`·`not` 을 못 받아서 나눴다. *"opinion 에는 출처를 달 수 없다"*
는 형식만으로 강제할 수 없고, **받은 뒤에 우리가 본다.**

> 강제할 수 있는 것과 검사할 것은 다르다. 이 층이 그 차이를 메운다.
"""

from pathlib import Path

import schema_contract

from . import GuardResult

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - 선택 의존
    Draft202012Validator = None

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema.json"


def check(claims: list[dict], case) -> GuardResult:
    document = {"claims": claims}

    if Draft202012Validator is None:
        # 검증기가 없는 것은 **내용 실패가 아니라 인프라 실패**다.
        # FAIL 로 조용히 넘기면 모든 case 가 이유 없이 떨어져 원인을 찾기 어렵다.
        raise SystemExit(
            "jsonschema 가 설치되지 않았다. G1 을 실행할 수 없다.\n"
            "  uv sync   (또는)   pip install jsonschema"
        )

    # 보내는 것이 아니라 **검사하는** 계약을 읽는다 — 머리말 참조.
    schema = schema_contract.load_strict(SCHEMA_PATH)
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda e: e.path)

    detail = [
        f"claims{''.join(f'[{p}]' for p in e.path)}: {e.message}"
        for e in errors[:5]
    ]
    if len(errors) > 5:
        detail.append(f"... and {len(errors) - 5} more")

    ok = not errors
    return GuardResult("G1", "schema_valid", ok, ok, detail)
