import tempfile
import unittest
from pathlib import Path

import openpyxl

from helpers import (
    load_export_module,
    parse_column_ssot,
    parse_enum_ssot,
    read_docs,
)


def _다중세트(테스트: unittest.TestCase, 이름: str) -> str:
    """컬럼 세트가 둘인 임시 프로필을 등록하고 그 키를 돌려준다.

    현역 산출물 6종은 전부 세트가 하나라, 다중 세트 코드 경로를 실제 프로필로는
    검증할 수 없다. 검사 대상은 프로필 데이터가 아니라 `_best_column_set` 의 동작이므로
    임시 프로필로 고정한다.

    **모듈은 캐싱된다.** 끼운 프로필을 그대로 두면 다른 테스트
    (`test_모듈이_로드되고_산출물_프로필을_노출한다`·`test_모든_프로필_컬럼이_문서에_존재한다`)가
    실행 순서에 따라 깨진다. addCleanup 으로 반드시 되돌린다.
    """
    mod = load_export_module()
    테스트.addCleanup(mod.DOCUMENT_PROFILES.pop, 이름, None)
    mod.DOCUMENT_PROFILES[이름] = {
        "sheet_name": "세트 1 시트",
        "sheet_names": ["세트 1 시트", "세트 2 시트"],
        "columns": [
            ["레벨", "산출물 코드", "대상"],
            ["기준", "목표치", "비고"],
        ],
        "merge_columns": [],
    }
    return 이름


class LoaderTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()

    def test_모듈이_로드되고_산출물_프로필을_노출한다(self):
        """기능 축 전환(v3.0.0) 후 프로필은 5종 + 개정이력 = 6개다.

        화면 축 산출물의 프로필을 지우지 않으면 그 컬럼명을 어떤 문서도 만들지 않게 되어
        test_모든_프로필_컬럼이_문서에_존재한다 가 잡는다. 되살리는 법은 archive/README.md.
        """
        self.assertEqual(
            sorted(self.mod.DOCUMENT_PROFILES),
            sorted([
                "개정이력", "요구사항정의서", "기능명세서",
                "테이블정의서", "단위테스트계획서", "추적매트릭스",
            ]),
        )

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
        """현역 산출물 6종은 전부 컬럼 세트가 하나다 — 그래도 코드 경로는 살아 있다.

        `_best_column_set` 은 여전히 세트를 순회하며 최적 세트를 고르고, `sheet_names` 로
        세트별 시트명을 준다. archive/ 에서 다중 세트 산출물(TE-01)을 되살리면 그때
        이 경로가 다시 쓰인다. 현역 프로필로는 검증할 수 없으므로 임시 프로필을 끼워
        경로 자체를 고정한다 — 지우면 다중 세트 지원이 조용히 죽는다.
        """
        rows = [["기준", "목표치", "비고"]]
        self.assertEqual(self.mod._matched_set_index(rows, _다중세트(self, "multi-a")), 1)

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
        # 현역 6종은 세트가 하나뿐이라 임시 프로필로 검증한다 — 사유는
        # MatchedSetIndexTest.test_두번째_컬럼_세트도_구분한다 의 docstring 참조.
        names = self.mod.DOCUMENT_PROFILES[_다중세트(self, "multi-b")]["sheet_names"]
        self.assertEqual(names[0], "세트 1 시트")
        self.assertEqual(names[1], "세트 2 시트")


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
        self.정본컬럼 = parse_column_ssot(
            "AN-05-traceability-matrix.md", "본문 컬럼 (정본)"
        )

    def test_정본_플랫_헤더가_비어있지_않다(self):
        """파싱이 조용히 빈 목록을 내면 아래 두 테스트가 공허하게 통과한다."""
        self.assertGreaterEqual(
            len(self.정본컬럼), 9,
            f"정본 헤더에서 뽑은 컬럼이 9개 미만입니다: {self.정본컬럼}",
        )

    def test_기능_축_컬럼이_정본에_있다(self):
        """29컬럼 감리형에서 9컬럼 기능 축 대조기로 개편한 핵심 컬럼들이다."""
        for 컬럼 in ["기능ID", "테이블·컬럼", "테스트 수", "Pass/Fail", "누락"]:
            with self.subTest(컬럼=컬럼):
                self.assertIn(컬럼, self.정본컬럼)

    def test_폐기된_컬럼이_정본에_없다(self):
        """감리형 29컬럼 중 화면·프로그램·제안요청 축은 기능 축 개편으로 사라졌다."""
        for 폐기 in ["제안요청ID", "수용여부", "화면ID", "프로그램ID", "과업완료여부"]:
            with self.subTest(컬럼=폐기):
                self.assertNotIn(폐기, self.정본컬럼)

    def test_프로필의_모든_컬럼이_정본에_있다(self):
        """프로필에만 있는 컬럼은 아무도 만들지 않는 유령 컬럼이다."""
        for 세트번호, 컬럼들 in enumerate(
            self.mod.DOCUMENT_PROFILES["추적매트릭스"]["columns"]
        ):
            for 컬럼 in 컬럼들:
                with self.subTest(세트=세트번호, 컬럼=컬럼):
                    self.assertIn(
                        컬럼, self.정본컬럼,
                        f"프로필의 '{컬럼}' 이 AN-05 템플릿의 정본 컬럼에 없습니다 "
                        "— 정본에 추가하거나 프로필에서 빼세요",
                    )

    def test_정본의_모든_컬럼이_전체_세트에_있다(self):
        """정본에만 있는 컬럼은 xlsx 에서 재배열되지 않고 뒤로 밀린다.

        컬럼 세트가 하나뿐이므로 그 세트가 정본을 그대로 담아야 한다.
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


class SheetTitleProfileTest(unittest.TestCase):
    """참조 양식의 「개 정 이 력」 제목 행은 개정이력 프로필에만 있다."""

    def setUp(self):
        self.mod = load_export_module()

    def test_개정이력만_sheet_title_을_가진다(self):
        for 이름, 프로필 in self.mod.DOCUMENT_PROFILES.items():
            with self.subTest(산출물=이름):
                if 이름 == "개정이력":
                    self.assertEqual(프로필["sheet_title"], "개 정 이 력")
                else:
                    self.assertNotIn("sheet_title", 프로필)


class MinWidthComputationTest(unittest.TestCase):
    """_column_width 는 자동 계산 너비와 min_widths 중 큰 값을 60 이내로 돌려준다."""

    def setUp(self):
        self.mod = load_export_module()

    def test_최소_너비가_자동_계산보다_크면_최소_너비를_쓴다(self):
        self.assertEqual(self.mod._column_width(["신규"], min_width=14), 14)

    def test_자동_계산이_최소_너비보다_크면_자동_계산을_쓴다(self):
        긴값 = "가" * 20  # 전각 20자 → 40 + 여백 4 = 44
        self.assertEqual(self.mod._column_width([긴값], min_width=14), 44)

    def test_상한은_60을_넘지_않는다(self):
        아주긴값 = "가" * 50  # 100 + 4 = 104 → 60 으로 캡
        self.assertEqual(self.mod._column_width([아주긴값], min_width=0), 60)

    def test_개정이력_min_widths_값이_고정돼_있다(self):
        self.assertEqual(
            self.mod.DOCUMENT_PROFILES["개정이력"]["min_widths"],
            {"개정 사유": 14, "개정일": 12, "작성자": 12, "승인자": 12},
        )

    def test_다른_산출물_프로필에는_min_widths_가_없다(self):
        for 이름, 프로필 in self.mod.DOCUMENT_PROFILES.items():
            if 이름 == "개정이력":
                continue
            with self.subTest(산출물=이름):
                self.assertNotIn("min_widths", 프로필)


class LeftAlignColumnSsotTest(unittest.TestCase):
    """left_align 목록의 컬럼명이 그 산출물의 컬럼 정본에 실재하는지 고정한다.

    오타가 나면 실행해도 에러가 나지 않고 정렬만 조용히 빠진다 — 이게 가장
    위험한 실패 모드다. 컬럼 정본(templates/)과 양방향으로 대조해 오타를 잡는다.
    """

    _정본_위치 = {
        "개정이력": ("revision-history.md", "개정이력 컬럼 (정본)"),
        "요구사항정의서": ("AN-02-requirements-definition.md", "본문 컬럼 (정본)"),
        "기능명세서": ("AN-03-function-spec.md", "본문 컬럼 (정본)"),
        "테이블정의서": ("DE-08-table-definition.md", "본문 컬럼 (정본)"),
        "단위테스트계획서": ("DE-13-unit-test-plan.md", "본문 컬럼 (정본)"),
        "추적매트릭스": ("AN-05-traceability-matrix.md", "본문 컬럼 (정본)"),
    }

    def setUp(self):
        self.mod = load_export_module()

    def test_left_align_컬럼이_전부_정본에_있다(self):
        for 산출물, (템플릿, 절제목) in self._정본_위치.items():
            정본컬럼 = parse_column_ssot(템플릿, 절제목)
            프로필 = self.mod.DOCUMENT_PROFILES[산출물]
            for 컬럼 in 프로필.get("left_align", []):
                with self.subTest(산출물=산출물, 컬럼=컬럼):
                    self.assertIn(
                        컬럼, 정본컬럼,
                        f"'{산출물}' 의 left_align '{컬럼}' 이 정본 컬럼에 없습니다 "
                        "— 오타이거나 정본 이름이 바뀌었는데 프로필이 안 따라왔습니다",
                    )

    def test_모든_산출물이_left_align_키를_가진다(self):
        for 산출물 in self._정본_위치:
            with self.subTest(산출물=산출물):
                self.assertIn("left_align", self.mod.DOCUMENT_PROFILES[산출물])


class RevisionHistoryTitleRenderTest(unittest.TestCase):
    """실제 xlsx 를 만들어 다시 열어 제목 행·병합·고정·필터를 확인한다."""

    def setUp(self):
        self.mod = load_export_module()

    def _render(self, filename: str, markdown: str):
        tables = self.mod.parse_markdown_tables(markdown)
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "out.xlsx")
            self.mod.create_xlsx([(filename, tables)], out)
            return openpyxl.load_workbook(out)

    _개정이력_MD = (
        "## 개정이력\n\n"
        "| 버전 | 개정일 | 개정 사유 | 개정 내용 | 작성자 | 승인자 |\n"
        "|------|--------|----------|----------|--------|--------|\n"
        "| 1.0 | 2026.09.03 | 신규 | 최초 작성 | 구본승 | |\n"
    )

    def test_제목_행이_병합되고_굵게_가운데_정렬된다(self):
        wb = self._render("ACT-개정이력.md", self._개정이력_MD)
        ws = wb["개정이력"]
        self.assertEqual(ws["A1"].value, "개 정 이 력")
        self.assertTrue(ws["A1"].font.bold)
        self.assertEqual(ws["A1"].font.size, 14)
        self.assertEqual(ws["A1"].alignment.horizontal, "center")
        self.assertIn("A1:F1", [str(r) for r in ws.merged_cells.ranges])

    def test_표는_제목_다음_2행부터_시작한다(self):
        wb = self._render("ACT-개정이력.md", self._개정이력_MD)
        ws = wb["개정이력"]
        self.assertEqual(ws["A2"].value, "버전")
        self.assertEqual(ws["A3"].value, "1.0")

    def test_제목_행이_있으면_고정과_필터가_한_행_밀린다(self):
        """freeze_panes·auto_filter 가 제목 행을 빼고 헤더부터 걸려야 한다.

        빼먹으면 필터가 제목 행에 걸려 표가 아니라 제목 셀을 필터링하게 된다.
        """
        wb = self._render("ACT-개정이력.md", self._개정이력_MD)
        ws = wb["개정이력"]
        self.assertEqual(ws.freeze_panes, "A3")
        self.assertEqual(ws.auto_filter.ref, "A2:F3")

    def test_다른_산출물은_제목_행을_만들지_않는다(self):
        md = (
            "### 요구사항 명세\n\n"
            "| 번호 | 요구사항ID | 대분류 | 중분류 | 요구사항명 | 요구사항 상세내용 "
            "| 비고 | 상태 | 요구사항 근거 | 변경 근거 |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n"
            "| 1 | REQ-001 | 데이터 전처리 | 상대평가기준 | 산출 | 상세 | | 신규 "
            "| 과업지시서 BR-01 | |\n"
        )
        wb = self._render("ACT-요구사항정의서.md", md)
        ws = wb["요구사항 명세"]
        self.assertEqual(ws["A1"].value, "번호")  # 제목이 없으니 1행이 바로 헤더
        self.assertEqual(ws.freeze_panes, "A2")

    def test_개정_사유_열이_최소_너비로_렌더링된다(self):
        """값이 "신규"뿐이면 자동 계산 너비가 min_widths 보다 작아진다."""
        wb = self._render("ACT-개정이력.md", self._개정이력_MD)
        ws = wb["개정이력"]
        self.assertEqual(ws.column_dimensions["C"].width, 14)


class AlignmentRenderTest(unittest.TestCase):
    """left_align 목록 열은 좌측, 나머지 데이터 열(세로 병합 셀 포함)은 중앙 —
    실제 xlsx 를 열어 확인한다."""

    def setUp(self):
        self.mod = load_export_module()

    def test_서술_열은_좌측_나머지는_중앙(self):
        md = (
            "### 요구사항 명세\n\n"
            "| 번호 | 요구사항ID | 대분류 | 중분류 | 요구사항명 | 요구사항 상세내용 "
            "| 비고 | 상태 | 요구사항 근거 | 변경 근거 |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n"
            "| 1 | REQ-001 | 데이터 전처리 | 상대평가기준 | 산출 | 상세 | | 신규 "
            "| 과업지시서 BR-01 | |\n"
            "| 2 | REQ-002 | 데이터 전처리 | 상대평가기준 | 산출2 | 상세2 | | 신규 "
            "| 과업지시서 BR-02 | |\n"
        )
        tables = self.mod.parse_markdown_tables(md)
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "out.xlsx")
            self.mod.create_xlsx([("ACT-요구사항정의서.md", tables)], out)
            wb = openpyxl.load_workbook(out)
        ws = wb["요구사항 명세"]
        # 번호(A) 는 left_align 목록에 없다 → 중앙
        self.assertEqual(ws["A2"].alignment.horizontal, "center")
        # 요구사항명(E) 은 left_align 목록에 있다 → 좌측
        self.assertEqual(ws["E2"].alignment.horizontal, "left")
        # 요구사항 근거(I) 도 좌측 — 문장형 근거라 중앙정렬하면 읽기 어렵다
        self.assertEqual(ws["I2"].alignment.horizontal, "left")
        # 대분류(C) 는 세로 병합 셀이지만 가로는 중앙이어야 한다
        self.assertEqual(ws["C2"].alignment.horizontal, "center")
        self.assertIn("C2:C3", [str(r) for r in ws.merged_cells.ranges])


class DropdownTest(unittest.TestCase):
    """열거형 열은 텍스트가 아니라 드롭다운이어야 한다.

    사람이 xlsx 에서 손으로 채울 때 `신규`·`유지함` 처럼 정본 밖 값이 들어가면
    다음 회차의 대조가 어긋난다. 값 목록을 코드에 적으면 템플릿 정본과 갈라지므로
    parse_enum_ssot 로 대조해 갈라짐을 잡는다.
    """

    def setUp(self):
        self.mod = load_export_module()

    def test_dropdowns_길이가_columns_와_같다(self):
        """세트가 여럿인 프로필에서 인덱스가 어긋나면 다른 시트의 값이 걸린다."""
        for name, profile in self.mod.DOCUMENT_PROFILES.items():
            if "dropdowns" not in profile:
                continue
            with self.subTest(프로필=name):
                self.assertEqual(
                    len(profile["dropdowns"]), len(profile["columns"]),
                    f"{name} 의 dropdowns 가 columns 와 길이가 다릅니다 "
                    "— 세트 인덱스가 어긋나면 다른 시트의 목록이 걸립니다",
                )

    def test_드롭다운_값이_템플릿_정본과_같다(self):
        """값을 코드에 적어 두면 템플릿 정본이 바뀔 때 조용히 갈라진다.

        AN-05 `상태` 의 값 정본은 AN-02 다 — AN-05 컬럼 정본표의 셋째 칸은
        출처(`AN-02`)라 열거값이 없다. 여기서 3값을 복제하지 않는다.
        """
        정본 = {
            ("요구사항정의서", "상태"): ("AN-02-requirements-definition.md", "상태"),
            ("추적매트릭스", "상태"): ("AN-02-requirements-definition.md", "상태"),
            ("테이블정의서", "구분"): ("DE-08-table-definition.md", "구분"),
            ("테이블정의서", "표준 판정"): ("DE-08-table-definition.md", "표준 판정"),
            ("단위테스트계획서", "결과"): ("DE-13-unit-test-plan.md", "결과"),
        }
        for (프로필명, 컬럼), (템플릿, 정본컬럼) in 정본.items():
            with self.subTest(프로필=프로필명, 컬럼=컬럼):
                실제 = self.mod.DOCUMENT_PROFILES[프로필명]["dropdowns"][0][컬럼]
                기대 = parse_enum_ssot(템플릿, "본문 컬럼 (정본)", 정본컬럼)
                self.assertEqual(
                    실제, 기대,
                    f"{프로필명}.{컬럼} 드롭다운이 {템플릿} 정본과 다릅니다: "
                    f"{실제} != {기대}",
                )

    def test_드롭다운_범위가_데이터_행만_덮는다(self):
        """열 전체로 걸면 헤더까지 검사 대상이 되어 목록 밖 값이라며 막힌다."""
        md = (
            "## 요구사항 명세\n\n"
            "| 번호 | 요구사항ID | 대분류 | 중분류 | 요구사항명 | 요구사항 상세내용 "
            "| 비고 | 상태 | 요구사항 근거 | 변경 근거 |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n"
            "| 1 | REQ-001 | 가 | 나 | 산출 | 상세 | | 유지 | RFP | |\n"
            "| 2 | REQ-002 | 가 | 나 | 산출2 | 상세2 | | 유지 | RFP | |\n"
        )
        tables = self.mod.parse_markdown_tables(md)
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "out.xlsx")
            self.mod.create_xlsx([("ACT-요구사항정의서.md", tables)], out)
            wb = openpyxl.load_workbook(out)
        ws = wb["요구사항 명세"]
        범위 = [str(dv.sqref) for dv in ws.data_validations.dataValidation]
        self.assertEqual(
            범위, ["H2:H3"],
            f"드롭다운 범위가 데이터 행(H2:H3)과 다릅니다: {범위} "
            "— 헤더(1행)를 포함하면 헤더 문자열이 목록 밖 값으로 막힙니다",
        )

    def test_제목_행이_있으면_드롭다운_범위가_밀린다(self):
        """개정이력처럼 표 위 제목 행이 있는 시트는 데이터가 한 행 밀린다.

        현역 프로필 중 sheet_title 을 가진 것은 개정이력뿐이고 거기엔 드롭다운이
        없다. 그래도 row_offset 보정이 빠지면 확인요청서 같은 뒤 프로필에서
        범위가 한 행씩 어긋나므로 합성 프로필로 그 경로를 검사한다.
        """
        원본 = self.mod.DOCUMENT_PROFILES.get("개정이력")
        self.assertIsNotNone(원본, "개정이력 프로필이 없습니다")
        고친것 = dict(원본)
        고친것["dropdowns"] = [{"개정 사유": ["신규", "변경"]}]
        self.mod.DOCUMENT_PROFILES["개정이력"] = 고친것
        try:
            md = (
                "## 개정이력\n\n"
                "| 버전 | 개정일 | 개정 사유 | 개정 내용 | 작성자 | 승인자 |\n"
                "|---|---|---|---|---|---|\n"
                "| 1.0 | 2026.09.07 | 신규 | 최초 작성 | 구본승 | |\n"
            )
            tables = self.mod.parse_markdown_tables(md)
            with tempfile.TemporaryDirectory() as tmp:
                out = str(Path(tmp) / "out.xlsx")
                self.mod.create_xlsx([("ACT-요구사항정의서.md", tables)], out)
                wb = openpyxl.load_workbook(out)
            ws = wb[원본["sheet_name"]]
            범위 = [str(dv.sqref) for dv in ws.data_validations.dataValidation]
            # openpyxl 은 단일 셀 범위를 `C3:C3` 가 아니라 `C3` 로 정규화한다.
            self.assertEqual(
                범위, ["C3"],
                f"제목 행(1) + 헤더(2) 뒤 데이터는 3행부터입니다: {범위} "
                "— row_offset 보정이 빠지면 2행(헤더)부터 걸립니다",
            )
        finally:
            self.mod.DOCUMENT_PROFILES["개정이력"] = 원본


if __name__ == "__main__":
    unittest.main()
