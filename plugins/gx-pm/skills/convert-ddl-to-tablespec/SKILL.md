---
name: convert-ddl-to-tablespec
description: DDL(Create Table SQL)을 DE-08 테이블정의서 형식으로 변환합니다. ERDCloud, DataGrip, DBeaver 등에서 복사한 DDL을 지원합니다.
---

# DDL → 테이블정의서 변환 (convert-ddl-to-tablespec)

DDL(Create Table SQL)을 파싱하여, DE-08 테이블정의서 양식에 맞는 구조화된 데이터를 생성한다.
ERDCloud, DataGrip, DBeaver 등 다양한 출처의 DDL을 지원한다.

## 입력

다음 중 하나:
- DDL 텍스트 (클립보드 붙여넣기)
- .sql 또는 .txt 파일 경로
- ERDCloud "모든 테이블 생성 SQL" 내보내기 결과
- 프로젝트 폴더의 `ddl.sql` 파일 (프로젝트설정 시 저장된 것)

### DDL 복사 방법 안내

프로파일에 `ddl.sql`이 있으면 자동 로드한다.
없으면 **AskUserQuestion 도구**로 다음 안내와 함께 DDL 입력을 요청한다:

```
DB 스키마의 전체 DDL을 복사해서 붙여넣어 주세요.

  [DataGrip에서 복사하기]
    1. 좌측 Database 패널에서 스키마(Schema) 우클릭
    2. SQL Scripts → Generate DDL to Clipboard
    3. 여기에 Ctrl+V로 붙여넣기

  [DBeaver에서 복사하기]
    1. 좌측 Database Navigator에서 스키마(Schema) 우클릭
    2. Generate SQL → DDL 선택
    3. 팝업 창에서 Ctrl+A(전체선택) → Ctrl+C(복사)
    4. 여기에 Ctrl+V로 붙여넣기
    ※ 또는: 스키마 우클릭 → Tools → Generate DDL

  [ERDCloud에서 복사하기]
    1. ERD 화면에서 "SQL 내보내기" 버튼 클릭
    2. "모든 테이블 생성 SQL" 선택
    3. 복사하여 여기에 붙여넣기

DDL을 붙여넣어 주세요:
```

## 처리 절차

### Step 1: 기존 스키마 로드

DDL 을 파싱해 테이블·컬럼 목록을 만든다. 전건의 `구분` 을 `기존` 으로 둔다.

```sql
CREATE TABLE 테이블명 (
  컬럼명 데이터타입(길이) [NOT NULL] [DEFAULT 값],
  PRIMARY KEY (컬럼1),
  FOREIGN KEY (컬럼) REFERENCES 참조테이블(참조컬럼)
);
```

`COMMENT ON COLUMN` 이 있으면 `컬럼 논리명` 으로 쓴다.

DDL 이 없으면 기존 스키마 없음으로 보고 Step 2 로 간다 (전건이 신규가 된다).

### Step 2: 기능명세 입력항목 매핑

AN-03 의 `입력항목` 을 파싱해 기존 컬럼에 매핑한다.

| 매핑 결과 | 처리 |
|----------|------|
| 기존 컬럼에 대응됨 | `연계기능ID` 를 채운다. `컬럼 논리명` 이 비었으면 입력항목의 항목명으로 채운다 |
| 대응 없음 | **신규 컬럼 후보.** `구분` 을 `신규` 로 둔다 |
| 기존 컬럼인데 제약이 다름 | `구분` 은 `기존` 으로 두고 비고에 불일치를 적는다 — 스키마를 바꾸지 않는다 |

제약 불일치는 버리지 않고 게이트에서 목록으로 보고한다.
`입력항목 50자 ↔ 컬럼 VARCHAR(100)` 은 둘 중 하나가 틀렸다는 뜻이다.

### Step 3: 기존 컬럼 표준 검증

`sqi-comn-term` MCP 가 세션에 있는지 먼저 확인한다. 없으면
`docs/표준용어-mcp-연계.md` 의 설치 안내를 출력하고 **중단한다.**
표준 검증 없이 컬럼명을 **지어내지 않는다.**

`sourcePriority` 는 프로파일에서 읽고, 없으면 `["BLDG_ENGY", "MOIS_STD"]` 를 제안하고 묻는다.

```
validate_column(columnNames=[기존 컬럼 전건], sourcePriority=[...])
```

| 결과 | 표준 판정 | 표준 권고명 |
|------|----------|-----------|
| `PASS` | `표준준수` | 공란 |
| `PARTIAL` · `FAIL` | `현행유지` | `표준은 {suggestedColumnName}` |

**기존 컬럼을 표준형으로 바꾸자고 제안하지 않는다.**

### Step 4: 신규 컬럼 표준 도출

```
translate_column(inputs=[신규 컬럼 논리명 전건], sourcePriority=[...])
```

| 결과 | 처리 |
|------|------|
| `FULL` | `신규적용` 으로 확정 제시. `근거` 에 `{ctgryNms} · {단어 매칭}` |
| `PARTIAL` · `AI_SUGGESTED` | 근거와 함께 제시. 사용자가 반려하면 대안을 묻는다 |
| `FAIL` · `decisionRequired=true` | **그 자리에서 사용자 선택.** `humanHint` 를 그대로 보여준다 |
| `dataTypeCandidates` 다건 | 타입 후보를 나열하고 선택을 요청 |

이 중단점은 **게이트로 이월하지 않는다** — `templates/pipeline-protocol.md` §이월 금지 항목.
컬럼명이 확정돼야 DE-13 의 경계값이 그 위에 선다.

### Step 5: 승인 게이트

신규 컬럼만 승인 대상이다. 기존은 확인용으로만 보여준다.

```
신규 컬럼 12건에 표준 컬럼명을 제안합니다.  (출처: BLDG_ENGY → MOIS_STD)

[신규 · 승인 필요]
  권한명        → AUTH_NM       권한=AUTH, 명=NM              VARCHAR(200)
  관측일자      → OBSRVN_YMD    관측=OBSRVN, 일자=YMD          CHAR(8)
  일평균기온    → ???_ARTMP     기온=ARTMP, 앞 단어 미확정  선택 필요

[기존 · 변경하지 않음]  비표준이지만 현재 사용 중이라 유지합니다.
  REGION_CD   (표준은 RGN_CD)    · TB_BLDG
  LATITUDE    (표준은 LAT)       · TB_BLDG

[제약 불일치]  기능명세와 스키마가 어긋납니다.
  FN-007 권한명 50자  ↔  TB_AUTH.AUTH_NM VARCHAR(100)
```

**AskUserQuestion 으로 묻는다.** `templates/approval-protocol.md` 의 인자 규칙을 따른다.

### Step 6: 개정이력

**manage-revision-history** 스킬로 개정이력 행을 만든다.
불변 키는 `테이블명 + 컬럼명` 이다.

## 출력 형식

`templates/DE-08-table-definition.md` 의 컬럼 순서를 그대로 쓴다.
개정이력 표를 맨 위에 둔다.

## 주의사항

- 요구사항에서 테이블을 추론하지 않는다. 이 스킬은 역생성 전용이다
- 기존 컬럼의 이름·타입·제약을 바꾸지 않는다
- 표준 검증 없이 컬럼명을 지어내지 않는다
