<div align="center">

# gx-pm

**공공/SI PM의 AI 운영 체제**

요구사항 분석부터 기능명세, 테이블 설계, 단위테스트, ID 추적까지

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)]()
[![Skills](https://img.shields.io/badge/skills-15-green.svg)]()
[![Commands](https://img.shields.io/badge/commands-7-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 이게 뭔가요?

`gx-pm`은 **공공/SI 프로젝트의 PM**을 위한 Claude Code 플러그인입니다.

RFP를 넣으면 요구사항을 뽑아주고, 요구사항에서 기능(입력항목·처리내용·출력결과)을 도출하고, DDL에서 테이블정의서를 역생성하고, 기능 1건당 단위테스트 케이스를 기계적으로 만들고, 산출물 간 ID가 끊기지 않았는지 추적합니다.

**v3.0.0**: 플러그인을 화면 축에서 **기능 축**으로 재정렬했습니다. 산출물이 13종에서 **5종**으로, 커맨드가 16개에서 **7개**로 줄었습니다.
`/gx-spec` 하나로 요구사항 → 기능 → 테이블 → 단위테스트 → 추적매트릭스를 순서대로 만들며, 판단이 필요한 **승인 게이트 3곳**에서만 멈춥니다.
ID 체계에서 **파생 ID가 전부 사라져** 어떤 ID를 바꿔도 재채번 파급이 없습니다 — 연결은 전부 `연계~ID` 열이 맡습니다.
내린 화면 축 산출물(DE-03·DE-05·DE-04·ST-01/02·DF-01 등)은 삭제하지 않고 `plugins/gx-pm/archive/`에 보관했습니다.

**v1.3.0부터**: 개발 완료 후 산출물을 맞춰야 할 때, DDL에서 테이블정의서를 **역생성**할 수 있습니다. `/gx-프로젝트설정` 한 번이면 모든 커맨드가 프로젝트 상황에 맞게 자동 동작합니다.

### 일반 PM 도구와 뭐가 다른가요?

| 일반 PM 플러그인 (pm-skills 등) | gx-pm |
|------|------|
| PRD, OKR, 로드맵 | **요구사항정의서, 기능명세서, 요구사항 추적표** |
| GTM, 그로스 루프 | **범위 협상, 공수 산정** |
| TAM/SAM/SOM | **WBS 분해, 진척률 분석** |
| 영어 중심 프레임워크 | **한국어 공공/SI 문서 양식** |

---

## 설치

### Claude Desktop 앱 (Code 탭)

1. 좌하단 **사용자 지정** 클릭
2. **개인 플러그인** 옆 **`+`** 버튼 → **플러그인 탐색**
3. 상단 **개인** 탭 → **`+`** 버튼 → URL에 `bs-koo/gx-pm` 입력 → **추가**
4. **gx-pm** 탭 선택 → **설치**
5. 프로젝트에서 `/gx-프로젝트설정` → `/gx-spec` 순으로 사용

### Claude Code CLI

```bash
# Claude Code CLI에서 실행
/plugin marketplace add bs-koo/gx-pm
/plugin install gx-pm@gx-pm
```

---

## 사용법

### 처음 시작할 때

```
/gx-프로젝트설정
```

프로젝트 유형, 기본 정보, 소스코드 경로, DDL을 한 번 설정하면 이후 모든 커맨드가 자동으로 활용합니다. 새 대화를 열어도 설정이 유지됩니다.

### 프로젝트 유형 4가지

| 유형 | 언제 사용 | 커맨드 동작 |
|------|----------|------------|
| **A. 신규 구축** | RFP만 있고, 코드 없음 | 정방향 생성 (RFP → 산출물) |
| **B. 추가 개발** | 기존 시스템에 새 기능 추가 | 기존 산출물에 이어쓰기 |
| **C. 산출물 정비** | 개발 완료, 산출물 부족 | DE-08은 DDL에서 역생성, 나머지는 기존 산출물·RFP로 정비 |
| **D. 변경 관리** | 기존 기능 수정 | 변경 대상만 갱신 |

### 커맨드 목록

**커맨드 이름 = 산출물 이름**입니다. 만들고 싶은 산출물을 그대로 입력하면 됩니다.

| 이렇게 말하면 | 커맨드 | 결과물 |
|--------------|--------|--------|
| "명세 다 만들어줘" | `/gx-spec` | **명세 5종 일괄 (승인 게이트 3곳)** |
| "프로젝트 설정해줘" | `/gx-프로젝트설정` | profile.json (프로젝트 프로파일) |
| "요구사항 뽑아줘" | `/gx-요구사항정의서` | AN-02 요구사항정의서 |
| "기능명세 만들어줘" | `/gx-기능명세서` | AN-03 기능명세서 |
| "DDL로 테이블정의서 만들어줘" | `/gx-테이블정의서` | DE-08 테이블정의서 |
| "단위테스트 계획 세워줘" | `/gx-단위테스트계획서` | DE-13 단위테스트계획서 |
| "추적매트릭스 확인해줘" | `/gx-추적매트릭스` | AN-05 추적매트릭스 |

---

## 핵심 기능

### 1. 단계별 승인 루프

모든 커맨드는 산출물을 한 번에 생성하지 않습니다. **각 단계마다 사용자 확인을 받고, 수정 요청이 있으면 반영한 뒤 다시 확인**합니다.

```
[산출물 생성] → [결과 표시] → 승인? → No → [수정 반영] → [다시 표시] → 승인? → ...
                                   → Yes → [다음 단계]
```

### 2. 시안/대안 자동 감지

요구사항에 "1안/2안", "A안/B안" 등 복수 시안이 있으면 **자동 감지하여 사용자에게 선택을 요청**합니다. 선택 전에는 산출물 생성을 시작하지 않습니다.

```
⚠ 시안 선택이 필요합니다

  1안: 이중 슬라이더 단일 화면 → 관리 항목 5개 예상
  2안: 쾌적성/온도 별도 관리 → 관리 항목 8개 예상

→ 어떤 시안으로 진행할까요? (1/2/병행)
```

### 3. 기존 산출물 처리

커맨드 실행 시 기존 산출물이 있으면 **3가지 선택지**를 제공합니다:

```
기존 요구사항정의서를 찾았습니다:
  B-요구사항정의서.md (35건, 마지막 수정: 1/15)

  1. 이어쓰기 — 기존 유지 + 새 항목 추가 (B-RE-036부터)
  2. 새로쓰기 — backup/ 폴더에 백업 후 처음부터 재생성
  3. 열기     — 기존 내용에서 특정 항목만 수정/삭제
```

### 4. DDL에서 역생성 (C유형)

개발 완료 후 산출물을 맞출 때, DB 스키마에서 테이블정의서를 **자동 역생성**합니다. 기존 컬럼은 이름을 바꾸지 않고, 신규 컬럼만 표준용어사전 근거로 제안합니다.

| 소스 | 역생성 산출물 | 방식 |
|------|-------------|------|
| DDL (DataGrip/DBeaver 복사) | 테이블정의서 (DE-08) | DDL 파싱 + 표준용어 MCP 표준화 |

소스코드는 `scan-source-index` 스킬로 3단계 점진 스캔해 실제 구현과 산출물을 대조하는 데 씁니다 (풀스캔 200만 → 1.7만 토큰).

### 5. xlsx 추출

승인된 산출물은 **공공 양식 컬럼 순서에 맞춘 xlsx로 즉시 추출**할 수 있습니다. 실제 산출물 엑셀에 바로 복사-붙여넣기가 가능합니다.

```bash
# CLI에서 직접 사용할 수도 있습니다
python utils/export-xlsx.py --dir 결과물/ --output 산출물.xlsx
```

---

## 프로젝트 흐름

### A. 신규 구축 (정방향)

**파이프라인 (권장)** — 커맨드 순서를 외우지 않아도 됩니다.

```
 /gx-프로젝트설정 (A유형)
       ↓
 /gx-spec       (명세 5종 일괄, 승인 게이트 3곳)
       ↓
 /gx-추적매트릭스 (누락 탐지)
```

**낱개로 만들 때** — 파이프라인 내부에서 도는 순서와 같습니다.

```
 /gx-요구사항정의서 → /gx-기능명세서 → /gx-테이블정의서 → /gx-단위테스트계획서
                                                              ↓
                                                       /gx-추적매트릭스 (누락 탐지)
```

### C. 산출물 정비 (역방향)

**파이프라인 (권장)**

```
 /gx-프로젝트설정 (C유형 + 소스경로 + DDL)
       ↓
 /gx-spec       DE-08은 DDL에서 역생성, 나머지는 기존 산출물·RFP로 정비
       ↓
 /gx-추적매트릭스 (누락 탐지)
```

**낱개로 만들 때**

```
 /gx-테이블정의서 ← DDL 역생성
       ↓
 /gx-추적매트릭스 (누락 탐지)
```

---

## 핵심: ID 추적 체인

공공/SI 프로젝트에서 감리 대응의 핵심은 **산출물 간 추적성**입니다. gx-pm은 모든 산출물을 하나의 ID 체인으로 연결합니다.

```
요구사항ID  (B-RE-001)
  └→ 기능ID  (B-FN-001)          ← 파생 아님. 독립 채번, N:M 매핑
       ├→ 테이블·컬럼 (DE-08)     ← 입력항목이 컬럼으로 매핑된다
       └→ 테스트ID (B-UT-001)    ← 파생 아님. 독립 채번, N:1 매핑
```

**갈래가 둘입니다.** 기능 요구사항은 기능명세를 거쳐 테스트로, 비기능 요구사항은 기능을 거치지 않고 바로 테스트로 갑니다 (DE-13의 `연계기능ID` 공란 행).

**파생 ID가 없습니다.** 어떤 ID도 다른 ID에서 만들어지지 않으므로, ID를 바꿔도 재채번 파급이 없습니다. 연결은 전부 `연계~ID` 열이 맡습니다.

`/gx-추적매트릭스`로 언제든 추적 상태를 확인할 수 있습니다 (모든 유형에서 사용 가능):

```
| 요구사항ID | 요구사항명 | 상태 | 기능ID | 기능명 | 테이블·컬럼 | 테스트 수 | Pass/Fail | 누락 |
|---|---|---|---|---|---|---|---|---|
| B-RE-001 | 벤치마크 스코어테이블 생성 기능 | 유지 | B-FN-001 | 스코어테이블 생성 | TB_SCORE (신규 4) | 6 | 6/0 | |
| B-RE-045 | 동시접속 500명 응답 3초 | 신규 | | | | 2 | 0/0 | 미수행 |
| B-RE-032 | 업로드 통계 데이터 조회 | 신규 | | | | 0 | — | 기능 미도출 |
```

**커버리지 판정**

| 지표 | 목표 |
|------|------|
| 기능 요구사항 → 기능 매핑률 | 100% |
| **비기능 요구사항 검증률** (DE-13 연계기능ID 공란 행) | **100%** |
| 단위테스트 Pass 률 | 100% |

---

## 스킬 상세

### 분석 (4개)

| 스킬 | 설명 |
|------|------|
| `extract-requirements` | RFP/과업지시서에서 요구사항 추출. ID 표 인식 + **기능/비기능 판정 정본** |
| `classify-requirements` | 비기능 세부 유형 + 대/중분류 + 공공/SI 5단계 우선순위 (기능/비기능 판정은 `extract-requirements` 정본) |
| `trace-requirements` | AN-05 추적매트릭스 생성/갱신. 누락 7유형 탐지 |
| `detect-alternatives` | 시안/대안 자동 감지. 1안/2안, A안/B안 등 패턴 스캔 |

### 설계 (2개)

| 스킬 | 설명 |
|------|------|
| `generate-function-spec` | 요구사항정의서(AN-02) → AN-03 기능명세서. 입력항목·처리내용·출력결과 도출 |
| `convert-ddl-to-tablespec` | 기존 DDL → DE-08 테이블정의서 역생성. 신규 컬럼만 표준용어사전 근거로 제안 |

### 테스트 (2개)

| 스킬 | 설명 |
|------|------|
| `generate-unit-test-plan` | 기능명세서(AN-03)·테이블정의서(DE-08) → DE-13 단위테스트계획서. 기능 축 케이스 도출 |
| `design-test-cases` | 입력항목·처리내용 → 테스트 케이스. 동등분할·경계값·결정테이블·상태전이, 정상/경계/예외 강제 |

### 프로젝트 관리 (4개)

| 스킬 | 설명 |
|------|------|
| `load-project-profile` | 프로파일 자동 감지·로드. 모든 커맨드의 Step 0에서 자동 실행 |
| `detect-existing-artifact` | 기존 산출물 감지 → 이어쓰기/새로쓰기/열기 3택 제공 |
| `scan-source-index` | 소스코드 3단계 점진 스캔 (Level 1 트리 ~2K, Level 2 헤더 ~15K 토큰). 실구현 대조용 |
| `manage-revision-history` | 5종 공통 개정이력 행 관리. 직전 버전과 대조해 초안을 만들고 승인을 받음 |

### 의사결정 (3개)

| 스킬 | 설명 |
|------|------|
| `prioritize-si` | 공공/SI 5단계 우선순위 (법적필수 > 감리필수 > 과업명시 > 발주처요청 > 품질개선) |
| `impact-analysis` | 변경 영향도 분석. ID 체인으로 직접/연쇄 영향 추적, 작업량 추정 |
| `id-trace` | ID 양방향 추적 + 누락 유형 탐지 + 추적 완료율 계산 |

---

## DB 스키마 연계

DDL 텍스트 기반으로 테이블정의서를 역생성합니다. DataGrip, DBeaver, ERDCloud 등 DDL을 내보낼 수 있는 도구라면 모두 지원합니다. **DE-08은 역생성 전용**입니다 — 요구사항에서 테이블을 추론하는 순방향 경로는 없습니다.

### DDL 복사 방법

| 도구 | 복사 방법 |
|------|----------|
| **DataGrip** | 스키마 우클릭 → SQL Scripts → Generate DDL to Clipboard |
| **DBeaver** | 스키마 우클릭 → Generate SQL → DDL → Ctrl+A → Ctrl+C |
| **ERDCloud** | SQL 내보내기 → 모든 테이블 생성 SQL |

### DDL → 테이블정의서

```
DDL 복사 → /gx-테이블정의서에 붙여넣기 → DE-08 자동 역생성
  → 기존 컬럼은 현행유지 + 표준 권고명 병기
  → 신규 컬럼(기능명세 입력항목 기반)만 표준용어 MCP 근거로 제안·승인
```

---

## 산출물 범위

| 코드 | 산출물명 | 커맨드 |
|------|---------|--------|
| AN-02 | 요구사항정의서 | `/gx-요구사항정의서` |
| AN-03 | 기능명세서 | `/gx-기능명세서` |
| DE-08 | 테이블정의서 | `/gx-테이블정의서` |
| DE-13 | 단위테스트계획서 | `/gx-단위테스트계획서` |
| AN-05 | 추적매트릭스 | `/gx-추적매트릭스` |

다섯 문서 모두 **개정이력 시트**를 갖습니다 (`manage-revision-history` 스킬, 정본 `templates/revision-history.md`).

내린 화면 축 산출물(DE-03·DE-05·DE-14·TE-01·ST-01/02·DF-01·IM-03·TE-02·TE-06 등)은 `plugins/gx-pm/archive/`에 보관돼 있습니다. 되살리는 방법은 `plugins/gx-pm/archive/README.md`를 참조하세요.

---

## 디렉토리 구조

```
gx-pm/                                      # 저장소 루트
├── .claude-plugin/
│   └── marketplace.json                   # 마켓플레이스 등록
├── .github/workflows/
│   └── test.yml                           # CI — 계약 테스트 실행
├── plugins/gx-pm/                          # 플러그인 본체
│   ├── .claude-plugin/
│   │   └── plugin.json                    # 플러그인 메타데이터
│   ├── commands/                          # 7개 커맨드
│   │   ├── gx-spec.md
│   │   ├── gx-기능명세서.md
│   │   ├── gx-단위테스트계획서.md
│   │   ├── gx-요구사항정의서.md
│   │   ├── gx-추적매트릭스.md
│   │   ├── gx-테이블정의서.md
│   │   └── gx-프로젝트설정.md
│   ├── skills/                            # 15개 스킬
│   │   ├── classify-requirements/
│   │   ├── convert-ddl-to-tablespec/
│   │   ├── design-test-cases/
│   │   ├── detect-alternatives/
│   │   ├── detect-existing-artifact/
│   │   ├── extract-requirements/
│   │   ├── generate-function-spec/
│   │   ├── generate-unit-test-plan/
│   │   ├── id-trace/
│   │   ├── impact-analysis/
│   │   ├── load-project-profile/
│   │   ├── manage-revision-history/
│   │   ├── prioritize-si/
│   │   ├── scan-source-index/
│   │   └── trace-requirements/
│   ├── templates/                         # 산출물 양식 + 정본 규약 11종
│   │   ├── AN-02-requirements-definition.md
│   │   ├── AN-03-function-spec.md
│   │   ├── AN-05-traceability-matrix.md
│   │   ├── DE-08-table-definition.md
│   │   ├── DE-13-unit-test-plan.md
│   │   ├── approval-protocol.md
│   │   ├── id-naming-rules.md
│   │   ├── pipeline-protocol.md
│   │   ├── prerequisites.md
│   │   ├── project-profile-schema.md
│   │   └── revision-history.md
│   ├── archive/                           # 화면 축 산출물 보관소 (커맨드10·스킬13·템플릿7)
│   │   ├── commands/
│   │   ├── skills/
│   │   ├── templates/
│   │   └── README.md                      # 되살리는 방법
│   ├── utils/
│   │   └── export-xlsx.py                 # 마크다운 → xlsx 변환
│   ├── tests/                             # unittest 계약 테스트
│   │   ├── fixtures/
│   │   │   └── requirement-tables.md
│   │   ├── helpers.py
│   │   ├── test_export_xlsx.py
│   │   ├── test_extract_rules.py
│   │   └── test_plugin_consistency.py
│   ├── docs/
│   │   └── 표준용어-mcp-연계.md
│   ├── CLAUDE.md                          # 플러그인 지침 (세션마다 로드)
│   └── CHANGELOG.md
├── docs/superpowers/                       # 설계서 · 구현 계획서
├── README.md
└── _config.yml                            # GitHub Pages
```

---

## FAQ

<details>
<summary>개발이 끝난 프로젝트에서 산출물을 맞출 수 있나요?</summary>

`/gx-프로젝트설정`에서 **C. 산출물 정비** 유형을 선택하고, DDL을 입력하면 됩니다. `/gx-테이블정의서`가 DDL에서 DE-08을 역생성하고, 나머지 4종(요구사항정의서·기능명세서·단위테스트계획서·추적매트릭스)은 기존 산출물과 RFP를 근거로 정비합니다.
</details>

<details>
<summary>기존 산출물이 있는 프로젝트에서도 사용할 수 있나요?</summary>

네. 커맨드 실행 시 기존 산출물을 자동 감지하여 **이어쓰기**(기존 유지 + 추가), **새로쓰기**(백업 후 재생성), **열기**(부분 수정) 중 선택할 수 있습니다. ID 번호는 기존 마지막 번호에 이어서 자동 부여됩니다.
</details>

<details>
<summary>여러 프로젝트를 동시에 관리할 수 있나요?</summary>

네. 하나의 작업 폴더에서 여러 프로젝트를 관리합니다. `/gx-프로젝트설정`을 실행하면 기존 프로젝트 목록이 표시되고, 원하는 프로젝트를 선택하거나 새로 생성할 수 있습니다. 프로젝트별로 별도 폴더에 산출물이 저장됩니다.
</details>

<details>
<summary>DDL은 어떻게 입력하나요?</summary>

DB 접속정보는 받지 않습니다. DataGrip에서는 스키마 우클릭 → SQL Scripts → Generate DDL to Clipboard, DBeaver에서는 스키마 우클릭 → Generate SQL → DDL로 전체 DDL을 클립보드에 복사한 뒤 붙여넣으면 됩니다.
</details>

<details>
<summary>비기능 요구사항은 어떻게 검증하나요?</summary>

기능을 거치지 않고 바로 테스트로 갑니다. `/gx-단위테스트계획서`가 DE-13에 `연계기능ID`가 공란인 행을 만들어 비기능 요구사항을 직접 검증합니다.
</details>

<details>
<summary>xlsx 추출은 어떻게 하나요?</summary>

모든 커맨드 완료 시 "xlsx로 추출할까요?" 선택지가 나옵니다. 선택하면 공공 양식 컬럼 순서에 맞춘 xlsx가 자동 생성되어 산출물 엑셀에 바로 복사-붙여넣기할 수 있습니다. CLI에서 직접 `python utils/export-xlsx.py --dir 결과물/`로도 사용 가능합니다.
</details>

<details>
<summary>DE-03·DE-05·감리대응 같은 화면 축 이전 산출물은 어디 갔나요?</summary>

삭제하지 않고 `plugins/gx-pm/archive/`에 보관했습니다. 감리가 있는 공공 사업이 오면 되살릴 수 있습니다 — 방법은 `plugins/gx-pm/archive/README.md`를 참조하세요.
</details>

---

## License

MIT
