# DE-05 프로그램정의서 양식

## 파일 형식
Excel (.xlsx)

## 시트 구성
1. **표지**
2. **개정이력**
3. **프로그램정의서** — 본문

## 본문 컬럼 구조

| 컬럼 | 설명 | 예시 |
|------|------|------|
| NO | 순번 | 1 |
| 업무명 | 업무 분류 | 국내외열사용기자재검사시스템 |
| 대분류 | 기능 대분류 | 열사용기자재 시스템 |
| 중분류 | 기능 중분류 | 시스템 관리 |
| 소분류 | 기능 소분류 | 운영자 권한 관리 |
| ID | 프로그램 ID (PG_{화면ID}) | PG_EHR_01_01_010 |
| 프로그램명 | 프로그램/화면 이름 | 운영자 권한 관리 |
| 메뉴_URL | 접근 URL | /mngr/sys/user/userMngtList.do |
| Package (Source) | 소스 패키지 | PG_MNGT_SYS |
| Controller | Controller 파일 | UserMngtController.java |
| VO | VO 파일 | (해당 시) |
| DAO | DAO 파일 | PG_MNGT_SYSDAO.java |
| Service | Service 파일 | UserMngtService.java |
| Impl | ServiceImpl 파일 | UserMngtServiceImpl.java |
| Sql | SQL 매퍼 파일 | PG_MNGT_SYS.xml |
| JSP | JSP 파일 경로 | /ehrd/mngr/sys/user/userMngtList.jsp |
| 요구사항 ID | 매핑되는 요구사항 | B-RE-001 |
| 화면설계서 ID | 매핑되는 화면정의서 | EHR_01_01_010 |

## 작성 규칙

- 프로그램 ID는 `PG_{화면ID}` 형식으로 부여 (예: PG_EHR_01_01_010)
- 하나의 화면에 여러 소스 파일이 매핑될 수 있음 (줄바꿈 구분)
- Java 기반 프로젝트 기준: Controller/VO/DAO/Service/Impl/SQL/JSP 구조
- 프레임워크에 따라 컬럼 구성이 달라질 수 있음 (Spring Boot, eGovFrame 등)
