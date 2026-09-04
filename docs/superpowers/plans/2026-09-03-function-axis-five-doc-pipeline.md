# 기능 축 5종 산출물 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-pm 플러그인을 화면 축에서 기능 축으로 재정렬하여, RFP에서 요구사항정의서·기능명세서·테이블정의서·단위테스트계획서·추적매트릭스 5종을 개정이력과 함께 산출한다.

**Architecture:** 산출물의 정본은 `templates/*.md`이고, 생성 로직은 `skills/*/SKILL.md`, 진입점은 `commands/gx-*.md`, xlsx 변환은 `utils/export-xlsx.py`다. 문서 간 계약은 `tests/`의 Python unittest가 강제한다. 새 산출물을 먼저 세운 뒤(Task 1~8) 화면 축 산출물을 `archive/`로 내린다(Task 9).

**Tech Stack:** Markdown(스킬·커맨드·템플릿), Python 3.10 표준 `unittest`, `openpyxl`, `sqi-comn-term` MCP

**Spec:** `docs/superpowers/specs/2026-09-03-function-axis-three-doc-design.md`

## Global Constraints

- **테스트 실행 명령**: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
  단일 클래스: `cd plugins/gx-pm && python -m unittest tests.test_export_xlsx.MergeRangesTest -v`
- **Python 3.10** — CI가 3.10이다. `match` 문·3.11+ 문법 금지. `X | None` 타입은 이미 쓰고 있으므로 허용
- **새 의존성 금지** — `openpyxl` 외에 추가하지 않는다
- **문서는 한국어**, 커밋 메시지도 한국어 (`feat:` `fix:` `docs:` `refactor:` `test:` 접두 유지)
- **모든 커밋 메시지 끝에 아래 두 줄을 붙인다:**
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
  ```
- **ID 기본 채번**: 요구사항 `REQ-{3자리}` / 기능 `FN-{3자리}` / 테스트 `UT-{3자리}`. 프로파일에서 변경 가능하며 미설정 시 AskUserQuestion으로 묻는다
- **판정값**: 단위테스트 `결과`는 `Pass` / `Fail` 2값. 상태는 `신규`/`유지`/`변경`/`삭제`. 개정 사유는 `신규`/`추가`/`변경`/`삭제`/`보완`
- **표준용어 MCP 없이 컬럼명을 지어내지 않는다** — `sqi-comn-term`이 없으면 설치 안내 후 중단
- **작업 브랜치**: `feat/function-axis-five-doc`. main에 직접 커밋하지 않는다

---

## File Structure

| 파일 | 책임 |
|------|------|
| `templates/revision-history.md` | 개정이력 시트의 컬럼·트리거·버전 규칙 정본 (신설) |
| `templates/AN-02-requirements-definition.md` | 요구사항정의서 10컬럼 정본 |
| `templates/AN-03-function-spec.md` | 기능명세서 10컬럼 정본 (신설) |
| `templates/DE-08-table-definition.md` | 테이블정의서 15컬럼 정본 |
| `templates/DE-13-unit-test-plan.md` | 단위테스트계획서 11컬럼 정본 |
| `templates/AN-05-traceability-matrix.md` | 추적매트릭스 8컬럼 정본 |
| `templates/id-naming-rules.md` | 3단 ID 체인 정본 |
| `templates/pipeline-protocol.md` | 이월 금지 3항목·파급 규칙 정본 |
| `skills/manage-revision-history/SKILL.md` | 개정이력 행 생성 판정 (횡단, 신설) |
| `skills/generate-function-spec/SKILL.md` | AN-02 → AN-03 도출 (신설) |
| `skills/extract-requirements/SKILL.md` | RFP → AN-02 도출 |
| `skills/convert-ddl-to-tablespec/SKILL.md` | DDL + AN-03 → DE-08, MCP 표준 판정 |
| `skills/generate-unit-test-plan/SKILL.md` | AN-03 + DE-08 → DE-13 |
| `skills/trace-requirements/SKILL.md` | 5종 대조 → AN-05 |
| `utils/export-xlsx.py` | 마크다운 표 → xlsx. 컬럼 프로파일·세로 병합 |
| `tests/helpers.py` | 테스트 공용 헬퍼. `archive/` 제외, 컬럼 정본 파서 |
| `tests/test_export_xlsx.py` | 프로파일·병합·재배열 단위 테스트 |
| `tests/test_plugin_consistency.py` | 문서 간 계약 테스트 |
| `archive/` | 커맨드에서 내린 화면 축 산출물 보관 (계약 검사 제외) |

---

## Task 1: 개정이력 정본과 횡단 스킬

개정이력은 5종 전부가 참조하는 횡단 규칙이라 가장 먼저 세운다. 이게 없으면 이후 모든 산출물 스킬이 각자 개정이력 로직을 복제한다.

**Files:**
- Create: `plugins/gx-pm/templates/revision-history.md`
- Create: `plugins/gx-pm/skills/manage-revision-history/SKILL.md`
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (클래스 추가)

**Interfaces:**
- Produces: `templates/revision-history.md`의 `## 개정이력 컬럼 (정본)` 절 — Task 2가 export 프로파일을 여기에 맞춘다. `skills/manage-revision-history` — Task 3~7의 산출물 스킬이 이름으로 참조한다

- [ ] **Step 1: 실패하는 계약 테스트를 쓴다**

`plugins/gx-pm/tests/test_plugin_consistency.py` 끝의 `if __name__ == "__main__":` 바로 위에 추가한다.

```python
class RevisionHistoryTest(unittest.TestCase):
    """개정이력은 5종 공통 횡단 규칙이다.

    정본은 templates/revision-history.md 다. 산출물마다 규칙을 복제하면
    "언제 버전을 올리는가"가 다섯 갈래로 갈라진다.
    """

    def setUp(self):
        정본파일 = PLUGIN_ROOT / "templates" / "revision-history.md"
        self.assertTrue(정본파일.exists(), "개정이력 정본 템플릿이 없습니다")
        self.정본 = 정본파일.read_text(encoding="utf-8")

    def test_개정이력_컬럼_여섯_개가_정본에_있다(self):
        for 컬럼 in ["버전", "개정일", "개정 사유", "개정 내용", "작성자", "승인자"]:
            with self.subTest(컬럼=컬럼):
                self.assertIn(컬럼, self.정본)

    def test_개정_사유_다섯_값이_정본에_있다(self):
        for 값 in ["신규", "추가", "변경", "삭제", "보완"]:
            with self.subTest(사유=값):
                self.assertIn(f"`{값}`", self.정본)

    def test_행이_추가되지_않는_세_경우가_명시돼_있다(self):
        """이 셋을 빠뜨리면 게이트에서 고칠 때마다 버전이 올라간다."""
        for 표지 in ["승인 게이트 안에서의 수정", "다른 문서만 바뀐", "diff"]:
            with self.subTest(경우=표지):
                self.assertIn(표지, self.정본)

    def test_사유_우선순위가_명시돼_있다(self):
        self.assertIn("삭제` > `변경` > `추가` > `보완", self.정본)

    def test_횡단_스킬이_정본을_참조한다(self):
        스킬 = PLUGIN_ROOT / "skills" / "manage-revision-history" / "SKILL.md"
        self.assertTrue(스킬.exists(), "manage-revision-history 스킬이 없습니다")
        self.assertIn(
            "templates/revision-history.md",
            스킬.read_text(encoding="utf-8"),
            "스킬이 정본을 참조하지 않고 규칙을 복제하고 있습니다",
        )
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.RevisionHistoryTest -v`
Expected: FAIL — `AssertionError: False is not true : 개정이력 정본 템플릿이 없습니다`

- [ ] **Step 3: 정본 템플릿을 만든다**

`plugins/gx-pm/templates/revision-history.md`:

```markdown
# 개정이력 (5종 공통)

산출물 5종(AN-02·AN-03·DE-08·DE-13·AN-05) 모두 **첫 시트가 개정이력, 둘째 시트가 본문**이다.
이 파일이 개정이력 규칙의 단일 정본이다. 산출물 템플릿은 이 파일을 참조만 하고 복제하지 않는다.

## 개정이력 컬럼 (정본)

| # | 컬럼 | 값 규칙 |
|---|------|--------|
| 1 | 버전 | `1.0` 에서 시작, 개정마다 `+1.0`. 소수점 둘째 자리는 쓰지 않는다 |
| 2 | 개정일 | `YYYY.MM.DD` |
| 3 | 개정 사유 | `신규` / `추가` / `변경` / `삭제` / `보완` |
| 4 | 개정 내용 | 무엇이 몇 건 바뀌었는지. ID 를 병기한다 |
| 5 | 작성자 | 프로파일의 이름을 기본값으로 제시하고 확인받는다 |
| 6 | 승인자 | **자동으로 채우지 않는다.** 공란으로 두고 결재 후 사람이 기입한다 |

## 행이 추가되는 경우

| 트리거 | 개정 사유 | 개정 내용 자동 초안 |
|--------|----------|-------------------|
| 최초 생성 | `신규` | `최초 작성` |
| 항목이 늘어남 | `추가` | `요구사항 7건 추가` |
| 기존 항목의 내용이 바뀜 | `변경` | `요구사항 2건 변경(REQ-005, REQ-012)` |
| 항목이 삭제 상태로 전환 | `삭제` | `요구사항 1건 삭제(REQ-028)` |
| 오탈자·분류 정리 등 내용 무관 수정 | `보완` | `분류 체계 정리` |

여러 종류가 한 번에 일어나면 **행 하나에 합친다.** 사유는 가장 무거운 것을 쓴다:
`삭제` > `변경` > `추가` > `보완`.

## 행이 추가되지 않는 경우

- **승인 게이트 안에서의 수정** — 게이트에서 고쳐 재출력한 것은 확정 전이므로 개정이 아니다.
  파일 저장 시점에 1행만 만든다
- **다른 문서만 바뀐 경우** — AN-02 만 바뀌면 AN-03·DE-13 의 개정이력은 올라가지 않는다
- **파급 재생성 결과가 기존과 동일한 경우** — diff 가 0 이면 행을 만들지 않는다

## 버전은 문서마다 독립이다

AN-02 가 3.0 이어도 DE-13 은 1.0 일 수 있다. 파급으로 함께 재생성했더라도
내용이 안 바뀐 문서의 버전은 올리지 않는다.

## 마크다운 표현

산출물 마크다운 파일의 **맨 위**에 이 표를 둔다. `export-xlsx.py` 가 첫 시트로 만든다.

```
## 개정이력

| 버전 | 개정일 | 개정 사유 | 개정 내용 | 작성자 | 승인자 |
|------|--------|----------|----------|--------|--------|
| 1.0 | 2026.09.03 | 신규 | 최초 작성 | 구본승 | |
```
```

- [ ] **Step 4: 횡단 스킬을 만든다**

`plugins/gx-pm/skills/manage-revision-history/SKILL.md`:

```markdown
---
name: manage-revision-history
description: 산출물의 개정이력 행을 직전 버전과 대조하여 생성하고 사용자 승인을 받습니다. AN-02·AN-03·DE-08·DE-13·AN-05 공통으로 쓰입니다.
---

# 개정이력 관리 (manage-revision-history)

산출물을 저장하기 직전에 호출한다. 직전 버전과 대조해 개정이력 행 초안을 만들고
사용자 확인을 받는다.

**규칙의 정본은 `templates/revision-history.md` 다.** 이 스킬은 그 규칙을 실행하는 절차다.

## 입력

| 항목 | 필수 | 설명 |
|------|------|------|
| 산출물 종류 | Y | AN-02 / AN-03 / DE-08 / DE-13 / AN-05 |
| 직전 버전 파일 | N | 없으면 최초 생성으로 판정한다 |
| 현재 산출물 행 | Y | 저장하려는 내용 |
| 작성자 | N | 프로파일에서 로드. 없으면 묻는다 |

## 처리 절차

### Step 1: 최초 생성인지 판정

직전 버전 파일이 없으면 `1.0 / 신규 / 최초 작성` 한 행을 만들고 Step 4 로 간다.

### Step 2: 행 단위 대조

산출물의 **불변 키**로 대조한다.

| 산출물 | 불변 키 |
|--------|--------|
| AN-02 | 요구사항ID |
| AN-03 | 기능ID |
| DE-08 | 테이블명 + 컬럼명 |
| DE-13 | 테스트ID |
| AN-05 | 요구사항ID |

대조 결과를 네 갈래로 센다: 추가 / 변경 / 삭제 / 동일.

**동일이 전부면 행을 만들지 않는다.** "개정 없음" 을 안내하고 버전을 유지한다.

### Step 3: 개정 사유·내용 초안

`templates/revision-history.md` 의 트리거 표를 따른다. 사유는 가장 무거운 것을 쓴다.

```
개정이력에 추가할 행입니다.

| 2.0 | 2026.09.03 | 추가 | 요구사항 7건 추가, 2건 변경(REQ-005, REQ-012) | 구본승 | |

  1. 그대로 확정
  2. 개정 사유 변경 (신규/추가/변경/삭제/보완)
  3. 개정 내용 직접 수정
```

**AskUserQuestion 으로 묻는다.** `templates/approval-protocol.md` 의 인자 규칙을 따른다.

### Step 4: 산출물 맨 위에 기입

`## 개정이력` 표의 **마지막 행으로** 추가한다. 기존 행은 고치지 않는다.

## 주의사항

- 승인자 열은 비운다. 결재 전에 채우면 결재 사실을 위조하는 것이 된다
- 게이트에서 사용자가 수정하고 재출력한 것은 개정이 아니다 — 파일 저장 시점에 1회만 호출한다
- 파급으로 함께 재생성한 문서라도 diff 가 0 이면 호출하지 않는다
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.RevisionHistoryTest -v`
Expected: PASS (5 tests)

- [ ] **Step 6: 전체 테스트를 돌려 회귀를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: `test_모든_스킬이_어느_커맨드에서든_호출된다` FAIL — `manage-revision-history` 가 아직 어느 커맨드에서도 호출되지 않는다.

이 실패는 Task 3~7이 산출물 스킬에 참조를 넣으면서 해소된다. 지금은 그 테스트에 예외를 두지 말고, 다음 스텝에서 커맨드 한 곳을 먼저 연결한다.

- [ ] **Step 7: `/gx-요구사항정의서` 커맨드에 호출 지점을 넣는다**

`plugins/gx-pm/commands/gx-요구사항정의서.md` 의 마지막 Step(승인 후 저장) 바로 앞에 추가한다.

```markdown
### Step N: 개정이력 기록

**manage-revision-history** 스킬로 개정이력 행을 만든다.
직전 버전과 대조해 초안을 제시하고 사용자 확인을 받은 뒤 산출물 맨 위 `## 개정이력` 표에 추가한다.
diff 가 0 이면 행을 만들지 않고 버전을 유지한다.
```

기존 Step 번호와 겹치지 않게 마지막 번호 + 1 을 쓴다 (`test_커맨드의_Step_번호가_중복되지_않는다` 가 검사한다).

- [ ] **Step 8: 전체 테스트 통과 확인**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: PASS (전건)

- [ ] **Step 9: 커밋**

```bash
git checkout -b feat/function-axis-five-doc
git add plugins/gx-pm/templates/revision-history.md \
        plugins/gx-pm/skills/manage-revision-history/ \
        plugins/gx-pm/commands/gx-요구사항정의서.md \
        plugins/gx-pm/tests/test_plugin_consistency.py
