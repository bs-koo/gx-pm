<div align="center">

# gx-pm

**공공/SI PM의 AI 운영 체제**

요구사항 분석부터 테스트 계획, ID 추적, 감리 대응까지

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)]()
[![Skills](https://img.shields.io/badge/skills-18-green.svg)]()
[![Commands](https://img.shields.io/badge/commands-8-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 이게 뭔가요?

`gx-pm`은 **공공/SI 프로젝트의 PM**을 위한 Claude Cowork 플러그인입니다.

RFP를 넣으면 요구사항을 뽑아주고, 화면목록표와 프로그램정의서를 만들어주고, ERDCloud DDL에서 테이블정의서를 변환해주고, 테스트 계획서를 자동 생성하고, 산출물 간 ID가 끊기지 않았는지 추적합니다. 감리가 오면 지적사항 대응 문서까지 만들어줍니다.

### 일반 PM 도구와 뭐가 다른가요?

| 일반 PM 플러그인 (pm-skills 등) | gx-pm |
|------|------|
| PRD, OKR, 로드맵 | **화면정의서, 요구사항 추적표, 인수테스트** |
| GTM, 그로스 루프 | **감리 대응, 범위 협상, 공수 산정** |
| TAM/SAM/SOM | **WBS 분해, 진척률 분석** |
| 영어 중심 프레임워크 | **한국어 공공/SI 문서 양식** |

---

## 설치

### Claude Cowork (데스크톱)

```
Customize (좌하단) → Browse plugins → Personal → +
→ "Add marketplace from GitHub" → SQI/gx-pm
```

### Claude Code CLI

```bash
claude plugin marketplace add SQI/gx-pm
claude plugin install gx-pm@gx-pm
```

---

## 사용법

PM이 `/pm-` 까지 입력하면 8개 커맨드가 자동완성됩니다.

| 이렇게 말하면 | 실행되는 커맨드 | 결과물 |
|--------------|---------------|--------|
| "RFP에서 요구사항 뽑아줘" | `/pm-analyze` | AN-02 요구사항정의서 |
| "화면목록 만들어줘" | `/pm-design` | DE-03 화면목록표 + DE-05 프로그램정의서 |
| "DDL로 테이블정의서 만들어줘" | `/pm-table` | DE-08 테이블정의서 |
| "테스트 계획서 만들어줘" | `/pm-test` | DE-13 단위테스트계획서 + DE-14 통합테스트시나리오 |
| "추적매트릭스 확인해줘" | `/pm-trace` | AN-05 추적매트릭스 + 누락 리포트 |
| "감리 지적사항 대응해줘" | `/pm-audit` | 감리 대응 문서 + 증빙 체크리스트 |
| "테스트 결과 기입해줘" | `/pm-result` | IM-03 / TE-02 / TE-06 결과서 |
| "회의록 정리해줘" | `/pm-report` | 회의록 / 주간보고서 |

---

## 프로젝트 흐름

```
 프로젝트 착수                    개발/시험 중                   감리/변경
 ──────────                    ──────────                   ──────────

 /pm-analyze                   /pm-report 회의록             /pm-audit
   → 요구사항정의서                → 구조화된 회의록              → 대응 문서
       ↓                                                        ↓
 /pm-design                    /pm-report 주간보고            /pm-trace
   → 화면목록표                    → 주간보고서                  → 추적매트릭스 갱신
   → 프로그램정의서                    ↓
       ↓                       /pm-result
 /pm-table                       → 단위테스트결과서
   → 테이블정의서 ←→ ERDCloud      → 통합테스트결과서
       ↓                          → 인수테스트결과서
 /pm-test
   → 단위테스트계획서
   → 통합테스트시나리오
       ↓
 /pm-trace
   → 요구사항추적매트릭스
   → 누락 탐지 리포트
```

---

## 핵심: ID 추적 체인

공공/SI 프로젝트에서 감리 대응의 핵심은 **산출물 간 추적성**입니다. gx-pm은 모든 산출물을 하나의 ID 체인으로 연결합니다.

```
제안요청ID  (SFR-027)
  └→ 요구사항ID  (B-RE-001)
       └→ 화면ID       (EHR_01_01_010)
            └→ 프로그램ID    (PG_EHR_01_01_010)
                 └→ 단위테스트ID  (U_EHR_01_01_010)
                      └→ 통합테스트ID  (B-TE-001)
```

`/pm-trace`로 언제든 추적 상태를 확인할 수 있습니다:

```
┌─ 제안요청: SFR-027
├─ 요구사항: B-RE-003 (교육 과정 관리)
│   ├─ 화면: EHR_03_01_010 (과정 목록) ✅
│   │   ├─ 프로그램: PG_EHR_03_01_010 ✅
│   │   └─ 단위테스트: U_EHR_03_01_010 ✅
│   ├─ 화면: EHR_03_01_020 (과정 등록) ✅
│   │   ├─ 프로그램: PG_EHR_03_01_020 ✅
│   │   └─ 단위테스트: U_EHR_03_01_020 ⚠ 누락
│   └─ 통합테스트: B-TE-002 ✅
└─ 과업완료: ⚠ 진행중 (단위테스트 1건 누락)
```

---

## 스킬 상세

### 분석 (3개)

| 스킬 | 설명 |
|------|------|
| `extract-requirements` | RFP/과업지시서에서 요구사항 추출. ID 자동 부여, 수용여부 초안 |
| `classify-requirements` | 기능/비기능 분류 + 대/중/소분류 + 공공/SI 5단계 우선순위 |
| `trace-requirements` | AN-05 추적매트릭스 생성/갱신. 4가지 누락 유형 탐지 |

### 설계 (5개)

| 스킬 | 설명 |
|------|------|
| `generate-screen-list` | 요구사항 → DE-03 화면목록표. 화면 유형 추론, ID 자동 부여 |
| `generate-program-list` | 화면목록 → DE-05 프로그램정의서. eGovFrame/Spring Boot 소스 구조 매핑 |
| `convert-ddl-to-tablespec` | ERDCloud DDL → DE-08 테이블정의서. 한글 속성명 자동 추론 |
| `generate-erd-guide` | 요구사항 → ERD 설계 가이드 + DDL 생성. Oracle/PG/MySQL 지원 |
| `generate-interface-spec` | 외부 연동 식별 → DE-04 인터페이스정의서. REST/SOAP/DB Link/파일/SSO |

### 테스트 (4개)

| 스킬 | 설명 |
|------|------|
| `generate-unit-test-plan` | 화면목록 → DE-13 단위테스트계획서. 검사기준 27개 항목 자동 매핑 |
| `generate-integration-test` | 요구사항 → DE-14 통합테스트시나리오. 업무 흐름 기반 Step 분해 |
| `fill-unit-test-result` | 계획서 → IM-03 결과서. 3가지 입력 모드, 적합률 자동 산출 |
| `fill-integration-test-result` | 계획서 → TE-02/TE-06 결과서. 부적합 조치 워크플로우 |

### 보고 (3개)

| 스킬 | 설명 |
|------|------|
| `meeting-notes` | 회의록 구조화. 발주처 지시사항/협의사항 자동 추출 |
| `weekly-report` | 주간보고서. 단계별 진척률, 감리 대응 현황 포함 |
| `audit-response` | 감리 지적 5가지 유형 분류 → 조치계획 → 증빙 체크리스트 |

### 의사결정 (3개)

| 스킬 | 설명 |
|------|------|
| `prioritize-si` | 공공/SI 5단계 우선순위 (법적필수 > 감리필수 > 과업명시 > 발주처요청 > 품질개선) |
| `impact-analysis` | 변경 영향도 분석. 직접/연쇄/간접 영향 추적, 작업량 추정, 변경요청서 초안 |
| `id-trace` | ID 양방향 추적 + 4가지 누락 유형 탐지 + 추적 완료율 계산 |

---

## ERDCloud 연계

ERDCloud는 별도 API가 없으므로 DDL 텍스트 기반으로 양방향 변환합니다.

### 정방향: ERDCloud → 테이블정의서

```
ERDCloud에서 "모든 테이블 생성 SQL" 내보내기
  → DDL 텍스트를 /pm-table에 붙여넣기
  → DE-08 테이블정의서 자동 생성
```

### 역방향: 요구사항 → ERDCloud

```
/pm-table 역방향
  → 요구사항/화면에서 엔터티 도출
  → DDL 생성 → ERDCloud에 붙여넣기
```

---

## 검사기준 자동 매핑

`/pm-test`는 화면 유형을 자동 판별하여 27개 검사기준을 매핑합니다.

| 화면 유형 | 공통(8) | 조회(4) | 입력(6) | 수정(2) | 삭제(2) | 첨부(3) | 출력(2) |
|----------|---------|---------|---------|---------|---------|---------|---------|
| 목록형 | O | O | - | - | - | - | △ |
| 등록형 | O | - | O | - | - | △ | - |
| 수정형 | O | - | - | O | △ | △ | - |
| 상세형 | O | O | - | - | - | - | △ |
| CRUD 통합 | O | O | O | O | O | △ | △ |

---

## 감리 대응

`/pm-audit`은 감리 지적사항을 5가지 유형으로 분류하고, 유형별 표준 조치 패턴을 적용합니다.

| 유형 | 표준 조치 | 후속 커맨드 |
|------|---------|------------|
| 산출물 누락 | 해당 산출물 즉시 작성 | `/pm-design`, `/pm-test` |
| 내용 미흡 | 산출물 보완 + 검토 이력 | 해당 스킬 재실행 |
| 추적성 부족 | 추적매트릭스 전면 갱신 | `/pm-trace 전체` |
| 품질 미달 | 테스트 보강 + 결과서 | `/pm-test`, `/pm-result` |
| 절차 미준수 | 변경관리 이력 소급 | `impact-analysis` |

---

## 산출물 커버리지

| 단계 | 산출물 코드 | 산출물명 | 생성 커맨드 |
|------|-----------|---------|------------|
| 분석 | AN-02 | 요구사항정의서 | `/pm-analyze` |
| 분석 | AN-05 | 요구사항추적매트릭스 | `/pm-trace` |
| 설계 | DE-03 | 화면목록표 | `/pm-design` |
| 설계 | DE-04 | 인터페이스정의서 | `/pm-design` |
| 설계 | DE-05 | 프로그램정의서 | `/pm-design` |
| 설계 | DE-08 | 테이블정의서 | `/pm-table` |
| 설계 | DE-13 | 단위테스트계획서 | `/pm-test` |
| 설계 | DE-14 | 통합테스트계획서 | `/pm-test` |
| 구현 | IM-03 | 단위테스트결과서 | `/pm-result` |
| 시험 | TE-02 | 통합테스트결과서 | `/pm-result` |
| 시험 | TE-06 | 인수테스트결과서 | `/pm-result` |

---

## 디렉토리 구조

```
gx-pm/
├── .claude-plugin/
│   ├── plugin.json            # 플러그인 메타데이터
│   └── marketplace.json       # 마켓플레이스 등록
├── skills/                     # 18개 스킬
│   ├── extract-requirements/
│   ├── classify-requirements/
│   ├── trace-requirements/
│   ├── generate-screen-list/
│   ├── generate-program-list/
│   ├── convert-ddl-to-tablespec/
│   ├── generate-erd-guide/
│   ├── generate-interface-spec/
│   ├── generate-unit-test-plan/
│   ├── generate-integration-test/
│   ├── fill-unit-test-result/
│   ├── fill-integration-test-result/
│   ├── meeting-notes/
│   ├── weekly-report/
│   ├── audit-response/
│   ├── prioritize-si/
│   ├── impact-analysis/
│   └── id-trace/
├── commands/                   # 8개 워크플로우
│   ├── pm-analyze.md
│   ├── pm-design.md
│   ├── pm-table.md
│   ├── pm-test.md
│   ├── pm-trace.md
│   ├── pm-audit.md
│   ├── pm-result.md
│   └── pm-report.md
├── templates/                  # 9개 산출물 양식
│   ├── AN-02-requirements-definition.md
│   ├── AN-05-traceability-matrix.md
│   ├── DE-03-screen-list.md
│   ├── DE-05-program-definition.md
│   ├── DE-08-table-definition.md
│   ├── DE-13-unit-test-plan.md
│   ├── DE-14-integration-test-plan.md
│   ├── inspection-criteria.md
│   └── id-naming-rules.md
├── README.md
├── CLAUDE.md
├── CHANGELOG.md
├── _config.yml                 # GitHub Pages
└── LICENSE
```

---

## FAQ

<details>
<summary>기존 산출물이 있는 프로젝트에서도 사용할 수 있나요?</summary>

네. 기존 산출물의 ID 체계를 자동 감지하여 이어서 채번합니다. `/pm-trace`로 기존 산출물 간 매핑 상태를 먼저 확인하는 것을 권장합니다.
</details>

<details>
<summary>ERDCloud 외 다른 ERD 도구도 지원하나요?</summary>

표준 SQL DDL을 내보낼 수 있는 도구라면 모두 지원합니다. `/pm-table`은 CREATE TABLE 문을 파싱하므로, ERDCloud, DBeaver, DataGrip 등에서 내보낸 DDL을 모두 처리할 수 있습니다.
</details>

<details>
<summary>eGovFrame 외 다른 프레임워크도 지원하나요?</summary>

`/pm-design`에서 프레임워크를 선택할 수 있습니다. 현재 eGovFrame과 Spring Boot를 지원하며, 소스파일 구조(Controller/Service/DAO 등)가 프레임워크별로 자동 매핑됩니다.
</details>

<details>
<summary>감리 대응 시 어떤 산출물을 준비해야 하나요?</summary>

`/pm-audit`에 감리 지적사항을 입력하면 유형별로 필요한 증빙 산출물 체크리스트를 자동 생성합니다. 각 지적사항에 대해 조치계획, 담당자, 완료예정일도 함께 관리할 수 있습니다.
</details>

<details>
<summary>pm-skills (phuryn)와 함께 사용할 수 있나요?</summary>

네. pm-skills는 일반 PM 프레임워크(JTBD, OKR, GTM 등)를 제공하고, gx-pm은 공공/SI 특화 산출물을 제공합니다. 서로 다른 영역을 커버하므로 함께 사용하면 더 강력합니다.
</details>

---

## License

MIT
