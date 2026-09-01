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


if __name__ == "__main__":
    unittest.main()
