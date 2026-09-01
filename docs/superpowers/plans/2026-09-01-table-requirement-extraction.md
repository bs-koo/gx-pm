# 표 형식 요구사항 추출 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `extract-requirements` 스킬이 ID 표로 제시된 요구사항을 놓치지 않게 하고, 그 규칙이 문서에만 있고 동작하지 않는 일이 없도록 계약 테스트로 고정한다.

**Architecture:** 스킬 문서(`SKILL.md`)에 다섯 번째 추출 패턴 — ID 접두 표 행 — 을 정규식과 함께 문자 그대로 싣는다. 그 정규식을 테스트가 문서에서 **뽑아내어** 픽스처 문서에 적용하고, 기대한 ID 만 정확히 추출하는지 검사한다. 문서의 규칙과 시험하는 규칙이 같은 문자열이므로 둘이 갈라질 수 없다.

**Tech Stack:** 마크다운 스킬 정의, Python 3.10 표준 `unittest`

**Spec:** `docs/superpowers/specs/2026-09-01-table-requirement-extraction-design.md`

## Global Constraints

- **새 파이썬 의존성 금지.** 표준 라이브러리 `unittest`·`re`·`pathlib` 만 쓴다.
- **모든 문서는 한국어.** 커밋 메시지도 한국어.
- **외부 저장소를 참조하지 않는다.** 픽스처는 이 레포 안에 만든다 — `D:\SQ\memo` 는 근거 자료일 뿐 테스트 대상이 아니다.
- **`templates/id-naming-rules.md` 의 제안요청ID 패턴 `SFR-{3자리 순번}` 을 바꾸지 않는다.** 원문 ID 는 `근거` 열에 병기한다.
- **버전을 올리지 않는다.** `CHANGELOG.md` 의 `## [Unreleased]` 에만 기록한다.
- **테스트 실행 명령** (모든 Task 공통):
  ```bash
  cd plugins/gx-pm && python -m unittest discover -s tests -v
  ```
  Task 1 시작 시점 기준 **59건**이 통과한다. 각 Task 는 이 숫자를 줄이지 않는다.
  개별 클래스 실행이 필요하면 `cd plugins/gx-pm/tests && python -m unittest test_extract_rules.<Class> -v`
  를 쓴다 — `cd plugins/gx-pm && python -m unittest tests.<모듈>` 형태는 `helpers` 를
  못 찾아 `ModuleNotFoundError` 로 죽는다(선존 환경 특성).

---

## 파일 구조

| 파일 | 책임 | Task |
|------|------|------|
| `plugins/gx-pm/skills/extract-requirements/SKILL.md` | 추출 규칙의 정본. 정규식이 여기 문자 그대로 실린다 | 1, 2 |
| `plugins/gx-pm/tests/fixtures/requirement-tables.md` | 규칙을 시험할 픽스처. 요구사항 표 2종 + 오탐 유발 표 2종 | 1 |
| `plugins/gx-pm/tests/test_extract_rules.py` | 문서에서 정규식을 뽑아 픽스처에 적용하는 계약 테스트 | 1, 2 |
| `plugins/gx-pm/CHANGELOG.md` | `## [Unreleased]` 에 기록 | 3 |

**왜 새 테스트 파일인가**: `test_plugin_consistency.py` 는 "문서 사이의 참조가 맞는가" 를 본다.
이번 것은 "문서에 적힌 규칙이 실제로 동작하는가" 라서 성격이 다르다. 파일을 나눈다.

---

## Task 1: 픽스처와 추출 규칙

**Files:**
- Create: `plugins/gx-pm/tests/fixtures/requirement-tables.md`
- Create: `plugins/gx-pm/tests/test_extract_rules.py`
- Modify: `plugins/gx-pm/skills/extract-requirements/SKILL.md`
- Modify: `plugins/gx-pm/tests/helpers.py`

