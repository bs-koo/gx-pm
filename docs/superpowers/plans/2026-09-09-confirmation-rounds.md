# 확인요청서 차수 왕복 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 미확정 질문을 대화(AskUserQuestion)에서 엑셀 파일로 옮기고, 게이트 2 에서 파이프라인을 중단해 최대 3차의 질문·답변 왕복으로 산출물을 확정한다.

**Architecture:** 확인요청서를 파일 하나(시트 4장)로 두고 `차수` 열로 이력을 쌓는다. 게이트 2 에서 1차를 발행하고 중단하며, 재개할 때 `apply-confirmations` 가 응답을 읽어 반영하고 **후속 질문을 다음 차수 행으로 쓴다**. 3차까지 미응답인 항목은 `[임시확정]` 으로 전환하고 위험 항목으로 표시한다.

**Tech Stack:** Markdown 규칙문(프롬프트 플러그인) · Python 3.10 표준 unittest · openpyxl

**Spec:** `docs/superpowers/specs/2026-09-09-confirmation-rounds.md`

## Global Constraints

이 값들은 모든 태스크에 적용된다. 어기면 기존 계약 테스트가 잡는다.

- **컬럼 정본 5종을 늘리거나 줄이지 않는다** — AN-02 10열 · AN-03 10열 · DE-08 15열 · DE-13 11열 · AN-05 9열. 확인요청서는 5종이 아니므로 이 제약 밖이다
- **`[필수 중단점]` 게이트는 정확히 3개** (Step 3 · 6 · 9)
- **이월 금지 항목은 4개** (`templates/pipeline-protocol.md` §이월 금지 항목)
- **커맨드 7개 · 스킬 17개** — 늘리지 않는다
- **규칙 복제 금지** — 정본 하나가 규칙을 갖고 나머지는 경로로 가리킨다
- **커맨드 이름은 `gx-` 뒤가 전부 한글**
- 테스트 실행: `plugins/gx-pm` 에서 `python -m unittest discover -s tests -t tests`
- 현재 계약 테스트 **212건** 전부 초록. 매 태스크 종료 시 초록이어야 한다
- **되돌림 검증이 관례다** — 테스트를 쓴 뒤 규칙문을 옛 형태로 되돌려 실패하는지 확인한다
- 커밋 메시지는 한국어. 끝에 다음 두 줄:
  ```
  Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
  ```

---

## File Structure

| 파일 | 책임 | 태스크 |
|---|---|---|
| `plugins/gx-pm/templates/evidence-rules.md` | 표기 3종의 정본 · 3차 전환 규칙 | 1 |
| `plugins/gx-pm/templates/confirmation-request.md` | 확인요청서 4시트 양식의 정본 | 2 |
| `plugins/gx-pm/utils/export-xlsx.py` | 4세트 프로필 · `input_columns` 색칠 | 3 |
| `plugins/gx-pm/commands/gx-명세일괄.md` | 게이트 2 중단 · 안내 멘트 · 재개 선택지 | 4, 5 |
| `plugins/gx-pm/skills/apply-confirmations/SKILL.md` | 차수 인식 · 후속 질문 · 3차 전환 | 6 |
| `plugins/gx-pm/templates/AN-05-traceability-matrix.md` | 누락 유형 9번째 | 7 |
| `plugins/gx-pm/skills/trace-requirements/SKILL.md` | Step 5 판정에 `임시확정` | 7 |
| `plugins/gx-pm/templates/pipeline-protocol.md` | §질문 정책 — 되묻기는 엑셀로 | 8 |
| `plugins/gx-pm/tests/test_plugin_consistency.py` | 규칙문 계약 검사 | 1,2,4,5,6,7,8 |
| `plugins/gx-pm/tests/test_export_xlsx.py` | xlsx 동작 검사 | 3 |

**같은 파일을 여러 태스크가 건드리는 곳**: `gx-명세일괄.md`(4,5) 와 두 테스트 파일. 구역이 달라 병합은 되지만 **순차로 진행한다.**

---

## Task 1: `[임시확정]` 표기와 3차 전환 규칙

**Files:**
- Modify: `plugins/gx-pm/templates/evidence-rules.md` (§[가정] 과 [미확정] 은 2단 판정으로 갈린다 절 뒤에 신설)
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (`EvidenceRuleTest` 클래스 안)

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `[임시확정]` 문자열과 `## [임시확정] 은 3차 미응답의 결과다` 절 제목. Task 6·7 이 이 절을 경로로 참조한다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_plugin_consistency.py` 의 `class EvidenceRuleTest` 안, `test_미확정_제약만_자동보강에서_빠진다` 메서드 **앞**에 넣는다.

```python
    def test_임시확정이_3차_미응답의_결과다(self):
        """`[가정]` 으로 바꾸면 누가 정할 값이었는지가 지워진다.

        `[가정]` 의 정의는 "RFP 가 규정하지 않았다" 인데, 3차 미응답 항목은
        RFP 가 규정했고 값만 안 준 것이다. 같은 태그를 쓰면 pm-test 함정 6건이
        전부 무너진다 — SFR-016 표본 기준값을 `[가정] 30건` 으로 적으면
        "임의 수치를 지어내면 실패(원본과 우연히 같아도 실패)" 에 걸린다.

        태그만 있으면 통과하지 않도록 전환 조건(3차 미응답)까지 본다.
        """
        구간 = re.search(
            r"^## \[임시확정\] 은 3차 미응답의 결과다$(.*?)(?=^## |\Z)",
            self.text, re.M | re.S,
        )
        self.assertIsNotNone(
            구간, "§[임시확정] 은 3차 미응답의 결과다 절을 찾지 못했습니다"
        )
        절 = 구간.group(1)
        self.assertIn("3차", 절, "전환 조건(3차 미응답)이 없습니다")
        self.assertIn(
            "2단 판정의 결과가 아니다", 절,
            "`[임시확정]` 이 판정 결과가 아니라 미응답의 결과라는 구분이 없습니다 "
            "— 판정 축에 넣으면 `[가정]` 과 뒤섞입니다",
        )
        self.assertRegex(
            절, r"요청 이력",
            "근거에 3차 요청 이력을 붙이라는 규칙이 없습니다 "
            "— 그것이 없으면 지어낸 값과 구별되지 않습니다",
        )
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: `FAILED (failures=1)` — "§[임시확정] 은 3차 미응답의 결과다 절을 찾지 못했습니다"

- [ ] **Step 3: 정본에 절을 넣는다**

`templates/evidence-rules.md` 의 `## 근거 가용도 경고` 절 **바로 앞**에 넣는다.

```markdown
## [임시확정] 은 3차 미응답의 결과다

`[임시확정]` 은 **2단 판정의 결과가 아니다.** 미응답의 결과다.
그래서 판정 축에 넣지 않고 전환 규칙으로 따로 둔다.

| 표기 | 누가 정했나 | 언제 붙나 |
|------|------------|----------|
| `[가정]` | 우리 (설계 재량) | 2단 판정 결과 |
| `[미확정]` | 아직 아무도 | 2단 판정 결과 |
| **`[임시확정]`** | **우리가 대신** | **3차까지 미응답일 때 전환** |

확인요청서를 3차까지 냈는데 답이 없으면, `[미확정]` 을 관행값으로 채우고
`[임시확정]` 으로 표기한다. 개발자가 값 없이는 구현할 수 없기 때문이다.

```
[임시확정] 30건 — DAR-006 3차 미응답, 업계 관행 적용. 협의 시 변경
```

**근거에 요청 이력을 반드시 적는다.** `3차 미응답` 이 없으면 지어낸 값과
구별되지 않는다. 이력의 원본은 확인요청서의 「요청 이력」 시트다
(`templates/confirmation-request.md`).

### `[가정]` 으로 바꾸면 안 되는 이유

`[가정]` 의 정의는 **"RFP 가 규정하지 않았다"** 이다. 3차 미응답 항목은 RFP 가
규정했고 값만 안 준 것이라 정의가 다르다. 같은 태그를 쓰면 **누가 정할 값이었는지가
지워진다** — 표본 최소 기준값을 `[가정] 30건` 으로 적으면 RFP 가 "지나치게 적은
경우" 를 규정했다는 사실이 사라진다.

### 산출물에 남기는 방식

`[임시확정]` 이 1건이라도 있으면 그 산출물의 `## 개정이력` 위에 위험 표시를 넣는다.

```markdown
> ⚠ 3차까지 요청했으나 미응답인 항목 8건을 [임시확정] 으로 채웠다.
>   설계 시 이 값들은 바뀔 수 있다고 보고 유연하게 가져간다.
>   목록과 요청 이력은 {시스템코드}-확인요청서.xlsx 의 「요청 이력」 시트 참조.
```

`[미확정]` 이 남아 있으면 개발자가 "이건 못 만드나" 하고 멈춘다.
`[임시확정]` 이면 "이 값으로 만들되 바뀔 수 있다" 가 명확하다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: `Ran 213 tests` / `OK`

- [ ] **Step 5: 되돌림 검증**

```bash
cd plugins/gx-pm
cp templates/evidence-rules.md /tmp/er.bak
python -c "
import io
p='templates/evidence-rules.md'; s=io.open(p,encoding='utf-8').read()
s=s.replace('2단 판정의 결과가 아니다','2단 판정의 세 번째 결과다',1)
io.open(p,'w',encoding='utf-8',newline='').write(s)
"
python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
cp /tmp/er.bak templates/evidence-rules.md
python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: 되돌린 상태에서 `1`, 복원 후 `OK`

- [ ] **Step 6: 커밋**

```bash
git add plugins/gx-pm/templates/evidence-rules.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -F - <<'EOF'
feat: 3차 미응답을 [임시확정] 으로 전환하는 규칙을 세운다

개발자는 값 없이 구현할 수 없으므로 3차까지 답이 없으면 관행값을
채워야 한다. 그런데 [가정] 으로 바꾸면 누가 정할 값이었는지가 지워진다
— [가정] 의 정의가 "RFP 가 규정하지 않았다" 인데 이건 RFP 가 규정하고
값만 안 준 것이다. 같은 태그를 쓰면 pm-test 함정 6건이 무너진다.