git commit -m "feat: 개정이력을 5종 공통 횡단 규칙으로 세운다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

---

## Task 2: export-xlsx 세로 병합과 개정이력 시트

참조 양식은 `대분류`·`중분류`가 같은 값끼리 세로 병합돼 있고, 개정이력이 첫 시트다. 지금 `export-xlsx.py`는 둘 다 못 한다.

**Files:**
- Modify: `plugins/gx-pm/utils/export-xlsx.py`
- Test: `plugins/gx-pm/tests/test_export_xlsx.py` (클래스 추가)

**Interfaces:**
- Consumes: Task 1의 `templates/revision-history.md` 컬럼 6개
- Produces: `merge_ranges(rows, merge_columns) -> list[tuple[int, int, int]]` — `(0기준 열 인덱스, 시작 시트행, 끝 시트행)`. `DOCUMENT_PROFILES[*]["merge_columns"]` 키. `"개정이력"` 프로파일. Task 3~7이 이 프로파일에 컬럼 세트를 등록한다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`plugins/gx-pm/tests/test_export_xlsx.py` 의 `if __name__ == "__main__":` 바로 위에 추가한다.

```python
class MergeRangesTest(unittest.TestCase):
    """참조 양식은 대분류·중분류를 같은 값끼리 세로 병합한다.

    행 인덱스는 시트 기준이다. rows[0] 이 헤더라 시트 1행,
    rows[i] 는 시트 i+1 행이 된다.
    """

    def setUp(self):
        self.mod = load_export_module()

    def test_연속_동일값을_병합_범위로_묶는다(self):
        rows = [
            ["대분류", "중분류", "요구사항ID"],
            ["데이터 전처리", "상대평가기준", "REQ-001"],
            ["데이터 전처리", "상대평가기준", "REQ-002"],
            ["데이터 전처리", "달력맞춤", "REQ-004"],
        ]
        구간 = self.mod.merge_ranges(rows, ["대분류", "중분류"])
        self.assertIn((0, 2, 4), 구간, "대분류 3행이 하나로 묶여야 합니다")
        self.assertIn((1, 2, 3), 구간, "중분류 2행이 하나로 묶여야 합니다")

    def test_한_행짜리는_병합하지_않는다(self):
        rows = [["대분류", "중분류"], ["A", "x"], ["B", "y"]]
        self.assertEqual(self.mod.merge_ranges(rows, ["대분류", "중분류"]), [])

    def test_빈값은_병합하지_않는다(self):
        """빈칸이 이어지는 것은 같은 값이 아니라 값이 없는 것이다."""
        rows = [["대분류"], [""], [""], [""]]
        self.assertEqual(self.mod.merge_ranges(rows, ["대분류"]), [])

    def test_병합_대상이_아닌_컬럼은_묶지_않는다(self):
        rows = [["요구사항ID"], ["REQ-001"], ["REQ-001"]]
        self.assertEqual(self.mod.merge_ranges(rows, ["대분류"]), [])

    def test_헤더에_없는_병합_컬럼은_무시한다(self):
        rows = [["중분류"], ["A"], ["A"]]
        self.assertEqual(self.mod.merge_ranges(rows, ["대분류", "중분류"]), [(0, 2, 3)])

    def test_떨어진_동일값은_따로_묶는다(self):
        """정렬이 깨진 표를 억지로 이어 붙이면 없는 사실을 만든다."""
        rows = [["대분류"], ["A"], ["A"], ["B"], ["A"], ["A"]]
        구간 = self.mod.merge_ranges(rows, ["대분류"])
        self.assertEqual(sorted(구간), [(0, 2, 3), (0, 5, 6)])


class RevisionHistoryProfileTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()

    def test_개정이력_프로필이_있다(self):
        self.assertIn("개정이력", self.mod.DOCUMENT_PROFILES)

    def test_개정이력_컬럼_여섯_개가_순서대로다(self):
        컬럼 = self.mod.DOCUMENT_PROFILES["개정이력"]["columns"][0]
        self.assertEqual(
            컬럼,
            ["버전", "개정일", "개정 사유", "개정 내용", "작성자", "승인자"],
        )

    def test_모든_프로필이_merge_columns_키를_가진다(self):
        """병합 대상이 없는 산출물은 빈 리스트를 갖는다 — 키 자체가 없으면
        create_xlsx 가 KeyError 로 죽는다."""
        for 이름, 프로필 in self.mod.DOCUMENT_PROFILES.items():
            with self.subTest(산출물=이름):
                self.assertIn("merge_columns", 프로필)
                self.assertIsInstance(프로필["merge_columns"], list)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_export_xlsx.MergeRangesTest tests.test_export_xlsx.RevisionHistoryProfileTest -v`
Expected: FAIL — `AttributeError: module 'gx_export_xlsx' has no attribute 'merge_ranges'`

- [ ] **Step 3: `merge_ranges` 를 구현한다**

`plugins/gx-pm/utils/export-xlsx.py` 의 `_reorder_columns` 함수 바로 아래에 추가한다.

```python
def merge_ranges(
    rows: list[list[str]], merge_columns: list[str]
) -> list[tuple[int, int, int]]:
    """연속으로 같은 값이 이어지는 칸을 세로 병합 범위로 돌려준다.

    반환값은 (0기준 열 인덱스, 시작 시트행, 끝 시트행) 이다.
    rows[0] 이 헤더라 시트 1행이고, rows[i] 는 시트 i+1 행이다.

    빈 값은 묶지 않는다 — 빈칸이 이어지는 것은 "같은 값" 이 아니라 "값이 없는 것" 이다.
    떨어져 있는 같은 값도 묶지 않는다 — 정렬이 깨진 표를 이어 붙이면 없는 사실을 만든다.
    """
    if len(rows) < 3:  # 헤더 + 데이터 2행 미만이면 묶을 것이 없다
        return []

    header = [h.strip() for h in rows[0]]
    ranges: list[tuple[int, int, int]] = []

    for col_name in merge_columns:
        if col_name not in header:
            continue
        col = header.index(col_name)

        start = 1
        while start < len(rows):
            value = rows[start][col].strip() if col < len(rows[start]) else ""
            end = start
            while end + 1 < len(rows):
                nxt = rows[end + 1][col].strip() if col < len(rows[end + 1]) else ""
                if nxt != value:
                    break
                end += 1
            if value and end > start:
                ranges.append((col, start + 1, end + 1))
            start = end + 1

    return ranges
```

- [ ] **Step 4: 프로파일에 `merge_columns` 와 개정이력을 추가한다**

`DOCUMENT_PROFILES` 딕셔너리 맨 위에 개정이력 프로파일을 추가한다.

```python
    "개정이력": {
        "sheet_name": "개정이력",
        # 컬럼 정본은 templates/revision-history.md 의 「개정이력 컬럼 (정본)」 절이다.
        "columns": [[
            "버전", "개정일", "개정 사유", "개정 내용", "작성자", "승인자",
        ]],
        "merge_columns": [],
    },
```

그리고 **기존 모든 프로파일에 `"merge_columns": []` 를 추가한다.** 참조 양식이 병합하는
요구사항정의서만 값을 넣는다 (Task 3 에서 `["대분류", "중분류"]` 로 채운다).

- [ ] **Step 5: `create_xlsx` 가 병합을 적용하게 한다**

`create_xlsx` 의 2단계 루프에서 시트에 행을 다 쓴 뒤, 열 너비 조정 코드 앞에 추가한다.
아래 코드는 워크시트 변수명이 `ws` 이고 `rows` 가 재배열 후 행이라고 가정한다 —
넣기 전에 그 루프의 실제 변수명을 확인하고 맞춘다.

```bash
cd plugins/gx-pm && grep -n "create_sheet\|column_dimensions" utils/export-xlsx.py
```

```python
            # 연속 동일값 세로 병합 (참조 양식 형태)
            if doc_type and doc_type in DOCUMENT_PROFILES:
                for col, row_start, row_end in merge_ranges(
                    rows, DOCUMENT_PROFILES[doc_type].get("merge_columns", [])
                ):
                    letter = get_column_letter(col + 1)
                    ws.merge_cells(f"{letter}{row_start}:{letter}{row_end}")
                    ws[f"{letter}{row_start}"].alignment = Alignment(
                        wrap_text=True, vertical="center"
                    )
```

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: PASS (전건). `test_모든_프로필_컬럼이_문서에_존재한다` 는 Task 1 이 만든 `templates/revision-history.md` 가 개정이력 6컬럼을 전부 담고 있어 통과한다.

- [ ] **Step 7: 실제 xlsx 로 눈으로 확인한다**

```bash
cd plugins/gx-pm
cat > /tmp/샘플-요구사항정의서.md <<'MD'
## 개정이력

| 버전 | 개정일 | 개정 사유 | 개정 내용 | 작성자 | 승인자 |
|------|--------|----------|----------|--------|--------|
| 1.0 | 2026.09.03 | 신규 | 최초 작성 | 구본승 | |
MD
python utils/export-xlsx.py /tmp/샘플-요구사항정의서.md --output /tmp/샘플.xlsx
python -c "import openpyxl; wb=openpyxl.load_workbook('/tmp/샘플.xlsx'); print(wb.sheetnames)"
```
Expected: `['개정이력']`

- [ ] **Step 8: 커밋**

```bash
git add plugins/gx-pm/utils/export-xlsx.py plugins/gx-pm/tests/test_export_xlsx.py
git commit -m "feat: xlsx 추출에 개정이력 시트와 연속 동일값 세로 병합을 넣는다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

---

## Task 3: AN-02 요구사항정의서 컬럼 교체

`제안요청ID`·`구분`·`소분류`·`요구내역`·`수용여부`를 버리고 `번호`·`요구사항명`·`상태`·`변경 근거`를 넣는다.

**Files:**
- Modify: `plugins/gx-pm/templates/AN-02-requirements-definition.md`
- Modify: `plugins/gx-pm/skills/extract-requirements/SKILL.md`
- Modify: `plugins/gx-pm/utils/export-xlsx.py` (요구사항정의서 프로파일)
- Modify: `plugins/gx-pm/tests/helpers.py` (컬럼 정본 파서 추가)
- Test: `plugins/gx-pm/tests/test_export_xlsx.py`

**Interfaces:**
- Consumes: Task 2의 `merge_columns` 키
- Produces: `helpers.parse_column_ssot(template_name, section_title) -> list[str]` — Task 4~7이 재사용한다. AN-02 10컬럼 — Task 4가 `연계요구사항ID`로 참조한다

- [ ] **Step 1: 컬럼 정본 파서를 헬퍼에 넣는다**

`plugins/gx-pm/tests/helpers.py` 끝에 추가한다.

```python
def parse_column_ssot(template_name: str, section_title: str) -> list[str]:
    """템플릿의 지정 절에서 컬럼 정본 목록을 뽑는다.

    표는 `| # | 컬럼 | 규칙 |` 형태이고 둘째 칸이 컬럼명이다.
    절 제목은 정확히 일치해야 한다 — 제목이 바뀌면 조용히 빈 목록을 내는 대신
    호출부의 길이 검사가 실패하게 둔다.
    """
    import re

    text = (PLUGIN_ROOT / "templates" / template_name).read_text(encoding="utf-8")
    구간 = re.search(
        rf"^#{{1,4}} {re.escape(section_title)}$(.*?)(?=^#{{1,4}} |\Z)",
        text, re.M | re.S,
    )
    if 구간 is None:
        return []
    컬럼: list[str] = []
    for 줄 in 구간.group(1).splitlines():
        벗긴줄 = 줄.strip()
        if not (벗긴줄.startswith("|") and 벗긴줄.endswith("|")):
            continue
        칸 = [c.strip() for c in 벗긴줄.strip("|").split("|")]
        if len(칸) < 2 or set("".join(칸)) <= set("-: "):
            continue
        if 칸[0] == "#":
            continue  # 머리행
        컬럼.append(칸[1])
    return 컬럼
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`plugins/gx-pm/tests/test_export_xlsx.py` 상단 import 에 `parse_column_ssot` 를 추가하고, `if __name__` 앞에 클래스를 추가한다.

```python
class An02ColumnSsotTest(unittest.TestCase):
    """AN-02 컬럼 정본은 templates/AN-02-requirements-definition.md 다."""

    def setUp(self):
        self.mod = load_export_module()
        self.정본 = parse_column_ssot(
            "AN-02-requirements-definition.md", "본문 컬럼 (정본)"
        )

    def test_정본이_열_개다(self):
        self.assertEqual(
            len(self.정본), 10,
            f"AN-02 정본 컬럼이 10개가 아닙니다: {self.정본}",
        )

    def test_정본_순서가_참조_양식과_같다(self):
        self.assertEqual(self.정본, [
            "번호", "요구사항ID", "대분류", "중분류", "요구사항명",
            "요구사항 상세내용", "비고", "상태", "요구사항 근거", "변경 근거",
        ])

    def test_프로필이_정본과_같다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["요구사항정의서"]["columns"][0], self.정본
        )

    def test_분류_두_열이_병합_대상이다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["요구사항정의서"]["merge_columns"],
            ["대분류", "중분류"],
        )

    def test_폐기된_컬럼이_프로필에_남아있지_않다(self):
        프로필 = self.mod.DOCUMENT_PROFILES["요구사항정의서"]["columns"][0]
        for 폐기 in ["제안요청ID", "수용여부", "소분류", "요구내역"]:
            with self.subTest(컬럼=폐기):
                self.assertNotIn(폐기, 프로필)
```

- [ ] **Step 3: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_export_xlsx.An02ColumnSsotTest -v`
Expected: FAIL — `AN-02 정본 컬럼이 10개가 아닙니다: []` (절이 아직 없다)

- [ ] **Step 4: 템플릿을 교체한다**

`plugins/gx-pm/templates/AN-02-requirements-definition.md` 를 통째로 바꾼다.

```markdown
# AN-02 요구사항정의서 양식

## 파일 형식
Excel (.xlsx)

## 시트 구성
1. **개정이력** — 규칙의 정본은 `templates/revision-history.md`
2. **요구사항 명세** — 본문 데이터

## 본문 컬럼 (정본)

| # | 컬럼 | 값 규칙 |
|---|------|--------|
| 1 | 번호 | 1부터 순차. 재실행 시 재부여한다 (삭제 행 포함) |
| 2 | 요구사항ID | 프로파일 채번(기본 `REQ-001`). 한 번 부여하면 불변, 삭제해도 재사용 금지 |
| 3 | 대분류 | 업무 대분류. 연속 동일값은 xlsx 에서 세로 병합된다 |
| 4 | 중분류 | 대분류 안에서 유일해야 한다 |
| 5 | 요구사항명 | 25자 내외 명사구. 문장(`~한다`)으로 쓰지 않는다 |
| 6 | 요구사항 상세내용 | 원문 표현 유지. 조건·제약·수치는 버리지 않는다 |
| 7 | 비고 | 원문의 범위 한정·부연만 옮긴다 |
| 8 | 상태 | `신규` / `유지` / `변경` / `삭제` |
| 9 | 요구사항 근거 | `과업지시서` · `제안서` · `신규(YYYY.MM.DD)` |
| 10 | 변경 근거 | 상태가 `변경`·`삭제`일 때 필수 |

## 상태 판정 (재실행 시)

요구사항ID 를 키로 기존 산출물과 입력을 대조한다.

