## 승인 전 확인 근거

- 요청: 2026-W36
- 검사 코드 커밋: 미확인 (작업 파일의 지문은 아래에 별도 기록)
- 커밋 뒤 검사 코드 변경: 미확인
- 실행: `python review.py --request 2026-W36` (현재 파일의 임시 사본) / 신호: 0
- 기대: G1~G5 모두 pass, 신호 0
- 관찰: 일치: G1~G5 모두 pass, 신호 0
- 입력 SHA-256: d1747435a8812e1e9c0f6537c833011ab3cf345c4aa66ad5e7de144adf1b33ca
- 글 파일: drafts/2026-W36.md
- 글 SHA-256: 73353554a423418c4c6df726f10ddfdf436b89af3b40752567329374e74764ed

- 검사 사본 지문 일치: True
- 검사 초안으로 만든 글 일치: True

| 검사 | 이번 판정 |
|---|---|
| G1 | pass |
| G2 | pass |
| G3 | pass |
| G4 | pass |
| G5 | pass |

### 확인하지 못한 것

- 저장된 초안의 규칙 검사만 실행했다. 새 모델 출력·실제 발행·외부 서비스는 확인하지 않았다.
- 인용과 주장의 의미 일치, 정보의 사실성·최신성은 사람이 확인해야 한다.
- 파일 지문은 변화를 찾는 값이며 서명이나 승인 기록이 아니다. 실행 환경·의존성 전체는 고정하지 않았다.
- Git 커밋을 읽지 못했다. 아래 파일 지문만 남긴다.

### 대조할 파일 지문 (SHA-256)

- `_utf8.py`: 5856a857e809dfc21438017224175142f448d5b876dc81e8a1d8affd8253bb1b
- `case.py`: 564eddf5b83fbd8bcbe89bbc396a93915a715dabf5359ff735972f65b27ba706
- `cases/case-01-standard.yaml`: 04d53ebe03741c6aed1d73a0a6ab6189d072fb15805621aa134f50f1638a49ea
- `cases/sources/week-01/arxiv-2601.12345.abstract.txt`: 865c1af70709a30528d9e29a7a8c7bec85b92b53c950841a5fce994b8b5a7570
- `cases/sources/week-01/arxiv-2601.67890.abstract.txt`: 2521cff3c693d4b2f03959a73b0e7ee58dcf0cd64c7daf2cb11e81b9c6453e5c
- `cases/sources/week-01/model-acme-lumen-3.card.md`: 9f441de6bf465dc8bd12017f5657a2b5f40c58edd78f541595007366878d96ab
- `cases/sources/week-01/release-vllm-v0.9.0.md`: 663037ba892dc58037f04f1cbdaee1350238b9f7f2345625224c070f44120ca1
- `checks/__init__.py`: 684263971e2150e3535daa92eee71b89e4c5cad370b4b63d7a044a59ece969af
- `checks/g1_schema.py`: 80d5778072e23030bbc082153330083d7e86852058f46da38afe97c670a86e56
- `checks/g2_source_exists.py`: 97582986262584655d83a71b0aa12bddf0e486eb382ada26ff627f79de8c58e1
- `checks/g3_quote_verbatim.py`: 6edb9335982372de732b5eff1be797aa4d3c0d0b3c794e89d7da91fced4b6647
- `checks/g4_coverage.py`: eb8eb350f28db3d827aaa2727036fdeeb07460eebe93427f517db64ae7adb05a
- `checks/g5_opinion_ratio.py`: 5f15dc9861430507ae8b553e35ef7f2e4ad05aa2e0ff7c992cb91afa39610ed3
- `drafts/2026-W36.md`: 73353554a423418c4c6df726f10ddfdf436b89af3b40752567329374e74764ed
- `requests/2026-W36/draft.json`: d1747435a8812e1e9c0f6537c833011ab3cf345c4aa66ad5e7de144adf1b33ca
- `requests/2026-W36/state.json`: aa7b5590a00b2c967fdd297cfb658053bbe757adf729eb6f25ebdce81758078b
- `review.py`: cfc174c853fe91af7590a380479b042498d2d86813319e81b8973424b8a95d57
- `schema.json`: 4ef6f66f5a78a2a0798c76ed9e56d2ee0c08a7e6fcfdc92ae7964712ea5c7d10
- `schema.strict.json`: 005ba9a535930c844523b22b1045876466fc4d7673906e6e19b3bf4c42432da2
- `schema_contract.py`: 1303af6886f37cafc8d166cd4995bc253b831a0918e70cfa1f5c0b2f2b25355b
- `scripts/approval_evidence.py`: 1d9c7187aee5c2f33fa639713ffd81a6cb6b38eaaf1b08dfc853c3a43bddf408
- `scripts/render.py`: 36bc95471510986a854af4075839dd92bff6151cd6a756abf6ddf8278e191aec
