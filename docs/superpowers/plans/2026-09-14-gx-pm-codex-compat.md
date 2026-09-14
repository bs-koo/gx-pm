# gx-pm Codex Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codex에서 gx-pm을 설치하고 기존 7개 워크플로를 스킬로 실행할 수 있게 한다.

**Architecture:** 플러그인 루트의 Codex 매니페스트와 저장소 루트 로컬 마켓플레이스가 기존 플러그인을 등록한다. 새 `gx-pm-workflow` 스킬은 기존 커맨드 문서를 읽는 어댑터이고, 질문 도구 차이만 처리한다.

**Tech Stack:** Codex CLI 0.154.0, JSON, Markdown SKILL.md, Python unittest

**Spec:** `docs/superpowers/specs/2026-09-14-gx-pm-codex-compat-design.md`

## Global Constraints

- 기존 Claude 커맨드 7개, 스킬 17개의 비즈니스 규칙 및 템플릿 정본을 복제하지 않는다.
- 원본의 필수 중단점과 `sqi-comn-term` MCP 하드 선행조건을 유지한다.
- Codex 매니페스트에서 지원하지 않는 `commands` 필드를 사용하지 않는다.

---

### Task 1: Codex 등록 계약

**Files:** Create `plugins/gx-pm/.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`; test `plugins/gx-pm/tests/test_codex_compat.py`.

**Interfaces:** 마켓플레이스 소스 `./plugins/gx-pm`; 플러그인 이름 `gx-pm`; 스킬 경로 `./skills/`.

- [ ] **Step 1: 실패 테스트 작성.** JSON을 읽어 두 매니페스트의 이름, 경로, 정책, 버전이 Claude 매니페스트와 일치하며 Codex 매니페스트에 `commands`가 없음을 검사한다.
- [ ] **Step 2: 실패 확인.** `python -m unittest discover -s plugins/gx-pm/tests -p test_codex_compat.py -v` 실행, 매니페스트 부재로 FAIL.
- [ ] **Step 3: 최소 구현.** `plugin.json`에 `name`, `version`, `description`, `author`, `skills`, `interface`를 쓰고 마켓플레이스에 `source.source=local`, `source.path=./plugins/gx-pm`, `policy.installation=AVAILABLE`, `policy.authentication=ON_INSTALL`을 쓴다.
- [ ] **Step 4: 통과 확인.** 같은 테스트와 `python C:/Users/SQI/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/gx-pm` 실행.

### Task 2: Codex 워크플로 어댑터

**Files:** Create `plugins/gx-pm/skills/gx-pm-workflow/SKILL.md`; modify `plugins/gx-pm/tests/test_plugin_consistency.py`; test `plugins/gx-pm/tests/test_codex_compat.py`.

**Interfaces:** `$gx-pm-workflow`가 명세일괄·프로젝트설정 및 산출물 5종을 `commands/gx-*.md`에 매핑한다. 모든 상대 경로는 스킬의 두 단계 상위인 플러그인 루트 기준이다.

- [ ] **Step 1: 실패 테스트 작성.** 7개 커맨드 참조, `AskUserQuestion` 변환 규칙, 응답 대기, 템플릿 루트 규칙을 검사한다.
- [ ] **Step 2: 실패 확인.** `python -m unittest discover -s plugins/gx-pm/tests -p test_codex_compat.py -v` 실행, 어댑터 부재로 FAIL.
- [ ] **Step 3: 최소 구현.** 프론트매터 `name: gx-pm-workflow`를 가진 스킬에 매핑 표, 원본 읽기 순서, 질문 도구 적응, 승인 게이트, 외부 MCP 선행조건을 기술한다. 기존 전수 스킬 테스트에는 이 Codex 진입 스킬만 별도 진입점으로 취급한다.
- [ ] **Step 4: 통과 확인.** 신규 테스트와 기존 테스트 전체 실행.

### Task 3: 설치 안내와 실제 등록

**Files:** Modify `README.md`; test `plugins/gx-pm/tests/test_codex_compat.py`.

**Interfaces:** 설치 명령 `codex plugin marketplace add <repo-root>`와 `codex plugin add gx-pm@gx-pm`; 시작 방법 `$gx-pm-workflow`.

- [ ] **Step 1: 실패 테스트 작성.** README에 두 설치 명령, 시작 스킬, 외부 MCP 제한이 명시되었는지 검사한다.
- [ ] **Step 2: 실패 확인.** 신규 테스트 실행, 문서 조건으로 FAIL.
- [ ] **Step 3: 최소 구현.** Claude 설치 문단 옆에 Codex 설치·사용·제약을 추가한다.
- [ ] **Step 4: 검증.** 전체 unittest, 플러그인 검사기, `codex plugin marketplace add`, `codex plugin add`, `codex plugin list --json`으로 등록과 캐시 구성 확인. 외부 설정 파일에 대한 권한이 필요하면 CLI 승인 요청으로 처리한다.

## Self-review

- Spec coverage: 등록, 실행 진입점, 질문 도구, 템플릿 경로, MCP 제한, 검증을 Task 1–3에 배치했다.
- Placeholder scan: 예시 명령의 `<repo-root>`는 사용자가 자기 경로로 바꾸는 설치 인자이며 미구현 표지가 아니다.
- Type consistency: 마켓플레이스 이름과 플러그인 이름은 모두 `gx-pm`이다.
