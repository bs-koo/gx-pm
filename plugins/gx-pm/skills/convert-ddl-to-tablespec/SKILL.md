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
없으면 AskUserQuestion으로 다음 안내와 함께 DDL 입력을 요청한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

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

## 대량 DDL 처리

테이블이 많은 경우 (50개 이상):
1. 전체 테이블 목록을 먼저 표시 (테이블명 + 컬럼 수만)
2. AskUserQuestion으로 확인: "전체 {N}개 테이블을 변환합니다. 진행할까요?"
3. 10개씩 끊어서 표시 + 승인 루프 (한 번에 50개 표를 보여주면 확인이 어려움)
4. 모든 테이블 승인 후 전체를 하나의 파일로 저장

## Entity 클래스에서 역추출

DDL 대신 JPA Entity 클래스에서도 테이블정의서를 생성할 수 있다:

```
Glob 패턴:
  - **/entity/**/*.java
  - **/domain/**/*.java
  - **/*Entity.java

추출 항목:
  - @Table(name="...") → 테이블명
  - @Column(name="...", length=N, nullable=false) → 컬럼 정보
  - @Id → PK
  - @ManyToOne, @JoinColumn → FK 관계
```

프로파일의 `type`이 `documentation`(C)이고 소스 경로가 있으면,
DDL 입력 대신 Entity 클래스 스캔을 선택지로 제공한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
테이블정의서를 어떤 소스에서 생성할까요?

  1. DDL 붙여넣기 (DataGrip/DBeaver에서 복사)
  2. Entity 클래스 스캔 (소스코드의 @Entity에서 추출)
  3. 프로젝트 DDL 파일 사용 (ddl.sql)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 지원 DB

- Oracle (VARCHAR2, NUMBER, DATE, CLOB 등)
- PostgreSQL (varchar, integer, timestamp 등)
- MySQL (varchar, int, datetime 등)
- 자동 감지: 데이터타입으로 DB 유형 판별 (프로파일의 db 설정값도 참조)
