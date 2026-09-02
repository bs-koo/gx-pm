# Codex 하네스 — 커맨드-스킬 대조표

측정: 2026-09-02 / gx-pm v2.0.0 / Codex CLI 0.130.0
근거: oh-my-gx `.claude/rules/harness-codex.md` (Codex CLI 0.130.0 실측)

Claude Code 사용자는 이 문서를 읽을 필요가 없다.

## 왜 이 문서가 있는가

Codex 플러그인 매니페스트가 지원하는 컴포넌트는 `skills`·`hooks`·`mcpServers`·`apps`
넷이다. `commands` 가 없다. gx-pm 은 커맨드 16개가 주 인터페이스이므로, Codex
사용자는 스킬 26개만 보고 **그것들을 어떤 순서로 조합해야 하는지 알 수 없다.**

이 문서는 "커맨드를 스킬로 추출하는 데 얼마나 드는가" 에 답한다.

## 실측 요약

| 항목 | 값 |
|---|---|
| 커맨드 | 16 |
| 스킬 | 26 |
| 커맨드가 부르지 않는 스킬 | 0 |
| **1:1 로 대응하는 커맨드** | **0** |
| 커맨드당 조립 스킬 (평균) | 4.1 |
| 커맨드 고유 로직 (Step 합계) | 118 |

**커맨드는 래퍼가 아니라 조립 절차다.** 스킬 26개는 부품이고, 커맨드 16개는
그 부품을 순서·중단점·승인 루프와 함께 엮는 절차다. 두 계층이 다르다.

## 커맨드 16 ↔ 스킬 26

`추출 우선순위` 는 Codex 에서 잃는 것의 크기 순이다.

> **셈 규칙**: `Step` 은 `### Step N` 헤딩의 고유 번호 수, `게이트` 는 그중
> `[필수 중단점]` 이 붙은 것이다. 분기 전용 단계(`### [계획] Step 4a` 형태)와
> 하위 게이트(`####`)는 이 셈에서 빠진다 — **실제 승인 중단점은 더 많다**:
> `/gx-시스템테스트` 5, `/gx-프로젝트설정` 5, `/gx-결함관리대장` 2.
> 추출 견적을 낼 때 이 셋은 표의 게이트 수보다 크게 잡는다.

| 커맨드 | 조립 스킬 | 고유 로직 | 추출 우선순위 |
|---|---|---|---|
| `/gx-spec` | `load-project-profile` · `detect-existing-artifact` · `detect-alternatives` | Step 9 · 게이트 2 | **1** — 명세 5종의 조합 순서가 여기에만 있다 |
| `/gx-testplan` | `load-project-profile` · `detect-existing-artifact` · `design-test-cases` | Step 8 · 게이트 2 | **1** — 테스트 4종의 조합 순서가 여기에만 있다 |
| `/gx-프로젝트설정` | `scan-source-index` | Step 7 · 게이트 4 | **2** — 다른 15개의 하드 선행조건 |
| `/gx-요구사항정의서` | `load-project-profile` · `detect-existing-artifact` · `detect-alternatives` · `extract-requirements` · `classify-requirements` · `prioritize-si` | Step 7 · 게이트 2 | 3 |
| `/gx-화면목록표` | `load-project-profile` · `detect-existing-artifact` · `scan-source-index` · `detect-alternatives` · `generate-screen-list` | Step 7 · 게이트 2 | 3 |
| `/gx-프로그램정의서` | `load-project-profile` · `detect-existing-artifact` · `reverse-scan-source` · `detect-alternatives` · `generate-program-list` | Step 7 · 게이트 2 | 3 |
| `/gx-인터페이스정의서` | `load-project-profile` · `detect-existing-artifact` · `reverse-scan-interfaces` · `detect-alternatives` · `generate-interface-spec` | Step 7 · 게이트 2 | 3 |
| `/gx-테이블정의서` | `load-project-profile` · `detect-existing-artifact` · `generate-erd-guide` · `convert-ddl-to-tablespec` · `detect-alternatives` | Step 6 · 게이트 2 | 3 |
| `/gx-총괄테스트계획서` | `load-project-profile` · `detect-existing-artifact` · `detect-alternatives` · `generate-master-test-plan` | Step 10 · 게이트 6 | 3 |
| `/gx-단위테스트계획서` | `load-project-profile` · `detect-existing-artifact` · `scan-source-index` · `generate-unit-test-plan` · `design-test-cases` | Step 10 · 게이트 3 | 3 |
| `/gx-통합테스트시나리오` | `load-project-profile` · `detect-existing-artifact` · `generate-integration-test` | Step 7 · 게이트 1 | 3 |
| `/gx-시스템테스트` | `load-project-profile` · `detect-existing-artifact` · `generate-system-test` · `manage-defects` | Step 7 · 게이트 3 | 3 |
| `/gx-테스트결과서` | `load-project-profile` · `detect-existing-artifact` · `fill-unit-test-result` · `fill-integration-test-result` · `manage-defects` | Step 9 · 게이트 3 | 3 |
| `/gx-결함관리대장` | `load-project-profile` · `detect-existing-artifact` · `manage-defects` | Step 4 · 게이트 1 | 3 |
| `/gx-추적매트릭스` | `load-project-profile` · `detect-existing-artifact` · `id-trace` · `trace-requirements` | Step 5 · 게이트 1 | 3 |
| `/gx-감리대응` | `load-project-profile` · `detect-existing-artifact` · `audit-response` · `impact-analysis` | Step 8 · 게이트 2 | 3 |

