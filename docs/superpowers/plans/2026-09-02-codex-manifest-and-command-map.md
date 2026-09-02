# Codex 매니페스트 이중화와 커맨드-스킬 대조표 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-pm 을 Codex CLI 에 등록할 수 있게 매니페스트를 이중화하고, 그 상태가 조용히 낡지 않도록 계약 테스트로 묶으며, 향후 커맨드 추출(3~5단계)의 견적 근거가 될 커맨드-스킬 대조표를 만든다.

**Architecture:** 기존 커맨드·스킬·템플릿은 **한 줄도 건드리지 않는다.** 추가되는 것은 매니페스트 2개, 문서 1개, 테스트 파일 1개, 그리고 기존 `VersionConsistencyTest` 의 확장 1건뿐이다. 스킬 본문은 단일 소스로 유지하고 하네스별로 복제하지 않는다 — `.codex-plugin/plugin.json` 도 `.claude-plugin/plugin.json` 과 같은 `./skills/` 를 가리킨다.

**Tech Stack:** Python 3 표준 라이브러리 `unittest` (외부 의존성 없음), JSON 매니페스트, 마크다운 문서. 테스트는 `plugins/gx-pm/` 에서 `python -m unittest discover -s tests` 로 돈다.

**Spec:** `docs/specs/2026-09-01-codex-compat-design.md`

**참조 구현 (실물):** `/d/SQ/oh-my-gx/` — Codex 대응을 이미 마친 자매 플러그인.
- `/d/SQ/oh-my-gx/.claude/rules/harness-codex.md` — Codex CLI 0.130.0 실측 기록
- `/d/SQ/oh-my-gx/.codex-plugin/plugin.json` — 동작하는 Codex 매니페스트
- `/d/SQ/oh-my-gx/.agents/plugins/marketplace.json` — 동작하는 Codex 마켓플레이스

---

## Global Constraints

- **기존 `commands/`·`skills/`·`templates/` 파일을 수정하지 않는다.** 이 계획의 범위는 매니페스트·테스트·문서 추가뿐이다. 커맨드를 래퍼로 바꾸는 3~5단계는 이 계획에 없다.
- **테스트는 표준 라이브러리 `unittest` 만 쓴다.** pytest·외부 패키지를 도입하지 않는다.
- **테스트 함수명은 한국어**로 짓는다 (기존 81건과 동일 관례). 클래스명은 영문.
- **모든 신규 테스트는 반증(falsification)을 거친다.** 일부러 규칙을 깨뜨려 FAIL 이 나오는 것을 확인하고 원복한다. 이 저장소는 "대상 문구가 다른 이유로 존재해 지시가 빠져도 통과하던" 가짜 검사를 이미 여러 번 겪었다.
- **테스트 실행은 `plugins/gx-pm/` 디렉터리에서** `python -m unittest discover -s tests` 로 한다. `python -m unittest tests.test_x.Class` 는 `helpers` import 때문에 실패한다. 클래스 하나만 돌릴 때는 `python -m unittest discover -s tests -k <클래스명> -v`.
- **착수 시점 기준선: 테스트 81건 전부 통과.** 어느 태스크도 기존 81건을 깨뜨리면 안 된다.
- **커밋 메시지 끝에 반드시 붙인다:**
  ```
  Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
  ```
- **`docs/specs/2026-09-01-codex-compat-design.md` 를 수정하지 않는다.** 다른 세션이 만든 미추적 파일이다. 정정 사항은 Task 3 이 만드는 문서에 기록한다.
- 콘솔이 `cp949` 라 파이썬으로 한국어를 직접 print 하면 인코딩 오류가 난다. 결과를 파일로 쓰고 읽는다.

---

## 설계 문서와 다른 점 — 실측으로 확인한 정정 4건

이 계획은 spec 을 그대로 따르지 않는다. 아래 4건은 실측이 spec 과 어긋난 지점이며, **실측을 따른다.**

### 정정 1. 버전은 "4중 일치" 가 아니라 **3중 일치**다

spec 「장벽 4」는 매니페스트 4곳의 버전이 항상 같아야 한다고 한다. 그러나 참조 구현의 `.agents/plugins/marketplace.json` 에는 **`version` 필드가 아예 없다.**

```json
{
  "name": "oh-my-gx",
  "interface": { "displayName": "oh-my-gx" },
  "plugins": [
    {
      "name": "oh-my-gx",
      "source": { "source": "url", "url": "./" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Developer Tools"
    }
  ]
}
```

따라서 버전을 비교할 대상은 `.claude-plugin/plugin.json` · `.claude-plugin/marketplace.json` · `.codex-plugin/plugin.json` 셋이다. `.agents/plugins/marketplace.json` 은 **버전 대신 `source` 가 올바른 플러그인 디렉터리를 가리키는지**를 검사한다.

### 정정 2. `.codex-plugin/plugin.json` 은 "commands 만 뺀 복사본" 이 아니다

spec 은 "기존 `plugin.json` 복사 후 `commands` 필드 제거" 라고 한다. 참조 구현은 그것 말고도 두 가지가 더 있다.

| 필드 | Claude 매니페스트 | Codex 매니페스트 |
|---|---|---|
| `commands` | 있음 | **없음** (Codex 미지원) |
| `license` | 없음 | 있음 |
| `interface` | 없음 | **있음** — `displayName`·`shortDescription`·`longDescription`·`developerName`·`category`·`capabilities`·`defaultPrompt`·`websiteURL`·`brandColor` |
| `hooks` | 인라인 객체 | 파일 경로 문자열 |

`interface` 블록은 Codex TUI 의 플러그인 카드에 쓰인다. 빠뜨리면 등록은 되지만 표시가 비어 보인다. gx-pm 에는 훅이 없으므로 `hooks` 는 양쪽 다 없다.

### 정정 3. `source` 값을 그대로 베끼면 안 된다

