import re
import unittest

from helpers import PLUGIN_ROOT, load_export_module, parse_column_ssot, read_docs


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
        rows = [["테스트ID", "연계기능ID", "연계요구사항ID", "사전조건", "입력",
                 "기대결과", "사후조건", "의존성", "테스트담당자", "수행일", "결과"]]
        self.assertEqual(self.mod._matched_set_index(rows, "단위테스트계획서"), 0)

    def test_두번째_컬럼_세트도_구분한다(self):
        # 단위테스트계획서는 27개 검사기준 시트 폐지로 컬럼 세트가 하나뿐이다.
        # "여러 세트를 구분한다" 는 취지는 세트가 여전히 여럿인 총괄테스트계획서로 검증한다.
        rows = [["기준", "목표치", "비고"]]
        self.assertEqual(self.mod._matched_set_index(rows, "총괄테스트계획서"), 1)

    def test_보조_표는_None_을_반환한다(self):
        rows = [["경계값", "값", "출처"]]
        self.assertIsNone(self.mod._matched_set_index(rows, "단위테스트계획서"))

    def test_일부만_겹치는_보조_표도_None_을_반환한다(self):
        # 교집합 5/11 ≈ 0.45 — 0.5 임계값이 실제로 하중을 받는지 본다.
        # 이 단언이 없으면 임계값을 0 으로 되돌려도 테스트가 통과한다.
        rows = [["테스트ID", "연계기능ID", "사전조건", "입력", "기대결과", "계"]]
        self.assertIsNone(self.mod._matched_set_index(rows, "단위테스트계획서"))

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
        # 단위테스트계획서는 27개 검사기준 시트 폐지로 sheet_names 자체가 없다.
        # 여러 세트가 각각 다른 시트명을 받는지는 총괄테스트계획서로 검증한다.
        names = self.mod.DOCUMENT_PROFILES["총괄테스트계획서"]["sheet_names"]
        self.assertEqual(names[0], "TE-01 테스트 레벨")
        self.assertEqual(names[1], "TE-01 종료기준")


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


class An05ColumnSsotTest(unittest.TestCase):
    """AN-05 컬럼 세트의 정본은 templates/AN-05-traceability-matrix.md 다.

    종전에는 템플릿·trace-requirements 스킬·export-xlsx 프로필 셋이 서로 다른 컬럼
    목록을 갖고 있었다 — 영역 1·2·4 전부에서 갈렸고, 그래서 extract-requirements 가
    AN-02 의 `근거` 열에 넣은 원문 ID 가 추적매트릭스로 넘어가지 못했다.
    양방향으로 묶어 다시 갈라질 수 없게 한다.
    """

    def setUp(self):
        self.mod = load_export_module()
        템플릿 = (
            PLUGIN_ROOT / "templates" / "AN-05-traceability-matrix.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(
            r"^### 본문 표 헤더 \(플랫[^\n]*\)$(.*?)(?=^#{1,3} |\Z)",
            템플릿, re.M | re.S,
        )
        self.assertIsNotNone(
            구간,
            "AN-05 템플릿에서 '### 본문 표 헤더 (플랫…)' 절을 찾지 못했습니다 "
            "— 절이 삭제됐거나 제목이 바뀌었습니다",
        )
        self.정본컬럼 = []
        for 줄 in 구간.group(1).splitlines():
            벗긴줄 = 줄.strip()
            if not (벗긴줄.startswith("|") and 벗긴줄.endswith("|")):
                continue
            칸 = [c.strip() for c in 벗긴줄.strip("|").split("|")]
            if len(칸) != 3 or set("".join(칸)) <= set("-: "):
                continue
            if 칸[0] == "#":
                continue  # 머리행
            self.정본컬럼.append(칸[1])

    def test_정본_플랫_헤더가_비어있지_않다(self):
        """파싱이 조용히 빈 목록을 내면 아래 두 테스트가 공허하게 통과한다."""
        self.assertGreaterEqual(
            len(self.정본컬럼), 20,
            f"정본 플랫 헤더에서 뽑은 컬럼이 20개 미만입니다: {self.정본컬럼}",
        )

    def test_프로필의_모든_컬럼이_정본에_있다(self):
        """프로필에만 있는 컬럼은 아무도 만들지 않는 유령 컬럼이다."""
        for 세트번호, 컬럼들 in enumerate(
            self.mod.DOCUMENT_PROFILES["추적매트릭스"]["columns"]
        ):
            for 컬럼 in 컬럼들:
                with self.subTest(세트=세트번호, 컬럼=컬럼):
                    self.assertIn(
                        컬럼, self.정본컬럼,
                        f"프로필의 '{컬럼}' 이 AN-05 템플릿의 플랫 헤더에 없습니다 "
                        "— 정본에 추가하거나 프로필에서 빼세요",
                    )

    def test_정본의_모든_컬럼이_전체_세트에_있다(self):
        """정본에만 있는 컬럼은 xlsx 에서 재배열되지 않고 뒤로 밀린다.

        전체 세트가 정본을 다 담아야 한다. 축약 세트는 부분집합이므로 검사하지 않는다.
        """
        전체세트 = self.mod.DOCUMENT_PROFILES["추적매트릭스"]["columns"][0]
        for 컬럼 in self.정본컬럼:
            with self.subTest(컬럼=컬럼):
                self.assertIn(
                    컬럼, 전체세트,
                    f"정본의 '{컬럼}' 이 프로필 전체 세트에 없습니다 "
                    "— xlsx 에서 공공 양식 순서로 재배열되지 않습니다",
                )


