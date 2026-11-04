# 프로젝트 프로파일 스키마

프로젝트 설정 정보를 저장하는 `profile.json`의 구조를 정의한다.
`/gx-프로젝트설정` 커맨드가 이 파일을 생성하고, 모든 커맨드가 이 파일을 참조한다.

---

## 저장 위치

```
{작업폴더}/
  └── {프로젝트명}/
        ├── profile.json        ← 이 파일
        ├── source-index.json   ← 소스 스캔 캐시 (선택)
        ├── requirements-state.json ← 원문·요구사항·CQ 결정·사용 ID·검토 상태
        ├── ddl.sql             ← DDL 원본 (선택)
        ├── {시스템코드}-*.md   ← 산출물들
        ├── backup/             ← 이전 버전 백업
        ├── 증적/               ← 내부 증적 (DE-13 수행대장 — xlsx 로 추출하지 않는다)
        ├── testdata/           ← DE-13 입력 파일 (업로드·불러오기 케이스)
        └── xlsx/               ← 엑셀 추출물
```

**`testdata/` 는 단위테스트계획서가 쓴다.** 파일이 입력인 케이스는 파일 없이
시험할 수 없어서, `skills/generate-unit-test-plan` 이 실제 파일을 만들어 두고
DE-13 의 `입력` 칸이 그 경로를 가리킨다. 규칙의 정본은
`templates/DE-13-unit-test-plan.md` §입력은 그대로 넣을 수 있어야 한다 다.

---

## profile.json 필드 정의

| 필드 | 타입 | 필수 | 설명 | 예시 |
|------|------|------|------|------|
| `name` | string | Y | 프로젝트 표시명 | `"교육행정시스템"` |
| `type` | string | Y | 프로젝트 유형 코드 | `"new"`, `"enhancement"`, `"documentation"`, `"change"` |
| `typeLabel` | string | Y | 프로젝트 유형 한글 라벨 | `"A. 신규 구축"` |
| `systemCode` | string | Y | 시스템 코드 (영문). 산출물 파일명·ID 접두어에 쓴다 | `"B"` |
| `prefix` | string | Y | 시스템 접두어. **현재 소비처 없음** — 아래 §소비처 없는 필드 | `"EHR"` |
| `idNaming` | object | N | 요구사항ID·기능ID·테스트ID 채번 규칙 | 아래 참조 |
| `framework` | string | Y | 프레임워크 유형 | `"egovframe"`, `"springboot"`, `"other"` |
| `db` | string | Y | DB 유형 | `"oracle"`, `"postgresql"`, `"mysql"`, `"other"` |
| `author` | string | Y | 작성자명 | `"홍길동"` |
| `networkType` | string | Y | 망 구분. **현재 소비처 없음** — 아래 §소비처 없는 필드 | `"internal"`, `"external"`, `"mixed"` |
| `auditDate` | string | N | 감리 일정 (YYYY-MM-DD) | `"2026-06-15"` |
| `assets` | object | N | 기존 자산 경로 정보 | 아래 참조 |
| `sourcePriority` | string[] | N | 표준용어사전 출처 우선순위. 실제 가용 출처와 프로젝트 도메인을 확인해 결정 | `["BLDG_ENGY", "MOIS_STD"]` |
| `policy` | object | N | 질문 정책 4개. `/gx-명세일괄` Step 0-4 가 묻고 저장한다 | 아래 참조 |
| `createdAt` | string | Y | 프로파일 생성일 (YYYY-MM-DD) | `"2026-03-31"` |
| `lastUsed` | string | Y | 마지막 사용일 (YYYY-MM-DD) | `"2026-03-31"` |

### policy 객체

`templates/pipeline-protocol.md` §질문 정책의 정책 층 4개를 담는다.
**선택 필드다** — 없으면 원문을 읽고 이번 산출물에 필요한 정책만 확인·저장한다.
단독 실행에도 같은 원칙을 적용하며 후속 문서 전용 선택은 미룬다. 필드 부재만으로 옛 프로파일을 거부하지 않는다.

| 필드 | 타입 | 값 | 뜻 |
|------|------|-----|-----|
| `splitCriterion` | string | `"verification-unit"`(권장) · `"rfp-one-to-one"` · `"function-domain"` | 요구사항 행 분할 기준 |
| `assumptionFill` | boolean | `false`(권장) · `true` | 미규정 설계값을 초안에 제안할지. `false`는 미정을 질문으로 남긴다. `true`도 `[가정]`·추천 근거를 표시하고 실제 승인을 받아야 한다. 업무 정책·수치·권한을 임의 확정하지 않는다 |
| `testDensity` | number \| null | `null`(권장) · `3` · `5` | 기능당 케이스 수 **경고 임계값**. 하한 패딩이 아니다 — 못 미치는 기능을 게이트에 올려 사람이 판단하게 한다. 수로 채우면 근거 없는 케이스가 생겨 `[가정]` 규율과 충돌하고, 그때는 **`[가정]` 규율이 이긴다** |
| `nonFunctionalVerification` | string | `"measurement-procedure"`(권장) · `"design-review"` · `"tool"` | 비기능 요구사항 검증 방법 |

