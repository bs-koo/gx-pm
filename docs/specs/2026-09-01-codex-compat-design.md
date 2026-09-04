# gx-pm Codex 하네스 호환 설계

작성: 2026-09-01
상태: 설계 확정 전
참조: oh-my-gx `.claude/rules/harness-codex.md` (Codex CLI 0.130.0 실측 기반)

## 요약

**gx-pm은 oh-my-gx보다 호환이 쉽다.** oh-my-gx에서 27곳·44곳·17개를 고쳐야 했던 3대 장벽이 gx-pm에는 아예 없다.

| 장벽 | oh-my-gx | gx-pm |
|------|---------:|------:|
| `${CLAUDE_PLUGIN_ROOT}` 절대경로 조립 | 27곳 | **0건** |
| `Skill()` 상호 호출 | 44곳 | **0건** |
| 서브에이전트(`Task`) 배포 | 17개 정의 | **0건** |
| 훅 번들 배포 | 2종 | **없음** |

대신 gx-pm에만 있는 장벽이 둘이다. **`commands` 컴포넌트**와 **`templates/` 배포**다. 둘 다 "Codex `plugin.json`이 무엇을 배포하는가"에 걸려 있다.

## 현황

```
gx-pm/                                  저장소 루트 = 마켓플레이스 루트
├─ .claude-plugin/marketplace.json      source: ./plugins/gx-pm
├─ docs/
└─ plugins/gx-pm/                       플러그인 루트
   ├─ .claude-plugin/plugin.json        skills: ./skills/ · commands: ./commands/
   ├─ commands/    16개  (한글 파일명 포함 — gx-감리대응.md 등)
   ├─ skills/      26개
   └─ templates/   16개  (커맨드·스킬이 111곳에서 참조)
```

oh-my-gx는 저장소 루트가 곧 플러그인 루트지만, gx-pm은 `plugins/` 아래에 플러그인을 두는 모노레포 형태다. 이 차이 자체는 문제가 아니다 — Codex도 같은 매니페스트 규격을 쓴다.

## 장벽 1 — `commands` 컴포넌트 미지원 (최대)

Codex `plugin.json`이 지원하는 컴포넌트 필드는 **`skills`·`hooks`·`mcpServers`·`apps`** 넷이다. `commands`가 없다.

gx-pm은 커맨드 16개가 **주 인터페이스**다. `/gx-spec` 하나로 명세 5종을, `/gx-testplan` 하나로 테스트 계획 4종을 만드는 파이프라인이 전부 커맨드에 있다. 이대로 설치하면 Codex 사용자는 26개 스킬만 보고, 그것들을 어떤 순서로 조합해야 하는지 알 수 없다.

### 대응: 커맨드를 얇은 래퍼로, 로직을 스킬로

Matt Pocock의 `grill-me` / `grilling` 패턴이 정확히 이 구조다.

```
commands/gx-spec.md          ← 얇은 래퍼 (Claude Code 슬래시 진입점)
   "skills/pipeline-spec/SKILL.md 의 절차를 따른다"

skills/pipeline-spec/SKILL.md  ← 파이프라인 로직 한 벌 (양쪽이 읽는다)
```

- **Claude Code**: 커맨드가 그대로 살아 있어 슬래시 자동완성·`argument-hint`가 유지된다
- **Codex**: 커맨드는 안 실리지만 스킬은 실린다. `pipeline-spec` 스킬을 직접 부르면 같은 절차가 돈다

**로직을 복제하지 않는다.** 커맨드에는 진입점 정보(description, argument-hint, 한 줄 포인터)만 남기고 본문을 스킬로 옮긴다.

이 작업이 이 설계에서 가장 큰 덩어리다. 커맨드 16개 중 파이프라인 2개(`gx-spec`·`gx-testplan`)와 단일 산출물 14개의 성격이 달라, 아래 우선순위로 나눈다.

| 순위 | 대상 | 이유 |
|------|------|------|
| 1 | `gx-spec` · `gx-testplan` | 파이프라인. 조합 순서가 여기에만 있어 Codex에서 가장 크게 잃는다 |
| 2 | `gx-프로젝트설정` | 다른 커맨드의 선행조건. 없으면 나머지가 막힌다 |
| 3 | 나머지 13개 | 대응 스킬이 이미 1:1로 있는 경우가 많다 — 확인 후 래퍼만 남기면 된다 |

