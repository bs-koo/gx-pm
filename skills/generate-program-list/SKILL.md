---
name: generate-program-list
description: 화면목록표를 기반으로 DE-05 프로그램정의서를 생성합니다. 소스파일 구조를 자동 매핑합니다.
---

# 프로그램정의서 생성 (generate-program-list)

화면목록표(DE-03)의 화면 목록을 기반으로 프로그램ID를 부여하고, 소스파일 구조(Controller/Service/DAO/SQL/JSP)를 매핑하여 DE-05 프로그램정의서를 생성한다.
본 스킬은 ID 체인의 **화면ID → 프로그램ID** 단계를 처리한다.

---

## 입력

| 항목 | 필수 여부 | 설명 |
|---|---|---|
| 화면목록표 데이터 | 필수 | DE-03 기준. 기능구분ID, 기능ID, 화면ID, 화면명 포함 |
| 프레임워크 유형 | 필수 | eGovFrame / Spring Boot / 기타 |
| 베이스 패키지명 | 권장 | 예: `kr.go.mois.ehr`, `com.example.cms` |
| 기존 소스 구조 | 선택 | 있으면 기존 패키지/파일명 패턴 참고 |
| 요구사항ID | 선택 | 화면과 요구사항의 연결 매핑 정보 |

---

## 처리 절차

### Step 1: 프로그램ID 매핑

화면ID로부터 프로그램ID를 생성한다.

부여 규칙:
- 패턴: `PG_{화면ID}` (예: `PG_EHR_01_01_010`)
- 모든 프로그램ID에 반드시 `PG_` 접두어를 사용한다 (id-trace 자동 판별과의 정합성 보장)

프로그램명 생성 규칙:
- `{화면명}` 그대로 사용 (예: "운영자 권한 관리 목록")

---

### Step 2: 업무명 / 대분류 / 중분류 / 소분류 도출

화면목록표의 기능구분ID, 기능ID를 기반으로 계층 구조를 추출한다.

| 컬럼 | 매핑 기준 | 예시 |
|---|---|---|
| 업무명 | 기능구분명 | 시스템관리 |
| 대분류 | 기능구분명 | 시스템관리 |
| 중분류 | 기능명 | 운영자 권한 관리 |
| 소분류 | 화면명 유형 접미어 | 목록 / 등록 / 상세 |

---

### Step 3: URL 패턴 생성

프레임워크별 URL 패턴 생성 규칙:

**eGovFrame (관리자 화면)**
```
/mngr/{기능구분소문자}/{기능소문자}/{화면유형}.do
예: /mngr/system/authority/list.do
    /mngr/system/authority/regist.do
    /mngr/system/authority/detail.do
```

**eGovFrame (사용자/외부 화면)**
```
/user/{기능구분소문자}/{기능소문자}/{화면유형}.do
예: /user/board/notice/list.do
    /user/board/notice/view.do
```

**Spring Boot REST API**
```
GET    /api/{기능구분소문자}/{기능소문자}       → 목록 조회
POST   /api/{기능구분소문자}/{기능소문자}       → 등록
GET    /api/{기능구분소문자}/{기능소문자}/{id}  → 상세 조회
PUT    /api/{기능구분소문자}/{기능소문자}/{id}  → 수정
DELETE /api/{기능구분소문자}/{기능소문자}/{id}  → 삭제
예: GET /api/system/authority
    POST /api/system/authority
```

URL 생성 시 기능명은 camelCase → kebab-case 변환 적용 (예: userAuth → user-auth).

---

### Step 4: Package(Source) 생성

Package는 소스파일이 속할 Java 패키지 경로를 나타낸다.

생성 규칙:
- 패턴: `{베이스패키지}.{기능구분소문자}.{기능소문자}`
- 예: `kr.go.mois.ehr.system.authority`

DE-05 표의 Package 컬럼 값은 기능구분ID를 소문자로 변환한 약칭으로 표기하는 경우도 있다:
- 예: `PG_EHR_01` → Package = `system`

---

### Step 5: 소스파일 구조 매핑

#### eGovFrame 기준 (표준)

| 컬럼 | 파일명 패턴 | 예시 |
|---|---|---|
| Controller | `{기능명PascalCase}Controller.java` | `AuthorityController.java` |
| VO | `{기능명PascalCase}VO.java` | `AuthorityVO.java` |
| DAO | `{기능명PascalCase}DAO.java` | `AuthorityDAO.java` |
| Service | `{기능명PascalCase}Service.java` | `AuthorityService.java` |
| Impl | `{기능명PascalCase}ServiceImpl.java` | `AuthorityServiceImpl.java` |
| Sql (MyBatis) | `{Package명PascalCase}.xml` | `Authority.xml` |
| JSP | `/{망구분}/{기능구분}/{기능}/{화면유형}.jsp` | `/mngr/system/authority/list.jsp` |

> 주의: VO/DAO/Service/Impl/SQL은 동일 기능의 여러 화면이 **공유**한다. 목록/등록/상세 화면이 동일한 Controller 파일을 참조하는 경우, 해당 컬럼에 동일 파일명을 기재한다.

