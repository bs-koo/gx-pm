---
name: reverse-scan-source
description: 실제 소스코드 프로젝트를 스캔하여 DE-05 프로그램정의서를 역생성합니다.
---

# 소스코드 역스캔 → 프로그램정의서 (reverse-scan-source)

소스코드의 Controller, Service, DAO, JSP 등을 스캔하여
실제 구현된 프로그램 목록을 DE-05 프로그램정의서 양식으로 역생성한다.

---

## 입력

| 항목 | 필수 | 설명 |
|------|------|------|
| sourcePath | Y | 소스코드 경로 (profile.json) |
| framework | Y | 프레임워크 유형 (profile.json) |
| prefix | Y | 시스템 접두어 (profile.json) |
| systemCode | Y | 시스템 코드 (profile.json) |
| source-index.json | 권장 | scan-source-index 결과 (없으면 자동 스캔) |

---

## 처리 절차

### Step 1: 소스 인덱스 로드

`source-index.json`이 있으면 로드. 없으면 **scan-source-index** 스킬을 먼저 실행하여 Level 1+2 스캔.

### Step 2: Controller 기반 프로그램 목록 조립

source-index.json의 `controllers` 데이터를 기반으로:

1. **Controller별 연관 파일 그룹핑**:
   - Controller 패키지 경로에서 업무 영역 추론 (패키지 깊이에 따른 유연한 매핑 로직 적용)
     예: `kr.go.energy.ehr.system.authority.web.AuthorityController`
     → 대분류: 시스템관리, 중분류: 권한관리
   - 패키지 깊이가 얕은 경우(예: `com.example.controller`), 사용자에게 기준 패키지 뎁스를 확인받는다
   - 같은 패키지의 Service, DAO, VO 자동 매칭
   - 같은 업무 영역의 JSP/HTML 파일 매칭
   - 같은 namespace의 Mapper XML 매칭

2. **URL 패턴 추출**:
   - `@RequestMapping` 값에서 URL 추출
   - eGovFrame: `/system/authority/list.do` 패턴
   - Spring Boot: `/api/system/authority` 패턴

3. **화면ID 역추론**:
   - JSP 파일명 또는 URL 패턴에서 화면ID를 역추론
   - 패턴: `{prefix}_{대분류번호}_{중분류번호}_{SN}`
   - 추론 불가 시 파일명 기반으로 임시 ID 부여 후 사용자 확인

4. **프로그램ID 생성**:
   - `PG_{화면ID}` 형식

### Step 3: 패키지 → 업무 영역 매핑 [필수 중단점]

패키지 구조에서 추론한 업무 영역 분류를 사용자에게 확인받는다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
소스코드에서 다음 업무 영역을 식별했습니다:

| 패키지 | 추론된 업무 영역 | Controller 수 |
|--------|----------------|--------------|
| system.authority | 시스템관리 > 권한관리 | 1 |
| system.user | 시스템관리 > 사용자관리 | 1 |
| education.course | 교육관리 > 과정관리 | 3 |
| ... | ... | ... |

업무 영역 분류가 맞나요?

✅ 승인 — "승인" 또는 "OK"
✏️ 수정 — 변경 내용 입력

  수정 예시:
  • "system.authority는 '공통관리 > 권한'으로 변경"
  • "education 하위는 전부 '교육훈련' 대분류로"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 4: DE-05 프로그램정의서 생성

승인된 업무 영역 분류를 기반으로 DE-05 양식의 표를 생성한다:

| NO | 업무명 | 대분류 | 중분류 | 소분류 | ID | 프로그램명 | 메뉴_URL | Package | Controller | VO | DAO | Service | Impl | Sql | JSP | 요구사항ID | 화면설계서ID |
|----|--------|--------|--------|--------|-----|-----------|---------|---------|------------|-----|------|---------|------|------|------|-----------|------------|

**규칙**:
- NO는 1부터 순번
- ID는 `PG_{화면ID}` 형식
- 프로그램명은 Controller 클래스명에서 추론 (예: AuthorityController → 권한관리)
- Package는 실제 패키지 경로
- Controller/VO/DAO/Service/Impl/Sql/JSP는 실제 파일명
- 요구사항ID/화면설계서ID는 빈 값 (추적매트릭스에서 매핑)

### Step 5: 화면 없는 프로그램 탐지

JSP/HTML이 매핑되지 않는 Controller를 별도로 표시:
- 배치 프로그램
- API 전용 엔드포인트
- 스케줄러
- 유틸리티 서비스

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
화면이 없는 프로그램 {N}건이 발견되었습니다:

| 프로그램명 | 유형 | URL | 비고 |
|-----------|------|-----|------|
| BatchJobController | 배치 | /batch/run | 화면 없음 |
| ApiAuthController | API | /api/auth | REST API |

이 프로그램들도 프로그램정의서에 포함할까요?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 출력

DE-05 양식의 마크다운 표. 이후 승인 루프를 거쳐 파일로 저장된다.

---

## 주의사항

1. **Level 3 스캔은 필요한 파일만**: 패키지 구조만으로 판단이 안 되는 경우에만 해당 파일 전체 읽기
2. **동일 기능의 여러 화면은 Controller/Service/DAO/SQL 공유, JSP만 개별**: generate-program-list 스킬의 규칙을 동일 적용
3. **테스트 코드(test/)는 제외**: src/test 디렉토리는 스캔 대상에서 제외
4. **화면ID 역추론이 불확실하면 사용자에게 확인**: 자동 추론 결과를 맹신하지 않음
5. **기존 프로그램정의서가 있으면 diff 표시**: 소스에만 있는 항목, 산출물에만 있는 항목을 구분하여 표시