참조 구현의 `url` 은 `"./"` 다. **oh-my-gx 는 저장소 루트가 곧 플러그인 루트이기 때문**이다. gx-pm 은 플러그인이 `plugins/gx-pm/` 아래에 있으므로 `"./plugins/gx-pm"` 이어야 한다. 이 한 글자 차이가 등록 실패를 만든다.

### 정정 4. "gx-pm 에는 정합성 린트가 없다" 는 사실이 아니다

spec 「검증」절은 검사 4종을 새로 만들라고 한다. 실측하면 `plugins/gx-pm/tests/` 에 **계약 테스트 81건**이 이미 돌고 있고, 그중 셋은 이미 구현돼 있다.

| spec 이 제안한 검사 | 실제 상태 |
|---|---|
| 버전 일치 | `VersionConsistencyTest.test_모든_매니페스트의_버전이_같다` — 확장만 하면 된다 (Task 1) |
| 참조 실존 | `CrossReferenceTest` 4건 + `LegacyReferenceTest` 2건 — 이미 있다 |
| 커맨드-스킬 대응 | `CrossReferenceTest.test_모든_스킬이_어느_커맨드에서든_호출된다` — 이미 있다 |
| `CLAUDE_PLUGIN_ROOT` 재발 방지 | **없다** — 유일하게 신규 (Task 2) |

또한 spec 이 말한 `templates/` 참조 111곳은 실측 **83곳**이다 (`grep -o 'templates/…\.md' commands skills`).

---

## File Structure

| 파일 | 책임 |
|---|---|
| `plugins/gx-pm/.codex-plugin/plugin.json` **(신규)** | Codex 플러그인 매니페스트. `commands` 없음, `interface` 있음, `skills` 는 Claude 쪽과 동일 경로 |
| `.agents/plugins/marketplace.json` **(신규, 저장소 루트)** | Codex 마켓플레이스 매니페스트. `source` 가 `plugins/gx-pm` 을 가리킨다 |
| `plugins/gx-pm/tests/test_codex_compat.py` **(신규)** | Codex 호환을 지키는 계약 테스트 전부 — 매니페스트 형태(Task 1), 하네스 비호환 패턴 재발 방지(Task 2), 대조표 결속(Task 3) |
| `plugins/gx-pm/docs/codex-harness.md` **(신규)** | 커맨드 16 ↔ 스킬 26 대조표, 도구 매핑, 실측 결과, spec 정정 기록 |
| `plugins/gx-pm/tests/helpers.py` (수정) | `runtime_docs()` 추가 — 런타임에 지시로 읽히는 문서만 반환 |
| `plugins/gx-pm/tests/test_plugin_consistency.py` (수정) | `VersionConsistencyTest` 에 Codex 매니페스트 버전 비교 1줄 추가 |
| `plugins/gx-pm/CHANGELOG.md` (수정) | 태스크별 항목 추가 |
| `README.md` (수정, 저장소 루트) | 디렉토리 트리에 `.codex-plugin/` 표기 |

`test_codex_compat.py` 를 한 파일로 두는 이유: 세 태스크가 만드는 검사는 전부 "Codex 에서 gx-pm 이 동작하는 조건" 이라는 하나의 책임이다. 함께 바뀌므로 함께 산다.

---

## 착수 전 확인

- [ ] `cd plugins/gx-pm && python -m unittest discover -s tests` → **81건 통과** 확인. 여기서 실패하면 이 계획의 전제가 깨진 것이므로 멈추고 보고한다.

---

### Task 1: Codex 매니페스트 이중화 + 버전 3중 일치

**Files:**
- Create: `plugins/gx-pm/.codex-plugin/plugin.json`
- Create: `.agents/plugins/marketplace.json` (저장소 루트)
- Create: `plugins/gx-pm/tests/test_codex_compat.py`
- Modify: `plugins/gx-pm/tests/test_plugin_consistency.py` (`VersionConsistencyTest`)
- Modify: `plugins/gx-pm/CHANGELOG.md`
- Modify: `README.md` (저장소 루트, 디렉토리 트리)

**Interfaces:**
- Consumes: `plugins/gx-pm/tests/helpers.py` 의 `PLUGIN_ROOT`, `REPO_ROOT` (기존)
- Produces: `test_codex_compat.py` 의 모듈 상수 4개 — 후속 태스크가 같은 파일에 클래스를 추가하며 재사용한다
  ```python
  CODEX_PLUGIN      # PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
  CODEX_MARKETPLACE # REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
  CLAUDE_PLUGIN     # PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
  CLAUDE_MARKETPLACE# REPO_ROOT / ".claude-plugin" / "marketplace.json"
  ```

---

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`plugins/gx-pm/tests/test_codex_compat.py` 를 새로 만든다.