| 대조 결과 | 상태 | 추가 동작 |
|---|---|---|
| 입력에만 있음 | `신규` | 근거에 `신규(오늘)` 자동 기재 |
| 양쪽에 있고 요구사항명·상세내용 동일 | `유지` | |
| 양쪽에 있고 요구사항명·상세내용 다름 | `변경` | 변경 근거 입력 요청 (필수) |
| 기존에만 있음 | `삭제` 후보 | 확인 후 상태만 변경. **행은 지우지 않는다** |

대·중분류나 비고만 바뀐 것은 `유지`다. 분류 정리는 요구사항의 개정이 아니다.

## 작성 규칙

- 삭제된 요구사항은 행을 지우지 않고 상태만 `삭제`로 바꾼다. 지우면 개정 추적이 끊긴다
- `변경 근거`가 비면 게이트에서 차단한다. 이 열이 비면 개정이력의 `개정 내용`을 만들 수 없다
- `변경 근거`는 자동 생성하지 않는다. 왜 바뀌었는지는 문서에 없다 — 사용자에게 묻는다
- 개정이력 기입은 `skills/manage-revision-history` 가 담당한다
```

- [ ] **Step 5: export 프로파일을 교체한다**

`plugins/gx-pm/utils/export-xlsx.py` 의 `"요구사항정의서"` 프로파일을 바꾼다.

```python
    "요구사항정의서": {
        "sheet_name": "요구사항 명세",
        # 컬럼 정본은 templates/AN-02-requirements-definition.md 의
        # 「본문 컬럼 (정본)」 절이다. 여기서 이름을 바꾸면 계약 테스트가 잡는다.
        "columns": [[
            "번호", "요구사항ID", "대분류", "중분류", "요구사항명",
            "요구사항 상세내용", "비고", "상태", "요구사항 근거", "변경 근거",
        ]],
        "merge_columns": ["대분류", "중분류"],
    },
```

- [ ] **Step 6: `extract-requirements` 스킬을 고친다**

Step 3(분류)·Step 4(ID 부여)·Step 5(수용여부 초안)·출력 형식 절을 아래로 교체한다. **Step 2의 ID 표 2단계 판정 규칙은 그대로 둔다** — `tests/test_extract_rules.py` 가 이 문서에서 정규식을 꺼내 쓴다.

```markdown
### Step 3: 행 분할

**컬럼을 채우기 전에 몇 행이 되는지가 먼저다.** 이 건수가 뒤 산출물 전체의 행 수를 정한다.

| 상황 | 처리 |
|------|------|
| `ㅇ` · `-` 불릿 하나 | 요구사항 1건 |
| ID 표의 행 하나 (Step 2 판정 통과) | 요구사항 1건 |
| 한 문장에 이질적 기능이 `및`·`~와 ~를` 로 묶임 | **쪼갠다** |
| 하나가 다른 하나의 수단인 경우 (`~하여 ~한다`) | 쪼개지 않는다 |

**판정 기준: 테스트를 따로 써야 하면 따로 쪼갠다.**

- `상대평가기준 생성 결과 조회 및 다운로드 기능` → 입력도 출력도 다르므로 **2건**
- `헤더정보를 읽어 컬럼 순서를 파악한 후 업로드` → 수단-목적 관계이므로 **1건**

애매하면 추정하지 않고 묻는다. Step 2 의 표 판정 애매성과 같은 중단점 규칙이다.

### Step 4: 분류

- **대분류**: 업무 영역. 출처 우선순위 ① RFP 목차·장 제목 ② ID 표의 분류 열 ③ 모델 분류
- **중분류**: 세부 업무. 대분류 안에서 유일해야 한다
- ③ 으로 갔으면 게이트에서 "문서에 없어 추정했다" 를 명시한다

### Step 5: ID 부여와 상태

- 요구사항ID: 프로파일 채번 규칙. 미설정이면 AskUserQuestion 으로 한 번 묻는다
  (기본 제안 `REQ-{3자리}`)
- 최초 작성이면 상태는 전건 `신규`, 근거는 `과업지시서` 등 출처
- 재실행이면 `templates/AN-02-requirements-definition.md` 의 상태 판정표를 따른다

### Step 6: 개정이력

**manage-revision-history** 스킬로 개정이력 행을 만든다.

## 출력 형식

```
## 개정이력

| 버전 | 개정일 | 개정 사유 | 개정 내용 | 작성자 | 승인자 |
|------|--------|----------|----------|--------|--------|
| 1.0 | 2026.09.03 | 신규 | 최초 작성 | 구본승 | |

## 요구사항 명세 — {시스템명}

| 번호 | 요구사항ID | 대분류 | 중분류 | 요구사항명 | 요구사항 상세내용 | 비고 | 상태 | 요구사항 근거 | 변경 근거 |
|------|-----------|--------|--------|-----------|-----------------|------|------|-------------|----------|
| 1 | REQ-001 | 데이터 전처리·입력 | 상대평가기준 생성 기능 | 벤치마크 EUI·CDF 스코어테이블 생성 기능 | 원단위 통계데이터를 이용한 세부용도별 벤치마크 EUI 테이블 및 CDF 생성 | | 신규 | 과업지시서 | |
```
```

`## 주의사항` 절의 `수용여부` 관련 항목을 지우고 아래로 바꾼다.

```markdown
## 주의사항

- 요구사항은 가능한 원문 표현을 유지 (해석하지 않음)
- 상세내역이 길면 핵심만 요약하되 **조건·제약·수치는 버리지 않는다** — 테스트 경계값의 유일한 출처다
- 요약했으면 비고에 원문 위치를 표기한다
- 원문 ID 는 `요구사항 근거` 열에 병기한다: `과업지시서 BR-01`
```

- [ ] **Step 7: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: `An02ColumnSsotTest` PASS. `test_모든_프로필_컬럼이_문서에_존재한다` 는 AN-05 템플릿이 아직 옛 컬럼(`제안요청ID`)을 담고 있어 통과한다. 실패가 남으면 그 메시지가 지목한 파일의 컬럼명을 정본과 맞춘다.

- [ ] **Step 8: 커밋**

```bash
git add plugins/gx-pm/templates/AN-02-requirements-definition.md \
        plugins/gx-pm/skills/extract-requirements/SKILL.md \
        plugins/gx-pm/utils/export-xlsx.py \
        plugins/gx-pm/tests/helpers.py \
        plugins/gx-pm/tests/test_export_xlsx.py
git commit -m "feat: 요구사항정의서를 상태·변경근거 중심 10컬럼으로 교체한다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

---

## Task 4: AN-03 기능명세서 신설

요구사항과 테스트 사이의 빠진 고리다. `입력항목`과 `처리내용`이 이후 테이블 컬럼과 테스트 케이스의 유일한 근거가 된다.

**Files:**
- Create: `plugins/gx-pm/templates/AN-03-function-spec.md`
- Create: `plugins/gx-pm/skills/generate-function-spec/SKILL.md`
- Create: `plugins/gx-pm/commands/gx-기능명세서.md`
- Modify: `plugins/gx-pm/utils/export-xlsx.py`
- Modify: `plugins/gx-pm/templates/prerequisites.md`
- Test: `plugins/gx-pm/tests/test_export_xlsx.py`

**Interfaces:**
- Consumes: Task 3의 AN-02 10컬럼 (`요구사항ID`, `대분류`, `중분류`, `요구사항 상세내용`)
- Produces: AN-03 10컬럼. Task 5가 `입력항목`을, Task 6이 `입력항목`·`처리내용`·`출력결과`를, Task 7이 `기능ID`·`연계요구사항ID`를 읽는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
class An03ColumnSsotTest(unittest.TestCase):
    """AN-03 컬럼 정본은 templates/AN-03-function-spec.md 다."""

    def setUp(self):
        self.mod = load_export_module()
        self.정본 = parse_column_ssot("AN-03-function-spec.md", "본문 컬럼 (정본)")

    def test_정본이_열_개다(self):
        self.assertEqual(len(self.정본), 10, f"AN-03 정본이 10개가 아닙니다: {self.정본}")

    def test_정본_순서가_설계와_같다(self):
        self.assertEqual(self.정본, [
            "기능ID", "대분류", "중분류", "기능명", "기능설명",
            "입력항목", "처리내용(로직)", "출력결과", "연계요구사항ID", "비고",
        ])

    def test_프로필이_정본과_같다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["기능명세서"]["columns"][0], self.정본
        )

    def test_분류_두_열이_병합_대상이다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["기능명세서"]["merge_columns"],
            ["대분류", "중분류"],
        )
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_export_xlsx.An03ColumnSsotTest -v`
Expected: FAIL — `FileNotFoundError` 또는 `AN-03 정본이 10개가 아닙니다: []`

- [ ] **Step 3: 템플릿을 만든다**

`plugins/gx-pm/templates/AN-03-function-spec.md`:

```markdown
# AN-03 기능명세서 양식

## 파일 형식
Excel (.xlsx)

## 시트 구성
1. **개정이력** — 규칙의 정본은 `templates/revision-history.md`
2. **기능명세** — 본문 데이터

## 본문 컬럼 (정본)

| # | 컬럼 | 값 규칙 |
|---|------|--------|
| 1 | 기능ID | 프로파일 채번(기본 `FN-001`). 요구사항ID 에서 파생하지 않는다 |
| 2 | 대분류 | AN-02 에서 승계. 새로 분류하지 않는다 |
| 3 | 중분류 | 〃. 분류가 갈리면 첫 연계 요구사항을 따르고 비고에 표기 |
| 4 | 기능명 | 명사구. 쪼갠 경우 서로 구분되는 이름 |
| 5 | 기능설명 | 2~3문장. 시스템 관점의 동작 서술 |
| 6 | 입력항목 | `항목명(타입, 제약, 필수여부, 기본값)` 을 `/` 로 구분 |
| 7 | 처리내용(로직) | `① ~ ② ~` 번호 순서, 3~7단계 |
| 8 | 출력결과 | 화면 결과 + 데이터 결과를 함께 |
| 9 | 연계요구사항ID | 다중 허용(쉼표). 최소 1건 |
| 10 | 비고 | `[확인필요]` 사유, 분류 승계 예외 |

## 행 분할 규칙

기본은 요구사항 1건 → 기능 1건.

| 상황 | 처리 | 예 |
|------|------|-----|
| 요구사항 하나에 조작 흐름이 둘 이상이고 입력·출력이 다름 | **쪼갠다** | `조회 및 다운로드` → FN-003 / FN-004 |
| 여러 요구사항이 같은 처리 로직을 공유 | **합친다**, 연계ID 다중 | REQ-007·REQ-027 |

**판정 기준: 처리내용(로직)이 같으면 한 기능이다.** 화면이 같은지는 보지 않는다.

## 입력항목 — 이 문서에서 가장 중요한 열

여기 적힌 제약이 그대로 DE-08 의 컬럼 제약과 DE-13 의 경계 케이스가 된다.
**제약이 비면 테스트가 정상 케이스만 나온다.**

도출 출처를 이 순서로 본다.

1. 요구사항 상세내용에 명시된 입력
2. 처리내용에서 역산 — 그룹핑하려면 그룹 키가 입력이어야 한다
3. 기존 DDL 이 있으면 컬럼 제약(길이·NotNull)

셋 다 실패하면 `[확인필요]` 로 두고 **지어내지 않는다.**

## 처리내용 — 예외 케이스의 유일한 출처

`검증 → 처리 → 저장` 3박자가 최소 형태다. **분기와 검증을 반드시 포함한다.**

- 분기(`~이면 ~한다`)가 그대로 DE-13 의 예외 케이스가 된다
- 트랜잭션 경계가 있으면 명시한다 (`⑤ 전체 커밋, 실패 시 롤백`)

분기가 하나도 없는 처리내용은 정상 흐름만 생각한 것이므로 게이트에서 되묻는다.

## 예시 행

| 기능ID | 대분류 | 중분류 | 기능명 | 기능설명 | 입력항목 | 처리내용(로직) | 출력결과 | 연계요구사항ID | 비고 |
|---|---|---|---|---|---|---|---|---|---|
| FN-001 | 데이터 전처리·입력 | 상대평가기준 생성 기능 | 벤치마크 스코어테이블 생성 | 원단위 통계 데이터로 세부용도별 EUI 테이블과 CDF 를 산출한다 | 원단위 통계파일(xlsx, 필수) / 세부용도 코드(필수) / 이상치 제외 여부(Y·N, 기본 N) | ① 헤더 검증 ② 세부용도별 그룹핑 ③ EUI 중위값·분위수 산출 ④ CDF 계산 ⑤ 스코어테이블 저장 | 생성 완료 안내 / TB_SCORE 1건 저장 | REQ-001 | |

## 작성 규칙

- **입력은 승인된 AN-02 뿐이다. 원본 RFP 를 다시 읽지 않는다** — 두 입력을 함께 보면
  AN-02 에 없는 기능이 생겨 추적이 끊긴다
- 연계요구사항ID 가 0건인 기능은 근거 없는 기능이므로 게이트에서 차단한다
- 개정이력 기입은 `skills/manage-revision-history` 가 담당한다
```

- [ ] **Step 4: export 프로파일을 추가한다**

`DOCUMENT_PROFILES` 의 `"요구사항정의서"` 바로 뒤에 넣는다.

```python
    "기능명세서": {
        "sheet_name": "기능명세",
        # 컬럼 정본은 templates/AN-03-function-spec.md 의 「본문 컬럼 (정본)」 절이다.
        "columns": [[
            "기능ID", "대분류", "중분류", "기능명", "기능설명",
            "입력항목", "처리내용(로직)", "출력결과", "연계요구사항ID", "비고",
        ]],
        "merge_columns": ["대분류", "중분류"],
    },
```

- [ ] **Step 5: 스킬을 만든다**

`plugins/gx-pm/skills/generate-function-spec/SKILL.md`:

```markdown
---
name: generate-function-spec
description: 승인된 요구사항정의서(AN-02)에서 기능을 도출하여 AN-03 기능명세서를 생성합니다. 입력항목·처리내용·출력결과를 채웁니다.
---

# 기능명세 생성 (generate-function-spec)

승인된 AN-02 요구사항정의서를 읽어 기능 단위로 재구성한다.
양식 정본은 `templates/AN-03-function-spec.md` 다.

## 입력

| 항목 | 필수 | 설명 |
|------|------|------|
| AN-02 요구사항정의서 | Y | 승인된 것만 |
| 기능ID 채번 규칙 | Y | 프로파일. 미설정이면 묻는다 |
| 기존 DDL | N | 있으면 입력항목 제약 도출에 쓴다 |

**원본 RFP 를 읽지 않는다.** AN-02 가 정본이다.

## 처리 절차

### Step 1: 기능 단위 판정

`templates/AN-03-function-spec.md` 의 행 분할 규칙을 따른다.
쪼개거나 합친 경우 비고에 사유를 남긴다.

### Step 2: 분류 승계

대·중분류를 AN-02 에서 그대로 가져온다. 여러 요구사항을 덮어 분류가 갈리면
첫 연계 요구사항의 분류를 쓰고 비고에 `분류 승계: REQ-007 기준` 을 남긴다.

### Step 3: 입력항목 도출

`templates/AN-03-function-spec.md` 의 도출 출처 3단계를 따른다.
근거가 없으면 `[확인필요]` 로 둔다 — **지어내지 않는다.**

### Step 4: 처리내용 도출

`검증 → 처리 → 저장` 3박자를 최소로 한다. 분기와 트랜잭션 경계를 명시한다.
분기가 0개면 사용자에게 되묻는다:

```
FN-004 처리내용에 분기가 없습니다.
정상 흐름만 정의되면 단위테스트가 예외 케이스를 만들지 못합니다.

  1. 예외 조건을 알려주세요
  2. 분기가 정말 없는 기능입니다 (단순 조회 등)