```json
"policy": {
  "splitCriterion": "verification-unit",
  "assumptionFill": false,
  "testDensity": null,
  "nonFunctionalVerification": "measurement-procedure"
}
```

### assets 객체

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `sourcePath` | string\|null | 소스코드 로컬 경로 | `"D:\\projects\\ehr-system"` |
| `testSourcePaths` | string[]\|null | `/gx-단위테스트실행`이 실제 실행할 프로젝트 경로들. 백엔드·프론트가 나뉘면 모두 적는다. 하위 호환을 위해 이름을 유지한다. 없으면 `sourcePath`, 실제 애플리케이션인 현재 폴더 순으로 찾는다 | `["D:\\projects\\ehr-api", "D:\\projects\\ehr-web"]` |
| `ddlFile` | string\|null | DDL 파일명 (프로젝트 폴더 내) | `"ddl.sql"` |
| `existingArtifacts` | string\|null | 기존 산출물 폴더 경로 | `"D:\\docs\\ehr-artifacts"` |

### idNaming 객체 — 채번 규칙

세 ID 의 접두어와 자릿수를 프로젝트마다 정한다. 규칙의 정본은
`templates/id-naming-rules.md` 이고, **이 객체는 그 규칙의 저장 자리**다.

| 필드 | 타입 | 기본값 | 설명 | 예시 |
|------|------|--------|------|------|
| `requirement` | string | `"REQ-{3자리}"` | 요구사항ID 채번 규칙 | `"B-RE-{3자리}"` |
| `function` | string | `"FN-{3자리}"` | 기능ID 채번 규칙 | `"B-FN-{3자리}"` |
| `test` | string | `"UT-{3자리}"` | 테스트ID 채번 규칙 | `"B-UT-{3자리}"` |

- `{3자리}` 는 001 부터 이어지는 순번이다. 자릿수를 바꾸려면 `{4자리}` 처럼 적는다
- **세 ID 는 서로 파생 관계가 아니다.** 각각 독립 채번하고 연결은 `연계~ID` 열이 맡는다
- **`idNaming` 이 없으면 커맨드가 AskUserQuestion 으로 한 번 묻고 여기에 저장한다.**
  묻는 자리는 `templates/id-naming-rules.md` §채번 규칙은 프로파일이 정한다 가 정본이다
  (`/gx-프로젝트설정` Step 3-1 에서 미리 정하거나, 처음 채번하는 커맨드가 묻는다).
  한 번 저장하면 다시 묻지 않는다
- 산출물이 이미 있는 프로젝트(B·C·D 유형)에서는 묻기 전에 기존 산출물의 ID 표기를
  읽어 기본값으로 제시한다 — 같은 프로젝트에서 채번 규칙이 갈리면 추적이 끊긴다

### 소비처 없는 필드 — `prefix` · `networkType`

기능 축 전환(v3.0.0)으로 이 두 필드를 쓰던 산출물이 `archive/` 로 내려갔다.
**현재 5종(AN-02 · AN-03 · DE-08 · DE-13 · AN-05) 어디에도 이 값을 적는 열이나
머리말 항목이 없다.** 사용자에게 묻기는 하되 "어딘가 쓰인다" 고 말하지 않는다.

| 필드 | 옛 소비처 | 지금 |
|------|---------|------|
| `prefix` | 화면ID 접두어 (`EHR_01_01_010`) | 없음. 파생 ID 폐지로 소멸 |
| `networkType` | DE-03 의 망구분 열 기본값 | 없음. 그 산출물이 `archive/` 로 갔다 |

**그런데도 필수 필드로 남긴 이유**: 지우면 세 곳이 함께 흔들린다 — 이 표,
`skills/load-project-profile/SKILL.md` 의 필수 필드 검사 목록,
`/gx-프로젝트설정` Step 3 의 질문. 게다가 기존 `profile.json` 이 필수 필드 누락으로
읽히지 않게 되고, `archive/` 의 산출물을 되살리면 다시 쓰인다.

**뺄지 남길지 판단할 때**: 감리가 있는 공공 사업에서 `archive/` 를 되살릴 계획이
없다면 위 세 곳을 **함께** 고쳐 제거한다. 한 곳만 고치면 프로파일을 읽지 못한다.