```python
"""Codex 하네스 호환 계약 테스트.

근거: oh-my-gx `.claude/rules/harness-codex.md` (Codex CLI 0.130.0 실측)
와 그 저장소의 동작하는 매니페스트 실물.

Codex 는 Claude Code 의 플러그인 규격을 그대로 채택했지만 매니페스트 위치와
지원 컴포넌트가 다르다. 한쪽만 갱신되면 Codex UI 에 옛 버전이 표시되거나
등록 자체가 실패하는데, 사람이 두 파일을 대조하는 방식으로는 반드시 어긋난다.
"""

import json
import unittest

from helpers import PLUGIN_ROOT, REPO_ROOT

CODEX_PLUGIN = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CODEX_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
CLAUDE_PLUGIN = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"


class CodexManifestTest(unittest.TestCase):
    """Codex 매니페스트가 Claude 매니페스트와 어긋나지 않는지."""

    def setUp(self):
        self.codex = json.loads(CODEX_PLUGIN.read_text(encoding="utf-8"))
        self.claude = json.loads(CLAUDE_PLUGIN.read_text(encoding="utf-8"))
        self.codex_market = json.loads(CODEX_MARKETPLACE.read_text(encoding="utf-8"))
        self.claude_market = json.loads(CLAUDE_MARKETPLACE.read_text(encoding="utf-8"))

    def test_codex_매니페스트에_commands_필드가_없다(self):
        """Codex plugin.json 이 지원하는 컴포넌트는 skills·hooks·mcpServers·apps 넷이다.

        commands 를 남겨두면 Codex 는 모르는 필드로 무시하지만, 남아 있는 것 자체가
        '커맨드가 Codex 에서 동작한다' 는 오해를 만든다. 커맨드 16개는 실리지 않는다.
        """
        self.assertNotIn(
            "commands", self.codex,
            "Codex 는 commands 컴포넌트를 지원하지 않습니다 — 필드를 지우세요",
        )

    def test_두_매니페스트가_같은_스킬_경로를_가리킨다(self):
        """스킬 본문은 단일 소스다. 하네스별로 복제하지 않는다."""
        self.assertEqual(
            self.codex["skills"], self.claude["skills"],
            "스킬 경로가 갈라졌습니다 — 스킬 본문은 한 벌만 유지합니다",
        )

    def test_두_매니페스트의_이름과_설명이_같다(self):
        """설명이 갈라지면 Codex UI 에만 옛 문구가 남는다.

        같게 묶어두면 test_설명문의_스킬_커맨드_수가_실제와_같다 의 개수 검사도
        Codex 쪽에 자동으로 적용된다 — 검사를 복제하지 않고 값을 묶는 쪽을 택했다.
        """
        self.assertEqual(self.codex["name"], self.claude["name"])
        self.assertEqual(self.codex["description"], self.claude["description"])

    def test_codex_매니페스트에_interface_블록이_있다(self):
        """Codex TUI 의 플러그인 카드가 읽는 블록이다. 없으면 표시가 빈다.

        Claude 매니페스트에는 없는 필드라 '복사 후 commands 만 제거' 로는 생기지 않는다.
        """
        self.assertIn("interface", self.codex)
        for 필드 in ("displayName", "shortDescription", "category", "capabilities"):
            with self.subTest(필드=필드):
                self.assertIn(필드, self.codex["interface"])

    def test_codex_마켓플레이스가_플러그인_디렉터리를_가리킨다(self):
        """참조 구현(oh-my-gx)의 url 은 './' 다 — 저장소 루트가 곧 플러그인 루트라서다.

        gx-pm 은 플러그인이 plugins/gx-pm 아래에 있다. './' 를 그대로 베끼면
        Codex 가 저장소 루트에서 plugin.json 을 찾다 실패한다.
        """
        entry = self.codex_market["plugins"][0]
        self.assertEqual(entry["name"], self.claude["name"])
        self.assertEqual(
            entry["source"]["url"],
            self.claude_market["plugins"][0]["source"],
            "Codex 마켓플레이스의 url 이 Claude 쪽 source 와 다른 곳을 가리킵니다",
        )

    def test_codex_마켓플레이스의_source_가_객체다(self):
        """Claude 는 문자열('./plugins/gx-pm'), Codex 는 {source, url} 객체다.

        스키마 차이라 문자열을 그대로 두면 파싱에서 걸린다.
        """
        source = self.codex_market["plugins"][0]["source"]
        self.assertIsInstance(source, dict)
        self.assertEqual(source["source"], "url")
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -k CodexManifestTest -v
```

기대: 6건 전부 **ERROR** — `FileNotFoundError: ...\.codex-plugin\plugin.json`

- [ ] **Step 3: Codex 플러그인 매니페스트를 만든다**

`plugins/gx-pm/.codex-plugin/plugin.json` — `name`·`version`·`description`·`author`·`homepage`·`repository`·`keywords`·`skills` 는 `.claude-plugin/plugin.json` 에서 **그대로** 옮기고, `commands` 를 빼고, `license` 와 `interface` 를 더한다.

```json
{
  "name": "gx-pm",
  "version": "2.0.0",
  "description": "공공/SI PM의 AI 운영 체제 — 산출물 이름 한국어 커맨드 16개, 명세·테스트 묶음 파이프라인, 선행조건 자동 검사, 프로젝트 프로파일, 역방향 생성, xlsx 추출. 26개 스킬로 요구사항부터 테스트·결함관리·감리대응까지 자동화합니다.",
  "author": {
    "name": "SQI"
  },
  "homepage": "https://github.com/bs-koo/gx-pm",
  "repository": "https://github.com/bs-koo/gx-pm",
  "license": "MIT",
  "keywords": [
    "product-manager",
    "public-sector",
    "SI",
    "korean",
    "requirements",
    "traceability",
    "test-plan",
    "audit",
    "ERDCloud",
    "cowork-plugin",
    "test-case",
    "defect-management",
    "system-test",
    "pipeline"
  ],
  "skills": "./skills/",
  "interface": {
    "displayName": "gx-pm",
    "shortDescription": "공공/SI 프로젝트 산출물을 요구사항부터 감리대응까지 만드는 PM 플러그인",
    "longDescription": "RFP·과업지시서에서 요구사항을 뽑아 요구사항정의서·화면목록표·프로그램정의서·인터페이스정의서·테이블정의서를 만들고, 총괄·단위·통합·시스템 테스트 계획과 결함관리대장, 요구사항추적매트릭스, 감리대응 자료까지 이어서 생성한다. 각 산출물은 승인 루프를 거쳐 확정하며 xlsx 로 추출할 수 있다.",
    "developerName": "SQI",
    "category": "Developer Tools",
    "capabilities": [
      "Interactive",
      "Read",
      "Write"
    ],
    "defaultPrompt": [
      "RFP에서 요구사항을 뽑아줘",
      "명세 5종을 한 번에 만들어줘",
      "요구사항 추적매트릭스를 만들어줘"
    ],
    "websiteURL": "https://github.com/bs-koo/gx-pm",
    "brandColor": "#0F766E"
  }
}
```

