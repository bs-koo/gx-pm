---
name: convert-ddl-to-tablespec
description: ERDCloud에서 내보낸 DDL(Create Table SQL)을 DE-08 테이블정의서 형식으로 변환합니다.
---

# DDL → 테이블정의서 변환 (convert-ddl-to-tablespec)

ERDCloud 또는 기타 도구에서 내보낸 DDL(Create Table SQL)을 파싱하여, DE-08 테이블정의서 양식에 맞는 구조화된 데이터를 생성한다.

## 입력

다음 중 하나:
- DDL 텍스트 (붙여넣기)
- .sql 또는 .txt 파일 업로드
- ERDCloud "모든 테이블 생성 SQL" 내보내기 결과

## 처리 절차

### Step 1: DDL 파싱
SQL CREATE TABLE 문을 파싱한다:

```sql
CREATE TABLE 테이블명 (
  컬럼명 데이터타입(길이) [NOT NULL] [DEFAULT 값],
  ...
  PRIMARY KEY (컬럼1, 컬럼2),
  FOREIGN KEY (컬럼) REFERENCES 참조테이블(참조컬럼)
);
```

추출 항목:
- 테이블명 (물리명)
- 각 컬럼: 컬럼명, 데이터타입, 길이, 소수점, 기본값, NOT NULL 여부
- PRIMARY KEY 컬럼 목록
- FOREIGN KEY 관계

### Step 2: COMMENT 파싱 (있으면)
```sql
COMMENT ON TABLE 테이블명 IS '엔터티명';
COMMENT ON COLUMN 테이블명.컬럼명 IS '속성명';
```

COMMENT가 없으면 Step 3에서 한글명을 추론한다.

### Step 3: 한글명 추론
COMMENT가 없는 경우:
- 테이블명에서 엔터티명 추론 (예: `USER_INFO` → `사용자 정보`)
- 컬럼명에서 속성명 추론 (예: `EMP_NO` → `직원번호`, `REG_DT` → `등록일시`)
- 추론 결과를 사용자에게 확인 요청

공통 컬럼명 사전:
| 영문 패턴 | 한글 속성명 |
|----------|-----------|
| *_NO | ~번호 |
| *_NM | ~명 |
| *_CD | ~코드 |
| *_DT, *_DTM | ~일시 |
| *_YN | ~여부 |
| *_CN | ~내용 |
| *_SN | ~일련번호 |
| REG_* | 등록~ |
| MOD_*, UPD_* | 수정~ |
| DEL_* | 삭제~ |
| USE_* | 사용~ |

### Step 4: 테이블정의서 생성
DE-08 양식에 맞게 출력한다.

## 출력 형식

```
## 테이블정의서 — {시스템명}

### {엔터티명} ({테이블명})

| 컬럼명 | 속성명 | 데이터타입 | 길이 | 소수점 | 기본값 | PK | FK | NotNull |
|--------|--------|-----------|------|--------|--------|----|----|---------|
| EMP_NO | 직원번호 | VARCHAR2 | 13 | | | Y | | Y |
| CORS_CD | 과정코드 | VARCHAR2 | 50 | | | Y | | Y |
```

테이블별로 섹션을 나누어 출력한다.

## 역방향: 테이블정의서 → DDL

사용자가 요청하면 반대 방향 변환도 수행한다:
- 마크다운 테이블 → CREATE TABLE SQL
- ERDCloud에 바로 입력할 수 있는 형식으로 출력

## 지원 DB

- Oracle (VARCHAR2, NUMBER, DATE, CLOB 등)
- PostgreSQL (varchar, integer, timestamp 등)
- MySQL (varchar, int, datetime 등)
- 자동 감지: 데이터타입으로 DB 유형 판별