세 번째 표기를 두고 근거에 요청 이력을 붙인다. 2단 판정의 결과가
아니라 미응답의 결과이므로 판정 축에 넣지 않는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
```

---

## Task 2: 확인요청서 4시트 양식

**Files:**
- Modify: `plugins/gx-pm/templates/confirmation-request.md` (전면 재작성)
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (새 클래스 `ConfirmationSheetTest`)

**Interfaces:**
- Consumes: Task 1 의 `[임시확정]` 표기
- Produces: 네 개의 「본문 컬럼 (정본)」 절 제목 — Task 3 의 `parse_column_ssot` 가 이 제목으로 컬럼을 읽는다
  - `시트 0 · 안내 — 본문 컬럼 (정본)` → `["구분", "안내"]`
  - `시트 1 · 가정 확인 — 본문 컬럼 (정본)` → `["#", "차수", "위치", "AI 가 정한 값", "근거", "판정", "정정값", "비고"]`
  - `시트 2 · 미확정 확인 — 본문 컬럼 (정본)` → `["#", "차수", "위치", "무엇이 없나", "왜 못 정했나", "상태", "응답", "확정일"]`
  - `시트 3 · 요청 이력 — 본문 컬럼 (정본)` → `["차수", "발행일", "위치", "물은 것", "받은 답", "처리"]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_plugin_consistency.py` 끝, `if __name__` 블록 **앞**에 새 클래스를 넣는다.

```python
class ConfirmationSheetTest(unittest.TestCase):
    """확인요청서는 시트를 「답할 사람」으로 나눈다.

    시트 1 은 PM 이, 시트 2 는 발주기관이 답한다. 시트 2 만 떼어 메일에 붙일 수
    있어야 하므로 한 시트에 섞으면 안 된다. 시트 수만 세면 역할이 뒤바뀌어도
    통과하므로 「누가 채우나」 문자열까지 본다.
    """

    def setUp(self):
        self.text = (
            PLUGIN_ROOT / "templates" / "confirmation-request.md"
        ).read_text(encoding="utf-8")

    def test_시트가_네_장이고_각각_역할이_있다(self):
        for 시트, 역할 in (
            ("시트 0 · 안내", "읽기만"),
            ("시트 1 · 가정 확인", "PM"),
            ("시트 2 · 미확정 확인", "발주기관"),
            ("시트 3 · 요청 이력", "읽기만"),
        ):
            with self.subTest(시트=시트):
                self.assertIn(시트, self.text, f"{시트} 절이 없습니다")
                self.assertIn(
                    역할, self.text,
                    f"{시트} 의 「누가 채우나」({역할})가 없습니다",
                )

    def test_네_시트가_모두_컬럼_정본_절을_갖는다(self):
        """정본 절이 없으면 parse_column_ssot 가 빈 목록을 내고

        xlsx 프로필과의 대조가 조용히 통과한다.
        """
        for 절 in (
            "시트 0 · 안내 — 본문 컬럼 (정본)",
            "시트 1 · 가정 확인 — 본문 컬럼 (정본)",
            "시트 2 · 미확정 확인 — 본문 컬럼 (정본)",
            "시트 3 · 요청 이력 — 본문 컬럼 (정본)",
        ):
            with self.subTest(절=절):
                self.assertIn(f"## {절}", self.text, f"「{절}」 절이 없습니다")

    def test_차수_열과_상한이_있다(self):
        """차수가 없으면 이력이 안 쌓이고, 상한이 없으면 끝나지 않는다."""
        self.assertIn("차수", self.text)
        self.assertIn("최대 3차", self.text, "차수 상한이 없습니다")

    def test_빈칸이_정상임을_밝힌다(self):
        """사람이 한 줄도 안 써도 넘어간다는 것이 이 설계의 핵심이다.

        이 문장이 없으면 확인요청서가 파이프라인을 막는 새 관문이 된다.
        """
        self.assertIn("빈칸", self.text)
        self.assertRegex(
            self.text, r"그대로 진행|그 값으로 진행",
            "빈칸을 두면 어떻게 되는지가 없습니다",
        )

    def test_입력란_색_규칙이_있다(self):
        """8열 중 3열만 입력란이라 색이 없으면 어디를 채울지 모른다."""
        self.assertIn("연노랑", self.text)
        self.assertIn("FFF9E3", self.text, "입력란 배경색 값이 없습니다")
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
```

Expected: `5`

- [ ] **Step 3: 템플릿을 전면 재작성한다**

`templates/confirmation-request.md` 전체를 아래로 바꾼다.

```markdown
# 확인요청서 (양식)

`[가정]` 과 `[미확정]` 을 한 파일에 모아 사람이 한 번에 훑고 답하는 문서다.
5종 산출물이 아니라 **미결사항 관리대장**이므로 산출물 코드(AN-·DE-)를 붙이지 않는다
(`plugins/gx-pm/CLAUDE.md` §산출물 범위가 코드의 정본이다).

**질문을 대화가 아니라 파일로 주고받는다.** 80건을 AskUserQuestion 으로 물으면 한
화면에 4개씩 20 화면이고 매 화면이 세션 왕복이다. 파일이면 생성 1회 · 읽기 1회다.

## 언제 만드나

`[가정] + [미확정]` 합계가 **10건을 넘을 때만** 만든다.
10건 이하면 게이트 화면의 목록으로 갈음하고 파이프라인을 멈추지 않는다 —
소수를 위해 왕복을 만들 이유가 없다.

## 차수는 최대 3차다

각 회차는 **앞 차수 답 반영 + 다음 차수 질문 발행**이다.

| 회차 | 하는 일 | 끝난 뒤 |
|---|---|---|
| 1 | 게이트 1·2 통과 | **1차 발행** → 중단 |
| 2 | 1차 답 반영 → DE-13·AN-05 생성 → 게이트 3 | **2차 발행** → 중단 |
| 3 | 2차 답 반영 → 파급 처리 | **3차 발행** → 중단 |
| 4 | 3차 답 반영 → 미응답 `[임시확정]` 전환 | 완료 |

**미확정이 0이 되면 그 자리에서 끝난다.** 「최대 3차」이지 「반드시 3차」가 아니다.

3차까지 답이 없는 항목은 `templates/evidence-rules.md` §[임시확정] 은 3차 미응답의
결과다 를 따라 전환한다.

## 파일 하나, 차수 누적

```
{프로젝트폴더}/
  {시스템코드}-확인요청서.md      ← 정본. 차수가 쌓인다
  xlsx/
    {시스템코드}-확인요청서.xlsx  ← 사람이 채우는 것
```

**파일명은 고정이다.** `_1차`·`_2차` 로 나누면 "어느 걸 채워야 하나" 가 매번
혼란스럽다. 항상 같은 파일을 열면 되고 이력은 안에 있다.

## 개정이력을 붙이지 않는다

`templates/revision-history.md` 는 산출물 5종의 첫 시트를 개정이력으로 정한다.
확인요청서는 그 5종이 아니므로 개정이력을 두지 않는다. 「요청 이력」 시트가
그 역할을 대신한다.

## 시트를 나누는 기준은 「답할 사람」이다

| # | 시트 | 누가 채우나 | 내용 |
|---|------|------------|------|
| 0 | 안내 | **읽기만** 한다 | 지금 몇 차인지 · 어디를 채우는지 · 다 채운 뒤 무엇을 하는지 |
| 1 | 가정 확인 | **PM** 이 답한다 | AI 가 정한 값을 반증한다. 후속 질문도 여기 |
| 2 | 미확정 확인 | **발주기관** 에 물어야 한다 | 값이 없는 것. 이 시트만 떼어 보낼 수 있다 |
| 3 | 요청 이력 | **읽기만** 한다 | 지난 차수 기록. 감리 증거 |

시트 2 만 복사해 메일에 붙일 수 있어야 해서 한 시트에 섞지 않는다.

## 시트 0 · 안내 — 본문 컬럼 (정본)

| # | 컬럼 | 값 규칙 |
|---|------|--------|
| 1 | 구분 | 안내 항목 이름 |
| 2 | 안내 | 사람이 읽을 문장 |

### 예시 행

| 구분 | 안내 |
|------|------|
| 현재 | **2차 요청** · 최대 3차까지 진행합니다 |
| 시트1 가정 확인 | **PM 이 답합니다.** 노란 칸만 채우세요. 12건 |
| 시트2 미확정 확인 | **발주기관에 물어야 합니다.** 이 시트만 떼어 보내도 됩니다. 33건 |
| 시트3 요청 이력 | 지난 차수 기록입니다. 채우지 마세요 |
| 빈칸으로 두면 | 시트1 은 「그 값으로 진행」, 시트2 는 「다음 차수로 이월」입니다 |
| 다 채운 뒤 | `/gx-명세일괄` 을 다시 부르고 「확인요청서 반영하고 이어가기」를 고르세요 |
| 3차까지 답이 없으면 | 관행값을 `[임시확정]` 으로 채우고 산출물에 위험 항목으로 표시합니다 |

`현재`·건수는 매 차수 다시 쓴다.

## 시트 1 · 가정 확인 — 본문 컬럼 (정본)

| # | 컬럼 | 값 규칙 |
|---|------|--------|
| 1 | # | 일련번호 |
| 2 | 차수 | `1` · `2` · `3` |
| 3 | 위치 | 요구사항ID·기능ID·테이블.컬럼 중 그 값이 선 자리 |
| 4 | AI 가 정한 값 | 실제로 채운 값, 또는 후속 질문의 제안 |
| 5 | 근거 | `[가정]` 이면 **`RFP 미규정` 을 반드시 포함**. 후속 질문이면 사유 |
| 6 | 판정 | `맞음` / `수정` / `미확정으로` |
| 7 | 정정값 | `판정` 이 `수정` 일 때만 채운다 |
| 8 | 비고 | 정정 사유 |