3순위는 **먼저 대조부터 한다.** 예컨대 `gx-요구사항정의서` 커맨드와 `extract-requirements` 스킬이 같은 일을 한다면 새 스킬을 만들 필요 없이 커맨드를 그 스킬을 가리키는 래퍼로 바꾸면 끝이다.

### 한글 커맨드 파일명

`gx-감리대응.md` 같은 한글 파일명이 Codex 슬래시 커맨드로 등록되는지는 **실측하지 않았다.** 커맨드가 어차피 Codex에 안 실리므로 이 설계에서는 문제가 되지 않지만, 위 대응으로 만드는 **스킬 이름은 영문으로 짓는다** — 스킬 `name`은 양쪽 하네스가 모두 파싱한다.

## 장벽 2 — `templates/` 배포

`plugin.json`은 `skills`와 `commands`만 선언한다. `templates/`는 어느 컴포넌트에도 속하지 않는다.

Claude Code는 플러그인 디렉토리를 통째로 캐시하므로 `templates/`가 함께 따라온다. **Codex가 같은지는 확인되지 않았다.** 스킬 디렉토리만 배포하는 구조라면 `templates/`가 존재하지 않고, 그것을 참조하는 **111곳이 전부 죽는다.**

oh-my-gx도 같은 문제를 한 건 겪었다 — `gx-setup`이 읽는 `config.json` 템플릿이 스킬 디렉토리 밖(플러그인 루트)에 있어, 스킬만 배포되는 하네스에서는 읽지 못한다. 그쪽은 "Read 실패 시 사용자에게 수동 복사를 안내"로 우회했지만, 111곳에는 쓸 수 없는 방법이다.

### 대응 A (권장) — templates를 스킬 디렉토리 안으로

```
skills/_shared/templates/approval-protocol.md
skills/_shared/templates/prerequisites.md
...
```

`skills/` 아래에 있으면 `skills` 컴포넌트로 배포된다. 참조는 **파일 위치 기준 상대경로**로 바꾼다.

```
스킬에서:   Read("../_shared/templates/approval-protocol.md")
커맨드에서: Read("../skills/_shared/templates/approval-protocol.md")
```

파일 사이의 상대 위치는 설치 위치와 무관하므로 두 하네스 모두에서 해석된다. oh-my-gx가 형제 스킬 참조(`../../gx-setup/references/project-type-hints.md`)로 검증한 방식과 같다.

`_shared`가 스킬로 오인되지 않게 그 디렉토리에는 `SKILL.md`를 두지 않는다.

### 대응 B — 각 스킬의 `references/`로 분산

템플릿을 쓰는 스킬 안에 각각 복사한다. 배포는 확실하지만 **같은 템플릿이 여러 벌로 갈라진다.** 16개 템플릿이 111곳에서 쓰이므로 중복이 크고, 드리프트가 확실히 생긴다. 권장하지 않는다.

### 먼저 할 일 — 실측

설계를 확정하기 전에 **Codex가 플러그인 디렉토리를 통째로 배포하는지** 확인한다. 통째로 배포한다면 장벽 2는 존재하지 않고 경로 규약만 정리하면 된다.

```bash
codex plugin marketplace add <gx-pm 저장소 경로>
# TUI에서 활성화 후 캐시 디렉토리에 templates/ 가 있는지 확인
```

## 장벽 3 — `AskUserQuestion` (경미)

29개 파일이 쓴다. Codex 대응은 `request_user_input`이며 **EXPERIMENTAL**이라 기본 모드에서 발화하지 않을 수 있다.

**스킬 본문을 고칠 필요는 없다.** 도구 매핑 표를 각 스킬이 참조할 수 있는 곳에 두고, 아래 계약을 명시한다.

> `request_user_input`을 쓸 수 없으면 자연어로 묻되, **승인 없이 다음 단계로 넘어가지 않는다**는 계약은 그대로 지킨다.

gx-pm은 승인 루프(`templates/approval-protocol.md`)가 산출물 확정의 핵심이므로, 이 계약이 특히 중요하다. 게이트가 조용히 통과되면 검토 없는 산출물이 나간다.

## 장벽 4 — 매니페스트 이중화 (기계적)

| 파일 | 내용 |
|------|------|
| `plugins/gx-pm/.codex-plugin/plugin.json` | 기존 `plugin.json` 복사 후 `commands` 필드 제거 (Codex 미지원) |
| `.agents/plugins/marketplace.json` | 기존 `marketplace.json`과 동일 내용 |

버전은 네 곳(기존 2 + 신규 2)이 항상 같아야 한다. 어긋나면 Codex UI에 옛 버전이 표시된다. oh-my-gx는 이 대조를 린트 `[1/26]`로 강제한다 — gx-pm에도 같은 검사를 두는 것을 권한다(아래 검증 참조).

