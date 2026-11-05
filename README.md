<div align="center">

# GX PM

**요구사항부터 테스트까지, 바뀌어도 이어지는 프로젝트 문서.**

공공·SI 프로젝트의 명세 작성, 변경 관리와 요구사항 추적을 돕는 Claude Code·Codex 플러그인입니다.

[![Version](https://img.shields.io/badge/version-4.6.0-blue.svg)](plugins/gx-pm/CHANGELOG.md)
[![Skills](https://img.shields.io/badge/skills-20-green.svg)](#스킬-구성)
[![Commands](https://img.shields.io/badge/commands-9-orange.svg)](#커맨드)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

[동작 방식](#플러그인-동작) · [시작하기](#시작하기) · [커맨드](#커맨드) · [스킬](#스킬-구성) · [상세 가이드](USAGE.md)

</div>

## 플러그인 동작

```text
자료 확인 → 요구사항 검토 → 명세 작성 → 검토·전달
                 ↕
        AI 추천 · 사용자 판단
```

1. **자료를 읽습니다.** RFP·과업지시서·기존 문서에서 요구사항과 근거를 정리합니다.
2. **모호한 내용을 확인합니다.** 범위·권한·조건이 불분명하면 AI 추천·근거·대안을 제시하고 사용자의 판단을 받습니다.
3. **문서를 연결합니다.** 확정된 요구사항을 기능·데이터·테스트 명세로 구체화하고, 문서 사이의 연계와 누락을 검토합니다.
4. **검토한 결과를 전달합니다.** Markdown을 기준으로 관리하고 Excel로 제공합니다. 미결이 남은 문서는 최종본과 검토용 초안을 구분합니다.

**요구사항정의서만 먼저 작성해도 됩니다.** 명세일괄은 아래 명세 5종을 작성합니다. 이후 요구사항이 바뀌면 기존 ID와 유효한 응답을 유지하고, 영향받는 문서와 미반영 변경을 확인합니다.

계획서 작성 후 실제 시험을 요청하면 로컬 프로젝트의 API·필요한 화면을 조작하고, 관측 결과와 증적을 **단위테스트결과서(IM-03)**에 기록합니다.

<details>
<summary>받을 수 있는 문서</summary>

| 산출물 | 담는 내용 |
|---|---|
| 요구사항정의서 · AN-02 | 요구사항, 출처, 분류와 변경 근거 |
| 기능명세서 · AN-03 | 기능별 입력·처리·출력과 요구사항 연계 |
| 테이블정의서 · DE-08 | DDL 기반 스키마, 제약과 표준 검토 |
| 단위테스트계획서 · DE-13 | 실행 조건, 입력과 기대결과 |
| 추적매트릭스 · AN-05 | 문서 간 연계, 누락과 검증 현황 |
| 단위테스트결과서 · IM-03 | 실제 시험의 결과·판정·증적 |

앞의 명세 5종을 먼저 작성하며, 결과서(IM-03)는 실제 시험을 수행할 때 별도로 작성합니다.

</details>

<details>
<summary>질문과 확인요청서는 어떻게 제공하나요?</summary>

단독 작성과 명세일괄에 같은 기준을 적용합니다.

| 확인 항목 | 제공 방식 |
|---|---|
| 0건 | 확인 결과 안내. 빈 파일은 만들지 않음 |
| 1~5건 | 대화로 질문하고 확인요청서 Markdown에 기록. Excel 요청 시 Excel도 제공 |
| 6건 이상 | 확인요청서 Markdown·Excel을 발행하고 실제 파일 링크와 응답 칸 안내 |

직접 의견을 입력하거나 보류할 수 있습니다. 빈칸은 승인으로 처리하지 않으며, 미결 판단에 의존하는 확정은 보류합니다. 파일 검토를 요청하면 소량도 Excel로 제공합니다.

</details>

## 시작하기

프로젝트 폴더에서 플러그인을 설치하고, 프로젝트 설정 후 필요한 문서를 요청합니다.

### Claude Code

```text
/plugin marketplace add bs-koo/gx-pm
/plugin install gx-pm@gx-pm

/gx-프로젝트설정
/gx-요구사항정의서 첨부한 과업지시서로 요구사항정의서를 작성해줘. 확인요청서도 Excel로 제공해줘.
```

### Codex CLI·앱

Windows PowerShell 기준입니다. macOS·Linux에서는 `codex.cmd` 대신 `codex`를 사용합니다.

```powershell
codex.cmd plugin marketplace add bs-koo/gx-pm
codex.cmd plugin add gx-pm@gx-pm
```

설치 후 프로젝트 폴더의 새 대화에서 요청합니다.

```text
$gx-pm-workflow 프로젝트 설정을 시작해줘.
$gx-pm-workflow 첨부한 과업지시서로 요구사항정의서를 작성해줘. 확인요청서도 Excel로 제공해줘.
```

기존 사용자는 플러그인을 업데이트하고 새 세션에서 버전을 확인합니다. 이전 캐시가 남으면 재설치하되 프로젝트 문서와 설정은 보존합니다.

<details>
<summary>테이블정의서·명세일괄을 위한 표준용어사전 연결</summary>

테이블정의서와 명세일괄에는 `sqi-comn-term` MCP 연결이 필요합니다. 요구사항정의서 단독 작성은 이 연결 없이 시작할 수 있습니다.

```powershell
codex.cmd mcp add sqi-comn-term --url https://term.sqisoft.com/api/v1/mcp
codex.cmd mcp list
```

등록 후 새 세션에서 `list_categories` 호출이 성공하는지 확인합니다. Claude 설정과 재연결 방법은 [표준용어 MCP 연계 안내](plugins/gx-pm/docs/표준용어-mcp-연계.md)를 참고하세요.

</details>

## 커맨드

Claude Code에서는 아래 커맨드를 사용합니다. Codex에서는 `$gx-pm-workflow` 뒤에 같은 작업을 요청합니다.

| 커맨드 | 하는 일 |
|---|---|
| `/gx-프로젝트설정` | 프로젝트 정보·기준 자료·기존 자산 등록 |
| `/gx-요구사항정의서` | 요구사항 추출·검토·추가·수정 |
| `/gx-기능명세서` | 요구사항을 기능별 입력·처리·출력으로 구체화 |
| `/gx-테이블정의서` | DDL·기능명세 기반 테이블 정의와 표준용어 검토 |
| `/gx-단위테스트계획서` | 기능·제약별 시험 입력과 판정 기준 작성 |
| `/gx-추적매트릭스` | 문서 간 연계·누락·변경 영향 검토 |
| `/gx-명세일괄` | 명세 5종을 순서대로 작성하고 단계별 검토 |
| `/gx-단위테스트실행` | 계획서에 따라 로컬 시험 수행·결과·증적 기록 |
| `/gx-단위테스트결과반영` | 단위테스트실행의 기존 호환 이름 |

## 스킬 구성

**커맨드가 작업의 시작점이라면, 스킬은 작성·검토의 규칙입니다.** 총 20개 스킬 중 작업에 필요한 것을 연결해 사용합니다. 각 이름을 누르면 상세 지침을 확인할 수 있습니다.

| 영역 | 스킬 | 역할 |
|---|---|---|
| 실행 연결 | [워크플로 연결](plugins/gx-pm/skills/gx-pm-workflow/SKILL.md) | Codex 요청을 공통 커맨드에 연결 |
| 프로젝트 준비 | [프로파일 로드](plugins/gx-pm/skills/load-project-profile/SKILL.md) | 프로젝트 설정과 자산 확인 |
| 프로젝트 준비 | [기존 산출물 확인](plugins/gx-pm/skills/detect-existing-artifact/SKILL.md) | 기존 문서·근거 확인과 처리 방식 결정 |
| 프로젝트 준비 | [소스 색인](plugins/gx-pm/skills/scan-source-index/SKILL.md) | 구현 대조를 위한 소스코드 탐색 |
| 요구사항 분석 | [요구사항 추출](plugins/gx-pm/skills/extract-requirements/SKILL.md) | 원문 요구사항과 출처 정리 |
| 요구사항 분석 | [요구사항 분류](plugins/gx-pm/skills/classify-requirements/SKILL.md) | 업무 분류·비기능 유형·우선순위 검토 |
| 요구사항 분석 | [대안 감지](plugins/gx-pm/skills/detect-alternatives/SKILL.md) | 시안·대안·선택이 필요한 지점 확인 |
| 요구사항 분석 | [공공·SI 우선순위](plugins/gx-pm/skills/prioritize-si/SKILL.md) | 법적·감리·과업 기준으로 우선순위 결정 |
| 명세 작성 | [기능명세 작성](plugins/gx-pm/skills/generate-function-spec/SKILL.md) | 요구사항을 기능·입력·처리·출력으로 구체화 |
| 명세 작성 | [테이블 정의](plugins/gx-pm/skills/convert-ddl-to-tablespec/SKILL.md) | DDL 변환·컬럼 매핑·표준용어 검토 |
| 테스트 | [단위테스트계획 작성](plugins/gx-pm/skills/generate-unit-test-plan/SKILL.md) | 기능과 데이터 제약에서 시험 항목 도출 |
| 테스트 | [테스트 케이스 설계](plugins/gx-pm/skills/design-test-cases/SKILL.md) | 동등분할·경계값·분기·상태전이 적용 |
| 테스트 | [시험 수행·결과 기록](plugins/gx-pm/skills/apply-test-results/SKILL.md) | 실제 실행의 관측 결과와 증적 기록 |
| 사용자 확인 | [확인 항목 검토](plugins/gx-pm/skills/review-confirmations/SKILL.md) | 질문·추천·확인요청서 발행 |
| 사용자 확인 | [확인 응답 반영](plugins/gx-pm/skills/apply-confirmations/SKILL.md) | 명시적인 답변·정정값 반영과 파급 처리 |
| 변경 관리 | [ID 승계](plugins/gx-pm/skills/reconcile-ids/SKILL.md) | 기존 ID 유지·신규 채번·삭제 번호 보호 |
| 변경 관리 | [개정이력 관리](plugins/gx-pm/skills/manage-revision-history/SKILL.md) | 변경 내용·버전·상위 문서 근거 기록 |
| 변경 관리 | [변경 영향 분석](plugins/gx-pm/skills/impact-analysis/SKILL.md) | 영향 범위·수정 작업량·변경요청서 검토 |
| 추적성 | [ID 추적](plugins/gx-pm/skills/id-trace/SKILL.md) | 요구사항·기능·테스트의 양방향 연결 추적 |
| 추적성 | [추적매트릭스 작성](plugins/gx-pm/skills/trace-requirements/SKILL.md) | 문서 간 연계와 누락·검증 현황 대조 |

## 더 알아보기

요청 예시·기존 문서 수정·확인요청서·Excel 출력·FAQ는 [사용 가이드](USAGE.md)에서 확인할 수 있습니다.

[변경 이력](plugins/gx-pm/CHANGELOG.md) · [공통 실행 안내](plugins/gx-pm/CLAUDE.md) · [문서 작성 기준](plugins/gx-pm/templates/approval-protocol.md) · [보관 문서](plugins/gx-pm/archive/README.md)

<details>
<summary>플러그인 개발·유지보수</summary>

커맨드·스킬·템플릿을 수정할 때는 [Claude·Codex 공동 유지보수 지침](docs/development/dual-harness-maintenance.md)을 따릅니다.

```text
plugins/gx-pm/
├── commands/      # 9개 커맨드
├── skills/        # 20개 스킬
├── templates/     # 양식·공통 규약 15종
├── utils/         # Excel 변환·시험 증적 검증
└── tests/         # 계약·회귀 검사
```

```powershell
python -m unittest discover -s plugins/gx-pm/tests -q
git diff --check
```

자동 검사와 실제 대화·문서 생성 검증은 구분합니다. 사용성을 확인할 때는 두 환경에서 질문·응답 대기·파일 발행·재개를 검토합니다.

</details>

## License

MIT
