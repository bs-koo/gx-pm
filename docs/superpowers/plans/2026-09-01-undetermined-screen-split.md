# 화면 분리 미결정 감지 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 문서가 화면 분리를 말하지 않을 때 `generate-screen-list` 가 조용히 추정하는 대신, 정책을 한 번 묻고 그 답을 산출물에 남기게 한다.

**Architecture:** 새 커맨드도 새 스킬도 새 Step 도 만들지 않는다. 추정이 실제로 일어나는 한 지점(`skills/generate-screen-list/SKILL.md` Step 3, 화면 수 추론표 **직전**)에 미결정 판정·유형별 동작·정책 질문·기록 규칙을 넣고, 파이프라인 규약의 §이월 금지 항목에 4번으로 등록해 `/gx-spec` 이 이 중단점을 게이트로 미루지 못하게 한다. 검증은 실행이 아니라 **문서에 적힌 규칙의 형태**를 계약 테스트로 고정한다.

**Tech Stack:** 마크다운 스킬/커맨드/템플릿 문서, Python stdlib `unittest` (외부 의존성 없음)

**Spec:** `docs/superpowers/specs/2026-09-01-undetermined-screen-split-design.md`

## Global Constraints

- **새 커맨드·새 스킬을 만들지 않는다.** `VersionConsistencyTest` 가 README 배지·디렉터리 트리·설명문의 개수를 실제와 대조한다. 개수가 바뀌면 10개 지점을 함께 고쳐야 한다 — 이 작업의 범위가 아니다.
- **새 `### Step` 을 만들지 않는다.** 하위 구조가 필요하면 `#### 3-1` 형태의 4단계 헤딩을 쓴다.
- **`[필수 중단점]` 라벨을 새로 붙이지 않는다.** `test_파이프라인에_필수_중단점이_2개_있다` 와 `test_필수_중단점이_게이트_단계에만_붙어_있다` 가 `/gx-spec` 의 게이트를 정확히 2개(게이트 1·게이트 2)로 고정한다. 이월 금지 중단점은 기존 관례대로 산문("**여기서 중단한다**")으로 적는다.
- **문서·주석·테스트 함수명은 한국어.** 기존 `tests/test_plugin_consistency.py` 의 관례를 그대로 따른다.
- **테스트는 stdlib `unittest` 만 쓴다.** `pytest`·`hypothesis` 등 외부 의존성 금지.
- **절 단위로 검사한다.** 파일 전체 substring 검사는 금지 — v2.0.0 최종 리뷰가 그 방식으로 통과하는 구멍을 찾아냈다 (`test_파생_ID가_모두_재생성_파급_규칙에_있다` 의 docstring 참조).
- **모든 새 테스트는 반증을 확인한다.** 규칙을 일부러 깨뜨려 그 테스트만 실패하는지 보고 되돌린다. 반증을 못 하면 그 테스트는 아무것도 지키지 않는 것이다.
- **테스트 실행 명령**: `python -m unittest discover -s tests -q` — `D:\SQ\gx-pm\gx-pm\plugins\gx-pm` 에서 실행한다.
- **현재 브랜치 `feat/table-requirement-extraction` 에서 그대로 작업한다.** 새 워크트리·새 브랜치를 만들지 않는다.
- **테스트 수 기준선: 66.** Task 1 후 69, Task 2 후 71, Task 3 후 72, Task 4 후 72.

---

## 파일 구조

| 파일 | 책임 | 작업 |
|------|------|------|
| `skills/generate-screen-list/SKILL.md` | 미결정 판정·유형별 동작·정책 질문·기록 규칙의 **정본** | Task 1·2 에서 Step 3 에 삽입 |
| `templates/pipeline-protocol.md` | 이월 금지 항목의 **정본** | Task 3 에서 4번 항목 추가 |
| `commands/gx-spec.md` | 파이프라인이 이 중단점을 지킨다는 선언 | Task 3 |
| `commands/gx-화면목록표.md` | 단독 실행이 이 판정을 거친다는 선언 | Task 3 |
| `tests/test_plugin_consistency.py` | 위 규칙들의 형태를 고정 | Task 1·2·3 |
| `CHANGELOG.md` | `## [Unreleased]` 기록 | Task 4 |

**정본은 `skills/generate-screen-list/SKILL.md` 하나다.** 커맨드와 규약은 참조만 한다 — 규칙을 복제하면 PR #11 이 고친 것과 같은 결함(런타임에 커맨드만 읽고 스킬에 도달하지 못함)이 재발한다.

---

### Task 1: 미결정 판정 + 유형별 동작

