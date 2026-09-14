# Claude·Codex 공동 유지보수 설계

## 문제

4.2.0에서 Codex가 gx-pm을 실행할 수 있게 됐지만, 이후 작업자가 Claude에서만 스킬이나 커맨드를 고치면 Codex 진입 스킬의 연결표, 질문 도구 변환, 설치 문서가 낡을 수 있다. 반대로 Codex만 보고 업무 규칙을 복제하면 Claude와 Codex의 산출물 결과가 갈라진다.

## 구조

업무 규칙의 정본은 기존 `plugins/gx-pm/commands/`, `skills/`, `templates/`에 둔다. `skills/gx-pm-workflow/SKILL.md`는 Codex 진입·도구 변환만 맡는다. 저장소 유지보수 절차는 `docs/development/dual-harness-maintenance.md` 한 곳에 둔다. 루트 `AGENTS.md`와 `CLAUDE.md`는 그 문서를 읽도록 짧게 안내한다. 설치된 플러그인에 포함되는 `plugins/gx-pm/CLAUDE.md`는 실행 규칙을 유지한다.

## 변경 계약

새 스킬·커맨드는 두 환경의 진입점, 플러그인 루트 기준 경로, 사용자 입력·승인 중단점, 외부 MCP 선행조건을 점검한다. Claude 전용 도구의 인자 형식을 공통 업무 규칙으로 확대하지 않는다. Codex는 현재 세션에서 제공되는 도구를 사용하고, 도구가 없으면 실제 사용자 응답을 기다린다. 공통 산출물 규칙은 중복하지 않는다.

변경 후에는 전체 Python 테스트, Codex 플러그인 검사기, 마켓플레이스 등록·설치 캐시 확인을 수행한다. 매니페스트와 README·CHANGELOG의 버전/개수 표기는 릴리스 시 함께 갱신한다. 외부 `sqi-comn-term` MCP가 필요한 실제 산출물 생성은 입력 자료와 서버가 준비된 환경에서 별도 확인한다.
