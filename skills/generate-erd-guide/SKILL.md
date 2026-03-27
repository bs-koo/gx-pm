---
name: generate-erd-guide
description: 요구사항과 화면에서 엔터티/관계를 도출하고, ERDCloud 입력용 DDL과 테이블정의서 초안을 생성합니다.
---

# ERD 설계 가이드 (generate-erd-guide)

요구사항정의서와 화면목록표를 분석하여 필요한 엔터티를 식별하고, 엔터티 간 관계를 도출한 뒤, ERDCloud에 바로 입력할 수 있는 DDL 초안과 DE-08 테이블정의서 초안을 생성한다.

---

## 입력

| 항목 | 필수 여부 | 설명 |
|---|---|---|
| 요구사항 목록 또는 화면목록 | 필수 | 요구사항 설명 또는 DE-03 화면목록표 |
| DB 유형 | 필수 | Oracle / PostgreSQL / MySQL |
| 테이블 네이밍 접두어 | 권장 | 예: `EHR_`, `CMS_` (없으면 생략) |
| 기존 테이블정의서 | 선택 | 있으면 기존 구조 참고, 신규 테이블만 추가 |

---

## 처리 절차

### Step 1: 엔터티 식별

요구사항/화면 설명에서 **관리 대상 데이터**를 나타내는 키워드를 추출하여 엔터티를 도출한다.

엔터티 식별 키워드:

| 키워드 유형 | 예시 키워드 | 도출 엔터티 예시 |
|---|---|---|
| 등록/관리 대상 | "환자를 등록한다", "회원 관리" | 환자(PATIENT), 회원(MEMBER) |
| 이력/로그 | "변경 이력을 관리한다", "접속 로그" | 변경이력(CHANGE_HIST), 접속로그(ACCESS_LOG) |
| 목록/현황 | "공지사항 목록", "결재 현황" | 공지사항(NOTICE), 결재(APPROVAL) |
| 첨부/파일 | "파일을 첨부한다", "첨부파일 관리" | 첨부파일(ATTACH_FILE) |
| 코드/공통 | "코드 관리", "공통코드" | 공통코드(COMMON_CODE) |
| 권한/메뉴 | "권한 관리", "메뉴 관리" | 권한(AUTHORITY), 메뉴(MENU) |

공통 엔터티 패턴 (대부분의 공공/SI 프로젝트에 공통 적용):

| 엔터티명 | 테이블명 예시 | 용도 |
|---|---|---|
| 사용자 | `EHR_USER` | 시스템 사용자/관리자 정보 |
| 공통코드 | `EHR_CMMNCODE` | 공통 코드 마스터 |
| 공통코드상세 | `EHR_CMMNCODE_DTL` | 공통 코드 상세값 |
| 게시판 | `EHR_BOARD` | 공지/게시판 기본 정보 |
| 첨부파일 | `EHR_ATTACH_FILE` | 공통 첨부파일 |
| 이력 | `EHR_{엔터티}_HIST` | 변경 이력 |
| 메뉴 | `EHR_MENU` | 시스템 메뉴 구조 |
| 권한 | `EHR_AUTHOR` | 사용자 권한 |

---

### Step 2: 엔터티 간 관계 도출

식별된 엔터티 간 관계 유형을 결정한다.

관계 도출 규칙:

| 관계 유형 | 판단 기준 | 예시 |
|---|---|---|
| 1:1 | 한 엔터티가 다른 엔터티를 정확히 한 번 참조 | 사용자 1:1 사용자상세정보 |
| 1:N | 부모 엔터티가 여러 자식 엔터티를 가짐 | 사용자 1:N 첨부파일 |
| N:M | 양쪽 엔터티가 서로 여러 개 참조 (중간 테이블 필요) | 사용자 N:M 권한 → 사용자권한매핑 |

