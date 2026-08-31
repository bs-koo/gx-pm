# gx-pm 파이프라인 커맨드 · `gx-` 접두 개명 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자가 커맨드 순서를 외우지 않아도 되도록 산출물 묶음 파이프라인 2종(`/gx-spec`·`/gx-testplan`)과 선행조건 레지스트리를 도입하고, 모든 커맨드에 `gx-` 접두를 부여한다.

**Architecture:** 세 축을 순서대로 쌓는다. 먼저 14개 커맨드를 `gx-` 접두로 개명하고(Task 1), 선행조건·파이프라인 규약을 템플릿 2종으로 정의한 뒤(Task 2), 개별 커맨드를 그 규약에 배선한다(Task 3). 그 위에 파이프라인 커맨드 2종을 올리고(Task 4·5), 프로젝트설정 Step 7 을 파이프라인 중심으로 다시 써서 16개 커맨드 전부가 사용자에게 도달 가능하게 만든다(Task 6). 마지막으로 매니페스트·문서를 v2.0.0 으로 맞춘다(Task 7).

**Tech Stack:** 마크다운 커맨드/스킬/템플릿 정의, Python 3.10 표준 `unittest` 계약 테스트, GitHub Actions CI

**Spec:** `docs/superpowers/specs/2026-08-31-gx-pipeline-commands-design.md`

## Global Constraints

- **커맨드 총 16개** — 개별 14 + 파이프라인 2. 스킬은 26개로 변하지 않는다.
- **파이프라인 이름은 `gx-spec` / `gx-testplan` 으로 고정.** `gx-design`·`gx-redesign` 은 다른 플러그인 스킬 이름이라 사용 금지.
- **구 커맨드 별칭을 만들지 않는다.** 14개 별칭은 자동완성을 두 배로 만들어 개명의 목적을 되돌린다.
- **버전은 1.5.1 → 2.0.0.** 매니페스트 4곳(`plugins/gx-pm/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md` 배지, `plugins/gx-pm/CHANGELOG.md` 최상단)이 전부 같아야 한다.
- **새 파이썬 의존성 금지.** 표준 `unittest` 만 쓴다 (`openpyxl` 은 기존 의존성이며 `export-xlsx.py` 전용).
- **`plugins/gx-pm/CHANGELOG.md` 의 기존 항목은 수정하지 않는다.** 과거 버전의 기록이므로 그 시점의 커맨드 이름이 그대로 남아야 한다. 새 항목만 최상단에 추가한다.
- **모든 문서는 한국어.** 커밋 메시지도 한국어.
- **테스트 실행 명령** (모든 Task 공통):
  ```bash
  cd plugins/gx-pm && python -m unittest discover -s tests -v
  ```
  Task 1 시작 시점 기준 38건이 통과한다. 각 Task 는 이 숫자를 줄이지 않는다.

---

## 파일 구조

| 파일 | 책임 | 다루는 Task |
|------|------|-----------|
| `plugins/gx-pm/commands/gx-*.md` (14) | 산출물 1종을 만드는 단독 커맨드 | 1, 3, 6 |
| `plugins/gx-pm/commands/gx-spec.md` | 명세 5종 파이프라인 | 4 |
| `plugins/gx-pm/commands/gx-testplan.md` | 테스트계획 4종 파이프라인 | 5 |
| `plugins/gx-pm/templates/prerequisites.md` | 커맨드별 하드/소프트 선행조건 **정본** | 2, 4, 5 |
| `plugins/gx-pm/templates/pipeline-protocol.md` | 단독/파이프라인 실행 차이, 재생성 파급 규칙 **정본** | 2 |
| `plugins/gx-pm/tests/test_plugin_consistency.py` | 계약 테스트 | 1, 2, 4, 5, 6 |
| `plugins/gx-pm/.claude-plugin/plugin.json` · `.claude-plugin/marketplace.json` · `README.md` · `plugins/gx-pm/CHANGELOG.md` | 버전·개수 표기 | 7 |

**정본 원칙**: 선행조건은 `prerequisites.md` 에만, 재생성 파급 규칙은 `pipeline-protocol.md` 에만 적는다. 커맨드 파일은 이들을 **참조**하고 값을 복제하지 않는다. `inspection-criteria.md` 가 검사기준 27개의 정본인 것과 같은 구조다.

---

## Task 1: `gx-` 접두 개명

**Files:**
- Rename: `plugins/gx-pm/commands/{14개}.md` → `plugins/gx-pm/commands/gx-{14개}.md`
- Modify: `plugins/gx-pm/` 아래 모든 `.md` 의 커맨드 참조 (`CHANGELOG.md` 제외)
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py`

**Interfaces:**
- Consumes: 없음 (첫 Task)
- Produces: 커맨드 이름 14종이 `gx-` 로 시작. 이후 모든 Task 는 `gx-요구사항정의서` 같은 새 이름만 쓴다. `helpers.command_names()` 의 반환값이 `{"gx-요구사항정의서", …}` 로 바뀐다.

- [ ] **Step 1: 개명 규칙 테스트를 먼저 쓴다 (실패해야 정상)**

`plugins/gx-pm/tests/test_plugin_consistency.py` 의 `class SkillFrontmatterTest` **바로 앞**에 아래 클래스를 삽입한다.

```python
class CommandNamingTest(unittest.TestCase):
    """커맨드는 자동완성에서 한 덩어리로 보여야 한다 (v2.0.0 개명)."""

    def test_모든_커맨드가_gx_접두를_쓴다(self):
        for name in sorted(command_names()):
            with self.subTest(커맨드=name):
                self.assertTrue(
                    name.startswith("gx-"),
                    "커맨드 파일명은 gx- 로 시작해야 합니다",
                )

    def test_gx_접두가_중복되지_않는다(self):
        for path, text in read_docs():
            with self.subTest(문서=path.relative_to(PLUGIN_ROOT)):
                self.assertNotIn(
                    "gx-gx-", text,
                    "일괄 치환이 두 번 적용됐습니다",
                )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.CommandNamingTest -v`
Expected: `test_모든_커맨드가_gx_접두를_쓴다` FAIL — 14개 subTest 전부 실패

- [ ] **Step 3: 커맨드 파일 14개를 `git mv` 로 개명한다**

```bash
cd plugins/gx-pm/commands
for f in 감리대응 결함관리대장 단위테스트계획서 시스템테스트 요구사항정의서 \
         인터페이스정의서 총괄테스트계획서 추적매트릭스 테스트결과서 테이블정의서 \
         통합테스트시나리오 프로그램정의서 프로젝트설정 화면목록표; do
  git mv "$f.md" "gx-$f.md"
done
ls
```
Expected: `gx-` 로 시작하는 14개 파일만 남는다.

- [ ] **Step 4: 문서 안의 커맨드 참조를 일괄 치환한다 (CHANGELOG 제외)**

```bash
cd plugins/gx-pm
for f in 감리대응 결함관리대장 단위테스트계획서 시스템테스트 요구사항정의서 \
         인터페이스정의서 총괄테스트계획서 추적매트릭스 테스트결과서 테이블정의서 \
         통합테스트시나리오 프로그램정의서 프로젝트설정 화면목록표; do
  find . -name '*.md' ! -name 'CHANGELOG.md' -not -path './.omc/*' \
    -exec sed -i "s|/$f|/gx-$f|g" {} +
done
grep -rn "gx-gx-" --include='*.md' . | head
```
Expected: `gx-gx-` 검색 결과 없음.

> **CHANGELOG 를 제외하는 이유**: 기존 항목은 v1.0~v1.5.1 시점의 기록이다. 그때의 커맨드 이름은 접두어가 없었고, 그것이 사실이다. 이력 문서를 소급 수정하면 "무엇이 언제 바뀌었는지" 가 사라진다.

- [ ] **Step 5: 백틱 커맨드 검사 정규식을 확장한다**

`test_백틱으로_참조된_커맨드가_모두_존재한다` 는 `` `/([가-힣]+)` `` 로 매칭해서 `gx-` 접두를 못 잡는다. 또한 Task 7 에서 CHANGELOG 에 넣을 개명 대응표가 구 이름을 백틱으로 인용하므로 `specs_only()` 를 적용해야 한다.

`CrossReferenceTest.setUp` 을 다음으로 교체한다:

```python
    def setUp(self):
        self.docs = read_docs()
        self.specs = specs_only(self.docs)
        self.skills = skill_names()
        self.commands = command_names()
        self.templates = template_names()