```

### Step 5: 출력결과 도출

화면 결과와 데이터 결과를 함께 적는다. 데이터 결과가 DE-13 의 `사후조건` 이 된다.

### Step 6: 검증

- 연계요구사항ID 가 0건인 기능이 있으면 **차단**한다
- AN-02 의 요구사항 중 어느 기능에도 안 걸린 것을 목록으로 보고한다
  (비기능 요구사항은 정상이다 — DE-13 에서 `연계기능ID` 공란 행으로 검증한다)

### Step 7: 개정이력

**manage-revision-history** 스킬로 개정이력 행을 만든다.

## 출력 형식

```
## 개정이력

| 버전 | 개정일 | 개정 사유 | 개정 내용 | 작성자 | 승인자 |
|------|--------|----------|----------|--------|--------|
| 1.0 | 2026.09.03 | 신규 | 최초 작성 | 구본승 | |

## 기능명세 — {시스템명}

| 기능ID | 대분류 | 중분류 | 기능명 | 기능설명 | 입력항목 | 처리내용(로직) | 출력결과 | 연계요구사항ID | 비고 |
|---|---|---|---|---|---|---|---|---|---|
| FN-001 | 데이터 전처리·입력 | 상대평가기준 생성 기능 | 벤치마크 스코어테이블 생성 | 원단위 통계 데이터로 세부용도별 EUI 테이블과 CDF 를 산출한다 | 원단위 통계파일(xlsx, 필수) / 세부용도 코드(필수) | ① 헤더 검증 ② 세부용도별 그룹핑 ③ EUI 중위값 산출 ④ CDF 계산 ⑤ 저장 | 생성 완료 안내 / TB_SCORE 1건 저장 | REQ-001 | |

### [확인필요] 목록

| 기능ID | 열 | 사유 |
|--------|-----|------|
| FN-004 | 입력항목 | 요구사항에 입력 제약이 없고 DDL 도 없음 |
```

## 주의사항

- 기능ID 는 요구사항ID 에서 파생하지 않는다 — 기능 1개가 요구사항 여러 건을 덮는 경우를
  표현해야 한다
- 기능설명은 요구사항 상세내용의 재진술이 아니다. 시스템이 무엇을 하는지를 쓴다
```

- [ ] **Step 6: 커맨드를 만든다**

`plugins/gx-pm/commands/gx-기능명세서.md`:

```markdown
---
description: "AN-03 기능명세서를 생성합니다. 요구사항정의서에서 기능을 도출하고 입력항목·처리내용·출력결과를 정의합니다. | 자연어: 기능명세서 만들어줘, 기능 정의, 기능 뽑아줘, 기능명세 작성"
---

# /gx-기능명세서 — AN-03 기능명세서 생성

> **선행조건**: `templates/prerequisites.md` 의 `/gx-기능명세서` 행을 따른다.
> **실행 규약**: `templates/pipeline-protocol.md` 를 따른다.

## Step 0: 프로젝트 컨텍스트 로드

**load-project-profile** 스킬로 활성 프로젝트를 확인한다. 프로파일이 없으면
`/gx-프로젝트설정` 을 먼저 실행하라고 안내 후 종료.

**detect-existing-artifact** 스킬로 기존 `{시스템코드}-기능명세서.md` 를 확인한다.

## Step 1: 요구사항정의서 로드

승인된 AN-02 를 읽는다. 없으면 `/gx-요구사항정의서` 를 먼저 실행하라고 안내 후 종료.

## Step 2: 기능 도출

**generate-function-spec** 스킬을 수행한다.

## Step 3: 승인 루프

`templates/approval-protocol.md` 를 따른다. `[확인필요]` 목록을 함께 보여준다.

## Step 4: 개정이력 기록

**manage-revision-history** 스킬로 개정이력 행을 만든다.

## Step 5: xlsx 추출

`utils/export-xlsx.py` 로 추출한다.

## 다음 제안

- `/gx-테이블정의서` — 입력항목을 컬럼으로 확정
- `/gx-단위테스트계획서` — 기능에서 테스트 케이스 도출
```

- [ ] **Step 7: 선행조건 레지스트리에 등록한다**

`plugins/gx-pm/templates/prerequisites.md` 의 표에 행을 추가한다. 형식은 기존 행과 동일하게 맞춘다.

```markdown
| `/gx-기능명세서` | 프로파일, AN-02 요구사항정의서 | — |
```

- [ ] **Step 8: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: PASS. `test_모든_커맨드가_레지스트리에_있다` 와 `test_모든_스킬이_어느_커맨드에서든_호출된다` 가 Step 6·7 로 해소된다.

- [ ] **Step 9: 커밋**

```bash
git add plugins/gx-pm/templates/AN-03-function-spec.md \
        plugins/gx-pm/skills/generate-function-spec/ \
        plugins/gx-pm/commands/gx-기능명세서.md \
        plugins/gx-pm/templates/prerequisites.md \
        plugins/gx-pm/utils/export-xlsx.py \
        plugins/gx-pm/tests/test_export_xlsx.py
git commit -m "feat: 요구사항과 테스트 사이에 기능명세서를 세운다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

---

## Task 5: DE-08 테이블정의서 — 역생성 + 신규 컬럼 표준 제안

순방향(요구사항→테이블)을 폐지하고, 기존 스키마는 고정한 채 신규 컬럼만 표준용어사전 근거로 제안한다.

**Files:**
- Modify: `plugins/gx-pm/templates/DE-08-table-definition.md`
- Modify: `plugins/gx-pm/skills/convert-ddl-to-tablespec/SKILL.md`
- Modify: `plugins/gx-pm/commands/gx-테이블정의서.md`
- Modify: `plugins/gx-pm/utils/export-xlsx.py`
- Test: `plugins/gx-pm/tests/test_export_xlsx.py`, `plugins/gx-pm/tests/test_plugin_consistency.py`

**Interfaces:**
- Consumes: Task 4의 AN-03 `입력항목`
- Produces: DE-08 15컬럼. Task 6이 `길이`·`NotNull`·`연계기능ID`를 읽어 경계·필수값 케이스를 만든다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`test_export_xlsx.py` 에 추가:

```python
class De08ColumnSsotTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()
        self.정본 = parse_column_ssot("DE-08-table-definition.md", "본문 컬럼 (정본)")

    def test_정본이_열다섯_개다(self):
        self.assertEqual(len(self.정본), 15, f"DE-08 정본이 15개가 아닙니다: {self.정본}")

    def test_구분과_표준_판정_열이_있다(self):
        for 컬럼 in ["구분", "표준 판정", "표준 권고명", "근거", "연계기능ID"]:
            with self.subTest(컬럼=컬럼):
                self.assertIn(컬럼, self.정본)

    def test_프로필이_정본과_같다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["테이블정의서"]["columns"][0], self.정본
        )

    def test_테이블명이_병합_대상이다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["테이블정의서"]["merge_columns"], ["테이블명"]
        )