class MergeRangesTest(unittest.TestCase):
    """참조 양식은 대분류·중분류를 같은 값끼리 세로 병합한다.

    행 인덱스는 시트 기준이다. rows[0] 이 헤더라 시트 1행,
    rows[i] 는 시트 i+1 행이 된다.
    """

    def setUp(self):
        self.mod = load_export_module()

    def test_연속_동일값을_병합_범위로_묶는다(self):
        rows = [
            ["대분류", "중분류", "요구사항ID"],
            ["데이터 전처리", "상대평가기준", "REQ-001"],
            ["데이터 전처리", "상대평가기준", "REQ-002"],
            ["데이터 전처리", "달력맞춤", "REQ-004"],
        ]
        구간 = self.mod.merge_ranges(rows, ["대분류", "중분류"])
        self.assertIn((0, 2, 4), 구간, "대분류 3행이 하나로 묶여야 합니다")
        self.assertIn((1, 2, 3), 구간, "중분류 2행이 하나로 묶여야 합니다")

    def test_한_행짜리는_병합하지_않는다(self):
        rows = [["대분류", "중분류"], ["A", "x"], ["B", "y"]]
        self.assertEqual(self.mod.merge_ranges(rows, ["대분류", "중분류"]), [])

    def test_빈값은_병합하지_않는다(self):
        """빈칸이 이어지는 것은 같은 값이 아니라 값이 없는 것이다."""
        rows = [["대분류"], [""], [""], [""]]
        self.assertEqual(self.mod.merge_ranges(rows, ["대분류"]), [])

    def test_병합_대상이_아닌_컬럼은_묶지_않는다(self):
        rows = [["요구사항ID"], ["REQ-001"], ["REQ-001"]]
        self.assertEqual(self.mod.merge_ranges(rows, ["대분류"]), [])

    def test_헤더에_없는_병합_컬럼은_무시한다(self):
        rows = [["중분류"], ["A"], ["A"]]
        self.assertEqual(self.mod.merge_ranges(rows, ["대분류", "중분류"]), [(0, 2, 3)])

    def test_떨어진_동일값은_따로_묶는다(self):
        """정렬이 깨진 표를 억지로 이어 붙이면 없는 사실을 만든다."""
        rows = [["대분류"], ["A"], ["A"], ["B"], ["A"], ["A"]]
        구간 = self.mod.merge_ranges(rows, ["대분류"])
        self.assertEqual(sorted(구간), [(0, 2, 3), (0, 5, 6)])


class RevisionHistoryProfileTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()

    def test_개정이력_프로필이_있다(self):
        self.assertIn("개정이력", self.mod.DOCUMENT_PROFILES)

    def test_개정이력_컬럼_여섯_개가_순서대로다(self):
        컬럼 = self.mod.DOCUMENT_PROFILES["개정이력"]["columns"][0]
        self.assertEqual(
            컬럼,
            ["버전", "개정일", "개정 사유", "개정 내용", "작성자", "승인자"],
        )

    def test_모든_프로필이_merge_columns_키를_가진다(self):
        """병합 대상이 없는 산출물은 빈 리스트를 갖는다 — 키 자체가 없으면
        create_xlsx 가 KeyError 로 죽는다."""
        for 이름, 프로필 in self.mod.DOCUMENT_PROFILES.items():
            with self.subTest(산출물=이름):
                self.assertIn("merge_columns", 프로필)
                self.assertIsInstance(프로필["merge_columns"], list)


class An02ColumnSsotTest(unittest.TestCase):
    """AN-02 컬럼 정본은 templates/AN-02-requirements-definition.md 다."""

    def setUp(self):
        self.mod = load_export_module()
        self.정본 = parse_column_ssot(
            "AN-02-requirements-definition.md", "본문 컬럼 (정본)"
        )

    def test_정본이_열_개다(self):
        self.assertEqual(
            len(self.정본), 10,
            f"AN-02 정본 컬럼이 10개가 아닙니다: {self.정본}",
        )

    def test_정본_순서가_참조_양식과_같다(self):
        self.assertEqual(self.정본, [
            "번호", "요구사항ID", "대분류", "중분류", "요구사항명",
            "요구사항 상세내용", "비고", "상태", "요구사항 근거", "변경 근거",
        ])

    def test_프로필이_정본과_같다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["요구사항정의서"]["columns"][0], self.정본
        )

    def test_분류_두_열이_병합_대상이다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["요구사항정의서"]["merge_columns"],
            ["대분류", "중분류"],
        )

    def test_폐기된_컬럼이_프로필에_남아있지_않다(self):
        프로필 = self.mod.DOCUMENT_PROFILES["요구사항정의서"]["columns"][0]
        for 폐기 in ["제안요청ID", "수용여부", "소분류", "요구내역"]:
            with self.subTest(컬럼=폐기):
                self.assertNotIn(폐기, 프로필)