```

`test_백틱으로_참조된_커맨드가_모두_존재한다` 를 다음으로 교체한다:

```python
    def test_백틱으로_참조된_커맨드가_모두_존재한다(self):
        # CHANGELOG 는 개명 대응표에서 구 이름을 인용하므로 검사 대상에서 뺀다.
        for path, text in self.specs:
            for match in re.finditer(r"`/(gx-[가-힣A-Za-z-]+)`", text):
                with self.subTest(문서=path.relative_to(PLUGIN_ROOT), 커맨드=match.group(1)):
                    self.assertIn(match.group(1), self.commands)
```

`specs_only()` 함수 정의를 현재 위치(`LegacyReferenceTest` 바로 앞)에서 **`from helpers import (...)` 블록 바로 뒤**로 옮긴다. Task 1 Step 6 의 `CommandNamingTest` 를 포함해 여러 클래스가 쓰므로 맨 위에 있어야 읽는 순서가 맞는다. (런타임 해석이라 위치가 아래여도 동작은 하지만, 정의보다 앞선 참조가 3곳이 된다.)

- [ ] **Step 6: 접두어 없는 백틱 커맨드가 남지 않았는지 검사하는 테스트를 추가한다**

`CommandNamingTest` 안에 추가:

```python
    def test_접두어_없는_커맨드_참조가_남아있지_않다(self):
        구커맨드 = re.compile(r"`/(?!gx-)[가-힣]+`")
        for path, text in specs_only(read_docs()):
            with self.subTest(문서=path.relative_to(PLUGIN_ROOT)):
                남은것 = 구커맨드.findall(text)
                self.assertEqual(
                    남은것, [],
                    f"개명되지 않은 커맨드 참조: {남은것}",
                )
```

- [ ] **Step 7: 전체 테스트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 41 tests, OK (기존 38 + `CommandNamingTest` 3)

실패하면 대부분 Step 4 의 치환 누락이다. `grep -rn '`/[가-힣]' --include='*.md' plugins/gx-pm` 로 위치를 찾는다.

- [ ] **Step 8: 커밋**

```bash
git add -A plugins/gx-pm
git commit -m "refactor!: 커맨드 14종에 gx- 접두 부여

자동완성 목록에서 이 플러그인의 커맨드가 한 덩어리로 보이도록 개명.
CHANGELOG 의 과거 항목은 그 시점의 사실이므로 제외했다.

BREAKING CHANGE: /요구사항정의서 등 구 커맨드는 더 이상 동작하지 않는다."
```

---

## Task 2: 선행조건 레지스트리 · 파이프라인 규약 템플릿

**Files:**
- Create: `plugins/gx-pm/templates/prerequisites.md`
- Create: `plugins/gx-pm/templates/pipeline-protocol.md`
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py`

**Interfaces:**
- Consumes: Task 1 의 `gx-` 커맨드 이름
- Produces:
  - `templates/prerequisites.md` — 표의 첫 칸이 `` `/gx-커맨드명` `` 형식인 마크다운 표. 커맨드 파일이 `templates/prerequisites.md` 로 참조한다.
  - `templates/pipeline-protocol.md` — `## 이월 금지 항목`, `## 재생성 파급 규칙`, `## 중단 후 재개` 섹션을 가진다. 재생성 파급 규칙 표는 `PG_`·`U_`·`TC_` 를 모두 언급한다.
- 이 시점에는 파이프라인 커맨드가 아직 없으므로 `prerequisites.md` 는 **14행**이다. Task 4·5 가 각자 자기 행을 추가한다.

- [ ] **Step 1: 레지스트리 검사 테스트를 먼저 쓴다 (실패해야 정상)**

`test_plugin_consistency.py` 의 `class DocumentCodeTest` **앞**에 삽입:

```python
class PrerequisiteRegistryTest(unittest.TestCase):
    """선행조건은 templates/prerequisites.md 가 정본이다.

    커맨드를 추가하면서 선행조건 정의를 빠뜨리면 Step 0 검사가 비어버린다.
    """

    def setUp(self):
        self.text = (PLUGIN_ROOT / "templates" / "prerequisites.md").read_text(
            encoding="utf-8"
        )
        self.listed = set(re.findall(r"^\|\s*`/(gx-[가-힣A-Za-z-]+)`\s*\|", self.text, re.M))

    def test_모든_커맨드가_레지스트리에_있다(self):
        self.assertEqual(
            command_names() - self.listed, set(),
            "선행조건이 정의되지 않은 커맨드가 있습니다",
        )

    def test_레지스트리에_없는_커맨드가_실려있지_않다(self):
        self.assertEqual(
            self.listed - command_names(), set(),
            "존재하지 않는 커맨드가 레지스트리에 있습니다",
        )

    def test_하드와_소프트_구분이_정의돼_있다(self):
        self.assertIn("하드", self.text)
        self.assertIn("소프트", self.text)
        self.assertIn("진행 중단", self.text)


class PipelineProtocolTest(unittest.TestCase):
    """파이프라인 실행 규약은 templates/pipeline-protocol.md 가 정본이다."""

    def setUp(self):
        self.text = (PLUGIN_ROOT / "templates" / "pipeline-protocol.md").read_text(
            encoding="utf-8"
        )

    def test_이월_금지_항목이_명시돼_있다(self):
        self.assertIn("이월 금지", self.text)
        self.assertIn("시안", self.text)
        self.assertIn("화면ID", self.text)

    def test_파생_ID가_모두_재생성_파급_규칙에_있다(self):
        rules = (PLUGIN_ROOT / "templates" / "id-naming-rules.md").read_text(
            encoding="utf-8"
        )
        파생 = re.findall(r"\|\s*`(\w+_)`\s*\|[^|]*\|\s*\*\*화면ID", rules)
        self.assertEqual(
            set(파생), {"PG_", "U_", "TC_"},
            "id-naming-rules.md 의 화면ID 파생 목록이 바뀌었습니다",
        )
        for 접두 in 파생:
            with self.subTest(접두=접두):
                self.assertIn(접두, self.text)

    def test_중단_후_재개_규칙이_있다(self):
        self.assertIn("detect-existing-artifact", self.text)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.PrerequisiteRegistryTest tests.test_plugin_consistency.PipelineProtocolTest -v`
Expected: 전부 ERROR — `FileNotFoundError: templates/prerequisites.md`

- [ ] **Step 3: `templates/prerequisites.md` 를 만든다**

