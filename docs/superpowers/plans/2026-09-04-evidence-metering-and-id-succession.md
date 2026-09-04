# 근거 계측과 ID 승계 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v3.0.0 을 실제 프로젝트에 돌려 드러난 결함 4건(ID 승계 부재 · 제약 미상 미검출 · 근거 가용도 미표시 · DDL 부재 표기 소실)을 막고 v3.1.0 으로 올린다.

**Architecture:** 이 플러그인은 마크다운 프롬프트다. 로직이 아니라 **규칙문**을 고치고, `tests/test_plugin_consistency.py` 가 규칙문의 존재와 정합을 계약으로 고정한다. 새 정본 `templates/evidence-rules.md` 하나와 새 스킬 `skills/reconcile-ids/SKILL.md` 하나를 세우고, 나머지는 기존 파일이 그 둘을 참조하도록 배선한다. **5종의 컬럼 구성과 게이트 3개는 건드리지 않는다.**

**Tech Stack:** Markdown (스킬·커맨드·템플릿) · Python 3 `unittest` (계약 테스트) · JSON (매니페스트)

**Spec:** `docs/superpowers/specs/2026-09-04-evidence-metering-and-id-succession.md`

## Global Constraints

- **작업 디렉터리는 `D:\SQ\gx-pm\gx-pm\plugins\gx-pm`** 이다. 테스트는 여기서 돈다.
- **테스트 실행 명령**: `python -m unittest discover -s tests -t tests -k <클래스명>`
  전건은 `python -m unittest discover -s tests -t tests`.
  `tests/` 에 `__init__.py` 가 없어 `python -m unittest tests.<모듈>` 형태는 `ModuleNotFoundError` 가 난다.
- **컬럼 정본을 늘리거나 줄이지 않는다.** AN-02 10열 · AN-03 10열 · DE-08 15열 · DE-13 11열 · AN-05 9열.
- **게이트를 늘리지 않는다.** `/gx-spec` 의 `[필수 중단점]` 은 정확히 3개다.
- **경계값·제약을 지어내지 않는다.** 근거가 없으면 채우는 게 아니라 세어서 보고한다.
- **문서는 한국어로 쓴다.** 기존 문체(단정형 종결, 백틱으로 감싼 파일 경로)를 따른다.
- **버전은 v3.1.0.** 4곳을 함께 고친다 — `.claude-plugin/plugin.json`, 저장소 루트
  `.claude-plugin/marketplace.json`, 저장소 루트 `README.md` 배지, `CHANGELOG.md` 최상단 헤딩.
- **커밋은 태스크마다 한 번.** 브랜치는 `feat/evidence-metering-and-id-succession`.
  `main` 에 직접 커밋하면 훅이 막는다. `git checkout -b` 와 `git commit` 을 **별도 명령으로** 실행한다
  (한 명령으로 이으면 훅이 `main` 기준으로 판단해 거부한다).

---

## File Structure

### 신설 2개

| 파일 | 책임 |
|------|------|
| `templates/evidence-rules.md` | 근거 4단 · `[확인필요]` 2종 · 가용도 경고의 **정본**. AN-03·DE-13·`/gx-spec` 이 참조만 하고 규칙을 복제하지 않는다 |
| `skills/reconcile-ids/SKILL.md` | 직전 버전과 대조해 ID 를 승계하는 **실행부**. `detect-existing-artifact`(선택 받기)와 `manage-revision-history`(변경 세기) 사이에 선다 |

### 수정 14개

| 파일 | 무엇을 |
|------|--------|
| `tests/helpers.py` | `read_docs()` 가 `.dev/` 를 뺀다 |
| `templates/AN-03-function-spec.md` | 도출 출처 3단 → 4단, `[확인필요]` 2종, 정본 참조 |
| `templates/DE-08-table-definition.md` | DDL 부재 시 문서 머리 경고 규칙 |
| `templates/id-naming-rules.md` | 불변 규칙에 승계 재생성 명시 |
| `templates/pipeline-protocol.md` | 이월 금지 4번째 항목 |
| `skills/generate-function-spec/SKILL.md` | `[확인필요]` 2종 판정, 근거 가용도 집계 |
| `skills/generate-unit-test-plan/SKILL.md` | Step 6 에 `제약 미상` |
| `skills/convert-ddl-to-tablespec/SKILL.md` | DDL 부재 시 경고 줄 삽입 |
| `skills/detect-existing-artifact/SKILL.md` | `새로쓰기` 를 ID 승계로 |
| `skills/manage-revision-history/SKILL.md` | `reconcile-ids` 선행 명시 |
| `commands/gx-spec.md` | 게이트 2·3 집계, `reconcile-ids` 배선, 이월 금지 4번째 |
| `commands/gx-요구사항정의서.md` · `gx-기능명세서.md` · `gx-단위테스트계획서.md` | `reconcile-ids` 배선 |
| 저장소 루트 `README.md` | 배지·트리·스킬 표·「3가지 선택지」 |
| `CHANGELOG.md` · `plugin.json` · 루트 `marketplace.json` · 루트 `.gitignore` | v3.1.0, `.dev/` 무시 |

---

## Task 1: 런타임 디렉터리가 계약 검사를 깨뜨리지 않게 한다

**Files:**
- Modify: `tests/helpers.py:44-56` (`read_docs()` 의 제외 목록)
- Modify: `../../.gitignore` (저장소 루트)

**Interfaces:**
- Produces: 이후 모든 태스크가 `python -m unittest discover -s tests -t tests` 를 **초록에서 시작**할 수 있다. 지금은 실패 1건을 안고 있어 자기 변경이 깨뜨린 것인지 구분이 안 된다.

**배경:** `.dev/main/decisions.md` 는 훅이 AskUserQuestion 기록을 남기는 런타임 파일이다. git 이 추적하지 않는데 `read_docs()` 가 읽어 `test_백틱으로_참조된_커맨드가_모두_존재한다` 를 깨뜨린다 (질문 선택지에 있던 `/gx-재생성` 을 실재 커맨드 참조로 본다). `.omc/` 는 이미 같은 이유로 제외돼 있다.

- [ ] **Step 1: 지금 깨져 있음을 확인한다**

Run: `python -m unittest discover -s tests -t tests > /tmp/t.txt 2>&1; sed -n '/^FAIL:/,/^---/p' /tmp/t.txt`

Expected: `FAIL: test_백틱으로_참조된_커맨드가_모두_존재한다 ... (문서=WindowsPath('.dev/main/decisions.md'), 커맨드='gx-재생성')`

- [ ] **Step 2: `read_docs()` 에서 `.dev` 를 뺀다**

`tests/helpers.py` 의 `read_docs()` 안, `if ".omc" in path.parts:` 블록 **바로 아래**에 넣는다.

```python
        if ".dev" in path.parts:
            continue  # .dev 는 훅이 쓰는 런타임 기록(의사결정 로그)이라 검사 대상이 아니다
```

그리고 같은 함수의 독스트링에서 이 줄을

```
    .omc 는 런타임 상태 디렉터리라 검사 대상이 아니다.
```

이렇게 바꾼다.

```
    .omc·.dev 는 런타임 상태 디렉터리라 검사 대상이 아니다. .dev 는 훅이 남기는
    의사결정 로그라 아직 만들지 않은 커맨드 이름이 선택지로 그대로 실린다.
```

- [ ] **Step 3: 초록이 되는지 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 125 tests` / `OK`

- [ ] **Step 4: 저장소 루트 `.gitignore` 에 `.dev/` 를 넣는다**

`# oh-my-claudecode runtime` 블록의 `.omc/` 바로 아래 줄에 넣는다.

```
.dev/
```

- [ ] **Step 5: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git checkout -b feat/evidence-metering-and-id-succession
```

```bash
cd /d/SQ/gx-pm/gx-pm && git add plugins/gx-pm/tests/helpers.py .gitignore && git commit -m "fix: 런타임 디렉터리 .dev 가 계약 검사를 깨뜨리지 않게 한다"
```

---

## Task 2: 근거 규칙 정본을 세운다

**Files:**
- Create: `templates/evidence-rules.md`
- Test: `tests/test_plugin_consistency.py` (`EvidenceRuleTest` 클래스 신설)

**Interfaces:**
- Produces: `templates/evidence-rules.md` 를 다음 태스크들이 경로 문자열로 참조한다.
  절 제목 세 개가 계약이다 — `## 근거 4단`, `## [확인필요] 는 두 종류다`, `## 근거 가용도 경고`.
  Task 3(AN-03·generate-function-spec) · Task 4(generate-unit-test-plan) · Task 5(gx-spec) 이 이 경로를 인용한다.

- [ ] **Step 1: 실패하는 계약 테스트를 쓴다**

`tests/test_plugin_consistency.py` 의 `class BoundaryRuleTest` **바로 위**에 넣는다.