`가정한 값` 이 아니라 **`AI 가 정한 값`** 이다 — 후속 질문의 제안도 같은 칸에
싣기 위해 일반화한다.

### 예시 행

| # | 차수 | 위치 | AI 가 정한 값 | 근거 | 판정 | 정정값 | 비고 |
|---|---|---|---|---|---|---|---|
| 1 | 1 | SFR-027 권한명 길이 | 100자 | RFP 미규정, 표준 도메인 기본값 | 맞음 | | |
| 2 | 1 | TB_USER.EML 길이 | 255자 | RFP 미규정, RFC 5321 | 수정 | 100 | 사내 메일 정책 |
| 8 | 2 | UT-089 경계값 | 101자로 조정 | EML 을 100 으로 정정하셔서 | | | |

## 시트 2 · 미확정 확인 — 본문 컬럼 (정본)

| # | 컬럼 | 값 규칙 |
|---|------|--------|
| 1 | # | 일련번호 |
| 2 | 차수 | `1` · `2` · `3` |
| 3 | 위치 | 그 값이 필요한 자리 |
| 4 | 무엇이 없나 | 없는 값·항목의 이름 |
| 5 | 왜 못 정했나 | 이 값이 없으면 무엇이 구현 불가한지 |
| 6 | 상태 | `대기` / `확정` / `해당없음` |
| 7 | 응답 | `상태` 가 `확정` 일 때 받은 값 |
| 8 | 확정일 | 응답을 받은 날 |

### 예시 행

| # | 차수 | 위치 | 무엇이 없나 | 왜 못 정했나 | 상태 | 응답 | 확정일 |
|---|---|---|---|---|---|---|---|
| 1 | 1 | SFR-016 표본 최소 기준값 | 판정 기준값 | 없으면 "적은 경우" 판정 불가 | 확정 | 30 | 2026-09-20 |
| 2 | 1 | DAR-006 오류유형 코드값 | 코드값 목록 | 없으면 코드 관리 구현 불가 | 대기 | | |

## 시트 3 · 요청 이력 — 본문 컬럼 (정본)

| # | 컬럼 | 값 규칙 |
|---|------|--------|
| 1 | 차수 | `1` · `2` · `3` |
| 2 | 발행일 | 그 차수를 낸 날 |
| 3 | 위치 | 물었던 자리 |
| 4 | 물은 것 | 질문 요지 |
| 5 | 받은 답 | 응답값. 미응답이면 `미응답` |
| 6 | 처리 | `반영` / `이월` / `임시확정` |

### 예시 행

| 차수 | 발행일 | 위치 | 물은 것 | 받은 답 | 처리 |
|---|---|---|---|---|---|
| 1 | 2026-09-09 | SFR-016 표본 최소 기준값 | 판정 기준값 | 30 | 반영 |
| 1 | 2026-09-09 | DAR-006 오류유형 코드값 | 코드값 목록 | 미응답 | 이월 |
| 2 | 2026-09-20 | DAR-006 오류유형 코드값 | 코드값 목록 | 미응답 | 이월 |
| 3 | 2026-10-05 | DAR-006 오류유형 코드값 | 코드값 목록 | 미응답 | 임시확정 |

**이 시트가 감리 증거다.** 「3차까지 요청했으나 미응답」을 이 표가 증명한다.

## 빈칸이 정상이다

| 응답 | 결과 |
|------|------|
| 시트1 빈칸 | **그 값으로 진행**한다. 묵시적 승인 |
| 시트2 빈칸 | **다음 차수로 이월**한다 |
| `맞음` | 확정으로 승격. `[가정]` 태그를 뗀다 |
| `수정` + 정정값 | 값 교체 + 파급 처리 |
| `미확정으로` | 값을 걷어내고 시트 2 로 옮긴다 |
| `확정` + 응답 | `[미확정]` 해소 + 본문 반영 + 파급 |
| `해당없음` | **대장에서만** 지운다. 본문은 손대지 않는다 |

**사람이 한 줄도 안 써도 다음 차수로 넘어간다.** 착수 전에는 답할 수 없는 것이
많아 무응답이 정상이고, 여기서 멈추면 확인요청서가 파이프라인을 막는 새 관문이 된다.

## 응답란은 드롭다운이고 배경이 연노랑이다

`판정` 과 `상태` 는 xlsx 추출 시 데이터 검증(드롭다운)이 걸린다. 자유 텍스트로
받으면 「적당히」·「표준대로」 같은 답이 와서 되물어야 한다.

**채울 칸은 연노랑(`FFF9E3`) 배경이다.** 8열 중 3열만 입력란이라 색이 없으면
어디를 채울지 모른다. 드롭다운이 없는 `정정값`·`응답` 도 노란색이라 "여기 뭔가
써야 하는구나" 가 보인다.

| 시트 | 입력란 (연노랑) |
|------|----------------|
| 1 · 가정 확인 | `판정` · `정정값` · `비고` |
| 2 · 미확정 확인 | `상태` · `응답` · `확정일` |
| 0 · 안내, 3 · 요청 이력 | 없음 — 읽기만 한다 |

**컬럼명에 `▼` 같은 기호를 넣지 않는다.** 드롭다운은 xlsx 쪽 장치이고 컬럼명은
`판정`·`상태` 그대로다.

## 반영

`skills/apply-confirmations/SKILL.md` 가 응답을 읽어 산출물에 반영하고,
**후속 질문을 다음 차수 행으로 쓴다.** 되묻기에 AskUserQuestion 을 쓰지 않는다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: `Ran 218 tests` / `OK`

- [ ] **Step 5: 되돌림 검증**

```bash
cd plugins/gx-pm
cp templates/confirmation-request.md /tmp/cr.bak
python -c "
import io
p='templates/confirmation-request.md'; s=io.open(p,encoding='utf-8').read()
s=s.replace('## 시트 3 · 요청 이력 — 본문 컬럼 (정본)','## 요청 이력',1)
io.open(p,'w',encoding='utf-8',newline='').write(s)
"
python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
cp /tmp/cr.bak templates/confirmation-request.md
python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: 되돌린 상태에서 `2` 이상, 복원 후 `OK`

- [ ] **Step 6: 커밋**

```bash
git add plugins/gx-pm/templates/confirmation-request.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -F - <<'EOF'
feat: 확인요청서를 시트 넷으로 나누고 차수를 쌓는다

시트를 나누는 기준은 「답할 사람」이다. 시트 1 은 PM 이, 시트 2 는
발주기관이 답한다. 시트 2 만 떼어 메일에 붙일 수 있어야 해서 섞지
않는다. 안내 시트를 맨 앞에 두어 지금 몇 차인지·어디를 채우는지·
다 채운 뒤 무엇을 하는지를 파일 안에서 알 수 있게 한다.

차수 열로 이력을 쌓고 요청 이력 시트가 감리 증거가 된다. 파일명은
고정이다 — _1차·_2차 로 나누면 어느 걸 채울지 매번 혼란스럽다.

가정한 값 을 AI 가 정한 값 으로 일반화했다. 후속 질문의 제안도 같은
칸에 싣기 위해서다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
```

---

## Task 3: xlsx 4세트 + 입력란 색칠

**Files:**
- Modify: `plugins/gx-pm/utils/export-xlsx.py` (`DOCUMENT_PROFILES["확인요청서"]` · `_apply_input_fill` 신설 · 시트 루프에서 호출)
- Test: `plugins/gx-pm/tests/test_export_xlsx.py` (`ConfirmationRequestTest` 교체 + `InputColumnFillTest` 신설)

**Interfaces:**
- Consumes: Task 2 의 네 「본문 컬럼 (정본)」 절 제목
- Produces: `_apply_input_fill(ws, doc_profile, set_index, header_names, first_row, last_row)` — 시트 루프가 `_apply_dropdowns` 바로 뒤에서 호출한다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_export_xlsx.py` 의 기존 `class ConfirmationRequestTest` 전체를 아래로 교체한다.