```markdown
# 선행조건 레지스트리

각 커맨드가 시작 전에 무엇을 갖고 있어야 하는지의 **정본**이다.
모든 커맨드는 Step 0 에서 이 표를 근거로 선행조건을 검사한다.
커맨드 파일은 이 값을 복제하지 않고 이 파일을 참조한다.

## 하드 / 소프트

| 구분 | 정의 | 없을 때의 동작 |
|------|------|--------------|
| **하드** | 없으면 산출물이 성립하지 않는다 | **진행 중단.** 선행 커맨드를 안내하고 종료한다 |
| **소프트** | 없어도 성립하지만 품질이 떨어진다 | 무엇이 빠지는지 알리고 **AskUserQuestion 으로 계속 여부를 확인**한다 |

> 소프트 선행이 없는 채로 만든 산출물은 저장 시 비고에 "축약 생성" 을 남긴다.
> 감리에서 "근거 없이 작성" 으로 지적되는 것을 막기 위해서다.

## 레지스트리

| 커맨드 | 하드 선행 | 소프트 선행 | 소프트가 없을 때 빠지는 것 |
|--------|----------|-----------|------------------------|
| `/gx-프로젝트설정` | — | — | — |
| `/gx-요구사항정의서` | 프로파일 | RFP/과업지시서 원문 | 제안요청ID(`SFR-`) 연결, 수용여부 근거 |
| `/gx-화면목록표` | 프로파일, 요구사항정의서 | 소스 인덱스(C유형) | 실제 화면과의 대조 |
| `/gx-프로그램정의서` | 프로파일, 화면목록표 | 소스 인덱스 | Controller/Service/DAO 실제 경로 |
| `/gx-인터페이스정의서` | 프로파일 | 소스 인덱스, 요구사항정의서 | 연동 요구사항ID 매핑 |
| `/gx-테이블정의서` | 프로파일 | DDL, 소스 인덱스 | 실제 컬럼 타입·제약 |
| `/gx-총괄테스트계획서` | 프로파일, 요구사항정의서 | 일정, 테스트 환경 정보 | 레벨별 일정, 환경 섹션 |
| `/gx-단위테스트계획서` | 프로파일, 화면목록표 | 총괄테스트계획서, 프로그램정의서 | 종료기준 연동, 프로그램ID 대조 |
| `/gx-통합테스트시나리오` | 프로파일, 요구사항정의서, 화면목록표 | 총괄테스트계획서 | 종료기준 연동 |
| `/gx-시스템테스트` | 프로파일, 요구사항정의서(비기능) | 총괄테스트계획서 | 종료기준 연동 |
| `/gx-추적매트릭스` | 프로파일, 요구사항정의서 | 화면목록표, 테스트 산출물 | 커버리지 판정 — 누락 유형 탐지 불가 |
| `/gx-테스트결과서` | 프로파일, 단위테스트계획서 **또는** 통합테스트시나리오 | 총괄테스트계획서, 결함관리대장 | 종료기준 판정, 부적합↔결함ID 연결 |
| `/gx-결함관리대장` | 프로파일 | 총괄테스트계획서 | 심각도·우선순위 기준 |
| `/gx-감리대응` | 프로파일 | 전 산출물 | 증빙 체크리스트 |

> `/gx-테스트결과서` 의 하드 선행은 **OR** 이다. 단위테스트 결과서(IM-03)와 통합테스트 결과서(TE-02)는
> 서로 다른 계획서에서 나오므로 둘 중 하나만 있으면 성립한다.

## Step 0 검사 문구

하드 선행이 없을 때:

```
{산출물명}을 만들려면 {선행 산출물}이 먼저 있어야 합니다.
`/gx-{선행커맨드}` 를 먼저 실행해 주세요.
```

소프트 선행이 없을 때 (AskUserQuestion):

```
{소프트 선행}이 없습니다. 이대로 진행하면 {빠지는 것}이 채워지지 않습니다.

  1. 그대로 진행 (비고에 "축약 생성" 표기)
  2. 중단하고 {소프트 선행}을 먼저 준비
```
```

- [ ] **Step 4: `templates/pipeline-protocol.md` 를 만든다**

```markdown
# 파이프라인 실행 규약

개별 커맨드는 **단독 실행**과 **파이프라인 실행**(`/gx-spec`·`/gx-testplan`) 두 경로를 가진다.
생성 로직은 동일하고, 차이는 **어디서 멈추느냐** 뿐이다.
파이프라인이 산출물 생성 로직을 복제하지 않는다.

## 단독 실행 vs 파이프라인 실행

| 단계 | 단독 실행 | 파이프라인 실행 |
|------|----------|---------------|
| Step 0 컨텍스트 로드 | 매번 수행 | 파이프라인이 1회 수행, 개별 커맨드는 생략 |
| 선행조건 검사 | 매번 수행 | 파이프라인이 묶음 단위로 1회 수행 |
| 시안/대안 감지 중단점 | 감지 시 중단 | **동일하게 중단** |
| 산출물 생성 | 수행 | 수행 |
| 산출물별 승인 루프 | 매번 중단 | **게이트로 이월** |
| xlsx 추출 질문 | 매번 질문 | 파이프라인 종료 시 1회 |
| "다음 제안" 출력 | 출력 | 생략 |

## 이월 금지 항목

다음 두 가지는 **절대 게이트로 미루지 않는다.**

1. **시안/대안 감지 중단점** — 시안 선택이 틀리면 뒤 산출물이 전부 틀린다.
2. **ID 확정 게이트** — 화면ID가 바뀌면 `PG_`·`U_`·`TC_` 가 전부 재채번된다.

## 게이트

게이트는 그 시점까지 만든 산출물을 **한꺼번에** 보여주고 AskUserQuestion 으로 승인을 받는다.
수정 요청이 오면 해당 산출물을 재생성하고, 아래 파급 규칙에 따라 **하위 산출물도 함께** 재생성한다.

## 재생성 파급 규칙

| 바뀐 것 | 함께 재생성해야 하는 것 |
|---------|--------------------|
| 요구사항ID | 화면목록표, 통합테스트시나리오, 시스템테스트, 추적매트릭스 |
| 화면ID | 프로그램정의서(`PG_`), 단위테스트계획서(`U_`), 테스트케이스(`TC_`) 전건 |
| 테이블·컬럼명 | 테이블정의서, 프로그램정의서의 DAO 항목 |
| 종료기준 (TE-01 §7) | 단위·통합·시스템 테스트계획서의 판정 기준 |

이 표는 `templates/id-naming-rules.md` 의 ID 체인에서 기계적으로 도출된 것이다.
새 파생 ID 유형이 생기면 두 파일을 **함께** 고친다.

## 중단 후 재개

파이프라인이 중간에 끊기면 이미 저장된 산출물은 **그대로 둔다.**
다음 실행 시 **detect-existing-artifact** 스킬이 감지하여 "이어서 진행" 을 제안한다.
파이프라인은 부분 재실행 플래그를 제공하지 않는다.
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 47 tests, OK (Task 1 의 41 + 신규 6)

- [ ] **Step 6: 커밋**

```bash
git add plugins/gx-pm/templates plugins/gx-pm/tests
git commit -m "feat: 선행조건 레지스트리·파이프라인 규약 템플릿 추가

선행조건은 prerequisites.md, 재생성 파급 규칙은 pipeline-protocol.md 가 정본.
커맨드 파일은 참조만 하고 값을 복제하지 않는다."
```

---

## Task 3: 개별 커맨드 14종 배선

**Files:**
- Modify: `plugins/gx-pm/commands/gx-*.md` 14개 전부
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py`

**Interfaces:**
- Consumes: Task 2 의 `templates/prerequisites.md`, `templates/pipeline-protocol.md`
- Produces: 모든 커맨드 파일이 (1) 상단 공통 규칙 인용문에 두 템플릿 참조를 포함하고, (2) Step 0 에 `## 선행조건` 검사를 두고, (3) 마지막 "다음 제안" 의 커맨드를 **백틱으로 감싼다**. Task 6 의 도달 가능성 테스트가 이 백틱에 의존한다.

> **일괄 작업이다.** 14개 파일에 같은 모양의 편집을 반복한다. 파일마다 다른 것은 선행조건 문구와 "다음 제안" 목록뿐이다.

- [ ] **Step 1: 배선 검사 테스트를 먼저 쓴다 (실패해야 정상)**

`test_plugin_consistency.py` 의 `class CommandStructureTest` 안에 추가:

```python
    def test_커맨드가_선행조건_템플릿을_참조한다(self):
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            if path.stem == "gx-프로젝트설정":
                continue  # 프로파일 자체를 만드는 커맨드라 선행조건이 없다
            with self.subTest(커맨드=path.stem):
                text = path.read_text(encoding="utf-8")
                self.assertIn("templates/prerequisites.md", text)

    def test_커맨드가_파이프라인_규약을_참조한다(self):
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            if path.stem == "gx-프로젝트설정":
                continue  # 파이프라인에 들어가지 않는다
            with self.subTest(커맨드=path.stem):
                text = path.read_text(encoding="utf-8")
                self.assertIn("templates/pipeline-protocol.md", text)

    def test_다음_제안의_커맨드가_백틱으로_감싸져_있다(self):
        맨커맨드 = re.compile(r"(?<![`/\w])/gx-[가-힣A-Za-z-]+")
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            # H1 제목(# /gx-... — 설명)은 예외
            본문 = "\n".join(
                line for line in text.splitlines() if not line.startswith("# /")
            )
            with self.subTest(커맨드=path.stem):
                self.assertEqual(
                    맨커맨드.findall(본문), [],
                    "백틱 없는 커맨드 참조가 있습니다 — 도달 가능성 검사가 놓칩니다",
                )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.CommandStructureTest -v`
Expected: 3건 FAIL. `test_다음_제안의_커맨드가_백틱으로_감싸져_있다` 는 `gx-요구사항정의서`, `gx-단위테스트계획서` 등에서 실패한다.

- [ ] **Step 3: 14개 커맨드의 상단 인용문에 템플릿 참조를 추가한다**

각 파일의 기존 인용문
```markdown
> **공통 규칙**: `templates/approval-protocol.md`의 승인 루프 프로토콜을 적용한다.
```
을 아래로 교체한다 (`gx-프로젝트설정` 은 `templates/prerequisites.md` 줄을 빼고, `gx-프로젝트설정` 은 `pipeline-protocol.md` 줄도 뺀다):

```markdown
> **공통 규칙**: `templates/approval-protocol.md`의 승인 루프 프로토콜을 적용한다.
> **선행조건**: `templates/prerequisites.md` 의 이 커맨드 행을 따른다.
> **파이프라인**: `/gx-spec` 또는 `/gx-testplan` 에서 호출된 경우 `templates/pipeline-protocol.md` 의 규약을 따른다.
```

- [ ] **Step 4: 각 커맨드 Step 0 에 선행조건 검사를 넣는다**

각 파일의 `### Step 0: 프로젝트 컨텍스트 로드` 안, `detect-existing-artifact` 문단 **뒤**에 삽입:

```markdown
**선행조건 검사** — `templates/prerequisites.md` 의 이 커맨드 행을 읽고:
- **하드 선행이 없으면**: 해당 선행 커맨드를 안내하고 **종료한다**. 추정으로 채우지 않는다.
- **소프트 선행이 없으면**: AskUserQuestion 으로 "그대로 진행 / 중단하고 준비" 를 묻는다.
  그대로 진행하면 산출물 비고에 "축약 생성" 을 남긴다.

파이프라인에서 호출된 경우 이 검사는 파이프라인이 이미 수행했으므로 **건너뛴다**.
```

`gx-프로젝트설정` 에는 이 블록을 넣지 않는다 (프로파일 자체를 만드는 커맨드다).

- [ ] **Step 5: 마지막 "다음 제안" Step 을 백틱으로 표준화한다**

각 파일의 마지막 Step (`### Step N: 다음 제안` 또는 `후속 조치 제안`) 본문에서 맨 커맨드를 백틱으로 감싼다.

변경 전 (`gx-요구사항정의서.md`):
```markdown
- "/gx-화면목록표 로 화면을 설계할까요?"
- "/gx-추적매트릭스 로 매핑을 확인할까요?"
```
변경 후:
```markdown
- "`/gx-화면목록표` 로 화면을 설계할까요?"
- "`/gx-추적매트릭스` 로 매핑을 확인할까요?"
```

같은 방식으로 처리할 파일과 위치:

| 파일 | 맨 커맨드가 있는 줄 |
|------|------------------|
| `gx-감리대응.md` | Step 7 본문의 `/gx-추적매트릭스` |
| `gx-결함관리대장.md` | Step 7 의 2줄 |
| `gx-단위테스트계획서.md` | Step 9 의 4줄 |
| `gx-시스템테스트.md` | Step 8 의 2줄 |
| `gx-요구사항정의서.md` | Step 6 의 2줄 |
| `gx-인터페이스정의서.md` | Step 6 의 1줄 |
| `gx-총괄테스트계획서.md` | Step 9 의 2줄 |
| `gx-추적매트릭스.md` | Step 5 |
| `gx-테스트결과서.md` | Step 8 |
| `gx-테이블정의서.md` | Step 5 |
| `gx-통합테스트시나리오.md` | Step 6 |
| `gx-프로그램정의서.md` | Step 6 |
| `gx-화면목록표.md` | Step 6 의 3줄 |
| `gx-프로젝트설정.md` | Step 7 (Task 6 에서 전면 재작성하므로 여기서는 백틱만 맞춘다) |

전수 확인:
```bash
cd plugins/gx-pm && grep -rnE "(^|[^\`/\w])/gx-" commands/ | grep -v "^commands/[^:]*:[0-9]*:# /gx-"
```
Expected: 결과 없음

- [ ] **Step 6: 전체 테스트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 50 tests, OK (Task 2 의 47 + 신규 3)

- [ ] **Step 7: 커밋**

```bash
git add plugins/gx-pm/commands plugins/gx-pm/tests
git commit -m "feat: 커맨드 14종에 선행조건 검사·파이프라인 규약 배선

Step 0 에서 하드/소프트 선행조건을 검사하고, 다음 제안의 커맨드를
백틱으로 표준화했다. 도달 가능성 검사가 이 백틱에 의존한다."
```

---

## Task 4: `/gx-spec` 명세 파이프라인

**Files:**
- Create: `plugins/gx-pm/commands/gx-spec.md`
- Modify: `plugins/gx-pm/templates/prerequisites.md` (레지스트리에 1행 추가)
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py`

**Interfaces:**
- Consumes: Task 2 의 두 템플릿, Task 3 이 배선한 개별 커맨드 5종
- Produces: 커맨드 `gx-spec`. `### Step N: … [필수 중단점` 형태의 게이트를 **정확히 2개** 가진다. 본문에서 5개 산출물 커맨드를 백틱으로 참조한다. Task 6 의 도달 가능성 테스트가 이 참조를 센다.

- [ ] **Step 1: 파이프라인 검사 테스트를 먼저 쓴다 (실패해야 정상)**

`test_plugin_consistency.py` 의 `class VersionConsistencyTest` **앞**에 삽입:

```python
PIPELINE_ARTIFACTS = {
    "gx-spec": [
        "gx-요구사항정의서",
        "gx-화면목록표",
        "gx-프로그램정의서",
        "gx-인터페이스정의서",
        "gx-테이블정의서",
    ],
    "gx-testplan": [
        "gx-총괄테스트계획서",
        "gx-단위테스트계획서",
        "gx-통합테스트시나리오",
        "gx-시스템테스트",
    ],
}


class PipelineCommandTest(unittest.TestCase):
    """파이프라인은 묶은 산출물을 빠짐없이 만들고, 게이트를 2개 유지해야 한다."""

    def _본문(self, 이름: str) -> str:
        return (PLUGIN_ROOT / "commands" / f"{이름}.md").read_text(encoding="utf-8")

    def test_파이프라인이_구성_산출물_커맨드를_모두_참조한다(self):
        for 이름, 산출물들 in PIPELINE_ARTIFACTS.items():
            if 이름 not in command_names():
                continue  # 아직 만들지 않은 파이프라인은 건너뛴다
            본문 = self._본문(이름)
            for 산출물 in 산출물들:
                with self.subTest(파이프라인=이름, 산출물=산출물):
                    self.assertIn(f"`/{산출물}`", 본문)

    def test_파이프라인에_필수_중단점이_2개_있다(self):
        for 이름 in PIPELINE_ARTIFACTS:
            if 이름 not in command_names():
                continue
            with self.subTest(파이프라인=이름):
                게이트 = re.findall(
                    r"^### Step \d+:.*\[필수 중단점", self._본문(이름), re.M
                )
                self.assertEqual(
                    len(게이트), 2,
                    f"게이트가 2개가 아닙니다: {게이트}",
                )

    def test_파이프라인이_규약_템플릿을_참조한다(self):
        for 이름 in PIPELINE_ARTIFACTS:
            if 이름 not in command_names():
                continue
            with self.subTest(파이프라인=이름):
                본문 = self._본문(이름)
                self.assertIn("templates/pipeline-protocol.md", 본문)
                self.assertIn("templates/prerequisites.md", 본문)
```

