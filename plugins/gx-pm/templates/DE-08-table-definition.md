# DE-08 테이블정의서 양식

## 파일 형식
Excel (.xlsx) — 단일 시트 (Data)

## 본문 컬럼 구조

| 컬럼 | 설명 | 예시 |
|------|------|------|
| 테이블명 | 물리 테이블명 | CDP_EXC_CRCMP |
| 엔터티명 | 논리 엔터티명 (한글) | CDP 예외 수료 정보 |
| 컬럼명 | 물리 컬럼명 | EMP_NO |
| 속성명 | 논리 속성명 (한글) | 직원번호 |
| 데이터타입 | 데이터 타입 | VARCHAR2 |
| 길이 | 데이터 길이 | 13 |
| 소수점 | 소수점 자릿수 | (빈칸) |
| 기본값 | 기본값 | (빈칸) |
| PK | Primary Key 여부 | Y / (빈칸) |
| FK | Foreign Key 여부 | Y / (빈칸) |
| 컬럼 NotNull | Not Null 여부 | Y / N |

## 작성 규칙

- 하나의 시트에 모든 테이블을 나열 (테이블명 기준 그룹핑)
- 같은 테이블의 컬럼들은 연속으로 배치
- PK 컬럼은 테이블 상단에 배치
- FK가 있으면 참조 테이블 정보를 별도 시트나 비고에 기재 가능
- ERDCloud에서 DDL 내보내기 시 이 양식으로 변환

## DDL → 테이블정의서 변환 매핑

```
CREATE TABLE 테이블명 (       → 테이블명
  컬럼명 데이터타입(길이),     → 컬럼명, 데이터타입, 길이
  PRIMARY KEY (컬럼명)        → PK: Y
  FOREIGN KEY ... REFERENCES  → FK: Y
  NOT NULL                    → 컬럼 NotNull: Y
)
COMMENT ON TABLE = '엔터티명'  → 엔터티명
COMMENT ON COLUMN = '속성명'  → 속성명
```
