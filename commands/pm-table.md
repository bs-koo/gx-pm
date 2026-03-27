---
description: ERDCloud DDL을 테이블정의서로 변환하거나, 요구사항에서 ERD 설계 가이드를 생성합니다
argument-hint: "<DDL 텍스트 또는 '역방향'>"
---

# /pm-table — 테이블 설계 (ERDCloud 연계)

ERDCloud DDL ↔ 테이블정의서(DE-08) 양방향 변환 워크플로우.

## 호출 예시

```
/pm-table CREATE TABLE users (...)
/pm-table [DDL 파일 업로드]
/pm-table 역방향               # 요구사항 → DDL 생성
/pm-table                      # 방향 선택
```

## 워크플로우

### Step 1: 방향 결정

인자가 DDL이면 → 정방향 (DDL → 테이블정의서)
"역방향"이면 → 역방향 (요구사항 → DDL)
없으면 → 사용자에게 선택:
  1. "ERDCloud DDL → 테이블정의서" (정방향)
  2. "요구사항/화면 → ERD 설계 + DDL" (역방향)

### [정방향] Step 2a: DDL → 테이블정의서

**convert-ddl-to-tablespec** 스킬 적용:
1. DDL 파싱 (테이블, 컬럼, 타입, PK/FK/NotNull)
2. COMMENT 파싱 (있으면 한글명 추출)
3. 한글명 추론 (COMMENT 없으면 컬럼명에서 추론)
4. 체크포인트: "한글 속성명이 맞는지 확인해주세요"
5. DE-08 양식으로 출력

### [역방향] Step 2b: 요구사항 → DDL

**generate-erd-guide** 스킬 적용:
1. 요구사항/화면에서 필요한 엔터티 식별
2. 엔터티 간 관계 도출 (1:N, N:M)
3. 주요 컬럼 + PK/FK 설계
4. ERDCloud 입력용 DDL 생성
5. 테이블정의서 초안도 함께 출력

### Step 3: 결과 저장

- `{시스템코드}-테이블정의서.md`
- (역방향 시) `{시스템코드}-DDL.sql`

### Step 4: 다음 단계 제안

- "/pm-test 로 테스트 계획서를 만들까요?"
- "/pm-trace 로 추적매트릭스를 갱신할까요?"