- [ ] **Step 2: 실패하지 않는 것을 확인한다 (아직 파이프라인이 없으므로 skip 조건으로 통과)**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.PipelineCommandTest -v`
Expected: 3 tests, OK — `command_names()` 에 `gx-spec` 도 `gx-testplan` 도 없어 세 테스트가 전부 빈 루프를 돈다. 파일을 만든 뒤에야 실제 검사가 걸린다.

> 통과하는 테스트로 시작하는 것이 TDD 절차 위반처럼 보이지만, 이 테스트의 실패 조건은 "파이프라인이 존재하는데 산출물을 빠뜨렸다" 이다. Step 3 에서 산출물 참조를 일부러 하나 빼고 돌려 FAIL 을 확인한 뒤 채우면 실패→통과 순서를 지킬 수 있다.

- [ ] **Step 3: `commands/gx-spec.md` 를 만든다**

````markdown
---
description: "명세 5종을 한 번에 만듭니다. 요구사항정의서 → 화면목록표 → 프로그램·인터페이스·테이블정의서를 게이트 2개로 확정. | 자연어: 설계 산출물 한번에, 명세 다 만들어줘, 처음부터 만들어줘, 산출물 쫙 뽑아줘"
argument-hint: "<RFP 텍스트 또는 파일>"
---

# /gx-spec — 명세 5종 일괄 생성

요구사항부터 테이블정의서까지, 서로 의존하는 명세 5종을 순서대로 만든다.
사용자는 커맨드 순서를 알 필요가 없다. **게이트 2곳에서만** 판단하면 된다.

> **공통 규칙**: `templates/approval-protocol.md`의 승인 루프 프로토콜을 적용한다.
> **선행조건**: `templates/prerequisites.md` 의 `/gx-spec` 행을 따른다.
> **실행 규약**: `templates/pipeline-protocol.md` 를 따른다. 개별 커맨드의 산출물별 승인 루프는 게이트로 이월하고, 시안/대안 감지 중단점은 이월하지 않는다.

## 만드는 것

| 순서 | 산출물 | 단독 커맨드 |
|------|--------|-----------|
| 1 | AN-02 요구사항정의서 | `/gx-요구사항정의서` |
| 2 | DE-03 화면목록표 | `/gx-화면목록표` |
| 3 | DE-05 프로그램정의서 | `/gx-프로그램정의서` |
| 4 | DE-04 인터페이스정의서 | `/gx-인터페이스정의서` |
| 5 | DE-08 테이블정의서 | `/gx-테이블정의서` |

낱개로 다시 만들고 싶으면 위 단독 커맨드를 쓴다. 생성 로직은 같다.

---

## 워크플로우

### Step 0: 프로젝트 컨텍스트 로드

**load-project-profile** 스킬로 활성 프로젝트를 확인한다. 프로파일이 없으면 `/gx-프로젝트설정` 을 먼저 실행하라고 안내 후 종료.

**detect-existing-artifact** 스킬로 5종 각각의 기존 파일을 확인한다.
- 일부만 있음 → "이미 만들어진 것을 건너뛰고 이어서 진행할까요?" 를 AskUserQuestion 으로 묻는다
- 전부 있음 → 어느 것부터 다시 만들지 묻는다

프로파일의 `type` 에 따라 각 산출물의 생성 방식이 분기한다 (A 정방향 / B 이어쓰기 / C 역생성 / D 변경분만).
분기 규칙은 각 단독 커맨드의 Step 0 정의를 그대로 따른다.

### Step 1: 묶음 선행조건 검사

`templates/prerequisites.md` 에서 5종 각각의 하드·소프트 선행을 읽어 **한 번에** 검사한다.

- 하드 선행 누락 → 안내 후 종료
- 소프트 선행 누락 → 무엇이 빠지는지 **한 화면에 모아** 보여주고 AskUserQuestion 으로 계속 여부를 묻는다

```
다음 입력이 없습니다:

  • RFP/과업지시서 원문 없음
      → 요구사항의 제안요청ID(SFR-) 연결과 수용여부 근거가 비어 있게 됩니다
  • DDL 없음
      → 테이블정의서의 컬럼 타입·제약이 추정값이 됩니다

  1. 그대로 진행 (해당 산출물 비고에 "축약 생성" 표기)
  2. 중단하고 입력을 준비
```

### Step 2: 요구사항정의서 생성

`/gx-요구사항정의서` 의 시안/대안 감지 → 추출 → 분류 → 우선순위 단계를 수행한다.
**시안이 감지되면 여기서 중단하고 선택을 받는다** (이월 금지).
산출물별 승인 루프는 게이트 1 로 이월한다.

### Step 3: 화면목록표 생성

`/gx-화면목록표` 의 생성 단계를 수행한다.
화면 구성 대안(단일 화면 vs 별도 메뉴, 탭 vs 페이지 분리)이 감지되면 **여기서 중단한다**.

### Step 4: 게이트 1 — ID 확정 [필수 중단점]

요구사항 {N}건과 화면 {M}건을 **함께** 출력한 후, **AskUserQuestion 도구**로 승인을 요청한다.

```
요구사항 {N}건 / 화면 {M}건을 확인해주세요.

⚠ 여기서 승인하면 화면ID가 확정됩니다.
   프로그램ID(PG_)·단위테스트ID(U_)·테스트케이스ID(TC_)가 전부 이 화면ID에서
   파생되므로, 나중에 화면ID를 바꾸면 후속 산출물이 전부 재채번됩니다.

주요 확인:
1. 요구사항 분류와 수용여부가 맞는지
2. 같은 페이지 영역이 별도 화면으로 분리되지 않았는지
3. 망구분(내부/외부)이 올바른지
4. 누락된 요구사항·화면이 있는지

승인하려면 '승인' 또는 'OK'를 입력하세요.
수정하려면 변경할 내용을 입력하세요.
```

수정 요청 시 `templates/pipeline-protocol.md` 의 **재생성 파급 규칙**을 적용한다.
요구사항ID가 바뀌면 화면목록표도 다시 만든다.

승인할 때까지 수정 → 재출력 → AskUserQuestion 을 반복한다.

### Step 5: 프로그램·인터페이스·테이블정의서 생성

세 산출물은 서로 의존하지 않으므로 순서가 자유롭다.

- `/gx-프로그램정의서` 의 생성 단계 — 화면ID에서 `PG_` 파생
- `/gx-인터페이스정의서` 의 생성 단계
- `/gx-테이블정의서` 의 생성 단계 — DDL 이 없으면 Step 1 에서 승인한 축약 생성

소프트 선행 없이 만든 산출물은 게이트 2 요약에 **"축약 생성"** 으로 표시한다.

### Step 6: 게이트 2 — 5종 일괄 검토 [필수 중단점]

5종 요약을 함께 출력한 후, **AskUserQuestion 도구**로 승인을 요청한다.

```
명세 5종을 확인해주세요.

  1. AN-02 요구사항정의서 — 기능 {N}건 / 비기능 {N}건
  2. DE-03 화면목록표 — 화면 {M}개
  3. DE-05 프로그램정의서 — 프로그램 {P}개
  4. DE-04 인터페이스정의서 — 인터페이스 {I}건   [축약 생성]
  5. DE-08 테이블정의서 — 테이블 {T}개

주요 확인:
1. 요구사항 ↔ 화면 매핑에 빠진 것이 없는지
2. 인터페이스가 요구사항과 연결되는지
3. 테이블이 프로그램의 DAO 와 맞는지

승인하려면 '승인' 또는 'OK'를 입력하세요.
수정할 산출물과 내용을 입력하세요. (예: "3번 프로그램정의서에 배치 2건 추가")
```

수정 시 재생성 파급 규칙을 적용한다. 화면ID가 바뀌면 프로그램정의서와 단위테스트계획서를 다시 만들어야 하므로, **화면ID 변경 요청은 게이트 1 로 되돌아간다.**

### Step 7: 결과 저장 + xlsx 추출

5종을 각각 `{시스템코드}-{산출물명}.md` 로 저장한다.

**AskUserQuestion 도구**로 한 번만 질문한다:

```
승인된 산출물 5종을 xlsx로 추출할까요?
  1. 5종 전부 xlsx 추출
  2. 일부만 추출 (산출물 번호 입력)
  3. 마크다운만 저장
```

### Step 8: 다음 안내

- "`/gx-testplan` 으로 테스트 계획 4종을 만들까요?"
- "`/gx-추적매트릭스` 로 요구사항 ↔ 화면 ↔ 프로그램 매핑을 검증할까요?"
````

- [ ] **Step 4: 선행조건 레지스트리에 `/gx-spec` 행을 추가한다**

`templates/prerequisites.md` 의 레지스트리 표 마지막(`/gx-감리대응` 행 뒤)에 추가:

```markdown
| `/gx-spec` | 프로파일 | RFP/과업지시서 원문, DDL, 소스 인덱스 | 묶은 5종 각 행과 동일 |
```

- [ ] **Step 5: 전체 테스트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 53 tests, OK (Task 3 의 50 + Step 1 에서 추가한 `PipelineCommandTest` 3건. 이제 그 3건이 `gx-spec` 을 실제로 검사한다)

`test_모든_스킬이_어느_커맨드에서든_호출된다` 가 실패하면 안 된다. `gx-spec` 이 스킬을 새로 도입하지 않기 때문이다.

- [ ] **Step 6: 커밋**

```bash
git add plugins/gx-pm/commands/gx-spec.md plugins/gx-pm/templates/prerequisites.md plugins/gx-pm/tests
git commit -m "feat: /gx-spec 명세 5종 파이프라인 추가

