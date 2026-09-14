---
name: gx-pm-workflow
description: Use in Codex for gx-pm public-sector/SI project setup, the five-document specification pipeline, or a single requirements, function, table, unit-test, or traceability document. Also use for Korean requests such as 프로젝트 설정, 명세일괄, 요구사항정의서, 기능명세서, 테이블정의서, 단위테스트계획서, 추적매트릭스.
---

# gx-pm Codex 진입점

이 스킬은 기존 gx-pm 커맨드의 Codex 어댑터다. 업무 규칙은 복제하지 않는다.

1. 이 `SKILL.md`가 있는 폴더의 두 단계 상위가 **설치된 플러그인 루트**다. 먼저 그 루트를 찾는다. 이후 `commands/`, `skills/`, `templates/`, `utils/`, `docs/`의 모든 상대 경로를 그 루트에서 해석한다. 사용자의 작업 폴더에서 같은 이름의 파일을 찾지 않는다.
2. 사용자 의도에 맞는 아래 원본 커맨드를 한 개 읽고, 그 문서가 참조하는 스킬과 템플릿을 필요할 때 읽는다. 원본의 단계 순서, ID 규칙, 선행조건, 승인 게이트를 따른다.

| 요청 | 원본 커맨드 |
|---|---|
| 프로젝트 설정·변경 | `commands/gx-프로젝트설정.md` |
| 명세 5종 일괄 | `commands/gx-명세일괄.md` |
| 요구사항정의서 | `commands/gx-요구사항정의서.md` |
| 기능명세서 | `commands/gx-기능명세서.md` |
| 테이블정의서·DDL 역생성 | `commands/gx-테이블정의서.md` |
| 단위테스트계획서 | `commands/gx-단위테스트계획서.md` |
| 추적매트릭스 | `commands/gx-추적매트릭스.md` |

3. 원본의 `AskUserQuestion` 호출 지시는 **필수 사용자 입력 지점**으로 해석한다. Codex에서 `request_user_input_async` 같은 사용자 입력 도구가 제공되면 해당 도구의 실제 스키마로 질문한다. 제공되지 않으면 대화에 질문을 하나 제시하고 턴을 끝내 실제 응답을 기다린다. Claude용 `questions`/`multiSelect` 인자 형식을 Codex 도구에 그대로 전달하지 않는다. 사용자에게 보인 텍스트나 시간 경과를 승인으로 간주하지 않는다. 승인·수정·선택 응답을 받은 뒤에만 다음 단계로 간다.
4. `templates/approval-protocol.md`의 승인 횟수와 파이프라인 게이트를 유지한다. Codex의 시스템·개발자·사용자 지시가 도구 선택이나 승인 권한을 다르게 정하면 그 지시를 우선하되, 산출물 확정에 필요한 실제 사용자 응답은 생략하지 않는다.
5. 테이블정의서와 명세일괄은 `templates/prerequisites.md`에 따라 `sqi-comn-term` MCP가 하드 선행조건이다. 세션에 없으면 `docs/표준용어-mcp-연계.md`의 Codex CLI / 앱 설치 안내를 보여주고 해당 워크플로를 중단한다. 서버를 임의로 대체하거나 표준 용어를 추측하지 않는다.
6. xlsx 추출을 요청받으면 원본 커맨드와 `templates/approval-protocol.md`에 지정된 시점에 `utils/export-xlsx.py`를 사용한다. 명령 경로 역시 설치된 플러그인 루트 기준이다.
