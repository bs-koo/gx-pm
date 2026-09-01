"""추출 규칙이 문서에만 있고 동작하지 않는 것을 막는다.

`design-test-cases` 의 경계값 규칙처럼, 마크다운에 적힌 규칙은 아무도 시험하지 않으면
적혀만 있고 동작하지 않는다. 여기서는 문서에 실린 정규식을 **그대로 뽑아** 픽스처와
"판정 예시" 목록에 적용한다.

이 장치가 갈라질 수 없게 고정하는 것은 **정규식 리터럴** 과 **판정 예시 목록**, 둘뿐이다.
정규식을 고치면 이 파일의 시험이 잡고, 판정 예시를 고치면 `test_문서의_판정_예시가_정규식과_일치한다`
가 잡는다. 그 둘을 감싼 산문(표 단위/행 단위 의미론, 중복 제거 절차 등)은 이 장치가 지키지
않는다 — 산문과 정규식이 어긋나도 이 스위트는 통과하며, 산문의 정확성은 테스트가 아니라
리뷰의 몫이다.

인식 규칙은 2단계다 — 1단계(정규식)는 ID 형태 후보를 기계적으로 찾고, 2단계(산문으로만
서술된 판단)는 그 표가 실제로 요구사항 표인지를 가른다. 이 파일이 시험할 수 있는 것은
1단계뿐이다. 그래서 "판정 예시" 목록은 셋으로 나뉜다 — 뽑는다(1단계 통과) / 정규식이
거른다(1단계에서 탈락) / 정규식은 걸리지만 요구사항 표가 아니다(1단계는 통과하지만 2단계
산문 판단으로만 거른다, 자동 검사 불가 — 여기서는 "정규식이 후보로는 잡는다"만 확인한다).
"""

import re
import unittest

from helpers import PLUGIN_ROOT

SKILL = PLUGIN_ROOT / "skills" / "extract-requirements" / "SKILL.md"
FIXTURE = PLUGIN_ROOT / "tests" / "fixtures" / "requirement-tables.md"

# 픽스처가 담고 있는 요구사항 ID. 순서까지 같아야 한다.
기대_ID = ["BR-01", "BR-02", "BR-03", "NFR-01", "NFR-02"]

# 문서에도 픽스처에도 등장하지 않는 합성 접두어. 규칙이 (?:BR|NFR|SFR|PER|SER|ECRM) 처럼
# 문서에 나온 접두어만 하드코딩해도 문서 기반 예시는 전부 통과해버린다 — 이 값만이
# 일반화([A-Z]{2,4})를 강제한다.
합성_ID = "XYZ-01"


def 문서에서_정규식을_뽑는다() -> str:
    """SKILL.md 의 ```regex 펜스에서 ID 표 인식(1단계) 정규식을 꺼낸다."""
    text = SKILL.read_text(encoding="utf-8")
    펜스 = re.findall(r"```regex\n(.*?)\n```", text, re.S)
    if len(펜스) != 1:
        raise AssertionError(
            f"SKILL.md 의 ```regex 펜스가 1개가 아닙니다 (발견 {len(펜스)}개) "
            "— 테스트가 어느 것을 시험할지 결정할 수 없습니다"
        )
    return 펜스[0].strip()