**Interfaces:**
- Consumes: 없음 (첫 Task)
- Produces:
  - `SKILL.md` 안에 ```` ```regex ```` 펜스로 감싼 정규식이 **정확히 1개** 존재한다.
    테스트가 이 펜스에서 정규식을 뽑는다.
  - `tests/fixtures/requirement-tables.md` — 요구사항 ID 5건(`BR-01`,`BR-02`,`BR-03`,`NFR-01`,`NFR-02`)과
    오탐 유발 표 2종을 담는다.
  - `test_extract_rules.py` 의 `ExtractRuleTest` 클래스.

- [ ] **Step 1: 픽스처를 문서 계약 검사에서 제외한다**

`read_docs()` 는 `PLUGIN_ROOT` 아래 모든 `.md` 를 훑는다. 픽스처를 그대로 두면
**모든 문서 계약 검사의 대상**이 된다 — 커맨드 참조·스킬 참조·예시 ID 규칙 전부.

지금 만들 픽스처는 깨끗해서 통과하지만, 나중에 "잘못된 예시를 일부러 담은 픽스처"
(예: 탐지 규칙을 시험하려고 `SCR-001` 을 넣는 경우)를 만들면 그때 터진다.
픽스처는 검사 **대상**이 아니라 검사 **도구**다.

`plugins/gx-pm/tests/helpers.py` 의 `read_docs()` 를 고친다:

```python
    docs = []
    for path in sorted(PLUGIN_ROOT.rglob("*.md")):
        if ".omc" in path.parts:
            continue
        if "fixtures" in path.parts:
            continue  # 픽스처는 검사 대상이 아니라 검사 도구다
        docs.append((path, path.read_text(encoding="utf-8")))
```

docstring 에도 한 줄 추가한다:

```python
    .omc 는 런타임 상태 디렉터리라 검사 대상이 아니다.
    tests/fixtures 는 규칙을 시험하기 위한 입력이라 검사 대상이 아니다 —
    일부러 잘못된 예시를 담는 픽스처가 계약 검사에 걸리면 안 된다.
    저장소 루트 README 도 포함한다 — 사용자의 첫 접점이라 다른 문서와 같은
    계약 검사(개명·백틱·정본 참조 등)를 받아야 한다.
```

Run: `cd plugins/gx-pm && python -m unittest discover -s tests`
Expected: **59 tests, OK** — 아직 픽스처가 없으므로 동작 변화가 없다

- [ ] **Step 2: 픽스처를 만든다**

`plugins/gx-pm/tests/fixtures/requirement-tables.md` 를 Write 도구로 만든다 (heredoc 금지 — 표와 별표가 셸에서 망가진다):

````markdown
# 픽스처 — 표 형식 요구사항 인식 시험용

이 문서는 `extract-requirements` 의 ID 표 인식 규칙을 시험하기 위한 픽스처다.
실제 산출물이 아니며 사람이 읽을 문서도 아니다. 규칙이 바뀌면 이 파일도 함께 고친다.

기대 추출: `BR-01` `BR-02` `BR-03` `NFR-01` `NFR-02` — 이 5건뿐이다.

## 2. 도메인 규칙

섹션 제목에 "요구사항" 이 없다. 섹션 규칙으로는 안 잡히고 표 규칙으로만 잡혀야 한다.

| ID | 규칙 | 비고 |
|----|------|------|
| BR-01 | 같은 회의실에서 시간이 겹치는 예약은 생성할 수 없다 | 문장 패턴에 안 걸린다 |
| BR-02 | 예약 시각은 **30분 단위**여야 한다 | 문장 패턴에도 걸린다 — 중복 제거 대상 |
| **BR-03** | 예약 가능 시간대는 09:00 ~ 18:00 이다 | ID 가 굵게 표기됐다 |

## 6. 비기능 요구사항

섹션 규칙과 표 규칙에 **둘 다** 걸린다. 중복 제거가 필요한 자리다.

| ID | 항목 | 요구 |
|----|------|------|
| NFR-01 | 저장소 | H2 인메모리 |
| NFR-02 | 시간대 | Asia/Seoul 고정 |

## 판정표 — 요구사항이 아니다

첫 열이 숫자다. 여기서 무언가 추출되면 오탐이다.

| # | 요청 구간 | 기대 결과 |
|---|-----------|-----------|
| 1 | 08:00~09:00 | 허용 |
| 2 | 08:30~09:30 | 거절 |

## 오류 응답 — 요구사항이 아니다

첫 열이 코드명이다. 대문자와 하이픈이 없어 ID 형태가 아니다.

| code | HTTP |
|------|------|
| OVERLAPPING_RESERVATION | 409 |
| NOT_RESERVER | 403 |
````

- [ ] **Step 3: 실패하는 테스트를 쓴다**

`plugins/gx-pm/tests/test_extract_rules.py` 를 Write 도구로 만든다:

```python
"""추출 규칙이 문서에만 있고 동작하지 않는 것을 막는다.

`design-test-cases` 의 경계값 규칙처럼, 마크다운에 적힌 규칙은 아무도 시험하지 않으면
적혀만 있고 동작하지 않는다. 여기서는 문서에 실린 정규식을 **그대로 뽑아** 픽스처에
적용한다. 문서의 규칙과 시험하는 규칙이 같은 문자열이라 둘이 갈라질 수 없다.
"""