## 하지 않아도 되는 것

oh-my-gx에서 큰 작업이었지만 gx-pm에는 해당 없는 항목들이다. 착수 전에 확인만 한다.

- **경로 규약 전환** — `CLAUDE_PLUGIN_ROOT` 0건. 이미 깨끗하다
- **`Skill()` 변환** — 0건. 커맨드가 스킬을 이름으로 언급할 뿐 도구 호출을 하지 않는다
- **서브에이전트 배포** — `Task` 디스패치 0건. Codex가 `agents` 필드를 지원하지 않는 문제 자체가 없다
- **훅 이중화** — 훅이 없다. `plugin_hooks` 미완 이슈에 걸리지 않는다
- **`allowed-tools`** — 3개 스킬만 선언. Codex가 이 필드를 모델 프롬프트에 넣지 않지만 영향 범위가 작다

## 단계

각 단계가 독립적으로 검증 가능하다.

| 단계 | 내용 | 선행 |
|------|------|------|
| **0** | Codex 실측 — 플러그인 디렉토리 배포 범위 확인 (`templates/` 포함 여부), `codex features list`로 `default_mode_request_user_input` 상태 확인 | — |
| **1** | 매니페스트 이중화 + 버전 대조 검사 | — |
| **2** | 커맨드 16개 ↔ 스킬 26개 대조표 작성. 1:1 대응이 있는 것과 없는 것을 가른다 | — |
| **3** | 파이프라인 2개(`gx-spec`·`gx-testplan`)를 스킬로 추출, 커맨드는 래퍼로 | 2 |
| **4** | `gx-프로젝트설정` 동일 처리 | 2 |
| **5** | 나머지 13개 — 대응 스킬이 있으면 래퍼로, 없으면 추출 | 3·4 |
| **6** | `templates/` 이동 + 참조 111곳 경로 전환 | 0 |
| **7** | 도구 매핑 표를 스킬이 닿는 곳에 배치 | — |

**0단계를 먼저 한다.** 6단계의 필요 여부가 여기서 갈린다.

1·2단계는 0단계와 무관하게 지금 할 수 있다.

## 검증

gx-pm에는 현재 정합성 린트가 없다. oh-my-gx의 `scripts/lint-consistency.sh`에 해당하는 것을 만드는 것이 이 작업의 부산물이 된다.

최소한 아래를 기계 검사로 둔다.

- **버전 4중 일치** — `plugin.json` · `marketplace.json` · `.codex-plugin/plugin.json` · `.agents/plugins/marketplace.json`
- **참조 실존** — `templates/` 참조 111곳이 실제 파일을 가리키는지. 6단계 이후에는 상대경로가 대상 파일에 닿는지
- **커맨드-스킬 대응** — 래퍼가 된 커맨드가 실존하는 스킬을 가리키는지
- **`CLAUDE_PLUGIN_ROOT` 재발 방지** — 현재 0건인 상태를 유지

검사를 쓸 때 주의할 것이 하나 있다. oh-my-gx는 **"대상 문구가 다른 이유로 존재해 지시가 빠져도 통과하던" 가짜 검사를 네 번** 겪었다. 새 검사는 반드시 **일부러 깨뜨려 FAIL이 나오는지 확인**하고 원복한다. 문구 존재만 보는 검사는 회귀를 못 잡는다.

## 미검증 항목

- **Codex의 플러그인 배포 범위** — 장벽 2의 전제. 0단계에서 확인한다
- **한글 파일명·스킬명 처리** — 커맨드가 Codex에 안 실리므로 당장은 무관하지만, 스킬 `description`의 한국어 자연어 트리거가 Codex에서 어떻게 매칭되는지는 별개 문제다
- **`request_user_input` 실제 발화** — EXPERIMENTAL 상태가 풀렸는지 `codex features list`로 확인
- **승인 루프의 자연어 폴백** — `approval-protocol.md`가 선택지 UI를 전제한다면, 자연어로 낮췄을 때 그 절차가 성립하는지 검토가 필요하다

## 참고

oh-my-gx의 `.claude/rules/harness-codex.md`가 Codex CLI 0.130.0 실측 결과를 담고 있다. 도구 매핑표, 훅 규약 차이, 동작하지 않는 것 네 가지가 정리되어 있으므로 착수 전에 읽는다. 하네스가 갱신되면 그 문서보다 실제 도구 목록을 우선한다.