```python
class EvidenceRuleTest(unittest.TestCase):
    """근거 계측의 정본은 templates/evidence-rules.md 다.

    v3.0.0 은 AN-03 이 '제약이 비면 테스트가 정상 케이스만 나온다' 고 경고하면서도
    비었는지 세지 않았다. 세는 규칙을 한 곳에 두고, 실행부가 복제 대신 참조하게 한다.
    """

    def setUp(self):
        self.text = (PLUGIN_ROOT / "templates" / "evidence-rules.md").read_text(
            encoding="utf-8"
        )

    def test_근거가_네_단이다(self):
        """소스 역추출이 v3.0.0 정본에 빠져 있었다.

        memo 실행에서 검증 순서·기본값 같은 규칙은 전부 소스에서 나왔는데
        도출 출처에 없는 근거였다. 단수를 셀 수 없으면 가용도 경고가 성립하지 않는다.
        """
        구간 = re.search(r"^## 근거 4단$(.*?)(?=^## |\Z)", self.text, re.M | re.S)
        self.assertIsNotNone(구간, "§근거 4단 절을 찾지 못했습니다")
        단 = re.findall(r"^\| [1-9] \|", 구간.group(1), re.M)
        self.assertEqual(len(단), 4, f"근거 단이 4개가 아닙니다: {len(단)}개")
        for 근거 in ("요구사항 상세내용", "처리내용 역산", "기존 DDL", "기존 소스"):
            with self.subTest(근거=근거):
                self.assertIn(근거, 구간.group(1))

    def test_확인필요가_두_종류로_갈린다(self):
        for 종류 in ("[확인필요:항목]", "[확인필요:제약]"):
            with self.subTest(종류=종류):
                self.assertIn(종류, self.text, f"{종류} 정의가 없습니다")

    def test_제약이_빈_것의_판정_기준이_있다(self):
        """'제약이 비었다' 를 정의하지 않으면 판정이 사람마다 달라진다."""
        self.assertIn("필수", self.text)
        self.assertRegex(
            self.text, r"길이·범위·형식·열거값",
            "정량 제약의 범위가 열거돼 있지 않습니다",
        )

    def test_가용도_미달인데_확인필요가_0건이면_경고한다(self):
        구간 = re.search(r"^## 근거 가용도 경고$(.*?)(?=^## |\Z)", self.text, re.M | re.S)
        self.assertIsNotNone(구간, "§근거 가용도 경고 절을 찾지 못했습니다")
        self.assertIn("4/4 미만", 구간.group(1))
        self.assertIn("0건", 구간.group(1))

    def test_제약_미상은_자동보강하지_않는다(self):
        self.assertIn("제약 미상", self.text)
        self.assertIn("지어내", self.text)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k EvidenceRuleTest`
Expected: 5건 모두 ERROR — `FileNotFoundError: ... templates/evidence-rules.md`

- [ ] **Step 3: 정본을 쓴다**

`templates/evidence-rules.md` 를 이 내용으로 만든다.

````markdown
# 근거 규칙 (정본)

기능명세(AN-03)의 `입력항목`·`처리내용(로직)` 을 무엇으로 채웠는지, 못 채운 것이
얼마나 되는지를 세는 규칙이다. AN-03·DE-13·`/gx-spec` 이 이 문서를 참조한다.
**규칙을 복제하지 않는다.**

## 근거 4단

번호가 작을수록 우선한다.

| # | 근거 | 가용 판정 |
|---|------|----------|
| 1 | 요구사항 상세내용 | 항상 가용 — AN-02 가 하드 선행이다 |
| 2 | 처리내용 역산 | 항상 가용 — 자기 산출물이다 |
| 3 | 기존 DDL 의 컬럼 제약 | `profile.assets.ddlFile` 이 있으면 가용 |
| 4 | 기존 소스의 구현 | `profile.assets.sourcePath` 또는 `source-index.json` 이 있으면 가용 |

**3·4 단이 실제 변수다.** A유형(신규 구축)은 둘 다 없어 2/4 가 된다.
C유형(산출물 정비)은 대개 4/4 다.

4단은 `scan-source-index` 스킬이 만든 색인에서 읽는다. 소스에서 읽은 제약은
문서 근거와 어긋날 수 있으므로, 어긋나면 **문서를 우선하고 불일치를 게이트에 보고한다.**

## [확인필요] 는 두 종류다

| 표기 | 뜻 | 결과 |
|------|-----|------|
| `[확인필요:항목]` | 입력항목 자체를 못 정했다 | 그 항목이 아예 없다 |
| `[확인필요:제약]` | 항목은 정했으나 타입·길이·범위·형식·필수여부를 못 정했다 | **경계 케이스가 안 나온다** |

AN-03 `입력항목` 열의 형식은 `항목명(타입, 제약, 필수여부, 기본값)` 이다.

### 제약이 비었다는 판정

괄호 안에 **길이·범위·형식·열거값**이 하나도 없으면 제약이 빈 것이다.
`필수` 만 있는 것은 제약이 아니다 — 미입력 예외 1건만 만들고 경계는 못 만든다.

| 표기 | 판정 |
|------|------|
| `이메일(필수)` | **비었다** → `[확인필요:제약]` |
| `이메일(필수, 1~255자)` | 찼다 |
| `상태(필수, 대기\|승인\|반려)` | 찼다 — 열거값이다 |
| `등록일(date, 필수)` | 찼다 — 타입이 형식을 정한다 |

판정 결과는 AN-03 의 `비고` 열에 적는다. **컬럼을 늘리지 않는다.**

집계할 때는 두 종류를 합쳐 `[확인필요] {K}건 — 항목 {K1} / 제약 {K2}` 로 낸다.

## 근거 가용도 경고

게이트 2 에 가용도를 함께 낸다.

```
근거 가용도 2/4 — 요구사항 상세 ✓ / 처리내용 역산 ✓ / 기존 DDL ✗ / 기존 소스 ✗
```

**가용도가 4/4 미만인데 `[확인필요]` 가 0건이면 경고한다.**

```
⚠ 근거 4단 중 2단만 살아 있는데 [확인필요] 가 0건입니다.
   문서 근거 없이 채운 값이 없는지 확인하세요.
```

근거가 덜 살아 있는데 아무것도 확인이 필요하지 않다는 건 산술적으로 이상하다.
이 한 줄이 없으면 A유형에서 「지어낸 값」과 「충분한 입력」이 화면에서 똑같아 보인다.

## 제약 미상은 자동 보강 대상이 아니다

`skills/generate-unit-test-plan/SKILL.md` Step 6 의 자동 보강은
**제약이 있는데 케이스가 없을 때만** 적용한다.

제약 자체가 없으면 보강하지 않는다. 경계값을 **지어내는** 것이 되기 때문이다.
근거 없는 경계값은 없는 것보다 나쁘다 — 통과하면 검증됐다고 오독된다.

`제약 미상` 목록에 넣어 게이트 3 에 보고하고, 사용자가 제약을 주면 그때 보강한다.
````

- [ ] **Step 4: 통과를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k EvidenceRuleTest`
Expected: `Ran 5 tests` / `OK`

- [ ] **Step 5: 전건이 여전히 초록인지 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 130 tests` / `OK`