def 문서에서_판정_예시를_뽑는다() -> tuple[list[str], list[str], list[str]]:
    """SKILL.md 의 '판정 예시' 절에서 세 목록을 꺼낸다.

    뽑는다 / 정규식이 거른다 / 정규식은 걸리지만 요구사항 표가 아니다.
    뒤 두 목록은 서로 다른 것이 거른다 — 앞은 1단계 정규식 자체가, 뒤는 문서에만
    있는 2단계 판단이 거른다. 하나로 합쳐서 정규식에만 물으면 뒤 목록의 항목은
    (정규식은 실제로 후보로 잡으므로) 언제나 실패한다.

    각 항목은 `- \\`...\\`` 또는 내용에 백틱이 섞인 경우 `` - ``...`` `` 형태로
    적는다 — 후자는 백틱을 포함한 예시(예: 백틱으로 표기된 ID)를 위한 것이다.
    """
    text = SKILL.read_text(encoding="utf-8")
    절 = re.search(r"#### 판정 예시(.*?)(?=\n#### |\n### |\Z)", text, re.S)
    if 절 is None:
        raise AssertionError("SKILL.md 에서 '#### 판정 예시' 절을 찾지 못했습니다")
    본문 = 절.group(1)

    for 표지 in ("**정규식이 거른다**", "**정규식은 걸리지만 요구사항 표가 아니다**"):
        if 표지 not in 본문:
            raise AssertionError(f"판정 예시 절에 '{표지}' 소제목이 없습니다")

    뽑는다_절, 나머지 = 본문.split("**정규식이 거른다**", 1)
    거른다_절, 아니다_절 = 나머지.split("**정규식은 걸리지만 요구사항 표가 아니다**", 1)

    def 뽑기(절: str) -> list[str]:
        # \1 백참조로 여는/닫는 백틱 개수(1개 또는 2개)를 맞춘다 — 예시 내용 자체에
        # 백틱이 들어가면(``BR-03`` 표기 예시) 이중 백틱 펜스로 감싸 적기 때문이다.
        return [
            m.group(2)
            for m in re.finditer(r"^- (`{1,2})(.+?)\1(?=\s|$)", 절, re.M)
        ]

    return 뽑기(뽑는다_절), 뽑기(거른다_절), 뽑기(아니다_절)


