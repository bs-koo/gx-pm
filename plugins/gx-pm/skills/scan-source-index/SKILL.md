---
name: scan-source-index
description: 소스코드를 3단계로 점진 스캔하여 source-index.json에 캐싱합니다. 토큰을 최소화하면서 프로젝트 구조를 파악합니다.
---

# 소스코드 스캔 인덱서 (scan-source-index)

소스코드 프로젝트를 점진적으로 스캔하여 구조를 파악한다.
풀스캔 대신 3단계 점진 스캔으로 토큰 사용을 최소화한다.

---

## 입력

| 항목 | 필수 | 설명 |
|------|------|------|
| sourcePath | Y | 소스코드 로컬 경로 (profile.json에서 로드) |
| framework | Y | 프레임워크 유형 (profile.json에서 로드) |

---

## 처리 절차

### Step 1: 캐시 확인

프로젝트 폴더에 `source-index.json`이 이미 있는지 확인한다.

- 있고 24시간 이내 → "기존 스캔 결과를 사용합니다." 안내 후 캐시 반환
- 있고 24시간 초과 → "스캔 결과가 오래되었습니다. 다시 스캔할까요?" 질문
- 없음 → Step 2로 진행

---

### Step 2: Level 1 스캔 — 디렉토리 트리 (~2,000 토큰)

**항상 실행**. sourcePath 하위의 파일 목록을 트리 형태로 추출한다.

```bash
# 실행할 명령
ls -R {sourcePath}/src 또는 tree 명령
```

**추출 정보**:
- 전체 파일 수 (확장자별: .java, .jsp, .html, .xml, .sql, .properties, .yml)
- 패키지 구조 (디렉토리 트리)
- 주요 디렉토리 식별:
  - `src/main/java` → Java 소스
  - `src/main/webapp` 또는 `src/main/resources/templates` → 화면 파일
  - `src/main/resources/mapper` 또는 `**/sqlmap` → MyBatis SQL
  - `src/main/resources` → 설정 파일

**프레임워크 자동 감지** (profile과 교차 확인):
- `pom.xml`에 `egovframework` → eGovFrame
- `pom.xml`에 `spring-boot` → Spring Boot
- `build.gradle` 존재 → Gradle 프로젝트

---

### Step 3: Level 2 스캔 — 핵심 파일 헤더 (~15,000 토큰)

**AskUserQuestion 도구**로 "상세 스캔을 진행할까요?" 확인 후 실행한다.

**대규모 프로젝트 안전장치**: Level 1에서 파악한 Java 파일 수가 300개를 초과하면, 전체 스캔 대신 업무 영역(패키지)별로 순차 스캔한다. 각 영역 스캔 전 사용자에게 "다음 영역을 스캔할까요?"를 확인받는다. 또한 각 유형(Controller, Service 등)별 스캔 대상 파일 수가 100개를 초과하면, 상위 100개만 스캔하고 나머지는 Level 3에서 필요 시 읽도록 한다.

#### 3-1. Controller 파일 스캔

```
Glob 패턴:
  - **/controller/**/*.java
  - **/web/**/*.java
  - **/*Controller.java

각 파일에서 상위 50줄만 Read:
  - @Controller, @RestController 어노테이션
  - @RequestMapping("...") → URL 패턴 추출
  - 클래스명 추출
```

#### 3-2. Service 파일 스캔

```
Glob 패턴:
  - **/service/**/*.java
  - **/*Service.java, **/*ServiceImpl.java

각 파일에서 상위 30줄만 Read:
  - @Service 어노테이션
  - 클래스명 추출
```

#### 3-3. DAO/Repository 파일 스캔

```
Glob 패턴:
  - **/dao/**/*.java, **/repository/**/*.java
  - **/*DAO.java, **/*Dao.java, **/*Repository.java, **/*Mapper.java

각 파일에서 상위 30줄만 Read:
  - @Repository, @Mapper 어노테이션
  - 클래스명 추출
```

#### 3-4. Entity/VO 파일 스캔

```
Glob 패턴:
  - **/entity/**/*.java, **/domain/**/*.java
  - **/vo/**/*.java, **/dto/**/*.java
  - **/*VO.java, **/*DTO.java, **/*Entity.java

각 파일에서:
  - @Entity, @Table(name="...") → 테이블 매핑
  - 클래스명, 필드 목록 (상위 100줄)
```

#### 3-5. 화면 파일 스캔 (파일명만)

```
Glob 패턴:
  - **/*.jsp
  - **/templates/**/*.html
  - **/static/**/*.html

파일명만 수집 (내용 읽지 않음)
```

#### 3-6. MyBatis Mapper XML 스캔