**Files:**
- Modify: `plugins/gx-pm/skills/generate-screen-list/SKILL.md` — `### Step 3: 화면 식별 및 화면ID 부여` 절
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` — 새 클래스 `ScreenSplitRuleTest`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `skills/generate-screen-list/SKILL.md` Step 3 안에 두 개의 표 — 머리행이 `| 미결정이다 | 결정돼 있다 |` 인 2열 판정표, 그리고 머리행이 `| 유형 | 동작 | 근거 |` 이고 첫 칸이 `**A**`~`**D**` 인 3열 유형표. 테스트 클래스 `ScreenSplitRuleTest` 와 그 헬퍼 `_step3()` · `_표_행(머리조건)` — Task 2 가 같은 클래스에 메서드를 더한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_plugin_consistency.py` 의 `class BoundaryRuleTest` **바로 앞**에 새 클래스를 넣는다 (스킬 규칙 검사끼리 모이도록):

```python
class ScreenSplitRuleTest(unittest.TestCase):
    """화면 분리 미결정 규칙의 정본은 generate-screen-list/SKILL.md Step 3 다.

    문서가 화면 수를 말하지 않는데 추론표를 그냥 적용하면, 그 수가 화면ID가 되고
    pipeline-protocol.md §재생성 파급 규칙이 통째로 발동한다 — PG_·U_·TC_ 전건이
    나중에 재채번된다. 그래서 '추정 전에 판정한다' 는 규칙이 문서에 살아 있어야 한다.
    """

    def setUp(self):
        self.text = (
            PLUGIN_ROOT / "skills" / "generate-screen-list" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def _step3(self) -> str:
        구간 = re.search(r"^### Step 3:(.*?)(?=^### |\Z)", self.text, re.M | re.S)
        self.assertIsNotNone(
            구간,
            "generate-screen-list/SKILL.md 에서 '### Step 3:' 절을 찾지 못했습니다 "
            "— 절이 삭제됐거나 제목이 바뀌었습니다",
        )
        return 구간.group(1)

    def _표_행(self, 머리조건) -> list[list[str]]:
        """머리행 조건을 만족하는 표의 본문 행을 (구분선 제외) 반환한다."""
        줄들 = self._step3().splitlines()
        시작 = next(
            (
                i
                for i, l in enumerate(줄들)
                if l.strip().startswith("|") and 머리조건(l)
            ),
            None,
        )
        self.assertIsNotNone(시작, "표의 머리행을 찾지 못했습니다")
        행: list[list[str]] = []
        for l in 줄들[시작 + 1 :]:
            if not l.strip().startswith("|"):
                break
            칸 = [c.strip() for c in l.strip().strip("|").split("|")]
            if set("".join(칸)) <= set("-: "):
                continue  # 구분선
            행.append(칸)
        return 행

    def test_미결정_판정이_양쪽으로_나뉘어_있다(self):
        """한쪽만 있으면 판정이 아니라 목록이다.

        '미결정이다' 만 있으면 무엇이 결정된 것인지 알 수 없어 전건이 미결정이 되고,
        '결정돼 있다' 만 있으면 판정 자체가 사라진다.
        """
        행 = self._표_행(lambda l: "미결정이다" in l and "결정돼 있다" in l)
        self.assertGreaterEqual(
            len(행), 3,
            f"미결정 판정표의 본문 행이 3개 미만입니다: {len(행)}개",
        )
        for 왼, 오 in (r[:2] for r in 행):
            with self.subTest(행=왼[:20]):
                self.assertTrue(왼, "판정표 '미결정이다' 칸이 비어 있습니다")
                self.assertTrue(오, "판정표 '결정돼 있다' 칸이 비어 있습니다")

    def test_프로젝트_유형_네_가지의_동작이_모두_정의돼_있다(self):
        """A·B·C·D 중 하나라도 빠지면 그 유형은 규칙 없이 실행된다."""
        행 = self._표_행(lambda l: "유형" in l and "동작" in l and "근거" in l)
        유형들 = [r[0] for r in 행]
        for 유형 in ("A", "B", "C", "D"):
            with self.subTest(유형=유형):
                self.assertTrue(
                    any(f"**{유형}**" in v for v in 유형들),
                    f"유형 {유형} 의 동작이 정의돼 있지 않습니다: {유형들}",
                )

    def test_D_유형은_화면_분리를_묻지_않는다(self):
        """D(변경 관리)에서 화면 분리를 물으면 답에 따라 기존 화면ID가 바뀔 수 있다.

        화면ID가 바뀌면 PG_·U_·TC_ 전건이 재채번된다 — 운영 중 시스템의 변경 건에서
        그 파급은 변경 범위를 통째로 벗어난다.
        """
        행 = self._표_행(lambda l: "유형" in l and "동작" in l and "근거" in l)
        D행 = [r for r in 행 if "**D**" in r[0]]
        self.assertEqual(len(D행), 1, f"유형 D 행이 1개가 아닙니다: {len(D행)}개")
        self.assertIn(
            "묻지 않는다", D행[0][1],
            "D(변경 관리)가 화면 분리를 묻게 돼 있습니다 "
            f"— 기존 화면ID가 바뀌면 후속 산출물이 전부 재채번됩니다: {D행[0][1]!r}",
        )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest tests.test_plugin_consistency.ScreenSplitRuleTest -v`
