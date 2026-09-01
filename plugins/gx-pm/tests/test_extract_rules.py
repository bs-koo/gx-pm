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