`description` 은 `.claude-plugin/plugin.json` 의 값과 **문자 하나까지 같아야** 한다 — `test_두_매니페스트의_이름과_설명이_같다` 가 검사한다. 복사해 붙인다.

`category` 는 참조 구현이 쓰는 `"Developer Tools"` 를 그대로 쓴다. Codex 가 받는 값의 목록을 실측하지 않았으므로, 동작이 확인된 값에서 벗어나지 않는다. `longDescription` 에는 **숫자를 넣지 않는다** — 스킬·커맨드 개수를 적으면 개수가 바뀔 때 조용히 낡는데 그것을 잡는 검사가 없다.

- [ ] **Step 4: Codex 마켓플레이스 매니페스트를 만든다**

`.agents/plugins/marketplace.json` — **저장소 루트**다. `plugins/gx-pm/` 아래가 아니다.

```json
{
  "name": "gx-pm",
  "interface": {
    "displayName": "gx-pm"
  },
  "plugins": [
    {
      "name": "gx-pm",
      "source": {
        "source": "url",
        "url": "./plugins/gx-pm"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Developer Tools"
    }
  ]
}
```

`url` 이 `"./"` 가 아니라 `"./plugins/gx-pm"` 인 것이 참조 구현과의 유일한 실질적 차이다. `.claude-plugin/marketplace.json` 의 `source` 값과 같아야 하며 `test_codex_마켓플레이스가_플러그인_디렉터리를_가리킨다` 가 검사한다.

`policy` 값은 참조 구현을 그대로 옮긴 것이고 Codex 가 받는 열거값을 실측하지 않았다. Step 8 의 등록 실측에서 거부되면 그때 조정하고, 결과를 Task 3 문서의 「미검증」에 적는다.

- [ ] **Step 5: 테스트 통과를 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -k CodexManifestTest -v
```

기대: **6건 PASS**

- [ ] **Step 6: 버전 3중 일치로 확장한다**

`plugins/gx-pm/tests/test_plugin_consistency.py` 의 `VersionConsistencyTest.setUp` 에 아래를 더한다 (`self.changelog = ...` 줄 바로 뒤).

```python
        self.codex_plugin_json = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
```

같은 클래스의 `test_모든_매니페스트의_버전이_같다` 마지막에 아래를 더한다.

```python
        self.assertEqual(
            self.codex_plugin_json["version"], version,
            ".codex-plugin/plugin.json 의 버전이 다릅니다 "
            "— Codex UI 에 옛 버전이 표시됩니다",
        )
```

클래스 독스트링의 첫 줄도 함께 고친다. 현재 `"""버전과 개수 표기가 10개 지점에 흩어져 있어 한쪽만 갱신되기 쉽다.` → `"""버전과 개수 표기가 11개 지점에 흩어져 있어 한쪽만 갱신되기 쉽다.`

`.agents/plugins/marketplace.json` 은 **여기에 넣지 않는다.** 그 파일에는 `version` 필드가 없다 (「정정 1」 참조). 대신 `CodexManifestTest.test_codex_마켓플레이스가_플러그인_디렉터리를_가리킨다` 가 `source` 로 묶는다.

- [ ] **Step 7: 반증한다 — 검사가 실제로 잡는지 확인**

세 가지를 하나씩 깨뜨리고 매번 FAIL 을 확인한 뒤 원복한다. **원복은 Edit 도구의 정확한 old/new 쌍으로만 한다** — 파일 복사본으로 되돌리지 않는다 (과거에 스크래치패드의 동명 파일이 다른 내용을 덮어쓴 사고가 있었다).

| # | 깨뜨릴 것 | 기대 |
|---|---|---|
| F1 | `.codex-plugin/plugin.json` 의 `"version": "2.0.0"` → `"1.9.0"` | `test_모든_매니페스트의_버전이_같다` FAIL |
| F2 | `.codex-plugin/plugin.json` 에 `"commands": "./commands/"` 추가 | `test_codex_매니페스트에_commands_필드가_없다` FAIL |
| F3 | `.agents/plugins/marketplace.json` 의 `"url": "./plugins/gx-pm"` → `"./"` | `test_codex_마켓플레이스가_플러그인_디렉터리를_가리킨다` FAIL |

각 반증 후:
```bash
cd plugins/gx-pm && python -m unittest discover -s tests 2>&1 | tail -5
```
원복 후 마지막에 한 번 더 돌려 **87건 통과**(81 + 6)를 확인한다.

- [ ] **Step 8: Codex 에 실제로 등록되는지 확인한다 (실측)**

이 머신에 `codex-cli 0.130.0` 이 설치돼 있다. 만든 매니페스트가 파싱되는지 직접 본다.

```bash
cd /d/SQ/gx-pm/gx-pm && timeout 60 codex plugin marketplace add . < /dev/null 2>&1 | head -30
```

- **성공하면**: 출력을 그대로 갈무리해 둔다. Task 3 문서의 「실측」에 적는다.
- **실패하면**: 에러 메시지를 갈무리해 두고 **이 태스크를 막지 않는다.** `policy`·`category` 열거값이 원인일 가능성이 높으므로 Task 3 문서의 「미검증」에 원문 그대로 남긴다. 매니페스트 파일 자체는 참조 구현과 같은 형태이므로 되돌리지 않는다.
- **60초 안에 끝나지 않으면**: TUI 를 띄우려는 것이다. 중단하고 "CLI 비대화 실행 불가" 로 기록한다.

이 단계는 **정보 수집이지 게이트가 아니다.** 어떤 결과가 나오든 Step 9 로 간다.

- [ ] **Step 9: README 디렉토리 트리에 반영한다**

저장소 루트 `README.md` 의 `## 디렉토리 구조` 트리에서 `plugins/gx-pm/` 아래 첫 항목 앞에 한 줄을 넣는다.

