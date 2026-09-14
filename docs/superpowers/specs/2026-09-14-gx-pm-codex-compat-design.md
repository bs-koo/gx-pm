# gx-pm Codex 호환 설계

## 목표와 현황

gx-pm 4.1.0은 `plugins/gx-pm` 아래 Claude 커맨드 7개, 스킬 17개, 공통 템플릿 13개, xlsx 유틸리티와 테스트를 가진다. Claude 마켓플레이스는 저장소 루트 `.claude-plugin/marketplace.json`에서 플러그인 하위 폴더를 가리킨다. Codex 0.154.0은 플러그인 매니페스트 `.codex-plugin/plugin.json`과 마켓플레이스 `.agents/plugins/marketplace.json`을 사용하며, Claude의 `commands` 필드를 지원하지 않는다. 2026-09-01의 기존 호환 설계는 당시 커맨드 16개 기준이므로 현재 표면에 그대로 적용할 수 없다.

## 선택한 구조

Codex 매니페스트는 기존 `skills/`를 노출하고, `gx-pm-workflow` 진입 스킬 하나를 추가한다. 이 스킬은 요청을 현재 7개 커맨드 중 하나에 매핑하고 해당 `commands/*.md`를 플러그인 루트 기준으로 읽는다. 실행 규칙은 원본 커맨드·스킬·템플릿에 남겨 중복을 피한다. 사용자는 Codex에서 `$gx-pm-workflow` 또는 자연어로 작업을 시작한다. Claude의 `/gx-*`와 동일한 슬래시 커맨드 자동완성은 Codex 플러그인 계약에 포함되지 않는다.

마켓플레이스는 저장소의 `.agents/plugins/marketplace.json`에 `gx-pm` 로컬 소스를 등록한다. 이 경로는 사용자가 저장소를 다른 PC에 복제해도 유지된다. 로컬 설치는 `codex plugin marketplace add <repo-root>` 다음 `codex plugin add gx-pm@gx-pm`이다.

## 런타임 호환 규칙

원본의 `AskUserQuestion`은 Claude 전용이다. Codex 진입 스킬은 각 필수 중단점에서 현재 세션의 사용자 입력 도구를 사용하고, 도구가 없으면 대화로 질문한 뒤 실제 응답을 기다린다. 도구 인자 형식을 Claude 형식으로 강제하지 않는다. 응답 없이 승인을 추정하거나 다음 단계로 넘어가지 않는다. `templates/`와 `commands/` 경로는 설치된 플러그인 루트에 상대적으로 해석한다.

`sqi-comn-term` MCP는 외부 선행조건이다. 이 저장소에 서버 구현이나 연결 정보가 없으므로 자동으로 등록하지 않는다. 테이블정의서와 명세일괄은 기존 하드 선행조건을 지켜 연결이 없으면 안내 후 중단한다. xlsx 유틸리티는 기존 Python 의존성을 유지한다.

## 검증

Codex 매니페스트 검사기, 기존 Python 테스트, 새 연결 계약 테스트를 통과시킨다. 로컬 Codex CLI에서 마켓플레이스와 플러그인이 목록에 보이는지 확인하고, 설치된 캐시에 커맨드·템플릿·스킬·유틸리티가 포함되는지 확인한다. 실제 프로젝트 산출물 생성은 RFP, 프로젝트 선택, 외부 MCP가 필요한 별도 통합 테스트다.