Expected: 3건 모두 FAIL — `_표_행` 의 `assertIsNotNone(시작, ...)` 에서 "표의 머리행을 찾지 못했습니다"

- [ ] **Step 3: SKILL.md Step 3 에 판정표와 유형표를 넣는다**

`skills/generate-screen-list/SKILL.md` 의 `### Step 3: 화면 식별 및 화면ID 부여` 절에서, 아래 두 줄 **사이**에 삽입한다:

```markdown
기능ID 하나당 필요한 **화면 수를 추론**한다.

화면 수 추론 기준:
```

삽입할 내용 (`기능ID 하나당 필요한 **화면 수를 추론**한다.` 다음, `화면 수 추론 기준:` 앞):

````markdown
#### 3-1. 추정하기 전에, 결정돼 있는지 본다

아래의 화면 수 추론표는 **추정**이다. 추정하기 전에 문서가 실제로 답을 주는지 확인한다.

| 미결정이다 | 결정돼 있다 |
|---|---|
| 화면·UI 요구사항인데 화면 수를 셀 근거가 본문에 없다 | 화면명이 열거돼 있다 (목록·등록·상세 등) |
| "열린다 / 표시된다 / 이동한다" 만 있고, 그것이 같은 화면 안인지 밖인지 말하지 않는다 | 모달·팝업·탭·페이지라고 명시돼 있다 |
| 소스에 모달 프래그먼트·탭이 있는데 화면 단위 규정이 없다 | 기존 화면목록표에 같은 기능의 분리 기준이 있다 |
| 한 요구사항이 조회·입력·확인을 모두 포함하는데 그 경계를 말하지 않는다 | 화면 수가 본문에 숫자로 적혀 있다 |

**detect-alternatives** 는 여기서 아무것도 잡지 못한다. 그 스킬은 **말해진** 대안
(`1안`/`2안`, "또는", "검토 필요")을 찾는데, 이 경우는 문서가 **아무 말도 하지 않는** 것이다.

미결정인데 그냥 추론표를 적용하면, 그렇게 나온 수가 그대로 화면ID가 된다.
`templates/pipeline-protocol.md` 의 재생성 파급 규칙에 따라 `PG_`·`U_`·`TC_` 가 전부
화면ID에서 파생되므로, 나중에 화면 수를 정정하면 후속 산출물이 전건 재채번된다.

#### 3-2. 유형별로 다르게 다룬다

| 유형 | 동작 | 근거 |
|------|------|------|
| **A** 신규 구축 | 묻는다 | 화면 분리의 근거가 RFP 밖에 없다 |
| **B** 추가 개발 | 기존 화면목록표의 분리 기준을 따르고, 같은 기능이 없을 때만 묻는다 | 기존 체계와 어긋나면 한 산출물에 분리 기준이 두 벌 생긴다 |
| **C** 산출물 정비 | 묻는다 | 모달 프래그먼트·탭을 화면으로 셀지는 소스 파일 목록이 답하지 않는다 |
| **D** 변경 관리 | **묻지 않는다** | 기존 화면ID는 바뀌면 안 된다. 답에 따라 화면 수가 달라지면 변경 범위 밖에서 재채번이 일어난다 |

````

- [ ] **Step 4: 통과를 확인한다**

Run: `python -m unittest tests.test_plugin_consistency.ScreenSplitRuleTest -v`
Expected: 3건 PASS

Run: `python -m unittest discover -s tests -q`
Expected: `Ran 69 tests` / `OK`

- [ ] **Step 5: 반증한다 — 세 테스트가 실제로 무언가를 지키는지 확인**

각 반증마다 **그 테스트만** 실패하고 나머지는 통과해야 한다. 확인 후 즉시 되돌린다.

1. 판정표 머리행을 `| 미결정이다 |` 로 줄이고 각 행의 오른쪽 칸을 지운다
   → `test_미결정_판정이_양쪽으로_나뉘어_있다` 만 FAIL. 되돌린다.
2. 유형표에서 `| **C** 산출물 정비 | ... |` 행을 통째로 지운다
   → `test_프로젝트_유형_네_가지의_동작이_모두_정의돼_있다` 만 FAIL. 되돌린다.
3. 유형 D 행의 `**묻지 않는다**` 를 `묻는다` 로 바꾼다
   → `test_D_유형은_화면_분리를_묻지_않는다` 만 FAIL. 되돌린다.