import re
import unittest

from helpers import PLUGIN_ROOT

SKILL = PLUGIN_ROOT / "skills" / "extract-requirements" / "SKILL.md"
FIXTURE = PLUGIN_ROOT / "tests" / "fixtures" / "requirement-tables.md"

# 픽스처가 담고 있는 요구사항 ID. 순서까지 같아야 한다.
기대_ID = ["BR-01", "BR-02", "BR-03", "NFR-01", "NFR-02"]


def 문서에서_정규식을_뽑는다() -> str:
    """SKILL.md 의 ```regex 펜스에서 ID 표 인식 정규식을 꺼낸다."""
    text = SKILL.read_text(encoding="utf-8")
    펜스 = re.findall(r"```regex\n(.*?)\n```", text, re.S)
    if len(펜스) != 1:
        raise AssertionError(
            f"SKILL.md 의 ```regex 펜스가 1개가 아닙니다 (발견 {len(펜스)}개) "
            "— 테스트가 어느 것을 시험할지 결정할 수 없습니다"
        )
    return 펜스[0].strip()


class ExtractRuleTest(unittest.TestCase):
    def setUp(self):
        self.패턴 = re.compile(문서에서_정규식을_뽑는다())
        self.픽스처 = FIXTURE.read_text(encoding="utf-8")

    def test_요구사항_표에서_ID를_전부_뽑는다(self):
        찾음 = [
            m.group(1)
            for line in self.픽스처.splitlines()
            if (m := self.패턴.match(line.strip()))
        ]
        self.assertEqual(
            찾음, 기대_ID,
            "문서에 적힌 정규식이 픽스처의 요구사항 ID 를 기대대로 뽑지 못합니다",
        )

    def test_요구사항이_아닌_표에서는_아무것도_안_뽑는다(self):
        오탐 = [
            line.strip()
            for line in self.픽스처.splitlines()
            if self.패턴.match(line.strip())
            and not any(i in line for i in 기대_ID)
        ]
        self.assertEqual(
            오탐, [],
            "판정표·오류응답표처럼 요구사항이 아닌 표에서 추출됐습니다",
        )

    def test_굵게_표기된_ID도_뽑는다(self):
        # 픽스처의 `| **BR-03** |` — RFP 가 ID 를 강조하는 일은 흔하다
        self.assertIn(
            "BR-03",
            [
                m.group(1)
                for line in self.픽스처.splitlines()
                if (m := self.패턴.match(line.strip()))
            ],
            "`**BR-03**` 처럼 굵게 표기된 ID 를 놓칩니다",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: 실패를 확인한다**

Run: `cd plugins/gx-pm/tests && python -m unittest test_extract_rules -v`
Expected: 3건 모두 ERROR — `AssertionError: SKILL.md 의 ```regex 펜스가 1개가 아닙니다 (발견 0개)`

정규식이 아직 문서에 없으므로 `setUp` 에서 죽는 것이 정상이다.

- [ ] **Step 5: 스킬 문서에 다섯 번째 패턴을 추가한다**

`plugins/gx-pm/skills/extract-requirements/SKILL.md` 의 Step 2 를 찾는다. 현재는 이렇다:

```markdown
### Step 2: 요구사항 추출
문서에서 다음 패턴으로 요구사항을 식별한다:
- "~해야 한다", "~를 제공한다", "~기능을 구현한다"
- "ㅇ" 또는 "o"로 시작하는 기능 항목
- 번호가 매겨진 기능 목록
- "기능 요구사항", "비기능 요구사항" 섹션의 항목
```

아래로 교체한다:

````markdown
### Step 2: 요구사항 추출
문서에서 다음 패턴으로 요구사항을 식별한다:
- "~해야 한다", "~를 제공한다", "~기능을 구현한다"
- "ㅇ" 또는 "o"로 시작하는 기능 항목
- 번호가 매겨진 기능 목록
- "기능 요구사항", "비기능 요구사항" 섹션의 항목
- **ID 접두 표 행** — 아래 참조

#### ID 접두 표 행

공공 RFP 는 요구사항을 **ID 표**로 주고, 그 표가 늘 "기능 요구사항" 이라는 제목 아래
있지 않다. 도메인 규칙 · 업무 규칙 · 비즈니스 규칙 · 제약사항 · 정책 · 준수사항 아래
놓이는 것이 보통이다. 섹션 제목에만 의존하면 이 경우를 전부 놓친다.

표의 첫 열이 `{영문 2~4자}-{숫자 2~3자리}` 형태이면 그 표를 요구사항 표로 보고
**각 행을 요구사항 1건으로** 뽑는다.

```regex
^\|\s*\*{0,2}([A-Z]{2,4}-\d{2,3})\*{0,2}\s*\|
```

`**BR-03**` 처럼 굵게 표기된 ID 도 잡는다. 첫 열이 숫자(`1`, `2`)이거나
코드명(`OVERLAPPING_RESERVATION`)인 표는 요구사항 표가 아니므로 뽑지 않는다.

> 이 정규식은 `tests/test_extract_rules.py` 가 이 문서에서 그대로 꺼내
> `tests/fixtures/requirement-tables.md` 에 적용해 검사한다. 고치면 픽스처도 함께 본다.
````

- [ ] **Step 6: 통과를 확인한다**

Run: `cd plugins/gx-pm/tests && python -m unittest test_extract_rules -v`
Expected: `Ran 3 tests ... OK`

- [ ] **Step 7: 규칙이 실제로 무는지 반증한다**

정규식의 `[A-Z]{2,4}` 를 `[A-Z]{5,6}` 으로 잠시 바꿔 `SKILL.md` 를 저장하고 다시 돌린다.

Run: `cd plugins/gx-pm/tests && python -m unittest test_extract_rules -v`
Expected: `test_요구사항_표에서_ID를_전부_뽑는다` FAIL — 찾음이 `[]` 가 된다

확인했으면 `[A-Z]{2,4}` 로 되돌리고 다시 돌려 OK 를 확인한다. 이 전후 출력을 리포트에 남긴다.

- [ ] **Step 8: 전체 스위트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: **62 tests, OK** (기존 59 + 신규 3)

`test_참조된_스킬_경로가_모두_존재한다` 나 `test_참조된_템플릿_경로가_모두_존재한다` 가
실패하면 Step 4 에서 넣은 인용문의 경로 표기를 확인한다.

- [ ] **Step 9: 커밋**

```bash
git add plugins/gx-pm/skills/extract-requirements/SKILL.md plugins/gx-pm/tests
git commit -m "feat: ID 표로 제시된 요구사항을 추출한다

공공 RFP 는 요구사항을 ID 표로 주는데, 그 표가 '기능 요구사항' 제목 아래
있지 않으면 종전 규칙이 전부 놓쳤다. 실측(memo/requirements/mvp.md):
도메인 규칙 표의 BR-01~08 중 1건만 추출됐다.

정규식을 SKILL.md 에 문자 그대로 싣고, 테스트가 그것을 문서에서 뽑아
픽스처에 적용한다 — 문서의 규칙과 시험하는 규칙이 같은 문자열이라 갈라질 수 없다."
```

---

## Task 2: 중복 제거 · 구분 판정 · 원문 ID 보존

**Files:**
- Modify: `plugins/gx-pm/skills/extract-requirements/SKILL.md`
- Modify: `plugins/gx-pm/tests/test_extract_rules.py`

**Interfaces:**
- Consumes: Task 1 의 ```` ```regex ```` 펜스와 `ExtractRuleTest`
- Produces: `SKILL.md` 에 세 규칙(중복 제거 · 구분 판정 · 원문 ID 보존)이 실린다.
  `test_extract_rules.py` 에 `ExtractRuleDocTest` 클래스가 추가된다.

> **왜 Task 1 과 나누는가**: Task 1 은 "무엇을 뽑는가", Task 2 는 "뽑은 것을 어떻게 다루는가" 다.
> 리뷰어가 한쪽을 통과시키고 다른 쪽을 반려할 수 있다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`plugins/gx-pm/tests/test_extract_rules.py` 의 `if __name__ == "__main__":` **바로 앞**에 추가한다:

```python
class ExtractRuleDocTest(unittest.TestCase):
    """뽑은 행을 어떻게 다루는지가 문서에 있어야 한다.

    규칙이 없으면 같은 요구사항이 2건으로 세어지거나(중복), 업무 규칙이
    비기능으로 분류되거나, 원문 ID 가 사라져 추적이 끊긴다.
    """

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_중복_제거_규칙이_있다(self):
        self.assertIn("중복 제거", self.text)
        self.assertIn(
            "1건", self.text,
            "같은 원문 ID 를 몇 건으로 셀지가 적혀 있지 않습니다",
        )

    def test_기능_비기능_판정_순서가_있다(self):
        for 조각 in ("NFR", "QE", "QR", "비기능"):
            with self.subTest(조각=조각):
                self.assertIn(조각, self.text)
        self.assertIn(
            "업무 규칙은 기능", self.text,
            "BR 같은 업무 규칙이 기능으로 분류된다는 근거가 없습니다",
        )

    def test_원문_ID_보존_위치가_있다(self):
        self.assertIn("근거", self.text)
        self.assertIn(
            "제안요청ID 열에 넣지 않는다", self.text,
            "원문 ID 를 제안요청ID 열에 넣지 말라는 금지가 없습니다 "
            "— SFR- 체계가 무너집니다",
        )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd plugins/gx-pm/tests && python -m unittest test_extract_rules.ExtractRuleDocTest -v`
Expected: 3건 FAIL

- [ ] **Step 3: 스킬 문서에 세 규칙을 추가한다**

Task 1 이 넣은 `#### ID 접두 표 행` 절의 **마지막 인용문 바로 뒤**에 이어 붙인다:

````markdown
#### 뽑은 행을 다루는 규칙

**중복 제거** — 섹션 규칙과 표 규칙에 모두 걸리는 항목이 있다.
예: `## 6. 비기능 요구사항` 아래의 NFR 표는 두 규칙에 다 걸린다.
같은 원문 ID 는 요구사항 **1건**으로 센다.

**기능 / 비기능 판정** — 아래 순서로 정한다.

1. 원문 ID 접두어가 `NFR` · `QE` · `QR` 이면 → 비기능
2. 섹션 제목에 "비기능" · "품질" · "성능" · "보안" 이 있으면 → 비기능
3. 그 외 → 기능

`BR`(업무 규칙)은 3번에 걸려 기능이 된다 — **업무 규칙은 기능 요구사항이다.**
"겹치는 예약을 거절한다" 는 성능도 보안도 아니라 시스템이 하는 일이다.

**원문 ID 보존** — 원문 ID 를 `근거` 열에 병기한다: `과업지시서 BR-01`.

**제안요청ID 열에 넣지 않는다.** 그 열의 정본 패턴은 `templates/id-naming-rules.md` 의
`SFR-{3자리 순번}` 이고, 거기에 `BR-01` 을 넣으면 ID 체계가 무너진다.
`근거` 열은 원래 출처를 적는 자리라 원문 ID 표기에 맞고, 이렇게 해야
추적매트릭스에서 `BR-01` 이 어느 요구사항이 됐는지 역추적할 수 있다.
````

- [ ] **Step 4: 통과를 확인한다**

Run: `cd plugins/gx-pm/tests && python -m unittest test_extract_rules -v`
Expected: `Ran 6 tests ... OK`

- [ ] **Step 5: 전체 스위트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: **65 tests, OK** (Task 1 의 62 + 신규 3)

- [ ] **Step 6: 커밋**

```bash
git add plugins/gx-pm/skills/extract-requirements/SKILL.md plugins/gx-pm/tests/test_extract_rules.py
git commit -m "feat: 표에서 뽑은 요구사항의 중복 제거·구분 판정·원문 ID 보존

세 규칙이 없으면 같은 요구사항이 2건으로 세어지거나, 업무 규칙이 비기능으로
분류되거나, 원문 ID 가 사라져 추적이 끊긴다.

원문 ID 는 근거 열에 병기한다. 제안요청ID 열은 SFR- 체계를 지킨다."
```

---

## Task 3: 문서 갱신

**Files:**
- Modify: `plugins/gx-pm/CHANGELOG.md`
- Modify: `plugins/gx-pm/CLAUDE.md`

**Interfaces:**
- Consumes: Task 1·2 의 결과 (테스트 65건)
- Produces: 없음 (마지막 Task)

- [ ] **Step 1: CHANGELOG 의 Unreleased 에 기록한다**

`plugins/gx-pm/CHANGELOG.md` 의 `## [Unreleased]` 아래 `### Fixed` 섹션이 이미 있다.
그 섹션의 **첫 항목으로** 삽입한다:

```markdown
- **`extract-requirements` 가 ID 표로 제시된 요구사항을 놓쳤다.** 공공 RFP 는 요구사항을
  ID 표로 주는데, 그 표가 "기능 요구사항" 제목 아래 있지 않으면(도메인 규칙·업무 규칙·
  제약사항 등) 종전 규칙이 전부 놓쳤다. 실측: 실제 요구사항서의 업무 규칙 표 8건 중
  **1건만** 추출됐고, 나머지 7건이 요구사항정의서에서 통째로 빠졌다
  - 표 인식 정규식을 `SKILL.md` 에 문자 그대로 싣고, 테스트가 그것을 문서에서 뽑아
    픽스처에 적용한다 — 문서의 규칙과 시험하는 규칙이 같은 문자열이라 갈라질 수 없다
  - 중복 제거·기능/비기능 판정·원문 ID 보존 규칙을 함께 명시했다.
    원문 ID 는 `근거` 열에 병기하며 `제안요청ID` 열의 `SFR-` 체계는 건드리지 않는다
```

같은 `## [Unreleased]` 블록 맨 아래의 `계약 테스트 55 → 57.` 줄을
`계약 테스트 55 → 65.` 로 고친다.

- [ ] **Step 2: CLAUDE.md 의 주의사항에 한 줄 추가한다**

`plugins/gx-pm/CLAUDE.md` 의 `## 주의사항` 목록에서
`- 검사기준 27개 항목의 정본은 ...` 줄을 찾아, 그 **바로 뒤**에 삽입한다:

```markdown
- 요구사항은 문장뿐 아니라 **ID 표**로도 제시된다 — 표 인식 규칙의 정본은 `skills/extract-requirements/SKILL.md` 의 "ID 접두 표 행" 절입니다. 섹션 제목이 "기능 요구사항" 이 아니어도(도메인 규칙·업무 규칙·제약사항) 뽑아야 합니다
```

- [ ] **Step 3: 전체 스위트를 돌린다**

Run: `cd plugins/gx-pm && python -m unittest discover -s tests -v`
Expected: **65 tests, OK** (Task 3 은 테스트를 추가하지 않는다)

`test_참조된_스킬_경로가_모두_존재한다` 가 실패하면 Step 2 에서 쓴
`skills/extract-requirements/SKILL.md` 경로 표기를 확인한다.

- [ ] **Step 4: 커밋**

```bash
git add plugins/gx-pm/CHANGELOG.md plugins/gx-pm/CLAUDE.md
git commit -m "docs: 표 형식 요구사항 추출을 CHANGELOG·CLAUDE.md 에 반영"
```

---

## 완료 조건

- [ ] `cd plugins/gx-pm && python -m unittest discover -s tests -v` → **65 tests, OK**
      (59 → 62 → 65, Task 1~3 순)
- [ ] `plugins/gx-pm/tests/fixtures/requirement-tables.md` 가 존재하고, 요구사항 ID 5건과
      오탐 유발 표 2종을 담는다
- [ ] `SKILL.md` 의 ```` ```regex ```` 펜스가 **정확히 1개**다
- [ ] Task 1 Step 6 의 반증 시험 전후 출력이 리포트에 남아 있다
- [ ] `git status` 클린