```
│   ├── .codex-plugin/                     # Codex 매니페스트 (commands 미지원)
```

`commands/ # 16개 커맨드` 와 `skills/ # 26개 스킬` 주석의 숫자는 **바꾸지 않는다** — `test_README_디렉토리_트리의_개수가_실제와_같다` 가 실제 개수와 대조한다.

- [ ] **Step 10: CHANGELOG 에 적는다**

`plugins/gx-pm/CHANGELOG.md` 의 `## [Unreleased]` → `### Added` 아래에 붙인다.

```markdown
- **Codex 매니페스트를 이중화했다.** Codex CLI 는 Claude Code 의 플러그인 규격을
  채택했지만 매니페스트를 `.codex-plugin/plugin.json` 과 `.agents/plugins/marketplace.json`
  에서 읽고, `commands` 컴포넌트를 지원하지 않는다. 두 파일을 추가하고
  `CodexManifestTest` 6건으로 Claude 매니페스트와 묶었다. 버전은 3중으로 대조한다
  — `.agents/plugins/marketplace.json` 에는 version 필드가 없어 대신 `source` 가
  `plugins/gx-pm` 을 가리키는지 검사한다. 참조 구현(oh-my-gx)의 `url` 은 `"./"` 인데
  그쪽은 저장소 루트가 곧 플러그인 루트라서다 — 그대로 베끼면 등록이 실패한다.
```

- [ ] **Step 11: 커밋한다**

```bash
cd /d/SQ/gx-pm/gx-pm
git add plugins/gx-pm/.codex-plugin/plugin.json .agents/plugins/marketplace.json \
        plugins/gx-pm/tests/test_codex_compat.py \
        plugins/gx-pm/tests/test_plugin_consistency.py \
        plugins/gx-pm/CHANGELOG.md README.md
git commit -m "$(cat <<'EOF'
feat: Codex 매니페스트를 이중화하고 버전을 3중으로 대조한다

Codex CLI 는 .codex-plugin/plugin.json 과 .agents/plugins/marketplace.json 을
읽고 commands 컴포넌트를 지원하지 않는다. 두 매니페스트를 추가하고 Claude 쪽과
값으로 묶었다. .agents 쪽에는 version 이 없어 source 로 대신 묶는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
)"
```

---

### Task 2: 하네스 비호환 패턴 재발 방지

**Files:**
- Modify: `plugins/gx-pm/tests/helpers.py` (`runtime_docs()` 추가)
- Modify: `plugins/gx-pm/tests/test_codex_compat.py` (`HarnessCompatTest` 추가)
- Modify: `plugins/gx-pm/CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 이 만든 `test_codex_compat.py`, 기존 `helpers.doc_label(path) -> Path`
- Produces: `helpers.runtime_docs() -> list[tuple[Path, str]]` — `commands/`·`skills/`·`templates/` 아래 모든 `.md` 를 (경로, 본문) 쌍으로 반환. Task 3 은 이 함수를 쓰지 않는다.

**왜 이 태스크가 있는가:** oh-my-gx 는 이 세 패턴 때문에 27곳·44곳·17개를 고쳤다. gx-pm 은 지금 **전부 0건**이다. 나중에 고치는 비용이 지금 막는 비용보다 훨씬 크므로, 0건인 상태를 테스트로 묶는다.

---

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`plugins/gx-pm/tests/test_codex_compat.py` 끝에 붙인다. import 줄에 `re` 와 헬퍼 둘을 더한다.

```python
import json
import re
import unittest