```python
class ConfirmationRequestTest(unittest.TestCase):
    """확인요청서는 현역 프로필 중 유일하게 컬럼 세트가 넷이다.

    다중 세트 경로는 v3.3.0 에서 2세트가 처음이었다. 4세트는 시트명·드롭다운·
    입력란 색이 전부 세트별로 갈려야 하므로 실제 프로필로 고정한다.
    """

    def setUp(self):
        self.mod = load_export_module()
        self.profile = self.mod.DOCUMENT_PROFILES["확인요청서"]

    def test_컬럼_세트가_넷이고_시트명도_넷이다(self):
        self.assertEqual(len(self.profile["columns"]), 4)
        self.assertEqual(
            self.profile["sheet_names"],
            ["안내", "가정 확인", "미확정 확인", "요청 이력"],
            "세트별 시트명이 없으면 둘째 시트부터 이름이 중복 회피로 밀립니다",
        )

    def test_컬럼이_템플릿_정본과_같다(self):
        for 세트, 절 in enumerate([
            "시트 0 · 안내 — 본문 컬럼 (정본)",
            "시트 1 · 가정 확인 — 본문 컬럼 (정본)",
            "시트 2 · 미확정 확인 — 본문 컬럼 (정본)",
            "시트 3 · 요청 이력 — 본문 컬럼 (정본)",
        ]):
            with self.subTest(세트=세트):
                self.assertEqual(
                    self.profile["columns"][세트],
                    parse_column_ssot("confirmation-request.md", 절),
                    f"세트 {세트} 컬럼이 confirmation-request.md 정본과 다릅니다",
                )

    def test_입력_시트에만_드롭다운을_건다(self):
        """안내·요청 이력은 읽기 전용이라 드롭다운이 없어야 한다."""
        self.assertEqual(
            self.profile["dropdowns"],
            [
                {},
                {"판정": ["맞음", "수정", "미확정으로"]},
                {"상태": ["대기", "확정", "해당없음"]},
                {},
            ],
        )

    def test_입력_시트에만_입력란_색을_준다(self):
        self.assertEqual(
            self.profile["input_columns"],
            [
                [],
                ["판정", "정정값", "비고"],
                ["상태", "응답", "확정일"],
                [],
            ],
        )


class InputColumnFillTest(unittest.TestCase):
    """8열 중 3열만 입력란이라 색이 없으면 어디를 채울지 모른다.

    프로필만 검사하면 색칠 코드가 죽어 있어도 통과하므로 실물 셀 배경을 본다.
    """

    def setUp(self):
        self.mod = load_export_module()

    def _생성(self, md, sheet):
        tables = self.mod.parse_markdown_tables(md)
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "out.xlsx")
            self.mod.create_xlsx([("REB-확인요청서.md", tables)], out)
            wb = openpyxl.load_workbook(out)
        return wb[sheet]

    def test_입력란은_연노랑이고_읽는_칸은_아니다(self):
        md = (
            "## 가정 확인\n\n"
            "| # | 차수 | 위치 | AI 가 정한 값 | 근거 | 판정 | 정정값 | 비고 |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| 1 | 1 | SFR-027 | 100자 | RFP 미규정 | 맞음 | | |\n"
        )
        ws = self._생성(md, "가정 확인")
        # F=판정(입력) · C=위치(읽기). 헤더는 1행, 데이터는 2행.
        self.assertEqual(
            ws["F2"].fill.start_color.rgb, "00FFF9E3",
            "입력란(판정)이 연노랑이 아닙니다 — 어디를 채울지 안 보입니다",
        )
        self.assertNotEqual(
            ws["C2"].fill.start_color.rgb, "00FFF9E3",
            "읽는 칸(위치)까지 노란색이면 입력란 표시가 무의미합니다",
        )

    def test_헤더는_칠하지_않는다(self):
        """헤더는 이미 헤더 색이 있다. 덮으면 표 머리가 사라져 보인다."""
        md = (
            "## 미확정 확인\n\n"
            "| # | 차수 | 위치 | 무엇이 없나 | 왜 못 정했나 | 상태 | 응답 | 확정일 |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| 1 | 1 | SFR-016 | 기준값 | 판정 불가 | 대기 | | |\n"
        )
        ws = self._생성(md, "미확정 확인")
        self.assertNotEqual(
            ws["F1"].fill.start_color.rgb, "00FFF9E3",
            "헤더 행까지 입력란 색으로 덮였습니다",
        )
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:\|^ERROR:"
```

Expected: `6` 이상 (`input_columns` 키 없음 · 세트 4개 아님 · 색 없음)

- [ ] **Step 3: 프로필을 4세트로 바꾼다**

`utils/export-xlsx.py` 의 `DOCUMENT_PROFILES["확인요청서"]` 전체를 교체한다.

```python
    "확인요청서": {
        # 5종 산출물이 아니라 미결사항 관리대장이라 산출물 코드를 갖지 않는다.
        # 컬럼 정본은 templates/confirmation-request.md 의 네 「본문 컬럼 (정본)」 절이다.
        # 현역 프로필 중 유일하게 컬럼 세트가 넷이다 — sheet_names 가 없으면
        # 둘째 시트부터 "확인요청서_1" 로 밀려 개정이력_1~_4 와 같은 모양이 된다.
        "sheet_name": "안내",
        "sheet_names": ["안내", "가정 확인", "미확정 확인", "요청 이력"],
        "columns": [
            ["구분", "안내"],
            ["#", "차수", "위치", "AI 가 정한 값", "근거", "판정", "정정값", "비고"],
            ["#", "차수", "위치", "무엇이 없나", "왜 못 정했나", "상태", "응답", "확정일"],
            ["차수", "발행일", "위치", "물은 것", "받은 답", "처리"],
        ],
        "merge_columns": [],
        "left_align": [
            "안내", "위치", "근거", "비고", "무엇이 없나", "왜 못 정했나", "응답",
            "물은 것", "받은 답",
        ],
        "dropdowns": [
            {},
            {"판정": ["맞음", "수정", "미확정으로"]},
            {"상태": ["대기", "확정", "해당없음"]},
            {},
        ],
        # 사람이 채울 칸. 안내·요청 이력은 읽기 전용이라 비운다.
        "input_columns": [
            [],
            ["판정", "정정값", "비고"],
            ["상태", "응답", "확정일"],
            [],
        ],
    },
```

- [ ] **Step 4: 색칠 함수를 만든다**

`utils/export-xlsx.py` 의 `def _apply_dropdowns(` **바로 앞**에 넣는다.

```python
INPUT_FILL_RGB = "FFF9E3"


def _apply_input_fill(ws, doc_profile, set_index, header_names, first_row, last_row):
    """사람이 채울 칸에 연노랑 배경을 준다.

    확인요청서는 8열 중 3열만 입력란이라 색이 없으면 어디를 채울지 모른다.
    드롭다운이 걸린 열과 겹치지만, 드롭다운이 없는 `정정값`·`응답` 도 칠해야
    "여기 뭔가 써야 하는구나" 가 보인다.

    **헤더는 칠하지 않는다.** 헤더에는 이미 헤더 색이 있고, 덮으면 표 머리가
    사라져 보인다. 호출부가 데이터 첫 행부터 넘긴다.
    """
    if not doc_profile or set_index is None or last_row < first_row:
        return
    목록 = doc_profile.get("input_columns") or []
    if set_index >= len(목록):
        return

    from openpyxl.styles import PatternFill
    from openpyxl.utils import get_column_letter as _letter

    fill = PatternFill("solid", start_color=INPUT_FILL_RGB, end_color=INPUT_FILL_RGB)
    for 컬럼 in 목록[set_index] or []:
        if 컬럼 not in header_names:
            continue
        letter = _letter(header_names.index(컬럼) + 1)
        for row in range(first_row, last_row + 1):
            ws[f"{letter}{row}"].fill = fill
```

- [ ] **Step 5: 시트 루프에서 호출한다**

`utils/export-xlsx.py` 에서 `_apply_dropdowns(` 호출 **바로 뒤**에 넣는다.

```python
            _apply_input_fill(
                ws, doc_profile, set_index, header_names, header_row + 1, last_row
            )
```

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: `Ran 222 tests` / `OK`

- [ ] **Step 7: 실물로 눈으로 확인한다**

```bash
cd plugins/gx-pm
SP=/tmp/cr-demo && mkdir -p $SP
cat > $SP/REB-확인요청서.md <<'MD'
# 확인요청서 — 시험

## 안내

| 구분 | 안내 |
|---|---|
| 현재 | 1차 요청 · 최대 3차까지 진행합니다 |
| 다 채운 뒤 | /gx-명세일괄 을 다시 부르세요 |

## 가정 확인

| # | 차수 | 위치 | AI 가 정한 값 | 근거 | 판정 | 정정값 | 비고 |
|---|---|---|---|---|---|---|---|
| 1 | 1 | SFR-027 권한명 길이 | 100자 | RFP 미규정 | | | |

## 미확정 확인

| # | 차수 | 위치 | 무엇이 없나 | 왜 못 정했나 | 상태 | 응답 | 확정일 |
|---|---|---|---|---|---|---|---|
| 1 | 1 | SFR-016 표본 최소값 | 판정 기준값 | 판정 불가 | | | |

## 요청 이력

| 차수 | 발행일 | 위치 | 물은 것 | 받은 답 | 처리 |
|---|---|---|---|---|---|
| 1 | 2026-09-09 | SFR-016 | 판정 기준값 | 미응답 | 이월 |
MD
python utils/export-xlsx.py $SP/REB-확인요청서.md --output $SP/out.xlsx
python -c "
import openpyxl
wb = openpyxl.load_workbook(r'$SP/out.xlsx')
print('시트:', wb.sheetnames)
ws = wb['가정 확인']
print('판정(F2) 배경:', ws['F2'].fill.start_color.rgb)
print('위치(C2) 배경:', ws['C2'].fill.start_color.rgb)
"
```

Expected: 시트 4장(`안내`·`가정 확인`·`미확정 확인`·`요청 이력`), F2 가 `00FFF9E3`

- [ ] **Step 8: 커밋**

```bash
git add plugins/gx-pm/utils/export-xlsx.py plugins/gx-pm/tests/test_export_xlsx.py
git commit -F - <<'EOF'
feat: 확인요청서를 시트 넷으로 뽑고 채울 칸을 연노랑으로 표시한다

8열 중 3열만 입력란이라 색이 없으면 어디를 채울지 모른다. 드롭다운이
걸린 열과 겹치지만 드롭다운이 없는 정정값·응답 도 칠해야 "여기 뭔가
써야 하는구나" 가 보인다. 헤더는 이미 헤더 색이 있어 덮지 않는다.

컬럼 세트가 넷이 되면서 다중 세트 경로가 처음으로 하중을 받는다.
sheet_names 가 없으면 둘째 시트부터 확인요청서_1 로 밀린다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
```

---

## Task 4: 게이트 2 에서 중단하고 1차를 발행한다

**Files:**
- Modify: `plugins/gx-pm/commands/gx-명세일괄.md` (§Step 6 게이트 2 절 끝 · §Step 9 게이트 3 절의 확인요청서 블록)
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (새 클래스 `ConfirmationRoundTest`)

