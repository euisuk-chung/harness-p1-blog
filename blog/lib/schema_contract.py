"""출력 형식 파일 **두 장**을 읽고, 기본 형식이 정해 둔 범위를 지키는지 확인한다.

## 두 장

    schema.json          기본 형식. 주장 목록의 뼈대만 —
                         drafter 안내(`.claude/agents/drafter.md` 의 "쓰는 형식")에 적는 것과 같은 모양
    schema.strict.json   검사하는 형식. 뼈대 + 조건부 규칙("의견이면 출처를 비운다" 등).
                         초안이 쓰인 뒤 G1 이 이것으로 본다  ← 있으면 쓴다

    기본 형식  ⊆  검사하는 형식

부탁한 모양(기본 형식)은 대부분 지켜지지만, 늘 지켜진다고 믿을 수는 없다.
받아들이는 기준은 **받은 뒤 우리가 보는** 검사하는 형식이 쥔다. 어긋나면 G1 이 거부한다.

> **부탁할 것과 검사할 것은 다르다.** 같다고 믿는 게 위험하다.

## 기본 형식은 좁게 쓴다 — 허용 부분집합

기본 형식은 좁은 키워드만 쓴다(`ALLOWED`). 이 목록은 출력 형식을 명령줄 옵션으로
넘기던 예전 설계(`claude -p --json-schema` 등) 때, 키워드를 하나씩 실제로 넘겨 보고 정했다.

    받는다   type properties items required additionalProperties
             enum const  minLength maxLength pattern
             minimum maximum exclusiveMinimum exclusiveMaximum
             minItems maxItems  anyOf
             title description $comment default examples

    거부한다 allOf oneOf if then else not uniqueItems      ← 예전 측정에서 거부된 것

지금 흐름은 형식을 명령줄로 넘기지 않고 drafter 안내에 적는다. 그래도 목록을 좁게 두는
까닭은, 기본 형식을 다른 도구로 옮길 때 다시 설계할 칸을 줄이기 위해서다.
부분집합으로 못 쓰는 규칙(*"opinion 에는 출처를 달 수 없다"* 는 `if`/`not` 없이 못 쓴다)은
버리지 않고 검사하는 형식으로 **나눠서 눈에 보이게** 둔다.

## 구조 규칙 하나 — **모든 속성이 `required` 에 있어야 한다**

선택 칸은 **`required` 에 넣고 타입을 null 로 연다.**

    "source_id": {"type": ["string", "null"]}

읽는 법이 달라진다 — *"없을 수 있다"* 가 아니라 *"없으면 null 이다"* 다.
**계약이 더 명확해진다.** 모델이 칸을 조용히 빠뜨릴 수 없다.

## 모르는 키워드를 **조용히 지우지 않는다**

> ⚠️ 초판은 `$schema` 만 벗겼다. "부딪힐 때마다 하나씩 벗기는" 방식이었다.
> 그러면 **계약이 조용히 달라진다** — 지운 키워드가 제약이었으면
> 우리는 막는다고 믿는데 실제로는 안 막힌다.

지금도 그렇다. 부분집합 밖이면 **실패시킨다.** 벗기는 것은 `$schema` 와 `$id`
둘뿐이고, 제약이 아니라 방언·식별 선언이다.

## ⚠️ 이 파일이 증명하는 것과 안 하는 것

> **증명한다**: `load()` 는 유효하지 않은 스키마, 부분집합 밖 키워드, `required` 밖 속성을
> 실패시킨다. G1 은 `load_strict()` 로 검사하는 형식을 읽어 판정한다.
>
> **증명하지 않는다**: 허용 목록이 지금의 도구들에서도 같게 받아들여진다는 것 — 예전 측정
> 뒤로 다시 재지 않았다. `for_cli()` 는 예전 설계에서 형식을 명령줄로 넘기던 함수로,
> 지금 흐름에서는 부르지 않는다.

`format` 은 뺐다 — 파이썬 `jsonschema` 가 기본 설정에서 **집행하지 않는다.**
있는데 안 도는 키워드를 두면 "막았다고 믿는" 상태가 된다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: 세 검증기가 다 받는 키워드. **여기 없는 것은 쓰지 않는다.**
#: 실제로 태워 보고 정했다 — 문서에서 고른 게 아니다.
ALLOWED = {
    # 구조
    "type", "properties", "items", "required", "additionalProperties",
    "enum", "const",
    # 문자열
    #   ⚠️ `format` 은 뺐다. 파이썬 jsonschema 가 기본으로 집행하지 않는다.
    "minLength", "maxLength", "pattern",
    # 수
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    # 배열
    #   ⚠️ `uniqueItems` 는 뺐다. Codex 가 거부한다.
    "minItems", "maxItems",
    # 조합 — **anyOf 하나만** 통과한다
    "anyOf",
    # 주석 — 판정에 영향이 없다
    "title", "description", "$comment", "default", "examples",
}

#: 어느 CLI 가 왜 거부하는지. 오류 메시지에 그대로 쓴다.
#: 이름만 알려 주면 "왜 안 되는지" 를 다시 찾아야 한다.
REJECTED_BY = {
    "allOf":       "Codex 가 거부한다 (400 invalid_json_schema)",
    "oneOf":       "Codex 가 거부한다 (400 invalid_json_schema)",
    "if":          "Codex 가 거부한다 (400 invalid_json_schema)",
    "then":        "Codex 가 거부한다 (`if` 와 함께 쓰인다)",
    "else":        "Codex 가 거부한다 (`if` 와 함께 쓰인다)",
    "not":         "Codex 가 거부한다 (type 없는 서브스키마를 못 읽는다)",
    "uniqueItems": "Codex 가 거부한다 (400 invalid_json_schema)",
    "format":      "파이썬 jsonschema 가 기본 설정에서 집행하지 않는다",
}

#: 넘길 때 벗기는 **둘**. 제약이 아니라 방언·식별 선언이라 벗겨도 뜻이 안 바뀐다.
STRIPPED_AT_ROOT = {"$schema", "$id"}


class SchemaContractError(Exception):
    """계약이 허용 부분집합을 벗어났다."""


def unknown_keywords(doc: Any, path: str = "") -> list[str]:
    """허용 목록 밖 키워드를 전부 찾는다. **조용히 지우지 않고 이름을 돌려준다.**"""
    found: list[str] = []
    if isinstance(doc, dict):
        for key, value in doc.items():
            if path == "" and key in STRIPPED_AT_ROOT:
                continue
            # `properties` 아래는 사용자가 정한 필드 이름이다. 키워드가 아니다.
            if key in ("properties", "$defs", "definitions"):
                for name, sub in (value or {}).items():
                    found += unknown_keywords(sub, f"{path}/{key}/{name}")
                continue
            if key not in ALLOWED:
                found.append(f"{path}/{key}" if path else key)
                continue
            found += unknown_keywords(value, f"{path}/{key}")
    elif isinstance(doc, list):
        for i, item in enumerate(doc):
            found += unknown_keywords(item, f"{path}[{i}]")
    return found


def optional_properties(doc: Any, path: str = "") -> list[str]:
    """`required` 에 빠진 속성을 찾는다.

    Codex 는 **모든 속성이 `required` 에 있기를** 요구한다.
    선택 필드는 `"type": ["string", "null"]` 로 연다 — 머리말 참조.
    """
    found: list[str] = []
    if isinstance(doc, dict):
        props = doc.get("properties")
        if isinstance(props, dict):
            missing = set(props) - set(doc.get("required") or [])
            for name in sorted(missing):
                found.append(f"{path}/properties/{name}" if path else f"properties/{name}")
        for key, value in doc.items():
            found += optional_properties(value, f"{path}/{key}")
    elif isinstance(doc, list):
        for i, item in enumerate(doc):
            found += optional_properties(item, f"{path}[{i}]")
    return found


def _read(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))

    import jsonschema

    try:
        jsonschema.Draft202012Validator.check_schema(doc)
    except jsonschema.SchemaError as exc:
        raise SchemaContractError(
            f"{path.name} 이 유효한 JSON Schema 가 아니다: {exc.message}"
        ) from exc
    return doc


def load(path: Path) -> dict:
    """**CLI 에 넘길** 계약을 읽고 세 가지를 확인한다. 하나라도 아니면 실패한다.

        1. JSON Schema 로서 유효한가        ← 메타스키마 검사
        2. 허용 부분집합 안인가              ← 키워드 이름 검사
        3. 모든 속성이 required 안에 있는가   ← Codex 의 구조 규칙

    ⚠️ 초판은 2번만 했다. 그래서 `{"type": "definitely-not-a-type"}` 이 통과했고,
    `allOf` 를 쓴 계약이 Codex 에서 400 으로 죽었다. **둘 다 리뷰가 아니라 실행이 잡았다.**
    """
    doc = _read(path)

    bad = unknown_keywords(doc)
    if bad:
        names = sorted({b.rsplit("/", 1)[-1] for b in bad})
        why = "\n".join(f"    {n} — {REJECTED_BY[n]}" for n in names if n in REJECTED_BY)
        raise SchemaContractError(
            f"{path.name} 이 허용 부분집합을 벗어났다: {', '.join(sorted(set(bad)))}\n"
            + (why + "\n" if why else "")
            + f"  세 검증기(파이썬 jsonschema · Claude · Codex)가 다 받는 키워드만 쓴다.\n"
            f"  조건부 규칙이 필요하면 {path.stem}.strict.json 으로 나눈다 — schema.py 머리말.\n"
            f"  늘리려면 schema_contract.py 의 ALLOWED 에 넣고,\n"
            f"  **세 곳에 실제로 태워 본 뒤** 넣는다."
        )

    loose = optional_properties(doc)
    if loose:
        raise SchemaContractError(
            f"{path.name} 에 required 밖 속성이 있다: {', '.join(loose)}\n"
            f"  Codex 는 **모든 속성이 required 안에** 있기를 요구한다.\n"
            f'  선택 필드는 required 에 넣고 타입을 열어 준다: "type": ["string", "null"]'
        )
    return doc


def strict_path(path: Path) -> Path:
    """`schema.json` → `schema.strict.json`. 없을 수도 있다."""
    return path.with_name(f"{path.stem}.strict{path.suffix}")


def load_strict(path: Path) -> dict:
    """**우리가 검사할** 계약. 있으면 strict, 없으면 보내는 것과 같다.

    strict 는 부분집합에 매이지 않는다 — 파이썬 `jsonschema` 만 읽기 때문이다.
    다만 **유효한 스키마이긴 해야** 한다.
    """
    strict = strict_path(path)
    if strict.exists():
        return _read(strict)
    return load(path)


def for_cli(path: Path) -> str:
    """CLI 에 넘길 문자열. **`$schema` 와 `$id` 만** 벗긴다.

    이 둘이 제약이 아니라 방언·식별 선언이라는 게 중요하다 —
    **제약은 하나도 안 지운다.** 지우면 계약이 달라진다.
    """
    doc = load(path)
    return json.dumps({k: v for k, v in doc.items() if k not in STRIPPED_AT_ROOT},
                      ensure_ascii=False)