관계 설명 출력 형식:
```
[사용자] 1 ─── N [첨부파일]  : 사용자 한 명이 여러 첨부파일 보유
[공지사항] 1 ─── N [첨부파일] : 공지사항 한 건에 여러 첨부파일 허용
[사용자] N ─── M [권한]       : 중간 테이블 EHR_USER_AUTHOR 필요
```

---

### Step 3: 컬럼 설계

컬럼 네이밍 규칙:

| 컬럼 유형 | 네이밍 규칙 | 예시 |
|---|---|---|
| PK (순번형) | `{테이블약어}_SN` | `USER_SN`, `NOTICE_SN` |
| PK (코드형) | `{테이블약어}_ID` | `AUTHOR_ID`, `MENU_ID` |
| FK | 참조 테이블의 PK명 그대로 사용 | 참조 PK가 `USER_SN`이면 FK도 `USER_SN` |
| 코드 컬럼 | `{의미}_CD` | `STAT_CD`, `TYPE_CD` |
| 여부 컬럼 | `{의미}_YN` | `DEL_YN`, `USE_YN` |
| 일시 컬럼 | `{의미}_DT` | `REG_DT`, `MOD_DT` |
| 내용 컬럼 | `{의미}_CN` | `NOTICE_CN`, `RMRK_CN` |

공통 컬럼 (모든 테이블에 반드시 포함):

| 컬럼명 | 설명 | DB별 타입 |
|---|---|---|
| `REG_DT` | 등록일시 | Oracle: DATE / PG: TIMESTAMP / MySQL: DATETIME |
| `REG_ID` | 등록자ID | VARCHAR2(20) / varchar(20) / varchar(20) |
| `MOD_DT` | 수정일시 | Oracle: DATE / PG: TIMESTAMP / MySQL: DATETIME |
| `MOD_ID` | 수정자ID | VARCHAR2(20) / varchar(20) / varchar(20) |
| `DEL_YN` | 삭제여부 | CHAR(1) DEFAULT 'N' |

---

### Step 4: DDL 생성 (ERDCloud 호환)

DB 유형별 DDL 생성 규칙:

**Oracle**
```sql
CREATE TABLE EHR_USER (
    USER_SN     NUMBER          NOT NULL,
    USER_ID     VARCHAR2(20)    NOT NULL,
    USER_NM     VARCHAR2(100)   NOT NULL,
    AUTHOR_ID   VARCHAR2(20),
    USE_YN      CHAR(1)         DEFAULT 'Y' NOT NULL,
    DEL_YN      CHAR(1)         DEFAULT 'N' NOT NULL,
    REG_DT      DATE            NOT NULL,
    REG_ID      VARCHAR2(20)    NOT NULL,
    MOD_DT      DATE,
    MOD_ID      VARCHAR2(20),
    CONSTRAINT PK_EHR_USER PRIMARY KEY (USER_SN)
);
```

**PostgreSQL**
```sql
CREATE TABLE ehr_user (
    user_sn     SERIAL          NOT NULL,
    user_id     VARCHAR(20)     NOT NULL,
    user_nm     VARCHAR(100)    NOT NULL,
    author_id   VARCHAR(20),
    use_yn      CHAR(1)         DEFAULT 'Y' NOT NULL,
    del_yn      CHAR(1)         DEFAULT 'N' NOT NULL,
    reg_dt      TIMESTAMP       NOT NULL DEFAULT NOW(),
    reg_id      VARCHAR(20)     NOT NULL,
    mod_dt      TIMESTAMP,
    mod_id      VARCHAR(20),
    CONSTRAINT pk_ehr_user PRIMARY KEY (user_sn)
);
```