from helpers import PLUGIN_ROOT, REPO_ROOT, doc_label, runtime_docs
```

```python
class HarnessCompatTest(unittest.TestCase):
    """Codex 호환을 유지하는 조건. 지금 0건인 것을 0건으로 묶는다.

    oh-my-gx 는 아래 세 패턴 때문에 27곳·44곳·17개를 고쳐야 했다. gx-pm 은
    처음부터 깨끗하므로 재발만 막으면 된다.

    검사 대상은 runtime_docs() — 런타임에 '지시'로 읽히는 문서뿐이다.
    read_docs() 를 쓰면 이 패턴을 *설명하는* 문서(CHANGELOG·docs/)가
    이 패턴을 *쓰는* 문서로 오인돼 실패한다.
    """

    def setUp(self):
        self.docs = runtime_docs()

    def test_절대경로_조립_변수를_쓰지_않는다(self):
        """${CLAUDE_PLUGIN_ROOT} 는 Codex 스킬 루트에서 설정된다는 보장이 없다.

        변수가 비면 플러그인이 아니라 작업 중인 프로젝트 루트를 뒤지다 파일을
        찾지 못한다. 파일 위치 기준 상대경로를 쓴다 — 파일 사이의 상대 위치는
        설치 위치와 무관하므로 두 하네스에서 모두 해석된다.
        """
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertNotIn(
                    "CLAUDE_PLUGIN_ROOT", text,
                    "절대경로 조립 변수가 들어왔습니다 "
                    "— 이 파일 위치 기준 상대경로로 바꾸세요",
                )

    def test_Skill_도구로_다른_스킬을_호출하지_않는다(self):
        """Codex 에는 Skill() 에 해당하는 도구가 없다.

        gx-pm 은 '**스킬명** 스킬로 …' 라는 산문 지시만 쓴다 — 그 형태는
        양쪽에서 같이 동작한다. 도구 호출 형태가 들어오는 순간 Codex 에서 죽는다.
        oh-my-gx 는 44곳을 '해당 SKILL.md 를 읽고 절차를 따른다' 로 옮겨야 했다.
        """
        패턴 = re.compile(r"\bSkill\s*\(")
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertEqual(
                    패턴.findall(text), [],
                    "Skill() 도구 호출이 들어왔습니다 "
                    "— '스킬명 스킬로 …' 산문 지시로 바꾸세요",
                )

    def test_Task_로_서브에이전트를_띄우지_않는다(self):
        """Codex plugin.json 에 agents 필드가 없어 에이전트 정의를 실을 수 없다.

        ~/.codex/agents/ 수동 배치도 0.130 에서 로드되지 않았다(노출 0건, 실측).
        gx-pm 은 서브에이전트를 쓰지 않으므로 이 제약에 걸리지 않는다 — 그 상태를
        유지한다. 들어오면 Codex 사용자에게는 그 단계가 통째로 사라진다.
        """
        패턴 = re.compile(r"\bTask\s*\(\s*(?:subagent_type|description|prompt)")
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertEqual(
                    패턴.findall(text), [],
                    "서브에이전트 디스패치가 들어왔습니다 "
                    "— Codex 는 agents 컴포넌트를 배포하지 못합니다",
                )
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -k HarnessCompatTest -v
```

기대: **ERROR** — `ImportError: cannot import name 'runtime_docs' from 'helpers'`

- [ ] **Step 3: `runtime_docs()` 를 만든다**

`plugins/gx-pm/tests/helpers.py` 의 `read_docs()` 함수 정의 **바로 뒤**에 붙인다.

```python
def runtime_docs() -> list[tuple[Path, str]]:
    """런타임에 '지시'로 읽히는 문서만 (경로, 본문) 쌍으로 반환한다.

    read_docs() 는 CHANGELOG·README·docs/ 까지 포함한다. 하네스 비호환 패턴
    검사는 그것들을 봐서는 안 된다 — 패턴을 *설명하는* 문서가 패턴을 *쓰는*
    문서로 오인돼 실패한다. 이 검사를 추가한 커밋의 CHANGELOG 항목이
    첫 희생자가 된다.

    커맨드·스킬·템플릿만 본다. 이 셋이 Claude 가 절차로 읽는 전부다.
    """
    docs = []
    for sub in ("commands", "skills", "templates"):
        for path in sorted((PLUGIN_ROOT / sub).rglob("*.md")):
            docs.append((path, path.read_text(encoding="utf-8")))
    return docs
```

- [ ] **Step 4: 테스트 통과를 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -k HarnessCompatTest -v
```

기대: **3건 PASS** (현재 코퍼스가 세 패턴 모두 0건이므로 바로 통과한다)

- [ ] **Step 5: 반증한다 — 세 검사가 각각 잡는지 확인**

세 검사는 지금 **아무것도 잡지 않는 상태에서 통과**한다. 반증 없이는 검사가 동작하는지 알 수 없다.

| # | 깨뜨릴 것 | 기대 |
|---|---|---|
| F1 | `skills/id-trace/SKILL.md` 아무 줄에 `${CLAUDE_PLUGIN_ROOT}/x.md` 삽입 | `test_절대경로_조립_변수를_쓰지_않는다` FAIL |
| F2 | 같은 파일에 `Skill(skill: "gx-pm:id-trace")` 삽입 | `test_Skill_도구로_다른_스킬을_호출하지_않는다` FAIL |
| F3 | 같은 파일에 `Task(subagent_type="explore")` 삽입 | `test_Task_로_서브에이전트를_띄우지_않는다` FAIL |

**추가 반증 F4 — 검사 범위가 맞는지.** `plugins/gx-pm/CHANGELOG.md` 에 `CLAUDE_PLUGIN_ROOT` 라는 낱말을 넣고 전체 테스트를 돌린다. **통과해야 한다.** 통과하지 않으면 `runtime_docs()` 의 범위가 잘못된 것이다 — Step 6 의 CHANGELOG 항목이 자기 검사에 걸린다.

각 반증 후 원복은 **Edit 도구의 정확한 old/new 쌍으로만** 한다. 마지막에 전체를 돌려 **90건 통과**(87 + 3)와 `git status` 가 의도한 파일만 보이는지 확인한다.

- [ ] **Step 6: CHANGELOG 에 적는다**

```markdown
- **하네스 비호환 패턴 3종의 재발을 막았다.** `${CLAUDE_PLUGIN_ROOT}` 절대경로
  조립, `Skill()` 상호 호출, `Task()` 서브에이전트 디스패치 — oh-my-gx 가 각각
  27곳·44곳·17개를 고쳐야 했던 것들이다. gx-pm 은 지금 전부 0건이므로 그 상태를
  `HarnessCompatTest` 3건으로 묶었다. 검사 범위는 커맨드·스킬·템플릿뿐이다
  (`helpers.runtime_docs()`) — 전체 문서를 보면 이 항목처럼 패턴을 설명하는
  글이 패턴을 쓰는 글로 오인된다.
```

- [ ] **Step 7: 커밋한다**

```bash
cd /d/SQ/gx-pm/gx-pm
git add plugins/gx-pm/tests/helpers.py plugins/gx-pm/tests/test_codex_compat.py \
        plugins/gx-pm/CHANGELOG.md
git commit -m "$(cat <<'EOF'
test: 하네스 비호환 패턴 3종이 0건인 상태를 묶는다

CLAUDE_PLUGIN_ROOT 절대경로 조립, Skill() 상호 호출, Task() 서브에이전트는
Codex 에서 동작하지 않는다. gx-pm 은 전부 0건이므로 재발만 막는다. 검사 범위는
커맨드·스킬·템플릿 — 전체 문서를 보면 패턴을 설명하는 글이 걸린다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
)"
```

---

### Task 3: 커맨드-스킬 대조표