세 반증이 모두 예상대로 실패하지 않으면 그 테스트는 아무것도 고정하지 못하는 것이다 — 테스트를 고친다.

Run (되돌린 후): `python -m unittest discover -s tests -q`
Expected: `Ran 69 tests` / `OK`

- [ ] **Step 6: 커밋**

```bash
git add plugins/gx-pm/skills/generate-screen-list/SKILL.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -m "feat: 화면 분리 미결정 판정과 유형별 동작을 generate-screen-list Step 3 에 정의

문서가 화면 수를 말하지 않는데 추론표를 그냥 적용하면 그 수가 화면ID가 되고
PG_·U_·TC_ 가 전부 거기서 파생된다. detect-alternatives 는 말해진 대안만 잡아
이 경우를 감지하지 못한다. 추정 전에 판정하고, D(변경 관리)에서는 묻지 않는다."
```

---

### Task 2: 정책 질문 1회 + 산출물 기록 + 재질문 금지

**Files:**
- Modify: `plugins/gx-pm/skills/generate-screen-list/SKILL.md` — Task 1 이 넣은 `#### 3-2` 다음
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` — `ScreenSplitRuleTest` 에 메서드 2개 추가

**Interfaces:**
- Consumes: Task 1 이 만든 `ScreenSplitRuleTest` 클래스와 그 `setUp` / `_step3()` / `_표_행(머리조건)` 헬퍼. `#### 3-1` · `#### 3-2` 가 이미 Step 3 안에 있다.
- Produces: 기록 표에 `` 해당 행의 `비고` 열 `` 형태의 행, 그리고 `화면 분리 기준:` 리터럴과 "이미 있으면 … 묻지 않는다" 규칙. Task 3 은 이 문자열들에 의존하지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`ScreenSplitRuleTest` 클래스 끝(`test_D_유형은_화면_분리를_묻지_않는다` 다음)에 추가한다:

```python
    def test_기록_규칙이_DE_03_의_실제_컬럼을_지목한다(self):
        """기록 규칙이 없는 컬럼을 지목하면 xlsx 추출에서 조용히 사라진다.

        화면 수의 근거는 감리 대상이고 xlsx 가 납품물이다. 규칙이 지목한 컬럼명과
        templates/DE-03-screen-list.md 의 컬럼 목록을 묶어 갈라질 수 없게 한다.
        """
        칸 = re.search(r"해당 행의 `([^`]+)` 열", self._step3())
        self.assertIsNotNone(
            칸,
            "기록 규칙에서 '해당 행의 `{컬럼}` 열' 표기를 Step 3 안에서 찾지 못했습니다 "
            "— 기록할 자리가 정의되지 않았습니다",
        )
        컬럼 = 칸.group(1)
        템플릿 = (
            PLUGIN_ROOT / "templates" / "DE-03-screen-list.md"
        ).read_text(encoding="utf-8")
        헤더 = re.findall(r"^\|\s*([^|]+?)\s*\|", 템플릿, re.M)
        self.assertIn(
            컬럼, 헤더,
            f"기록 규칙이 지목한 `{컬럼}` 이 DE-03 템플릿의 컬럼이 아닙니다 "
            "— 기록해도 xlsx 추출에서 사라집니다",
        )

    def test_이미_기록된_기준은_다시_묻지_않는다(self):
        """재질문 금지 규칙이 없으면 이어쓰기·재실행 때마다 같은 것을 다시 묻는다.

        B(추가 개발)와 D(변경 관리)가 기존 기준을 따른다는 §3-2 의 규정도
        '기록된 기준을 읽는다' 는 이 규칙 위에 서 있다.
        """
        step3 = self._step3()
        self.assertIn(
            "화면 분리 기준:", step3,
            "기록 형식 '화면 분리 기준:' 이 Step 3 에 없습니다",
        )
        self.assertRegex(
            step3, r"이미 있으면[^\n]*묻지 않는다",
            "재질문 금지 규칙이 없습니다 — 재실행 때마다 같은 것을 다시 묻게 됩니다",
        )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest tests.test_plugin_consistency.ScreenSplitRuleTest -v`
Expected: 새 2건 FAIL (`해당 행의 … 열` 표기 없음 / `화면 분리 기준:` 없음), Task 1 의 3건은 PASS

- [ ] **Step 3: SKILL.md 에 정책 질문과 기록 규칙을 넣는다**

Task 1 이 넣은 `#### 3-2` 유형표 **다음**, `화면 수 추론 기준:` **앞**에 삽입한다:

`````markdown
#### 3-3. 정책 하나로 한 번 묻는다 — 건별로 묻지 않는다

화면 분리 모호성은 건별로 갈리지 않고 **정책 하나로 뭉친다** — "모달을 화면으로 세는가"
가 UI 요구사항 전건에 똑같이 걸린다. UI 요구사항 20건에 질문 20개를 내면 파이프라인을
못 쓰게 된다. **AskUserQuestion 을 한 번만** 부른다.

선택지마다 **결과 화면 수를 양쪽 다 계산해서** 보여준다. 감당할 비용을 모르는 채로
고르게 하면 묻는 의미가 없다.

```
화면 분리 기준을 정해주세요. 요구사항 {N}건이 이 기준에 걸립니다.

  1. 모달·팝업·탭은 화면으로 세지 않는다      → 화면 {M1}개
  2. 모달·팝업은 별도 화면으로 센다            → 화면 {M2}개
  3. 건별로 정하겠다                            → {N}건을 하나씩 확인

⚠ 여기서 정한 화면 수가 그대로 화면ID가 되고,
   PG_·U_·TC_ 가 전부 여기서 파생됩니다. 나중에 바꾸면 후속 산출물이 전건 재채번됩니다.
```

3번을 고르면 그때만 건별로 묻는다. 기본은 1회다.

#### 3-4. 정한 기준을 산출물에 남긴다

답을 받고 잊으면 재실행 때 같은 것을 다시 묻고, 감리에서 화면 수의 근거를 댈 수 없다.
두 자리에 남기며, 각각 하는 일이 다르다.

| 자리 | 형식 | 하는 일 |
|------|------|--------|
| 화면목록표 표 위 인용줄 | `> 화면 분리 기준: {기준} ({확인일} 확인)` | 마크다운 정본에 남아 **detect-existing-artifact** 가 다음 실행 때 읽는다 |
| 해당 행의 `비고` 열 | `화면 분리: {요약} (미결정 확인)` | xlsx 로 나가는 컬럼이라 납품물에 근거가 남는다 |

인용줄(`>`)은 시트명이 되지 않는다 — `utils/export-xlsx.py` 의 `parse_markdown_tables()`
가 인용문·표·목록을 제목 후보에서 명시적으로 제외한다.

**재질문 금지**: 표 위 인용줄에 `화면 분리 기준:` 이 **이미 있으면** 그 기준을 그대로
적용하고 다시 묻지 않는다. §3-2 에서 B(추가 개발)와 D(변경 관리)가 "기존 기준을 따른다"
고 한 것이 성립하는 근거가 이 규칙이다.

`````

- [ ] **Step 4: 통과를 확인한다**

Run: `python -m unittest tests.test_plugin_consistency.ScreenSplitRuleTest -v`
Expected: 5건 PASS

Run: `python -m unittest discover -s tests -q`
Expected: `Ran 71 tests` / `OK`

- [ ] **Step 5: 반증한다**

각 반증마다 **그 테스트만** 실패해야 한다. 확인 후 즉시 되돌린다.

1. 기록 표에서 `` 해당 행의 `비고` 열 `` 을 `` 해당 행의 `결정근거` 열 `` 로 바꾼다 (`결정근거` 는 DE-03 에 없는 컬럼)
   → `test_기록_규칙이_DE_03_의_실제_컬럼을_지목한다` 만 FAIL. 되돌린다.
2. **재질문 금지** 문단을 통째로 지운다
   → `test_이미_기록된_기준은_다시_묻지_않는다` 만 FAIL. 되돌린다.

Run (되돌린 후): `python -m unittest discover -s tests -q`
Expected: `Ran 71 tests` / `OK`

- [ ] **Step 6: 커밋**

```bash
git add plugins/gx-pm/skills/generate-screen-list/SKILL.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -m "feat: 화면 분리 정책을 1회만 묻고 답을 산출물 두 자리에 기록

건별로 물으면 UI 요구사항 20건에 질문 20개가 된다. 모호성은 정책 하나로 뭉치므로
AskUserQuestion 을 한 번만 부르고 선택지별 화면 수를 양쪽 다 보여준다.
답은 표 위 인용줄(재실행이 읽는다)과 비고 열(xlsx 로 나간다)에 남기고,
이미 있으면 다시 묻지 않는다."
```

---

### Task 3: 파이프라인 결속 — 이월 금지 4번 + 두 커맨드

**Files:**
- Modify: `plugins/gx-pm/templates/pipeline-protocol.md` — `## 단독 실행 vs 파이프라인 실행` 표, `## 이월 금지 항목` 절, `## 중단 후 재개` 절
- Modify: `plugins/gx-pm/commands/gx-spec.md` — `### Step 3: 화면목록표 생성`
- Modify: `plugins/gx-pm/commands/gx-화면목록표.md` — `### Step 3: 화면목록표 생성`
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` — `PipelineProtocolTest` 에 메서드 1개 추가

**Interfaces:**
- Consumes: Task 1·2 가 `skills/generate-screen-list/SKILL.md` Step 3 에 넣은 규칙. 두 커맨드와 규약은 그 경로를 **참조만** 한다 — 규칙 문구를 복제하지 않는다.
- Produces: `templates/pipeline-protocol.md` §이월 금지 항목의 4번 항목. 기존 3개와 같은 `4. **이름** — 설명` 형태를 지킨다 (테스트가 `^\d+\. \*\*(.+?)\*\*` 로 센다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`PipelineProtocolTest` 의 `test_이월_금지_항목이_명시돼_있다` **바로 다음**에 추가한다:

```python
    def test_이월_금지_항목에_화면_분리_미결정이_있다(self):
        """§이월 금지 항목 **절 안에서만** 검사한다.

        파일 전체를 substring 으로 훑으면 §재생성 파급 규칙의 '화면ID' 표기가
        조건을 채워버려, 이 항목이 이월 금지 목록에서 통째로 빠져도 통과한다.
        빠지면 /gx-spec 이 이 중단점을 게이트 1 로 미뤄도 아무도 모른다 —
        그때는 화면ID가 이미 채번된 뒤라 되돌리는 비용이 전건 재채번이다.
        """
        구간 = re.search(
            r"^## 이월 금지 항목$(.*?)(?=^## |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(
            구간,
            "pipeline-protocol.md 에서 '## 이월 금지 항목' 절을 찾지 못했습니다 "
            "— 절이 삭제됐거나 제목이 바뀌었습니다",
        )
        절 = 구간.group(1)
        항목 = re.findall(r"^\d+\. \*\*(.+?)\*\*", 절, re.M)
        self.assertEqual(
            len(항목), 4,
            f"이월 금지 항목이 4개가 아닙니다: {항목}",
        )
        self.assertTrue(
            any("화면 분리" in v for v in 항목),
            f"'화면 분리' 미결정 중단점이 이월 금지 항목에 없습니다: {항목}",
        )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest tests.test_plugin_consistency.PipelineProtocolTest -v`
Expected: `test_이월_금지_항목에_화면_분리_미결정이_있다` FAIL — "이월 금지 항목이 4개가 아닙니다: ['시안/대안 감지 중단점', 'ID 확정 게이트', '입력 수집 중단점']"

- [ ] **Step 3: `templates/pipeline-protocol.md` 를 고친다**

(3-a) `## 단독 실행 vs 파이프라인 실행` 표에서 이 행 **바로 다음**에 새 행을 넣는다.

기존 행:

```markdown
| 시안/대안 감지 중단점 | 감지 시 중단 | **동일하게 중단** |
```

넣을 행:

```markdown
| 화면 분리 미결정 중단점 | 판정 시 중단 | **동일하게 중단** |
```

(3-b) `## 이월 금지 항목` 절의 첫 줄을 고친다.

이 줄을:

```markdown
다음 세 가지는 **절대 게이트로 미루지 않는다.**
```

이렇게 바꾼다:

```markdown
다음 네 가지는 **절대 게이트로 미루지 않는다.**
```

그리고 3번 항목 다음에 4번을 추가한다:

```markdown
4. **화면 분리 미결정 중단점** — 문서가 화면 수를 결정하지 않았는데 추정하면, 그렇게 나온 수가 그대로 화면ID가 되어 아래 §재생성 파급 규칙이 통째로 발동한다. `detect-alternatives` 는 **말해진** 대안만 잡으므로 이 경우를 감지하지 못한다. 판정 기준과 유형별 동작은 `skills/generate-screen-list/SKILL.md` Step 3 이 정본이다.
```

(3-c) `## 중단 후 재개` 절 끝에 한 문단을 추가한다:

```markdown
화면 분리 기준처럼 **사용자가 답한 결정**은 산출물 안에 남긴다
(`skills/generate-screen-list/SKILL.md` Step 3). 재개할 때 다시 묻지 않는 근거가 그 기록이다.
```

- [ ] **Step 4: `commands/gx-spec.md` Step 3 을 고친다**

이 절을:

```markdown
### Step 3: 화면목록표 생성

`/gx-화면목록표` 의 생성 단계를 수행한다.
화면 구성 대안(단일 화면 vs 별도 메뉴, 탭 vs 페이지 분리)이 감지되면 **여기서 중단한다**.
```

이렇게 바꾼다:

```markdown
### Step 3: 화면목록표 생성

`/gx-화면목록표` 의 생성 단계를 수행한다.
화면 구성 대안(단일 화면 vs 별도 메뉴, 탭 vs 페이지 분리)이 감지되면 **여기서 중단한다**.

문서가 화면 분리에 대해 **아무 말도 하지 않는** 경우도 **여기서 중단한다**.
판정은 `skills/generate-screen-list/SKILL.md` Step 3 을 따른다 — 대안 감지와 달리
이쪽은 문서에 단서가 없어 **detect-alternatives** 가 잡지 못한다.
게이트 1 로 이월하지 않는다: 게이트 1 은 화면ID가 이미 채번된 뒤다.
```

`### Step 3:` 제목 줄은 그대로 둔다. `[필수 중단점]` 라벨을 붙이지 않는다 — 그 라벨은 게이트 전용이고 `test_파이프라인에_필수_중단점이_2개_있다` 가 게이트를 2개로 고정한다. 위 Step 2 의 시안 중단점도 같은 이유로 산문으로만 적혀 있다.

- [ ] **Step 5: `commands/gx-화면목록표.md` Step 3 을 고친다**

이 절을:

```markdown
### Step 3: 화면목록표 생성

**generate-screen-list** 스킬 적용:
- 기능구분ID, 기능ID 부여
- 화면ID 자동 계산 ({기능ID}_{SN})
- 망구분 판별 (프로젝트 망 유형 기반)
```

이렇게 바꾼다:

```markdown
### Step 3: 화면목록표 생성

**generate-screen-list** 스킬 적용:
- **화면 분리 미결정 판정** — 문서가 화면 수를 결정하지 않았으면 화면ID를 채번하기 전에 기준을 묻고, 답을 산출물에 남긴다. 유형별 동작(A·C 묻는다 / B 기존 기준 / D 묻지 않는다)은 스킬 Step 3 이 정본이다
- 기능구분ID, 기능ID 부여
- 화면ID 자동 계산 ({기능ID}_{SN})
- 망구분 판별 (프로젝트 망 유형 기반)
```

- [ ] **Step 6: 통과와 회귀를 함께 확인한다**

Run: `python -m unittest tests.test_plugin_consistency.PipelineProtocolTest -v`
Expected: 4건 PASS

게이트 개수가 그대로인지 반드시 확인한다 — 이 태스크가 낼 수 있는 유일한 회귀다:

Run: `python -m unittest tests.test_plugin_consistency.PipelineCommandTest -v`
Expected: 5건 PASS, 특히 `test_파이프라인에_필수_중단점이_2개_있다` 와 `test_필수_중단점이_게이트_단계에만_붙어_있다`

Run: `python -m unittest discover -s tests -q`
Expected: `Ran 72 tests` / `OK`

- [ ] **Step 7: 반증한다**

1. `pipeline-protocol.md` 의 4번 항목을 §이월 금지 항목에서 잘라내 `## 게이트` 절 아래로 옮긴다 (파일 안에 문구는 그대로 남는다)
   → `test_이월_금지_항목에_화면_분리_미결정이_있다` 만 FAIL. 되돌린다.
   이것이 절 단위 검사가 파일 전체 substring 검사보다 강하다는 증거다.
2. `commands/gx-spec.md` 의 제목 줄을 `### Step 3: 화면목록표 생성 [필수 중단점]` 으로 바꾼다
   → `test_파이프라인에_필수_중단점이_2개_있다` 와 `test_필수_중단점이_게이트_단계에만_붙어_있다` 가 FAIL.
   **이것이 라벨을 붙이면 안 되는 이유의 증거다.** 되돌린다.

Run (되돌린 후): `python -m unittest discover -s tests -q`
Expected: `Ran 72 tests` / `OK`

- [ ] **Step 8: 커밋**

```bash
git add plugins/gx-pm/templates/pipeline-protocol.md plugins/gx-pm/commands/gx-spec.md plugins/gx-pm/commands/gx-화면목록표.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -m "feat: 화면 분리 미결정을 이월 금지 항목 4번으로 등록

게이트 1 은 화면ID가 이미 채번된 뒤라 이 결정을 거기로 미룰 수 없다.
파이프라인·단독 실행 양쪽이 스킬의 판정을 참조하게 하고(복제하지 않는다),
검사는 이월 금지 항목 절 안에서만 한다 — 파일 전체 substring 은
항목이 다른 절로 옮겨가도 통과한다."
```

---

### Task 4: CHANGELOG 기록

**Files:**
- Modify: `plugins/gx-pm/CHANGELOG.md` — `## [Unreleased]` 의 설명문 다음, 기존 `### Changed` 절 **앞**

**Interfaces:**
- Consumes: Task 1~3 의 결과 — 정본 경로(`skills/generate-screen-list/SKILL.md` Step 3)와 이월 금지 4번
- Produces: 없음 (마지막 태스크)

- [ ] **Step 1: `### Added` 절을 넣는다**

`## [Unreleased]` 아래 설명문 다음, 기존 `### Changed` 절 **앞**에 삽입한다:

```markdown
### Added

- **화면 분리가 결정돼 있지 않으면 묻는다.** `detect-alternatives` 는 **말해진** 대안
  (`1안`/`2안`, "또는", "검토 필요")만 잡는다. 문서가 화면 분리에 대해 **아무 말도 하지 않는**
  경우는 감지되지 않고, `generate-screen-list` 의 화면 수 추론표가 조용히 판정했다
  - 실측: 실제 요구사항서의 `FR-05 예약 화면` — "빈 슬롯을 클릭하면 예약 폼이 **열리고**"
    가 같은 화면의 모달인지 별도 화면인지 문서가 답하지 않는다. 읽는 방식에 따라
    **화면 1개 또는 3개**로 갈리고, 그 수가 그대로 화면ID가 된다
  - 화면ID는 ID 체인의 뿌리다. `PG_`·`U_`·`TC_` 가 전부 여기서 파생되므로,
    이 한 지점의 조용한 오추정이 나중에 정정되면 후속 산출물이 **전건 재채번**된다
  - 건별로 묻지 않는다 — 모호성은 "모달을 화면으로 세는가" 라는 **정책 하나로 뭉치므로**
    AskUserQuestion 을 1회만 부르고, 선택지별 결과 화면 수를 양쪽 다 계산해서 보여준다
  - 유형별로 다르다: A·C 는 묻고, B 는 기존 화면목록표의 기준을 따르며,
    **D(변경 관리)는 묻지 않는다** — 기존 화면ID가 바뀌면 변경 범위 밖에서 재채번이 일어난다
  - 답은 두 자리에 남는다. 표 위 인용줄은 마크다운 정본에 남아 재실행이 읽고,
    `비고` 열은 xlsx 로 나가 납품물에 근거가 남는다. 이미 있으면 다시 묻지 않는다
  - 이월 금지 항목 **4번**으로 등록했다. 게이트 1 은 화면ID가 이미 채번된 뒤라
    이 결정을 거기로 미룰 수 없다. 검사는 이월 금지 항목 **절 안에서만** 한다 —
    파일 전체 substring 검사는 항목이 다른 절로 옮겨가도 통과한다
  - 새 커맨드·새 스킬·새 Step 을 만들지 않았다. 추정이 실제로 일어나는 한 지점
    (`skills/generate-screen-list/SKILL.md` Step 3, 추론표 직전)에만 넣었다
```

- [ ] **Step 2: 전체 테스트를 돌린다**

CHANGELOG 는 `read_docs()` 대상이라 백틱 규약·개명 검사·정본 참조 검사를 함께 받는다.

Run: `python -m unittest discover -s tests -q`
Expected: `Ran 72 tests` / `OK`

- [ ] **Step 3: 커밋**

```bash
git add plugins/gx-pm/CHANGELOG.md
git commit -m "docs: CHANGELOG 에 화면 분리 미결정 감지 반영 (테스트 72)"
```

---

## 자체 점검

**1. 설계서 대응**

| 설계서 | 태스크 |
|--------|--------|
| §2.1 놓을 자리 (추론표 직전) | Task 1 Step 3 — 삽입 지점을 두 줄 사이로 명시 |
| §2.2 미결정 판정 | Task 1 |
| §2.3 유형별 동작 | Task 1 |
| §2.4 정책 하나로 묻는다 | Task 2 |
| §2.5 기록 두 자리 + 재질문 금지 | Task 2 |
| §2.6 파이프라인 결속 + 라벨 금지 | Task 3 |
| §3 검증 1·2 | Task 1 의 테스트 3건 |
| §3 검증 3 | Task 2 의 테스트 2건 |
| §3 검증 4 | Task 3 의 테스트 1건 |
| §3 회귀로 지켜야 하는 것 | Task 3 Step 6·7 |

빠진 요구사항 없음.

**2. 자리표시자 점검**

없음. 삽입할 마크다운 전문, 테스트 코드 전문, 커밋 메시지 전문이 실려 있다. 반증 절차도 "무엇을 어떻게 깨뜨려 어느 테스트가 실패해야 하는지" 까지 적혀 있다.

**3. 이름 일관성**

- `ScreenSplitRuleTest` — Task 1 이 만들고 Task 2 가 메서드를 더한다
- `_step3()` / `_표_행(머리조건)` — Task 1 이 정의, Task 2 의 `test_이미_기록된_기준은_다시_묻지_않는다` 가 `_step3()` 을 쓴다
- `PipelineProtocolTest` 의 `self.text` — 기존 `setUp` 이 `pipeline-protocol.md` 를 읽는다. Task 3 의 새 메서드가 그것을 그대로 쓴다
- 기록 리터럴 `화면 분리 기준:` — Task 2 의 SKILL.md 와 두 테스트가 같은 문자열을 쓴다
- 이월 금지 항목 이름 `화면 분리 미결정 중단점` — Task 3 의 규약과 테스트(`"화면 분리" in v`)가 맞는다
- 테스트 수 66 → 69 → 71 → 72 — 각 태스크의 Expected 와 Global Constraints 가 일치한다
