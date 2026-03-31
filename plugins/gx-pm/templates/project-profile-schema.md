# 프로젝트 프로파일 스키마

프로젝트 설정 정보를 저장하는 `profile.json`의 구조를 정의한다.
`/프로젝트설정` 커맨드가 이 파일을 생성하고, 모든 커맨드가 이 파일을 참조한다.

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
| `systemCode` | string | Y | 시스템 코드 (영문) | `"B"` |
| `prefix` | string | Y | 시스템 접두어 (화면ID용) | `"EHR"` |
| `framework` | string | Y | 프레임워크 유형 | `"egovframe"`, `"springboot"`, `"other"` |
| `db` | string | Y | DB 유형 | `"oracle"`, `"postgresql"`, `"mysql"`, `"other"` |
| `author` | string | Y | 작성자명 | `"홍길동"` |
| `networkType` | string | Y | 망 구분 | `"internal"`, `"external"`, `"mixed"` |
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

---

## 프로젝트 유형 상세

| type 값 | typeLabel | 설명 |
|---------|-----------|------|
| `new` | A. 신규 구축 | RFP/과업지시서만 있고, 코드도 산출물도 없음. 설계부터 시작 |
| `enhancement` | B. 추가 개발 | 운영 중인 시스템에 새로운 요구사항(신규 화면, 신규 기능)을 추가. 기존 코드/산출물은 유지하고 새 것만 추가 |
| `documentation` | C. 산출물 정비 | 개발은 끝났는데 산출물이 없거나 실제와 안 맞음. 코드/DB를 기준으로 산출물을 역생성하거나 맞춤 정비 |
| `change` | D. 변경 관리 | 운영 중 시스템의 기존 화면/기능/테이블을 수정하는 건. 변경요청서 기반으로 영향받는 산출물만 골라서 갱신 |

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
  "assets": {
    "sourcePath": "D:\\projects\\ehr-system",
    "ddlFile": "ddl.sql",
    "existingArtifacts": null
  },
  "createdAt": "2026-03-31",
  "lastUsed": "2026-03-31"
}
```