**Files:**
- Create: `plugins/gx-pm/docs/codex-harness.md`
- Modify: `plugins/gx-pm/tests/test_codex_compat.py` (`CodexCommandMapTest` 추가)
- Modify: `plugins/gx-pm/CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 이 만든 `test_codex_compat.py`, 기존 `helpers.command_names() -> set[str]`, `helpers.skill_names() -> set[str]`, `helpers.PLUGIN_ROOT`
- Produces: 없음 (마지막 태스크)

**왜 이 태스크가 있는가:** spec 「단계」의 3~5단계(커맨드를 스킬로 추출)를 착수할지 말지가 이 대조표에서 갈린다. spec 은 *"나머지 13개는 대응 스킬이 이미 1:1로 있는 경우가 많다 — 확인 후 래퍼만 남기면 된다"* 고 하는데, **실측하면 1:1 인 커맨드는 0개**다. 이 표가 그 사실의 근거가 된다.

**⚠ 이 문서는 기존 계약 테스트 6건의 검사 대상에 들어간다.** `helpers.read_docs()` 가 `PLUGIN_ROOT` 아래 모든 `.md` 를 훑기 때문이다. 아래를 지키지 않으면 다른 테스트가 깨진다.

| 규칙 | 위반하면 깨지는 테스트 |
|---|---|
| `` `이름` `` 뒤에 바로 `스킬` 이라는 낱말을 붙이지 않는다 (예: `` `pipeline-spec` 스킬 `` ✗). 아직 없는 스킬 이름이 그 형태로 들어가면 실존 검사에 걸린다 | `CrossReferenceTest.test_참조된_스킬이_모두_존재한다` |
| `` `/gx-…` `` 로 적는 커맨드는 실존하는 16개만 | `CrossReferenceTest.test_백틱으로_참조된_커맨드가_모두_존재한다` |
| `templates/…​.md` 로 적는 경로는 실존하는 것만 | `CrossReferenceTest.test_참조된_템플릿_경로가_모두_존재한다` |
| `skills/…/SKILL.md` 로 적는 경로는 실존하는 것만 | `CrossReferenceTest.test_참조된_스킬_경로가_모두_존재한다` |
| `/pm-` 로 시작하는 문자열을 쓰지 않는다 | `LegacyReferenceTest.test_존재하지_않는_pm_커맨드를_안내하지_않는다` |
| `SCR-1`·`SC-1`·`SN-1` 형태의 예시 ID 를 쓰지 않는다 | `LegacyReferenceTest.test_예시_ID_가_네이밍_규칙을_따른다` |

---

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`plugins/gx-pm/tests/test_codex_compat.py` 끝에 붙인다. import 줄에 `command_names`, `skill_names` 를 더한다.

```python
from helpers import (
    PLUGIN_ROOT,
    REPO_ROOT,
    command_names,
    doc_label,
    runtime_docs,
    skill_names,
)
```

```python
COMMAND_MAP = PLUGIN_ROOT / "docs" / "codex-harness.md"


class CodexCommandMapTest(unittest.TestCase):
    """대조표가 낡으면 커맨드 추출 견적이 조용히 틀려진다.

    이 표의 쓸모는 하나다 — '커맨드를 스킬로 추출하는 데 얼마나 드는가' 에
    답하는 것. 커맨드가 늘거나 줄거나, 커맨드가 부르는 스킬이 바뀌면 답이
    달라지는데 표는 그대로 남는다. 여기서 걸리게 한다.

    구조는 PrerequisiteRegistryTest 와 같다 — 정본 표에 전수가 실려 있고,
    없는 것도 실려 있지 않아야 한다.
    """

    def setUp(self):
        self.text = COMMAND_MAP.read_text(encoding="utf-8")
        self.표 = re.search(
            r"^## 커맨드 16 ↔ 스킬 26$(.*?)(?=^#{1,3} |\Z)",
            self.text, re.M | re.S,
        )
        self.assertIsNotNone(
            self.표, "'## 커맨드 16 ↔ 스킬 26' 절을 찾지 못했습니다"
        )
        self.행 = re.findall(
            r"^\|\s*`/(gx-[가-힣A-Za-z-]+)`\s*\|([^|]*)\|",
            self.표.group(1), re.M,
        )
        self.실린커맨드 = {이름 for 이름, _ in self.행}

    def test_대조표가_비어있지_않다(self):
        """표 파싱이 조용히 실패하면 아래 두 검사가 공집합끼리 비교해 통과한다.

        (기존 An05ColumnSsotTest 가 같은 이유로 파싱 가드를 갖고 있다.)
        """
        self.assertGreater(len(self.행), 0, "대조표에서 커맨드 행을 하나도 찾지 못했습니다")

    def test_모든_커맨드가_대조표에_있다(self):
        self.assertEqual(
            command_names() - self.실린커맨드, set(),
            "대조표에 없는 커맨드가 있습니다 — 커맨드를 추가했다면 표에도 넣으세요",
        )

    def test_대조표에_없는_커맨드가_실려있지_않다(self):
        self.assertEqual(
            self.실린커맨드 - command_names(), set(),
            "존재하지 않는 커맨드가 대조표에 있습니다",
        )

    def test_대조표의_조립_스킬이_실제_커맨드에_있다(self):
        """'gx-요구사항정의서가 6개를 조립한다' 는 추출 견적의 근거다.

        커맨드 본문이 바뀌어 스킬이 빠져도 표는 그대로 남아, 견적만 조용히
        틀려진다. 개수 대신 이름을 대조해 그 드리프트를 잡는다.
        """
        실존스킬 = skill_names()
        for 이름, 스킬칸 in self.행:
            본문 = (PLUGIN_ROOT / "commands" / f"{이름}.md").read_text(encoding="utf-8")
            for 스킬 in re.findall(r"`([a-z][a-z0-9-]+)`", 스킬칸):
                with self.subTest(커맨드=이름, 스킬=스킬):
                    self.assertIn(스킬, 실존스킬, "존재하지 않는 스킬입니다")
                    self.assertIn(
                        f"**{스킬}**", 본문,
                        f"대조표는 {이름} 이 이 스킬을 조립한다고 하는데 "
                        "커맨드 본문에 없습니다",
                    )
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -k CodexCommandMapTest -v
```

기대: 4건 전부 **ERROR** — `FileNotFoundError: ...\docs\codex-harness.md`

- [ ] **Step 3: 대조표 문서를 만든다**

`plugins/gx-pm/docs/codex-harness.md` 를 아래 내용 그대로 만든다. 표의 값은 실측된 것이다 (`**스킬명**` 굵은 표기를 커맨드 본문에서 등장 순서대로 추출, `### Step N:` 개수, `### Step N: … [필수 중단점]` 개수).

