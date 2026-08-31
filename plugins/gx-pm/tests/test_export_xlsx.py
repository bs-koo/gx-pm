import unittest

from helpers import load_export_module, read_docs


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

    def test_긴_산문은_종결어미가_없어도_제목으로_쓰지_않는다(self):
        # 32자, 종결어미 아님 — 길이 가드로만 걸러진다.
        # 이 단언이 없으면 <= 30 을 <= 100 으로 되돌려도 테스트가 통과한다.
        md = (
            "### 근거\n\n"
            "본 계획은 발주처 협의 결과와 감리 지적사항을 반영하여 수립한 것임\n\n"
            "| A | B |\n|---|---|\n| 1 | 2 |\n"
        )
        self.assertEqual(self.mod.parse_markdown_tables(md)[0][0], "근거")

    def test_코드펜스는_표_제목으로_쓰지_않는다(self):
        md = (
            "### 결함 상태 흐름\n\n"
            "```\n"
            "Open -> Assigned -> Fixed\n"
            "```\n\n"
            "| 상태 | 의미 |\n|---|---|\n| Open | 등록됨 |\n"
        )
        self.assertEqual(self.mod.parse_markdown_tables(md)[0][0], "결함 상태 흐름")

    def test_긴_코드블록_뒤에도_상위_헤딩을_찾는다(self):
        body = "\n".join(f"line {i}" for i in range(12))
        md = f"### 상태 흐름\n\n```\n{body}\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        self.assertEqual(self.mod.parse_markdown_tables(md)[0][0], "상태 흐름")


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

    def test_일부만_겹치는_보조_표도_None_을_반환한다(self):
        # 교집합 1/8 = 0.125 — 0.5 임계값이 실제로 하중을 받는지 본다.
        # 이 단언이 없으면 임계값을 0 으로 되돌려도 테스트가 통과한다.
        self.assertIsNone(self.mod._matched_set_index([["화면ID", "계"]], "단위테스트계획서"))

    def test_산출물_유형이_없으면_None_을_반환한다(self):
        rows = [["결함ID", "심각도"]]
        self.assertIsNone(self.mod._matched_set_index(rows, None))

    def test_시트명_세트와_재배열_세트가_어긋나지_않는다(self):
        """종전에는 같은 판단이 두 벌이었다.

        시트명은 `_matched_set_index`, 컬럼 순서는 `_reorder_columns` 가 각자
        "가장 잘 맞는 세트" 를 다시 계산했다. 한쪽 임계값만 고치면 시트가
        A 세트의 이름을 달고 B 세트의 순서로 나온다 — 눈으로만 보이는 고장이다.
        지금은 둘 다 `_best_column_set` 하나를 쓴다.

        컬럼 순서를 뒤집어 넣어 재배열이 실제로 일어나게 만든 뒤 검사한다.
        """
        for 산출물, 프로필 in self.mod.DOCUMENT_PROFILES.items():
            for 세트번호, 컬럼들 in enumerate(프로필["columns"]):
                if not 컬럼들:
                    continue
                뒤집힌 = list(reversed(컬럼들))
                rows = [뒤집힌, ["x"] * len(뒤집힌)]
                with self.subTest(산출물=산출물, 세트=세트번호):
                    골라진 = self.mod._matched_set_index(rows, 산출물)
                    self.assertIsNotNone(골라진, "완전 일치인데 본문 표로 보지 않았습니다")
                    self.assertEqual(
                        self.mod._reorder_columns(rows, 산출물)[0],
                        list(프로필["columns"][골라진]),
                        "재배열이 시트명과 다른 컬럼 세트를 썼습니다",
                    )


class SheetNamingTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()

    def test_컬럼_세트별로_다른_시트명을_준다(self):
        names = self.mod.DOCUMENT_PROFILES["단위테스트계획서"]["sheet_names"]
        self.assertEqual(names[0], "DE-13 단위테스트계획")
        self.assertEqual(names[1], "DE-13 테스트케이스")


class ProfileColumnBindingTest(unittest.TestCase):
    """DOCUMENT_PROFILES 의 컬럼명과 문서가 따로 놀지 않게 묶는다.

    프로필 컬럼은 xlsx 재배열의 기준이고, 그 이름을 실제로 만들어 내는 것은
    스킬·템플릿 문서다. 한쪽에서 컬럼명을 바꾸면 매칭률이 임계값 아래로 떨어져
    **조용히** 재배열이 멈추고 사용자는 원본 순서를 받는다. 예외도 오류도 없다.

    검사 강도를 여기까지로 정한 이유:
    문서가 컬럼을 세 가지 모양으로 적는다 — 표 헤더 행, `| 컬럼 | 설명 |` 서술표,
    산문. 더 엄격한 기준(헤더 행에 완전히 등장할 것)은 축약 예시를 쓰는 정당한
    스킬 문서를 오탐한다. 실측으로 확인함(엄격 기준 12건 오탐, 이 기준 0건).
    """

    def setUp(self):
        self.mod = load_export_module()
        self.문서 = "".join(text for _, text in read_docs())

    def test_모든_프로필_컬럼이_문서에_존재한다(self):
        for 산출물, 프로필 in self.mod.DOCUMENT_PROFILES.items():
            for 세트번호, 컬럼들 in enumerate(프로필["columns"]):
                for 컬럼 in 컬럼들:
                    with self.subTest(산출물=산출물, 세트=세트번호, 컬럼=컬럼):
                        self.assertIn(
                            컬럼, self.문서,
                            f"프로필이 기대하는 컬럼 '{컬럼}' 을 어떤 문서도 만들지 않습니다 "
                            "— 오타이거나, 문서에서 이름이 바뀌었는데 프로필이 안 따라왔습니다",
                        )


if __name__ == "__main__":
    unittest.main()