게이트 2개(화면ID 확정 · 5종 일괄 검토)로 사용자 판단 지점을 좁혔다.
생성 로직은 개별 커맨드를 참조하고 복제하지 않는다."
```

---

## Task 5: `/gx-testplan` 테스트계획 파이프라인

**Files:**
- Create: `plugins/gx-pm/commands/gx-testplan.md`
- Modify: `plugins/gx-pm/templates/prerequisites.md` (레지스트리에 1행 추가)

**Interfaces:**
- Consumes: Task 4 의 `PIPELINE_ARTIFACTS` 딕셔너리 (이미 `gx-testplan` 항목을 포함하고 있다), Task 2 의 두 템플릿
- Produces: 커맨드 `gx-testplan`. 게이트 정확히 2개. 4개 산출물 커맨드를 백틱으로 참조.

- [ ] **Step 1: 테스트가 `gx-testplan` 을 아직 건너뛰는 것을 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.PipelineCommandTest -v`
Expected: OK — `gx-testplan` 은 `command_names()` 에 없어 건너뛴다.

- [ ] **Step 2: `commands/gx-testplan.md` 를 만든다**

````markdown
---
description: "테스트 계획 4종을 한 번에 만듭니다. 총괄 테스트계획서로 종료기준을 확정하고 단위·통합·시스템 테스트를 일괄 생성. | 자연어: 테스트 계획 한번에, 테스트 준비 다 해줘, 시험 계획 쫙 만들어줘"
argument-hint: ""
---

# /gx-testplan — 테스트 계획 4종 일괄 생성

총괄 테스트계획서로 **종료기준을 먼저 확정**하고, 그 기준 위에 단위·통합·시스템 테스트를 세운다.
종료기준이 뒤에 오면 계획서마다 판정 기준이 어긋나 감리에서 "시험 절차 미준수" 로 지적된다.

> **공통 규칙**: `templates/approval-protocol.md`의 승인 루프 프로토콜을 적용한다.
> **선행조건**: `templates/prerequisites.md` 의 `/gx-testplan` 행을 따른다.
> **실행 규약**: `templates/pipeline-protocol.md` 를 따른다.

## 만드는 것

| 순서 | 산출물 | 단독 커맨드 | 검증 대상 |
|------|--------|-----------|----------|
| 1 | TE-01 총괄 테스트계획서 | `/gx-총괄테스트계획서` | 전 레벨 전략·종료기준 |
| 2 | DE-13 단위테스트계획서 | `/gx-단위테스트계획서` | 기능 (화면 단위) |
| 3 | DE-14 통합테스트시나리오 | `/gx-통합테스트시나리오` | 기능 (업무 흐름) |
| 4 | ST-01 시스템테스트 | `/gx-시스템테스트` | **비기능** |

---

## 워크플로우

### Step 0: 프로젝트 컨텍스트 로드

**load-project-profile** 스킬로 활성 프로젝트를 확인한다. 없으면 `/gx-프로젝트설정` 안내 후 종료.

**detect-existing-artifact** 스킬로 4종의 기존 파일을 확인하고, 일부만 있으면 이어서 진행할지 묻는다.

### Step 1: 묶음 선행조건 검사

`templates/prerequisites.md` 의 `/gx-testplan` 행을 따른다.

하드 선행이 없으면 안내 후 종료한다:

```
테스트 계획을 세우려면 요구사항정의서와 화면목록표가 먼저 있어야 합니다.
`/gx-spec` 으로 명세를 먼저 만들어 주세요.
```

**비기능 요구사항 건수를 여기서 센다.** 0건이면 경고한다:

```
⚠ 비기능 요구사항이 0건입니다.
   시스템테스트(ST-01)는 비기능 요구사항만 검증하므로 만들 것이 없습니다.
   요구사항정의서에 성능·보안·호환성·접근성 항목이 빠진 것은 아닌지 확인해 주세요.

  1. 그대로 진행 (시스템테스트 생략)
  2. 중단하고 `/gx-요구사항정의서` 로 비기능 요구사항을 보완
```

조용히 넘어가지 않는다. 비기능 요구사항 누락은 감리 지적 항목이다.

### Step 2: 총괄 테스트계획서 생성

`/gx-총괄테스트계획서` 의 생성 단계를 수행한다.
`templates/TE-01-master-test-plan.md` 의 9개 장을 채우되, **§7 진입기준/종료기준**을 가장 먼저 확정한다.

### Step 3: 게이트 1 — 종료기준 확정 [필수 중단점]

TE-01 의 §7 종료기준과 §8 결함 관리 기준을 출력한 후, **AskUserQuestion 도구**로 승인을 요청한다.

```
테스트 종료기준을 확인해주세요.

  계획 케이스 실행률     100%
  Critical 결함 잔존     0건
  Major 결함 잔존        0건
  Minor 결함 조치율      90% 이상
  요구사항 커버리지      100%
  적합률                 95% 이상

⚠ 여기서 확정한 종료기준이 IM-03·TE-02·ST-02·TE-06 판정의 유일한 근거가 됩니다.
   결과서의 수치가 이 기준과 어긋나면 감리에서 "시험 절차 미준수"로 지적됩니다.

주요 확인:
1. 제외 범위와 그 사유가 적혀 있는지
2. 결함 조치 예비기간이 일정에 있는지 (테스트 종료일 = 납기일이면 조치 시간이 0)
3. 인수테스트 수행자가 발주처 담당자 실명인지
4. 운영 데이터를 쓴다면 비식별 조치 방법이 명시됐는지

승인하려면 '승인' 또는 'OK'를 입력하세요.
수정하려면 변경할 내용을 입력하세요.
```

종료기준이 바뀌면 `templates/pipeline-protocol.md` 의 파급 규칙에 따라 뒤 3종의 판정 기준을 다시 맞춘다.

### Step 4: 단위·통합·시스템 테스트 생성

- `/gx-단위테스트계획서` — 화면별 DE-13 + **design-test-cases** 스킬로 테스트케이스 분해
- `/gx-통합테스트시나리오` — 업무 흐름별 DE-14, 예외 흐름은 별도 ID
- `/gx-시스템테스트` — 비기능 요구사항별 ST-01. Step 1 에서 0건으로 확인됐으면 **생략하고 그 사실을 게이트 2 에 적는다**

세 산출물의 판정 기준은 전부 Step 3 에서 확정한 종료기준을 인용한다. 별도로 정하지 않는다.

### Step 5: 게이트 2 — 4종 일괄 검토 [필수 중단점]

4종 요약을 함께 출력한 후, **AskUserQuestion 도구**로 승인을 요청한다.

```
테스트 계획 4종을 확인해주세요.

  1. TE-01 총괄 테스트계획서 — 레벨 4개, 종료기준 6항목
  2. DE-13 단위테스트계획서 — 단위테스트 {U}건 / 테스트케이스 {C}건
  3. DE-14 통합테스트시나리오 — 시나리오 {S}건 (정상 {N} / 예외 {E})
  4. ST-01 시스템테스트 — 측정 항목 {M}건        [비기능 0건으로 생략]

  요구사항 커버리지: 기능 {N}/{N}건, 비기능 {N}/{N}건

주요 확인:
1. 커버리지 100%인지 — 어느 테스트에도 연결되지 않은 요구사항이 있는지
2. 테스트케이스에 정상/경계/예외가 모두 있는지
3. 예외 흐름 시나리오가 정상 흐름과 별도 ID인지

승인하려면 '승인' 또는 'OK'를 입력하세요.
```

### Step 6: 결과 저장 + xlsx 추출

4종을 각각 저장하고, **AskUserQuestion 도구**로 한 번만 질문한다:

```
승인된 산출물 4종을 xlsx로 추출할까요?
  1. 4종 전부 xlsx 추출
  2. 일부만 추출 (산출물 번호 입력)
  3. 마크다운만 저장
```

### Step 7: 다음 안내

- "`/gx-테스트결과서` 로 수행 결과를 기입할까요?"
- "`/gx-결함관리대장` 으로 발견된 결함을 관리할까요?"
- "`/gx-추적매트릭스` 로 요구사항 커버리지를 검증할까요?"
````

- [ ] **Step 3: 선행조건 레지스트리에 `/gx-testplan` 행을 추가한다**

`templates/prerequisites.md` 의 `/gx-spec` 행 뒤에 추가:

```markdown
| `/gx-testplan` | 프로파일, 요구사항정의서, 화면목록표 | 일정, 테스트 환경 정보 | 총괄 테스트계획서의 일정·환경 섹션 |
```

- [ ] **Step 4: 전체 테스트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 53 tests, OK — 테스트 수는 그대로이고, `PipelineCommandTest` 가 이제 두 파이프라인을 모두 검사한다.

- [ ] **Step 5: 커밋**

```bash
git add plugins/gx-pm/commands/gx-testplan.md plugins/gx-pm/templates/prerequisites.md
git commit -m "feat: /gx-testplan 테스트 계획 4종 파이프라인 추가

게이트 1에서 종료기준을 먼저 확정해 뒤 3종의 판정 기준이 어긋나지 않게 했다.
비기능 요구사항 0건은 조용히 넘기지 않고 경고한다."
```

---

## Task 6: `/gx-프로젝트설정` Step 7 재작성 + 도달 가능성 테스트

**Files:**
- Modify: `plugins/gx-pm/commands/gx-프로젝트설정.md` (Step 7 전체 교체)
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py`

**Interfaces:**
- Consumes: Task 3 의 백틱 표준화, Task 4·5 의 파이프라인 커맨드
- Produces: 16개 커맨드 전부가 어느 커맨드 파일에서든 백틱으로 언급된다.

> v1.5.0 에서 추가한 `/gx-총괄테스트계획서`·`/gx-시스템테스트`·`/gx-결함관리대장` 은 Step 7 에 **한 번도 등장하지 않는다.** 기능은 있는데 사용자가 도달할 방법이 없다. 이 Task 가 그 구멍을 막고 재발을 테스트로 고정한다.

- [ ] **Step 1: 도달 가능성 테스트를 먼저 쓴다 (실패해야 정상)**

`test_plugin_consistency.py` 의 `CrossReferenceTest` 안, `test_모든_스킬이_어느_커맨드에서든_호출된다` **바로 뒤**에 추가:

```python
    def test_모든_커맨드가_사용자에게_도달_가능하다(self):
        """스킬 배선 검사의 대칭 짝.

        '참조된 커맨드가 존재하는가'만 검사하고 '존재하는 커맨드가 안내되는가'를
        검사하지 않으면, v1.5.0 처럼 발견 경로가 0인 커맨드가 생긴다.
        """
        도달가능 = set()
        for path in (PLUGIN_ROOT / "commands").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"`/(gx-[가-힣A-Za-z-]+)`", text):
                if match.group(1) != path.stem:  # 자기 자신은 제외
                    도달가능.add(match.group(1))
        self.assertEqual(
            self.commands - 도달가능, set(),
            "어느 커맨드에서도 안내되지 않는 커맨드가 있습니다 — 사용자가 도달할 수 없습니다",
        )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.CrossReferenceTest -v`
Expected: `test_모든_커맨드가_사용자에게_도달_가능하다` FAIL — 차집합에 `gx-감리대응`, `gx-spec`, `gx-testplan` 등이 나온다.

실제 차집합은 Task 3 의 백틱 표준화 결과에 따라 달라진다. 출력된 목록을 그대로 Step 3 의 확인 근거로 쓴다.

- [ ] **Step 3: `gx-프로젝트설정.md` 의 Step 7 을 교체한다**

기존:
```markdown
### Step 7: 다음 안내

유형에 따라 다음 단계를 안내한다.

유형에 따라 다음 커맨드를 텍스트로 안내한다:

- **A. 신규 구축**: `/gx-요구사항정의서`, `/gx-화면목록표`
- **B. 추가 개발**: `/gx-요구사항정의서` (이어쓰기), `/gx-화면목록표`
- **C. 산출물 정비**: `/gx-프로그램정의서`, `/gx-테이블정의서`, `/gx-인터페이스정의서`
- **D. 변경 관리**: `/gx-요구사항정의서`, `/gx-추적매트릭스`
```

교체:
````markdown
### Step 7: 다음 안내

유형에 따라 다음 단계를 텍스트로 안내한다.
**파이프라인을 1순위로 권한다.** 사용자가 커맨드 순서를 외우지 않아도 되는 것이 요점이다.

#### A. 신규 구축 / B. 추가 개발 / C. 산출물 정비

```
다음은 명세부터 만듭니다.

  1순위  `/gx-spec`      명세 5종 일괄 생성
                         요구사항 → 화면목록 → 프로그램·인터페이스·테이블
                         게이트 2곳에서만 확인하면 됩니다

  이어서  `/gx-testplan`  테스트 계획 4종 일괄 생성
                         총괄 → 단위 · 통합 · 시스템

낱개로 만들고 싶으면 산출물 이름을 그대로 부르세요:
  `/gx-요구사항정의서`  `/gx-화면목록표`  `/gx-프로그램정의서`
  `/gx-인터페이스정의서`  `/gx-테이블정의서`  `/gx-총괄테스트계획서`
  `/gx-단위테스트계획서`  `/gx-통합테스트시나리오`  `/gx-시스템테스트`
```

유형별 차이:
- **A. 신규 구축**: RFP 를 `/gx-spec` 에 그대로 넣는다
- **B. 추가 개발**: `/gx-spec` 이 기존 산출물을 감지해 **이어쓰기**로 동작한다
- **C. 산출물 정비**: `/gx-spec` 이 소스 인덱스·DDL 에서 **역생성**한다

#### D. 변경 관리

```
변경 관리는 영향받는 산출물만 골라서 고칩니다. 파이프라인을 쓰지 않습니다.

  1. `/gx-요구사항정의서`   변경 요구사항만 추가
  2. `/gx-추적매트릭스`     무엇이 영향받는지 확인
  3. 영향 산출물만 개별 커맨드로 갱신
```

#### 전 유형 공통 — 시험 수행 이후

```
  `/gx-테스트결과서`    수행 결과 기입, 종료기준 판정
  `/gx-결함관리대장`    결함 등록·상태 추적 (심각도·우선순위)
  `/gx-추적매트릭스`    요구사항 커버리지 검증
  `/gx-감리대응`        감리 지적사항 대응 문서 + 증빙 체크리스트
```
````

- [ ] **Step 4: 도달 가능성 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.CrossReferenceTest -v`
Expected: OK

차집합이 남으면 그 커맨드를 Step 7 의 해당 목록에 추가한다. 16개가 전부 등장해야 한다.

- [ ] **Step 5: 전체 테스트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 54 tests, OK (Task 5 의 53 + 신규 1)

`test_커맨드의_Step_번호가_중복되지_않는다` 가 실패하면 Step 7 교체 시 헤더를 중복 삽입한 것이다.

- [ ] **Step 6: 커밋**

```bash
git add plugins/gx-pm/commands/gx-프로젝트설정.md plugins/gx-pm/tests
git commit -m "fix: 프로젝트설정 Step 7 재작성 — 16개 커맨드 전부 도달 가능하게

v1.5.0 신규 3종(총괄테스트계획서·시스템테스트·결함관리대장)이 어디서도
안내되지 않아 발견 경로가 0이었다. 파이프라인 중심으로 다시 쓰고,
스킬 배선 검사와 대칭인 도달 가능성 테스트로 재발을 막는다."
```

---

## Task 7: 매니페스트·문서 v2.0.0

**Files:**
- Modify: `plugins/gx-pm/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`
- Modify: `plugins/gx-pm/CHANGELOG.md` (최상단에 새 항목 추가, 기존 항목은 불변)

**Interfaces:**
- Consumes: Task 1~6 의 결과 — 커맨드 16개, 스킬 26개
- Produces: 4개 매니페스트의 버전이 `2.0.0` 으로 일치하고, 개수 표기가 실제와 같다. `VersionConsistencyTest` 3건이 이를 검사한다.

- [ ] **Step 1: 현재 개수를 확인한다**

```bash
cd plugins/gx-pm && ls commands/*.md | wc -l && ls -d skills/*/ | wc -l
```
Expected: `16`, `26`

- [ ] **Step 2: `plugins/gx-pm/.claude-plugin/plugin.json` 을 고친다**

```json
  "description": "공공/SI PM의 AI 운영 체제 — 산출물 이름 한국어 커맨드 16개, 명세·테스트 묶음 파이프라인, 선행조건 자동 검사, 프로젝트 프로파일, 역방향 생성, xlsx 추출. 26개 스킬로 요구사항부터 테스트·결함관리·감리대응까지 자동화합니다.",
  "version": "2.0.0",
```

