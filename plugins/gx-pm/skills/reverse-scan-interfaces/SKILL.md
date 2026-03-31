---
name: reverse-scan-interfaces
description: 소스코드에서 외부 시스템 연동 코드를 탐지하여 인터페이스정의서를 역생성합니다.
---

# 소스코드 역스캔 → 인터페이스정의서 (reverse-scan-interfaces)

소스코드의 HTTP 클라이언트 호출, 외부 연동 설정 등을 스캔하여
실제 구현된 인터페이스 목록을 역생성한다.

---

## 입력

| 항목 | 필수 | 설명 |
|------|------|------|
| sourcePath | Y | 소스코드 경로 (profile.json) |
| systemCode | Y | 시스템 코드 (profile.json) |
| source-index.json | 권장 | scan-source-index 결과 |

---

## 처리 절차

### Step 1: 외부 호출 코드 탐지

소스코드에서 외부 시스템 호출 패턴을 Grep으로 탐지한다:

#### 1-1. HTTP 클라이언트 호출

```
Grep 패턴 (Java):
  - RestTemplate
  - WebClient
  - HttpClient
  - OkHttpClient
  - CloseableHttpClient
  - HttpURLConnection
  - URL\(.*http

Grep 패턴 (JavaScript/TypeScript):
  - axios\.(get|post|put|delete|patch)
  - fetch\(
  - HttpClient
  - request\(
```

#### 1-2. 외부 연동 어노테이션/설정

```
Grep 패턴:
  - @FeignClient
  - @WebService
  - @WebServiceClient
  - WebServiceTemplate
  - SoapClient
```

#### 1-3. 파일 전송

```
Grep 패턴:
  - FTPClient
  - SFTPClient
  - JSch
  - ChannelSftp
  - FileTransfer
```

#### 1-4. 외부 URL 설정

```
설정 파일 스캔 (application.yml, application.properties):
  - http:// 또는 https://로 시작하는 값
  - api.url, external.url, endpoint 등의 키
  - 자체 도메인(localhost, 127.0.0.1) 제외
```

### Step 2: 연동 지점 상세 분석

탐지된 각 연동 지점에 대해 해당 파일의 관련 부분만 Read (Level 3 스캔):

- **URL/엔드포인트**: 실제 호출 URL 추출
- **HTTP 메서드**: GET/POST/PUT/DELETE
- **헤더/인증**: Authorization, API Key, Bearer Token 패턴
- **요청 데이터**: 요청 DTO/Map 구조 추출
- **응답 데이터**: 응답 DTO/Map 구조 추출
- **타임아웃**: 설정된 timeout 값
- **오류 처리**: try-catch, fallback 패턴

### Step 3: 인터페이스 그룹핑

탐지된 연동 지점을 외부 시스템별로 그룹핑한다:

- URL 도메인이 같으면 같은 외부 시스템으로 판단
- 설정 파일의 키 그룹핑 (예: `naver.api.*` → 네이버 API)
- FeignClient의 name 속성으로 그룹핑

### Step 4: 탐지 결과 확인 [필수 중단점]

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
소스코드에서 외부 연동 {N}건을 탐지했습니다:

| # | 연동 대상 (추정) | 연동 방식 | 호출 위치 | URL/엔드포인트 |
|---|----------------|----------|----------|--------------|
| 1 | 공공데이터포털 | REST API | DataPortalService.java | data.go.kr/api/... |
| 2 | SSO 인증서버 | REST API | SsoAuthClient.java | sso.internal/auth |
| 3 | 문자발송시스템 | REST API | SmsService.java | sms.example.com/send |

이 연동 목록이 맞나요?

✅ 승인 — "승인" 또는 "OK"
✏️ 수정 — 변경 내용 입력

  수정 예시:
  • "1번 연동 대상을 '행정안전부 공공데이터'로 수정"
  • "4번에 SFTP 파일 전송 추가 (FtpUploader.java)"
  • "2번은 내부 시스템이라 제외"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 5: 인터페이스정의서 생성

승인된 연동 목록을 기반으로 인터페이스정의서를 생성한다:

#### 인터페이스 목록 표

| 인터페이스ID | 인터페이스명 | 송신시스템 | 수신시스템 | 연동방식 | 연동주기 | 관련 요구사항ID |
|------------|------------|----------|----------|---------|---------|--------------|

#### 인터페이스 상세 (건별)

각 인터페이스에 대해:

| 항목 | 내용 |
|------|------|
| 인터페이스ID | IF-{시스템코드}-{순번} |
| 인터페이스명 | {연동 기능명} |
| 송신시스템 | {시스템명} |
| 수신시스템 | {외부시스템명} |
| 연동방식 | REST API / SOAP / 파일 / DB Link |
| HTTP 메서드 | GET / POST / PUT / DELETE |
| URL | {엔드포인트 URL} |
| 요청 파라미터 | {파라미터 목록} |
| 응답 데이터 | {응답 필드 목록} |
| 인증방식 | API Key / Bearer Token / Basic Auth / 없음 |
| 타임아웃 | {N}초 |
| 연동주기 | 실시간 / 배치({N}분) / 이벤트 기반 |
| 오류처리 | {오류 처리 방식} |

---

## 출력

인터페이스 목록 + 상세 정의 마크다운 표.
이후 승인 루프를 거쳐 파일로 저장된다.

---

## 주의사항

1. **내부 API 호출은 제외한다**: 같은 시스템 내 Controller 간 호출, 내부 서비스 도메인(예: `.svc.cluster.local`, 사설 IP 대역 `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), localhost 호출은 외부 연동이 아님
2. **민감정보(API 키, 비밀번호)는 마스킹한다**: 실제 값 대신 `{API_KEY}` 등으로 표시
3. **테스트 코드(test/)는 제외한다**
4. **라이브러리 내부 호출은 제외한다**: node_modules, lib 하위의 HTTP 호출은 무시
5. **연동 대상 시스템명은 추정값이므로 반드시 사용자 확인**: URL 도메인만으로는 정확한 시스템명을 알 수 없음
6. **설정 파일의 프로필별 URL 차이를 안내**: dev/staging/prod 환경별 URL이 다를 수 있음
