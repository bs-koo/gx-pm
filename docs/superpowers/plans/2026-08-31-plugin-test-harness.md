# 플러그인 테스트 하네스 및 경계값 규칙 보강 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-pm 플러그인에 자동 검증 수단(테스트 하네스)을 도입하고, 실제 프로젝트 드라이런에서 드러난 경계값 도출 규칙의 구멍과 xlsx 시트명 버그를 테스트 주도로 고친다.

**Architecture:** 표준 라이브러리 `unittest`만 사용하는 테스트 패키지를 `plugins/gx-pm/tests/`에 신설한다. 두 축으로 나뉜다 — (1) `utils/export-xlsx.py`의 순수 함수를 검증하는 단위 테스트, (2) 스킬·커맨드·템플릿·매니페스트 간 정합성을 검증하는 문서 계약 테스트. 후자는 v1.5.0에서 손으로 잡았던 "불일치 10건"류가 재발하지 않도록 고정하는 회귀 그물이다. 마지막에 GitHub Actions로 두 축을 CI에 건다.

**Tech Stack:** Python 3.10 표준 라이브러리(`unittest`, `importlib`, `json`, `re`, `pathlib`), `openpyxl` 3.1.5(이미 설치됨, `ensure_openpyxl()`이 자동 설치), GitHub Actions