#### Spring Boot 기준 (대안)

| 컬럼 | 파일명 패턴 | 예시 |
|---|---|---|
| Controller | `{기능명PascalCase}Controller.java` | `AuthorityController.java` |
| VO | `{기능명PascalCase}RequestDto.java` / `ResponseDto.java` | `AuthorityRequestDto.java` |
| DAO | `{기능명PascalCase}Repository.java` | `AuthorityRepository.java` |
| Service | `{기능명PascalCase}Service.java` | `AuthorityService.java` |
| Impl | `{기능명PascalCase}ServiceImpl.java` | `AuthorityServiceImpl.java` |
| Sql | `{기능명PascalCase}Mapper.xml` (MyBatis) 또는 JPA 사용 시 N/A | `AuthorityMapper.xml` |
| JSP | React/Vue 사용 시 N/A, Thymeleaf: `/{경로}/{화면유형}.html` | `/authority/list.html` |

---

### Step 6: 요구사항ID / 화면설계서ID 연결

- 요구사항ID: 해당 화면이 충족하는 요구사항ID 기재 (예: `B-RE-001`)
- 화면설계서ID: 화면설계서가 존재하는 경우 화면ID를 그대로 참조 (예: `EHR_01_01_010`)
- 정보가 없는 경우 공란 처리

---

## 체크포인트 (사용자 확인 필수)

프로그램정의서 초안 생성 후 아래 문구로 확인을 요청한다:

> "프로그램 구조가 맞는지 확인해주세요.
> - 프레임워크 및 패키지 구조가 실제 프로젝트와 일치하는지
> - URL 패턴이 프로젝트 URL 규칙과 맞는지
> - 소스파일명(Controller/Service 등) 명명 규칙이 맞는지
> - 동일 소스를 공유하는 화면이 올바르게 묶여 있는지
> 수정이 필요한 항목을 알려주시면 반영하겠습니다."

---

## 출력: DE-05 프로그램정의서

### 출력 형식 (마크다운 표)

| NO | 업무명 | 대분류 | 중분류 | 소분류 | ID | 프로그램명 | 메뉴_URL | Package | Controller | VO | DAO | Service | Impl | Sql | JSP | 요구사항ID | 화면설계서ID |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 시스템관리 | 시스템관리 | 운영자 권한 관리 | 목록 | PG_EHR_01_01_010 | 운영자 권한 관리 목록 | /mngr/system/authority/list.do | PG_EHR_01 | AuthorityController.java | AuthorityVO.java | AuthorityDAO.java | AuthorityService.java | AuthorityServiceImpl.java | Authority.xml | /mngr/system/authority/list.jsp | B-RE-001 | EHR_01_01_010 |
| 2 | 시스템관리 | 시스템관리 | 운영자 권한 관리 | 등록 | PG_EHR_01_01_020 | 운영자 권한 등록 | /mngr/system/authority/regist.do | PG_EHR_01 | AuthorityController.java | AuthorityVO.java | AuthorityDAO.java | AuthorityService.java | AuthorityServiceImpl.java | Authority.xml | /mngr/system/authority/regist.jsp | B-RE-001 | EHR_01_01_020 |
| 3 | 시스템관리 | 시스템관리 | 운영자 권한 관리 | 상세 | PG_EHR_01_01_030 | 운영자 권한 상세 | /mngr/system/authority/detail.do | PG_EHR_01 | AuthorityController.java | AuthorityVO.java | AuthorityDAO.java | AuthorityService.java | AuthorityServiceImpl.java | Authority.xml | /mngr/system/authority/detail.jsp | B-RE-001 | EHR_01_01_030 |

---

## 주의사항 / 규칙

1. **소스파일 공유**: 동일 기능(기능ID)의 여러 화면은 Controller, VO, DAO, Service, Impl, SQL 파일을 공유한다. 각 행에 동일한 파일명을 반복 기재한다.
2. **JSP는 화면별 개별**: JSP 파일만 화면마다 별도 파일명을 갖는다.
3. **NO 채번**: 전체 프로그램정의서에서 1번부터 순차 채번. 기존 목록이 있으면 마지막 번호 이어서 채번.
4. **화면ID → 프로그램ID 고유성**: 프로그램ID는 화면ID와 1:1 대응이므로 중복 불가.
5. **후속 ID 체인**: 프로그램ID는 단위테스트ID(`U_{화면ID}`) 생성의 기준이 되므로 화면ID를 정확히 반영해야 한다.
6. **eGovFrame URL .do 확장자**: 표준 eGovFrame 프로젝트는 `.do` 확장자를 사용한다. 프로젝트 설정에 따라 `.action`, `/` 방식으로 변경 가능.
7. **Spring Boot REST 전환 시**: JSP 컬럼을 `View` 또는 `Template`으로 대체하고, Sql 컬럼은 JPA 사용 시 `N/A`로 표기한다.