class An03ColumnSsotTest(unittest.TestCase):
    """AN-03 컬럼 정본은 templates/AN-03-function-spec.md 다."""

    def setUp(self):
        self.mod = load_export_module()
        self.정본 = parse_column_ssot("AN-03-function-spec.md", "본문 컬럼 (정본)")

    def test_정본이_열_개다(self):
        self.assertEqual(len(self.정본), 10, f"AN-03 정본이 10개가 아닙니다: {self.정본}")

    def test_정본_순서가_설계와_같다(self):
        self.assertEqual(self.정본, [
            "기능ID", "대분류", "중분류", "기능명", "기능설명",
            "입력항목", "처리내용(로직)", "출력결과", "연계요구사항ID", "비고",
        ])

    def test_프로필이_정본과_같다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["기능명세서"]["columns"][0], self.정본
        )

    def test_분류_두_열이_병합_대상이다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["기능명세서"]["merge_columns"],
            ["대분류", "중분류"],
        )


class De08ColumnSsotTest(unittest.TestCase):
    """DE-08 컬럼 정본은 templates/DE-08-table-definition.md 다.

    이 문서는 역생성 전용이다 — 기존 컬럼은 고정하고 신규 컬럼만 표준용어사전
    근거로 제안한다. `구분`·`표준 판정`이 그 승인 게이트를 데이터로 남긴다.
    """

    def setUp(self):
        self.mod = load_export_module()
        self.정본 = parse_column_ssot("DE-08-table-definition.md", "본문 컬럼 (정본)")

    def test_정본이_열다섯_개다(self):
        self.assertEqual(len(self.정본), 15, f"DE-08 정본이 15개가 아닙니다: {self.정본}")

    def test_구분과_표준_판정_열이_있다(self):
        for 컬럼 in ["구분", "표준 판정", "표준 권고명", "근거", "연계기능ID"]:
            with self.subTest(컬럼=컬럼):
                self.assertIn(컬럼, self.정본)

    def test_프로필이_정본과_같다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["테이블정의서"]["columns"][0], self.정본
        )

    def test_테이블명이_병합_대상이다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["테이블정의서"]["merge_columns"], ["테이블명"]
        )


class De13ColumnSsotTest(unittest.TestCase):
    """DE-13 컬럼 정본은 templates/DE-13-unit-test-plan.md 다.

    종전에는 화면당 27개 검사기준 체크리스트 + 테스트케이스 시트, 두 벌 구조였다.
    지금은 기능명세(AN-03)·테이블정의서(DE-08)에서 케이스를 기계적으로 도출하는
    11컬럼 단일 시트다. 27개 검사기준 시트가 정말 없어졌는지는 이 테스트가 잡는다.
    """

    def setUp(self):
        self.mod = load_export_module()
        self.정본 = parse_column_ssot("DE-13-unit-test-plan.md", "본문 컬럼 (정본)")

    def test_정본이_열한_개다(self):
        self.assertEqual(len(self.정본), 11, f"DE-13 정본이 11개가 아닙니다: {self.정본}")

    def test_정본_순서가_설계와_같다(self):
        self.assertEqual(self.정본, [
            "테스트ID", "연계기능ID", "연계요구사항ID", "사전조건", "입력",
            "기대결과", "사후조건", "의존성", "테스트담당자", "수행일", "결과",
        ])

    def test_프로필이_한_시트다(self):
        """27개 검사기준 시트를 폐지했으므로 컬럼 세트는 하나다."""
        프로필 = self.mod.DOCUMENT_PROFILES["단위테스트계획서"]
        self.assertEqual(len(프로필["columns"]), 1)
        self.assertNotIn("sheet_names", 프로필)

    def test_화면_축_컬럼이_남아있지_않다(self):
        프로필 = self.mod.DOCUMENT_PROFILES["단위테스트계획서"]["columns"][0]
        for 폐기 in ["화면ID", "화면명", "단위테스트ID", "검사기준 항목", "사용자구분"]:
            with self.subTest(컬럼=폐기):
                self.assertNotIn(폐기, 프로필)

    def test_프로필이_정본과_같다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["단위테스트계획서"]["columns"][0], self.정본
        )


if __name__ == "__main__":
    unittest.main()