**Spec:** 이 문서의 [배경 · 근거](#배경--근거) 절이 스펙이다. 원자료는 PR #6 드라이런 코멘트 — https://github.com/bs-koo/gx-pm/pull/6#issuecomment-5472721030

---

## 배경 · 근거

`SQ/memo`(Spring Boot 회의실예약 시스템)에 C유형(산출물 정비) 경로로 드라이런을 돌렸다. 이 프로젝트에는 사람이 직접 작성한 테스트 49건(정책 21 · 서비스 9 · 취소 19)이 있어 플러그인 산출과 정면 대조가 가능했다.

**대조 결과** — 플러그인 도출 36건 중 일치 31건, 플러그인만 잡은 것 5건, **놓친 것 4건**.

| # | 놓친 케이스 | 기대 결과 |
|---|---|---|
| 1 | 0분 예약 (시작 == 종료) | `INVALID_DURATION` |
| 2 | 시작시각 == 현재시각 | **통과** (`isBefore`는 같으면 false) |
| 3 | 시작시각 초 != 0 | `INVALID_TIME_UNIT` |
| 4 | 시작시각 나노초 != 0 | `INVALID_TIME_UNIT` |

**공통 원인**: `design-test-cases`가 경계값을 **상수값에서만** 도출하고 검증 메서드의 조건절을 전개하지 않았다. `MIN_DURATION=30` 상수만 보면 29/30이 나오지만 실제 검증은 `duration < MIN`이라 0도 걸린다. `start.isBefore(now)`의 통과 측 경계가 "정확히 현재"라는 것도, `isOnUnit()`이 초·나노초까지 본다는 것도 메서드 본문을 읽어야 나온다.

**부수 발견 (xlsx)**: 산출물 유형이 인식되면 문서 안의 **모든** 표가 양식 시트명을 물려받아 `DE-13 단위테스트계획서_1`, `_2`, `_3`처럼 쌓였다. 12시트 중 6시트가 무의미한 이름이었다. 또한 표 제목 추출이 산문 한 줄("목표치는 전부 발주처(또는 PM) 협의가 필요하다.")을 시트명으로 채택했다.

**근본 문제**: 위 두 결함 모두 **드라이런을 돌려보기 전까지 아무도 몰랐다.** 플러그인에는 테스트가 0건이고 CI도 없다. v1.5.0에서 발견한 불일치 10건도 전부 수작업 검토로 찾은 것이다. 같은 종류의 결함이 다시 들어오는 것을 막을 장치가 없다.

### 선행 시도와의 관계

브랜치 `feat/test-artifacts-upgrade`의 커밋 `145cff9`가 위 개선을 이미 담고 있으나 **PR #6 머지(`4e111e6`) 이후에 푸시되어 머지되지 않았다.** 이 계획은 그 커밋을 체리픽하지 않는다. 이유:

- `145cff9`의 Python 변경은 수동 확인만 거쳤다. 테스트 없이 병합하면 같은 문제가 반복된다.
- 마크다운 규칙 변경(경계값 3유형)은 테스트가 불가능하므로 내용을 그대로 이식하되, 규칙 섹션의 존재를 구조 검사로 고정한다.

`145cff9`는 참고용으로 남기고, 이 브랜치 머지 후 삭제한다.

---

## Global Constraints

- **Python 3.10** 기준. `str | None` 같은 PEP 604 문법 사용 가능
- **테스트 프레임워크는 표준 라이브러리 `unittest`만 사용한다.** pytest는 이 환경에 설치돼 있지 않고, 플러그인 저장소에 새 의존성을 요구하지 않는다
- **`utils/export-xlsx.py`의 파일명을 바꾸지 않는다.** 하이픈이 있어 일반 import가 불가하므로 `importlib`로 로드한다. 파일명은 `README.md`·`templates/approval-protocol.md`에 CLI 경로로 문서화돼 있어 변경 시 문서가 깨진다
- **테스트는 `plugins/gx-pm` 디렉터리에서 실행한다**: `python -m unittest discover -s tests -v`
- 산출물 코드 정본은 `plugins/gx-pm/CLAUDE.md`의 "산출물 범위" 표 — 인터페이스정의서 **DE-04**, 테이블정의서 **DE-08**
- 커밋 메시지는 한국어, 본문에 변경 이유를 적는다

---

## File Structure

| 파일 | 책임 |
|---|---|
| `plugins/gx-pm/tests/helpers.py` | 하이픈 파일명 모듈 로더, 플러그인 경로 상수, 문서 수집 유틸 |
| `plugins/gx-pm/tests/test_export_xlsx.py` | 마크다운 파싱·컬럼 재배열·시트명 결정 단위 테스트 |
| `plugins/gx-pm/tests/test_plugin_consistency.py` | 스킬/커맨드/템플릿/매니페스트 간 계약 테스트 |
| `plugins/gx-pm/utils/export-xlsx.py` | (수정) 표 제목 추출, 본문/보조 표 판별, 컬럼 세트별 시트명 |
| `plugins/gx-pm/skills/design-test-cases/SKILL.md` | (수정) 경계값 도출 3유형, 제약 출처, 검증 순서 규칙 |
| `.github/workflows/test.yml` | CI — push·PR에서 테스트 실행 |

테스트를 두 파일로 나눈 이유: 실행 코드 테스트와 문서 계약 테스트는 실패 원인이 완전히 다르다. 전자는 로직 버그, 후자는 문서 편집 실수다. 함께 두면 실패 시 원인 파악이 느려진다.

---

### Task 1: 테스트 하네스 부트스트랩

`utils/export-xlsx.py`는 파일명에 하이픈이 있어 `import`가 불가능하다. 모든 후속 테스트가 이 로더에 의존하므로 먼저 세운다.

**Files:**
- Create: `plugins/gx-pm/tests/helpers.py`
- Create: `plugins/gx-pm/tests/test_export_xlsx.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `helpers.PLUGIN_ROOT: Path` — `plugins/gx-pm` 절대 경로
  - `helpers.load_export_module() -> ModuleType` — `utils/export-xlsx.py`를 `gx_export_xlsx` 이름으로 로드
  - `helpers.read_docs() -> list[tuple[Path, str]]` — `.omc` 제외한 모든 `.md`의 (경로, 본문)

- [ ] **Step 1: 로더 헬퍼를 작성한다**

`plugins/gx-pm/tests/helpers.py`:

```python
"""테스트 공용 헬퍼.

utils/export-xlsx.py 는 파일명에 하이픈이 있어 일반 import 가 불가능하다.
파일명은 README·approval-protocol 에 CLI 경로로 문서화돼 있어 바꾸지 않고,
importlib 로 로드한다.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXPORT_SCRIPT = PLUGIN_ROOT / "utils" / "export-xlsx.py"
REPO_ROOT = PLUGIN_ROOT.parent.parent

_cached_module: ModuleType | None = None


def load_export_module() -> ModuleType:
    """export-xlsx.py 를 모듈로 로드한다. 한 번 로드하면 캐싱한다."""
    global _cached_module
    if _cached_module is not None:
        return _cached_module
    spec = importlib.util.spec_from_file_location("gx_export_xlsx", EXPORT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈 스펙을 만들 수 없습니다: {EXPORT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _cached_module = module
    return module


def read_docs() -> list[tuple[Path, str]]:
    """플러그인의 모든 마크다운 문서를 (경로, 본문) 쌍으로 반환한다.

    .omc 는 런타임 상태 디렉터리라 검사 대상이 아니다.
    """
    docs = []
    for path in sorted(PLUGIN_ROOT.rglob("*.md")):
        if ".omc" in path.parts:
            continue
        docs.append((path, path.read_text(encoding="utf-8")))
    return docs


def skill_names() -> set[str]:
    return {d.name for d in (PLUGIN_ROOT / "skills").iterdir() if d.is_dir()}


def command_names() -> set[str]:
    return {p.stem for p in (PLUGIN_ROOT / "commands").glob("*.md")}


def template_names() -> set[str]:
    return {p.name for p in (PLUGIN_ROOT / "templates").glob("*.md")}
```

- [ ] **Step 2: 스모크 테스트를 작성한다 (실패해야 함)**

`plugins/gx-pm/tests/test_export_xlsx.py`:

```python
import unittest

from helpers import load_export_module


class LoaderTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()

    def test_모듈이_로드되고_산출물_프로필을_노출한다(self):
        profiles = self.mod.DOCUMENT_PROFILES
        self.assertIn("요구사항정의서", profiles)
        self.assertIn("결함관리대장", profiles)
        self.assertIn("시스템테스트계획서", profiles)

    def test_모든_프로필이_컬럼_세트_리스트를_가진다(self):
        for name, profile in self.mod.DOCUMENT_PROFILES.items():
            with self.subTest(산출물=name):
                self.assertIsInstance(profile["columns"], list)
                self.assertTrue(profile["columns"], "컬럼 세트가 비어 있습니다")
                for column_set in profile["columns"]:
                    self.assertIsInstance(column_set, list)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 테스트를 실행해 통과를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: `Ran 2 tests ... OK`

(이 태스크는 기존 동작을 고정하는 특성상 처음부터 통과한다. 로더가 깨지면 이후 모든 테스트가 실패하므로 별도 태스크로 분리했다.)

- [ ] **Step 4: 커밋**

```bash
git add plugins/gx-pm/tests/helpers.py plugins/gx-pm/tests/test_export_xlsx.py
git commit -m "test: 플러그인 테스트 하네스 도입

utils/export-xlsx.py 는 하이픈 파일명이라 일반 import 가 불가능하다.
파일명이 README·approval-protocol 에 CLI 경로로 문서화돼 있어 유지하고
importlib 로 로드하는 헬퍼를 세운다. pytest 대신 표준 unittest 만 쓴다."
```

---

### Task 2: 표 제목 추출 — 산문이 시트명이 되는 문제

드라이런에서 `목표치는 전부 발주처(또는 PM) 협의가 필요하다.`가 시트명이 됐다. 표 직전을 거슬러 올라가며 첫 비-표 라인을 제목으로 채택하는데, 산문 문단이 걸린 것이다.

**Files:**
- Modify: `plugins/gx-pm/utils/export-xlsx.py:200-231` (`parse_markdown_tables`)
- Test: `plugins/gx-pm/tests/test_export_xlsx.py`

**Interfaces:**
- Consumes: `helpers.load_export_module()` (Task 1)
- Produces: `parse_markdown_tables(text: str) -> list[tuple[str, list[str]]]` — 동작 변경 없음, 제목 선택 규칙만 강화

- [ ] **Step 1: 실패 테스트를 작성한다**

`test_export_xlsx.py`에 클래스를 추가한다:

```python
class ParseMarkdownTablesTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()

    def test_헤딩을_표_제목으로_쓴다(self):
        md = "### 케이스 생성 요약\n\n| 화면ID | 계 |\n|---|---|\n| A | 3 |\n"
        tables = self.mod.parse_markdown_tables(md)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0][0], "케이스 생성 요약")

    def test_산문_문단은_표_제목으로_쓰지_않는다(self):
        md = (
            "### 목표치 미확정 항목\n\n"
            "목표치는 전부 발주처(또는 PM) 협의가 필요하다.\n\n"
            "| ID | 항목 |\n|---|---|\n| B-ST-001 | 응답시간 |\n"
        )
        tables = self.mod.parse_markdown_tables(md)
        self.assertEqual(tables[0][0], "목표치 미확정 항목")

    def test_인용문은_표_제목으로_쓰지_않는다(self):
        md = (
            "### 제약 출처 추적\n\n"
            "> 테이블정의서가 없어 도메인 코드에서 도출했다.\n\n"
            "| 경계값 | 출처 |\n|---|---|\n| 20자 | 정책 상수 |\n"
        )
        tables = self.mod.parse_markdown_tables(md)
        self.assertEqual(tables[0][0], "제약 출처 추적")

    def test_짧은_라벨_라인은_제목으로_쓴다(self):
        md = "**부적합 목록**\n\n| 결함ID | 심각도 |\n|---|---|\n| B-DF-001 | Major |\n"
        tables = self.mod.parse_markdown_tables(md)
        self.assertEqual(tables[0][0], "**부적합 목록**")
```

- [ ] **Step 2: 실행해서 실패를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v -k ParseMarkdownTables`
Expected: `test_산문_문단은_표_제목으로_쓰지_않는다` FAIL —
`AssertionError: '목표치는 전부 발주처(또는 PM) 협의가 필요하다.' != '목표치 미확정 항목'`
`test_인용문은_표_제목으로_쓰지_않는다`도 FAIL

- [ ] **Step 3: 제목 선택 규칙을 고친다**

`utils/export-xlsx.py`의 `parse_markdown_tables` 안, 표 직전 제목 탐색 루프를 교체한다.

기존:

```python
                for j in range(i - 1, max(i - 6, -1), -1):
                    candidate = lines[j].strip()
                    if candidate.startswith("#"):
                        table_title = candidate.lstrip("#").strip()
                        break
                    if candidate and not candidate.startswith("|"):
                        table_title = candidate
                        break
```

변경 후:

```python
                for j in range(i - 1, max(i - 6, -1), -1):
                    candidate = lines[j].strip()
                    if candidate.startswith("#"):
                        table_title = candidate.lstrip("#").strip()
                        break
                    # 인용문·목록·표는 제목이 아니다 — 계속 거슬러 올라간다
                    if candidate.startswith((">", "|", "-", "*", "1.")):
                        continue
                    # 산문 한 줄이 시트명이 되는 것을 막는다.
                    # 짧고 문장으로 끝나지 않는 라인만 라벨로 인정한다.
                    if candidate and len(candidate) <= 30 and not candidate.endswith((".", "다", "요", "!", "?")):
                        table_title = candidate
                        break
```

- [ ] **Step 4: 실행해서 통과를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: `Ran 6 tests ... OK`

- [ ] **Step 5: 커밋**

```bash
git add plugins/gx-pm/utils/export-xlsx.py plugins/gx-pm/tests/test_export_xlsx.py
git commit -m "fix: 산문 한 줄이 xlsx 시트명이 되던 문제

표 직전을 거슬러 올라가며 첫 비-표 라인을 제목으로 채택해,
'목표치는 전부 발주처 협의가 필요하다.' 같은 문단이 시트명이 됐다.
인용문·목록은 건너뛰고, 30자 이하이며 문장으로 끝나지 않는
라인만 라벨로 인정한다."
```

---

### Task 3: 본문 표와 보조 표 분리 — `_1`·`_2` 시트명 누적

드라이런에서 12시트 중 6시트가 `DE-13 단위테스트계획서_1`, `_2` 식이었다. 산출물 유형이 인식되면 문서 안 **모든** 표가 양식 시트명을 물려받기 때문이다. 프로필 컬럼과 맞는 본문 표만 양식명을 쓰고, 근거·통계 등 보조 표는 자기 제목을 쓰게 한다.

**Files:**
- Modify: `plugins/gx-pm/utils/export-xlsx.py` — `_matched_set_index` 신설, `DOCUMENT_PROFILES`에 `sheet_names` 추가, `create_xlsx`의 시트명 결정 블록
- Test: `plugins/gx-pm/tests/test_export_xlsx.py`

**Interfaces:**
- Consumes: `helpers.load_export_module()` (Task 1)
- Produces:
  - `_matched_set_index(rows: list[list[str]], doc_type: str | None) -> int | None` — 본문 표면 매칭된 컬럼 세트 인덱스, 보조 표면 `None`
  - `DOCUMENT_PROFILES[*]["sheet_names"]: list[str]` (선택 키) — 컬럼 세트별 시트명

- [ ] **Step 1: 실패 테스트를 작성한다**

```python
class MatchedSetIndexTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()

    def test_본문_표는_매칭된_컬럼_세트_인덱스를_반환한다(self):
        rows = [["기능구분ID", "기능구분명", "기능ID", "기능명",
                 "화면ID", "화면명", "사용자구분", "단위테스트ID"]]
        self.assertEqual(self.mod._matched_set_index(rows, "단위테스트계획서"), 0)

    def test_두번째_컬럼_세트도_구분한다(self):
        rows = [["화면ID", "화면명", "단위테스트ID", "테스트케이스ID", "요구사항ID",
                 "검사기준 항목", "설계기법", "구분", "사전조건", "입력 데이터"]]
        self.assertEqual(self.mod._matched_set_index(rows, "단위테스트계획서"), 1)

    def test_보조_표는_None_을_반환한다(self):
        rows = [["경계값", "값", "출처"]]
        self.assertIsNone(self.mod._matched_set_index(rows, "단위테스트계획서"))

    def test_산출물_유형이_없으면_None_을_반환한다(self):
        rows = [["결함ID", "심각도"]]
        self.assertIsNone(self.mod._matched_set_index(rows, None))


class SheetNamingTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()

    def test_컬럼_세트별로_다른_시트명을_준다(self):
        names = self.mod.DOCUMENT_PROFILES["단위테스트계획서"]["sheet_names"]
        self.assertEqual(names[0], "DE-13 단위테스트계획")
        self.assertEqual(names[1], "DE-13 테스트케이스")
```

- [ ] **Step 2: 실행해서 실패를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: FAIL — `AttributeError: module 'gx_export_xlsx' has no attribute '_matched_set_index'`,
`KeyError: 'sheet_names'`

- [ ] **Step 3: `_matched_set_index`를 추가한다**

`utils/export-xlsx.py`의 `def _reorder_columns(` 바로 앞에 삽입한다:

```python
def _matched_set_index(rows: list[list[str]], doc_type: str | None) -> int | None:
    """이 표가 산출물 본문 표라면 매칭된 컬럼 세트의 인덱스를, 아니면 None 을 반환한다.

    프로필 컬럼 세트와 절반 이상 일치하면 본문 표다.
    근거·통계 같은 보조 표는 산출물 시트명을 물려받지 않고 자기 제목을 쓴다.
    """
    if not doc_type or doc_type not in DOCUMENT_PROFILES or not rows:
        return None
    header = {h.strip() for h in rows[0]}
    best: int | None = None
    best_ratio = 0.0
    for index, target in enumerate(DOCUMENT_PROFILES[doc_type]["columns"]):
        if not target:
            continue
        ratio = len([c for c in target if c in header]) / len(target)
        if ratio >= 0.5 and ratio > best_ratio:
            best, best_ratio = index, ratio
    return best
```

- [ ] **Step 4: 컬럼 세트가 여럿인 산출물에 `sheet_names`를 추가한다**

`DOCUMENT_PROFILES`의 `"단위테스트계획서"` 항목에서 `"sheet_name"` 줄 바로 다음에 추가한다:

```python
        "sheet_names": ["DE-13 단위테스트계획", "DE-13 테스트케이스"],
```

`"총괄테스트계획서"` 항목에도 같은 위치에 추가한다:

```python
        "sheet_names": ["TE-01 테스트 레벨", "TE-01 종료기준", "TE-01 추진체제"],
```

- [ ] **Step 5: 시트명 결정 블록을 교체한다**

`create_xlsx` 안에서 기존:

```python
            if doc_type and doc_type in DOCUMENT_PROFILES:
                base_name = DOCUMENT_PROFILES[doc_type]["sheet_name"]
            elif title:
                base_name = title
            else:
                base_name = "Data"
```

변경 후:

```python
            set_index = _matched_set_index(rows, doc_type)
            if set_index is not None:
                # 본문 데이터 표 — 공공 양식 시트명을 쓴다
                profile = DOCUMENT_PROFILES[doc_type]
                names = profile.get("sheet_names")
                base_name = (
                    names[set_index]
                    if names and set_index < len(names)
                    else profile["sheet_name"]
                )
            elif title:
                # 근거·통계 등 보조 표 — 마크다운 제목을 시트명으로 쓴다
                base_name = title
            else:
                base_name = "Data"
```

- [ ] **Step 6: 실행해서 통과를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: `Ran 12 tests ... OK`

- [ ] **Step 7: 실제 xlsx 생성으로 종단 확인**

임시 산출물을 만들어 시트명을 확인한다:

```bash
cd plugins/gx-pm
mkdir -p /tmp/gxdry && cat > "/tmp/gxdry/B-단위테스트계획서.md" <<'MD'
## 단위테스트계획

| 기능구분ID | 기능구분명 | 기능ID | 기능명 | 화면ID | 화면명 | 사용자구분 | 단위테스트ID |
|---|---|---|---|---|---|---|---|
| A_01 | 관리 | A_01_01 | 권한 | A_01_01_010 | 권한목록 | 관리자 | U_A_01_01_010 |

### 케이스 생성 요약

이 표는 본문이 아니라 요약이므로 자기 제목을 시트명으로 써야 한다.

| 화면ID | 정상 | 경계 | 예외 |
|---|---|---|---|
| A_01_01_010 | 2 | 3 | 1 |
MD
python utils/export-xlsx.py --dir /tmp/gxdry --output /tmp/gxdry/out.xlsx
python -c "
import openpyxl
wb = openpyxl.load_workbook('/tmp/gxdry/out.xlsx')
print(wb.sheetnames)
assert 'DE-13 단위테스트계획' in wb.sheetnames, wb.sheetnames
assert '케이스 생성 요약' in wb.sheetnames, wb.sheetnames
assert not any(n.endswith('_1') for n in wb.sheetnames), wb.sheetnames
print('시트명 분리 확인')
"
```

Expected: `['DE-13 단위테스트계획', '케이스 생성 요약']` 출력 후 `시트명 분리 확인`

- [ ] **Step 8: 커밋**

```bash
git add plugins/gx-pm/utils/export-xlsx.py plugins/gx-pm/tests/test_export_xlsx.py
git commit -m "fix: xlsx 보조 표가 _1·_2 시트로 쌓이던 문제

산출물 유형이 인식되면 문서 안 모든 표가 양식 시트명을 물려받아
DE-13 단위테스트계획서_1, _2 식으로 쌓였다. 드라이런에서 12시트 중
6시트가 무의미한 이름이었다.

프로필 컬럼 세트와 절반 이상 일치하는 본문 표만 양식명을 쓰고,
근거·통계 등 보조 표는 자기 제목을 쓴다. 컬럼 세트가 여럿인
산출물은 세트별 시트명을 준다 (DE-13 → 단위테스트계획/테스트케이스)."
```

---

### Task 4: 문서 계약 테스트

v1.5.0에서 손으로 찾은 불일치 10건이 재발하지 않도록 고정한다. 스킬·커맨드·템플릿·매니페스트가 서로를 참조하는 구조라 한쪽만 고쳐지는 실수가 반복된다.

**Files:**
- Create: `plugins/gx-pm/tests/test_plugin_consistency.py`

**Interfaces:**
- Consumes: `helpers.PLUGIN_ROOT`, `helpers.REPO_ROOT`, `helpers.read_docs()`, `helpers.skill_names()`, `helpers.command_names()`, `helpers.template_names()` (Task 1)
- Produces: 없음 (검증 전용)

- [ ] **Step 1: 교차 참조 테스트를 작성한다**

`plugins/gx-pm/tests/test_plugin_consistency.py`:

```python
"""스킬·커맨드·템플릿·매니페스트 간 계약 테스트.

v1.5.0 에서 수작업으로 찾은 불일치 10건이 재발하지 않도록 고정한다.
실패하면 문서 편집 실수이지 로직 버그가 아니다.
"""

import json
import re
import unittest

from helpers import (
    PLUGIN_ROOT,
    REPO_ROOT,
    command_names,
    read_docs,
    skill_names,
    template_names,
)


class SkillFrontmatterTest(unittest.TestCase):
    def test_스킬_프론트매터_name_이_디렉터리명과_같다(self):
        for skill_dir in sorted((PLUGIN_ROOT / "skills").iterdir()):
            with self.subTest(스킬=skill_dir.name):
                skill_file = skill_dir / "SKILL.md"
                self.assertTrue(skill_file.exists(), "SKILL.md 가 없습니다")
                text = skill_file.read_text(encoding="utf-8")
                match = re.match(r"^---\nname:\s*(\S+)\ndescription:", text)
                self.assertIsNotNone(match, "프론트매터 형식이 name → description 순이 아닙니다")
                self.assertEqual(match.group(1), skill_dir.name)


class CrossReferenceTest(unittest.TestCase):
    def setUp(self):
        self.docs = read_docs()
        self.skills = skill_names()
        self.commands = command_names()
        self.templates = template_names()

    def test_참조된_스킬이_모두_존재한다(self):
        pattern = re.compile(r"\*\*([a-z][a-z0-9-]{4,})\*\*\s*스킬|`([a-z][a-z0-9-]{4,})`\s*스킬")
        for path, text in self.docs:
            for match in pattern.finditer(text):
                name = match.group(1) or match.group(2)
                with self.subTest(문서=path.name, 스킬=name):
                    self.assertIn(name, self.skills)

    def test_백틱으로_참조된_커맨드가_모두_존재한다(self):
        for path, text in self.docs:
            for match in re.finditer(r"`/([가-힣]+)`", text):
                with self.subTest(문서=path.name, 커맨드=match.group(1)):
                    self.assertIn(match.group(1), self.commands)

    def test_참조된_템플릿_경로가_모두_존재한다(self):
        for path, text in self.docs:
            for match in re.finditer(r"templates/([A-Za-z0-9\-]+\.md)", text):
                with self.subTest(문서=path.name, 템플릿=match.group(1)):
                    self.assertIn(match.group(1), self.templates)

    def test_참조된_스킬_경로가_모두_존재한다(self):
        for path, text in self.docs:
            for match in re.finditer(r"skills/([a-z0-9-]+)/SKILL\.md", text):
                with self.subTest(문서=path.name, 스킬=match.group(1)):
                    self.assertIn(match.group(1), self.skills)

    def test_모든_스킬이_어느_커맨드에서든_호출된다(self):
        used = set()
        for path in (PLUGIN_ROOT / "commands").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"\*\*([a-z][a-z0-9-]{4,})\*\*", text):
                if match.group(1) in self.skills:
                    used.add(match.group(1))
        self.assertEqual(
            self.skills - used, set(),
            "커맨드에서 호출되지 않는 스킬이 있습니다 — 배선 누락입니다",
        )
```

- [ ] **Step 2: 실행해서 통과를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v -k Consistency`
Expected: 전부 PASS (main 상태가 이미 정합하므로)

만약 실패하면 문서 쪽 실제 결함이므로 고친 뒤 진행한다.

- [ ] **Step 3: 레거시 참조·산출물 코드 테스트를 추가한다**

같은 파일에 이어서 작성한다:

```python
def specs_only(docs: list[tuple, ...]) -> list:
    """규칙 검사 대상 문서만 남긴다.

    CHANGELOG 는 '무엇을 고쳤는지' 설명하느라 과거의 잘못된 표기를 그대로 인용한다.
    (예: "/pm-design 참조 9곳 제거", "SCR-001 → EHR_01_01_020")
    이력 문서를 규칙으로 검사하면 고친 사실을 적었다는 이유로 실패한다.
    """
    return [(path, text) for path, text in docs if path.name != "CHANGELOG.md"]


class LegacyReferenceTest(unittest.TestCase):
    def setUp(self):
        self.docs = specs_only(read_docs())

    def test_존재하지_않는_pm_커맨드를_안내하지_않는다(self):
        for path, text in self.docs:
            with self.subTest(문서=path.name):
                self.assertNotIn(
                    "/pm-", text,
                    "구 커맨드(/pm-design·/pm-test·/pm-trace) 참조가 남아 있습니다",
                )

    def test_예시_ID_가_네이밍_규칙을_따른다(self):
        # 화면ID 는 {접두}_{xx}_{xx}_{xxx}, 시나리오ID 는 {시스템코드}-TE-{순번}
        forbidden = re.compile(r"\bSCR-\d|\bSC-\d|\bSN-\d")
        for path, text in self.docs:
            with self.subTest(문서=path.name):
                self.assertIsNone(
                    forbidden.search(text),
                    "규칙을 벗어난 예시 ID 가 있습니다 (SCR-·SC-·SN-)",
                )


class DocumentCodeTest(unittest.TestCase):
    """산출물 코드 정본은 CLAUDE.md 의 '산출물 범위' 표다."""

    def setUp(self):
        self.docs = specs_only(read_docs())

    def test_테이블정의서는_DE_08_이다(self):
        wrong = re.compile(r"테이블정의서\s*\(?DE-09|DE-09\s*테이블정의서")
        for path, text in self.docs:
            with self.subTest(문서=path.name):
                self.assertIsNone(wrong.search(text), "테이블정의서는 DE-08 입니다")

    def test_인터페이스정의서는_DE_04_이다(self):
        wrong = re.compile(r"인터페이스정의서\s*\|\s*DE-07|DE-07\s*인터페이스정의서")
        for path, text in self.docs:
            with self.subTest(문서=path.name):
                self.assertIsNone(wrong.search(text), "인터페이스정의서는 DE-04 입니다")


class CommandStructureTest(unittest.TestCase):
    def test_커맨드에_description_프론트매터가_있다(self):
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            with self.subTest(커맨드=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\ndescription:"))

    def test_커맨드의_Step_번호가_중복되지_않는다(self):
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            with self.subTest(커맨드=path.name):
                numbers = re.findall(r"^### Step (\d+):", path.read_text(encoding="utf-8"), re.M)
                self.assertEqual(
                    len(numbers), len(set(numbers)),
                    f"Step 번호가 중복됩니다: {numbers}",
                )
```

- [ ] **Step 4: 버전 표기 일관성 테스트를 추가한다**

같은 파일에 이어서 작성한다:

```python
class VersionConsistencyTest(unittest.TestCase):
    """버전과 개수 표기가 10개 지점에 흩어져 있어 한쪽만 갱신되기 쉽다.

    v1.4.0 에서 marketplace.json 과 README 배지가 실제로 누락됐다.
    """

    def setUp(self):
        self.plugin_json = json.loads(
            (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.changelog = (PLUGIN_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.skill_count = len(skill_names())
        self.command_count = len(command_names())

    def test_모든_매니페스트의_버전이_같다(self):
        version = self.plugin_json["version"]
        self.assertEqual(self.marketplace["plugins"][0]["version"], version)
        self.assertEqual(re.search(r"version-([\d.]+)-blue", self.readme).group(1), version)
        self.assertEqual(re.search(r"## \[([\d.]+)\]", self.changelog).group(1), version)

    def test_README_배지가_실제_스킬_커맨드_수와_같다(self):
        self.assertEqual(
            int(re.search(r"skills-(\d+)-green", self.readme).group(1)), self.skill_count
        )
        self.assertEqual(
            int(re.search(r"commands-(\d+)-orange", self.readme).group(1)), self.command_count
        )

    def test_설명문의_스킬_커맨드_수가_실제와_같다(self):
        for label, description in [
            ("plugin.json", self.plugin_json["description"]),
            ("marketplace.json", self.marketplace["plugins"][0]["description"]),
        ]:
            with self.subTest(매니페스트=label):
                self.assertEqual(
                    int(re.search(r"(\d+)개 스킬", description).group(1)), self.skill_count
                )
                self.assertEqual(
                    int(re.search(r"커맨드 (\d+)개", description).group(1)), self.command_count
                )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: 전체 실행해서 통과를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 전 테스트 PASS

- [ ] **Step 6: 회귀 그물이 실제로 작동하는지 확인한다**

테스트가 통과하는 것만으로는 그물이 촘촘한지 알 수 없다. 일부러 결함을 넣어 잡히는지 본다.

`CHANGELOG.md`가 아니라 **스킬 문서**에 넣어야 한다 — 이력 문서는 `specs_only()`가 제외한다.

```bash
cd plugins/gx-pm
python - <<'PY'
import pathlib
p = pathlib.Path("skills/audit-response/SKILL.md")
p.write_text(p.read_text(encoding="utf-8") + "\n- 후속: /pm-trace\n", encoding="utf-8")
PY
python -m unittest discover -s tests -k LegacyReference
```

Expected: FAIL — `구 커맨드(/pm-design·/pm-test·/pm-trace) 참조가 남아 있습니다`

되돌린다:

```bash
git checkout plugins/gx-pm/skills/audit-response/SKILL.md
cd plugins/gx-pm && python -m unittest discover -s tests -k LegacyReference
```

Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add plugins/gx-pm/tests/test_plugin_consistency.py
git commit -m "test: 문서 계약 테스트 도입

v1.5.0 에서 수작업으로 찾은 불일치 10건을 회귀 테스트로 고정한다.
스킬 프론트매터·교차 참조·배선 누락·레거시 커맨드·산출물 코드·
예시 ID 규칙·Step 번호 중복·버전 표기 일관성을 검사한다.

버전 표기는 10개 지점에 흩어져 있어 v1.4.0 에서 marketplace.json 과
README 배지가 실제로 누락됐다."
```

---

### Task 5: 경계값 도출 규칙 3유형 세분화

드라이런에서 놓친 4건의 원인을 규칙으로 고정한다. 마크다운 규칙이라 실행 테스트는 불가능하므로, 규칙 섹션의 존재를 구조 검사로 고정해 삭제·유실을 막는다.

**Files:**
- Modify: `plugins/gx-pm/skills/design-test-cases/SKILL.md`
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (구조 검사 추가)

**Interfaces:**
- Consumes: `helpers.PLUGIN_ROOT` (Task 1)
- Produces: 없음

- [ ] **Step 1: 규칙 섹션 존재를 요구하는 실패 테스트를 작성한다**

`test_plugin_consistency.py`에 클래스를 추가한다:

```python
class BoundaryRuleTest(unittest.TestCase):
    """드라이런에서 놓친 4건(영값·통과 측 경계·하위 정밀도)의 재발을 막는다.

    마크다운 규칙이라 실행 검증은 불가능하다. 규칙 섹션이 삭제되지 않도록
    존재만 고정한다.
    """

    def setUp(self):
        self.text = (
            PLUGIN_ROOT / "skills" / "design-test-cases" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_경계값_도출이_3유형으로_나뉘어_있다(self):
        for heading in ("유형 A", "유형 B", "유형 C"):
            with self.subTest(유형=heading):
                self.assertIn(heading, self.text)

    def test_영값_케이스_규칙이_있다(self):
        self.assertIn("영값", self.text)

    def test_통과_측_경계_규칙과_연산자표가_있다(self):
        self.assertIn("isBefore", self.text)
        self.assertIn("경계 정확히 일치", self.text)

    def test_하위_정밀도_전개_규칙이_있다(self):
        self.assertIn("나노초", self.text)

    def test_제약_출처에_도메인_검증_코드가_있다(self):
        self.assertIn("도메인 검증 코드", self.text)

    def test_검증_조건_순차_검사_규칙이_있다(self):
        self.assertIn("먼저 걸리는 조건", self.text)
```

- [ ] **Step 2: 실행해서 실패를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v -k BoundaryRule`
Expected: 6건 전부 FAIL

- [ ] **Step 3: 제약 출처에 도메인 검증 코드를 추가한다**

`skills/design-test-cases/SKILL.md`의 "## 입력" 표에서 마지막 행 다음에 추가한다:

```markdown
| 도메인 검증 코드 | 선택 | **정책 클래스·검증 메서드·오류코드 enum** (C유형에서 주 출처) |
```

같은 절의 인용문 다음에 이어서 추가한다:

```markdown
### 제약 출처 우선순위

1. **테이블정의서(DE-08)** — 컬럼 길이·NotNull·타입
2. **화면정의서** — 입력 항목 제약 (테이블보다 좁으면 이쪽이 우선)
3. **도메인 검증 코드** — 정책 상수 + **검증 메서드 본문** + 오류코드 enum
4. **사용자 확인** — 위 셋에서 못 찾으면 임의 추정하지 않고 물어본다

> 산출물이 없는 C유형(산출물 정비)에서는 3번이 사실상 유일한 출처다.
> 애노테이션(`@Column(length=)`·`@Size`)이 없는 프로젝트도 흔하므로,
> **정책 클래스의 상수와 검증 메서드를 함께 읽는다.**

### 오류코드 enum 은 예외 케이스의 완전한 목록이다

오류코드 enum 이 있으면 **각 코드가 곧 예외 케이스 1건 이상**이다.
enum 전건을 훑어 대응 케이스가 없는 코드를 찾으면 예외 누락을 구조적으로 막을 수 있다.

```
ErrorCode 13종 → 대응 케이스 12종 생성, INVALID_DATE_FORMAT 1종 미커버
→ 조회 화면에 날짜 형식 오류 케이스 추가
```
```

- [ ] **Step 4: 경계값분석 절을 3유형으로 교체한다**

`#### 경계값분석 (Boundary Value Analysis)` 절 전체(기존 "날짜 범위는 별도 규칙" 블록까지)를 다음으로 교체한다:

```markdown
#### 경계값분석 (Boundary Value Analysis)

**제약 유형별로 도출 규칙이 다르다.** 아래 3유형을 구분해서 적용한다.

##### 유형 A — 길이·수량 제약

**영값 / 최소-1 / 최소 / 최대 / 최대+1** 을 만든다.

```
제약: 권한명 VARCHAR2(50) NOT NULL
  0자   → 저장 차단 (필수값 위반)        [예외]
  1자   → 정상 저장 (하한 경계)          [경계]
  50자  → 정상 저장 (상한 경계)          [경계]
  51자  → 저장 차단 (길이 초과 안내)      [경계]
```

**영값(0·빈 문자열·0분·0건)을 반드시 포함한다.** 상수값(`MIN=30`)만 보면 29/30 만 나오지만,
실제 검증은 `duration < MIN` 이므로 **0 도 걸린다**. 영값은 별도 오류로 갈리는 경우가 많아
빠뜨리면 실제 결함을 놓친다.

```
제약: 예약 길이 30분 이상 4시간 이하
  0분      → INVALID_DURATION (시작==종료)   [경계] ← 영값. 놓치기 쉬움
  30분     → 정상                              [경계]
  4시간    → 정상                              [경계]
  4시간30분 → INVALID_DURATION                [경계]
```

##### 유형 B — 시각·순서 제약 ("이후/이전/이하")

**경계-1 / 경계 정확히 일치 / 경계+1** 3건을 만든다.
**"정확히 일치"가 통과 측인지 차단 측인지는 비교 연산자가 결정**하므로 코드를 확인한다.

| 검증 코드 | 경계 일치 시 |
|---|---|
| `start.isBefore(now)` → 차단 | **일치는 통과** (isBefore 는 같으면 false) |
| `start.isAfter(limit)` → 차단 | **일치는 통과** |
| `end > CLOSE` → 차단 | **일치는 통과** |
| `duration < MIN` → 차단 | **일치는 통과** |

```
제약: 지난 시간 예약 불가 (start.isBefore(now) → PAST_DATETIME)
  현재 -1분  → PAST_DATETIME     [경계]
  현재 정각  → **정상 저장**      [경계] ← 통과 측 경계. 놓치기 쉬움
  현재 +1분  → 정상 저장          [정상]
```

##### 유형 C — 단위(step) 제약

배수/비배수뿐 아니라 **하위 정밀도 잔여값**까지 만든다.
검증 메서드가 초·나노초까지 보는 경우가 많다.

```
제약: 30분 단위 (isOnUnit: minute % 30 == 0 && second == 0 && nano == 0)
  10:00      → 정상                    [경계]
  10:15      → INVALID_TIME_UNIT       [경계]
  10:00:30   → INVALID_TIME_UNIT       [경계] ← 초 잔여. 놓치기 쉬움
  10:00:00.5 → INVALID_TIME_UNIT       [경계] ← 나노초 잔여
```

##### 공통 — 검증 메서드 조건절 전개

**검증 메서드 본문의 `if` 하나당 최소 2건**을 만든다: 차단되는 케이스 1건 + 통과 측 경계 1건.
상수만 훑으면 위 3유형의 "놓치기 쉬움" 표시 케이스가 전부 빠진다.

##### 날짜 범위 제약

```
제약: 조회 시작일 ≤ 종료일
  시작일 = 종료일          → 정상 조회 (당일)   [경계]
  시작일 = 종료일 + 1일    → 오류 안내          [예외]
```
```

- [ ] **Step 5: 강제 검증 규칙과 주의사항을 보강한다**

"### Step 3: 케이스 구분 강제 검증"의 표에 3행을 추가한다 (기존 마지막 행 앞):

```markdown
| 수량·기간 제약마다 **영값 케이스 1건** | 영값 케이스 자동 추가 |
| 시각·순서 제약마다 **경계 정확히 일치 케이스 1건** | 통과 측 경계 자동 추가 |
| 오류코드 enum 이 있으면 **전 코드에 대응 케이스 존재** | 미커버 코드 목록 표시 |
```

표 다음 인용문 뒤에 추가한다:

```markdown
> **조회 전용 화면은 최소 케이스 수를 강제하지 않는다.** 입력 제약이 없어 경계값이
> 본질적으로 적으므로, 미달 시 자동 보강 대신 사용자에게 기준 적용 여부를 묻는다.
```

"## 주의사항"의 2번 항목을 교체하고 두 항목을 추가한다:

기존:

```markdown
2. 경계값은 **테이블정의서 → 화면정의서 → 사용자 확인** 순으로 근거를 찾는다. 근거 없이 임의 추정하지 않는다
```

변경 후:

```markdown
2. 경계값은 **테이블정의서 → 화면정의서 → 도메인 검증 코드 → 사용자 확인** 순으로 근거를 찾는다. 근거 없이 임의 추정하지 않는다
3. **상수값만 보고 경계를 만들지 않는다** — 검증 메서드의 조건절을 함께 읽는다.
   상수만 보면 영값(0분·빈 문자열)과 통과 측 경계(현재 정각·18:00 정각), 하위 정밀도(초·나노초)가 전부 빠진다
4. 검증 조건이 순차 검사되면 **먼저 걸리는 조건이 실제 결과**다.
   (예: 15분 예약은 길이 위반이자 단위 위반이지만, 단위 검사가 앞서므로 `INVALID_TIME_UNIT`)
   기대 결과에 이 순서를 반영하지 않으면 케이스가 실패한다
```

이후 항목 번호를 순차 재부여한다 (기존 3~7 → 5~9).

- [ ] **Step 6: 실행해서 통과를 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 전 테스트 PASS

- [ ] **Step 7: 드라이런에서 놓친 4건이 규칙으로 도출되는지 대조한다**

`skills/design-test-cases/SKILL.md`를 읽고 아래 4건이 각각 어느 규칙에서 나오는지 확인한다. 문서에 근거가 없으면 규칙이 부족한 것이므로 보강한다.

| 놓쳤던 케이스 | 근거가 될 규칙 |
|---|---|
| 0분 예약 | 유형 A — 영값 필수 |
| 시작시각 == 현재시각 통과 | 유형 B — 경계 정확히 일치 + 연산자표 `isBefore` |
| 초 != 0 | 유형 C — 하위 정밀도 잔여 |
| 나노초 != 0 | 유형 C — 하위 정밀도 잔여 |

- [ ] **Step 8: 커밋**

```bash
git add plugins/gx-pm/skills/design-test-cases/SKILL.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -m "fix: 경계값 도출 규칙을 3유형으로 세분화

실제 프로젝트 드라이런에서 사람이 쓴 테스트 49건과 대조한 결과
4건을 놓쳤다. 공통 원인은 경계값을 상수값에서만 도출하고
검증 메서드의 조건절을 전개하지 않은 것이다.

- 유형 A 길이·수량: 영값(0·빈 문자열·0분) 케이스 필수화
- 유형 B 시각·순서: 경계 정확히 일치 필수화 + 비교 연산자별 통과 측 판정표
- 유형 C 단위: 하위 정밀도 잔여(초·나노초) 전개
- 제약 출처에 도메인 검증 코드 추가 (C유형의 주 출처)
- 오류코드 enum 을 예외 케이스 완전 목록으로 활용
- 검증 조건 순차 검사 규칙 명시

마크다운 규칙이라 실행 검증이 불가능하므로 규칙 섹션의 존재를
구조 검사로 고정했다."
```

---

### Task 6: CI 연결

테스트가 있어도 돌지 않으면 의미가 없다. 저장소에 워크플로가 하나도 없으므로 신설한다.

**Files:**
- Create: `.github/workflows/test.yml`
- Modify: `plugins/gx-pm/CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1~5의 테스트 전부
- Produces: 없음

- [ ] **Step 1: 워크플로를 작성한다**

`.github/workflows/test.yml`:

```yaml
name: test

on:
  push:
    branches: [main]
  pull_request:

jobs:
  unittest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: openpyxl 설치
        run: pip install openpyxl

      - name: 테스트 실행
        working-directory: plugins/gx-pm
        run: python -m unittest discover -s tests -v
```

- [ ] **Step 2: 로컬에서 CI와 같은 명령으로 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 전 테스트 PASS, 실패 0

- [ ] **Step 3: CHANGELOG 에 항목을 추가한다**

`plugins/gx-pm/CHANGELOG.md`의 `# Changelog` 바로 다음에 삽입한다:

```markdown
## [1.5.1] - 2026-08-31

실제 프로젝트(Spring Boot 회의실예약 시스템) 드라이런에서 드러난 규칙 구멍과
xlsx 시트명 버그를 고치고, 재발 방지용 테스트 하네스를 도입했다.

### Added

- **테스트 하네스** (`plugins/gx-pm/tests/`) — 표준 `unittest` 기반, 새 의존성 없음
  - `test_export_xlsx.py`: 마크다운 파싱·컬럼 재배열·시트명 결정 단위 테스트
  - `test_plugin_consistency.py`: 스킬·커맨드·템플릿·매니페스트 계약 테스트.
    v1.5.0 에서 수작업으로 찾은 불일치 10건을 회귀 테스트로 고정
- **CI** (`.github/workflows/test.yml`) — push·PR 에서 테스트 실행. 종전에는 워크플로가 없었다

### Changed

- **`design-test-cases` 경계값 도출 규칙을 3유형으로 세분화**
  - 유형 A 길이·수량: **영값(0·빈 문자열·0분)** 케이스 필수화
  - 유형 B 시각·순서: **경계 정확히 일치** 필수화 + 비교 연산자별 통과 측 판정표
  - 유형 C 단위: **하위 정밀도 잔여(초·나노초)** 전개
  - 제약 출처에 **도메인 검증 코드** 추가 — C유형에서는 사실상 유일한 출처
  - 오류코드 enum 을 예외 케이스 완전 목록으로 활용
  - 검증 조건 순차 검사 규칙 명시

### Fixed

- **xlsx 보조 표가 `_1`·`_2` 시트로 쌓이던 문제** — 산출물 유형이 인식되면 문서 안 모든 표가
  양식 시트명을 물려받았다. 드라이런에서 12시트 중 6시트가 무의미한 이름이었다.
  본문 표만 양식명을 쓰고 보조 표는 자기 제목을 쓰도록 분리하고, 컬럼 세트별 시트명을 지원
- **산문 한 줄이 시트명이 되던 문제** — 표 직전 첫 비-표 라인을 제목으로 채택해
  문단이 시트명이 됐다. 인용문·목록을 건너뛰고 짧은 라벨만 인정하도록 수정
```

- [ ] **Step 4: 버전을 올린다**

`plugins/gx-pm/.claude-plugin/plugin.json` 의 `version` 을 `1.5.1` 로,
`.claude-plugin/marketplace.json` 의 `plugins[0].version` 을 `1.5.1` 로,
`README.md` 의 배지 `version-1.5.0-blue` 를 `version-1.5.1-blue` 로 바꾼다.

- [ ] **Step 5: 버전 일관성 테스트로 확인한다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v -k VersionConsistency`
Expected: PASS (Task 4에서 만든 테스트가 4개 지점을 대조한다)

- [ ] **Step 6: 전체 테스트 실행**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: 전 테스트 PASS

- [ ] **Step 7: 커밋**

```bash
git add .github/workflows/test.yml plugins/gx-pm/CHANGELOG.md \
        plugins/gx-pm/.claude-plugin/plugin.json .claude-plugin/marketplace.json README.md
git commit -m "ci: 테스트 워크플로 추가 및 v1.5.1 버전업

저장소에 워크플로가 하나도 없어 테스트가 있어도 돌지 않는다.
push·PR 에서 unittest 를 실행한다. openpyxl 외 의존성은 없다."
```

---

## 검증 요약

계획 완료 시 다음이 성립해야 한다.

| 항목 | 확인 방법 |
|---|---|
| 전 테스트 통과 | `cd plugins/gx-pm && python -m unittest discover -s tests -v` |
| xlsx 시트명 분리 | Task 3 Step 7의 종단 확인 스크립트 |
| 회귀 그물 동작 | Task 4 Step 6의 의도적 결함 주입 |
| 놓쳤던 4건 재도출 | Task 5 Step 7의 규칙 대조표 |
| CI 실행 | PR 생성 후 GitHub Actions 체크 통과 |

## 후속 정리

이 브랜치가 머지되면 `feat/test-artifacts-upgrade` 브랜치를 삭제한다. 미머지 커밋 `145cff9`의 내용은 이 계획의 Task 3·5가 테스트와 함께 대체한다.

```bash
git push origin --delete feat/test-artifacts-upgrade
git branch -D feat/test-artifacts-upgrade
```