---

## 요구사항 검토 상태 — requirements-state.json

프로젝트 폴더의 내부 검토 상태 파일이다. 제출용 AN-02 10열과 확인요청서 양식은 유지한다.
요구사항 작성·수정 시 review-confirmations가 관리하고 detect-existing-artifact·reconcile-ids·apply-confirmations가
읽고 갱신한다. 원문·요구사항·결정의 근거를 파일에서 다시 확인하며 대화 기억이나 수정 시각만으로 판단하지 않는다.

| 필드 | 내용 |
|---|---|
| `schemaVersion` | `1` |
| `inputScope` | `full`(전체 개정본) / `partial`(부분 수정) / `additional`(추가 자료) |
| `sources` | 자료별 `id`·`path`·개정/수신 기준 `revision`·실제 파일 `sha256` |
| `requirements` | 요구사항ID별 `contentHash`·`sourceRefs`·`classification`·`priority`·`decisionRefs`. 미정값은 미정으로 기록 |
| `decisions` | CQ별 대상 요구사항ID·필드·`basisHash`·실제 `response`·`status`. 근거가 바뀌면 영향을 받는 결정만 재확인 |
| `idHistory` | `requirement`·`function`·`test`별 사용한 전체 ID 배열. 삭제 ID 포함, 합집합으로 누적 |
| `documents` | `AN-02`·`AN-03`·`DE-08`·`DE-13`·`AN-05` 키별 `version`·파일 SHA-256인 `contentHash`·`status`(초안/부분확정/확정)·`openCQ` 배열·미반영 상위 변경 `upstreamChanges` 배열 |

해시는 실제 파일 또는 필드 이름과 값을 정렬해 직렬화한 요구사항 행의 SHA-256으로 계산한다.
원본 자료가 바뀌면 사본·이전 기준을 보존하고 ID·필드에 연결된 변경을 대조한다. 사람이 본문을 직접 수정해
버전이 같아도 내용 지문이 다르면 검토 대상으로 표시한다. 파일이 없는 기존 프로젝트는 현재 파일·이력에서
확인한 기준과 사용 번호만 이관한다. 확인할 수 없는 과거 승인을 만들어 넣지 않는다.
쓰기 전에 기존 상태를 백업하고 JSON 구문과 대상 경로를 검증한다. 문서 저장에 실패하면 상태만 확정으로
올리지 않는다. 사용자 응답 없이 `response`·확정 상태를 채우지 않으며 내부 상태를 고객 Excel로 내보내지 않는다.

## 프로젝트 유형 상세

| type 값 | typeLabel | 설명 |
|---------|-----------|------|
| `new` | A. 신규 구축 | RFP/과업지시서만 있고, 코드도 산출물도 없음. 설계부터 시작 |
| `enhancement` | B. 추가 개발 | 운영 중인 시스템에 새로운 요구사항(신규 기능)을 추가. 기존 코드/산출물은 유지하고 새 것만 추가 |
| `documentation` | C. 산출물 정비 | 개발은 끝났는데 산출물이 없거나 실제와 안 맞음. 코드/DB를 기준으로 산출물을 역생성하거나 맞춤 정비 |
| `change` | D. 변경 관리 | 운영 중 시스템의 기존 기능/테이블을 수정하는 건. 변경요청서 기반으로 영향받는 산출물만 골라서 갱신 |

### 유형별 필수 자산

| 유형 | sourcePath | ddlFile | existingArtifacts |
|------|-----------|---------|-------------------|
| A. 신규 구축 | 불필요 | 불필요 | 불필요 |
| B. 추가 개발 | 권장 | 권장 | 권장 |
| C. 산출물 정비 | **필수** | 권장 | 선택 |
| D. 변경 관리 | 권장 | 권장 | 권장 |

---

## 예시

```json
{
  "name": "교육행정시스템 고도화",
  "type": "enhancement",
  "typeLabel": "B. 추가 개발",
  "systemCode": "B",
  "prefix": "EHR",
  "framework": "egovframe",
  "db": "oracle",
  "author": "홍길동",
  "networkType": "mixed",
  "auditDate": "2026-06-15",
  "idNaming": {
    "requirement": "B-RE-{3자리}",
    "function": "B-FN-{3자리}",
    "test": "B-UT-{3자리}"
  },
  "assets": {
    "sourcePath": "D:\\projects\\ehr-system",
    "ddlFile": "ddl.sql",
    "existingArtifacts": null
  },
  "createdAt": "2026-03-31",
  "lastUsed": "2026-03-31"
}
```
