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

    def test_볼드_라벨_라인은_제목으로_쓴다(self):
        md = "**부적합 목록**\n\n| 결함ID | 심각도 |\n|---|---|\n| B-DF-001 | Major |\n"
        tables = self.mod.parse_markdown_tables(md)
        self.assertEqual(tables[0][0], "**부적합 목록**")

    def test_글머리표_항목은_표_제목으로_쓰지_않는다(self):
        md = (
            "### 결함 현황\n\n"
            "- 조치율 50%\n\n"
            "| 결함ID | 상태 |\n|---|---|\n| B-DF-001 | Open |\n"
        )
        tables = self.mod.parse_markdown_tables(md)
        self.assertEqual(tables[0][0], "결함 현황")

    def test_번호목록_항목은_표_제목으로_쓰지_않는다(self):
        md = (
            "### 조치 절차\n\n"
            "1. 원인 분석\n\n"
            "| 단계 | 내용 |\n|---|---|\n| 1 | 분석 |\n"
        )
        tables = self.mod.parse_markdown_tables(md)
        self.assertEqual(tables[0][0], "조치 절차")


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


if __name__ == "__main__":
    unittest.main()