**MySQL**
```sql
CREATE TABLE ehr_user (
    user_sn     INT             NOT NULL AUTO_INCREMENT,
    user_id     VARCHAR(20)     NOT NULL,
    user_nm     VARCHAR(100)    NOT NULL,
    author_id   VARCHAR(20),
    use_yn      CHAR(1)         DEFAULT 'Y' NOT NULL,
    del_yn      CHAR(1)         DEFAULT 'N' NOT NULL,
    reg_dt      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reg_id      VARCHAR(20)     NOT NULL,
    mod_dt      DATETIME        ON UPDATE CURRENT_TIMESTAMP,
    mod_id      VARCHAR(20),
    PRIMARY KEY (user_sn)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

ERDCloud 입력 시 유의사항:
- ERDCloud는 표준 SQL DDL을 그대로 붙여넣기하면 자동으로 ERD 다이어그램을 생성한다.
- Oracle의 경우 `CONSTRAINT` 구문이 포함된 DDL을 지원한다.
- 외래키(FK) 제약조건은 DDL에 포함하면 ERDCloud에서 관계선이 자동 생성된다.

---

### Step 5: 테이블정의서 초안 생성 (DE-08)

각 테이블별로 아래 형식의 테이블정의서 초안을 출력한다.

#### 테이블 기본 정보

| 항목 | 내용 |
|---|---|
| 테이블ID | EHR_USER |
| 테이블명(논리) | 사용자 |
| 테이블명(물리) | EHR_USER |
| 설명 | 시스템 사용자 및 관리자 기본 정보를 관리하는 테이블 |

#### 컬럼 정의

| NO | 컬럼ID(물리) | 컬럼명(논리) | 데이터타입 | 길이 | NULL여부 | 기본값 | PK | FK | 설명 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | USER_SN | 사용자순번 | NUMBER | - | NOT NULL | - | PK | - | 자동증가 순번 |
| 2 | USER_ID | 사용자ID | VARCHAR2 | 20 | NOT NULL | - | - | - | 로그인 ID |
| 3 | USER_NM | 사용자명 | VARCHAR2 | 100 | NOT NULL | - | - | - | 사용자 이름 |
| 4 | AUTHOR_ID | 권한ID | VARCHAR2 | 20 | NULL | - | - | FK | EHR_AUTHOR.AUTHOR_ID 참조 |
| 5 | USE_YN | 사용여부 | CHAR | 1 | NOT NULL | Y | - | - | Y: 사용, N: 미사용 |
| 6 | DEL_YN | 삭제여부 | CHAR | 1 | NOT NULL | N | - | - | Y: 삭제, N: 정상 |
| 7 | REG_DT | 등록일시 | DATE | - | NOT NULL | - | - | - | 레코드 등록 일시 |
| 8 | REG_ID | 등록자ID | VARCHAR2 | 20 | NOT NULL | - | - | - | 레코드 등록한 사용자ID |
| 9 | MOD_DT | 수정일시 | DATE | - | NULL | - | - | - | 최종 수정 일시 |
| 10 | MOD_ID | 수정자ID | VARCHAR2 | 20 | NULL | - | - | - | 최종 수정한 사용자ID |

---

## 주의사항 / 규칙

1. **PK 자동증가**: Oracle은 SEQUENCE + TRIGGER 또는 GENERATED AS IDENTITY 사용. PostgreSQL은 SERIAL 또는 GENERATED ALWAYS AS IDENTITY. MySQL은 AUTO_INCREMENT.
2. **DEL_YN 소프트 삭제**: 공공 시스템은 물리 삭제 대신 DEL_YN = 'Y' 처리가 원칙. DELETE 쿼리 사용 금지.
3. **N:M 관계**: 반드시 중간 매핑 테이블을 생성한다. 중간 테이블명은 `{테이블A}_{테이블B}_MAP` 형식.
4. **이력 테이블**: 주요 데이터 변경이 필요한 엔터티는 `_HIST` 접미사 테이블을 별도 생성 권장.
5. **ERDCloud DDL 주의**: Oracle DDL은 ERDCloud에서 일부 구문 오류가 발생할 수 있으므로 CONSTRAINT 구문을 단순화할 것.
6. **테이블정의서와 DDL 동기화**: 컬럼 추가/변경 시 DDL과 테이블정의서를 반드시 함께 수정해야 한다.