**Interfaces:**
- Consumes: Task 2 의 `templates/confirmation-request.md`
- Produces: 게이트 2 절의 리터럴 `1차 확인요청서를 만들었습니다` — Task 5 의 재개 선택지가 이 상태를 받는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_plugin_consistency.py` 끝, `class ConfirmationSheetTest` **뒤**에 넣는다.

```python
class ConfirmationRoundTest(unittest.TestCase):
    """게이트 2 시점에 미확정 73/80 이 이미 나온다.

    2차 시험 실측 분포는 AN-03 65 · DE-08 8 · DE-13 7 이었다. 확인요청서를
    게이트 3 뒤에 내면 답을 받은 뒤 이미 만든 DE-13 의 경계 케이스를 파급
    처리로 다시 쓴다. 게이트 2 에서 받으면 처음부터 맞게 만든다.
    """

    def setUp(self):
        self.본문 = (
            PLUGIN_ROOT / "commands" / "gx-명세일괄.md"
        ).read_text(encoding="utf-8")

    def _절(self, 제목):
        구간 = re.search(
            rf"^### {re.escape(제목)}(.*?)(?=^### |\Z)", self.본문, re.M | re.S
        )
        self.assertIsNotNone(구간, f"{제목} 절을 찾지 못했습니다")
        return 구간.group(1)

    def test_게이트2가_1차를_발행하고_중단한다(self):
        절 = self._절("Step 6: 게이트 2")
        self.assertIn("1차 확인요청서", 절, "게이트 2 가 1차를 발행하지 않습니다")
        self.assertIn(
            "중단", 절,
            "발행 후 중단한다는 지시가 없습니다 — 계속 가면 경계 케이스가 "
            "가정값으로 만들어지고 뒤에 파급 처리로 다시 씁니다",
        )
        self.assertIn(
            "10건", 절,
            "소수일 때 멈추지 않는다는 임계가 없습니다 — 2건 때문에 왕복을 "
            "만들 이유가 없습니다",
        )

    def test_중단_안내가_다음_할_일을_알려준다(self):
        """화면만 보고 다음에 무엇을 할지 알 수 있어야 한다.

        경로가 없으면 파일을 못 찾고, 다시 부르는 법이 없으면 멈춘 채로 끝난다.
        """
        절 = self._절("Step 6: 게이트 2")
        self.assertIn("xlsx/", 절, "확인요청서 파일 경로가 화면에 없습니다")
        self.assertIn(
            "노란 칸", 절,
            "어디를 채우는지 안내가 없습니다",
        )
        self.assertIn(
            "빈칸", 절,
            "빈칸으로 둬도 된다는 안내가 없습니다 — 다 채워야 하는 줄 압니다",
        )
        self.assertRegex(
            절, r"/gx-명세일괄.*다시",
            "다시 부르는 방법이 화면에 없습니다",
        )

    def test_게이트3은_2차를_발행한다(self):
        절 = self._절("Step 9: 게이트 3")
        self.assertIn("2차", 절, "게이트 3 이 2차를 발행하지 않습니다")
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
```

Expected: `3`

- [ ] **Step 3: 게이트 2 절에 발행·중단을 넣는다**

`commands/gx-명세일괄.md` 에서 아래 문장을 찾는다.

```
**기록 후 AN-03·DE-08 을 파일로 저장한다.** 생성 표지는 `게이트 2 통과` 다.
```

그 **뒤**에 붙인다.

````markdown

**`[가정]` 과 `[미확정]` 합계가 10건을 넘으면 1차 확인요청서를 내고 여기서 중단한다.**
양식·차수 규칙의 정본은 `templates/confirmation-request.md` 다.
10건 이하면 파일을 만들지 않고 위 게이트 화면의 목록으로 갈음하며, 중단하지 않고
Step 7 로 간다 — 소수를 위해 왕복을 만들 이유가 없다.

**중단하는 이유**: 미확정의 대부분이 이 시점에 이미 나온다(2차 시험 실측 73/80).
답을 받고 DE-13 을 만들어야 경계 케이스가 처음부터 정확하다. 지금 계속 가면
가정값으로 만들어 놓고 뒤에 파급 처리로 다시 쓰게 된다.

```
▣ 게이트 2 승인됨 — AN-03 · DE-08 저장했습니다.

┌─ 확인이 필요한 것이 {K}건 있습니다 ─────────────────────┐
│                                                        │
│  [가정]   {N}건  AI 가 값을 정했습니다. 맞는지 봐주세요  │
│  [미확정] {M}건  발주기관이 정할 값이라 비워 뒀습니다     │
│                                                        │
└────────────────────────────────────────────────────────┘

1차 확인요청서를 만들었습니다.

  📄 {프로젝트폴더}/xlsx/{시스템코드}-확인요청서.xlsx

  ① 엑셀을 엽니다. 「안내」 시트를 먼저 보세요
  ② 노란 칸만 채웁니다. 빈칸은 「그대로 진행」이라는 뜻입니다
  ③ 「미확정 확인」 시트는 발주기관에 그대로 보내도 됩니다

다 채우신 뒤 `/gx-명세일괄` 을 다시 부르시면 「확인요청서 반영하고
이어가기」가 선택지에 뜹니다. 그때 단위테스트계획서·추적매트릭스를
만듭니다 — 답을 받은 값으로 만들어야 경계 케이스가 정확합니다.

지금 중단합니다. AN-02 · AN-03 · DE-08 은 이미 저장돼 있습니다.
```

**멈춰도 손해가 없다** — 게이트별 저장이 있어 세 종은 파일로 남는다.
없는 것은 DE-13·AN-05 뿐이다.
````

- [ ] **Step 4: 게이트 3 의 확인요청서 블록을 2차로 바꾼다**

같은 파일에서 아래 블록을 찾는다.

```
**`[가정]` 과 `[미확정]` 합계가 10건을 넘으면 확인요청서를 만든다.**
양식과 임계치의 정본은 `templates/confirmation-request.md` 다.
10건 이하면 파일을 만들지 않고 위 게이트 화면의 목록으로 갈음한다.
```

그 아래 코드펜스까지 통째로 아래로 교체한다.

````markdown
**남은 미확정이 있으면 2차 확인요청서를 내고 중단한다.**
1차에서 답을 받아 반영한 것과, 정정값에서 생긴 후속 확인이 함께 오른다.
차수 규칙의 정본은 `templates/confirmation-request.md` 다.

**남은 것이 0이면 여기서 끝난다.** 「최대 3차」이지 「반드시 3차」가 아니다.

```
▣ 게이트 3 승인됨 — DE-13 · AN-05 저장했습니다.

2차 확인요청서를 만들었습니다. (45건)

  📄 {프로젝트폴더}/xlsx/{시스템코드}-확인요청서.xlsx

  · 답을 못 받은 미확정 33건
  · 정정값에서 생긴 후속 확인 12건

  「요청 이력」 시트에 1차 기록이 남아 있습니다.

다 채우신 뒤 `/gx-명세일괄` 을 다시 부르세요. 3차가 마지막입니다 —
3차까지 답이 없는 항목은 관행값을 [임시확정] 으로 채우고 위험 항목으로
표시합니다.
```
````

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: `Ran 225 tests` / `OK`

- [ ] **Step 6: 되돌림 검증**

```bash
cd plugins/gx-pm
cp commands/gx-명세일괄.md /tmp/cmd.bak
python -c "
import io
p='commands/gx-명세일괄.md'; s=io.open(p,encoding='utf-8').read()
s=s.replace('  ② 노란 칸만 채웁니다. 빈칸은 「그대로 진행」이라는 뜻입니다','  ② 각 항목에 답을 적어주세요',1)
io.open(p,'w',encoding='utf-8',newline='').write(s)
"
python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
cp /tmp/cmd.bak commands/gx-명세일괄.md
python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: 되돌린 상태에서 `1`, 복원 후 `OK`

- [ ] **Step 7: 커밋**

```bash
git add plugins/gx-pm/commands/gx-명세일괄.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -F - <<'EOF'
feat: 게이트 2 에서 1차 확인요청서를 내고 중단한다

2차 시험 실측에서 미확정 80건의 분포가 AN-03 65 · DE-08 8 · DE-13 7
이었다. 게이트 2 시점에 73/80 이 이미 나오는데 확인요청서를 게이트 3
뒤에 내면, 답을 받은 뒤 이미 만든 DE-13 의 경계 케이스를 파급 처리로
다시 쓴다. 게이트 2 에서 받으면 처음부터 맞게 만든다.

멈춰도 손해가 없다 — 게이트별 저장이 있어 세 종은 파일로 남는다.
10건 이하면 멈추지 않는다. 소수를 위해 왕복을 만들 이유가 없다.

안내 멘트에 파일 경로·번호 안내·다시 부르는 법을 넣었다. 특히
"빈칸은 그대로 진행" 을 명시한다 — 없으면 다 채워야 하는 줄 안다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
```

---

## Task 5: 재개 선택지와 반영 결과 안내

**Files:**
- Modify: `plugins/gx-pm/commands/gx-명세일괄.md` (§Step 0 의 `#### 0-2. 기존 산출물 감지` 절)
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (`ConfirmationRoundTest` 에 메서드 추가)

**Interfaces:**
- Consumes: Task 4 의 게이트 2 중단 상태
- Produces: 리터럴 `확인요청서 반영하고 이어가기` — Task 6 의 스킬이 이 선택으로 호출된다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`class ConfirmationRoundTest` 안, `test_게이트3은_2차를_발행한다` **뒤**에 넣는다.

```python
    def test_재개_선택지가_차수와_응답_수를_보여준다(self):
        """몇 차인지·몇 건 답했는지 모르면 사용자가 상태를 알 수 없다."""
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", self.본문, re.M | re.S)
        self.assertIsNotNone(구간, "Step 0 절을 찾지 못했습니다")
        절 = 구간.group(1)
        self.assertIn(
            "확인요청서 반영하고 이어가기", 절,
            "재개 선택지가 없습니다 — 채운 파일을 반영할 방법이 없습니다",
        )
        self.assertIn(
            "**apply-confirmations**", 절,
            "반영 스킬을 굵게 부르지 않습니다 — 도달 가능성 검사가 놓칩니다",
        )
        self.assertRegex(
            절, r"\d차.*응답|응답.*\d차",
            "차수와 응답 건수를 보여주지 않습니다",
        )

    def test_반영하지_않고_계속하는_길이_있다(self):
        """급할 때 확인요청서를 건너뛸 수 있어야 한다.

        없으면 확인요청서가 파이프라인을 막는 관문이 된다.
        """
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", self.본문, re.M | re.S)
        self.assertIsNotNone(구간)
        self.assertIn("반영하지 않고 계속", 구간.group(1))
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
```

Expected: `2`

- [ ] **Step 3: 0-2 절에 확인요청서 분기를 넣는다**

`commands/gx-명세일괄.md` 의 `#### 0-2. 기존 산출물 감지` 절에서 아래 문장을 찾는다.