- [ ] **Step 6: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git add plugins/gx-pm/templates/evidence-rules.md plugins/gx-pm/tests/test_plugin_consistency.py && git commit -m "feat: 근거 계측의 정본 evidence-rules.md 를 세운다"
```

---

## Task 3: AN-03 과 기능명세 생성이 근거 규칙을 따르게 한다

**Files:**
- Modify: `templates/AN-03-function-spec.md` (「입력항목 — 이 문서에서 가장 중요한 열」 절)
- Modify: `skills/generate-function-spec/SKILL.md` (Step 3, Step 6, 출력 형식)
- Test: `tests/test_plugin_consistency.py` (`EvidenceRuleTest` 에 메서드 추가)

**Interfaces:**
- Consumes: Task 2 의 `templates/evidence-rules.md` — 경로를 문자열로 인용한다.
- Produces: `generate-function-spec` 이 게이트 2 에 넘기는 집계 3종 —
  `근거 가용도 {n}/4` · `[확인필요] {K}건 — 항목 {K1} / 제약 {K2}` · `제약 미상 기능 {P}건`.
  Task 5 의 게이트 2 출력이 이 세 이름을 그대로 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`EvidenceRuleTest` 클래스 **끝에** 메서드 3개를 추가한다.

```python
    def test_AN_03_이_근거_정본을_참조한다(self):
        an03 = (PLUGIN_ROOT / "templates" / "AN-03-function-spec.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("templates/evidence-rules.md", an03)
        self.assertIn("[확인필요:제약]", an03)

    def test_AN_03_도출_출처가_네_단이다(self):
        """3단(요구사항·역산·DDL)만 적혀 있으면 소스 근거가 다시 사라진다."""
        an03 = (PLUGIN_ROOT / "templates" / "AN-03-function-spec.md").read_text(
            encoding="utf-8"
        )
        구간 = re.search(
            r"^## 입력항목 — 이 문서에서 가장 중요한 열$(.*?)(?=^## |\Z)",
            an03, re.M | re.S,
        )
        self.assertIsNotNone(구간, "AN-03 의 §입력항목 절을 찾지 못했습니다")
        단 = re.findall(r"^[1-9]\. ", 구간.group(1), re.M)
        self.assertEqual(len(단), 4, f"도출 출처가 4단이 아닙니다: {len(단)}개")
        self.assertIn("기존 소스", 구간.group(1))

    def test_기능명세_스킬이_확인필요_두_종류를_모두_안다(self):
        """정본만 고치고 실행부를 안 고치면 규칙이 돌지 않는다."""
        스킬 = (
            PLUGIN_ROOT / "skills" / "generate-function-spec" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for 종류 in ("[확인필요:항목]", "[확인필요:제약]"):
            with self.subTest(종류=종류):
                self.assertIn(종류, 스킬)
        self.assertIn("templates/evidence-rules.md", 스킬)
        for 집계 in ("근거 가용도", "제약 미상"):
            with self.subTest(집계=집계):
                self.assertIn(집계, 스킬)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k EvidenceRuleTest`
Expected: 3건 FAIL (`AssertionError: 'templates/evidence-rules.md' not found` 등)

- [ ] **Step 3: AN-03 템플릿의 도출 출처를 4단으로 바꾼다**

`templates/AN-03-function-spec.md` 의 이 블록을

```
도출 출처를 이 순서로 본다.

1. 요구사항 상세내용에 명시된 입력
2. 처리내용에서 역산 — 그룹핑하려면 그룹 키가 입력이어야 한다
3. 기존 DDL 이 있으면 컬럼 제약(길이·NotNull)

셋 다 실패하면 `[확인필요]` 로 두고 **지어내지 않는다.**
```

이렇게 바꾼다.

```
도출 출처를 이 순서로 본다. 정본은 `templates/evidence-rules.md` §근거 4단이다.

1. 요구사항 상세내용에 명시된 입력
2. 처리내용에서 역산 — 그룹핑하려면 그룹 키가 입력이어야 한다
3. 기존 DDL 이 있으면 컬럼 제약(길이·NotNull)
4. 기존 소스가 있으면 실제 구현의 검증 로직 — `scan-source-index` 색인에서 읽는다

넷 다 실패하면 `[확인필요:항목]` 으로 두고 **지어내지 않는다.**
항목은 찾았으나 길이·범위·형식·열거값을 못 찾았으면 `[확인필요:제약]` 이다.
`이메일(필수)` 는 제약이 빈 것이고, `이메일(필수, 1~255자)` 는 찬 것이다.
판정 기준은 `templates/evidence-rules.md` §[확인필요] 는 두 종류다 가 정본이다.
```

같은 파일 컬럼 표의 10번 행을

```
| 10 | 비고 | `[확인필요]` 사유, 분류 승계 예외 |
```

이렇게 바꾼다.

```
| 10 | 비고 | `[확인필요:항목]`·`[확인필요:제약]` 사유, 분류 승계 예외 |
```

- [ ] **Step 4: `generate-function-spec` 의 Step 3 을 바꾼다**

이 블록을

```
### Step 3: 입력항목 도출

`templates/AN-03-function-spec.md` 의 도출 출처 3단계를 따른다.
근거가 없으면 `[확인필요]` 로 둔다 — **지어내지 않는다.**
```

이렇게 바꾼다.

````
### Step 3: 입력항목 도출

`templates/AN-03-function-spec.md` 의 도출 출처 4단을 따른다.
판정 기준의 정본은 `templates/evidence-rules.md` 다.

- 항목 자체를 못 정했으면 `[확인필요:항목]`
- 항목은 정했으나 길이·범위·형식·열거값이 하나도 없으면 `[확인필요:제약]`

둘 다 **지어내지 않는다.** `필수` 만 붙은 것은 제약이 빈 것이다.

**근거 가용도를 함께 센다.** 4단 중 몇 단이 살아 있는지를 프로파일에서 판정한다.

| 단 | 가용 조건 |
|---|----------|
| 1·2 | 항상 가용 |
| 3 | `profile.assets.ddlFile` 이 있다 |
| 4 | `profile.assets.sourcePath` 또는 `source-index.json` 이 있다 |
````

- [ ] **Step 5: `generate-function-spec` 의 Step 6 에 집계를 넣는다**

Step 6 의 마지막 줄 뒤에 이 블록을 덧붙인다.

````
- **제약 미상 기능**을 센다 — 입력항목 전부가 `[확인필요:제약]` 이거나
  정량 제약이 하나도 없는 기능이다. 이 기능은 DE-13 에서 경계 케이스가 나오지 않는다.
  **차단하지 않는다.** 지어낼 수 없으므로 목록으로 넘긴다.

게이트 2 에 넘길 집계 3종을 만든다.

```
근거 가용도 {n}/4 — 요구사항 상세 {✓} / 처리내용 역산 {✓} / 기존 DDL {✗} / 기존 소스 {✓}
[확인필요] {K}건 — 항목 {K1} / 제약 {K2}
제약 미상 기능 {P}건
```

`{n} < 4` 이고 `{K} == 0` 이면 `templates/evidence-rules.md` §근거 가용도 경고의
경고 문구를 함께 넘긴다.
````

- [ ] **Step 6: 출력 형식의 `[확인필요] 목록` 표에 `종류` 열을 넣는다**

이 표를

```
### [확인필요] 목록

| 기능ID | 열 | 사유 |
|--------|-----|------|
| FN-004 | 입력항목 | 요구사항에 입력 제약이 없고 DDL 도 없음 |
```

이렇게 바꾼다.

```
### [확인필요] 목록

| 기능ID | 종류 | 열 | 사유 |
|--------|------|-----|------|
| FN-004 | 항목 | 입력항목 | 요구사항·처리내용·DDL·소스 어디에도 입력이 없음 |
| FN-006 | 제약 | 입력항목 | `사유(필수)` — 길이 근거가 없음. 근거 4단 중 2단만 가용 |
```

- [ ] **Step 7: 통과를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k EvidenceRuleTest`
Expected: `Ran 8 tests` / `OK`

- [ ] **Step 8: 전건을 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 133 tests` / `OK`

- [ ] **Step 9: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git add plugins/gx-pm/templates/AN-03-function-spec.md plugins/gx-pm/skills/generate-function-spec/SKILL.md plugins/gx-pm/tests/test_plugin_consistency.py && git commit -m "feat: 제약이 비었다는 사실을 세어 게이트에 넘긴다"
```

---

## Task 4: 제약 미상이 자동 보강으로 메워지지 않게 한다

**Files:**
- Modify: `skills/generate-unit-test-plan/SKILL.md` (Step 6 충분성 검증, 체크포인트)
- Test: `tests/test_plugin_consistency.py` (`EvidenceRuleTest` 에 메서드 추가)

**Interfaces:**
- Consumes: Task 3 이 만든 `제약 미상 기능 {P}건` 집계.
- Produces: 게이트 3 에 넘길 `제약 미상으로 경계 케이스가 없는 기능 {P}건`. Task 5 가 쓴다.

**배경:** 현재 Step 6 은 「제약이 **있는데** 경계 케이스가 없으면 자동 보강」한다. 제약이 아예 없으면 이 규칙에 걸리지 않고, 「정상 케이스만 있는 기능」에도 안 걸린다 (미입력 예외가 1건 생기므로). 조용히 통과한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`EvidenceRuleTest` 끝에 추가한다.

```python
    def test_단위테스트_스킬이_제약_미상을_보강에서_제외한다(self):
        """제약이 없는데 경계값을 만들면 지어낸 테스트가 된다.

        v3.0.0 Step 6 은 '제약이 있는데 케이스가 없으면' 만 보강했다. 제약이 아예
        없는 경우는 정상+미입력 2건에서 멈추는데 '정상 케이스만' 에도 안 걸려
        조용히 통과했다.
        """
        스킬 = (
            PLUGIN_ROOT / "skills" / "generate-unit-test-plan" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("제약 미상", 스킬)
        self.assertIn("templates/evidence-rules.md", 스킬)
        구간 = re.search(
            r"^### Step 6: 충분성 검증$(.*?)(?=^### |\Z)", 스킬, re.M | re.S
        )
        self.assertIsNotNone(구간, "generate-unit-test-plan 의 Step 6 절을 찾지 못했습니다")
        self.assertIn("제약 미상", 구간.group(1))
        self.assertRegex(
            구간.group(1), r"보강하지 않는다|지어내",
            "Step 6 에 '제약이 없으면 보강하지 않는다' 는 지시가 없습니다",
        )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k EvidenceRuleTest`
Expected: 1건 FAIL — `AssertionError: '제약 미상' not found`

- [ ] **Step 3: Step 6 을 고친다**

`skills/generate-unit-test-plan/SKILL.md` 의 이 블록을

```
### Step 6: 충분성 검증

- 정상 케이스만 있는 기능이 있으면 **차단**한다
- 필수 항목이 있는데 미입력 예외가 없으면 자동 보강한다
- 길이·범위 제약이 있는데 경계 케이스가 없으면 자동 보강한다
```

이렇게 바꾼다.

````
### Step 6: 충분성 검증

- 정상 케이스만 있는 기능이 있으면 **차단**한다
- 필수 항목이 있는데 미입력 예외가 없으면 자동 보강한다
- 길이·범위 제약이 **있는데** 경계 케이스가 없으면 자동 보강한다

**제약이 아예 없으면 보강하지 않는다.** 경계값을 지어내는 것이 되기 때문이다.
판정 기준은 `templates/evidence-rules.md` §제약이 비었다는 판정이 정본이다.

정량 제약(길이·범위·형식·열거값)이 하나도 없는 기능은 케이스가 정상 + 미입력
2건에서 멈춘다. 이걸 `제약 미상` 목록에 모아 게이트 3 에 보고한다.

```
제약 미상으로 경계 케이스가 없는 기능 {P}건 — 지어내지 않고 남겨둔 것입니다

  · FN-006  사유(필수)      길이 근거 없음
  · FN-011  검색어(필수)    형식 근거 없음
```

**차단하지 않는다.** 사용자가 제약을 주면 그때 보강한다.
차단하면 A유형(RFP만)에서 파이프라인이 아예 못 지나간다 — 제약이 원래 없는 게 정상이다.
````

- [ ] **Step 4: 체크포인트 목록에 항목을 더한다**

체크포인트 블록의 `5.` 뒤에 한 줄 넣는다.

```
6. 제약 미상으로 경계 케이스가 없는 {N}건 — 제약을 지금 줄지, 남겨둘지
```

- [ ] **Step 5: 통과를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k EvidenceRuleTest`
Expected: `Ran 9 tests` / `OK`

- [ ] **Step 6: 전건을 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 134 tests` / `OK`

- [ ] **Step 7: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git add plugins/gx-pm/skills/generate-unit-test-plan/SKILL.md plugins/gx-pm/tests/test_plugin_consistency.py && git commit -m "feat: 제약이 없으면 경계값을 지어내지 않고 목록으로 남긴다"
```

---

## Task 5: 게이트 2·3 이 계측 결과를 보여준다

**Files:**
- Modify: `commands/gx-spec.md` (Step 6 게이트 2 블록, Step 9 게이트 3 블록)
- Test: `tests/test_plugin_consistency.py` (`EvidenceRuleTest` 에 메서드 추가)

**Interfaces:**
- Consumes: Task 3 의 집계 3종, Task 4 의 `제약 미상` 목록.
- Produces: 없음 — 사용자 화면이 종착지다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`EvidenceRuleTest` 끝에 추가한다.

```python
    def test_게이트2가_근거_집계를_보여준다(self):
        """계측하고 안 보여주면 계측하지 않은 것과 같다.

        Step 절로 범위를 좁혀서 본다 — 파일 어딘가에 낱말이 있는 것으로는
        게이트 화면에 실린다는 보장이 안 된다.
        """
        본문 = (PLUGIN_ROOT / "commands" / "gx-spec.md").read_text(encoding="utf-8")
        구간 = re.search(
            r"^### Step 6: 게이트 2(.*?)(?=^### |\Z)", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "gx-spec.md 에서 Step 6(게이트 2) 절을 찾지 못했습니다")
        for 항목 in ("근거 가용도", "[확인필요]", "제약 미상"):
            with self.subTest(항목=항목):
                self.assertIn(항목, 구간.group(1), f"게이트 2 에 '{항목}' 이 없습니다")
        self.assertIn("templates/evidence-rules.md", 구간.group(1))

    def test_게이트3이_제약_미상을_보여준다(self):
        본문 = (PLUGIN_ROOT / "commands" / "gx-spec.md").read_text(encoding="utf-8")
        구간 = re.search(
            r"^### Step 9: 게이트 3(.*?)(?=^### |\Z)", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "gx-spec.md 에서 Step 9(게이트 3) 절을 찾지 못했습니다")
        self.assertIn("제약 미상", 구간.group(1))
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k EvidenceRuleTest`
Expected: 2건 FAIL

- [ ] **Step 3: 게이트 2 블록을 고친다**

`commands/gx-spec.md` Step 6 의 코드펜스 안에서 이 네 줄을

```
  • AN-03 기능명세 표
  • DE-08 테이블정의 표 (신규 컬럼 강조)
  • [확인필요] 목록 {K}건 — 입력항목·처리내용을 문서에서 확정하지 못한 곳
  • 제약 불일치 목록 {C}건 — 기능의 입력 제약과 컬럼 제약이 어긋난 곳
```

이렇게 바꾼다.

```
  • AN-03 기능명세 표
  • DE-08 테이블정의 표 (신규 컬럼 강조)
  • 근거 가용도 {n}/4 — 요구사항 상세 {✓} / 처리내용 역산 {✓} / 기존 DDL {✗} / 기존 소스 {✓}
  • [확인필요] 목록 {K}건 — 항목 {K1} / 제약 {K2}
  • 제약 미상 기능 {P}건 — 입력항목에 정량 제약이 없어 경계 케이스가 안 나옵니다
  • 제약 불일치 목록 {C}건 — 기능의 입력 제약과 컬럼 제약이 어긋난 곳
```

같은 Step 의 코드펜스 **바로 아래**, `승인 후 **manage-revision-history**` 줄 **위**에 이 문단을 넣는다.

```
`{n} < 4` 이고 `{K} == 0` 이면 `templates/evidence-rules.md` §근거 가용도 경고의
경고 문구를 위 목록 아래에 함께 낸다. 근거가 덜 살아 있는데 확인할 것이 하나도
없다는 건 산술적으로 이상하다 — 지어낸 값이 있다는 신호다.
```

- [ ] **Step 4: 게이트 3 블록을 고친다**

Step 9 의 코드펜스 안에서 이 세 줄을

```
  • DE-13 단위테스트계획 표
  • AN-05 추적매트릭스 표
  • 누락 유형별 건수
```

이렇게 바꾼다.

```
  • DE-13 단위테스트계획 표
  • AN-05 추적매트릭스 표
  • 누락 유형별 건수
  • 제약 미상으로 경계 케이스가 없는 기능 {P}건 — 지어내지 않고 남겨둔 것입니다
```

같은 코드펜스의 「주요 확인」 3번 뒤에 한 줄 넣는다.

```
4. 제약 미상 {P}건에 지금 제약을 줄지, 다음 차수로 남길지
```

- [ ] **Step 5: 통과를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k EvidenceRuleTest`
Expected: `Ran 11 tests` / `OK`

- [ ] **Step 6: 전건을 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 136 tests` / `OK`

- [ ] **Step 7: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git add plugins/gx-pm/commands/gx-spec.md plugins/gx-pm/tests/test_plugin_consistency.py && git commit -m "feat: 게이트 2·3 이 근거 계측 결과를 보여준다"
```

---

## Task 6: DDL 부재 사실이 문서에 남는다

**Files:**
- Modify: `templates/DE-08-table-definition.md` (「기존 DDL 이 없으면 전건이 `신규`」 문장 근처)
- Modify: `skills/convert-ddl-to-tablespec/SKILL.md` (Step 2 진입 지점)
- Test: `tests/test_plugin_consistency.py` (`DdlAbsenceNoticeTest` 클래스 신설)

**Interfaces:**
- Consumes: 없음.
- Produces: DE-08 산출물의 `## 개정이력` 위에 놓이는 인용 블록 한 줄. 다른 태스크가 소비하지 않는다.

**배경:** `commands/gx-spec.md:128` 이 DDL 부재를 게이트 2 **화면**에만 적는다. 승인하면 화면은 사라지고 문서만 남아, 나중에 여는 사람은 그것이 설계 초안인지 실제 스키마인지 알 수 없다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`EvidenceRuleTest` **아래**에 새 클래스로 넣는다.

```python
class DdlAbsenceNoticeTest(unittest.TestCase):
    """DDL 이 없어 전건 신규가 된 DE-08 은 실제 스키마가 아니라 설계 초안이다.

    v3.0.0 은 이 사실을 게이트 2 화면에만 적었다. 승인하면 화면은 사라지고
    문서만 남아, 이 문서가 실제 스키마로 오독된다 — 플러그인이 없애려던 문제 그 자체다.
    """

    def test_DE_08_템플릿이_설계_초안_표기를_요구한다(self):
        text = (
            PLUGIN_ROOT / "templates" / "DE-08-table-definition.md"
        ).read_text(encoding="utf-8")
        self.assertIn("설계 초안", text)
        self.assertIn("개정이력", text)
        self.assertRegex(
            text, r"전건이? 신규",
            "전건 신규일 때만이라는 조건이 없습니다 — 일부 신규에도 붙으면 경고가 무뎌집니다",
        )

    def test_역생성_스킬이_경고_줄을_넣는다(self):
        """템플릿만 고치고 실행부를 안 고치면 규칙이 돌지 않는다."""
        text = (
            PLUGIN_ROOT / "skills" / "convert-ddl-to-tablespec" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("설계 초안", text)
        self.assertIn("templates/DE-08-table-definition.md", text)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k DdlAbsenceNoticeTest`
Expected: 2건 FAIL — `AssertionError: '설계 초안' not found`

- [ ] **Step 3: DE-08 템플릿에 규칙 절을 넣는다**

`templates/DE-08-table-definition.md` 에서 이 줄을 찾는다.

```
- 기존 DDL 이 없으면 전건이 `신규` 가 되어 전부 표준 제안 대상이 된다
```

그 줄이 속한 목록 **바로 아래**, 다음 `##` 헤딩 **위**에 이 절을 넣는다.

````
## DDL 부재 시 문서 머리 경고 (필수)

기존 DDL 이 없어 **컬럼 전건이 `신규`** 가 된 경우, 산출물의 `## 개정이력` **바로 위**에
이 줄을 넣는다.

```
> ⚠ **기존 DDL 부재** — 이 문서는 AN-03 기능명세의 입력항목에서 도출한 **설계 초안**이다.
> 실제 스키마가 아니므로, 개발 착수 후 실제 DDL 로 `/gx-테이블정의서` 를 다시 돌려 재생성한다.
```

기존 컬럼이 **1건이라도** 있으면 넣지 않는다. 전건 신규일 때만이다.
일부 신규에도 붙이면 경고가 무뎌져 아무도 안 읽는다.

게이트 화면에만 적고 문서에 안 남기면, 게이트를 승인한 뒤 이 사실이 사라진다.
그러면 이 문서를 나중에 여는 사람은 설계 초안인지 실제 스키마인지 알 방법이 없다.
````

- [ ] **Step 4: `convert-ddl-to-tablespec` 에 삽입 단계를 넣는다**

이 줄을 찾는다.

```
DDL 이 없으면 기존 스키마 없음으로 보고 Step 2 로 간다 (전건이 신규가 된다).
```

그 줄 바로 뒤에 이어 붙인다.

```
이 경우 산출물의 `## 개정이력` 바로 위에 **설계 초안 경고 줄**을 넣는다.
문구와 조건은 `templates/DE-08-table-definition.md` §DDL 부재 시 문서 머리 경고가 정본이다.
기존 컬럼이 1건이라도 있으면 넣지 않는다.
```

- [ ] **Step 5: 통과를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k DdlAbsenceNoticeTest`
Expected: `Ran 2 tests` / `OK`

- [ ] **Step 6: 전건을 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 138 tests` / `OK`

- [ ] **Step 7: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git add plugins/gx-pm/templates/DE-08-table-definition.md plugins/gx-pm/skills/convert-ddl-to-tablespec/SKILL.md plugins/gx-pm/tests/test_plugin_consistency.py && git commit -m "feat: DDL 이 없어 만든 테이블정의서에 설계 초안임을 남긴다"
```

---

## Task 7: ID 승계 스킬을 만든다

**Files:**
- Create: `skills/reconcile-ids/SKILL.md`
- Test: `tests/test_plugin_consistency.py` (`IdSuccessionTest` 클래스 신설)

**Interfaces:**
- Consumes: `backup/{시스템코드}-{산출물명}_{YYMMDD}.md` (`detect-existing-artifact` 가 만든다), 프로파일의 `idNaming`.
- Produces: ID 가 확정된 표 + 승계 집계 `승계 {S} / 신규 {N} / 삭제 {D} / 판정 필요 {A}`.
  Task 8 이 `detect-existing-artifact` 에서, Task 9 가 커맨드 4개에서 이 스킬을 부른다.
  `manage-revision-history` 가 이 스킬 **뒤에** 돈다.

**배경:** memo 실행에서 `RSV-RE-003` 이 「비밀번호 길이」→「이메일 형식 검증」으로 의미가 바뀌었다. `manage-revision-history` Step 2 가 요구사항ID 를 **불변 키**로 대조하므로, ID 가 밀리면 개정이력이 전건 「삭제 + 추가」로 나와 무의미해진다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`DdlAbsenceNoticeTest` **아래**에 새 클래스로 넣는다.

```python
class IdSuccessionTest(unittest.TestCase):
    """새로쓰기가 ID 를 처음부터 다시 매기면 개정이력의 불변 키 대조가 무너진다.

    memo 실행에서 RSV-RE-003 의 의미가 바뀌어 직전 버전과 ID 로 대조할 수 없었다.
    """

    def setUp(self):
        self.text = (
            PLUGIN_ROOT / "skills" / "reconcile-ids" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_대조_대상이_세_산출물이다(self):
        """DE-08 은 테이블명+컬럼명이 자연 키고 AN-05 는 ID 를 갖지 않는다."""
        for 산출물 in ("AN-02", "AN-03", "DE-13"):
            with self.subTest(산출물=산출물):
                self.assertIn(산출물, self.text)

    def test_판정_사다리가_네_갈래다(self):
        구간 = re.search(r"^### Step 3(.*?)(?=^### |\Z)", self.text, re.M | re.S)
        self.assertIsNotNone(구간, "§Step 3 판정 사다리 절을 찾지 못했습니다")
        갈래 = re.findall(r"^\| [①②③④] \|", 구간.group(1), re.M)
        self.assertEqual(len(갈래), 4, f"판정 갈래가 4개가 아닙니다: {len(갈래)}개")

    def test_승계_판정_애매성을_그_자리에서_묻는다(self):
        self.assertIn("이월하지 않는", self.text)
        self.assertRegex(self.text, r"그 자리에서 (묻는다|중단한다)")

    def test_삭제된_ID_를_재사용하지_않는다(self):
        self.assertIn("재사용", self.text)
        self.assertIn("templates/id-naming-rules.md", self.text)

    def test_전부_새로_매기기에_경고가_붙는다(self):
        """탈출구는 있어야 하지만 대가를 알려야 한다."""
        self.assertIn("개정이력", self.text)
        self.assertRegex(
            self.text, r"불변 키",
            "ID 를 전부 새로 매기면 무엇이 깨지는지 적혀 있지 않습니다",
        )

    def test_개정이력보다_먼저_돈다고_명시한다(self):
        self.assertIn("manage-revision-history", self.text)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k IdSuccessionTest`
Expected: 6건 모두 ERROR — `FileNotFoundError`

- [ ] **Step 3: 스킬을 쓴다**

`skills/reconcile-ids/SKILL.md` 를 이 내용으로 만든다.

````markdown
---
name: reconcile-ids
description: 산출물을 다시 만들 때 직전 버전과 대조해 같은 항목의 ID 를 승계합니다. 신규만 다음 순번을 받고 삭제된 ID 는 재사용하지 않습니다.
---

# ID 승계 대조 (reconcile-ids)

산출물 본문을 다시 도출한 뒤, **저장하기 전·게이트 승인 전**에 직전 버전과 대조하여
ID 를 승계한다. 게이트에서 사용자가 보는 표에는 이미 최종 ID 가 실려 있어야 한다.

## 왜 필요한가

`skills/manage-revision-history/SKILL.md` Step 2 는 산출물의 **불변 키**(요구사항ID·기능ID·
테스트ID)로 직전 버전과 대조한다. ID 가 밀리면 그 대조가 전건 「삭제 + 추가」로 나와
개정이력이 무의미해진다.

## 대상

| 산출물 | 대상 여부 | 이유 |
|--------|----------|------|
| AN-02 요구사항정의서 | **O** | 요구사항ID |
| AN-03 기능명세서 | **O** | 기능ID |
| DE-13 단위테스트계획서 | **O** | 테스트ID |
| DE-08 테이블정의서 | X | `테이블명 + 컬럼명` 이 자연 키라 승계가 필요 없다 |
| AN-05 추적매트릭스 | X | 자체 ID 를 갖지 않는 대조 결과물이다 |

## 입력

| 항목 | 필수 | 설명 |
|------|------|------|
| 직전 버전 파일 | N | `backup/{시스템코드}-{산출물명}_{YYMMDD}.md` 중 가장 최근 것 |
| 새로 도출한 표 | Y | 아직 ID 를 확정하지 않은 상태 |
| 산출물 유형 | Y | AN-02 · AN-03 · DE-13 중 하나 |
| 채번 규칙 | Y | 프로파일 `idNaming` |

## 처리 절차

### Step 1: 직전 버전 로드

`backup/` 에서 해당 산출물의 가장 최근 파일을 읽는다.
**없으면 전건 신규로 보고 순번 1부터 부여한 뒤 종료한다.** 첫 생성이 그렇다.

### Step 2: 대조 키

| 산출물 | 1차 키 (완전일치) | 2차 키 (의미일치) |
|--------|------------------|------------------|
| AN-02 | 요구사항명 | 요구사항 상세내용의 주 동작 + 대분류 |
| AN-03 | 기능명 | 처리내용(로직)의 주 동작 + 연계요구사항ID |
| DE-13 | 연계기능ID + 입력 | 기대결과 + 사전조건 |

### Step 3: 판정 사다리

| 순서 | 조건 | 처리 |
|---|------|------|
| ① | 1차 키가 완전히 같다 | **승계**. 묻지 않는다 |
| ② | 1차 키는 다르나 2차 키가 같다 | **승계 후보**. 그 자리에서 묻는다 |
| ③ | 둘 다 다르다 | **신규**. 마지막 순번 다음부터 |
| ④ | 직전에 있는데 새 결과에 없다 | **삭제**. Step 4 |

한 항목이 ①과 ② 양쪽에 걸리면 ①이 이긴다.
②에서 후보가 둘 이상이면 전부 보여주고 고르게 한다.

**②는 이월하지 않는다.** 게이트로 미루면 그 ID 로 이미 아래 산출물이 만들어진 뒤다.
DE-13 의 테스트ID 를 게이트 3 에서 고치면 Step 8 에서 이미 만들어진 AN-05 를 다시 만들어야 한다.
그 자리에서 묻는다.

### Step 4: 삭제 처리

| 산출물 | 처리 |
|--------|------|
| AN-02 | `상태` 열을 `삭제` 로 두고 **행을 남긴다**. `변경 근거` 에 사유를 적는다 |
| AN-03 | 행을 만들지 않는다 |
| DE-13 | 행을 만들지 않는다 |

AN-03·DE-13 에는 `상태` 열이 없어 남길 자리가 없다. **컬럼 정본은 늘리지 않는다.**
삭제 건수는 게이트에 보고한다.

삭제된 ID 는 **재사용하지 않는다.** 순번에 구멍이 남는 것을 허용한다
(`templates/id-naming-rules.md` §불변 규칙).

### Step 5: 신규 순번 시작점

직전 버전의 **최대 순번 + 1**. 삭제된 항목의 순번도 차지한 것으로 본다.

### Step 6: 승계안 보고 + 승인

**AskUserQuestion 도구**로 묻는다. `templates/approval-protocol.md` 의 인자 규칙을 따른다.

```
직전 버전과 대조했습니다. ({산출물명})

  승계   {S}건   기존 ID 유지
  신규   {N}건   {첫ID} 부터 부여
  삭제   {D}건   ID 폐기 (재사용 안 함)

  ⚠ 판정 필요 {A}건
     · "{직전 이름}" ↔ "{새 이름}"  → 같은 항목이면 {기존ID} 승계

  1. 위 승계안대로 진행
  2. 판정 필요 건을 하나씩 확인
  3. ID 를 전부 새로 매기기 (기존 ID 폐기)
```

`{A}` 가 0이면 2번을 빼고 1·3번만 낸다.

3번을 고르면 한 번 더 확인한다.

```
기존 ID {S}건이 폐기됩니다. 개정이력의 불변 키 대조가 성립하지 않아
직전 버전과의 변경 내역을 만들 수 없습니다. 계속할까요?
```

### Step 7: 개정이력으로 넘긴다

ID 가 확정된 표를 **manage-revision-history** 스킬에 넘긴다.
**순서를 뒤집지 않는다** — 불변 키 대조는 ID 가 확정된 뒤에만 성립한다.

## 출력 형식

```
## ID 승계 결과 — {산출물명}

| 구분 | 건수 | 비고 |
|------|------|------|
| 승계 | 45 | 기존 ID 유지 |
| 신규 | 7 | RSV-RE-053 ~ RSV-RE-059 |
| 삭제 | 1 | RSV-RE-018 (재사용 안 함) |
```

## 주의사항

1. **백업본이 없으면 이 스킬은 아무것도 하지 않는다** — 첫 생성이므로 정상이다
2. **`이어쓰기` 경로에서는 부르지 않는다** — 기존 행을 손대지 않으므로 대조할 것이 없다
3. **DE-08·AN-05 에는 적용하지 않는다** — 위 「대상」 표
4. **판정 필요 건은 게이트로 미루지 않는다** — Step 3 ②
````

- [ ] **Step 4: 통과를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k IdSuccessionTest`
Expected: `Ran 6 tests` / `OK`

- [ ] **Step 5: 전건을 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 144 tests` — 실패 1건.
`test_모든_스킬이_어느_커맨드에서든_호출된다` 가 `{'reconcile-ids'}` 로 실패한다.
배선은 Task 9 에서 한다. 이 실패는 예상된 것이다.

- [ ] **Step 6: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git add plugins/gx-pm/skills/reconcile-ids plugins/gx-pm/tests/test_plugin_consistency.py && git commit -m "feat: ID 승계 대조 스킬 reconcile-ids 를 만든다"
```

---

## Task 8: 새로쓰기가 ID 를 승계한다

**Files:**
- Modify: `skills/detect-existing-artifact/SKILL.md` (「새로쓰기 선택 시」, 「주의사항」)
- Modify: `skills/manage-revision-history/SKILL.md` (Step 2 앞)
- Modify: `templates/id-naming-rules.md` (§불변 규칙)
- Test: `tests/test_plugin_consistency.py` (`IdSuccessionTest` 에 메서드 추가)

**Interfaces:**
- Consumes: Task 7 의 `skills/reconcile-ids/SKILL.md`.
- Produces: `새로쓰기` 경로가 ID 를 보존한다. Task 9 의 커맨드 배선이 이 경로를 전제한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`IdSuccessionTest` 끝에 추가한다.

```python
    def test_새로쓰기가_ID_승계를_거친다(self):
        """새로쓰기의 의도는 '본문을 다시 뽑겠다' 이지 'ID 를 날리겠다' 가 아니다.

        절 안에서만 본다 — 파일 어딘가에 스킬 이름이 있는 것으로는
        새로쓰기 경로가 그걸 거친다는 보장이 안 된다.
        """
        text = (
            PLUGIN_ROOT / "skills" / "detect-existing-artifact" / "SKILL.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(
            r"^#### 2\. 새로쓰기 선택 시$(.*?)(?=^#### |\Z)", text, re.M | re.S
        )
        self.assertIsNotNone(구간, "detect-existing-artifact 의 §새로쓰기 절을 찾지 못했습니다")
        self.assertIn("reconcile-ids", 구간.group(1))

    def test_새로쓰기_안내문이_ID_를_날린다고_말하지_않는다(self):
        """선택지 설명이 옛 동작을 그대로 적고 있으면 사용자가 잘못 고른다."""
        text = (
            PLUGIN_ROOT / "skills" / "detect-existing-artifact" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("ID는 직전 버전과 대조해 승계", text)

    def test_개정이력이_ID_승계를_선행으로_둔다(self):
        text = (
            PLUGIN_ROOT / "skills" / "manage-revision-history" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("reconcile-ids", text)

    def test_채번_규칙이_승계_재생성을_명시한다(self):
        text = (PLUGIN_ROOT / "templates" / "id-naming-rules.md").read_text(
            encoding="utf-8"
        )
        구간 = re.search(r"^## 불변 규칙$(.*?)(?=^## |\Z)", text, re.M | re.S)
        self.assertIsNotNone(구간, "id-naming-rules.md 의 §불변 규칙 절을 찾지 못했습니다")
        self.assertIn("reconcile-ids", 구간.group(1))
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k IdSuccessionTest`
Expected: 4건 FAIL

- [ ] **Step 3: `detect-existing-artifact` 의 새로쓰기 절을 고친다**

이 블록을

```
#### 2. 새로쓰기 선택 시

1. `backup/` 폴더가 없으면 생성
2. 기존 파일을 `backup/{시스템코드}-{산출물명}_{YYMMDD}.md`로 복사
3. 기존 파일을 삭제
4. "기존 파일을 backup/{파일명}으로 백업했습니다." 안내
5. 처음부터 새로 생성하는 워크플로우를 진행
```

이렇게 바꾼다.

```
#### 2. 새로쓰기 선택 시

1. `backup/` 폴더가 없으면 생성
2. 기존 파일을 `backup/{시스템코드}-{산출물명}_{YYMMDD}.md`로 복사
3. 기존 파일을 삭제
4. "기존 파일을 backup/{파일명}으로 백업했습니다." 안내
5. 처음부터 새로 생성하는 워크플로우를 진행
6. **본문을 도출한 뒤, 저장·승인 전에 reconcile-ids 스킬로 ID 를 승계한다**

**새로쓰기는 본문을 다시 뽑는 것이지 ID 를 날리는 것이 아니다.**
6번을 건너뛰면 같은 요구사항이 다른 ID 를 받아, `manage-revision-history` 의
불변 키 대조가 전건 「삭제 + 추가」로 나온다. 개정이력이 무의미해진다.

ID 를 정말 전부 새로 매기려면 `reconcile-ids` 의 승계안 화면에서 3번을 고른다.
```

- [ ] **Step 4: 선택지 안내문을 고친다**

같은 파일 Step 2 의 코드펜스 안에서 이 두 줄을

```
  2. 새로쓰기
     기존 파일을 backup/ 폴더에 날짜를 붙여 백업한 후,
     처음부터 다시 생성합니다.
     백업 위치: backup/{시스템코드}-{산출물명}_{YYMMDD}.md
```

이렇게 바꾼다.

```
  2. 새로쓰기
     기존 파일을 backup/ 폴더에 날짜를 붙여 백업한 후,
     본문을 처음부터 다시 생성합니다.
     ID는 직전 버전과 대조해 승계합니다 — 같은 항목이면 기존 ID를 유지합니다.
     백업 위치: backup/{시스템코드}-{산출물명}_{YYMMDD}.md
```

- [ ] **Step 5: 주의사항에 한 줄 더한다**

「주의사항」의 `3. **새로쓰기 시 반드시 백업한다**...` 뒤에 넣는다.

```
4. **새로쓰기 시 ID 를 승계한다**: `reconcile-ids` 를 거치지 않으면 개정이력이 무너진다
```

이후 번호를 하나씩 밀어 5·6 으로 고친다.

- [ ] **Step 6: `manage-revision-history` 에 선행을 명시한다**

`### Step 2: 행 단위 대조` 의 첫 줄

```
산출물의 **불변 키**로 대조한다.
```

**앞에** 이 문단을 넣는다.

```
**이 대조는 reconcile-ids 스킬이 먼저 돈 것을 전제한다.**
ID 가 확정되지 않은 상태로 대조하면 같은 항목이 다른 ID 를 갖게 되어
결과가 전건 「삭제 + 추가」로 나온다. 순서를 뒤집지 않는다.
```

- [ ] **Step 7: `id-naming-rules.md` 의 불변 규칙에 한 줄 더한다**

```
- 재실행 시 마지막 순번 다음부터 이어서 부여한다
```

뒤에 넣는다.

```
- 산출물을 다시 만들 때는 **reconcile-ids** 스킬이 직전 버전과 대조해 ID 를 승계한다.
  같은 항목이면 기존 ID 를 그대로 쓰고, 신규만 다음 순번을 받는다
```

- [ ] **Step 8: 통과를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k IdSuccessionTest`
Expected: `Ran 10 tests` / `OK`

- [ ] **Step 9: 전건을 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 148 tests` — 실패 1건 (`test_모든_스킬이_어느_커맨드에서든_호출된다`). Task 9 에서 해소된다.

- [ ] **Step 10: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git add plugins/gx-pm/skills/detect-existing-artifact/SKILL.md plugins/gx-pm/skills/manage-revision-history/SKILL.md plugins/gx-pm/templates/id-naming-rules.md plugins/gx-pm/tests/test_plugin_consistency.py && git commit -m "feat: 새로쓰기가 ID 를 날리지 않고 승계한다"
```

---

## Task 9: 커맨드에 배선하고 이월 금지를 넷으로 늘린다

**Files:**
- Modify: `templates/pipeline-protocol.md` (§이월 금지 항목)
- Modify: `commands/gx-spec.md` (Step 2 · Step 4 · Step 7)
- Modify: `commands/gx-요구사항정의서.md` (Step 5 앞) · `gx-기능명세서.md` (Step 4 앞) · `gx-단위테스트계획서.md` (Step 5 앞)
- Modify: `tests/test_plugin_consistency.py` (`이월금지_중단점` 표 · 개수 검사 2건)

**Interfaces:**
- Consumes: Task 7·8 의 `reconcile-ids`.
- Produces: `test_모든_스킬이_어느_커맨드에서든_호출된다` 가 다시 초록이 된다.

**배경:** `이월금지_중단점` 표는 중단점 낱말 → Step 을 매핑한다. ID 승계 판정은 **세 Step(2·4·7)에서** 일어나므로, 개수 대조를 낱말의 **중복 없는 집합**으로 바꿔야 한다. 지금처럼 평탄화한 리스트 길이로 비교하면 규약 항목 4개 대 선언 낱말 6개가 되어 실패한다.

- [ ] **Step 1: 규약의 이월 금지 항목을 넷으로 늘린다**

`templates/pipeline-protocol.md` 의 이 줄을

```
다음 세 가지는 **절대 게이트로 미루지 않는다.**
```

이렇게 바꾸고

```
다음 네 가지는 **절대 게이트로 미루지 않는다.**
```

3번 항목 뒤에 4번을 붙인다.

```
4. **ID 승계 판정 애매성** — 산출물을 다시 만들 때 직전 버전의 어느 항목과 같은 것인지
   애매하면 그 자리에서 물어야 한다. 게이트로 미루면 그 ID 로 이미 아래 산출물이
   만들어진 뒤다. DE-13 의 테스트ID 를 게이트 3 에서 고치면 Step 8 에서 이미 만들어진
   AN-05 를 다시 만들어야 한다. 판정 기준은
   `skills/reconcile-ids/SKILL.md` Step 3 이 정본이다.
```

같은 파일 「단독 실행 vs 파이프라인 실행」 표의 `| 표 판정 애매성 중단점 |` 행 뒤에 넣는다.

```
| ID 승계 판정 중단점 | 판정 시 중단 | **동일하게 중단** |
```

- [ ] **Step 2: 테스트의 매핑 표와 개수 검사를 고친다**

`PipelineCommandTest.이월금지_중단점` 을 이렇게 바꾼다.

```python
    이월금지_중단점 = [
        {
            "step": "2",
            "중단점": ["시안", "표 판정", "ID 승계"],
            "정본": [
                "skills/extract-requirements/SKILL.md",
                "skills/reconcile-ids/SKILL.md",
            ],
        },
        {
            "step": "4",
            "중단점": ["ID 승계"],
            "정본": ["skills/reconcile-ids/SKILL.md"],
        },
        {
            "step": "5",
            "중단점": ["신규 컬럼명"],
            "정본": ["skills/convert-ddl-to-tablespec/SKILL.md"],
        },
        {
            "step": "7",
            "중단점": ["ID 승계"],
            "정본": ["skills/reconcile-ids/SKILL.md"],
        },
    ]
```

`test_gx_spec_이_이월_금지_항목을_하나도_빠뜨리지_않는다` 의 이 줄을

```python
        선언된것 = [낱말 for 항목 in self.이월금지_중단점 for 낱말 in 항목["중단점"]]
```

이렇게 바꾼다.

```python
        # ID 승계 판정은 Step 2·4·7 세 곳에서 같은 이름으로 일어난다.
        # 평탄화한 리스트 길이로 규약 항목 수와 비교하면 중복이 초과로 잡힌다.
        선언된것 = sorted(
            {낱말 for 항목 in self.이월금지_중단점 for 낱말 in 항목["중단점"]}
        )
```

`PipelineProtocolTest.test_이월_금지_항목이_세_개다` 를 이렇게 바꾼다.

```python
    def test_이월_금지_항목이_네_개다(self):
        """화면 축 제거로 화면 분리·ID 확정 두 항목이 소멸했고(v3.0.0),

        v3.1.0 에서 ID 승계 판정 애매성이 들어왔다. 이건 v2 의 'ID 확정' 과 다르다 —
        파생 ID 를 정하는 것이 아니라 직전 버전의 어느 항목과 같은지를 정하는 것이다.
        """
        구간 = re.search(
            r"^## 이월 금지 항목$(.*?)(?=^## |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(구간, "이월 금지 항목 절을 찾지 못했습니다")
        번호 = re.findall(r"^\d+\.\s", 구간.group(1), re.M)
        self.assertEqual(
            len(번호), 4,
            f"이월 금지 항목이 4개가 아닙니다: {len(번호)}개",
        )

    def test_이월_금지_항목에_ID_승계_판정이_있다(self):
        self.assertIn("ID 승계 판정", self.text)
        self.assertIn("reconcile-ids", self.text)
```

- [ ] **Step 3: 실패를 확인한다**

Run: `python -m unittest discover -s tests -t tests -k PipelineCommandTest`
Expected: `test_gx_spec_이_이월_금지_중단점을_선언한다` 가 Step 4·7 에서 FAIL

- [ ] **Step 4: `gx-spec.md` Step 2 에 ID 승계 중단점을 더한다**

Step 2 의 이 목록

```
- **시안/대안 감지** — 시안 선택이 틀리면 뒤 산출물이 전부 틀린다
- **표 판정 애매성** — ID 표가 요구사항 표인지 애매하면 그 자리에서 묻는다.
  판정 기준은 `skills/extract-requirements/SKILL.md` Step 2 가 정본이다.
  게이트 1 로 미루면 이미 그 건수로 만들어진 뒤다
```

바로 아래에 이어 붙이고, 그 위 문장의 「2개」를 「3개」로 고친다.

```
- **ID 승계 판정 애매성** — 직전 버전이 있으면 **reconcile-ids** 스킬로 ID 를 승계한다.
  어느 항목과 같은 것인지 애매하면 그 자리에서 묻는다. 이월하지 않는다.
  판정 기준은 `skills/reconcile-ids/SKILL.md` Step 3 이 정본이다
```

즉 Step 2 의 이 문장

```
**이월하지 않는 중단점 2개가 이 단계에 있다** (`templates/pipeline-protocol.md` §이월 금지 항목).
```

를 이렇게 바꾼다.

```
**이월하지 않는 중단점 3개가 이 단계에 있다** (`templates/pipeline-protocol.md` §이월 금지 항목).
```

- [ ] **Step 5: `gx-spec.md` Step 4 에 문단을 더한다**

Step 4 의 본문 뒤에 이어 붙인다.

```
직전 버전이 있으면 **reconcile-ids** 스킬로 기능ID 를 승계한다.
**ID 승계 판정 애매성 중단점은 이월하지 않는다** — 어느 기능과 같은 것인지 애매하면
그 자리에서 묻는다. 판정 기준은 `skills/reconcile-ids/SKILL.md` Step 3 이 정본이다.
```

- [ ] **Step 6: `gx-spec.md` Step 7 에 문단을 더한다**

Step 7 의 본문 뒤에 이어 붙인다.

```
직전 버전이 있으면 **reconcile-ids** 스킬로 테스트ID 를 승계한다.
**ID 승계 판정 애매성 중단점은 이월하지 않는다** — 게이트 3 으로 미루면 Step 8 에서
이미 만들어진 AN-05 를 다시 만들어야 한다. 그 자리에서 묻는다.
판정 기준은 `skills/reconcile-ids/SKILL.md` Step 3 이 정본이다.
```

- [ ] **Step 7: 단독 커맨드 3종에 배선한다**

`commands/gx-요구사항정의서.md` 의 `### Step 5: 개정이력 기록` **바로 위**에 넣는다.

```
### Step 4-1: ID 승계

직전 버전이 `backup/` 에 있으면 **reconcile-ids** 스킬로 요구사항ID 를 승계한다.
백업본이 없으면 첫 생성이므로 건너뛴다.
개정이력보다 **먼저** 돈다 — 불변 키 대조가 ID 확정을 전제한다.
```

`commands/gx-기능명세서.md` 의 `## Step 4: 개정이력 기록` **바로 위**에 넣는다.

```
## Step 3-1: ID 승계

직전 버전이 `backup/` 에 있으면 **reconcile-ids** 스킬로 기능ID 를 승계한다.
백업본이 없으면 첫 생성이므로 건너뛴다.
```

`commands/gx-단위테스트계획서.md` 의 `### Step 5: 케이스 검토 [필수 중단점 — 승인 루프]` **바로 위**에 넣는다.

```
### Step 4-1: ID 승계

직전 버전이 `backup/` 에 있으면 **reconcile-ids** 스킬로 테스트ID 를 승계한다.
백업본이 없으면 첫 생성이므로 건너뛴다.
```

- [ ] **Step 8: Step 번호 중복이 없는지 확인한다**

`test_커맨드의_Step_번호가_중복되지_않는다` 가 이를 검사한다.
`Step 4-1` · `Step 3-1` 형식은 기존 번호와 겹치지 않는다.

Run: `python -m unittest discover -s tests -t tests -k CommandStructureTest`
Expected: `OK`

- [ ] **Step 9: 전건을 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 149 tests` / `OK` — Task 7·8 에서 남겨둔 배선 실패가 여기서 해소된다.

- [ ] **Step 10: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git add plugins/gx-pm/templates/pipeline-protocol.md plugins/gx-pm/commands plugins/gx-pm/tests/test_plugin_consistency.py && git commit -m "feat: ID 승계 판정을 이월 금지 중단점으로 세우고 커맨드에 배선한다"
```

---

## Task 10: v3.1.0 으로 올리고 문서를 맞춘다

**Files:**
- Modify: `.claude-plugin/plugin.json` (version, description)
- Modify: `../../.claude-plugin/marketplace.json` (version, description)
- Modify: `../../README.md` (배지 3줄 · 스킬 표 · 디렉토리 트리 · 「3가지 선택지」)
- Modify: `CHANGELOG.md` (최상단에 v3.1.0 절)

**Interfaces:**
- Consumes: Task 2~9 의 결과 (스킬 16개 · 템플릿 12종).
- Produces: 없음 — 마지막 태스크다.

- [ ] **Step 1: 지금 무엇이 어긋나는지 확인한다**

Run: `python -m unittest discover -s tests -t tests -k VersionConsistencyTest`
Expected: `OK` — 스킬 수는 아직 배지와 맞지 않을 수 있으니 확인한다.

Run: `ls skills | wc -l && ls templates | wc -l`
Expected: `16` / `12`

- [ ] **Step 2: 매니페스트 2개를 고친다**

`.claude-plugin/plugin.json` — `"version": "3.0.0"` 을 `"3.1.0"` 으로.
`description` 안의 `15개 스킬` 을 `16개 스킬` 로. `커맨드 7개` 는 그대로.

`../../.claude-plugin/marketplace.json` — 같은 두 곳을 같게 고친다.

- [ ] **Step 3: README 배지를 고친다**

```
[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)]()
[![Skills](https://img.shields.io/badge/skills-15-green.svg)]()
```

```
[![Version](https://img.shields.io/badge/version-3.1.0-blue.svg)]()
[![Skills](https://img.shields.io/badge/skills-16-green.svg)]()
```

- [ ] **Step 4: README 디렉토리 트리를 고친다**

`# 15개 스킬` → `# 16개 스킬`
`# 산출물 양식 + 정본 규약 11종` → `# 산출물 양식 + 정본 규약 12종`

`skills/` 목록에서 알파벳 순서 자리(`prioritize-si/` 와 `scan-source-index/` 사이)에 넣는다.

```
│   │   ├── reconcile-ids/
```

`templates/` 목록에서 알파벳 순서 자리(`DE-13-unit-test-plan.md` 와 `id-naming-rules.md` 사이)에 넣는다.

```
│   │   ├── evidence-rules.md
```

- [ ] **Step 5: README 스킬 표에 행을 더한다**

`| `detect-existing-artifact` | 기존 산출물 감지 → 이어쓰기/새로쓰기/열기 3택 제공 |` 을 이렇게 바꾼다.

```
| `detect-existing-artifact` | 기존 산출물 감지 → 이어쓰기/새로쓰기/열기 3택 제공. 새로쓰기는 ID를 승계 |
```

같은 표에 행을 더한다.

```
| `reconcile-ids` | 재생성 시 직전 버전과 대조해 ID 승계. 신규만 다음 순번, 삭제된 ID는 재사용 안 함 |
```

- [ ] **Step 6: README 「3가지 선택지」 예시를 고친다**

```
  2. 새로쓰기 — backup/ 폴더에 백업 후 처음부터 재생성
```

```
  2. 새로쓰기 — backup/ 폴더에 백업 후 본문 재생성 (ID는 직전 버전에서 승계)
```

- [ ] **Step 7: README 머리말에 v3.1.0 한 줄을 더한다**

`**v3.0.0**: 플러그인을 화면 축에서...` 줄 **위**에 넣는다.

```
**v3.1.0**: 재생성해도 ID가 밀리지 않습니다. 제약이 비어 경계 케이스가 안 나오는 기능과, 근거가 부족한데 확인 요청이 0건인 상황을 게이트에서 알려줍니다.
```

- [ ] **Step 8: CHANGELOG 최상단에 절을 더한다**

```markdown
## [3.1.0] - 2026-09-04

v3.0.0 을 실제 프로젝트에 돌려 드러난 결함 4건을 막는다.

### 고침

- **새로쓰기가 ID 를 날리지 않는다.** 직전 버전과 대조해 같은 항목이면 기존 ID 를
  그대로 준다 (`reconcile-ids` 신설). 종전에는 처음부터 다시 매겨,
  `manage-revision-history` 의 불변 키 대조가 전건 「삭제 + 추가」로 나왔다.
- **제약이 비었다는 사실을 센다.** `[확인필요]` 를 `[확인필요:항목]` 과
  `[확인필요:제약]` 으로 가른다. 종전에는 `이메일(필수)` 처럼 제약 없이 적힌 항목이
  실패로 잡히지 않아 경계 케이스가 없는 기능이 조용히 통과했다.
- **근거 가용도를 게이트에 낸다.** 4단(요구사항 상세 · 처리내용 역산 · 기존 DDL ·
  기존 소스) 중 몇 단이 살아 있는지를 표시하고, 4/4 미만인데 `[확인필요]` 가
  0건이면 경고한다. 종전에는 「지어낸 값」과 「충분한 입력」이 화면에서 같아 보였다.
- **DDL 부재 사실이 문서에 남는다.** 전건 신규인 DE-08 은 머리에 설계 초안 경고를
  넣는다. 종전에는 게이트 화면에만 적혀 승인하면 사라졌다.

### 더함

- `templates/evidence-rules.md` — 근거 4단 · `[확인필요]` 2종 · 가용도 경고의 정본
- `skills/reconcile-ids/SKILL.md` — ID 승계 대조
- 이월 금지 항목이 셋에서 **넷**으로. `ID 승계 판정 애매성` 이 들어왔다
- 도출 출처에 **기존 소스**가 4단으로 들어왔다. v3.0.0 정본에 빠져 있었다

### 안 고친 것

- 게이트 1 조기 진단(요구사항 상세내용의 정량 제약 유무) — 다음 차수
- A유형 낱개 실행 권고 안내 — 규칙이 아니라 안내라 가치가 작다
```

- [ ] **Step 9: 전건을 확인한다**

Run: `python -m unittest discover -s tests -t tests 2>&1 | tail -3`
Expected: `Ran 149 tests` / `OK`

- [ ] **Step 10: 커밋**

```bash
cd /d/SQ/gx-pm/gx-pm && git add -A && git commit -m "docs: v3.1.0 — 근거 계측과 ID 승계로 버전·문서·매니페스트를 맞춘다"
```

---

## Self-Review

**1. 스펙 커버리지**

| 스펙 절 | 태스크 |
|---------|--------|
| §3 근거 규칙 정본 | Task 2 |
| §3.1 근거 4단 | Task 2, Task 3 (AN-03 반영) |
| §3.2 `[확인필요]` 2종 | Task 2, Task 3 |
| §3.3 가용도 경고 | Task 2, Task 3 (집계), Task 5 (표시) |
| §3.4 제약 미상 자동 보강 금지 | Task 2, Task 4 |
| §4 DDL 부재 표기 | Task 6 |
| §5.1 새로쓰기 의미 변경 | Task 8 |
| §5.2 `reconcile-ids` | Task 7 |
| §5.3 삭제 처리 | Task 7 (Step 4) |
| §6 게이트 출력 | Task 5 |
| §7 이월 금지 4번째 | Task 9 |
| §8 변경 범위 | 전 태스크 |
| §10 검증 | 각 태스크의 계약 테스트 |

빠진 스펙 요구는 없다.

**2. 플레이스홀더 점검**

`TBD` · `적절히` · `유사하게` 없음. 모든 편집 대상에 바꿀 전후 문자열을 그대로 적었다.

**3. 이름 정합**

- 스킬 이름 `reconcile-ids` — Task 7 신설, Task 8·9 참조. 표기 일치.
- 정본 경로 `templates/evidence-rules.md` — Task 2 신설, Task 3·4·5 참조. 표기 일치.
- 절 제목 `## 근거 4단` · `## [확인필요] 는 두 종류다` · `## 근거 가용도 경고` ·
  `## 제약이 비었다는 판정` — Task 2 가 만들고 Task 2·3·4 의 정규식이 찾는다. 일치.
- 집계 이름 `근거 가용도` · `[확인필요]` · `제약 미상` — Task 3 이 만들고 Task 5 가 쓴다. 일치.
- 테스트 클래스 `EvidenceRuleTest`(Task 2~5) · `DdlAbsenceNoticeTest`(Task 6) ·
  `IdSuccessionTest`(Task 7~8) — 중복 없음.

**4. 테스트 수 진행**

125(Task 1 이후 초록) → 130 → 133 → 134 → 136 → 138 → 144 → 148 → 149 → 149.
Task 7·8 은 배선 실패 1건을 의도적으로 남기고 Task 9 에서 해소한다. 계획에 명시했다.
