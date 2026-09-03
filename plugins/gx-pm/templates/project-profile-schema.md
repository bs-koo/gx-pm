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
        ├── ddl.sql             ← DDL 원본 (선택)
        ├── {시스템코드}-*.md   ← 산출물들
        ├── backup/             ← 이전 버전 백업
        └── xlsx/               ← 엑셀 추출물
```

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
| `createdAt` | string | Y | 프로파일 생성일 (YYYY-MM-DD) | `"2026-03-31"` |
| `lastUsed` | string | Y | 마지막 사용일 (YYYY-MM-DD) | `"2026-03-31"` |

### assets 객체

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `sourcePath` | string\|null | 소스코드 로컬 경로 | `"D:\\projects\\ehr-system"` |
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