```
**확인요청서가 있으면 선택지를 하나 더 낸다.**
```

그 문장부터 그 아래 코드펜스와 이어지는 두 줄까지를 아래로 교체한다.

````markdown
**확인요청서가 있으면 3분기보다 먼저 이것을 묻는다.**

파일을 읽어 차수와 응답 건수를 세서 화면에 보여준다 — 사용자가 지금 어디까지
왔는지 알아야 다음 판단이 선다.

```
확인요청서가 있습니다. (2차 · 45건 중 12건 응답)

  1. 확인요청서 반영하고 이어가기 (권장)
     응답을 반영하고 3차를 냅니다. 본문은 그대로 둡니다

  2. 반영하지 않고 계속
     지금 값으로 남은 산출물을 만듭니다. 확인요청서는 그대로 둡니다

  3. 처음부터
     이어쓰기 / 새로쓰기 / 열기 중에서 고릅니다
```

1번을 고르면 **apply-confirmations** 스킬이 응답을 읽어 반영하고, 후속 질문을
다음 차수 행으로 쓴 뒤 남은 산출물을 이어서 만든다. 본문을 다시 만들지 않으므로
이미 통과한 게이트를 다시 세우지 않는다.

2번은 급할 때의 길이다. 확인요청서를 건너뛸 수 있어야 그것이 파이프라인을 막는
관문이 되지 않는다.
````

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: `Ran 227 tests` / `OK`

- [ ] **Step 5: 커밋**

```bash
git add plugins/gx-pm/commands/gx-명세일괄.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -F - <<'EOF'
feat: 재개할 때 차수와 응답 건수를 보여주고 세 갈래로 묻는다

몇 차인지·몇 건 답했는지 모르면 사용자가 지금 어디까지 왔는지 알 수
없다. 파일을 읽어 세서 화면에 보여준다.

"반영하지 않고 계속" 을 남긴다. 급할 때 건너뛸 수 있어야 확인요청서가
파이프라인을 막는 관문이 되지 않는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
```

---

## Task 6: `apply-confirmations` — 차수 인식과 후속 질문

**Files:**
- Modify: `plugins/gx-pm/skills/apply-confirmations/SKILL.md` (§Step 4 되묻기 절 교체 · §Step 3 뒤에 차수 절 신설 · §출력 교체)
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (새 클래스 `ApplyConfirmationsRoundTest`)