```

`test_plugin_consistency.py` 에 추가:

```python
class TableSpecStandardTest(unittest.TestCase):
    """테이블정의서는 표준용어 MCP 없이 컬럼명을 지어내지 않는다."""

    def setUp(self):
        self.스킬 = (
            PLUGIN_ROOT / "skills" / "convert-ddl-to-tablespec" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_두_MCP_도구를_모두_쓴다(self):
        for 도구 in ["validate_column", "translate_column"]:
            with self.subTest(도구=도구):
                self.assertIn(도구, self.스킬)

    def test_기존_컬럼을_바꾸지_않는다고_명시한다(self):
        self.assertIn("현행유지", self.스킬)

    def test_MCP_부재_시_중단한다고_명시한다(self):
        self.assertIn("지어내지 않는다", self.스킬)

    def test_MCP_연계_정본을_참조한다(self):
        self.assertIn("docs/표준용어-mcp-연계.md", self.스킬)

    def test_순방향_생성_경로가_남아있지_않다(self):
        커맨드 = (
            PLUGIN_ROOT / "commands" / "gx-테이블정의서.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "generate-erd-guide", 커맨드,
            "요구사항에서 테이블을 추론하는 순방향 경로가 남아 있습니다",
        )
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_export_xlsx.De08ColumnSsotTest tests.test_plugin_consistency.TableSpecStandardTest -v`
Expected: FAIL — `DE-08 정본이 15개가 아닙니다: []` 와 `'현행유지' not found`

- [ ] **Step 3: 템플릿을 교체한다**

`plugins/gx-pm/templates/DE-08-table-definition.md` 를 통째로 바꾼다.

```markdown
# DE-08 테이블정의서 양식

## 파일 형식
Excel (.xlsx)

## 시트 구성
1. **개정이력** — 규칙의 정본은 `templates/revision-history.md`
2. **테이블정의** — 본문 데이터

## 이 문서는 역생성 문서다

**요구사항에서 테이블을 추론해 만들지 않는다.** 그렇게 만든 정의서는 추측이고,
개발이 시작되는 순간 거짓말이 된다. 기존 DDL 을 읽어 고정하고, 기능명세서(AN-03)의
`입력항목` 중 기존 컬럼에 매핑되지 않는 것만 **신규 컬럼 후보**로 제안한다.

## 본문 컬럼 (정본)

| # | 컬럼 | 값 규칙 |
|---|------|--------|
| 1 | 테이블명 | 물리 테이블명. 연속 동일값은 세로 병합된다 |
| 2 | 테이블 논리명 | DB 코멘트 → 표준용어 역변환 → 기능명세 순으로 복원 |
| 3 | 컬럼명 | 기존은 DDL 그대로, 신규는 승인된 표준 컬럼명 |
| 4 | 컬럼 논리명 | 기능명세 `입력항목` 의 항목명과 매칭 |
| 5 | 데이터타입 | |
| 6 | 길이 | DE-13 경계 케이스의 근거 |
| 7 | 소수점 | |
| 8 | PK | |
| 9 | NotNull | DE-13 필수값 예외 케이스의 근거 |
| 10 | 기본값 | |
| 11 | 구분 | `기존` / `신규` / `변경` |
| 12 | 표준 판정 | `표준준수` / `현행유지` / `신규적용` |
| 13 | 표준 권고명 | `현행유지` 일 때 표준형 (`표준은 RGN_CD`) |
| 14 | 근거 | `행안부표준 · 지역=RGN, 코드=CD` |
| 15 | 연계기능ID | 이 컬럼을 쓰는 기능 |

## 기존 컬럼은 바꾸지 않는다

운영 중인 스키마를 바꾸자고 제안하는 것은 이 문서의 권한 밖이다.
비표준이어도 `표준 판정` 을 `현행유지` 로 두고 `표준 권고명` 에 표준형을 남긴다.

`현행유지` 행은 감리에서 강점이 된다 — "비표준을 몰랐다" 가 아니라
"알고 있고 운영 중이라 유지한다" 가 문서로 남는다.

## 표준 판정 규칙

| 대상 | MCP 도구 | 결과 → 판정 |
|------|---------|-----------|
| 기존 컬럼 | `validate_column` | `PASS` → `표준준수` / `PARTIAL`·`FAIL` → `현행유지` + 표준 권고명 병기 |
| 신규 컬럼 | `translate_column` | `FULL` → `신규적용` / `PARTIAL`·`AI_SUGGESTED` → 근거와 함께 제시 / `FAIL`·`decisionRequired` → 그 자리에서 사용자 선택 |

상세 프로토콜의 정본은 `docs/표준용어-mcp-연계.md` 다.

## 예시 행

| 테이블명 | 테이블 논리명 | 컬럼명 | 컬럼 논리명 | 데이터타입 | 길이 | 소수점 | PK | NotNull | 기본값 | 구분 | 표준 판정 | 표준 권고명 | 근거 | 연계기능ID |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TB_SCORE | 스코어테이블 | OBSVTR_NM | 관측소명 | VARCHAR | 200 | | | Y | | 신규 | 신규적용 | | 행안부표준 · 관측소=OBSVTR, 명=NM | FN-001 |
| TB_BLDG | 건물대장 | REGION_CD | 지역코드 | VARCHAR | 10 | | | Y | | 기존 | 현행유지 | 표준은 RGN_CD | 행안부표준 · 지역=RGN | FN-003 |

## 작성 규칙

- 기존 DDL 이 없으면 전건이 `신규` 가 되어 전부 표준 제안 대상이 된다
- 표준용어 MCP 가 세션에 없으면 `docs/표준용어-mcp-연계.md` 의 설치 안내를 출력하고 중단한다
- 개정이력 기입은 `skills/manage-revision-history` 가 담당한다
```

- [ ] **Step 4: export 프로파일을 교체한다**

```python
    "테이블정의서": {
        "sheet_name": "테이블정의",
        # 컬럼 정본은 templates/DE-08-table-definition.md 의 「본문 컬럼 (정본)」 절이다.
        "columns": [[
            "테이블명", "테이블 논리명", "컬럼명", "컬럼 논리명",
            "데이터타입", "길이", "소수점", "PK", "NotNull", "기본값",
            "구분", "표준 판정", "표준 권고명", "근거", "연계기능ID",
        ]],
        "merge_columns": ["테이블명"],
    },
```

- [ ] **Step 5: 스킬을 재작성한다**

`plugins/gx-pm/skills/convert-ddl-to-tablespec/SKILL.md` 의 `## 처리 절차` 이하를 바꾼다.
프론트매터와 `## 입력`(DDL 복사 방법 안내)은 그대로 둔다 — 사용자에게 유용하고 커맨드가 참조한다.

```markdown
## 처리 절차

### Step 1: 기존 스키마 로드

DDL 을 파싱해 테이블·컬럼 목록을 만든다. 전건의 `구분` 을 `기존` 으로 둔다.

```sql
CREATE TABLE 테이블명 (
  컬럼명 데이터타입(길이) [NOT NULL] [DEFAULT 값],
  PRIMARY KEY (컬럼1),
  FOREIGN KEY (컬럼) REFERENCES 참조테이블(참조컬럼)
);
```

`COMMENT ON COLUMN` 이 있으면 `컬럼 논리명` 으로 쓴다.

DDL 이 없으면 기존 스키마 없음으로 보고 Step 2 로 간다 (전건이 신규가 된다).

### Step 2: 기능명세 입력항목 매핑

AN-03 의 `입력항목` 을 파싱해 기존 컬럼에 매핑한다.

| 매핑 결과 | 처리 |
|----------|------|
| 기존 컬럼에 대응됨 | `연계기능ID` 를 채운다. `컬럼 논리명` 이 비었으면 입력항목의 항목명으로 채운다 |
| 대응 없음 | **신규 컬럼 후보.** `구분` 을 `신규` 로 둔다 |
| 기존 컬럼인데 제약이 다름 | `구분` 은 `기존` 으로 두고 비고에 불일치를 적는다 — 스키마를 바꾸지 않는다 |

제약 불일치는 버리지 않고 게이트에서 목록으로 보고한다.
`입력항목 50자 ↔ 컬럼 VARCHAR(100)` 은 둘 중 하나가 틀렸다는 뜻이다.

### Step 3: 기존 컬럼 표준 검증

`sqi-comn-term` MCP 가 세션에 있는지 먼저 확인한다. 없으면
`docs/표준용어-mcp-연계.md` 의 설치 안내를 출력하고 **중단한다.**
표준 검증 없이 컬럼명을 **지어내지 않는다.**

`sourcePriority` 는 프로파일에서 읽고, 없으면 `["BLDG_ENGY", "MOIS_STD"]` 를 제안하고 묻는다.

```
validate_column(columnNames=[기존 컬럼 전건], sourcePriority=[...])
```

| 결과 | 표준 판정 | 표준 권고명 |
|------|----------|-----------|
| `PASS` | `표준준수` | 공란 |
| `PARTIAL` · `FAIL` | `현행유지` | `표준은 {suggestedColumnName}` |

**기존 컬럼을 표준형으로 바꾸자고 제안하지 않는다.**

### Step 4: 신규 컬럼 표준 도출

```
translate_column(inputs=[신규 컬럼 논리명 전건], sourcePriority=[...])
```

| 결과 | 처리 |
|------|------|
| `FULL` | `신규적용` 으로 확정 제시. `근거` 에 `{ctgryNms} · {단어 매칭}` |
| `PARTIAL` · `AI_SUGGESTED` | 근거와 함께 제시. 사용자가 반려하면 대안을 묻는다 |
| `FAIL` · `decisionRequired=true` | **그 자리에서 사용자 선택.** `humanHint` 를 그대로 보여준다 |
| `dataTypeCandidates` 다건 | 타입 후보를 나열하고 선택을 요청 |

이 중단점은 **게이트로 이월하지 않는다** — `templates/pipeline-protocol.md` §이월 금지 항목.
컬럼명이 확정돼야 DE-13 의 경계값이 그 위에 선다.

### Step 5: 승인 게이트

신규 컬럼만 승인 대상이다. 기존은 확인용으로만 보여준다.

```
신규 컬럼 12건에 표준 컬럼명을 제안합니다.  (출처: BLDG_ENGY → MOIS_STD)

[신규 · 승인 필요]
  권한명        → AUTH_NM       권한=AUTH, 명=NM              VARCHAR(200)
  관측일자      → OBSRVN_YMD    관측=OBSRVN, 일자=YMD          CHAR(8)
  일평균기온    → ???_ARTMP     기온=ARTMP, 앞 단어 미확정  선택 필요

[기존 · 변경하지 않음]  비표준이지만 현재 사용 중이라 유지합니다.
  REGION_CD   (표준은 RGN_CD)    · TB_BLDG
  LATITUDE    (표준은 LAT)       · TB_BLDG

[제약 불일치]  기능명세와 스키마가 어긋납니다.
  FN-007 권한명 50자  ↔  TB_AUTH.AUTH_NM VARCHAR(100)
```

**AskUserQuestion 으로 묻는다.** `templates/approval-protocol.md` 의 인자 규칙을 따른다.

### Step 6: 개정이력

**manage-revision-history** 스킬로 개정이력 행을 만든다.
불변 키는 `테이블명 + 컬럼명` 이다.

## 출력 형식

`templates/DE-08-table-definition.md` 의 컬럼 순서를 그대로 쓴다.
개정이력 표를 맨 위에 둔다.

## 주의사항

- 요구사항에서 테이블을 추론하지 않는다. 이 스킬은 역생성 전용이다
- 기존 컬럼의 이름·타입·제약을 바꾸지 않는다
- 표준 검증 없이 컬럼명을 지어내지 않는다
```

- [ ] **Step 6: 커맨드를 고친다**

`plugins/gx-pm/commands/gx-테이블정의서.md` 에서 `generate-erd-guide` 를 부르는 절과
"정방향 / 역방향" 분기를 제거하고, DDL 로드 → AN-03 매핑 → MCP 판정 → 승인 흐름으로 바꾼다.
`generate-erd-guide` 스킬 참조는 한 곳도 남기지 않는다 (Task 9에서 archive 로 내린다).

`description` 프론트매터도 갱신한다:

```yaml
description: "DE-08 테이블정의서를 생성합니다. 기존 DDL을 역생성하고 기능명세의 신규 컬럼만 표준용어사전 근거로 제안합니다. | 자연어: 테이블정의서 만들어줘, DDL 변환, 컬럼 표준화, DB 정의서"
```

- [ ] **Step 7: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: PASS. 실패가 남으면 `test_모든_프로필_컬럼이_문서에_존재한다` 가 지목한 컬럼명을 템플릿과 맞춘다.

- [ ] **Step 8: 커밋**

```bash
git add plugins/gx-pm/templates/DE-08-table-definition.md \
        plugins/gx-pm/skills/convert-ddl-to-tablespec/SKILL.md \
        plugins/gx-pm/commands/gx-테이블정의서.md \
        plugins/gx-pm/utils/export-xlsx.py \
        plugins/gx-pm/tests/
git commit -m "feat: 테이블정의서를 역생성 전용으로 바꾸고 신규 컬럼만 표준 제안한다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

---

## Task 6: DE-13 단위테스트계획서 재작성

화면 기반 27개 검사기준 체크리스트를 폐지하고 기능 축 11컬럼 단일 시트로 바꾼다.

**Files:**
- Modify: `plugins/gx-pm/templates/DE-13-unit-test-plan.md`
- Modify: `plugins/gx-pm/skills/generate-unit-test-plan/SKILL.md`
- Modify: `plugins/gx-pm/skills/design-test-cases/SKILL.md`
- Modify: `plugins/gx-pm/commands/gx-단위테스트계획서.md`
- Modify: `plugins/gx-pm/utils/export-xlsx.py`
- Test: `plugins/gx-pm/tests/test_export_xlsx.py`

**Interfaces:**
- Consumes: Task 4의 AN-03 `입력항목`·`처리내용(로직)`·`출력결과`, Task 5의 DE-08 `길이`·`NotNull`
- Produces: DE-13 11컬럼. Task 7이 `테스트ID`·`연계기능ID`·`연계요구사항ID`·`결과`를 읽는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
class De13ColumnSsotTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()
        self.정본 = parse_column_ssot("DE-13-unit-test-plan.md", "본문 컬럼 (정본)")

    def test_정본이_열한_개다(self):
        self.assertEqual(len(self.정본), 11, f"DE-13 정본이 11개가 아닙니다: {self.정본}")

    def test_정본_순서가_설계와_같다(self):
        self.assertEqual(self.정본, [
            "테스트ID", "연계기능ID", "연계요구사항ID", "사전조건", "입력",
            "기대결과", "사후조건", "의존성", "테스트담당자", "수행일", "결과",
        ])

    def test_프로필이_한_시트다(self):
        """27개 검사기준 시트를 폐지했으므로 컬럼 세트는 하나다."""
        프로필 = self.mod.DOCUMENT_PROFILES["단위테스트계획서"]
        self.assertEqual(len(프로필["columns"]), 1)
        self.assertNotIn("sheet_names", 프로필)

    def test_화면_축_컬럼이_남아있지_않다(self):
        프로필 = self.mod.DOCUMENT_PROFILES["단위테스트계획서"]["columns"][0]
        for 폐기 in ["화면ID", "화면명", "단위테스트ID", "검사기준 항목", "사용자구분"]:
            with self.subTest(컬럼=폐기):
                self.assertNotIn(폐기, 프로필)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_export_xlsx.De13ColumnSsotTest -v`
Expected: FAIL — `DE-13 정본이 11개가 아닙니다: []`

- [ ] **Step 3: 템플릿을 교체한다**

`plugins/gx-pm/templates/DE-13-unit-test-plan.md` 를 통째로 바꾼다.

```markdown
# DE-13 단위테스트계획서 양식

## 파일 형식
Excel (.xlsx)

## 시트 구성
1. **개정이력** — 규칙의 정본은 `templates/revision-history.md`
2. **단위테스트계획** — 본문 데이터

## 본문 컬럼 (정본)

| # | 컬럼 | 값 규칙 |
|---|------|--------|
| 1 | 테스트ID | 프로파일 채번(기본 `UT-001`). 기능별로 이어서 |
| 2 | 연계기능ID | AN-03 참조. **비기능 테스트는 공란** |
| 3 | 연계요구사항ID | 기능을 경유해 자동 채움. 사용자 입력 금지 |
| 4 | 사전조건 | `계정·권한` / `선행 데이터` / `시스템 상태` 3유형. `없음` 으로 두지 않는다 |
| 5 | 입력 | 구체적인 값. `유효한 값` 처럼 추상적으로 쓰지 않는다 |
| 6 | 기대결과 | 관측 가능한 판정 기준. 화면 문구는 따옴표로 원문 그대로 |
| 7 | 사후조건 | 데이터 결과. 예외 케이스는 "변화 없음" 을 명시한다 |
| 8 | 의존성 | 선행 테스트ID. 없으면 `없음` |
| 9 | 테스트담당자 | 계획서는 공란 |
| 10 | 수행일 | 계획서는 공란 |
| 11 | 결과 | 계획서는 공란. `Pass` / `Fail` 2값 |

## 케이스 도출 규칙 — 기능 1건에서 테스트 N건

| 도출 출처 | 만들어지는 케이스 | 최소 건수 |
|---|---|---|
| 기능 전체 | 정상 흐름 | 1 |
| AN-03 `입력항목` 의 각 제약 (길이·범위·형식) | 경계 — 최소·최대·초과 | 제약당 2 |
| AN-03 `입력항목` 의 각 필수 항목 | 예외 — 미입력 | 필수항목당 1 |
| AN-03 `처리내용` 의 각 분기 (`~이면`) | 예외 — 분기 미충족 | 분기당 1 |
| AN-03 `처리내용` 의 롤백·트랜잭션 | 예외 — 중간 실패 | 있으면 1 |
| DE-08 의 `길이`·`NotNull` | 경계·필수값 보정 | 제약이 다르면 DE-08 이 우선 |

**정상 케이스만 있는 기능은 게이트에서 차단한다.**

## 비기능 요구사항의 처리

비기능 요구사항은 기능이 아니므로 AN-03 에 들어가지 않는다.
**`연계기능ID` 를 공란으로 두고 `연계요구사항ID` 만 채운 행**으로 검증한다.

| 테스트ID | 연계기능ID | 연계요구사항ID | 사전조건 | 입력 | 기대결과 | 사후조건 | 의존성 |
|---|---|---|---|---|---|---|---|
| UT-051 | | REQ-045 | 운영 동등 환경, 데이터 10만건 | 동시 사용자 500명 30분 부하 | 평균 응답 3초 이내, 오류율 1% 미만 | 측정 로그 보관 | 없음 |

`연계기능ID` 가 공란인 행이 비기능 테스트다. 별도 산출물을 만들지 않는다.

## 예시 행

| 테스트ID | 연계기능ID | 연계요구사항ID | 사전조건 | 입력 | 기대결과 | 사후조건 | 의존성 | 테스트담당자 | 수행일 | 결과 |
|---|---|---|---|---|---|---|---|---|---|---|
| UT-001 | FN-001 | REQ-001 | 원단위 통계파일 업로드 완료 | 세부용도=업무시설, 이상치제외=N | 세부용도별 EUI 중위값 테이블 생성, CDF 스코어 0~1 | TB_SCORE 1건 저장, 이력 로그 1건 | 없음 | | | |
| UT-002 | FN-001 | REQ-001 | 〃 | 헤더 컬럼 순서가 뒤바뀐 파일 | "헤더 형식 오류" 안내 후 처리 중단 | **저장 없음** | UT-001 | | | |

## 작성 규칙

- `연계요구사항ID` 는 기능을 경유해 자동으로 채운다. 손으로 넣으면 AN-03 과 어긋난다
- 예외 케이스의 `사후조건` 에 "변화 없음" 이 없으면, 안내만 띄우고 저장은 되는 결함을 못 잡는다
- 의존성이 있으면 실행 순서가 고정되고 병렬 실행이 막힌다는 뜻이다
- 개정이력 기입은 `skills/manage-revision-history` 가 담당한다
```

- [ ] **Step 4: export 프로파일을 교체한다**

`sheet_names` 키를 **삭제**하고 컬럼 세트를 하나로 만든다.

```python
    "단위테스트계획서": {
        "sheet_name": "단위테스트계획",
        # 컬럼 정본은 templates/DE-13-unit-test-plan.md 의 「본문 컬럼 (정본)」 절이다.
        "columns": [[
            "테스트ID", "연계기능ID", "연계요구사항ID", "사전조건", "입력",
            "기대결과", "사후조건", "의존성", "테스트담당자", "수행일", "결과",
        ]],
        "merge_columns": [],
    },
```

- [ ] **Step 5: `generate-unit-test-plan` 스킬을 재작성한다**

화면 유형 판별·27개 검사기준 매핑 절을 전부 지우고 아래로 바꾼다.

```markdown
## 입력

| 항목 | 필수 | 설명 |
|------|------|------|
| AN-03 기능명세서 | Y | 승인된 것만 |
| DE-08 테이블정의서 | N | 있으면 제약을 우선한다 |
| AN-02 요구사항정의서 | Y | 비기능 요구사항 목록용 |
| 테스트ID 채번 규칙 | Y | 프로파일. 미설정이면 묻는다 |

## 처리 절차

### Step 1: 기능별 케이스 도출

`templates/DE-13-unit-test-plan.md` 의 케이스 도출 규칙표를 따른다.
설계기법(동등분할·경계값·결정테이블·상태전이) 적용은 **design-test-cases** 스킬을 따른다.
기법 이름은 컬럼으로 내보내지 않는다 — 내부 도출 규칙이다.

### Step 2: 제약 출처 우선순위

같은 항목의 제약이 AN-03 과 DE-08 에서 다르면 **DE-08 이 우선**한다.
스키마가 실제로 강제하는 값이기 때문이다. 불일치는 게이트에서 목록으로 보고한다.

### Step 3: 연계요구사항ID 자동 채움

`연계기능ID` 로 AN-03 을 조회해 그 기능의 `연계요구사항ID` 를 그대로 옮긴다.
**사용자에게 묻지 않는다.**

### Step 4: 비기능 요구사항 케이스

AN-02 에서 어느 기능에도 안 걸린 요구사항을 찾아, `연계기능ID` 공란 행으로 만든다.
측정 조건·목표치가 요구사항 상세내용에 없으면 그 자리에서 묻는다.

### Step 5: 의존성 판정

선행 케이스가 만든 데이터를 쓰는 케이스에만 선행 테스트ID 를 적는다.
순환 의존이 생기면 차단한다.

### Step 6: 충분성 검증

- 정상 케이스만 있는 기능이 있으면 **차단**한다
- 필수 항목이 있는데 미입력 예외가 없으면 자동 보강한다
- 길이·범위 제약이 있는데 경계 케이스가 없으면 자동 보강한다

### Step 7: 개정이력

**manage-revision-history** 스킬로 개정이력 행을 만든다.
```

- [ ] **Step 6: `design-test-cases` 스킬을 축소한다**

프론트매터 `description` 을 바꾸고, 출력 컬럼(테스트케이스 시트 형식) 절을 지운다.
경계값 3유형·설계기법 표는 **내부 도출 규칙**으로 남긴다.

```yaml
description: 기능명세의 입력항목·처리내용에서 테스트 케이스를 도출하는 내부 규칙입니다. 동등분할·경계값분석·결정테이블·상태전이 적용 기준을 정의합니다.
```

문서 첫 문단을 바꾼다.

```markdown
# 테스트 케이스 도출 규칙 (design-test-cases)

**이 스킬은 산출물을 만들지 않는다.** `generate-unit-test-plan` 이 케이스를 뽑을 때
따르는 내부 규칙이다. 설계기법 이름은 DE-13 컬럼으로 내보내지 않는다.

도출 출처는 AN-03 의 `입력항목`·`처리내용(로직)` 과 DE-08 의 `길이`·`NotNull` 이다.
화면 유형은 더 이상 도출 근거가 아니다.
```

`화면 유형별 기본 설계기법` 표를 아래로 바꾼다.

```markdown
## 기능 유형별 기본 설계기법

| 기능 유형 | 적용 기법 | 최소 케이스 수 |
|----------|---------|-------------|
| 조회·목록 | 동등분할(검색조건 유효/무효), 경계값(페이징 첫·끝·범위초과) | 6건 |
| 등록 | 동등분할(필수/선택), 경계값(길이·범위), 결정테이블(필수값 조합), 예외(중복) | 8건 |
| 수정 | 상태전이(상태별 수정 가능 여부), 경계값, 예외(동시 수정 충돌) | 6건 |
| 삭제 | 예외(참조 무결성, 이미 삭제된 건) | 4건 |
| 파일 업로드·배치 | 동등분할(형식), 경계값(건수·용량), 예외(형식 오류·중간 실패 롤백) | 8건 |
| API·연계 | 동등분할(파라미터), 경계값, 예외(오류 응답 코드) | 6건 |
| 산출·계산 | 경계값(입력 범위 끝), 예외(0 나눗셈·결측치) | 6건 |

최소 케이스 수는 하한선이다. 입력 항목 수와 분기 수에 따라 늘어난다.
```

- [ ] **Step 7: 커맨드를 고친다**

`plugins/gx-pm/commands/gx-단위테스트계획서.md` 에서 화면목록표 선행조건과 화면 유형 판별 절을 지우고, AN-03·DE-08 을 입력으로 받게 바꾼다. `description` 도 갱신한다.

`plugins/gx-pm/templates/prerequisites.md` 의 `/gx-단위테스트계획서` 행의 하드 선행을
`AN-03 기능명세서` 로 바꾼다.

- [ ] **Step 8: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 9: 커밋**

```bash
git add plugins/gx-pm/templates/DE-13-unit-test-plan.md \
        plugins/gx-pm/skills/generate-unit-test-plan/SKILL.md \
        plugins/gx-pm/skills/design-test-cases/SKILL.md \
        plugins/gx-pm/commands/gx-단위테스트계획서.md \
        plugins/gx-pm/templates/prerequisites.md \
        plugins/gx-pm/utils/export-xlsx.py \
        plugins/gx-pm/tests/test_export_xlsx.py
git commit -m "refactor: 단위테스트계획서를 화면 27개 검사기준에서 기능 축 케이스로 바꾼다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

---

## Task 7: AN-05 추적매트릭스 기능 축 개편

29컬럼을 9컬럼으로 줄인다. `제안요청ID`·`수용여부`·화면·프로그램 컬럼이 사라진다.

**Files:**
- Modify: `plugins/gx-pm/templates/AN-05-traceability-matrix.md`
- Modify: `plugins/gx-pm/skills/trace-requirements/SKILL.md`
- Modify: `plugins/gx-pm/skills/id-trace/SKILL.md`
- Modify: `plugins/gx-pm/commands/gx-추적매트릭스.md`
- Modify: `plugins/gx-pm/utils/export-xlsx.py`
- Modify: `plugins/gx-pm/tests/test_export_xlsx.py` (`An05ColumnSsotTest`)

**Interfaces:**
- Consumes: Task 3~6의 AN-02·AN-03·DE-08·DE-13 컬럼
- Produces: AN-05 9컬럼

- [ ] **Step 1: 기존 SSOT 테스트를 새 절 이름에 맞춘다**

`An05ColumnSsotTest.setUp` 의 정규식 파싱을 Task 3 의 헬퍼로 교체한다.

```python
    def setUp(self):
        self.mod = load_export_module()
        self.정본컬럼 = parse_column_ssot(
            "AN-05-traceability-matrix.md", "본문 컬럼 (정본)"
        )
```

그리고 `test_정본_플랫_헤더가_비어있지_않다` 의 하한을 9로 낮춘다.

```python
    def test_정본_플랫_헤더가_비어있지_않다(self):
        """파싱이 조용히 빈 목록을 내면 아래 두 테스트가 공허하게 통과한다."""
        self.assertGreaterEqual(
            len(self.정본컬럼), 9,
            f"정본 헤더에서 뽑은 컬럼이 9개 미만입니다: {self.정본컬럼}",
        )
```

새 테스트를 추가한다.

```python
    def test_기능_축_컬럼이_정본에_있다(self):
        for 컬럼 in ["기능ID", "테이블·컬럼", "테스트 수", "Pass/Fail", "누락"]:
            with self.subTest(컬럼=컬럼):
                self.assertIn(컬럼, self.정본컬럼)

    def test_폐기된_컬럼이_정본에_없다(self):
        for 폐기 in ["제안요청ID", "수용여부", "화면ID", "프로그램ID", "과업완료여부"]:
            with self.subTest(컬럼=폐기):
                self.assertNotIn(폐기, self.정본컬럼)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_export_xlsx.An05ColumnSsotTest -v`
Expected: FAIL — 절 이름 `본문 컬럼 (정본)` 이 없어 빈 목록이 나온다

- [ ] **Step 3: 템플릿을 교체한다**

`plugins/gx-pm/templates/AN-05-traceability-matrix.md` 를 통째로 바꾼다.

```markdown
# AN-05 추적매트릭스 양식

## 파일 형식
Excel (.xlsx)

## 시트 구성
1. **개정이력** — 규칙의 정본은 `templates/revision-history.md`
2. **추적매트릭스** — 본문 데이터

## 이 문서는 대조기다

앞의 네 산출물을 읽어 **끊긴 곳을 찾는 것**이 본업이고, 표는 그 부산물이다.
새 정보를 만들지 않는다.

## 본문 컬럼 (정본)

| # | 컬럼 | 출처 |
|---|------|------|
| 1 | 요구사항ID | AN-02 |
| 2 | 요구사항명 | AN-02 |
| 3 | 상태 | AN-02 |
| 4 | 기능ID | AN-03 `연계요구사항ID` 역조회 |
| 5 | 기능명 | AN-03 |
| 6 | 테이블·컬럼 | DE-08 `연계기능ID` 역조회. `TB_SCORE (신규 4)` 형태 |
| 7 | 테스트 수 | DE-13 `연계기능ID`·`연계요구사항ID` 역조회 |
| 8 | Pass/Fail | DE-13 `결과` 집계. 미수행이면 `—` |
| 9 | 누락 | 아래 누락 판정표 |

## 누락 판정

| 유형 | 판정 조건 | 표기 |
|------|----------|------|
| 기능 미도출 | 기능 요구사항인데 연계된 기능이 0건 | `기능 미도출` |
| 테스트 미작성 | 기능이 있는데 테스트가 0건 | `테스트 미작성` |
| 비기능 검증 누락 | 어느 기능에도 안 걸린 요구사항인데 비기능 테스트도 0건 | `비기능 검증 누락` |
| 정상만 검증 | 그 기능의 테스트가 전부 정상 흐름 | `예외 케이스 없음` |
| 미수행 | 테스트는 있는데 `결과` 가 전건 공란 | `미수행` |
| 실패 잔존 | `Fail` 이 1건 이상 | `실패 {N}건` |
| 삭제 미정리 | 상태가 `삭제` 인데 연계된 기능·테스트가 살아 있음 | `삭제 미정리` |

**비기능 요구사항에 기능ID 가 없는 것은 누락이 아니다.** DE-13 의 `연계기능ID` 공란
행으로 검증되면 정상이다.

## 예시 행

| 요구사항ID | 요구사항명 | 상태 | 기능ID | 기능명 | 테이블·컬럼 | 테스트 수 | Pass/Fail | 누락 |
|---|---|---|---|---|---|---|---|---|
| REQ-001 | 벤치마크 스코어테이블 생성 기능 | 유지 | FN-001 | 벤치마크 스코어테이블 생성 | TB_SCORE (신규 4) | 6 | 6/0 | |
| REQ-045 | 동시접속 500명 응답 3초 | 신규 | | | | 2 | 0/0 | 미수행 |
| REQ-032 | 업로드 통계 데이터 조회 | 신규 | | | | 0 | — | 기능 미도출 |

## 작성 규칙

- 요구사항 1건이 기능 여러 개에 걸리면 행을 나누고 요구사항ID 를 세로 병합한다
- 이 표는 손으로 채우지 않는다. 네 산출물에서 기계적으로 조립한다
- 개정이력 기입은 `skills/manage-revision-history` 가 담당한다
```

- [ ] **Step 4: export 프로파일을 교체한다**

축약 세트를 지우고 하나만 남긴다.

```python
    "추적매트릭스": {
        "sheet_name": "추적매트릭스",
        # 컬럼 정본은 templates/AN-05-traceability-matrix.md 의
        # 「본문 컬럼 (정본)」 절이다. 양방향 계약 테스트가 묶고 있다.
        "columns": [[
            "요구사항ID", "요구사항명", "상태", "기능ID", "기능명",
            "테이블·컬럼", "테스트 수", "Pass/Fail", "누락",
        ]],
        "merge_columns": ["요구사항ID"],
    },
```

- [ ] **Step 5: `trace-requirements` 와 `id-trace` 스킬을 고친다**

화면·프로그램·통합테스트·시스템테스트 조회 절을 지우고, 위 9컬럼과 누락 판정표를 따르게 한다.
누락 유형은 템플릿을 정본으로 참조만 하고 복제하지 않는다.

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add plugins/gx-pm/templates/AN-05-traceability-matrix.md \
        plugins/gx-pm/skills/trace-requirements/SKILL.md \
        plugins/gx-pm/skills/id-trace/SKILL.md \
        plugins/gx-pm/commands/gx-추적매트릭스.md \
        plugins/gx-pm/utils/export-xlsx.py \
        plugins/gx-pm/tests/test_export_xlsx.py
git commit -m "refactor: 추적매트릭스를 기능 축 9컬럼 대조기로 줄인다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

---

## Task 8: ID 체계와 파이프라인 규약 교체

파생 ID 가 사라졌으므로 체인과 이월 금지 항목·파급 규칙을 다시 쓴다.

**Files:**
- Modify: `plugins/gx-pm/templates/id-naming-rules.md`
- Modify: `plugins/gx-pm/templates/pipeline-protocol.md`
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (`PipelineProtocolTest` 수정)

**Interfaces:**
- Consumes: Task 3~7의 ID 컬럼
- Produces: 이월 금지 3항목·파급 규칙표 — Task 9의 `/gx-spec` 이 참조한다

- [ ] **Step 1: 기존 테스트를 새 규약에 맞춰 고친다**

`test_plugin_consistency.py` 의 `PipelineProtocolTest` 에서
`test_이월_금지_항목에_화면_분리_미결정이_있다` 를 **삭제**하고 아래로 교체한다.

```python
    def test_이월_금지_항목이_세_개다(self):
        """화면 축 제거로 화면 분리·ID 확정 두 항목이 소멸했다."""
        구간 = re.search(
            r"^## 이월 금지 항목$(.*?)(?=^## )", self.규약, re.M | re.S
        )
        self.assertIsNotNone(구간, "이월 금지 항목 절을 찾지 못했습니다")
        번호 = re.findall(r"^\d+\.\s", 구간.group(1), re.M)
        self.assertEqual(
            len(번호), 3,
            f"이월 금지 항목이 3개가 아닙니다: {len(번호)}개",
        )

    def test_이월_금지_항목에_신규_컬럼명_결정이_있다(self):
        self.assertIn("신규 컬럼명 결정", self.규약)
        self.assertIn("convert-ddl-to-tablespec", self.규약)

    def test_화면_축_잔재가_규약에_없다(self):
        for 잔재 in ["화면ID", "화면 분리", "PG_", "generate-screen-list"]:
            with self.subTest(잔재=잔재):
                self.assertNotIn(잔재, self.규약)
```

`test_파생_ID가_모두_재생성_파급_규칙에_있다` 는 파생 ID 가 없어졌으므로 아래로 교체한다.

```python
    def test_파급_규칙이_다섯_갈래를_모두_덮는다(self):
        구간 = re.search(
            r"^## 재생성 파급 규칙$(.*?)(?=^## |\Z)", self.규약, re.M | re.S
        )
        self.assertIsNotNone(구간, "재생성 파급 규칙 절을 찾지 못했습니다")
        본문 = 구간.group(1)
        for 항목 in [
            "요구사항ID", "요구사항 상세내용", "기능ID",
            "입력항목", "컬럼 제약",
        ]:
            with self.subTest(항목=항목):
                self.assertIn(항목, 본문)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.PipelineProtocolTest -v`
Expected: FAIL — 이월 금지 항목이 5개이고 `화면ID` 잔재가 남아 있다

- [ ] **Step 3: `id-naming-rules.md` 를 교체한다**

`## ID 체인` 절부터 `### 화면ID` 이하 파생 ID 절을 전부 아래로 바꾼다.
`## 시스템 코드` 절은 남긴다 (프로파일이 참조한다).

```markdown
## ID 체인

```
요구사항ID (기본 REQ-{3자리})
  └→ 기능ID (기본 FN-{3자리})            ← 파생 아님. 독립 채번, N:M 매핑
       ├→ 테이블·컬럼 (DE-08)            ← 입력항목이 컬럼으로 매핑된다
       └→ 테스트ID (기본 UT-{3자리})     ← 파생 아님. 독립 채번, N:1 매핑
```

**파생 ID 가 없다.** 어떤 ID 도 다른 ID 에서 만들어지지 않으므로,
상위 ID 가 바뀌어도 하위 ID 를 재채번할 필요가 없다. 연결은 전부 `연계~ID` 열이 맡는다.

기능ID 를 요구사항ID 에서 파생시키지 않는 이유: 기능 1개가 요구사항 여러 건을 덮는 경우가
흔하고, 파생형은 그 경우를 표현하지 못한다.

## 채번 규칙은 프로파일이 정한다

접두어·자릿수는 프로젝트마다 다르다. 프로파일에 없으면 커맨드가 AskUserQuestion 으로
한 번 묻고 저장한다.

| ID | 기본 제안 | 대안 예 |
|----|---------|--------|
| 요구사항ID | `REQ-001` | `B-RE-001` (시스템코드 포함) |
| 기능ID | `FN-001` | `B-FN-001` |
| 테스트ID | `UT-001` | `B-UT-001` |

## 불변 규칙

- 한 번 부여한 ID 는 바꾸지 않는다
- 삭제해도 재사용하지 않는다. 순번에 구멍이 남는 것을 허용한다
- 재실행 시 마지막 순번 다음부터 이어서 부여한다

## 비기능 요구사항

기능ID 를 갖지 않는다. DE-13 에서 `연계기능ID` 공란 행으로 검증되면 정상이며,
`연계요구사항ID` 만으로 추적된다.
```

- [ ] **Step 4: `pipeline-protocol.md` 를 교체한다**

`## 단독 실행 vs 파이프라인 실행` 표에서 `화면 분리 미결정 중단점` 행을
`신규 컬럼명 결정 중단점` 으로 바꾼다. 그리고 두 절을 교체한다.

```markdown
## 이월 금지 항목

다음 세 가지는 **절대 게이트로 미루지 않는다.**

1. **시안/대안 감지 중단점** — 시안 선택이 틀리면 뒤 산출물이 전부 틀린다.
2. **표 판정 애매성 중단점** — ID 표가 요구사항 표인지 애매한데 추정하면, 유령 요구사항이
   들어오거나 진짜 요구사항이 빠져 요구사항 건수가 흔들린다. 그 건수가 추적매트릭스 행 수를
   정하므로 게이트에 도달했을 때는 이미 늦다. 판정 기준과 묻는 방법은
   `skills/extract-requirements/SKILL.md` Step 2 가 정본이다.
3. **신규 컬럼명 결정 중단점** — 표준용어 MCP 가 `decisionRequired` 를 내면 그 자리에서
   물어야 한다. 컬럼명이 확정돼야 단위테스트의 경계값이 그 위에 선다. 판정 기준은
   `skills/convert-ddl-to-tablespec/SKILL.md` Step 4 가 정본이다.

## 재생성 파급 규칙

| 바뀐 것 | 함께 재생성해야 하는 것 |
|---------|--------------------|
| 요구사항ID | 기능명세서·단위테스트계획서의 연계ID 전건 |
| 요구사항 상세내용 | 그 요구사항을 연계한 기능 행 → 테이블(신규 컬럼) → 그 기능의 테스트 전건 |
| 기능ID | 테이블정의서·단위테스트계획서의 연계기능ID 전건 |
| 기능 입력항목·처리내용 | 테이블(신규 컬럼) → 그 기능의 테스트 케이스 전건 |
| 테이블 컬럼 제약 | 그 컬럼을 쓰는 테스트의 경계·필수값 케이스 |

이 표는 `templates/id-naming-rules.md` 의 ID 체인에서 도출된 것이다.
연결 관계가 바뀌면 두 파일을 **함께** 고친다.

게이트에서 영향 범위를 먼저 보여주고 재생성 여부를 묻는다.

```
REQ-005 변경의 영향: 기능 1건(FN-007), 컬럼 2건, 테스트 5건(UT-014~UT-018)
  1. 전부 재생성
  2. 기능명세서만 재생성
  3. 표시만 하고 두기
```
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: `PipelineProtocolTest` PASS. 다른 문서에 남은 화면 축 잔재로 `test_예시_ID_가_네이밍_규칙을_따른다` 가 실패할 수 있다 — Task 9 에서 해당 문서를 archive 로 내리면 해소되므로, 실패 문서가 archive 대상 목록에 있는지 확인하고 아니면 지금 고친다.

- [ ] **Step 6: 커밋**

```bash
git add plugins/gx-pm/templates/id-naming-rules.md \
        plugins/gx-pm/templates/pipeline-protocol.md \
        plugins/gx-pm/tests/test_plugin_consistency.py
git commit -m "refactor: ID 체인을 3단으로 줄이고 이월 금지를 3항목으로 정리한다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

---

## Task 9: 화면 축 archive 이동과 `/gx-spec` 재정의

이 작업 하나로 플러그인 표면이 16커맨드에서 7커맨드로 줄어든다. 새 산출물이 전부 준비된 뒤에 한다.

**Files:**
- Create: `plugins/gx-pm/archive/README.md`
- Move: 커맨드 9개, 스킬 13개, 템플릿 7개 → `plugins/gx-pm/archive/`
- Modify: `plugins/gx-pm/tests/helpers.py`
- Modify: `plugins/gx-pm/commands/gx-spec.md`
- Modify: `plugins/gx-pm/templates/prerequisites.md`
- Modify: `plugins/gx-pm/utils/export-xlsx.py`
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py`

**Interfaces:**
- Consumes: Task 8의 이월 금지 3항목
- Produces: 7커맨드 표면 — Task 10의 README 카운트 테스트가 읽는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
class ArchiveIsolationTest(unittest.TestCase):
    """archive/ 는 보관소다. 계약 검사 대상이 아니다.

    삭제하지 않는 이유: 감리가 있는 공공 사업이 오면 화면 축 산출물을 되살린다.
    검사 대상으로 두면 옛 컬럼·옛 ID 규칙이 새 계약을 전부 깨뜨린다.
    """

    def test_archive_문서가_계약_검사에서_빠진다(self):
        보관경로 = [
            path for path, _ in read_docs()
            if "archive" in path.parts
        ]
        self.assertEqual(
            보관경로, [],
            f"archive/ 문서가 검사 대상에 들어 있습니다: {보관경로}",
        )

    def test_archive에_설명이_있다(self):
        readme = PLUGIN_ROOT / "archive" / "README.md"
        self.assertTrue(readme.exists(), "archive/README.md 가 없습니다")
        self.assertIn("되살리는 방법", readme.read_text(encoding="utf-8"))


class SurfaceTest(unittest.TestCase):
    """기능 축 전환 후 사용자에게 보이는 표면."""

    def test_커맨드가_일곱_개다(self):
        self.assertEqual(
            sorted(command_names()),
            sorted([
                "gx-프로젝트설정", "gx-spec",
                "gx-요구사항정의서", "gx-기능명세서", "gx-테이블정의서",
                "gx-단위테스트계획서", "gx-추적매트릭스",
            ]),
        )

    def test_화면_축_커맨드가_남아있지_않다(self):
        for 내린것 in [
            "gx-화면목록표", "gx-프로그램정의서", "gx-인터페이스정의서",
            "gx-결함관리대장", "gx-총괄테스트계획서", "gx-시스템테스트",
            "gx-테스트결과서", "gx-감리대응", "gx-testplan",
        ]:
            with self.subTest(커맨드=내린것):
                self.assertNotIn(내린것, command_names())

    def test_spec_파이프라인이_다섯_산출물을_순서대로_부른다(self):
        text = (PLUGIN_ROOT / "commands" / "gx-spec.md").read_text(encoding="utf-8")
        순서 = [
            "/gx-요구사항정의서", "/gx-기능명세서", "/gx-테이블정의서",
            "/gx-단위테스트계획서", "/gx-추적매트릭스",
        ]
        위치 = [text.find(c) for c in 순서]
        self.assertNotIn(-1, 위치, f"파이프라인에 빠진 커맨드가 있습니다: {순서}")
        self.assertEqual(위치, sorted(위치), "파이프라인 산출물이 파생 순서대로가 아닙니다")

    def test_spec_파이프라인에_게이트가_세_개다(self):
        text = (PLUGIN_ROOT / "commands" / "gx-spec.md").read_text(encoding="utf-8")
        for 게이트 in ["게이트 1", "게이트 2", "게이트 3"]:
            with self.subTest(게이트=게이트):
                self.assertIn(게이트, text)
        self.assertNotIn("게이트 4", text)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.SurfaceTest -v`
Expected: FAIL — 커맨드가 17개(Task 4 신설 포함)다

- [ ] **Step 3: `read_docs()` 가 archive 를 건너뛰게 한다**

`plugins/gx-pm/tests/helpers.py` 의 `read_docs()` 안 루프에 조건을 추가한다.
`.omc` 검사 바로 아래에 넣는다.

```python
        if "archive" in path.parts:
            continue  # archive/ 는 보관소다. 옛 컬럼·옛 ID 규칙이 새 계약을 깨뜨린다
```

docstring 에도 한 줄 추가한다.

```
    archive/ 는 커맨드에서 내린 산출물의 보관소라 검사 대상이 아니다.
```

- [ ] **Step 4: 파일을 archive 로 옮긴다**

```bash
cd plugins/gx-pm
mkdir -p archive/commands archive/skills archive/templates

for c in gx-화면목록표 gx-프로그램정의서 gx-인터페이스정의서 gx-결함관리대장 \
         gx-총괄테스트계획서 gx-시스템테스트 gx-테스트결과서 gx-감리대응 gx-testplan; do
  git mv "commands/$c.md" "archive/commands/$c.md"
done

for s in generate-screen-list generate-program-list generate-interface-spec \
         manage-defects generate-master-test-plan generate-system-test \
         fill-unit-test-result fill-integration-test-result audit-response \
         generate-integration-test generate-erd-guide reverse-scan-source \
         reverse-scan-interfaces; do
  git mv "skills/$s" "archive/skills/$s"
done

for t in DE-03-screen-list.md DE-05-program-definition.md \
         DE-14-integration-test-plan.md TE-01-master-test-plan.md \
         ST-01-system-test.md DF-01-defect-log.md inspection-criteria.md; do
  git mv "templates/$t" "archive/templates/$t"
done
```

- [ ] **Step 5: archive 설명을 쓴다**

`plugins/gx-pm/archive/README.md`:

```markdown
# archive — 커맨드에서 내린 산출물

2026-09-03 기능 축 전환(v3.0.0)으로 커맨드 표면에서 내린 파일들이다.
**삭제하지 않은 이유**: 감리가 있는 공공 사업은 화면목록표·감리대응·총괄테스트계획서를
여전히 요구한다. 그때 되살린다.

## 여기 있는 것

| 종류 | 파일 |
|------|------|
| 커맨드 | 화면목록표 · 프로그램정의서 · 인터페이스정의서 · 결함관리대장 · 총괄테스트계획서 · 시스템테스트 · 테스트결과서 · 감리대응 · testplan |
| 스킬 | 위 커맨드가 쓰던 13개 |
| 템플릿 | DE-03 · DE-05 · DE-14 · TE-01 · ST-01 · DF-01 · inspection-criteria |

## 되살리는 방법

1. 해당 파일을 `commands/` · `skills/` · `templates/` 로 되돌린다
2. `templates/prerequisites.md` 에 선행조건 행을 추가한다
3. 화면ID 파생 규칙(`PG_` · `U_` · `TC_`)이 필요하면 `templates/id-naming-rules.md` 에
   되살린다 — 현재 체인에는 파생 ID 가 없다
4. 옛 컬럼(`제안요청ID` · `수용여부` · `화면ID`)을 참조하는 곳을 현재 컬럼으로 고친다
5. 테스트를 돌린다: `python -m unittest discover -s tests -v`

## 주의

`tests/helpers.py` 의 `read_docs()` 가 이 디렉터리를 건너뛴다.
여기 있는 파일은 계약 검사를 받지 않으므로, 되살릴 때 반드시 4번을 한다.
```

- [ ] **Step 6: `/gx-spec` 을 5종 3게이트로 재작성한다**

`plugins/gx-pm/commands/gx-spec.md` 를 통째로 바꾼다.

```markdown
---
description: "명세 5종을 한 번에 만듭니다. 요구사항정의서 → 기능명세서 → 테이블정의서 → 단위테스트계획서 → 추적매트릭스를 게이트 3개로 확정. | 자연어: 산출물 한번에, 명세 다 만들어줘, 처음부터 만들어줘, 산출물 쫙 뽑아줘"
---

# /gx-spec — 명세 5종 일괄 생성

사용자는 커맨드 순서를 알 필요가 없다. **게이트 3곳에서만** 판단하면 된다.

> **선행조건**: `templates/prerequisites.md` 의 `/gx-spec` 행을 따른다.
> **실행 규약**: `templates/pipeline-protocol.md` 를 따른다. 개별 커맨드의 산출물별
> 승인 루프는 게이트로 이월하고, 이월 금지 3항목은 이월하지 않는다.

## 구성

| 순서 | 산출물 | 단독 커맨드 |
|------|--------|-----------|
| 1 | AN-02 요구사항정의서 | `/gx-요구사항정의서` |
| 2 | AN-03 기능명세서 | `/gx-기능명세서` |
| 3 | DE-08 테이블정의서 | `/gx-테이블정의서` |
| 4 | DE-13 단위테스트계획서 | `/gx-단위테스트계획서` |
| 5 | AN-05 추적매트릭스 | `/gx-추적매트릭스` |

## Step 0: 프로젝트 컨텍스트 로드

**load-project-profile** 스킬로 활성 프로젝트를 확인한다. 없으면 `/gx-프로젝트설정` 안내 후 종료.

**detect-existing-artifact** 스킬로 기존 산출물 5종을 확인한다.

채번 규칙이 프로파일에 없으면 여기서 한 번 묻고 저장한다.

```
요구사항ID·기능ID·테스트ID 채번 규칙을 정해주세요.
  1. REQ-001 / FN-001 / UT-001   (참조 양식과 동일)
  2. B-RE-001 / B-FN-001 / B-UT-001   (시스템코드 포함)
  3. 직접 입력
```

## Step 1: 묶음 선행조건 검사

**하드 선행**은 `templates/prerequisites.md` 의 `/gx-spec` 행만 따른다 (프로파일).
구성 5종 각각의 하드 선행은 이 파이프라인이 스스로 만드는 산출물이므로 여기서 적용하지 않는다.

## Step 2: 요구사항정의서 생성

`/gx-요구사항정의서` 의 시안/대안 감지 → 추출 → 행 분할 → 분류 단계를 수행한다.
표 판정 애매성 중단점은 **이월하지 않는다.**

## Step 3: 게이트 1 — 요구사항 승인 [필수 중단점]

요구사항 건수가 뒤 산출물 전체의 행 수를 정하므로 **반드시 단독 게이트**다.

승인 후 `manage-revision-history` 로 AN-02 개정이력을 기록한다.

## Step 4: 기능명세서 생성

`/gx-기능명세서` 의 생성 단계를 수행한다. `[확인필요]` 목록을 모아 둔다.

## Step 5: 테이블정의서 생성

`/gx-테이블정의서` 의 생성 단계를 수행한다.
신규 컬럼명 결정 중단점은 **이월하지 않는다** — MCP 가 `decisionRequired` 를 내면 그 자리에서 묻는다.

## Step 6: 게이트 2 — 기능 + 테이블 승인 [필수 중단점]

기능의 입력항목이 곧 컬럼이라 따로 보면 판단이 안 된다. 함께 보여준다.

- AN-03 기능명세 표
- DE-08 테이블정의 표 (신규 컬럼 강조)
- `[확인필요]` 목록
- 제약 불일치 목록

승인 후 `manage-revision-history` 로 AN-03·DE-08 개정이력을 기록한다.

## Step 7: 단위테스트계획서 생성

`/gx-단위테스트계획서` 의 생성 단계를 수행한다. 비기능 요구사항은
`연계기능ID` 공란 행으로 만든다.

## Step 8: 추적매트릭스 생성

`/gx-추적매트릭스` 의 생성 단계를 수행한다. 누락 목록을 뽑는다.

## Step 9: 게이트 3 — 테스트 + 추적 결과 승인 [필수 중단점]

- DE-13 단위테스트계획 표
- AN-05 추적매트릭스 표
- 누락 유형별 건수

승인 후 `manage-revision-history` 로 DE-13·AN-05 개정이력을 기록한다.

## Step 10: xlsx 추출

`utils/export-xlsx.py` 로 5개 파일을 추출한다.

## 재생성 파급

게이트에서 수정 요청이 오면 `templates/pipeline-protocol.md` 의 재생성 파급 규칙에 따라
하위 산출물도 함께 재생성한다. 영향 범위를 먼저 보여주고 묻는다.
```

- [ ] **Step 7: 선행조건 레지스트리와 남는 공용 스킬을 정리한다**

`plugins/gx-pm/templates/prerequisites.md` 에서 archive 로 내린 커맨드 9개의 행을 지운다.
`/gx-spec` 행의 구성 산출물 설명을 5종으로 갱신한다.

남는 공용 스킬 6개가 사라진 산출물을 참조한다. 각 파일에서 산출물 목록을 5종으로 줄이고
화면 축 어휘(`화면목록표` · `화면ID` · `프로그램정의서` · `제안요청ID` · `수용여부`)를 없앤다.

| 스킬 | 고칠 곳 |
|------|--------|
| `load-project-profile` | 프로파일이 로드하는 산출물 목록 → 5종. 채번 규칙 항목 추가 |
| `detect-existing-artifact` | 감지 대상 파일명 목록 → 5종 |
| `detect-alternatives` | 대안 감지 대상 산출물 목록 → 5종 |
| `classify-requirements` | 구분(기능/비기능) 판정은 유지. `수용여부` 초안 절 삭제 |
| `prioritize-si` | 우선순위 산출 대상을 요구사항으로 한정. 화면 우선순위 절 삭제 |
| `impact-analysis` | 영향도 추적 경로를 새 3단 체인으로 교체 |

고친 뒤 **고아 스킬이 없는지** 확인한다. archive 로 내린 커맨드에서만 불리던 스킬이
남아 있으면 `test_모든_스킬이_어느_커맨드에서든_호출된다` 가 잡는다.

```bash
cd plugins/gx-pm
for s in $(ls -d skills/*/ | xargs -n1 basename); do
  grep -qr -- "$s" commands/ || echo "고아 스킬: $s"
done
```

출력이 나오면 그 스킬을 부르는 커맨드에 호출 지점을 넣거나, 쓰이지 않으면 archive 로 내린다.

- [ ] **Step 8: export 프로파일에서 내린 산출물을 지운다**

`DOCUMENT_PROFILES` 에서 아래 키를 삭제한다.

```
화면목록표 · 프로그램정의서 · 인터페이스정의서 · 총괄테스트계획서 ·
단위테스트결과서 · 통합테스트시나리오 · 통합테스트결과서 · 인수테스트결과서 ·
시스템테스트계획서 · 시스템테스트결과서 · 결함관리대장
```

남는 것은 6개다: `개정이력` · `요구사항정의서` · `기능명세서` · `테이블정의서` ·
`단위테스트계획서` · `추적매트릭스`.

- [ ] **Step 9: 테스트가 통과하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: `SurfaceTest`·`ArchiveIsolationTest` PASS. README 카운트 테스트
(`test_README_배지가_실제_스킬_커맨드_수와_같다` 등)는 Task 10 에서 해소되므로 여기서는 실패해도 된다. 그 외 실패는 여기서 고친다.

- [ ] **Step 10: 커밋**

```bash
git add -A plugins/gx-pm
git commit -m "refactor: 화면 축 산출물을 archive 로 내리고 spec 을 5종 3게이트로 재정의한다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

---

## Task 10: 문서·버전 정리와 통합 계약

표면이 바뀌었으므로 README·CHANGELOG·CLAUDE.md·매니페스트를 맞추고, 5종이 개정이력을 빠짐없이 참조하는지 묶는다.

**Files:**
- Modify: `README.md`, `plugins/gx-pm/CLAUDE.md`, `plugins/gx-pm/CHANGELOG.md`
- Modify: `plugins/gx-pm/.claude-plugin/plugin.json`, `plugins/gx-pm/.codex-plugin/plugin.json`
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py`

**Interfaces:**
- Consumes: Task 1~9 전부

- [ ] **Step 1: 통합 계약 테스트를 쓴다**

```python
class FiveDocumentContractTest(unittest.TestCase):
    """산출물 5종이 같은 규약을 따르는지 묶는다."""

    산출물스킬 = [
        "extract-requirements",
        "generate-function-spec",
        "convert-ddl-to-tablespec",
        "generate-unit-test-plan",
        "trace-requirements",
    ]

    def test_다섯_스킬이_모두_개정이력_스킬을_부른다(self):
        for 스킬 in self.산출물스킬:
            with self.subTest(스킬=스킬):
                text = (
                    PLUGIN_ROOT / "skills" / 스킬 / "SKILL.md"
                ).read_text(encoding="utf-8")
                self.assertIn(
                    "manage-revision-history", text,
                    "개정이력을 기록하지 않으면 버전이 올라가지 않습니다",
                )

    def test_다섯_템플릿이_모두_개정이력_시트를_선언한다(self):
        for 템플릿 in [
            "AN-02-requirements-definition.md",
            "AN-03-function-spec.md",
            "DE-08-table-definition.md",
            "DE-13-unit-test-plan.md",
            "AN-05-traceability-matrix.md",
        ]:
            with self.subTest(템플릿=템플릿):
                text = (PLUGIN_ROOT / "templates" / 템플릿).read_text(encoding="utf-8")
                self.assertIn("templates/revision-history.md", text)

    def test_다섯_템플릿이_모두_본문_컬럼_정본_절을_갖는다(self):
        from helpers import parse_column_ssot
        for 템플릿, 개수 in [
            ("AN-02-requirements-definition.md", 10),
            ("AN-03-function-spec.md", 10),
            ("DE-08-table-definition.md", 15),
            ("DE-13-unit-test-plan.md", 11),
            ("AN-05-traceability-matrix.md", 9),
        ]:
            with self.subTest(템플릿=템플릿):
                self.assertEqual(
                    len(parse_column_ssot(템플릿, "본문 컬럼 (정본)")), 개수
                )

    def test_화면_축_잔재가_현역_문서에_없다(self):
        """archive/ 밖에는 화면 축 어휘가 남으면 안 된다."""
        잔재 = ["화면목록표", "PG_{화면ID}", "제안요청ID", "수용여부"]
        for path, text in specs_only(read_docs()):
            for 낱말 in 잔재:
                with self.subTest(문서=doc_label(path), 낱말=낱말):
                    self.assertNotIn(낱말, text)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd plugins/gx-pm && python -m unittest tests.test_plugin_consistency.FiveDocumentContractTest -v`
Expected: FAIL — README·CLAUDE.md 에 `화면목록표` 가 남아 있다

- [ ] **Step 3: `plugins/gx-pm/CLAUDE.md` 를 고친다**

ID 체인 도식을 `templates/id-naming-rules.md` 의 3단 체인으로 바꾸고,
"시작하기" 절의 `/gx-testplan` 안내를 지운다. 산출물 목록을 5종으로 줄인다.
"체인 갈래 3개" 설명을 아래로 바꾼다.

```markdown
**갈래가 둘입니다.** 기능 요구사항은 기능명세를 거쳐 테스트로,
비기능 요구사항은 기능을 거치지 않고 바로 테스트로 갑니다
(DE-13 의 `연계기능ID` 공란 행).

**파생 ID 가 없습니다.** 어떤 ID 도 다른 ID 에서 만들어지지 않으므로,
ID 를 바꿔도 재채번 파급이 없습니다. 연결은 전부 `연계~ID` 열이 맡습니다.
```

- [ ] **Step 4: `README.md` 를 고친다**

- 배지의 스킬·커맨드 수를 실제와 맞춘다 (`test_README_배지가_실제_스킬_커맨드_수와_같다`)
- 디렉터리 구조 트리를 실제 파일과 맞춘다 (`test_README_디렉토리_트리의_개수가_실제와_같다`).
  `archive/` 도 트리에 넣는다
- 설명문의 스킬·커맨드 수를 맞춘다 (`test_설명문의_스킬_커맨드_수가_실제와_같다`)
- 산출물 목록과 사용 예시를 5종으로 바꾼다

실제 수를 먼저 확인한다.

```bash
cd plugins/gx-pm
echo "커맨드: $(ls commands/*.md | wc -l)"
echo "스킬:   $(ls -d skills/*/ | wc -l)"
echo "템플릿: $(ls templates/*.md | wc -l)"
```

- [ ] **Step 5: 버전을 v3.0.0 으로 올린다**

세 곳을 같은 값으로 바꾼다 (`test_모든_매니페스트의_버전이_같다`).

```bash
cd plugins/gx-pm
grep -rn '"version"' .claude-plugin/plugin.json .codex-plugin/plugin.json
```

`CHANGELOG.md` 맨 위에 항목을 추가한다.

```markdown
## [3.0.0] - 2026-09-03

**Breaking.** 플러그인을 화면 축에서 기능 축으로 재정렬했다.
산출물이 13종에서 **5종**으로, 커맨드가 16개에서 **7개**로 줄었다.

### Added

- **기능명세서(AN-03)** — 요구사항과 테스트 사이의 빠진 고리.
  `입력항목`·`처리내용(로직)`이 테이블 컬럼과 테스트 케이스의 유일한 근거가 된다
- **개정이력** (`templates/revision-history.md`, `manage-revision-history` 스킬) —
  5종 공통 횡단. 재생성 시 직전 버전과 대조해 초안을 만들고 승인을 받는다
- **xlsx 연속 동일값 세로 병합** — 참조 양식의 대분류·중분류 병합 형태

### Changed

- **요구사항정의서(AN-02)** — `제안요청ID`·`구분`·`소분류`·`요구내역`·`수용여부` 폐기,
  `번호`·`요구사항명`·`상태`·`변경 근거` 추가. 삭제 요구사항은 행을 남기고 상태만 바꾼다
- **테이블정의서(DE-08)** — 순방향(요구사항→테이블) 폐지. 기존 스키마는 역생성으로 고정하고
  신규 컬럼만 표준용어 MCP 근거로 제안한 뒤 승인받는다. 기존 비표준 컬럼은 `현행유지`
- **단위테스트계획서(DE-13)** — 화면 27개 검사기준 체크리스트 폐지.
  기능 축 11컬럼 단일 시트. 결과는 `Pass`/`Fail` 2값
- **추적매트릭스(AN-05)** — 29컬럼 → 9컬럼 대조기
- **ID 체계** — 파생 ID 전면 폐지. 요구사항 → 기능 → 테스트 3단, 전부 독립 채번
- **이월 금지 항목** 5개 → 3개. `신규 컬럼명 결정`이 새로 들어오고
  `화면 분리 미결정`·`ID 확정 게이트`가 소멸
- **`/gx-spec`** — 5종 파이프라인, 게이트 3개

### Removed

커맨드 9개·스킬 13개·템플릿 7개를 `plugins/gx-pm/archive/` 로 옮겼다.
삭제가 아니라 보관이며, 되살리는 방법은 `archive/README.md` 에 있다.

- 커맨드: 화면목록표 · 프로그램정의서 · 인터페이스정의서 · 결함관리대장 ·
  총괄테스트계획서 · 시스템테스트 · 테스트결과서 · 감리대응 · testplan
- 비기능 요구사항은 시스템테스트(ST-01) 대신 DE-13 의 `연계기능ID` 공란 행으로 검증한다
```

- [ ] **Step 6: 전체 테스트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: PASS (전건)

- [ ] **Step 7: 실제 xlsx 로 5종 추출을 확인한다**

```bash
cd plugins/gx-pm
python - <<'PY'
from pathlib import Path
샘플 = Path("/tmp/gx샘플"); 샘플.mkdir(exist_ok=True)
(샘플/"B-요구사항정의서.md").write_text("""## 개정이력

| 버전 | 개정일 | 개정 사유 | 개정 내용 | 작성자 | 승인자 |
|------|--------|----------|----------|--------|--------|
| 1.0 | 2026.09.03 | 신규 | 최초 작성 | 구본승 | |

## 요구사항 명세

| 번호 | 요구사항ID | 대분류 | 중분류 | 요구사항명 | 요구사항 상세내용 | 비고 | 상태 | 요구사항 근거 | 변경 근거 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | REQ-001 | 전처리 | 기준 생성 | 스코어테이블 생성 기능 | 원단위 통계로 EUI 테이블 생성 | | 신규 | 과업지시서 | |
| 2 | REQ-002 | 전처리 | 기준 생성 | 도일 생성 기능 | ASOS 자료로 냉난방도일 생성 | | 신규 | 과업지시서 | |
""", encoding="utf-8")
PY
python utils/export-xlsx.py /tmp/gx샘플/B-요구사항정의서.md --output /tmp/gx샘플/out.xlsx
python -c "
import openpyxl
wb = openpyxl.load_workbook('/tmp/gx샘플/out.xlsx')
print('시트:', wb.sheetnames)
ws = wb['요구사항 명세']
print('헤더:', [c.value for c in ws[1]])
print('병합:', ws.merged_cells.ranges)
"
```
Expected: 시트 `['개정이력', '요구사항 명세']`, 헤더가 정본 10컬럼 순서, 병합에 `C2:C3`·`D2:D3` 포함

- [ ] **Step 8: 커밋**

```bash
git add -A
git commit -m "docs: v3.0.0 — 기능 축 5종으로 문서·버전·매니페스트를 맞춘다

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY"
```

- [ ] **Step 9: PR 을 올린다**

```bash
git push -u origin feat/function-axis-five-doc
gh pr create --title "기능 축 5종 산출물 파이프라인 (v3.0.0)" --body "$(cat <<'EOF'
## 무엇을 바꿨나

플러그인을 화면 축에서 기능 축으로 재정렬했다. 산출물 13종 → **5종**, 커맨드 16개 → **7개**.

요구사항 → 기능 → 테이블 → 테스트 → 추적. 파생 ID 가 없어 ID 를 바꿔도 재채번 파급이 없다.

## 산출물 5종

| 산출물 | 컬럼 | 비고 |
|--------|------|------|
| AN-02 요구사항정의서 | 10 | 상태·변경 근거 중심. 삭제 행을 남긴다 |
| AN-03 기능명세서 | 10 | **신설.** 입력항목·처리내용이 뒤 전부의 근거 |
| DE-08 테이블정의서 | 15 | 순방향 폐지. 신규 컬럼만 표준용어 MCP 로 제안·승인 |
| DE-13 단위테스트계획서 | 11 | 화면 27개 검사기준 폐지. Pass/Fail |
| AN-05 추적매트릭스 | 9 | 29컬럼에서 축소. 대조기 |

다섯 문서 모두 **개정이력 시트**를 갖고, 재생성 시 직전 버전과 대조해 행을 자동 생성한다.

## 되돌리기

내린 커맨드·스킬·템플릿은 삭제하지 않고 `plugins/gx-pm/archive/` 에 있다.
되살리는 방법은 `archive/README.md` 참조.

## 설계·계획

- 설계서: `docs/superpowers/specs/2026-09-03-function-axis-three-doc-design.md`
- 계획서: `docs/superpowers/plans/2026-09-03-function-axis-five-doc-pipeline.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
)"
```

---

## 실행 순서 요약

| Task | 무엇 | 깨지는 것 |
|------|------|----------|
| 1 | 개정이력 정본 + 횡단 스킬 | 없음 (신설) |
| 2 | export 세로 병합 + 개정이력 시트 | 없음 (신설) |
| 3 | AN-02 컬럼 교체 | AN-02 참조처 |
| 4 | AN-03 신설 | 없음 (신설) |
| 5 | DE-08 재작성 | 순방향 경로 |
| 6 | DE-13 재작성 | 27개 검사기준 참조처 |
| 7 | AN-05 개편 | 옛 29컬럼 참조처 |
| 8 | ID·파이프라인 규약 | 화면 축 잔재 전부 |
| 9 | archive 이동 + `/gx-spec` | **표면 전체** |
| 10 | 문서·버전 | README 카운트 |

Task 9 가 가장 크고 되돌리기 어렵다. Task 1~8 이 전부 녹색일 때만 진입한다.