````markdown
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

`AskUserQuestion` 은 31개 파일이 쓴다. `request_user_input` 이
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
- **`policy`·`category` 열거값.** `.agents/plugins/marketplace.json` 의
  `installation: AVAILABLE` · `authentication: ON_INSTALL` 과 `category: Developer Tools`
  는 참조 구현에서 옮긴 값이다. Codex 가 받는 값의 목록은 확인하지 않았다.
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
````

- [ ] **Step 4: 테스트 통과를 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -k CodexCommandMapTest -v
```

기대: **4건 PASS**

이어서 전체를 돌려 기존 계약 테스트가 새 문서 때문에 깨지지 않았는지 본다.

```bash
cd plugins/gx-pm && python -m unittest discover -s tests 2>&1 | tail -5
```

기대: **94건 통과** (90 + 4)

여기서 `CrossReferenceTest` 나 `LegacyReferenceTest` 가 실패하면 이 태스크 머리의
6줄짜리 규칙표를 위반한 것이다. 실패한 subTest 가 어느 낱말을 지목하는지 보고 고친다.

- [ ] **Step 5: 반증한다**

| # | 깨뜨릴 것 | 기대 |
|---|---|---|
| F1 | 대조표에서 `` | `/gx-감리대응` | `` 로 시작하는 행 하나를 통째로 지운다 | `test_모든_커맨드가_대조표에_있다` FAIL |
| F2 | `/gx-추적매트릭스` 행의 `` `id-trace` `` 를 `` `impact-analysis` `` 로 바꾼다 (실존 스킬이지만 그 커맨드는 부르지 않는다) | `test_대조표의_조립_스킬이_실제_커맨드에_있다` FAIL |
| F3 | `## 커맨드 16 ↔ 스킬 26` 제목을 `## 대조표` 로 바꾼다 | `setUp` 의 `assertIsNotNone` 이 4건 전부 FAIL |

F2 가 중요하다. **실존하는 스킬 이름을 넣어도 잡히는지**를 확인하는 것이다 —
이름 존재만 보는 검사였다면 F2 는 통과했을 것이고, 그러면 표가 조용히 낡는다.

원복은 Edit 도구의 정확한 old/new 쌍으로만 한다. 마지막에 전체 94건 통과와
`git status` 를 확인한다.

- [ ] **Step 6: CHANGELOG 에 적는다**

```markdown
- **커맨드-스킬 대조표를 만들었다** (`docs/codex-harness.md`). Codex 는 commands
  컴포넌트를 지원하지 않아 커맨드 16개가 실리지 않는다. 추출 비용을 재려고 전수를
  실측했더니 **1:1 로 대응하는 커맨드가 하나도 없었다** — 커맨드는 래퍼가 아니라
  평균 4.1개 스킬을 순서·중단점·승인 루프와 함께 엮는 조립 절차다. 설계 문서가
  "래퍼만 남기면 되는 경우가 많다" 고 본 3순위 13개는 조립 절차 13벌을 새로 쓰는
  작업이다. `CodexCommandMapTest` 4건이 표를 실제 커맨드에 결속한다.
```

- [ ] **Step 7: 커밋한다**

```bash
cd /d/SQ/gx-pm/gx-pm
git add plugins/gx-pm/docs/codex-harness.md plugins/gx-pm/tests/test_codex_compat.py \
        plugins/gx-pm/CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs: 커맨드-스킬 대조표로 Codex 추출 견적의 근거를 만든다

커맨드 16개를 전수 실측한 결과 1:1 로 대응하는 것이 하나도 없었다. 커맨드는
래퍼가 아니라 평균 4.1개 스킬을 엮는 조립 절차다. 표는 CodexCommandMapTest 4건이
실제 커맨드 본문에 결속한다 — 실존하는 스킬 이름을 잘못 넣어도 잡힌다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
)"
```

---

## 완료 기준

- [ ] `cd plugins/gx-pm && python -m unittest discover -s tests` → **94건 통과** (81 + 13)
- [ ] 신규 테스트 13건이 각각 반증을 거쳤다 (Task 1 F1~F3, Task 2 F1~F4, Task 3 F1~F3)
- [ ] `git status` 에 의도하지 않은 수정 파일이 없다 — 특히 `commands/`·`skills/`·`templates/` 아래 파일은 **한 건도** 수정돼 있으면 안 된다
- [ ] `docs/specs/2026-09-01-codex-compat-design.md` 가 미추적 상태 그대로다 (커밋되지 않았고 수정되지 않았다)
- [ ] Task 1 Step 8 의 `codex plugin marketplace add` 결과가 `docs/codex-harness.md` 에 기록됐다

## 이 계획이 하지 않는 것

- 커맨드 16개를 스킬로 추출하지 않는다 (spec 3~5단계)
- `templates/` 를 `skills/` 아래로 옮기지 않는다 (spec 6단계) — Task 3 이 기록하는
  Codex 배포 범위 실측 없이 하면 헛수고일 수 있다
- `utils/export-xlsx.py` 의 배포 문제를 풀지 않는다 — 같은 실측에 걸려 있다
- 기존 계약 테스트 21건을 손대지 않는다 — 추출 설계가 정해진 뒤의 일이다
