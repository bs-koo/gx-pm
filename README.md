# GX PM

## 요구사항 한 장에서, 서로 연결된 명세까지.

RFP와 기존 자료로 요구사항을 정리하고, 기능·테이블·테스트 명세로 이어갑니다.
기존 문서의 ID와 사용자 결정을 유지하며 변경 영향과 실제 시험 결과를 관리합니다.

**Claude Code · Codex 지원**

[![Version](https://img.shields.io/badge/version-4.6.0-blue.svg)](plugins/gx-pm/CHANGELOG.md)
[![Skills](https://img.shields.io/badge/skills-20-green.svg)](#스킬-구성)
[![Commands](https://img.shields.io/badge/commands-9-orange.svg)](#커맨드-목록)

[동작 방식](#어떻게-동작하나요) · [스킬](#스킬-구성) · [설치](#설치하고-시작하기) · [상세 가이드](USAGE.md)

## 어떻게 동작하나요?

**자료 확인 → 명세 작성 → 사용자 검토 → 저장·Excel 전달**

1. **자료를 연결합니다.** 프로젝트를 설정하고 RFP·DDL·기존 문서를 확인합니다.
2. **필요한 문서를 작성합니다.** 요구사항정의서만 시작하거나 명세 5종을 일괄 작성합니다.
3. **판단할 내용을 확인합니다.** 질문에 추천·근거·대안·영향을 제시하고 실제 응답을 기다립니다.
4. **결과물을 정리합니다.** ID·개정이력·문서 간 연계를 유지하고 검토한 문서를 저장·내보냅니다.

수정 요청에는 기존 문서와 대상 ID·변경 근거를 함께 제공하면 됩니다.
미결사항이 남은 문서는 최종본 내보내기를 보류하며, 요청하면 검토용 초안을 제공합니다.

### 무엇을 받을 수 있나요?

| 산출물 | 담는 내용 |
|---|---|
| 요구사항정의서 · AN-02 | 요구사항, 출처, 분류와 변경 근거 |
| 기능명세서 · AN-03 | 기능별 입력·처리·출력과 요구사항 연계 |
| 테이블정의서 · DE-08 | DDL 기반 스키마, 제약과 표준 검토 |
| 단위테스트계획서 · DE-13 | 실행 조건, 입력과 기대결과 |
| 추적매트릭스 · AN-05 | 문서 간 연계, 누락과 검증 현황 |
| 단위테스트결과서 · IM-03 | 실제 시험의 결과·판정·증적 |

앞의 **명세 5종**을 먼저 작성합니다. 결과서(IM-03)는 로컬 API·화면 시험을 실제 수행할 때 별도로 작성합니다.
문서는 Markdown으로 관리하고 Excel로 내보낼 수 있습니다.

## 스킬 구성

평소에는 커맨드나 `$gx-pm-workflow`로 요청하면 됩니다. 20개 스킬이 아래 역할을 나누어 수행합니다.

| 스킬 | 역할 |
|---|---|
| `gx-pm-workflow` | Codex 요청을 공통 작업 절차에 연결 |
| `load-project-profile` | 프로젝트 설정 확인·활성화 |
| `detect-existing-artifact` | 기존 문서와 기준 버전 확인 |
| `scan-source-index` | 소스 구조를 색인화해 구현과 명세 대조 |
| `extract-requirements` | 원문에서 요구사항과 출처 추출 |
| `classify-requirements` | 업무·비기능 유형과 우선순위 분류 |
| `detect-alternatives` | 미결정 대안과 선택지 식별 |
| `generate-function-spec` | 요구사항을 기능의 입력·처리·출력으로 구체화 |
| `convert-ddl-to-tablespec` | DDL 기반 테이블정의서 작성 |
| `generate-unit-test-plan` | 기능별 단위테스트계획서 작성 |
| `design-test-cases` | 정상·경계·예외 테스트 설계 |
| `apply-test-results` | 로컬 시험 수행·결과와 증적 기록 |
| `review-confirmations` | 사용자 판단이 필요한 항목 수집·확인 |
| `apply-confirmations` | 명시적인 사용자 응답 반영 |
| `reconcile-ids` | 기존 ID 승계·신규 및 삭제 항목 대조 |
| `manage-revision-history` | 산출물 개정이력과 근거 버전 관리 |
| `impact-analysis` | 변경에 영향받는 문서·작업 범위 분석 |
| `prioritize-si` | 공공·SI 기준으로 우선순위 평가 |
| `id-trace` | 특정 ID의 상위·하위 연계 조회 |
| `trace-requirements` | 산출물 간 연계와 누락을 추적매트릭스로 확인 |

## 설치하고 시작하기

### Claude Code

```text
/plugin marketplace add bs-koo/gx-pm
/plugin install gx-pm@gx-pm
```

설치 후 프로젝트를 열고 요청합니다.

```text
/gx-프로젝트설정
/gx-요구사항정의서 첨부한 과업지시서로 요구사항정의서만 작성해줘.
```

### Codex

Windows PowerShell에서 설치합니다. macOS·Linux에서는 `codex.cmd` 대신 `codex`를 사용합니다.

```powershell
codex.cmd plugin marketplace add bs-koo/gx-pm
codex.cmd plugin add gx-pm@gx-pm
```

새 대화에서 프로젝트 설정 후 작업을 요청합니다.

```text
$gx-pm-workflow 프로젝트 설정을 시작해줘. 기준 자료는 이 폴더에 있어.
$gx-pm-workflow 첨부한 과업지시서로 요구사항정의서만 작성해줘.
```

**테이블정의서·명세일괄은 `sqi-comn-term` MCP 연결이 필요합니다.** 요구사항정의서만 작성할 때는 필요하지 않습니다.

```powershell
codex.cmd mcp add sqi-comn-term --url https://term.sqisoft.com/api/v1/mcp
```

등록 후 새 세션에서 `list_categories` 호출을 확인합니다. [Claude·Codex 연결 안내](plugins/gx-pm/docs/표준용어-mcp-연계.md)

## 커맨드 목록

Claude Code에서는 아래 커맨드를, Codex에서는 `$gx-pm-workflow`에 같은 작업을 요청합니다.

| 커맨드 | 작업 |
|---|---|
| `/gx-프로젝트설정` | 프로젝트 기본 정보·자산 등록 |
| `/gx-요구사항정의서` | 요구사항 작성·수정 |
| `/gx-기능명세서` | 기능명세 작성·수정 |
| `/gx-테이블정의서` | DDL 기반 테이블정의 |
| `/gx-단위테스트계획서` | 테스트 계획 작성 |
| `/gx-추적매트릭스` | 연계·누락·변경 영향 검토 |
| `/gx-명세일괄` | 명세 5종 일괄 작성 |
| `/gx-단위테스트실행` | 로컬 시험 수행·결과 기록 |
| `/gx-단위테스트결과반영` | 단위테스트실행의 호환 별칭 |

## 더 알아보기

- [사용 가이드](USAGE.md): 요청 예시, 기존 문서 수정, 확인요청서, Excel 출력과 FAQ
- [변경 이력](plugins/gx-pm/CHANGELOG.md): 최신 버전의 변경 사항
- [공동 유지보수 지침](docs/development/dual-harness-maintenance.md): Claude·Codex 실행 경로와 검증

<details>
<summary>개발자를 위한 저장소 구성·검증</summary>

```text
gx-pm/
├── .claude-plugin/marketplace.json         # Claude 마켓플레이스 등록
├── .agents/plugins/marketplace.json       # Codex 마켓플레이스 등록
├── .github/workflows/test.yml             # 회귀 검증
├── plugins/gx-pm/
│   ├── .claude-plugin/plugin.json         # Claude 플러그인 정보
│   ├── .codex-plugin/plugin.json          # Codex 플러그인 정보
│   ├── commands/                         # 9개 커맨드
│   ├── skills/                           # 20개 스킬
│   ├── templates/                        # 산출물 양식·공통 규약 15종
│   ├── utils/                            # Excel 변환·시험 증적 검증
│   ├── tests/                            # 계약·회귀 테스트
│   ├── docs/                             # 표준용어 MCP 연계 안내
│   ├── archive/                          # 비활성 커맨드·스킬·양식
│   ├── CLAUDE.md                         # 공통 실행 지침
│   └── CHANGELOG.md                      # 변경 이력
├── docs/development/                      # 개발·검토 문서
└── README.md
```

```powershell
python -m unittest discover -s plugins/gx-pm/tests -q
git diff --check
```

</details>

## License

MIT