**Interfaces:**
- Consumes: Task 1 의 `[임시확정]`, Task 2 의 시트 구조, Task 5 의 호출 경로
- Produces: 없음 (마지막 실행부)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_plugin_consistency.py` 끝, `class ConfirmationRoundTest` **뒤**에 넣는다.

```python
class ApplyConfirmationsRoundTest(unittest.TestCase):
    """되묻기가 대화로 남으면 왕복이 20회가 된다.

    80건을 AskUserQuestion 으로 물으면 한 화면에 4개씩 20 화면이고 매 화면이
    세션 왕복이다. 답변이 새 애매성을 만들면 즉시 되묻지 않고 다음 차수 행으로
    써야 왕복이 0이 된다.
    """

    def setUp(self):
        self.text = (
            PLUGIN_ROOT / "skills" / "apply-confirmations" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_AskUserQuestion_을_쓰지_않는다(self):
        """문장만 바꾸면 통과하므로 도구 이름의 부재를 직접 본다."""
        self.assertNotIn(
            "AskUserQuestion", self.text,
            "되묻기에 AskUserQuestion 이 남아 있습니다 "
            "— 다음 차수 엑셀 행으로 보내야 왕복이 사라집니다",
        )

    def test_되묻던_네_경우가_다음_차수_행이_된다(self):
        self.assertIn("다음 차수", self.text)
        for 경우 in ("정정값이 비었", "형식", "충돌", "파급"):
            with self.subTest(경우=경우):
                self.assertIn(경우, self.text, f"되묻던 경우 「{경우}」 가 없습니다")

    def test_3차_상한과_임시확정_전환이_있다(self):
        self.assertIn("3차", self.text)
        self.assertIn("[임시확정]", self.text)
        self.assertIn(
            "templates/evidence-rules.md", self.text,
            "전환 규칙의 정본을 가리키지 않습니다 — 여기서 복제하면 두 벌이 갈립니다",
        )

    def test_요청_이력을_남긴다(self):
        """3차까지 요청했다는 증거가 없으면 [임시확정] 이 지어낸 값과 같아진다."""
        self.assertIn("요청 이력", self.text)
        self.assertIn("미응답", self.text)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
```

Expected: `4`

- [ ] **Step 3: `## 언제 도는가` 와 `## 왜 이 방식인가` 를 교체한다**

`skills/apply-confirmations/SKILL.md` 의 두 절을 아래로 바꾼다.

```markdown
## 언제 도는가

`/gx-명세일괄` Step 0-2 에서 **「확인요청서 반영하고 이어가기」** 를 고를 때 돈다.
본문을 다시 만들지 않는다 — **응답만 반영하고 다음 차수를 낸다.**

착수 협의로 값이 정해진 뒤 다시 부를 수 있다. 같은 파일에 이어 쓰면 된다.

## 왜 이 방식인가

미확정을 대화로 하나씩 물으면 왕복이 20회가 되고, 답이 오면 새 질문이 생겨
파이프라인이 끝나지 않는다. 사람이 **엑셀에서 한 번에** 답하고 이 스킬은
**읽고 파급만** 처리한다. 대화 왕복이 1~2회로 준다.

**되묻기에 AskUserQuestion 을 쓰지 않는다.** 답변이 새 애매성을 만들면 즉시
되묻지 않고 다음 차수 행으로 쓴다. 이것이 왕복을 0으로 만드는 자리다.
```

- [ ] **Step 4: Step 4 되묻기 절을 후속 질문 절로 교체한다**

`### Step 4: 되묻기 — 네 경우뿐` 절 전체를 아래로 바꾼다.

````markdown
### Step 4: 후속 질문을 다음 차수 행으로 쓴다

응답이 새 애매성을 만들면 **묻지 않고 시트 1 에 다음 차수 행을 추가한다.**

| 상황 | `AI 가 정한 값` | `근거` |
|------|----------------|--------|
| `수정` 인데 정정값이 비었다 | 원래 값 | 정정값이 비어 있어 원래 값을 유지했습니다 |
| 형식이 안 맞는다 | 원래 값 | 숫자가 필요한데 문장이 들어왔습니다: "{입력값}" |
| 다른 행과 충돌한다 | 둘 중 하나를 제안 | TB_A.EML 은 100, TB_B.EML 은 255 로 갈립니다 |
| 파급 방향이 갈린다 | 파급 결과 제안 | EML 을 100 으로 정정하셔서 UT-089 경계값을 101 로 바꿉니다 |

```
| 8 | 2 | UT-089 경계값 | 101자로 조정 | EML 을 100 으로 정정하셔서 | | | |
```

`판정` 을 비워 두면 다음 회차에서 「그 값으로 진행」으로 처리된다 —
사람이 아무것도 안 해도 파이프라인이 멈추지 않는다.

### Step 4-1: 차수를 올린다

| 상황 | 처리 |
|------|------|
| 답을 못 받은 `[미확정]` | 차수를 +1 해서 시트 2 에 다시 올린다 |
| 새로 생긴 후속 질문 | 새 차수로 시트 1 에 추가 |
| 이번 차수에 처리된 것 | 시트 3 「요청 이력」에 `반영` 으로 기록 |
| 이번 차수에 답이 없던 것 | 시트 3 에 `미응답` · `이월` 로 기록 |

**최대 3차다.** `templates/confirmation-request.md` §차수는 최대 3차다 가 정본이다.

### Step 4-2: 3차 미응답을 `[임시확정]` 으로 전환한다

3차까지 답이 없는 `[미확정]` 은 관행값을 채우고 `[임시확정]` 으로 표기한다.
전환 규칙의 정본은 `templates/evidence-rules.md` §[임시확정] 은 3차 미응답의
결과다 다. **여기서 규칙을 다시 정의하지 않는다.**

1. 관행값을 정하고 근거에 **`3차 미응답`** 을 반드시 적는다
2. 시트 3 에 `임시확정` 으로 기록한다
3. 그 값이 실린 산출물의 `## 개정이력` 위에 위험 표시를 넣는다
4. AN-05 `누락` 열에 `임시확정` 판정이 뜨도록 `trace-requirements` 를 다시 돌린다

**관행값을 못 정하는 것은 전환하지 않는다.** 파일 항목 구성처럼 관행이 없는
것은 `[미확정]` 으로 남기고 위험 목록에만 올린다 — 없는 항목을 지어내는 것은
`[임시확정]` 의 범위가 아니다.
````

- [ ] **Step 5: 출력 절을 교체한다**

`## 출력` 절의 코드펜스를 아래로 바꾼다.

````markdown
```
2차 확인요청서를 읽었습니다.

  가정 12건 — 맞음 8 · 수정 3 · 미확정으로 1
  미확정 33건 — 확정 9 · 대기 23 · 해당없음 1

  반영
    AN-03  입력항목 3건의 제약 갱신
    DE-08  컬럼 길이 3건 갱신
    DE-13  경계 케이스 18건 추가 (미확정 9건이 값을 얻어 보강 대상이 됨)

  3차로 넘어가는 것 27건
    · 답을 못 받은 미확정 23건
    · 정정값에서 생긴 후속 확인 4건

  📄 {프로젝트폴더}/xlsx/{시스템코드}-확인요청서.xlsx

3차가 마지막입니다. 답이 없는 항목은 [임시확정] 으로 채우고 위험 항목으로
표시합니다.
```

**「3차로 넘어가는 것」을 갈라 보여준다** — 사람이 "내가 안 한 게 아니라
발주기관 답이 안 온 것" 을 구분할 수 있어야 한다.

4회차(3차 반영)의 출력은 이렇다.

```
3차 확인요청서를 읽었습니다.

  확정 5건 · 미응답 8건

  미응답 8건을 [임시확정] 으로 채웠습니다.

    DAR-006  오류유형 코드값 목록   → EM01~EM09 임시 부여
    SFR-016  표본 최소 기준값       → 30건 (통계 관행)
    ...

  관행값을 정할 수 없어 [미확정] 으로 남긴 것 2건
    DAR-001  원천 파일 4종 항목 구성

  ⚠ 이 10건은 개발 착수 시 재작업 위험 항목입니다.
     산출물 5종 머리말과 AN-05 `누락` 열에 표시했습니다.
     요청 이력은 확인요청서 「요청 이력」 시트에 남아 있습니다.

5종이 최종 확정됐습니다. 차수 왕복을 마칩니다.
```
````

- [ ] **Step 6: 주의사항에 한 줄 더한다**

`## 주의사항` 의 마지막 항목 뒤에 붙인다.

```markdown
- **되묻지 않는다.** 애매하면 다음 차수 행으로 쓴다 — 대화 왕복이 이 스킬의 비용이다
```

- [ ] **Step 7: 테스트가 통과하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: `Ran 231 tests` / `OK`

- [ ] **Step 8: 되돌림 검증**

```bash
cd plugins/gx-pm
cp skills/apply-confirmations/SKILL.md /tmp/ac.bak
python -c "
import io
p='skills/apply-confirmations/SKILL.md'; s=io.open(p,encoding='utf-8').read()
s=s.replace('되묻지 않고 다음 차수 행으로 쓴다','AskUserQuestion 으로 되묻는다',1)
io.open(p,'w',encoding='utf-8',newline='').write(s)
"
python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
cp /tmp/ac.bak skills/apply-confirmations/SKILL.md
python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: 되돌린 상태에서 `1`, 복원 후 `OK`

- [ ] **Step 9: 커밋**

```bash
git add plugins/gx-pm/skills/apply-confirmations/SKILL.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -F - <<'EOF'
feat: 되묻기를 대화에서 다음 차수 엑셀 행으로 옮긴다

80건을 AskUserQuestion 으로 물으면 한 화면에 4개씩 20 화면이고 매
화면이 세션 왕복이라 그때마다 컨텍스트가 다시 실린다. 답변이 새
애매성을 만들면 즉시 되묻지 않고 다음 차수 행으로 쓴다 — 이것이
왕복을 0으로 만드는 자리다.

되묻던 네 경우가 전부 시트 1 의 행이 된다. 판정을 비워 두면 다음
회차에서 "그 값으로 진행" 으로 처리되므로 사람이 아무것도 안 해도
파이프라인이 멈추지 않는다.

3차 미응답은 [임시확정] 으로 전환하되 관행값을 못 정하는 것은
전환하지 않는다. 없는 항목을 지어내는 것은 그 범위가 아니다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
```

---

## Task 7: AN-05 `임시확정` 판정

**Files:**
- Modify: `plugins/gx-pm/templates/AN-05-traceability-matrix.md` (§누락 판정 표)
- Modify: `plugins/gx-pm/skills/trace-requirements/SKILL.md` (§Step 5 판정 사다리 · description 의 「8유형」)
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (`DesignConstraintReflectionTest` 에 메서드 추가)

**Interfaces:**
- Consumes: Task 1 의 `[임시확정]`, Task 6 의 전환 처리
- Produces: 없음

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`class DesignConstraintReflectionTest` 안, `test_누락_유형_수_표기가_문서마다_같다` **앞**에 넣는다.

```python
    def test_임시확정이_아홉번째_유형이다(self):
        """정본에 유형을 더하고 판정 순서를 안 고치면 그 유형이 영영 안 나온다.

        v3.2.0 의 `설계 제약 미반영` 이 그랬다 — 정본은 8유형인데 Step 5 는
        7개뿐이라 매트릭스를 만들어도 한 번도 찍히지 않았다.

        `임시확정` 은 값이 채워져 있어 다른 판정에 안 걸리므로, 사다리에
        자리를 주지 않으면 빈칸으로 남는다.
        """
        정본 = (
            PLUGIN_ROOT / "templates" / "AN-05-traceability-matrix.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^## 누락 판정$(.*?)(?=^## |\Z)", 정본, re.M | re.S)
        self.assertIsNotNone(구간, "AN-05 의 §누락 판정 절을 찾지 못했습니다")
        유형 = re.findall(r"^\| (\S[^|]*?) \|", 구간.group(1), re.M)
        유형 = [t for t in 유형 if t not in ("유형",) and "---" not in t]
        self.assertEqual(
            len(유형), 9,
            f"누락 유형이 9개가 아닙니다: {len(유형)}개 — {유형}",
        )
        self.assertIn("임시확정", 구간.group(1))

        절 = self._step5절()
        self.assertIn(
            "임시확정", 절,
            "Step 5 판정 순서에 `임시확정` 이 없습니다 — 정본에만 넣으면 "
            "매트릭스에 한 번도 안 찍힙니다",
        )
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
```

Expected: `1` 이상 (유형 수 8 ≠ 9)

- [ ] **Step 3: AN-05 정본에 유형을 더한다**

`templates/AN-05-traceability-matrix.md` §누락 판정 표의 마지막 행 뒤에 넣는다.

```markdown
| 임시확정 | 3차까지 요청했으나 미응답이라 관행값을 채운 항목이 이 요구사항에 걸려 있음 | `임시확정` |
```

그 아래 설명 문단 뒤에 붙인다.

```markdown
**`임시확정` 은 결함이 아니라 위험 표시다.** 값이 채워져 있어 다른 판정에 걸리지
않으므로 따로 자리를 준다. 전환 규칙은 `templates/evidence-rules.md`
§[임시확정] 은 3차 미응답의 결과다 가, 요청 이력은
`templates/confirmation-request.md` 의 「요청 이력」 시트가 정본이다.
```

- [ ] **Step 4: Step 5 판정 사다리에 자리를 준다**

`skills/trace-requirements/SKILL.md` 의 `7. **테스트는 있는데 \`결과\` 가 전건 공란**` 항목 **앞**에 넣고, 뒤 번호를 하나씩 민다(7→8, 8→9).

```markdown
7. **이 요구사항에 걸린 값 중 `[임시확정]` 이 1건 이상 있다** — `임시확정`.
   3차까지 요청했으나 답이 없어 관행값으로 채운 것이라, 개발 착수 시 재작업
   위험이 있다. 결함이 아니라 위험 표시다.

   **값이 채워져 있어 다른 판정에 안 걸린다.** 여기에 자리를 주지 않으면
   매트릭스에서 빈칸으로 남아 아무도 위험을 모른다.
```

`7. **테스트는 있는데...` 를 `8.` 로, `8. 위 어디에도 안 걸리면` 을 `9.` 로 고친다.

- [ ] **Step 5: 비기능 경로 범위를 넓힌다**

같은 파일에서 `3~7번(테스트·데이터 축 판정)만 적용한다` 를 찾아 아래로 바꾼다.

```markdown
3~8번(테스트·데이터 축 판정)만 적용한다.
```

- [ ] **Step 6: 유형 수 표기를 고친다**

같은 파일 frontmatter 의 `끊긴 곳(누락)을 8유형으로 탐지합니다` 를 `9유형` 으로,
`commands/gx-추적매트릭스.md` 와 `skills/id-trace/SKILL.md` 의 `8유형` 표기도 함께 고친다.

```bash
cd plugins/gx-pm
grep -rln "8유형" --include=*.md . | grep -v "^./archive/\|^./CHANGELOG.md"
```

찾은 파일마다 `8유형` → `9유형`.

- [ ] **Step 7: 테스트가 통과하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: `Ran 232 tests` / `OK`

- [ ] **Step 8: 커밋**

```bash
git add plugins/gx-pm/templates/AN-05-traceability-matrix.md plugins/gx-pm/skills/trace-requirements/SKILL.md plugins/gx-pm/commands/gx-추적매트릭스.md plugins/gx-pm/skills/id-trace/SKILL.md plugins/gx-pm/tests/test_plugin_consistency.py
git commit -F - <<'EOF'
feat: 임시확정을 AN-05 아홉번째 누락 유형으로 세운다

임시확정 은 값이 채워져 있어 다른 판정에 안 걸린다. 사다리에 자리를
주지 않으면 매트릭스에서 빈칸으로 남아 아무도 위험을 모른다.
v3.2.0 의 설계 제약 미반영 이 정본에만 있고 실행부에 없어 한 번도
찍히지 않았던 것과 같은 형태다.

결함이 아니라 위험 표시다 — 3차까지 요청했으나 답이 없어 관행값으로
채운 것이라 개발 착수 시 재작업 가능성이 있다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
```

---

## Task 8: 질문 정책 갱신과 버전

**Files:**
- Modify: `plugins/gx-pm/templates/pipeline-protocol.md` (§질문 정책)
- Modify: `plugins/gx-pm/CHANGELOG.md` · `plugins/gx-pm/.claude-plugin/plugin.json` · `.claude-plugin/marketplace.json` · `README.md`
- Modify: `D:\SQ\pm-test\00-테스트-실행안내.md`
- Test: `plugins/gx-pm/tests/test_plugin_consistency.py` (`QuestionCounterTest` 계열에 메서드 추가)

**Interfaces:**
- Consumes: Task 6 의 「되묻기는 엑셀로」
- Produces: 없음 (마지막)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`test_상한이_강제가_아니라_관측임을_밝힌다` **뒤**에 넣는다.

```python
    def test_되묻기가_엑셀로_간다는_것이_정책에_있다(self):
        """§질문 정책이 대화 질문만 다루면 엑셀 경로가 정책 밖에 남는다.

        어느 질문이 대화이고 어느 것이 파일인지가 한 곳에 없으면, 뒤에
        누가 되묻기를 다시 AskUserQuestion 으로 되돌려도 근거가 없다.
        """
        본문 = (
            PLUGIN_ROOT / "templates" / "pipeline-protocol.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^## 질문 정책$(.*?)(?=^## |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간)
        절 = 구간.group(1)
        self.assertIn("확인요청서", 절, "확인요청서 경로가 질문 정책에 없습니다")
        self.assertRegex(
            절, r"엑셀|파일로",
            "질문을 파일로 주고받는다는 층이 없습니다",
        )
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | grep -ac "^FAIL:"
```

Expected: `1`

- [ ] **Step 3: 질문 정책에 네 번째 층을 더한다**

`templates/pipeline-protocol.md` §질문 정책의 세 층 표 **뒤**에 넣는다.

```markdown
### 네 번째 층은 대화가 아니다

| 층 | 어디서 | 무엇을 | 상한 |
|----|--------|--------|------|
| **확인요청서** | **엑셀 파일** | `[가정]` 반증 · `[미확정]` 응답 · 후속 질문 | **3차** |

미확정 80건을 대화로 물으면 한 화면에 4개씩 20 화면이고 매 화면이 세션
왕복이다. 파일이면 생성 1회 · 읽기 1회다.

**`apply-confirmations` 는 AskUserQuestion 을 쓰지 않는다.** 답변이 새 애매성을
만들어도 즉시 되묻지 않고 다음 차수 행으로 쓴다. 양식과 차수 규칙의 정본은
`templates/confirmation-request.md` 다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
cd plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
```

Expected: `Ran 233 tests` / `OK`

- [ ] **Step 5: CHANGELOG 를 쓴다**

`plugins/gx-pm/CHANGELOG.md` 의 `## [Unreleased]` 바로 뒤에 넣는다.

```markdown

## [3.4.0] - 2026-09-09

미확정 질문을 대화에서 엑셀로 옮기고, 게이트 2 에서 중단해 최대 3차의
질문·답변 왕복으로 산출물을 확정한다.

### 바뀜

- **게이트 2 에서 중단하고 1차 확인요청서를 낸다.** 2차 시험 실측에서 미확정
  80건의 분포가 AN-03 65 · DE-08 8 · DE-13 7 이었다 — **게이트 2 시점에
  73/80 이 이미 나온다.** 게이트 3 뒤에 내면 답을 받은 뒤 이미 만든 DE-13 의
  경계 케이스를 파급 처리로 다시 쓴다. 10건 이하면 멈추지 않는다.
- **되묻기가 대화에서 엑셀로.** `apply-confirmations` 의 「되묻는 네 경우」가
  AskUserQuestion 이었다. 80건을 대화로 물으면 20 화면이고 매 화면이 세션
  왕복이다. 답변이 새 애매성을 만들면 **다음 차수 행으로 쓴다.**
- **확인요청서가 시트 넷으로.** 안내 · 가정 확인 · 미확정 확인 · 요청 이력.
  시트를 나누는 기준은 **「답할 사람」** 이다 — 시트 2 만 떼어 발주기관에
  보낼 수 있어야 한다.

### 새로

- **`[임시확정]` 세 번째 표기.** 3차까지 미응답이면 관행값을 채우되
  `[가정]` 과 구별한다 — `[가정]` 의 정의는 "RFP 가 규정하지 않았다" 인데
  이건 RFP 가 규정하고 값만 안 준 것이다. 같은 태그를 쓰면 누가 정할
  값이었는지가 지워지고 pm-test 함정 6건이 무너진다.
- **입력란 연노랑 배경.** 8열 중 3열만 입력란이라 색이 없으면 어디를 채울지
  모른다.
- **AN-05 `임시확정` 판정** (9번째 유형). 값이 채워져 있어 다른 판정에 안
  걸리므로 자리를 따로 준다.
- **요청 이력 시트.** 「3차까지 요청했으나 미응답」을 이 표가 증명한다.

### 계약 테스트

212 → 233건.
```

- [ ] **Step 6: 버전 4곳을 올린다**

```bash
cd D:/SQ/gx-pm/gx-pm
sed -i 's/"version": "3.3.1"/"version": "3.4.0"/' plugins/gx-pm/.claude-plugin/plugin.json .claude-plugin/marketplace.json
sed -i 's|badge/version-3.3.1|badge/version-3.4.0|' README.md
grep -rn "3\.4\.0" README.md .claude-plugin/marketplace.json plugins/gx-pm/.claude-plugin/plugin.json
```

Expected: 세 파일 모두 `3.4.0`

- [ ] **Step 7: pm-test 실행 안내서를 갱신한다**

`D:\SQ\pm-test\00-테스트-실행안내.md` 의 §3차 실행 절 뒤에 4차 왕복 절을 넣는다.

```markdown
## 4차 실행 — v3.4.0 차수 왕복

v3.4.0 은 게이트 2 에서 멈추고 확인요청서를 낸다. 실행이 4회로 나뉜다.

| 회차 | 하는 일 | 끝난 뒤 |
|---|---|---|
| 1 | 게이트 1·2 | 1차 확인요청서 → 중단 |
| 2 | 1차 반영 → DE-13·AN-05 → 게이트 3 | 2차 → 중단 |
| 3 | 2차 반영 | 3차 → 중단 |
| 4 | 3차 반영 → `[임시확정]` 전환 | 완료 |

### 확인할 것

| # | 확인 | 기대 |
|---|---|---|
| 1 | 게이트 2 중단 | 확인요청서를 내고 멈춘다. 세 종은 저장돼 있다 |
| 2 | 안내 멘트 | 파일 경로 · 번호 안내 · 다시 부르는 법이 화면에 |
| 3 | 시트 4장 | 안내 · 가정 확인 · 미확정 확인 · 요청 이력 |
| 4 | 입력란 색 | `판정`·`정정값`·`상태`·`응답` 이 연노랑 |
| 5 | 빈칸 진행 | 한 줄도 안 채우고 재실행해도 넘어간다 |
| 6 | 후속 질문 | 정정값을 넣으면 2차에 후속 행이 생긴다 |
| 7 | 대화 왕복 | 4회차 합계 10회 이하 (결정 기록으로 셈) |
| 8 | DE-13 밀도 | **5.0 이상** |
| 9 | 3차 전환 | 미응답분이 `[임시확정]` 이 되고 위험 목록이 뜬다 |
| 10 | AN-05 | `임시확정` 판정이 뜬다 |
| 11 | 요청 이력 | 1·2·3차가 다 남고 `미응답` 이 기록된다 |
| 12 | 조기 종료 | 미확정 0 이면 4회를 안 돈다 |

### 확인 스크립트

```bash
cd 건물에너지데이터통합관리시스템

# 3·4 — 시트와 입력란 색
python -c "
import openpyxl
wb = openpyxl.load_workbook('xlsx/REB-확인요청서.xlsx')
print('시트:', wb.sheetnames)
ws = wb['가정 확인']
print('판정 배경:', ws['F2'].fill.start_color.rgb)
"

# 9 — 임시확정 전환
grep -o '\[임시확정\]' REB-*.md | wc -l

# 10 — AN-05 판정
awk -F'|' 'NF>=9 && $2 ~ /REB-RE-/ {gsub(/^ +| +$/,"",$10); print ($10==""?"(빈칸)":$10)}' \
  REB-추적매트릭스.md | sort | uniq -c | sort -rn
```
```

- [ ] **Step 8: 전체 테스트와 커밋**

```bash
cd D:/SQ/gx-pm/gx-pm/plugins/gx-pm && python -m unittest discover -s tests -t tests 2>&1 | tail -3
cd D:/SQ/gx-pm/gx-pm
git add -A
git commit -F - <<'EOF'
docs: v3.4.0 — 확인요청서 차수 왕복으로 버전·문서를 맞춘다

질문 정책에 네 번째 층을 더한다. 어느 질문이 대화이고 어느 것이 파일인지
한 곳에 없으면, 뒤에 누가 되묻기를 다시 AskUserQuestion 으로 되돌려도
근거가 없다.

계약 테스트 212 → 233.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KxEq1noDvMSxBJFQzMP9eY
EOF
```

---

## Self-Review 결과

**1. 스펙 커버리지** — 스펙의 각 절을 태스크에 대응시켰다.

| 스펙 절 | 태스크 |
|---|---|
| 표기 3종 · `[임시확정]` | 1 |
| 차수 왕복 (4회 실행 / 3차) | 2(규칙) · 4(발행) · 6(전환) |
| 확인요청서 파일 구성 (시트 4장) | 2(정본) · 3(xlsx) |
| 채울 칸 색 | 2(규칙) · 3(구현) |
| 안내 멘트 3종 | 4(게이트 2·3) · 5(재개) · 6(반영 결과) |
| 게이트 2 중단 | 4 |
| 재개 선택지 | 5 |
| 후속 질문 | 6 |
| AN-05 `임시확정` | 7 |
| 정본 영향 · 계약 테스트 | 전 태스크 |
| pipeline-protocol §질문 정책 | 8 |
| 검증 (pm-test 4차) | 8 Step 7 |

빠진 것 없음.

**2. 플레이스홀더 스캔** — TBD·TODO 없음. 모든 코드·문구를 실제 내용으로 적었다.
`{시스템코드}`·`{K}` 같은 중괄호는 **런타임 치환 변수**이고 기존 규칙문의 관례다
(예: `templates/DE-08-table-definition.md` 의 `{suggestedColumnName}`).

**3. 타입 정합성**

- `_apply_input_fill` 의 인자 순서가 Task 3 Step 4(정의)와 Step 5(호출)에서 일치
- `input_columns` 는 `columns`·`dropdowns` 와 같은 길이 4 — Task 3 의 두 테스트가 검사
- 시트명 4개가 Task 2(정본 절 제목) · Task 3(`sheet_names`) 에서 일치
- 컬럼명 `AI 가 정한 값` 이 Task 2 정본 · Task 3 프로필 · Task 6 후속 질문 표에서 동일
- 누락 유형 수가 Task 7 에서 8 → 9 로 일관 (정본 표 · Step 5 사다리 · 유형 수 표기)
- 테스트 건수 누계: 212 → 213(T1) → 218(T2) → 222(T3) → 225(T4) → 227(T5) → 231(T6) → 232(T7) → 233(T8)