```
Glob 패턴:
  - **/mapper/**/*.xml, **/sqlmap/**/*.xml

각 파일에서 Grep:
  - <mapper namespace="..."> → namespace 추출
  - <select id="...">, <insert id="...">, <update id="...">, <delete id="..."> → SQL ID 목록
```

#### 3-7. 설정 파일 스캔

```
파일:
  - application.yml / application.properties
  - application-*.yml (프로필별)

주요 설정값 추출:
  - server.port, server.servlet.context-path
  - spring.datasource.url (URL만, 비밀번호 제외)
  - 외부 연동 URL 설정
```

---

### Step 4: Level 3 스캔 — 상세 읽기 (필요 시)

Level 1~2로 판단이 안 되는 특정 파일만 전체 읽기.
이 단계는 자동 실행하지 않고, 사용자가 특정 파일의 구현을 확인해 달라고 할 때만 요청한다.

---

### Step 5: 인덱스 저장

스캔 결과를 `source-index.json`으로 저장한다:

```json
{
  "scannedAt": "2026-03-31T10:00:00",
  "sourcePath": "D:\\projects\\ehr-system",
  "framework": "egovframe",
  "stats": {
    "javaFiles": 143,
    "jspFiles": 52,
    "xmlMappers": 38,
    "configFiles": 5,
    "packages": 28
  },
  "packages": [
    "kr.go.energy.ehr.system.authority",
    "kr.go.energy.ehr.system.user",
    "kr.go.energy.ehr.education.course"
  ],
  "controllers": [
    {
      "file": "src/main/java/kr/go/energy/ehr/system/authority/web/AuthorityController.java",
      "class": "AuthorityController",
      "annotations": ["@Controller"],
      "urls": ["/system/authority/list.do", "/system/authority/save.do"],
      "methods": ["selectList", "save", "delete"]
    }
  ],
  "services": [
    {
      "file": "src/main/java/kr/go/energy/ehr/system/authority/service/AuthorityService.java",
      "class": "AuthorityService"
    }
  ],
  "daos": [
    {
      "file": "src/main/java/kr/go/energy/ehr/system/authority/dao/AuthorityDAO.java",
      "class": "AuthorityDAO"
    }
  ],
  "entities": [
    {
      "file": "src/main/java/kr/go/energy/ehr/system/authority/vo/AuthorityVO.java",
      "class": "AuthorityVO",
      "tableName": null
    }
  ],
  "views": [
    "src/main/webapp/WEB-INF/jsp/system/authority/authorityList.jsp",
    "src/main/webapp/WEB-INF/jsp/system/authority/authorityForm.jsp"
  ],
  "mappers": [
    {
      "file": "src/main/resources/mapper/system/authority/AuthorityMapper.xml",
      "namespace": "kr.go.energy.ehr.system.authority.dao.AuthorityDAO",
      "sqlIds": ["selectList", "selectOne", "insert", "update", "delete"]
    }
  ],
  "config": {
    "contextPath": "/ehr",
    "port": 8080,
    "externalUrls": []
  }
}
```

---

## 토큰 사용량 예상

| 레벨 | 파일 500개 프로젝트 기준 | 설명 |
|------|----------------------|------|
| Level 1 (트리) | ~2,000 토큰 | 파일명만 |
| Level 2 (헤더) | ~15,000 토큰 | 핵심 파일 상위 30~50줄만 |
| Level 3 (상세) | 파일당 ~500 토큰 | 필요한 파일만 |
| **합계 (L1+L2)** | **~17,000 토큰** | 풀스캔 대비 0.85% |

---

## 주의사항

1. **비밀번호, 키, 시크릿 등 민감정보는 수집하지 않는다**:
   - `AWS_ACCESS_KEY`, `JWT_SECRET`, `API_KEY` 등 일반적인 시크릿 패턴 탐지 및 제외
   - `password`, `secret`, `key`, `token`, `credential` 키를 가진 설정값은 수집 대상에서 제외
   - JDBC URL 및 쿼리 파라미터(user, password 등)에 포함된 인증정보 마스킹 (예: `user/****@host:1521/db`, `?user=admin&password=****`)
   - URL 파라미터에 `apiKey`, `token`, `secret` 등이 포함되면 마스킹
   - DB 비밀번호, API 키 등은 절대 source-index.json에 저장하지 않는다
2. **node_modules, target, build 등 빌드 산출물은 제외한다**
3. **.git 디렉토리는 제외한다**
4. **Level 2는 사용자 확인 후 실행한다**: 토큰 사용을 사용자가 인지하도록
5. **캐시를 적극 활용한다**: 같은 세션 내에서 재스캔하지 않음