`keywords` 배열에 `"pipeline"` 을 추가한다.

- [ ] **Step 3: `.claude-plugin/marketplace.json` 을 고친다**

```json
  "metadata": {
    "description": "공공/SI PM의 AI 운영 체제 — /gx-spec 하나로 명세 5종, /gx-testplan 하나로 테스트 계획 4종. 커맨드 16개, 소스/DB 역생성, 감리대응 지원"
  },
```
`plugins[0].description` 은 `plugin.json` 의 `description` 과 같은 문자열로 맞추고, `plugins[0].version` 을 `"2.0.0"` 으로 바꾼다.

> `test_설명문의_스킬_커맨드_수가_실제와_같다` 는 두 description 에서 `(\d+)개 스킬` 과 `커맨드 (\d+)개` 를 각각 찾는다. **두 패턴이 모두 있어야 한다.** marketplace 의 `metadata.description` 은 검사 대상이 아니지만, `plugins[0].description` 은 검사 대상이다.

- [ ] **Step 4: `README.md` 를 고친다**

1. 배지 3줄:
```markdown
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)]()
[![Skills](https://img.shields.io/badge/skills-26-green.svg)]()
[![Commands](https://img.shields.io/badge/commands-16-orange.svg)]()
```

2. "이게 뭔가요?" 아래 v1.5.0 소개 문단 **앞**에 v2.0.0 문단을 추가:
```markdown
**v2.0.0 신규**: 커맨드 순서를 외우지 않아도 됩니다.
`/gx-spec` 하나로 명세 5종(요구사항·화면목록·프로그램·인터페이스·테이블)을,
`/gx-testplan` 하나로 테스트 계획 4종(총괄·단위·통합·시스템)을 만듭니다.
판단이 필요한 **게이트 2곳**에서만 멈춥니다.
모든 커맨드에 `gx-` 접두가 붙어 자동완성에서 한 덩어리로 보입니다.
```

3. 설치 안내의 `5. 프로젝트에서 /요구사항정의서 등 슬래시 커맨드로 사용` 을
   `5. 프로젝트에서 /gx-프로젝트설정 → /gx-spec 순으로 사용` 으로 바꾼다.

4. 커맨드 표(현재 87~100행)의 커맨드 이름에 `gx-` 를 붙이고, 표 **맨 위**에 파이프라인 2행을 추가:
```markdown
| "명세 다 만들어줘" | `/gx-spec` | **명세 5종 일괄 (게이트 2곳)** |
| "테스트 계획 다 만들어줘" | `/gx-testplan` | **테스트 계획 4종 일괄 (게이트 2곳)** |
```

5. 나머지 본문(147행 이후, 356행 이후, 368행 이후 표 포함)의 커맨드 참조에 `gx-` 를 붙인다:
```bash
for f in 감리대응 결함관리대장 단위테스트계획서 시스템테스트 요구사항정의서 \
         인터페이스정의서 총괄테스트계획서 추적매트릭스 테스트결과서 테이블정의서 \
         통합테스트시나리오 프로그램정의서 프로젝트설정 화면목록표; do
  sed -i "s|/$f|/gx-$f|g" README.md
done
grep -c "gx-gx-" README.md
```
Expected: `0`

- [ ] **Step 5: `plugins/gx-pm/CHANGELOG.md` 최상단에 v2.0.0 항목을 추가한다**

`# Changelog` 바로 아래, `## [1.5.1]` **앞**에 삽입한다. 기존 항목은 손대지 않는다.

````markdown
## [2.0.0] - 2026-08-31

사용자가 커맨드 순서를 외우고 있어야 했던 문제를 고쳤다.
산출물 사이의 선행 관계를 명시하고, 묶음 파이프라인 2종을 도입했다.

### Breaking

- **커맨드 14종 전부 `gx-` 접두로 개명.** 구 이름은 동작하지 않으며 별칭도 제공하지 않는다.

  | 구 이름 | 신 이름 |
  |---------|---------|
  | `/프로젝트설정` | `/gx-프로젝트설정` |
  | `/요구사항정의서` | `/gx-요구사항정의서` |
  | `/화면목록표` | `/gx-화면목록표` |
  | `/프로그램정의서` | `/gx-프로그램정의서` |
  | `/인터페이스정의서` | `/gx-인터페이스정의서` |
  | `/테이블정의서` | `/gx-테이블정의서` |
  | `/총괄테스트계획서` | `/gx-총괄테스트계획서` |
  | `/단위테스트계획서` | `/gx-단위테스트계획서` |
  | `/통합테스트시나리오` | `/gx-통합테스트시나리오` |
  | `/시스템테스트` | `/gx-시스템테스트` |
  | `/테스트결과서` | `/gx-테스트결과서` |
  | `/결함관리대장` | `/gx-결함관리대장` |
  | `/추적매트릭스` | `/gx-추적매트릭스` |
  | `/감리대응` | `/gx-감리대응` |

  `profile.json` 과 산출물 파일명은 영향받지 않는다. 기존 프로젝트 폴더는 그대로 열린다.

### Added

- **`/gx-spec`** — 명세 5종 일괄 생성 (요구사항 · 화면목록 · 프로그램 · 인터페이스 · 테이블).
  게이트 2곳: 화면ID 확정, 5종 일괄 검토
- **`/gx-testplan`** — 테스트 계획 4종 일괄 생성 (총괄 · 단위 · 통합 · 시스템).
  게이트 2곳: 종료기준 확정, 4종 일괄 검토
- **`templates/prerequisites.md`** — 커맨드별 하드/소프트 선행조건 정본.
  하드가 없으면 진행 중단, 소프트가 없으면 무엇이 빠지는지 알리고 계속 여부 확인
- **`templates/pipeline-protocol.md`** — 단독/파이프라인 실행 차이, 이월 금지 항목,
  재생성 파급 규칙(요구사항ID · 화면ID · 종료기준이 바뀌면 무엇을 다시 만드는지)
- 계약 테스트 16건 추가 (38 → 54) — `gx-` 접두 강제, 선행조건 레지스트리 완전성,
  파이프라인 게이트 수, **커맨드 도달 가능성**

### Fixed

- **`/gx-프로젝트설정` Step 7 이 v1.5.0 신규 커맨드 3종을 안내하지 않던 문제.**
  `/총괄테스트계획서`·`/시스템테스트`·`/결함관리대장` 은 기능이 있는데도
  어느 안내에도 등장하지 않아 발견 경로가 0이었다. Step 7 을 파이프라인 중심으로
  다시 쓰고, 16개 커맨드가 전부 도달 가능한지 테스트로 고정했다.
- `test_백틱으로_참조된_커맨드가_모두_존재한다` 의 정규식이 `gx-` 접두를
  매칭하지 못하던 문제
````

- [ ] **Step 6: 전체 테스트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 54 tests, OK (Task 7 은 테스트를 추가하지 않는다)

`test_모든_매니페스트의_버전이_같다` 가 실패하면 4곳 중 하나를 빠뜨린 것이다.
`test_README_배지가_실제_스킬_커맨드_수와_같다` 가 실패하면 배지 숫자가 16이 아니다.

- [ ] **Step 7: 커밋**

```bash
git add plugins/gx-pm/.claude-plugin/plugin.json .claude-plugin/marketplace.json README.md plugins/gx-pm/CHANGELOG.md
git commit -m "chore: v2.0.0 — 매니페스트·README·CHANGELOG 갱신

커맨드 16개(개별 14 + 파이프라인 2), 스킬 26개.
CHANGELOG 에 개명 대응표 14행 전문 게재."
```

---

## 완료 조건

- [ ] `cd plugins/gx-pm && python -m unittest discover -s tests -v` → **54 tests, OK**
      (38 → 41 → 47 → 50 → 53 → 53 → 54 → 54, Task 1~7 순)
- [ ] `ls plugins/gx-pm/commands/` → `gx-` 로 시작하는 16개 파일
- [ ] `grep -rn "gx-gx-" --include='*.md' .` → 결과 없음
- [ ] `grep -rnE "(^|[^\`/\w])/gx-" plugins/gx-pm/commands/ | grep -v ":# /gx-"` → 결과 없음
- [ ] 4개 매니페스트의 버전이 전부 `2.0.0`
- [ ] CI(`.github/workflows/test.yml`) 통과