### 이 표가 뒤집는 것

설계 문서 `docs/specs/2026-09-01-codex-compat-design.md` 는 3순위 13개를
*"대응 스킬이 이미 1:1로 있는 경우가 많다 — 확인 후 래퍼만 남기면 된다"* 고 봤다.
**1:1 인 커맨드는 하나도 없다.** 3순위는 래퍼 작업이 아니라 조립 절차 문서
13벌을 새로 쓰는 작업이다.

## 도구 매핑

스킬·커맨드 본문은 Claude Code 도구명으로 서술돼 있다. Codex 에서는 아래로 옮긴다.

| 본문 표기 | Codex API | 비고 |
|---|---|---|
| `AskUserQuestion` | `request_user_input` | 선택지 지원. EXPERIMENTAL |
| Bash 실행 | `exec_command` / `local_shell` | |

`AskUserQuestion` 은 30개 파일이 쓴다 (커맨드 16 · 스킬 11 · 템플릿 3). `request_user_input` 이
`default_mode_request_user_input` 미완으로 기본 모드에서 발화하지 않을 수 있다.

> **계약**: `request_user_input` 을 쓸 수 없으면 자연어로 묻되,
> **승인 없이 다음 단계로 넘어가지 않는다**는 계약은 그대로 지킨다.

gx-pm 은 승인 루프(`templates/approval-protocol.md`)가 산출물 확정의 핵심이다.
게이트가 조용히 통과되면 검토 없는 산출물이 나간다.

## 지금 걸리지 않는 것

| 장벽 | oh-my-gx | gx-pm |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}` 절대경로 조립 | 27곳 | **0** |
| `Skill()` 상호 호출 | 44곳 | **0** |
| 서브에이전트 배포 | 17개 정의 | **0** |
| 훅 번들 배포 | 2종 | **없음** |

세 항목은 `tests/test_codex_compat.py` 의 `HarnessCompatTest` 가 0건으로 묶는다.

## 미검증

- **Codex 의 플러그인 배포 범위.** `templates/` 16개와 `utils/export-xlsx.py` 는
  `skills` 컴포넌트 밖에 있다. Codex 가 플러그인 디렉터리를 통째로 배포하면 문제가
  없고, 스킬 디렉터리만 배포하면 `templates/` 참조 83곳과 xlsx 추출이 전부 죽는다.
  설계 문서는 `templates/` 만 다루는데 `utils/` 도 같은 처지다.
- **활성화 이후.** `codex plugin marketplace add .` 는 성공했다(exit 0,
  `Added marketplace \`gx-pm\``, 2026-09-02 실측) — 매니페스트가 파싱되고
  `policy`·`category` 열거값도 받아들여진다는 뜻이다. 다만 **등록이 활성화는 아니다.**
  플러그인 활성화는 Codex TUI 에서만 되므로, 실제로 스킬이 노출되는지와 아래
  배포 범위 항목은 여전히 미확인이다.
- **`request_user_input` 실제 발화.** `codex features list` 로 확인한다.
- **한국어 스킬 `description` 의 트리거 매칭.** 커맨드는 어차피 실리지 않지만,
  스킬 설명의 한국어 자연어 트리거가 Codex 에서 어떻게 매칭되는지는 별개 문제다.

## 다음

1. **Codex 배포 범위 실측** — 위 「미검증」 첫 항목. 이것이 `templates/` 이동
   작업의 필요 여부를 가른다.
2. **1·2 순위 추출** — `/gx-spec` · `/gx-testplan` · `/gx-프로젝트설정`.
   Codex 에서 가장 크게 잃는 셋이다.
3. **3순위 13개** — 위 표대로 조립 절차 13벌. 1·2 순위를 끝내고 실제 비용을
   본 뒤에 판단한다.

추출 작업은 커맨드 본문을 비우게 되는데, 그 본문을 검사하는 계약 테스트가
21건 있다 (`CommandStructureTest` · `PipelineCommandTest` 등). 게이트 개수,
산출물 파생 순서, 화면 분리 중단점 선언 — 전부 런타임 동작을 지키는 검사다.
추출 설계는 그 21건을 어디로 옮길지부터 정해야 한다.
