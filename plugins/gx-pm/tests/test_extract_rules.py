"""추출 규칙이 문서에만 있고 동작하지 않는 것을 막는다.

`design-test-cases` 의 경계값 규칙처럼, 마크다운에 적힌 규칙은 아무도 시험하지 않으면
적혀만 있고 동작하지 않는다. 여기서는 문서에 실린 정규식을 **그대로 뽑아** 픽스처와
"판정 예시" 목록에 적용한다.

이 장치가 갈라질 수 없게 고정하는 것은 **정규식 리터럴** 과 **판정 예시 목록**, 둘뿐이다.
정규식을 고치면 이 파일의 시험이 잡고, 판정 예시를 고치면 `test_문서의_판정_예시가_정규식과_일치한다`
가 잡는다. 그 둘을 감싼 산문(표 단위/행 단위 의미론, 중복 제거 절차 등)은 이 장치가 지키지
않는다 — 산문과 정규식이 어긋나도 이 스위트는 통과하며, 산문의 정확성은 테스트가 아니라
리뷰의 몫이다.
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


def 문서에서_판정_예시를_뽑는다() -> tuple[list[str], list[str]]:
    """SKILL.md 의 '판정 예시' 절에서 뽑는다/뽑지 않는다 목록을 꺼낸다.

    문서에 적힌 예시를 그대로 시험 입력으로 쓴다. 사람이 읽는 예시와 정규식이
    어긋나면 여기서 걸린다 — 산문에 짐을 지우는 유일한 지점이다.
    """
    text = SKILL.read_text(encoding="utf-8")
    절 = re.search(r"#### 판정 예시(.*?)(?=\n#### |\n### |\Z)", text, re.S)
    if 절 is None:
        raise AssertionError("SKILL.md 에서 '#### 판정 예시' 절을 찾지 못했습니다")
    본문 = 절.group(1)
    if "**뽑지 않는다**" not in 본문:
        raise AssertionError("판정 예시 절에 '**뽑지 않는다**' 소제목이 없습니다")
    앞, 뒤 = 본문.split("**뽑지 않는다**", 1)
    뽑기 = lambda s: re.findall(r"^- `([^`]+)`", s, re.M)
    return 뽑기(앞), 뽑기(뒤)


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

    def test_ID_표기_변형과_근접_오답을_가른다(self):
        """픽스처와 무관한 입력으로 정규식의 정밀도만 시험한다.

        종전 형태(`**BR-03**` 이 뽑히는지)는 test_요구사항_표에서_ID를_전부_뽑는다 가
        순서까지 정확히 비교하므로 혼자서는 절대 실패하지 못했다 — 개수만 늘리고
        아무것도 지키지 않는 테스트였다.
        """
        뽑혀야_함 = {
            "| BR-03 | 내용 |": "BR-03",
            "| **BR-03** | 내용 |": "BR-03",          # RFP 가 ID 를 강조하는 일은 흔하다
            "|  NFR-01  | 내용 |": "NFR-01",          # 여백이 넉넉한 표
            "| SFR-001 | 내용 |": "SFR-001",          # 3자리 순번
        }
        for 줄, 기대 in 뽑혀야_함.items():
            with self.subTest(줄=줄):
                m = self.패턴.match(줄.strip())
                self.assertIsNotNone(m, "요구사항 ID 표기 변형을 놓칩니다")
                self.assertEqual(m.group(1), 기대)

        뽑히면_안_됨 = [
            "| B-1 | 내용 |",                          # 1자리 코드 + 1자리 순번
            "| BR_03 | 내용 |",                        # 하이픈이 아니라 밑줄
            "| br-03 | 내용 |",                        # 소문자
            "| 1 | 08:00~09:00 | 허용 |",              # 판정표
            "| OVERLAPPING_RESERVATION | 409 |",       # 오류 코드명
            "| 회의실 | BR-03 | 내용 |",               # ID 가 첫 열이 아니다
        ]
        for 줄 in 뽑히면_안_됨:
            with self.subTest(줄=줄):
                self.assertIsNone(
                    self.패턴.match(줄.strip()),
                    "요구사항 ID 가 아닌 것을 뽑았습니다",
                )

    def test_문서의_판정_예시가_정규식과_일치한다(self):
        """문서가 약속한 판정과 정규식의 실제 동작이 같은지 대조한다.

        픽스처에는 BR·NFR·SFR 뿐이라, 픽스처만으로는 규칙이 그 셋 밖으로
        일반화되는지 전혀 증명되지 않는다. 정규식을 `(?:BR|NFR|SFR)` 로
        하드코딩해도 전체 스위트가 통과한다 — 이 테스트가 그 구멍을 막는다.
        """
        뽑는다, 뽑지_않는다 = 문서에서_판정_예시를_뽑는다()
        self.assertGreaterEqual(len(뽑는다), 5, "'뽑는다' 예시가 너무 적습니다")
        self.assertGreaterEqual(len(뽑지_않는다), 5, "'뽑지 않는다' 예시가 너무 적습니다")

        for 줄 in 뽑는다:
            with self.subTest(뽑는다=줄):
                self.assertIsNotNone(
                    self.패턴.match(줄.strip()),
                    "문서가 뽑는다고 적었는데 정규식이 놓칩니다",
                )
        for 줄 in 뽑지_않는다:
            with self.subTest(뽑지_않는다=줄):
                self.assertIsNone(
                    self.패턴.match(줄.strip()),
                    "문서가 뽑지 않는다고 적었는데 정규식이 뽑습니다",
                )


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
            "같은 원문 ID 는 요구사항 **1건**으로 센다", self.text,
            "중복 제거 규칙이 몇 건으로 세라고 말하지 않습니다",
        )

    def test_기능_비기능_판정_순서가_있다(self):
        for 조각 in ("NFR", "QE", "QR"):
            with self.subTest(조각=조각):
                self.assertIn(조각, self.text)
        self.assertIn(
            "업무 규칙은 기능", self.text,
            "BR 같은 업무 규칙이 기능으로 분류된다는 근거가 없습니다",
        )

    def test_원문_ID_보존_위치가_있다(self):
        self.assertIn(
            "과업지시서 BR-01", self.text,
            "원문 ID 를 근거 열에 어떻게 적는지 예시가 없습니다",
        )
        self.assertIn(
            "제안요청ID 열에 넣지 않는다", self.text,
            "원문 ID 를 제안요청ID 열에 넣지 말라는 금지가 없습니다 "
            "— SFR- 체계가 무너집니다",
        )


if __name__ == "__main__":
    unittest.main()