class ExtractRuleTest(unittest.TestCase):
    def setUp(self):
        self.패턴 = re.compile(문서에서_정규식을_뽑는다())
        self.픽스처 = FIXTURE.read_text(encoding="utf-8")

    def test_요구사항_표에서_ID를_전부_뽑는다(self):
        찾음 = [
            m.group(1)
            for line in self.픽스처.splitlines()
            if (m := self.패턴.match(line))
        ]
        self.assertEqual(
            찾음, 기대_ID,
            "문서에 적힌 정규식이 픽스처의 요구사항 ID 를 기대대로 뽑지 못합니다",
        )

    def test_ID_표기_변형과_근접_오답을_가른다(self):
        """정규식의 정밀도를 문서의 '판정 예시' 목록으로 시험한다.

        목록을 여기 다시 하드코딩하지 않는다 — SKILL.md 가 정본이고, 이미 그 목록을
        문서에서_판정_예시를_뽑는다() 가 파싱한다. 두 테스트가 같은 헬퍼를 읽는 것은
        괜찮지만, 같은 데이터를 두 번 하드코딩하는 것은 안 된다(둘 중 하나만
        고치고 다른 하나는 낡은 채로 남는다).

        유일하게 하드코딩하는 합성_ID(XYZ-01)는 문서에도 픽스처에도 없는 접두어라
        (?:BR|NFR|SFR|PER|SER|ECRM) 식으로 정규식을 접두어 나열로 바꿔치기해도
        문서 기반 예시만으로는 절대 잡히지 않는다 — 이것만이 일반화를 강제한다.
        """
        뽑는다, 정규식이_거른다, _ = 문서에서_판정_예시를_뽑는다()

        for 줄 in 뽑는다:
            with self.subTest(뽑는다=줄):
                self.assertIsNotNone(
                    self.패턴.match(줄), "요구사항 ID 표기 변형을 놓칩니다",
                )
        for 줄 in 정규식이_거른다:
            with self.subTest(정규식이_거른다=줄):
                self.assertIsNone(
                    self.패턴.match(줄), "요구사항 ID 가 아닌 것을 뽑았습니다",
                )

        self.assertIsNotNone(
            self.패턴.match(f"| {합성_ID} | 내용 |"),
            "문서·픽스처에 없는 합성 접두어를 놓칩니다 "
            "— 정규식이 특정 접두어 나열로 하드코딩됐을 수 있습니다",
        )

    def test_문서의_판정_예시가_정규식과_일치한다(self):
        """문서가 약속한 판정과 정규식(1단계)의 실제 동작이 같은지 대조한다.

        픽스처에는 BR·NFR·SFR 뿐이라, 픽스처만으로는 규칙이 그 셋 밖으로
        일반화되는지 전혀 증명되지 않는다. 정규식을 `(?:BR|NFR|SFR)` 로
        하드코딩해도 픽스처 시험은 통과한다 — 문서의 PER·SER·ECRM 예시가 그 구멍을
        막는다.

        '정규식은 걸리지만 요구사항 표가 아니다' 목록은 2단계(산문) 판단으로만
        걸러지므로, 여기서는 정규식이 "후보로는 잡는다"만 확인한다 — 2단계
        자체는 자동 검사 대상이 아니다(모듈 docstring 참조).
        """
        뽑는다, 정규식이_거른다, 정규식은_걸리지만_아니다 = 문서에서_판정_예시를_뽑는다()
        self.assertGreaterEqual(len(뽑는다), 5, "'뽑는다' 예시가 너무 적습니다")
        self.assertGreaterEqual(len(정규식이_거른다), 5, "'정규식이 거른다' 예시가 너무 적습니다")
        self.assertGreaterEqual(
            len(정규식은_걸리지만_아니다), 3,
            "'정규식은 걸리지만 요구사항 표가 아니다' 예시가 너무 적습니다",
        )

        for 줄 in 뽑는다:
            with self.subTest(뽑는다=줄):
                self.assertIsNotNone(
                    self.패턴.match(줄),
                    "문서가 뽑는다고 적었는데 정규식이 놓칩니다",
                )
        for 줄 in 정규식이_거른다:
            with self.subTest(정규식이_거른다=줄):
                self.assertIsNone(
                    self.패턴.match(줄),
                    "문서가 정규식이 거른다고 적었는데 정규식이 뽑습니다",
                )
        for 줄 in 정규식은_걸리지만_아니다:
            with self.subTest(정규식은_걸리지만_아니다=줄):
                self.assertIsNotNone(
                    self.패턴.match(줄),
                    "문서가 '정규식은 걸린다'(2단계에서만 거른다)고 적었는데 "
                    "정규식 자체가 놓칩니다 — 이 목록은 1단계 후보에는 걸려야 합니다",
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
        """판정 순서를 실제로 검사한다.

        종전 형태(NFR·QE·QR·"업무 규칙은 기능" 네 문자열이 존재하는지만 확인)는
        순서를 전혀 보지 않아, 1번(원문 ID 접두어)과 3번(그 외 → 기능) 항목을
        서로 바꿔 캐치올이 먼저 발동해도(모든 NFR 이 기능으로 분류되고 시스템테스트ID
        가 하나도 나가지 않아도) 통과했다. 세 절의 등장 위치를 비교해 순서를
        고정한다.
        """
        for 조각 in ("NFR", "QE", "QR"):
            with self.subTest(조각=조각):
                self.assertIn(조각, self.text)
        self.assertIn(
            "업무 규칙은 기능", self.text,
            "BR 같은 업무 규칙이 기능으로 분류된다는 근거가 없습니다",
        )

        단계1 = "원문 ID 접두어가 `NFR`"
        단계2 = "섹션 제목에 \"비기능\""
        단계3 = "그 외 → 기능"
        for 조각 in (단계1, 단계2, 단계3):
            self.assertIn(조각, self.text, f"판정 순서 절에서 '{조각}' 을 찾지 못했습니다")

        위치1 = self.text.index(단계1)
        위치2 = self.text.index(단계2)
        위치3 = self.text.index(단계3)
        self.assertLess(
            위치1, 위치2,
            "판정 순서가 바뀌었습니다 — 원문 ID 접두어(NFR/QE/QR) 판정이 "
            "섹션 제목 판정보다 뒤에 있습니다",
        )
        self.assertLess(
            위치2, 위치3,
            "판정 순서가 바뀌었습니다 — 섹션 제목 판정이 '그 외 → 기능' 보다 뒤에 있습니다",
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
