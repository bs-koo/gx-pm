"""스킬·커맨드·템플릿·매니페스트 간 계약 테스트.

v1.5.0 에서 수작업으로 찾은 불일치 10건이 재발하지 않도록 고정한다.
실패하면 문서 편집 실수이지 로직 버그가 아니다.

**검사 범위를 절이 아니라 줄로 좁힌다.** 규칙문의 한 문장을 지키려는 검사가
낱말 존재(`assertIn("10건", 절)`)만 보면, 같은 낱말이 그 절 다른 곳에도 있어
규칙이 바뀌거나 사라져도 조용히 통과한다. 한 문장을 검사할 때는 `[^\n]*` 로
한 줄에 묶은 정규식을 쓰고, 기준어(「합계」 같은 판정의 축)를 정규식에 넣는다.
"""

import json
import re
import unittest

from helpers import (
    PLUGIN_ROOT,
    REPO_ROOT,
    archived_skill_names,
    archived_template_names,
    command_names,
    doc_label,
    read_docs,
    skill_names,
    strip_fences,
    template_names,
)


def specs_only(docs: list) -> list:
    """규칙 검사 대상 문서만 남긴다.

    CHANGELOG 는 '무엇을 고쳤는지' 설명하느라 과거의 잘못된 표기를 그대로 인용한다.
    (예: "/pm-design 참조 9곳 제거", "SCR-001 → EHR_01_01_020")
    이력 문서를 규칙으로 검사하면 고친 사실을 적었다는 이유로 실패한다.
    """
    return [(path, text) for path, text in docs if path != PLUGIN_ROOT / "CHANGELOG.md"]


class CommandNamingTest(unittest.TestCase):
    """커맨드는 자동완성에서 한 덩어리로 보여야 한다 (v2.0.0 개명)."""

    def test_모든_커맨드가_gx_접두를_쓴다(self):
        for name in sorted(command_names()):
            with self.subTest(커맨드=name):
                self.assertTrue(
                    name.startswith("gx-"),
                    "커맨드 파일명은 gx- 로 시작해야 합니다",
                )

    def test_gx_접두가_중복되지_않는다(self):
        for path, text in read_docs():
            with self.subTest(문서=doc_label(path)):
                self.assertNotIn(
                    "gx-gx-", text,
                    "일괄 치환이 두 번 적용됐습니다",
                )

    def test_접두어_없는_커맨드_참조가_남아있지_않다(self):
        구커맨드 = re.compile(r"`/(?!gx-)[가-힣]+`")
        for path, text in specs_only(read_docs()):
            with self.subTest(문서=doc_label(path)):
                남은것 = 구커맨드.findall(text)
                self.assertEqual(
                    남은것, [],
                    f"개명되지 않은 커맨드 참조: {남은것}",
                )


class SkillFrontmatterTest(unittest.TestCase):
    def test_스킬_프론트매터_name_이_디렉터리명과_같다(self):
        for skill_dir in sorted((PLUGIN_ROOT / "skills").iterdir()):
            with self.subTest(스킬=skill_dir.name):
                skill_file = skill_dir / "SKILL.md"
                self.assertTrue(skill_file.exists(), "SKILL.md 가 없습니다")
                text = skill_file.read_text(encoding="utf-8")
                match = re.match(r"^---\nname:\s*(\S+)\ndescription:", text)
                self.assertIsNotNone(match, "프론트매터 형식이 name → description 순이 아닙니다")
                self.assertEqual(match.group(1), skill_dir.name)


class CrossReferenceTest(unittest.TestCase):
    def setUp(self):
        self.docs = read_docs()
        self.specs = specs_only(self.docs)
        self.skills = skill_names()
        self.commands = command_names()
        self.templates = template_names()
        # 이력 문서(CHANGELOG)는 내린 스킬·템플릿을 이름째 인용한다.
        # 검사에서 빼는 대신 보관 목록까지 허용해, 진짜 오타는 여전히 잡히게 둔다.
        self.보관스킬 = archived_skill_names()
        self.보관템플릿 = archived_template_names()

    # "gx-pm 스킬은 allowed-tools 제한이 없다" 처럼 플러그인 이름 자체를 가리키는 문장이 있다.
    # 스킬 디렉터리가 아니므로 검사 대상이 아니다.
    스킬_아닌_이름 = {"gx-pm"}

    def test_참조된_스킬이_모두_존재한다(self):
        # 굵게·백틱뿐 아니라 **평문 참조도** 잡는다.
        # 종전 정규식은 `**name** 스킬` 과 `` `name` 스킬`` 만 봐서,
        # 평문으로만 적힌 참조 6곳이 검사 밖에 있었다.
        pattern = re.compile(r"(?<![\w-])(?:\*\*|`)?([a-z][a-z0-9-]{4,})(?:\*\*|`)?\s*스킬")
        for path, text in self.docs:
            for match in pattern.finditer(text):
                name = match.group(1)
                if name in self.스킬_아닌_이름:
                    continue
                허용 = self.skills
                if path == PLUGIN_ROOT / "CHANGELOG.md":
                    허용 = self.skills | self.보관스킬
                with self.subTest(문서=doc_label(path), 스킬=name):
                    self.assertIn(name, 허용)

    def test_백틱으로_참조된_커맨드가_모두_존재한다(self):
        # CHANGELOG 는 개명 대응표에서 구 이름을 인용하므로 검사 대상에서 뺀다.
        for path, text in self.specs:
            for match in re.finditer(r"`/(gx-[가-힣A-Za-z-]+)`", text):
                with self.subTest(문서=doc_label(path), 커맨드=match.group(1)):
                    self.assertIn(match.group(1), self.commands)

    def test_참조된_템플릿_경로가_모두_존재한다(self):
        for path, text in self.docs:
            허용 = self.templates
            if path == PLUGIN_ROOT / "CHANGELOG.md":
                허용 = self.templates | self.보관템플릿
            for match in re.finditer(r"templates/([A-Za-z0-9\-]+\.md)", text):
                with self.subTest(문서=doc_label(path), 템플릿=match.group(1)):
                    self.assertIn(match.group(1), 허용)

    def test_참조된_스킬_경로가_모두_존재한다(self):
        for path, text in self.docs:
            허용 = self.skills
            if path == PLUGIN_ROOT / "CHANGELOG.md":
                허용 = self.skills | self.보관스킬
            for match in re.finditer(r"skills/([a-z0-9-]+)/SKILL\.md", text):
                with self.subTest(문서=doc_label(path), 스킬=match.group(1)):
                    self.assertIn(match.group(1), 허용)

    def test_모든_스킬이_어느_커맨드에서든_호출된다(self):
        used = set()
        for path in (PLUGIN_ROOT / "commands").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"\*\*([a-z][a-z0-9-]{4,})\*\*", text):
                if match.group(1) in self.skills:
                    used.add(match.group(1))
        self.assertEqual(
            self.skills - used, set(),
            "커맨드에서 호출되지 않는 스킬이 있습니다 — 배선 누락입니다",
        )

    def test_모든_커맨드가_사용자에게_도달_가능하다(self):
        """스킬 배선 검사(test_모든_스킬이_어느_커맨드에서든_호출된다)의 대칭 짝.

        '참조된 커맨드가 존재하는가'만 검사하고 '존재하는 커맨드가 안내되는가'를
        검사하지 않으면, v1.5.0 처럼 발견 경로가 없는 커맨드가 생긴다.

        형제 커맨드끼리의 상호 참조는 발견 경로가 아니다. 아무 커맨드도 실행해본 적 없는
        사용자가 보는 것은 진입점 2종뿐이므로, 그 합집합이 전체 커맨드를 덮어야 한다.

        v3.0.0 에서 `/gx-testplan` 이 archive 로 내려가 진입점이 셋에서 둘로 줄었다.
        """
        진입점 = ("gx-프로젝트설정", "gx-명세일괄")
        도달가능 = set()
        for 이름 in 진입점:
            path = PLUGIN_ROOT / "commands" / f"{이름}.md"
            self.assertTrue(path.exists(), f"진입점 커맨드가 없습니다: {이름}")
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"`/(gx-[가-힣A-Za-z-]+)`", text):
                if match.group(1) != 이름:
                    도달가능.add(match.group(1))
        self.assertEqual(
            self.commands - 도달가능, set(),
            f"진입점({', '.join(진입점)})에서 안내되지 않는 커맨드가 있습니다 "
            "— 신규 사용자가 도달할 수 없습니다",
        )


class LegacyReferenceTest(unittest.TestCase):
    def setUp(self):
        self.docs = specs_only(read_docs())

    def test_존재하지_않는_pm_커맨드를_안내하지_않는다(self):
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertNotIn(
                    "/pm-", text,
                    "구 커맨드(/pm-design·/pm-test·/pm-trace) 참조가 남아 있습니다",
                )

    def test_예시_ID_가_네이밍_규칙을_따른다(self):
        # 화면ID 는 {접두}_{xx}_{xx}_{xxx}, 시나리오ID 는 {시스템코드}-TE-{순번}
        forbidden = re.compile(r"\bSCR-\d|\bSC-\d|\bSN-\d")
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertIsNone(
                    forbidden.search(text),
                    "규칙을 벗어난 예시 ID 가 있습니다 (SCR-·SC-·SN-)",
                )


class ArchiveIsolationTest(unittest.TestCase):
    """archive/ 는 보관소다. 계약 검사 대상이 아니다.

    삭제하지 않는 이유: 감리가 있는 공공 사업이 오면 화면 축 산출물을 되살린다.
    검사 대상으로 두면 옛 컬럼·옛 ID 규칙이 새 계약을 전부 깨뜨린다.
    """

    def test_archive_문서가_계약_검사에서_빠진다(self):
        보관경로 = [
            path for path, _ in read_docs()
            if "archive" in path.parts
        ]
        self.assertEqual(
            보관경로, [],
            f"archive/ 문서가 검사 대상에 들어 있습니다: {보관경로}",
        )

    def test_archive에_설명이_있다(self):
        readme = PLUGIN_ROOT / "archive" / "README.md"
        self.assertTrue(readme.exists(), "archive/README.md 가 없습니다")
        self.assertIn("되살리는 방법", readme.read_text(encoding="utf-8"))


class SurfaceTest(unittest.TestCase):
    """기능 축 전환 후 사용자에게 보이는 표면."""

    def test_커맨드가_일곱_개다(self):
        self.assertEqual(
            sorted(command_names()),
            sorted([
                "gx-프로젝트설정", "gx-명세일괄",
                "gx-요구사항정의서", "gx-기능명세서", "gx-테이블정의서",
                "gx-단위테스트계획서", "gx-추적매트릭스",
            ]),
        )

    def test_화면_축_커맨드가_남아있지_않다(self):
        for 내린것 in [
            "gx-화면목록표", "gx-프로그램정의서", "gx-인터페이스정의서",
            "gx-결함관리대장", "gx-총괄테스트계획서", "gx-시스템테스트",
            "gx-테스트결과서", "gx-감리대응", "gx-testplan",
            "gx-통합테스트시나리오",
        ]:
            with self.subTest(커맨드=내린것):
                self.assertNotIn(내린것, command_names())

    def test_spec_파이프라인이_다섯_산출물을_순서대로_부른다(self):
        text = (PLUGIN_ROOT / "commands" / "gx-명세일괄.md").read_text(encoding="utf-8")
        순서 = [
            "/gx-요구사항정의서", "/gx-기능명세서", "/gx-테이블정의서",
            "/gx-단위테스트계획서", "/gx-추적매트릭스",
        ]
        위치 = [text.find(c) for c in 순서]
        self.assertNotIn(-1, 위치, f"파이프라인에 빠진 커맨드가 있습니다: {순서}")
        self.assertEqual(위치, sorted(위치), "파이프라인 산출물이 파생 순서대로가 아닙니다")

    def test_spec_파이프라인에_게이트가_세_개다(self):
        text = (PLUGIN_ROOT / "commands" / "gx-명세일괄.md").read_text(encoding="utf-8")
        for 게이트 in ["게이트 1", "게이트 2", "게이트 3"]:
            with self.subTest(게이트=게이트):
                self.assertIn(게이트, text)
        self.assertNotIn("게이트 4", text)


class PrerequisiteRegistryTest(unittest.TestCase):
    """선행조건은 templates/prerequisites.md 가 정본이다.

    커맨드를 추가하면서 선행조건 정의를 빠뜨리면 Step 0 검사가 비어버린다.
    """

    def setUp(self):
        self.text = (PLUGIN_ROOT / "templates" / "prerequisites.md").read_text(
            encoding="utf-8"
        )
        self.listed = set(re.findall(r"^\|\s*`/(gx-[가-힣A-Za-z-]+)`\s*\|", self.text, re.M))

    def test_모든_커맨드가_레지스트리에_있다(self):
        self.assertEqual(
            command_names() - self.listed, set(),
            "선행조건이 정의되지 않은 커맨드가 있습니다",
        )

    def test_레지스트리에_없는_커맨드가_실려있지_않다(self):
        self.assertEqual(
            self.listed - command_names(), set(),
            "존재하지 않는 커맨드가 레지스트리에 있습니다",
        )

    def test_하드와_소프트_구분이_정의돼_있다(self):
        self.assertIn("하드", self.text)
        self.assertIn("소프트", self.text)
        self.assertIn("진행 중단", self.text)


class PipelineProtocolTest(unittest.TestCase):
    """파이프라인 실행 규약은 templates/pipeline-protocol.md 가 정본이다."""

    def setUp(self):
        self.text = (PLUGIN_ROOT / "templates" / "pipeline-protocol.md").read_text(
            encoding="utf-8"
        )

    def test_이월_금지_항목이_명시돼_있다(self):
        self.assertIn("이월 금지", self.text)
        self.assertIn("시안", self.text)
        self.assertIn("신규 컬럼명", self.text)

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

    def test_이월_금지_항목에_신규_컬럼명_결정이_있다(self):
        self.assertIn("신규 컬럼명 결정", self.text)
        self.assertIn("convert-ddl-to-tablespec", self.text)

    def test_화면_축_잔재가_규약에_없다(self):
        for 잔재 in ["화면ID", "화면 분리", "PG_", "generate-screen-list"]:
            with self.subTest(잔재=잔재):
                self.assertNotIn(잔재, self.text)

    def test_이월_금지_항목에_표_판정_애매성이_있다(self):
        """§이월 금지 항목 절 안에서만 검사한다.

        extract-requirements 의 '애매하면 묻는다' 는 사용자를 세우는 중단점인데
        규약의 어느 표에도 분류돼 있지 않았다. 분류되지 않으면 /gx-명세일괄 실행 중
        Claude 는 거기서 멈춰야 하는지 게이트 1 로 미뤄야 하는지 지시를 받지 못한다.
        """
        구간 = re.search(
            r"^## 이월 금지 항목$(.*?)(?=^## |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(
            구간, "pipeline-protocol.md 에서 '## 이월 금지 항목' 절을 찾지 못했습니다"
        )
        항목 = re.findall(r"^\d+\. \*\*(.+?)\*\*", 구간.group(1), re.M)
        self.assertEqual(len(항목), 4, f"이월 금지 항목이 4개가 아닙니다: {항목}")
        self.assertTrue(
            any("표 판정" in v for v in 항목),
            f"'표 판정' 애매성 중단점이 이월 금지 항목에 없습니다: {항목}",
        )

    def test_단독_파이프라인_대조표에_중단점이_모두_있다(self):
        """§이월 금지 항목의 중단점은 §단독 실행 vs 파이프라인 실행 표에도 있어야 한다.

        한쪽에만 있으면 '이월 금지' 라고 선언해 놓고 파이프라인 실행 시 어떻게
        동작하는지는 규정하지 않은 상태가 된다.
        """
        표 = re.search(
            r"^## 단독 실행 vs 파이프라인 실행$(.*?)(?=^## |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(표, "'## 단독 실행 vs 파이프라인 실행' 절을 찾지 못했습니다")
        본문 = 표.group(1)
        for 중단점 in ("시안/대안 감지 중단점", "표 판정 애매성 중단점",
                     "신규 컬럼명 결정 중단점", "입력 수집 중단점"):
            with self.subTest(중단점=중단점):
                self.assertIn(
                    중단점, 본문,
                    f"'{중단점}' 이 단독/파이프라인 대조표에 없습니다",
                )

    def test_파급_규칙이_다섯_갈래를_모두_덮는다(self):
        구간 = re.search(
            r"^## 재생성 파급 규칙$(.*?)(?=^## |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(구간, "재생성 파급 규칙 절을 찾지 못했습니다")
        본문 = 구간.group(1)
        for 항목 in [
            "요구사항ID", "요구사항 상세내용", "기능ID",
            "입력항목", "컬럼 제약",
        ]:
            with self.subTest(항목=항목):
                self.assertIn(항목, 본문)

    def test_중단_후_재개_규칙이_있다(self):
        self.assertIn("detect-existing-artifact", self.text)


class DocumentCodeTest(unittest.TestCase):
    """산출물 코드 정본은 CLAUDE.md 의 '산출물 범위' 표다."""

    def setUp(self):
        self.docs = specs_only(read_docs())

    def test_테이블정의서는_DE_08_이다(self):
        wrong = re.compile(r"테이블정의서\s*\(?DE-09|DE-09\s*테이블정의서")
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertIsNone(wrong.search(text), "테이블정의서는 DE-08 입니다")

    def test_인터페이스정의서는_DE_04_이다(self):
        wrong = re.compile(r"인터페이스정의서\s*\|\s*DE-07|DE-07\s*인터페이스정의서")
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertIsNone(wrong.search(text), "인터페이스정의서는 DE-04 입니다")


class CommandStructureTest(unittest.TestCase):
    def test_커맨드에_description_프론트매터가_있다(self):
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            with self.subTest(커맨드=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(
                    text.startswith("---\ndescription:"),
                    "description 프론트매터가 없거나 순서가 다릅니다",
                )

    def test_커맨드의_Step_번호가_중복되지_않는다(self):
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            with self.subTest(커맨드=path.name):
                numbers = re.findall(r"^### Step (\d+):", path.read_text(encoding="utf-8"), re.M)
                self.assertEqual(
                    len(numbers), len(set(numbers)),
                    f"Step 번호가 중복됩니다: {numbers}",
                )

    def test_커맨드가_선행조건_템플릿을_참조한다(self):
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            if path.stem == "gx-프로젝트설정":
                continue  # 프로파일 자체를 만드는 커맨드라 선행조건이 없다
            with self.subTest(커맨드=path.stem):
                text = path.read_text(encoding="utf-8")
                self.assertIn("templates/prerequisites.md", text)

    def test_커맨드가_파이프라인_규약을_참조한다(self):
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            if path.stem == "gx-프로젝트설정":
                continue  # 파이프라인에 들어가지 않는다
            with self.subTest(커맨드=path.stem):
                text = path.read_text(encoding="utf-8")
                self.assertIn("templates/pipeline-protocol.md", text)

    def test_커맨드가_추출_패턴을_복제하지_않는다(self):
        """gx-요구사항정의서 커맨드가 extract-requirements 의 추출 규칙을 복제하면,

        Claude 는 커맨드를 먼저 읽으므로 거기서 규칙을 다 찾았다고 여기고
        SKILL.md 의 표 인식 규칙(다섯 번째 패턴)에 도달하지 못한다 — 표 형식
        요구사항 추출 기능이 정의만 있고 런타임에는 죽는다.
        """
        path = PLUGIN_ROOT / "commands" / "gx-요구사항정의서.md"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn(
            "추출 규칙:", text,
            "커맨드가 추출 규칙을 복제하고 있습니다 — "
            "skills/extract-requirements/SKILL.md Step 2 를 참조로 바꾸세요",
        )

    def test_커맨드_이름이_모두_한국어다(self):
        """한글과 영어가 섞이면 목록에서 눈으로 찾는 비용이 올라간다.

        이 플러그인의 사용자는 공공·SI PM 이고, 커맨드 이름이 과업지시서의
        산출물명과 **글자 그대로 같은 것**이 가장 낮은 진입 장벽이다.
        `gx-spec` 하나만 영어였던 것을 `gx-명세일괄` 로 맞췄다 — 다시 영어가
        섞이면 그 이유를 여기서 다시 논의하게 된다.

        `gx-` 접두는 영문 그대로다. 그 뒤만 본다.
        """
        어긴것 = [
            path.stem
            for path in sorted((PLUGIN_ROOT / "commands").glob("*.md"))
            if not re.fullmatch(r"gx-[가-힣]+", path.stem)
        ]
        self.assertEqual(
            어긴것, [],
            f"한국어가 아닌 커맨드 이름이 있습니다: {어긴것} "
            "— 커맨드 이름은 `gx-` 뒤가 전부 한글이어야 합니다",
        )

    def test_파이프라인과_설정_커맨드가_순서를_보여준다(self):
        """목록은 가나다순으로 뜨므로 실행 순서가 드러나지 않는다.

        제일 먼저 써야 할 `/gx-프로젝트설정` 이 ㅍ이라 맨 아래로 가고,
        두 번째인 `/gx-명세일괄` 은 중간에 묻힌다. description 앞머리의
        번호가 목록에서 그 순서를 대신 알려준다.
        """
        for 커맨드, 번호 in (("gx-프로젝트설정", "①"), ("gx-명세일괄", "②")):
            with self.subTest(커맨드=커맨드):
                본문 = (PLUGIN_ROOT / "commands" / f"{커맨드}.md").read_text(
                    encoding="utf-8"
                )
                설명 = re.search(r"^description:\s*\"?(.*)$", 본문, re.M)
                self.assertIsNotNone(설명, f"{커맨드} 의 description 을 찾지 못했습니다")
                self.assertTrue(
                    설명.group(1).lstrip().startswith(번호),
                    f"{커맨드} description 이 {번호} 로 시작하지 않습니다 "
                    "— 가나다순 목록에서 실행 순서가 안 보입니다",
                )

    def test_다음_제안의_커맨드가_백틱으로_감싸져_있다(self):
        맨커맨드 = re.compile(r"(?<![`/\w])/gx-[가-힣A-Za-z-]+")
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            # H1 제목(# /gx-... — 설명)은 예외
            본문 = "\n".join(
                line for line in text.splitlines() if not line.startswith("# /")
            )
            with self.subTest(커맨드=path.stem):
                self.assertEqual(
                    맨커맨드.findall(strip_fences(본문)), [],
                    "백틱 없는 커맨드 참조가 있습니다 — 도달 가능성 검사가 놓칩니다",
                )


# v3.0.0 기능 축 전환으로 파이프라인은 `/gx-명세일괄` 하나만 남았다.
# `/gx-testplan` 과 화면 축 산출물은 archive/ 에 있다 — 되살리는 법은 archive/README.md.
PIPELINE_ARTIFACTS = {
    "gx-명세일괄": [
        "gx-요구사항정의서",
        "gx-기능명세서",
        "gx-테이블정의서",
        "gx-단위테스트계획서",
        "gx-추적매트릭스",
    ],
}

# 파이프라인별 게이트 수. 게이트는 사용자가 멈춰서 판단하는 자리이므로
# 개수가 조용히 줄면 승인 없이 지나가는 산출물이 생긴다.
PIPELINE_GATES = {"gx-명세일괄": 3}


class PipelineCommandTest(unittest.TestCase):
    """파이프라인은 묶은 산출물을 빠짐없이 만들고, PIPELINE_GATES 만큼 게이트를 유지해야 한다."""

    def _본문(self, 이름: str) -> str:
        return (PLUGIN_ROOT / "commands" / f"{이름}.md").read_text(encoding="utf-8")

    def test_파이프라인이_구성_산출물_커맨드를_모두_참조한다(self):
        for 이름, 산출물들 in PIPELINE_ARTIFACTS.items():
            if 이름 not in command_names():
                continue  # 아직 만들지 않은 파이프라인은 건너뛴다
            본문 = self._본문(이름)
            for 산출물 in 산출물들:
                with self.subTest(파이프라인=이름, 산출물=산출물):
                    self.assertIn(f"`/{산출물}`", 본문)

    def test_파이프라인에_필수_중단점이_정해진_수만큼_있다(self):
        for 이름 in PIPELINE_ARTIFACTS:
            if 이름 not in command_names():
                continue
            기대 = PIPELINE_GATES[이름]
            with self.subTest(파이프라인=이름):
                게이트 = re.findall(
                    r"^### Step \d+:.*\[필수 중단점", self._본문(이름), re.M
                )
                self.assertEqual(
                    len(게이트), 기대,
                    f"게이트가 {기대}개가 아닙니다: {게이트}",
                )

    def test_필수_중단점이_게이트_단계에만_붙어_있다(self):
        """개수만 세면 라벨을 엉뚱한 Step 으로 옮겨도 통과한다.

        게이트는 '무엇을 확정하는가' 로 이름이 붙는다 — 게이트 1 은 ID·종료기준 확정,
        게이트 2 는 기능+테이블 승인, 게이트 3 은 테스트+추적 승인이다. 저장·xlsx 처럼
        판단이 없는 단계로 라벨이 옮겨 붙으면 사용자가 멈춰서 확인할 지점이 사라지는데,
        개수는 그대로라 아무도 모른다.
        """
        for 이름 in PIPELINE_ARTIFACTS:
            if 이름 not in command_names():
                continue
            기대 = PIPELINE_GATES[이름]
            제목들 = re.findall(
                r"^### Step \d+:(.*?)\[필수 중단점\]", self._본문(이름), re.M
            )
            with self.subTest(파이프라인=이름):
                self.assertEqual(
                    len(제목들), 기대,
                    f"[필수 중단점] 이 {기대}개가 아닙니다: {제목들}",
                )
                for 순번, 제목 in enumerate(제목들, start=1):
                    self.assertIn(
                        f"게이트 {순번}", 제목,
                        f"{순번}번째 [필수 중단점] 이 '게이트 {순번}' 단계가 아닙니다 "
                        f"— 라벨이 판단 없는 단계로 옮겨졌습니다: {제목.strip()!r}",
                    )

    def test_파이프라인_산출물이_파생_순서대로_나온다(self):
        """산출물 순서는 이 기능의 전제다.

        요구사항 건수가 정해져야 기능 행이 서고, 기능의 입력항목이 있어야 컬럼과
        테스트 케이스의 근거가 생긴다. 추적매트릭스는 앞 넷을 읽는 대조기라 반드시 맨 뒤다.
        참조 '존재' 만 검사하면 순서를 뒤집어도 통과하는데, 뒤집힌 순서는
        파이프라인을 무의미하게 만든다.
        """
        for 이름, 산출물들 in PIPELINE_ARTIFACTS.items():
            if 이름 not in command_names():
                continue
            본문 = self._본문(이름)
            with self.subTest(파이프라인=이름):
                위치 = []
                for 산출물 in 산출물들:
                    자리 = 본문.find(f"`/{산출물}`")
                    self.assertNotEqual(
                        자리, -1, f"산출물 참조가 없습니다: {산출물}"
                    )
                    위치.append((자리, 산출물))
                self.assertEqual(
                    [산출물 for _, 산출물 in sorted(위치)], 산출물들,
                    "산출물이 파생 순서대로 등장하지 않습니다 "
                    f"— PIPELINE_ARTIFACTS[{이름!r}] 순서와 어긋납니다",
                )

    def test_파이프라인이_규약_템플릿을_참조한다(self):
        for 이름 in PIPELINE_ARTIFACTS:
            if 이름 not in command_names():
                continue
            with self.subTest(파이프라인=이름):
                본문 = self._본문(이름)
                self.assertIn("templates/pipeline-protocol.md", 본문)
                self.assertIn("templates/prerequisites.md", 본문)

    # 이월 금지 중단점이 gx-명세일괄.md 의 어느 Step 에서 지켜지는가.
    # 정본은 templates/pipeline-protocol.md §이월 금지 항목이고, 이 표는 그 항목들이
    # 파이프라인 본문의 어디에 내려앉는지를 적는다. 항목이 늘면 여기도 늘려야 하며,
    # 늘리지 않으면 아래 개수 대조가 잡는다.
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

    def test_gx_spec_이_이월_금지_중단점을_선언한다(self):
        """이월 금지 중단점은 `[필수 중단점]` 라벨을 달 수 없다 — 게이트 수가 틀어진다.

        라벨이 없으니 게이트 개수 정규식이 세지 못하고, 문단을 통째로 지워도 아무 테스트도
        걸리지 않는다. 문단이 사라지면 /gx-명세일괄 은 그 자리에서 멈추지 않고 다음 게이트까지
        간다 — 그때는 이미 그 판정 위에 뒤 산출물이 다 만들어진 뒤다.

        **Step 절로 범위를 좁혀서 본다.** 파일 전체에서 낱말의 존재만 세면 결속이 없다.
        `이월하지 않는다` 는 두 Step 에 각각 있으므로 한쪽을 통째로 지워도 파일 어딘가에
        남고, "그 자리에서 묻는다" 를 "게이트에서 함께 본다" 로 바꿔도 — 이 테스트가
        막으려는 바로 그 회귀인데 — 낱말과 정본 경로는 그대로라 초록으로 통과한다.
        그래서 절 안에서 낱말·정본 경로·동작 문장을 **함께** 본다.

        종전에는 화면 분리 미결정 중단점을 같은 취지로 고정하고 있었다. 화면 축이
        사라지면서 그 중단점은 소멸했고, 남은 세 항목이 같은 위험을 물려받는다.
        """
        본문 = self._본문("gx-명세일괄")
        for 항목 in self.이월금지_중단점:
            구간 = re.search(
                rf"^### Step {항목['step']}:(.*?)(?=^### |\Z)", 본문, re.M | re.S
            )
            self.assertIsNotNone(
                구간,
                f"gx-명세일괄.md 에서 '### Step {항목['step']}:' 절을 찾지 못했습니다",
            )
            절 = 구간.group(1)
            with self.subTest(step=항목["step"]):
                self.assertIn(
                    "이월하지 않는", 절,
                    f"Step {항목['step']} 에 이월 금지 선언이 없습니다 "
                    "— 이 중단점이 게이트로 밀립니다",
                )
                self.assertRegex(
                    절, r"그 자리에서 (묻는다|중단한다)",
                    f"Step {항목['step']} 에 '그 자리에서 묻는다/중단한다' 동작 문장이 "
                    "없습니다 — 선언만 있고 무엇을 하라는 지시가 없습니다",
                )
                for 낱말 in 항목["중단점"]:
                    self.assertIn(
                        낱말, 절,
                        f"'{낱말}' 중단점이 Step {항목['step']} 에 선언돼 있지 않습니다",
                    )
                for 정본 in 항목["정본"]:
                    self.assertIn(
                        정본, 절,
                        f"Step {항목['step']} 의 중단점이 판정 정본({정본})을 "
                        "그 절 안에서 가리키지 않습니다",
                    )

    def test_gx_spec_이_이월_금지_항목을_하나도_빠뜨리지_않는다(self):
        """개수를 규약에서 읽어 대조한다.

        위 테스트는 `이월금지_중단점` 표에 적힌 것만 검사하므로, 규약에 네 번째 항목이
        생겨도 표를 안 고치면 조용히 통과한다. 정본의 항목 수를 세어 묶어 둔다.
        """
        규약 = (PLUGIN_ROOT / "templates" / "pipeline-protocol.md").read_text(
            encoding="utf-8"
        )
        구간 = re.search(r"^## 이월 금지 항목$(.*?)(?=^## |\Z)", 규약, re.M | re.S)
        self.assertIsNotNone(구간, "pipeline-protocol.md 에서 §이월 금지 항목을 찾지 못했습니다")
        규약항목 = re.findall(r"^\d+\. \*\*(.+?)\*\*", 구간.group(1), re.M)
        # ID 승계 판정은 Step 2·4·7 세 곳에서 같은 이름으로 일어난다.
        # 평탄화한 리스트 길이로 규약 항목 수와 비교하면 중복이 초과로 잡힌다.
        선언된것 = sorted(
            {낱말 for 항목 in self.이월금지_중단점 for 낱말 in 항목["중단점"]}
        )
        self.assertEqual(
            len(선언된것), len(규약항목),
            f"규약의 이월 금지 항목 {len(규약항목)}개 중 gx-명세일괄.md 가 선언하는 것은 "
            f"{len(선언된것)}개입니다: 규약={규약항목} / 선언={선언된것}",
        )
        for 낱말 in 선언된것:
            with self.subTest(중단점=낱말):
                self.assertTrue(
                    any(낱말 in 항목 for 항목 in 규약항목),
                    f"'{낱말}' 이 규약의 이월 금지 항목에 없습니다: {규약항목}",
                )

    def test_gx_spec_이_프로파일_부재를_하드로_막는다(self):
        """실행 중 프로파일 없이 `/gx-명세일괄` 을 부르자 파이프라인이 종료하지 않고

        프로파일을 그 자리에서 만들었다. `/gx-프로젝트설정` 의 `[필수 중단점]` 3개
        (유형 선택·기본 정보·설정 승인)가 통째로 사라졌고, 유형은 사용자가 아니라
        모델이 판정했다. 유형이 틀리면 5종 전부가 틀린다.

        규약(`templates/prerequisites.md`)에는 프로파일이 하드 선행이라고 적혀 있었지만
        Step 0 이 그걸 선언하는지 보는 검사가 없었다. 이월 금지 중단점은
        test_gx_spec_이_이월_금지_중단점을_선언한다 가 절 단위로 잡는데,
        하드 선행 중단은 잡는 것이 없었다.

        Step 0 절로 범위를 좁혀서 본다 — 파일 어딘가에 낱말이 있는 것으로는
        그 절이 종료를 지시한다는 보장이 안 된다.
        """
        본문 = self._본문("gx-명세일괄")
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간, "gx-명세일괄.md 에서 '### Step 0:' 절을 찾지 못했습니다")
        절 = 구간.group(1)

        self.assertIn(
            "안내 후 종료", 절,
            "Step 0 에 프로파일 부재 시 종료 지시가 없습니다 "
            "— 파이프라인이 프로파일을 대신 만들게 됩니다",
        )
        self.assertIn(
            "`/gx-프로젝트설정`", 절,
            "Step 0 이 선행 커맨드를 백틱으로 안내하지 않습니다",
        )
        self.assertIn(
            "templates/prerequisites.md", 절,
            "Step 0 이 하드 선행 정본을 가리키지 않습니다",
        )
        self.assertRegex(
            절, r"대신 만들지 않는다",
            "Step 0 에 '프로파일을 여기서 만들지 않는다' 는 금지가 없습니다 "
            "— 종료 지시만으로는 채번 문장에 끌려갑니다",
        )

    def test_gx_spec_의_채번_질문이_프로파일_존재를_전제한다(self):
        """Step 0 은 '프로파일이 없으면 종료' 와 '채번이 없으면 여기서 묻고 저장' 을

        함께 담는다. 뒤 문장이 조건 없이 적히면 '프로파일 항목이 없으면 여기서 채운다'
        로 확장 해석되어 앞 문장을 무력화한다. 실제로 그렇게 읽힌 실행이 있었다.
        지시문(하라)이 금지문(하지 마라)보다 행동을 끌어당기므로, 조건을 붙여 둔다.
        """
        본문 = self._본문("gx-명세일괄")
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간, "gx-명세일괄.md 에서 '### Step 0:' 절을 찾지 못했습니다")
        절 = 구간.group(1)

        채번문장 = re.search(r"^\*\*(.*?채번.*?|.*?idNaming.*?)\*\*", 절, re.M)
        self.assertIsNotNone(
            채번문장, "Step 0 에서 채번 규칙을 다루는 굵은 문장을 찾지 못했습니다"
        )
        self.assertRegex(
            채번문장.group(1), r"프로파일은 있는데|프로파일이 있고",
            "채번 질문이 프로파일 존재를 전제하지 않습니다 "
            f"— 프로파일 전체를 여기서 채우는 것으로 읽힙니다: {채번문장.group(1)!r}",
        )
        self.assertIn(
            "이 항목만 여기서 채운다", 절,
            "다른 프로파일 항목까지 채우지 말라는 한정이 없습니다",
        )

    def test_gx_spec_이_종료_화면을_리터럴로_준다(self):
        """"안내 후 종료한다" 라는 문장만으로는 실행이 종료하지 않는다.

        v3.2.0 은 그 문장을 갖고도 프로파일을 대신 만들었다 — 규칙문은 설치본에
        그대로 있었는데 실행이 안 지켰다. 안내 문구를 주지 않으면 실행이 자기
        나름대로 안내하다가 "이왕이면 만들어주자" 로 간다. 완성된 출력 블록은
        재해석할 여지가 없고, 모델이 자기 출력으로 종료를 선언하게 만든다.

        기존 리터럴 4개는 test_gx_spec_이_프로파일_부재를_하드로_막는다 가 지킨다.
        이 테스트는 그것을 교체하지 않고 **추가**했는지를 본다.
        """
        본문 = self._본문("gx-명세일괄")
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간, "gx-명세일괄.md 에서 '### Step 0:' 절을 찾지 못했습니다")
        절 = 구간.group(1)
        self.assertIn(
            "/gx-명세일괄 을 종료합니다", 절,
            "프로파일 부재 시 출력할 종료 화면이 리터럴로 없습니다 "
            "— 문장으로만 적은 종료 지시는 v3.2.0 에서 지켜지지 않았습니다",
        )
        self.assertIn(
            "A 신규구축", 절,
            "종료 화면이 프로젝트 유형 4개를 보여주지 않습니다 "
            "— 무엇을 건너뛰게 되는지가 사용자에게 안 보입니다",
        )

    def test_질문_정책이_세_층으로_갈린다(self):
        """상한을 층 구분 없이 걸면 이월 금지 항목과 충돌한다.

        §이월 금지 항목은 "절대 게이트로 미루지 않는다" 인데, 상한 초과분을
        확인요청서(게이트 3 산출물)로 올리면 정확히 그 금지 행위가 된다.
        정책 위반 감지도 그 넷의 권장안을 정하는 질문이라 면제 쪽이다 —
        중단점은 면제인데 그걸 푸는 질문이 상한에 걸리면 중단점이 못 선다.
        """
        본문 = (
            PLUGIN_ROOT / "templates" / "pipeline-protocol.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^## 질문 정책$(.*?)(?=^## |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간, "pipeline-protocol.md 에 §질문 정책 절이 없습니다")
        절 = 구간.group(1)
        self.assertIn("면제", 절, "이월 금지 항목을 상한에서 면제한다는 규칙이 없습니다")
        self.assertRegex(
            절, r"정책 위반 감지[^\n]*면제|면제[^\n]*정책 위반 감지"
            r"|\*\*정책 위반 감지도 면제 쪽이다",
            "정책 위반 감지가 면제인지 상한 대상인지 정해져 있지 않습니다",
        )
        self.assertIn(
            "5번째 이월 금지 항목이 새로 생기는 것이 아니다", 절,
            "항목 수가 4개 그대로라는 못박음이 없습니다 — 이월 금지 4개 계약이 흔들립니다",
        )

    def test_애매성_상한에_초과_동작이_있다(self):
        """상한만 정하고 초과 동작을 안 적으면 구현이 스스로 정한다.

        추정해서 채우면 정직도가 무너지고, 이월 금지 4개를 확인요청서로 올리면
        규약 위반이다. 6번째부터 무엇을 하는지 못박아야 한다.
        """
        본문 = (
            PLUGIN_ROOT / "templates" / "pipeline-protocol.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^## 질문 정책$(.*?)(?=^## |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간)
        절 = 구간.group(1)
        self.assertIn("6번째", 절, "상한 초과 시 동작이 없습니다")
        self.assertIn(
            "추정해서 채우지 않는다", 절,
            "초과분을 추정으로 채우지 말라는 금지가 없습니다",
        )
        self.assertIn(
            "[미확정]", 절,
            "초과분의 행선지(`[미확정]` + 확인요청서)가 없습니다",
        )

    def test_상한이_강제가_아니라_관측임을_밝힌다(self):
        """프롬프트 플러그인에는 카운터 원시연산이 없다.

        `강제한다` 고 적으면 지켜진다고 오해하게 된다 — 이 레포에는 규칙문은
        있는데 실행이 안 지킨 전례가 있다(gx-명세일괄 프로파일 하드 중단).
        묶기로 회피되고 중복 출력도 막지 못한다는 것을 밝혀야, 3차 시험에서
        결정 기록으로 실효를 판정할 근거가 생긴다.
        """
        본문 = (
            PLUGIN_ROOT / "templates" / "pipeline-protocol.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^## 질문 정책$(.*?)(?=^## |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간)
        절 = 구간.group(1)
        self.assertIn("관측", 절)
        self.assertIn(
            "묶으면", 절,
            "카운터가 묶기로 회피된다는 한계가 적혀 있지 않습니다",
        )
        self.assertIn("[애매성 3/5]", 절, "카운터 출력 형식 예시가 없습니다")

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

    def test_세_층_표현이_대화_층으로_한정된다(self):
        """서두의 '세 층'이 무한정이면 네 번째(파일) 층과 층 수가 안 맞는다.

        확인요청서 층은 대화가 아니라 파일이다. 서두가 '대화로 묻는' 한정
        없이 '세 층'이라고만 하면, 이 절에 실제로는 네 층(대화 셋 + 파일
        하나)이 있다는 사실과 충돌한다 — 뒤에 읽는 사람이 어느 쪽을 믿을지
        모르게 된다.
        """
        본문 = (
            PLUGIN_ROOT / "templates" / "pipeline-protocol.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^## 질문 정책$(.*?)(?=^## |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간)
        절 = 구간.group(1)
        서두 = re.search(r"^질문은[^\n]*세 층[^\n]*$", 절, re.M)
        self.assertIsNotNone(
            서두, "질문 정책 서두에서 '질문은 ... 세 층' 문장을 찾지 못했습니다",
        )
        self.assertIn(
            "대화", 서두.group(0),
            "'세 층' 문장이 대화 층으로 한정돼 있지 않습니다 "
            "— 네 번째(파일) 층과 합치면 절 안의 층 수가 안 맞습니다",
        )

    def test_정책_층이_Step_0_에_있고_프로파일에_저장된다(self):
        """저장처가 없으면 재개할 때 정책을 다시 묻게 된다.

        「통과한 게이트를 다시 세우지 않는다」와 어긋난다. `.dev` 결정 기록은
        훅이 쓰는 런타임 파일이라 helpers.read_docs 가 계약 검사에서 제외하므로
        저장처가 될 수 없다.
        """
        본문 = self._본문("gx-명세일괄")
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간)
        절 = 구간.group(1)
        self.assertIn("정책 층", 절, "Step 0 에 정책 층이 없습니다")
        self.assertIn(
            "templates/project-profile-schema.md", 절,
            "정책의 저장 위치를 가리키지 않습니다",
        )
        스키마 = (
            PLUGIN_ROOT / "templates" / "project-profile-schema.md"
        ).read_text(encoding="utf-8")
        for 필드 in (
            "splitCriterion", "assumptionFill", "testDensity",
            "nonFunctionalVerification",
        ):
            with self.subTest(필드=필드):
                self.assertIn(필드, 스키마, f"policy.{필드} 가 스키마에 없습니다")
        self.assertRegex(
            스키마, r"`testDensity`[^\n]*경고 임계값",
            "testDensity 가 하한 패딩인지 경고 임계값인지 정해져 있지 않습니다 "
            "— 하한 패딩이면 근거 없는 케이스가 생겨 `[가정]` 규율과 충돌합니다",
        )

    def test_확인요청서_반영_경로가_배선돼_있다(self):
        """스킬만 만들고 커맨드가 안 부르면 도달할 수 없다.

        커맨드를 늘리지 않는 대신 Step 0-2 의 기존 산출물 분기에 선택지를 얹었다.
        선택지 문구가 없으면 사용자가 이 경로를 찾을 방법이 없고, 스킬 굵게 표기가
        없으면 도달 가능성 검사(test_문서의_스킬_경로가_모두_존재한다)가 놓친다.
        """
        본문 = self._본문("gx-명세일괄")
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간, "Step 0 절을 찾지 못했습니다")
        절 = 구간.group(1)
        self.assertIn(
            "**apply-confirmations**", 절,
            "Step 0 이 apply-confirmations 스킬을 굵게 부르지 않습니다",
        )
        self.assertIn(
            "확인요청서 반영하고 이어가기", 절,
            "확인요청서 반영 선택지가 없습니다 — 사용자가 이 경로를 찾을 수 없습니다",
        )

    def test_확인요청서_임계치가_정본에_있다(self):
        """임계치를 정하지 않으면 매번 다른 기준으로 파일이 생긴다."""
        양식 = (
            PLUGIN_ROOT / "templates" / "confirmation-request.md"
        ).read_text(encoding="utf-8")
        self.assertIn("6건 이상", 양식, "확인요청서 생성 임계치가 없습니다")
        self.assertIn(
            "개정이력", 양식,
            "개정이력을 붙이는지 안 붙이는지가 정해져 있지 않습니다 "
            "— revision-history 는 5종의 첫 시트를 개정이력으로 정합니다",
        )
        본문 = self._본문("gx-명세일괄")
        self.assertIn(
            "templates/confirmation-request.md", 본문,
            "gx-명세일괄 이 확인요청서 양식 정본을 가리키지 않습니다",
        )

    def test_반영_무응답이_묵시적_승인이다(self):
        """무응답에서 멈추면 파이프라인이 사람을 기다린다.

        착수 전에는 답할 수 없는 것이 많아 무응답이 정상이다. 이 규칙이 없으면
        확인요청서가 파이프라인을 막는 새 관문이 된다 — 없애려던 문제 그 자체다.
        """
        스킬 = (
            PLUGIN_ROOT / "skills" / "apply-confirmations" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("묵시적 승인", 스킬)
        self.assertRegex(
            스킬, r"무응답도 정상 종료",
            "무응답으로도 끝난다는 규칙이 없습니다",
        )
        self.assertIn(
            "templates/pipeline-protocol.md", 스킬,
            "파급 규칙 정본을 가리키지 않습니다 — 여기서 복제하면 두 벌이 갈립니다",
        )

    def test_게이트마다_저장한다(self):
        """저장이 Step 10 한 곳뿐이면 중간에 끊겼을 때 승인분이 사라진다.

        `templates/pipeline-protocol.md` §중단 후 재개는 "이미 저장된 산출물은
        그대로 둔다" 고 정해두었는데, 정작 저장이 맨 끝에만 있어 규약이 헛돌았다.
        MCP 를 Step 1 에서 하드로 막던 것도 이 손실 때문이었다.

        "게이트마다 저장한다" 한 줄을 어딘가에 적는 것으로는 통과하지 않도록
        게이트 세 절을 각각 본다 — 한 절만 고치고 나머지를 빠뜨리는 것이
        이 레포가 반복해 겪은 형태다.
        """
        본문 = self._본문("gx-명세일괄")
        for 절제목 in ("Step 3: 게이트 1", "Step 6: 게이트 2", "Step 9: 게이트 3"):
            with self.subTest(게이트=절제목):
                구간 = re.search(
                    rf"^### {re.escape(절제목)}(.*?)(?=^### |\Z)", 본문, re.M | re.S
                )
                self.assertIsNotNone(구간, f"{절제목} 절을 찾지 못했습니다")
                self.assertRegex(
                    구간.group(1), r"파일로 저장한다",
                    f"{절제목} 통과 후 저장한다는 지시가 없습니다",
                )

    def test_생성_표지의_자리가_정해져_있다(self):
        """표지가 없으면 파일 존재만으로 게이트 통과를 판정할 수 없다.

        단독 커맨드도 같은 파일을 만들기 때문이다. 자리를 안 정하면 게이트 화면에만
        찍히고 파일에 안 남아 다음 세션이 못 읽는다.
        """
        본문 = self._본문("gx-명세일괄")
        구간 = re.search(r"^## 생성 표지$(.*?)(?=^## |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간, "gx-명세일괄.md 에 §생성 표지 절이 없습니다")
        절 = 구간.group(1)
        self.assertIn(
            "개정이력", 절,
            "표지 자리가 `## 개정이력` 기준으로 명시돼 있지 않습니다",
        )
        self.assertIn("게이트 1 통과", 절, "표지 문구 예시가 없습니다")

    def test_중간_산출물은_백업_대상이_아니다(self):
        """게이트 저장분을 백업하면 같은 날짜 파일명이 진짜 직전 버전을 덮어쓴다.

        `reconcile-ids` Step 1 은 그 백업을 ID 승계의 유일한 기준선으로 읽으므로,
        반쯤 만들다 만 산출물이 기준선이 되면 승계가 통째로 어긋난다.
        데이터 손실 경로라 순번 규칙도 함께 본다.
        """
        스킬 = (
            PLUGIN_ROOT / "skills" / "detect-existing-artifact" / "SKILL.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(
            r"^#### 2\. 새로쓰기 선택 시$(.*?)(?=^#### |\Z)", 스킬, re.M | re.S
        )
        self.assertIsNotNone(구간, "새로쓰기 절을 찾지 못했습니다")
        절 = 구간.group(1)
        self.assertIn(
            "게이트", 절,
            "게이트 통과 표지가 붙은 중간 산출물을 백업에서 빼라는 규칙이 없습니다",
        )
        self.assertIn(
            "_2", 절,
            "같은 날 두 번 백업할 때의 순번 규칙이 없습니다 — 앞 백업을 덮어씁니다",
        )

    def test_gx_spec_step0가_하위_절로_갈린다(self):
        """Step 0 이 한 덩어리면 종료 지시 뒤 문장들이 이어서 읽힌다.

        프로파일 검사·산출물 감지·채번이 같은 절에 붙어 있으면, 종료해야 할
        자리에서 실행이 계속 읽어 내려간다. 하위 절로 끊어 각각의 시작과 끝을
        분명히 한다.

        `#### ` 은 `^### ` 정규식에 안 걸리므로 Step 0 절 범위는 그대로다 —
        기존 두 테스트(프로파일 하드 중단 · 채번 질문 전제)가 계속 통과한다.
        """
        본문 = self._본문("gx-명세일괄")
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간, "gx-명세일괄.md 에서 '### Step 0:' 절을 찾지 못했습니다")
        하위 = re.findall(r"^#### (0-\d)\. ", 구간.group(1), re.M)
        self.assertEqual(
            하위, sorted(하위),
            f"Step 0 하위 절의 번호 순서가 어긋납니다: {하위}",
        )
        self.assertGreaterEqual(
            len(하위), 3,
            f"Step 0 이 하위 절로 갈리지 않았습니다: {하위} "
            "— 프로파일 검사·산출물 감지·채번은 각각 독립된 절이어야 합니다",
        )


class VersionConsistencyTest(unittest.TestCase):
    """버전과 개수 표기가 10개 지점에 흩어져 있어 한쪽만 갱신되기 쉽다.

    v1.4.0 에서 marketplace.json 과 README 배지가 실제로 누락됐다.
    """

    def setUp(self):
        self.plugin_json = json.loads(
            (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.changelog = (PLUGIN_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.skill_count = len(skill_names())
        self.command_count = len(command_names())

    def test_모든_매니페스트의_버전이_같다(self):
        version = self.plugin_json["version"]
        self.assertEqual(self.marketplace["plugins"][0]["version"], version)
        self.assertEqual(re.search(r"version-([\d.]+)-blue", self.readme).group(1), version)
        self.assertEqual(re.search(r"## \[([\d.]+)\]", self.changelog).group(1), version)

    def test_README_배지가_실제_스킬_커맨드_수와_같다(self):
        self.assertEqual(
            int(re.search(r"skills-(\d+)-green", self.readme).group(1)), self.skill_count
        )
        self.assertEqual(
            int(re.search(r"commands-(\d+)-orange", self.readme).group(1)), self.command_count
        )

    def test_README_디렉토리_트리의_개수가_실제와_같다(self):
        """배지는 test_README_배지가_실제_스킬_커맨드_수와_같다 가 지키지만,

        '## 디렉토리 구조' 트리의 commands/·skills/ 주석 숫자는 어떤 테스트도
        보지 않아 배지가 고쳐진 뒤에도(v1.4.0~v2.0.0 T7 이전) 11개/22개로
        방치됐었다. 트리 자체를 다시 세지는 않는다 — 주석 숫자만 실제 개수와
        비교해, 파일을 추가/삭제하고 이 주석을 깜빡했을 때 여기서 걸리게 한다.
        """
        commands_match = re.search(r"commands/\s*#\s*(\d+)개 커맨드", self.readme)
        self.assertIsNotNone(
            commands_match,
            "README '## 디렉토리 구조' 트리에서 'commands/ ... #N개 커맨드' 주석을 찾지 못했습니다",
        )
        self.assertEqual(
            int(commands_match.group(1)),
            self.command_count,
            "README 디렉토리 트리의 commands/ 개수 주석이 실제 커맨드 수와 다릅니다 "
            "— 커맨드를 추가/삭제했다면 트리의 주석과 파일 목록도 함께 갱신하세요",
        )

        skills_match = re.search(r"skills/\s*#\s*(\d+)개 스킬", self.readme)
        self.assertIsNotNone(
            skills_match,
            "README '## 디렉토리 구조' 트리에서 'skills/ ... #N개 스킬' 주석을 찾지 못했습니다",
        )
        self.assertEqual(
            int(skills_match.group(1)),
            self.skill_count,
            "README 디렉토리 트리의 skills/ 개수 주석이 실제 스킬 수와 다릅니다 "
            "— 스킬을 추가/삭제했다면 트리의 주석과 디렉터리 목록도 함께 갱신하세요",
        )

    def test_설명문의_스킬_커맨드_수가_실제와_같다(self):
        for label, description in [
            ("plugin.json", self.plugin_json["description"]),
            ("marketplace.json", self.marketplace["plugins"][0]["description"]),
        ]:
            with self.subTest(매니페스트=label):
                self.assertEqual(
                    int(re.search(r"(\d+)개 스킬", description).group(1)), self.skill_count
                )
                self.assertEqual(
                    int(re.search(r"커맨드 (\d+)개", description).group(1)), self.command_count
                )


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

    def test_가정과_미확정이_2단_판정으로_갈린다(self):
        """옛 분류(`항목`/`제약`)는 무엇이 비었는가를 갈랐다.

        그것으로는 「지어내도 되는 값」과 「발주기관만 아는 값」이 구별되지 않아,
        표본 최소 수 같은 판정 기준값을 관행값으로 채우는 것을 막지 못했다.
        새 분류는 **누가 정할 값인가**를 가른다.

        표만 있고 판정 순서가 없으면 실행이 순서를 스스로 정하므로 순서 문자열도 본다.
        """
        for 종류 in ("[가정]", "[미확정]"):
            with self.subTest(종류=종류):
                self.assertIn(종류, self.text, f"{종류} 정의가 없습니다")
        self.assertIn(
            "RFP 가 그 값을 줬는가", self.text,
            "2단 판정의 1번(RFP 가 값을 줬는가)이 없습니다",
        )
        self.assertRegex(
            self.text, r"없으면 요구사항을 구현할 수 없는가",
            "2단 판정의 2번(없으면 구현 불가인가)이 없습니다 "
            "— 이것이 발주기관 몫과 설계 재량을 가르는 기준입니다",
        )
        self.assertIn(
            "RFP 미규정", self.text,
            "`[가정]` 근거에 `RFP 미규정` 을 적으라는 규칙이 없습니다 "
            "— 그것이 2단 판정을 통과했다는 증거입니다",
        )

    def test_가정_표식이_세_홉을_관통한다(self):
        """AN-03 에만 적으면 DE-13 이 무표식 값에서 경계를 뽑는다.

        제약의 최종 승자는 DE-08 이므로(generate-unit-test-plan Step 2),
        AN-03 비고의 태그는 DE-08 길이 열에서 숫자만 남기고 끊긴다. 그러면
        감리에 나가는 DE-13 에서 가정값 검증과 RFP 값 검증이 구별되지 않는다.

        한 홉만 적혀 있어도 통과하지 않도록 세 자리를 각각 본다.
        """
        구간 = re.search(
            r"^### 표식은 세 홉을 관통한다$(.*?)(?=^#{2,3} |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(구간, "§표식은 세 홉을 관통한다 절을 찾지 못했습니다")
        절 = 구간.group(1)
        for 홉, 자리 in (("AN-03", "입력항목"), ("DE-08", "근거"), ("DE-13", "입력")):
            with self.subTest(홉=홉):
                self.assertIn(홉, 절, f"{홉} 홉이 표식 경로에 없습니다")
                self.assertIn(자리, 절, f"{홉} 의 표식 자리({자리})가 없습니다")

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

    def test_미확정_제약만_자동보강에서_빠진다(self):
        """자동 보강을 두 갈래로 가르지 않으면 배선이 반쪽이 된다.

        옛 규칙은 "제약이 비면 보강하지 않는다" 였다. 그 전제는 "제약이 비면
        근거가 없다" 였는데, 2단 판정이 RFP 미규정 항목에 근거를 만들면서
        전제가 바뀌었다. `[가정]` 은 보강하고 `[미확정]` 은 보강하지 않는다.

        한쪽만 적혀 있으면 실행이 나머지를 스스로 정하므로 둘 다 본다.
        DE-13 밀도가 이 갈래에 달려 있다 — `[가정]` 을 보강하지 않으면 경계
        케이스가 안 나와 밀도가 그대로다.
        """
        구간 = re.search(
            r"^## \[미확정\] 제약은 자동 보강 대상이 아니다$(.*?)(?=^## |\Z)",
            self.text, re.M | re.S,
        )
        self.assertIsNotNone(
            구간, "§[미확정] 제약은 자동 보강 대상이 아니다 절을 찾지 못했습니다"
        )
        절 = 구간.group(1)
        self.assertIn("지어내", 절, "보강하지 않는 이유(지어내기)가 없습니다")
        self.assertRegex(
            절, r"\[가정\][^\n]*\|[^\n]*한다",
            "`[가정]` 제약을 보강한다는 갈래가 없습니다 — 밀도가 오르지 않습니다",
        )
        self.assertRegex(
            절, r"\[미확정\][^\n]*\|[^\n]*하지 않는다",
            "`[미확정]` 제약을 보강하지 않는다는 갈래가 없습니다",
        )
        self.assertNotIn(
            "임시확정", 절,
            "값을 대신 정하는 갈래가 남아 있습니다 — v4.0.0 은 3차 미응답을 "
            "관행값으로 채우지 않고 `[미확정]` 으로 남긴 뒤 최종본을 보류합니다",
        )

    def test_옛_확인필요_표기가_남아_있지_않다(self):
        """정본만 새 표기로 바꾸고 실행부에 옛 표기가 남으면 둘이 갈린다.

        이 플러그인이 반복해 겪은 형태다 — 규칙은 정본에 있고 실행부가 안 한다.
        `read_docs()` 범위(archive·.dev·tests/fixtures 제외) 전체를 훑는다.
        `CHANGELOG.md` 만 예외다: 과거 기록이라 그때의 표기가 남는 것이 맞다.
        """
        남은 = [
            path.relative_to(REPO_ROOT)
            for path, text in read_docs()
            if path.name != "CHANGELOG.md" and "[확인필요" in text
        ]
        self.assertEqual(
            남은, [],
            f"옛 `[확인필요]` 표기가 남아 있습니다: {남은} "
            "— `[가정]`/`[미확정]` 2단 판정으로 바꾸세요",
        )

    def test_가정_표식을_세_홉의_실행부가_모두_안다(self):
        """정본에 경로를 그려도 각 홉의 실행부가 모르면 표식이 끊긴다.

        AN-03 비고에만 적히면 DE-08 `길이` 열에는 숫자만 남고, 제약의 최종 승자가
        DE-08 이라 그 뒤로는 되살릴 자리가 없다. DE-13 은 무표식 값에서 경계를
        뽑고, 감리에서 가정값 검증이 RFP 값 검증처럼 보인다.

        한 홉만 알아도 통과하지 않도록 세 파일을 각각 본다.
        """
        for 파일 in (
            PLUGIN_ROOT / "templates" / "DE-08-table-definition.md",
            PLUGIN_ROOT / "templates" / "DE-13-unit-test-plan.md",
            PLUGIN_ROOT / "skills" / "convert-ddl-to-tablespec" / "SKILL.md",
        ):
            with self.subTest(파일=파일.name):
                text = 파일.read_text(encoding="utf-8")
                self.assertIn(
                    "[가정]", text,
                    f"{파일.name} 이 `[가정]` 표식을 다루지 않습니다 "
                    "— 이 홉에서 표식이 끊깁니다",
                )

    def test_AN_03_이_근거_정본을_참조한다(self):
        an03 = (PLUGIN_ROOT / "templates" / "AN-03-function-spec.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("templates/evidence-rules.md", an03)
        self.assertIn("[미확정]", an03)
        self.assertIn("[가정]", an03)

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

    def test_기능명세_스킬이_가정과_미확정을_모두_안다(self):
        """정본만 고치고 실행부를 안 고치면 규칙이 돌지 않는다."""
        스킬 = (
            PLUGIN_ROOT / "skills" / "generate-function-spec" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for 종류 in ("[가정]", "[미확정]"):
            with self.subTest(종류=종류):
                self.assertIn(종류, 스킬)
        self.assertIn("templates/evidence-rules.md", 스킬)
        self.assertIn(
            "RFP 미규정", 스킬,
            "`[가정]` 근거에 `RFP 미규정` 을 적으라는 지시가 실행부에 없습니다",
        )
        for 집계 in ("근거 가용도", "[미확정] 제약"):
            with self.subTest(집계=집계):
                self.assertIn(집계, 스킬)

    def test_단위테스트_스킬이_제약_미상을_보강에서_제외한다(self):
        """제약이 없는데 경계값을 만들면 지어낸 테스트가 된다.

        v3.0.0 Step 6 은 '제약이 있는데 케이스가 없으면' 만 보강했다. 제약이 아예
        없는 경우는 정상+미입력 2건에서 멈추는데 '정상 케이스만' 에도 안 걸려
        조용히 통과했다.
        """
        스킬 = (
            PLUGIN_ROOT / "skills" / "generate-unit-test-plan" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("[미확정] 제약", 스킬)
        self.assertIn("templates/evidence-rules.md", 스킬)
        구간 = re.search(
            r"^### Step 6: 충분성 검증$(.*?)(?=^### |\Z)", 스킬, re.M | re.S
        )
        self.assertIsNotNone(구간, "generate-unit-test-plan 의 Step 6 절을 찾지 못했습니다")
        절 = 구간.group(1)
        self.assertIn("[미확정] 제약", 절)
        self.assertRegex(
            절, r"보강하지 않는다|지어내",
            "Step 6 에 '[미확정] 제약은 보강하지 않는다' 는 지시가 없습니다",
        )
        self.assertRegex(
            절, r"\[가정\].*보강",
            "Step 6 이 `[가정]` 제약을 보강한다고 말하지 않습니다 "
            "— 이 갈래가 없으면 DE-13 밀도가 오르지 않습니다",
        )
        self.assertIn(
            "[가정:", 절,
            "보강한 케이스에 `[가정:N]` 표식을 붙이라는 지시가 없습니다 "
            "— 감리에서 RFP 값 검증과 구별되지 않습니다",
        )

    def test_게이트2가_근거_집계를_보여준다(self):
        """계측하고 안 보여주면 계측하지 않은 것과 같다.

        Step 절로 범위를 좁혀서 본다 — 파일 어딘가에 낱말이 있는 것으로는
        게이트 화면에 실린다는 보장이 안 된다.
        """
        본문 = (PLUGIN_ROOT / "commands" / "gx-명세일괄.md").read_text(encoding="utf-8")
        구간 = re.search(
            r"^### Step 6: 게이트 2(.*?)(?=^### |\Z)", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "gx-명세일괄.md 에서 Step 6(게이트 2) 절을 찾지 못했습니다")
        for 항목 in ("근거 가용도", "[가정]", "[미확정]"):
            with self.subTest(항목=항목):
                self.assertIn(항목, 구간.group(1), f"게이트 2 에 '{항목}' 이 없습니다")
        self.assertIn("templates/evidence-rules.md", 구간.group(1))

    def test_게이트3이_미확정_제약을_보여준다(self):
        본문 = (PLUGIN_ROOT / "commands" / "gx-명세일괄.md").read_text(encoding="utf-8")
        구간 = re.search(
            r"^### Step 9: 게이트 3(.*?)(?=^### |\Z)", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "gx-명세일괄.md 에서 Step 9(게이트 3) 절을 찾지 못했습니다")
        self.assertIn("[미확정] 제약", 구간.group(1))


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
        """낱말 존재만 보면 Step 7 을 통째로 지워도 통과한다.

        `manage-revision-history` 는 §왜 필요한가에도 나오므로 파일 전체 검사는
        순서 계약을 지키지 못한다. Step 7 절 안에서 순서 문장까지 함께 본다.
        """
        구간 = re.search(r"^### Step 7(.*?)(?=^### |^## |\Z)", self.text, re.M | re.S)
        self.assertIsNotNone(구간, "reconcile-ids 의 Step 7 절을 찾지 못했습니다")
        self.assertIn("manage-revision-history", 구간.group(1))
        self.assertIn("순서를 뒤집지 않는다", 구간.group(1))

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


class RequirementStatusValueTest(unittest.TestCase):
    """AN-02 `상태` 열은 3값이다 (`유지`/`변경`/`삭제`).

    `신규`를 없앤 이유: 최초 작성이면 전건이 `신규`라 아무 정보가 없고, 재실행 때도
    `신규`와 `유지`가 모두 "현재 유효함"을 뜻해 구분이 흐렸다. 무엇이 새로 들어왔는지는
    `요구사항 근거` 열과 개정이력의 `개정 사유`가 이미 기록하므로, 상태 열은
    "이번 개정에서 손댔는가"만 답하면 된다 — 그래서 최초 작성에도 전건 `유지`다.

    정본은 templates/AN-02-requirements-definition.md 하나다. DE-08 `구분` 열의
    `신규`(컬럼의 신규 여부)와 revision-history.md `개정 사유`의 `신규`(문서 최초 생성)는
    다른 축이라 이 테스트의 대상이 아니다 — 그래서 절 범위를 좁혀서 검사한다.
    """

    def setUp(self):
        self.정본파일 = (
            PLUGIN_ROOT / "templates" / "AN-02-requirements-definition.md"
        )
        self.정본 = self.정본파일.read_text(encoding="utf-8")

    def _컬럼_값규칙(self, 컬럼명: str) -> str:
        """`본문 컬럼 (정본)` 표에서 지정 컬럼의 '값 규칙' 칸 원문을 돌려준다."""
        구간 = re.search(
            r"^## 본문 컬럼 \(정본\)$(.*?)(?=^## |\Z)", self.정본, re.M | re.S
        )
        self.assertIsNotNone(구간, "§본문 컬럼 (정본) 절을 찾지 못했습니다")
        for 줄 in 구간.group(1).splitlines():
            벗긴줄 = 줄.strip()
            if not (벗긴줄.startswith("|") and 벗긴줄.endswith("|")):
                continue
            칸 = [c.strip() for c in 벗긴줄.strip("|").split("|")]
            if len(칸) < 3 or set("".join(칸)) <= set("-: "):
                continue
            if 칸[1] == 컬럼명:
                return 칸[2]
        self.fail(f"'{컬럼명}' 컬럼 행을 찾지 못했습니다")

    def _상태_판정표_행(self) -> list[list[str]]:
        """`## 상태 판정` 절의 판정표를 [대조 결과, 상태, 추가 동작] 행 목록으로 돌려준다."""
        구간 = re.search(
            r"^## 상태 판정[^\n]*\n(.*?)(?=^## |\Z)", self.정본, re.M | re.S
        )
        self.assertIsNotNone(구간, "§상태 판정 절을 찾지 못했습니다")
        행목록 = []
        for 줄 in 구간.group(1).splitlines():
            벗긴줄 = 줄.strip()
            if not (벗긴줄.startswith("|") and 벗긴줄.endswith("|")):
                continue
            칸 = [c.strip() for c in 벗긴줄.strip("|").split("|")]
            if len(칸) < 3 or set("".join(칸)) <= set("-: "):
                continue
            if 칸[0] == "대조 결과":
                continue  # 머리행
            행목록.append(칸)
        return 행목록

    def test_상태값이_정확히_3개다(self):
        """컬럼 정본의 '값 규칙' 칸에서 첫 구획(— 앞)의 백틱 값만 상태값으로 센다.

        — 뒤 설명문에는 `유지`가 다시 나온다("최초 작성 시 전건이 이 값") — 그건
        상태값 목록이 아니라 뜻풀이라 다시 세면 안 된다.
        """
        값규칙 = self._컬럼_값규칙("상태")
        목록구간 = 값규칙.split("—", 1)[0]
        상태값 = re.findall(r"`([^`]+)`", 목록구간)
        self.assertEqual(
            set(상태값), {"유지", "변경", "삭제"},
            f"AN-02 상태값이 3값(유지/변경/삭제)이 아닙니다: {상태값}",
        )
        self.assertNotIn("신규", 상태값, "`신규`가 상태값으로 남아 있습니다")

    def test_상태_판정표의_상태_열도_3값_안에_있다(self):
        상태열값 = set()
        for 행 in self._상태_판정표_행():
            상태열값.update(re.findall(r"`([^`]+)`", 행[1]))
        self.assertTrue(
            상태열값 <= {"유지", "변경", "삭제"},
            f"판정표의 상태 열에 3값 밖의 값이 있습니다: {상태열값}",
        )
        self.assertNotIn("신규", 상태열값, "판정표의 상태 열에 `신규`가 남아 있습니다")

    def test_상태_판정표가_네_갈래를_모두_덮는다(self):
        갈래 = self._상태_판정표_행()
        대조결과들 = "\n".join(행[0] for 행 in 갈래)
        for 표지 in ("입력에만 있음", "동일", "다름", "기존에만 있음"):
            with self.subTest(갈래=표지):
                self.assertIn(표지, 대조결과들, f"'{표지}' 갈래가 판정표에 없습니다")
        self.assertEqual(len(갈래), 4, f"판정표 행이 4개가 아닙니다: {len(갈래)}개")

    def test_최초_작성도_유지로_성립한다는_근거가_있다(self):
        """`유지`가 '이번 개정에서 손대지 않음'으로 정의되어 최초 작성에도 성립함을
        정본이 스스로 설명해야 한다 — 안 그러면 다음에 읽는 사람이 버그로 본다."""
        self.assertIn("손대지 않음", self.정본)
        self.assertIn("최초 작성", self.정본)

    def test_extract_requirements가_상태값을_복제하지_않고_정본을_가리킨다(self):
        text = (
            PLUGIN_ROOT / "skills" / "extract-requirements" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("templates/AN-02-requirements-definition.md", text)
        self.assertNotRegex(
            text, r"`유지`\s*/\s*`변경`\s*/\s*`삭제`",
            "정본의 3값 나열을 그대로 복제하고 있습니다",
        )
        self.assertNotIn("전건 `신규`", text, "extract-requirements 에 옛 상태값이 남아 있습니다")

    def test_요구사항정의서_커맨드가_상태값을_복제하지_않고_정본을_가리킨다(self):
        text = (
            PLUGIN_ROOT / "commands" / "gx-요구사항정의서.md"
        ).read_text(encoding="utf-8")
        self.assertIn("templates/AN-02-requirements-definition.md", text)
        self.assertNotRegex(
            text, r"`유지`\s*/\s*`변경`\s*/\s*`삭제`",
            "정본의 3값 나열을 그대로 복제하고 있습니다",
        )
        self.assertNotIn("전건 `신규`", text, "커맨드에 옛 상태값이 남아 있습니다")

    def test_순서_경고문이_두_파일에_있고_옛_문구가_없다(self):
        """ID 승계 전에 상태를 판정하면 안 된다는 경고 — 3값 체계에서는 순서를 어기면
        `변경`이 `유지`로 잡히고 `삭제`가 아예 안 잡히는 실제 피해를 말해야 한다.
        옛 문구("전건이 `신규`로 나온다")는 4값 체계의 근거라 남아 있으면 안 된다.
        """
        옛문구 = re.compile(r"전건이\s*`?신규`?\s*로\s*나온다")
        새경고_신호 = ("삭제", "잡히지 않는다")

        커맨드 = (
            PLUGIN_ROOT / "commands" / "gx-요구사항정의서.md"
        ).read_text(encoding="utf-8")
        reconcile = (
            PLUGIN_ROOT / "skills" / "reconcile-ids" / "SKILL.md"
        ).read_text(encoding="utf-8")

        for 라벨, text in (("commands/gx-요구사항정의서.md", 커맨드),
                          ("skills/reconcile-ids/SKILL.md", reconcile)):
            with self.subTest(파일=라벨):
                self.assertIsNone(
                    옛문구.search(text),
                    f"{라벨} 에 4값 체계의 옛 경고 문구가 남아 있습니다",
                )
                for 신호 in 새경고_신호:
                    self.assertIn(신호, text, f"{라벨} 에 새 경고의 '{신호}' 신호가 없습니다")


class BoundaryRuleTest(unittest.TestCase):
    """드라이런에서 놓친 4건(영값·통과 측 경계·하위 정밀도)의 재발을 막는다.

    마크다운 규칙이라 실행 검증은 불가능하다. 규칙 섹션이 삭제되지 않도록
    존재만 고정한다.
    """

    def setUp(self):
        self.text = (
            PLUGIN_ROOT / "skills" / "design-test-cases" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_경계값_도출이_3유형으로_나뉘어_있다(self):
        for heading in ("유형 A", "유형 B", "유형 C"):
            with self.subTest(유형=heading):
                self.assertIn(heading, self.text, f"{heading} 절이 없습니다")

    def test_영값_케이스_규칙이_있다(self):
        self.assertIn("영값", self.text)

    def test_통과_측_경계_규칙과_연산자표가_있다(self):
        self.assertIn("isBefore", self.text)
        self.assertIn("경계 정확히 일치", self.text)

    def test_하위_정밀도_전개_규칙이_있다(self):
        self.assertIn("나노초", self.text)

    def test_제약_출처에_도메인_검증_코드가_있다(self):
        self.assertIn("도메인 검증 코드", self.text)

    def test_검증_조건_순차_검사_규칙이_있다(self):
        self.assertIn("먼저 걸리는 조건", self.text)


class RevisionHistoryTest(unittest.TestCase):
    """개정이력은 5종 공통 횡단 규칙이다.

    정본은 templates/revision-history.md 다. 산출물마다 규칙을 복제하면
    "언제 버전을 올리는가"가 다섯 갈래로 갈라진다.
    """

    def setUp(self):
        정본파일 = PLUGIN_ROOT / "templates" / "revision-history.md"
        self.assertTrue(정본파일.exists(), "개정이력 정본 템플릿이 없습니다")
        self.정본 = 정본파일.read_text(encoding="utf-8")

    def test_개정이력_컬럼_여섯_개가_정본에_있다(self):
        for 컬럼 in ["버전", "개정일", "개정 사유", "개정 내용", "작성자", "승인자"]:
            with self.subTest(컬럼=컬럼):
                self.assertIn(컬럼, self.정본)

    def test_개정_사유_다섯_값이_정본에_있다(self):
        for 값 in ["신규", "추가", "변경", "삭제", "보완"]:
            with self.subTest(사유=값):
                self.assertIn(f"`{값}`", self.정본)

    def test_행이_추가되지_않는_세_경우가_명시돼_있다(self):
        """이 셋을 빠뜨리면 게이트에서 고칠 때마다 버전이 올라간다."""
        for 표지 in ["승인 게이트 안에서의 수정", "다른 문서만 바뀐", "diff"]:
            with self.subTest(경우=표지):
                self.assertIn(표지, self.정본)

    def test_사유_우선순위가_명시돼_있다(self):
        self.assertIn("삭제` > `변경` > `추가` > `보완", self.정본)

    def test_횡단_스킬이_정본을_참조한다(self):
        스킬 = PLUGIN_ROOT / "skills" / "manage-revision-history" / "SKILL.md"
        self.assertTrue(스킬.exists(), "manage-revision-history 스킬이 없습니다")
        self.assertIn(
            "templates/revision-history.md",
            스킬.read_text(encoding="utf-8"),
            "스킬이 정본을 참조하지 않고 규칙을 복제하고 있습니다",
        )


class TableSpecStandardTest(unittest.TestCase):
    """테이블정의서는 표준용어 MCP 없이 컬럼명을 지어내지 않는다."""

    def setUp(self):
        self.스킬 = (
            PLUGIN_ROOT / "skills" / "convert-ddl-to-tablespec" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_두_MCP_도구를_모두_쓴다(self):
        for 도구 in ["validate_column", "translate_column"]:
            with self.subTest(도구=도구):
                self.assertIn(도구, self.스킬)

    def test_기존_컬럼을_바꾸지_않는다고_명시한다(self):
        self.assertIn("현행유지", self.스킬)

    def test_MCP_부재_시_중단한다고_명시한다(self):
        self.assertIn("지어내지 않는다", self.스킬)

    def test_MCP_연계_정본을_참조한다(self):
        self.assertIn("docs/표준용어-mcp-연계.md", self.스킬)

    def test_순방향_생성_경로가_남아있지_않다(self):
        커맨드 = (
            PLUGIN_ROOT / "commands" / "gx-테이블정의서.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "generate-erd-guide", 커맨드,
            "요구사항에서 테이블을 추론하는 순방향 경로가 남아 있습니다",
        )


class FiveDocumentContractTest(unittest.TestCase):
    """산출물 5종이 같은 규약을 따르는지 묶는다."""

    산출물스킬 = [
        "extract-requirements",
        "generate-function-spec",
        "convert-ddl-to-tablespec",
        "generate-unit-test-plan",
        "trace-requirements",
    ]

    def test_다섯_스킬이_모두_개정이력_스킬을_부른다(self):
        for 스킬 in self.산출물스킬:
            with self.subTest(스킬=스킬):
                text = (
                    PLUGIN_ROOT / "skills" / 스킬 / "SKILL.md"
                ).read_text(encoding="utf-8")
                self.assertIn(
                    "manage-revision-history", text,
                    "개정이력을 기록하지 않으면 버전이 올라가지 않습니다",
                )

    def test_다섯_템플릿이_모두_개정이력_시트를_선언한다(self):
        for 템플릿 in [
            "AN-02-requirements-definition.md",
            "AN-03-function-spec.md",
            "DE-08-table-definition.md",
            "DE-13-unit-test-plan.md",
            "AN-05-traceability-matrix.md",
        ]:
            with self.subTest(템플릿=템플릿):
                text = (PLUGIN_ROOT / "templates" / 템플릿).read_text(encoding="utf-8")
                self.assertIn("templates/revision-history.md", text)

    def test_다섯_템플릿이_모두_본문_컬럼_정본_절을_갖는다(self):
        from helpers import parse_column_ssot
        for 템플릿, 개수 in [
            ("AN-02-requirements-definition.md", 10),
            ("AN-03-function-spec.md", 10),
            ("DE-08-table-definition.md", 15),
            ("DE-13-unit-test-plan.md", 12),
            ("AN-05-traceability-matrix.md", 9),
        ]:
            with self.subTest(템플릿=템플릿):
                self.assertEqual(
                    len(parse_column_ssot(템플릿, "본문 컬럼 (정본)")), 개수
                )

    def test_화면_축_잔재가_현역_문서에_없다(self):
        """archive/ 밖에는 화면 축 어휘가 남으면 안 된다."""
        잔재 = ["화면목록표", "PG_{화면ID}", "제안요청ID", "수용여부"]
        for path, text in specs_only(read_docs()):
            for 낱말 in 잔재:
                with self.subTest(문서=doc_label(path), 낱말=낱말):
                    self.assertNotIn(낱말, text)


class SplitOmissionAndDataProvenanceTest(unittest.TestCase):
    """분할 누락 되묻기와 데이터 출처 검사 — 실제 실행에서 뚫린 결함을 막는다.

    SFR-012(벤치마크 산출)는 원본 기능 6건을 묶은 요구사항이었는데 gx-pm 은 3건으로만
    갈랐고, 그중 "원본 보존 적재"가 통째로 사라졌다. 그 결과 SFR-017(통계 원본 세부
    조회 + 이상값 조건부 재산출)에 해당하는 기능이 읽을 데이터를 만드는 기능이 없는
    채로 남았다. 행 분할 규칙(`templates/AN-03-function-spec.md`)은 있었지만 적용을
    빠뜨렸는지 보는 장치가 없어서 못 잡았다 — 같은 실행에서 SFR-022~024(로그인·
    로그아웃·토큰갱신)는 요구사항 단계에서 뭉쳐 있던 것을 정확히 갈랐으니, 규칙이
    아니라 적용이 흔들린 것이다.
    """

    def setUp(self):
        self.스킬 = (
            PLUGIN_ROOT / "skills" / "generate-function-spec" / "SKILL.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^### Step 6: 검증$(.*?)(?=^### |\Z)", self.스킬, re.M | re.S)
        self.assertIsNotNone(구간, "generate-function-spec 의 Step 6 절을 찾지 못했습니다")
        self.step6 = 구간.group(1)

    def test_Step6_이_분할_누락을_되묻는다(self):
        self.assertIn("분할 누락", self.step6)
        self.assertRegex(
            self.step6, r"되묻는다|되묻기",
            "분할 누락은 차단이 아니라 되묻기여야 합니다",
        )
        # 실제로 뚫린 사례(SFR-012)가 판정 기준을 구체화한다 — 산출물 3종 열거
        self.assertIn("원단위", self.step6)
        self.assertIn("건물 등급", self.step6)

    def test_Step6_이_데이터_출처를_검사한다(self):
        self.assertIn("데이터 출처", self.step6)
        self.assertIn("만드는 기능", self.step6)

    def test_두_검사_모두_차단하지_않는다(self):
        """정말 한 기능인 경우도, 외부에서 들어오는 데이터인 경우도 있다 — 되묻기·
        목록 보고이지 차단이 아니다."""
        for 라벨 in ("분할 누락", "데이터 출처"):
            with self.subTest(검사=라벨):
                시작 = self.step6.find(라벨)
                self.assertNotEqual(시작, -1, f"'{라벨}' 문단을 찾지 못했습니다")
                문단 = self.step6[시작:시작 + 400]
                self.assertRegex(
                    문단, r"차단(하지 않는다|이 아니라)",
                    f"'{라벨}' 검사 문단에 차단하지 않는다는 선언이 없습니다",
                )

    def test_게이트2_집계가_5종으로_늘었다(self):
        self.assertIn("집계 5종", self.스킬)
        for 항목 in ("분할 누락 의심", "데이터 출처 없음"):
            with self.subTest(항목=항목):
                self.assertIn(항목, self.스킬)


class Gate2ShowsSplitAndProvenanceTest(unittest.TestCase):
    """계측하고 화면에 안 내면 계측하지 않은 것과 같다 — 근거 가용도 계측과 같은 원칙
    (test_게이트2가_근거_집계를_보여준다 참조). Step 절로 범위를 좁혀서 본다."""

    def setUp(self):
        본문 = (PLUGIN_ROOT / "commands" / "gx-명세일괄.md").read_text(encoding="utf-8")
        구간 = re.search(
            r"^### Step 6: 게이트 2(.*?)(?=^### |\Z)", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "gx-명세일괄.md 에서 Step 6(게이트 2) 절을 찾지 못했습니다")
        self.게이트2 = 구간.group(1)

    def test_게이트2에_분할_누락과_데이터_출처_집계가_실린다(self):
        for 항목 in ("분할 누락", "데이터 출처"):
            with self.subTest(항목=항목):
                self.assertIn(항목, self.게이트2, f"게이트 2 화면에 '{항목}' 이 없습니다")


class DesignConstraintReflectionTest(unittest.TestCase):
    """DAR-005(회차 누적 규칙)처럼 기능을 거치지 않는 데이터 요구사항이 DE-08 어디에도
    반영되지 않고 조용히 사라지던 결함을 막는다. 원본 시스템은 이 규칙을 놓쳐 마지막
    회차 대장 46건에 900만 건이 조인되는 사고가 실제로 났다. 기존 누락 판정 7유형은
    전부 기능 축만 보고, `테이블·컬럼` 열은 DE-08 의 `연계기능ID` 역조회라 기능을
    거치지 않는 데이터 요구사항은 대조 대상이 아니었다.
    """

    def setUp(self):
        self.an05 = (
            PLUGIN_ROOT / "templates" / "AN-05-traceability-matrix.md"
        ).read_text(encoding="utf-8")

    def _누락판정_유형행(self) -> list[str]:
        구간 = re.search(r"^## 누락 판정$(.*?)(?=^## |\Z)", self.an05, re.M | re.S)
        self.assertIsNotNone(구간, "AN-05 의 §누락 판정 절을 찾지 못했습니다")
        유형행 = []
        for 줄 in 구간.group(1).splitlines():
            벗긴줄 = 줄.strip()
            if not (벗긴줄.startswith("|") and 벗긴줄.endswith("|")):
                continue
            칸 = [c.strip() for c in 벗긴줄.strip("|").split("|")]
            if len(칸) < 3 or set("".join(칸)) <= set("-: "):
                continue
            if 칸[0] == "유형":
                continue  # 머리행
            유형행.append(칸[0])
        return 유형행

    def test_누락_판정이_8유형이고_설계_제약_미반영이_있다(self):
        유형행 = self._누락판정_유형행()
        self.assertEqual(len(유형행), 8, f"누락 판정 유형이 8개가 아닙니다: {유형행}")
        self.assertIn("설계 제약 미반영", 유형행)

    def test_AN_05_컬럼_정본은_9개_그대로다(self):
        """누락 열의 표기값만 늘어야 한다 — 컬럼 정본(9개)을 늘리거나 줄이면 안 된다."""
        from helpers import parse_column_ssot
        self.assertEqual(
            len(parse_column_ssot("AN-05-traceability-matrix.md", "본문 컬럼 (정본)")), 9
        )

    def test_convert_ddl_이_데이터_요구사항_반영_단계를_갖는다(self):
        """정본만 고치고 실행부를 안 고치면 규칙이 돌지 않는다 (기존 관례와 동일)."""
        스킬 = (
            PLUGIN_ROOT / "skills" / "convert-ddl-to-tablespec" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("데이터 요구사항", 스킬)
        self.assertRegex(
            스킬, r"차단하지 않(는다|고)",
            "데이터 요구사항 반영 단계가 차단하지 않는다고 선언하지 않았습니다",
        )
        self.assertIn("templates/AN-05-traceability-matrix.md", 스킬)

    def test_trace_requirements_가_8번째_유형을_판정한다(self):
        """정본에 유형을 더하고 판정 순서를 안 고치면 그 유형이 영영 안 나온다.

        AN-05 템플릿에 `설계 제약 미반영` 을 넣었을 때 실제로 그랬다 — 정본은 8유형인데
        `trace-requirements` Step 5 의 판정 순서는 7개뿐이라, 매트릭스를 만들어도
        그 값이 한 번도 찍히지 않았다. 이 플러그인이 반복해 겪은 형태다:
        규칙은 정본에 있고 실행부가 그걸 안 한다.

        Step 5 절로 범위를 좁혀서 본다.
        """
        스킬 = (
            PLUGIN_ROOT / "skills" / "trace-requirements" / "SKILL.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^### Step 5: 누락 판정$(.*?)(?=^## |\Z)", 스킬, re.M | re.S)
        self.assertIsNotNone(
            구간, "trace-requirements 의 §Step 5 누락 판정 절을 찾지 못했습니다"
        )
        절 = 구간.group(1)
        번호 = re.findall(r"^\d+\. ", 절, re.M)
        self.assertEqual(
            len(번호), 8,
            f"판정 순서가 8단계가 아닙니다: {len(번호)}단계 "
            "— 정본의 누락 유형 수와 어긋나면 안 나오는 유형이 생깁니다",
        )
        self.assertIn(
            "설계 제약 미반영", 절,
            "Step 5 판정 순서에 `설계 제약 미반영` 이 없습니다",
        )
        self.assertIn(
            "skills/convert-ddl-to-tablespec/SKILL.md", 절,
            "Step 5 가 반영 절차의 정본을 가리키지 않습니다",
        )

    def _step5절(self) -> str:
        스킬 = (
            PLUGIN_ROOT / "skills" / "trace-requirements" / "SKILL.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^### Step 5: 누락 판정$(.*?)(?=^## |\Z)", 스킬, re.M | re.S)
        self.assertIsNotNone(
            구간, "trace-requirements 의 §Step 5 누락 판정 절을 찾지 못했습니다"
        )
        return 구간.group(1)

    def test_미수행이_판정_사다리_맨_뒤에_온다(self):
        """`미수행` 이 앞에 있으면 그 뒤 판정이 한 번도 발화하지 못한다.

        계획 단계 산출물은 `결과` 가 언제나 전건 공란이라, `미수행` 조건이
        테스트를 가진 행을 전부 선점한다. v3.2.0 시험에서 실제로 AN-05 86행
        전건이 `미수행` 으로 나왔고, v3.2.0 이 새로 넣은 `설계 제약 미반영` 은
        한 번도 찍히지 않는 죽은 코드였다.

        개수만 세는 test_trace_requirements_가_8번째_유형을_판정한다 로는 이걸
        못 잡는다 — 아홉 개가 다 있어도 순서가 틀리면 안 나온다. 그래서 순서를 본다.

        `미수행` 은 진행 상태이고 나머지는 산출물 결함이라, 결함이 먼저 걸려야 한다.
        """
        절 = self._step5절()
        미수행 = 절.find("`미수행`")
        self.assertNotEqual(미수행, -1, "Step 5 에 `미수행` 판정이 없습니다")
        for 앞 in ("실패 {N}건", "예외 케이스 없음", "설계 제약 미반영"):
            위치 = 절.find(앞)
            self.assertNotEqual(위치, -1, f"Step 5 에 `{앞}` 이 없습니다")
            self.assertLess(
                위치, 미수행,
                f"`{앞}` 이 `미수행` 보다 뒤에 있습니다 — 계획 단계 문서는 `결과` 가 "
                "전건 공란이라 `미수행` 이 먼저 걸리면 이 판정은 영영 발화하지 못합니다",
            )

    def test_비기능_경로가_데이터_축_판정까지_적용한다(self):
        """비기능 경로에서 데이터 축 판정을 빼면 데이터 요구사항이 빈칸으로 남는다.

        데이터 요구사항은 기능을 거치지 않아 비기능 경로로 흐른다. 그 경로가
        `테스트 수 기준` 판정만 적용하면 `설계 제약 미반영` 이 걸리지 않는다.
        판정 사다리 맨 앞의 `미수행` 선점과 함께, 이것이 그 유형이 한 번도
        발화하지 못한 두 번째 원인이었다.

        범위 표기(`3~7번`)만 검사하면 괄호가 옛말로 남아도 통과하므로 괄호도 본다.
        """
        절 = self._step5절()
        self.assertIn(
            "3~7번", 절,
            "비기능 경로가 데이터 축 판정(`설계 제약 미반영`)까지 적용하지 않습니다",
        )
        self.assertNotIn(
            "테스트 수 기준", 절,
            "범위는 넓혔는데 괄호가 `테스트 수 기준` 으로 남아 있습니다 "
            "— 데이터 축 판정이 들어왔으므로 거짓입니다",
        )

    def test_AN_05_예시의_상태가_정본_3값_안에_있다(self):
        """예시가 정본을 어기면 그 예시를 보고 만든 산출물이 정본을 어긴다.

        AN-02 정본은 `신규` 가 상태값이 아니라고 못박았는데 AN-05 예시 행은
        `신규` 를 쓰고 있었다. xlsx 드롭다운을 걸면 정본이 자기 예시를 거부한다.
        """
        본문 = (
            PLUGIN_ROOT / "templates" / "AN-05-traceability-matrix.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^## 예시 행$(.*?)(?=^## |\Z)", 본문, re.M | re.S)
        self.assertIsNotNone(구간, "AN-05 템플릿의 §예시 행 절을 찾지 못했습니다")
        for 행 in re.findall(r"^\| REQ-\d+ \|.*$", 구간.group(1), re.M):
            상태 = [칸.strip() for 칸 in 행.split("|")][3]
            self.assertIn(
                상태, {"유지", "변경", "삭제"},
                f"AN-05 예시의 상태값 {상태!r} 이 AN-02 정본의 3값 밖입니다: {행}",
            )

    def test_AN_05_Pass_Fail_설명이_미수행을_못박지_않는다(self):
        """컬럼 정본이 특정 판정을 못박으면 판정 순서를 바꿀 때 정본이 갈라진다.

        `0/0`(누락 열에 `미수행`) 이라고 적혀 있었는데, `미수행` 이 사다리 맨 뒤로
        가면서 테스트 1건짜리 행은 `예외 케이스 없음` 을 받는다. 괄호가 거짓이 된다.
        """
        본문 = (
            PLUGIN_ROOT / "templates" / "AN-05-traceability-matrix.md"
        ).read_text(encoding="utf-8")
        행 = next(줄 for 줄 in 본문.splitlines() if "| 8 | Pass/Fail |" in 줄)
        self.assertNotIn(
            "누락 열에 `미수행`", 행,
            "Pass/Fail 컬럼 정의가 `미수행` 을 못박고 있습니다 "
            "— 판정 순서가 바뀌면 거짓이 됩니다. `누락` 열을 가리키기만 하세요",
        )

    def test_적용_순서의_정본이_사다리다(self):
        """정의표의 행 순서를 적용 순서로 읽으면 사다리 뒤쪽이 죽는다.

        정본 표는 유형 **정의**의 정본(「유형 · 조건 · 표기」 3열)이고, 적용
        순서의 정본은 Step 5 사다리다. 정의표에서 `미수행` 은 5행이고
        `설계 제약 미반영` 은 그 뒤라, 커맨드가 정의표를 「순서대로
        적용한다」고 지시하면 그 둘이 한 번도 발화하지 못한다 — v3.2.0 에서
        `설계 제약 미반영` 이 죽은 코드였던 것과 같은 형태다.
        """
        본문 = (
            PLUGIN_ROOT / "commands" / "gx-추적매트릭스.md"
        ).read_text(encoding="utf-8")
        self.assertNotRegex(
            본문, r"AN-05-traceability-matrix\.md[^\n]*누락 판정표를 순서대로",
            "gx-추적매트릭스 가 정의표를 「순서대로 적용한다」고 지시합니다 "
            "— 정의표의 행 순서는 적용 순서가 아닙니다",
        )
        self.assertRegex(
            본문,
            r"적용 순서의 정본[^\n]*`skills/trace-requirements/SKILL\.md`[^\n]*Step 5",
            "gx-추적매트릭스 가 적용 순서의 정본(Step 5 사다리)을 가리키지 "
            "않습니다 — 스킬 경로 문자열은 이 문서 다른 곳에도 있어, 한 줄로 "
            "묶어 보지 않으면 포인터가 빠져도 통과합니다",
        )

    def test_누락_유형_수_표기가_문서마다_같다(self):
        """`7유형` 이라고 적힌 곳이 네 군데 있었다. 정본만 8로 늘리면 나머지가

        낡은 수를 주장한다. 반대로 실행부가 못 미치는데 설명만 늘리면 없는 기능을
        있다고 말한다 — 어느 쪽이든 문서가 서로를 부정한다.
        """
        유형수 = len(self._누락판정_유형행())
        for 경로 in (
            PLUGIN_ROOT / "skills" / "trace-requirements" / "SKILL.md",
            PLUGIN_ROOT / "skills" / "id-trace" / "SKILL.md",
            PLUGIN_ROOT / "commands" / "gx-추적매트릭스.md",
        ):
            본문 = 경로.read_text(encoding="utf-8")
            with self.subTest(문서=경로.name):
                낡은표기 = re.findall(r"누락[^\n]{0,20}?(\d+)(?:유형|가지 유형)", 본문)
                for 수 in 낡은표기:
                    self.assertEqual(
                        int(수), 유형수,
                        f"{경로.name} 이 누락 유형을 {수}개로 적었습니다 "
                        f"— 정본은 {유형수}개입니다",
                    )

    def test_AN_05_가_데이터_요구사항_정의를_convert_ddl_로_가리킨다(self):
        """정본을 옮겨 적지 않고 경로로 가리키는지 — 같은 개념이 두 곳에서 따로
        정의되면 다음 수정에서 어긋난다."""
        self.assertIn("skills/convert-ddl-to-tablespec/SKILL.md", self.an05)

class ConfirmationSheetTest(unittest.TestCase):
    """확인요청서는 시트를 「값이 있나 없나」로 나눈다.

    시트 1 은 AI 가 정한 값을 반증하고, 시트 2 는 값이 아예 없는 것을 채운다.
    시트 2 만 떼어 낼 수 있어야 하므로 한 시트에 섞으면 안 된다.

    **누구에게 물으라고 지시하지 않는다.** 값을 어디서 구할지는 파일을 받은
    사람이 안다 — 양식이 특정 상대를 지목하면 그 상대가 아닌 경로로 값을 구할
    때 문구가 거짓이 된다.

    시트 수만 세면 역할이 뒤바뀌어도 통과한다. 그래서 분류표에서 **그 시트의
    행 한 줄**을 잘라 「누가 채우나」 칸을 본다 — 문서 전체를 보면 다른 시트의
    역할 낱말에 걸려 조용히 통과한다.
    """

    def setUp(self):
        self.text = (
            PLUGIN_ROOT / "templates" / "confirmation-request.md"
        ).read_text(encoding="utf-8")

    def test_시트가_네_장이고_각각_역할이_있다(self):
        for 번호, 시트명, 역할 in (
            (0, "안내", "읽기만"),
            (1, "가정 확인", "채운다"),
            (2, "미확정 확인", "채운다"),
            (3, "요청 이력", "읽기만"),
        ):
            with self.subTest(시트=f"시트 {번호} · {시트명}"):
                self.assertIn(
                    f"시트 {번호} · {시트명}", self.text,
                    f"시트 {번호} · {시트명} 절이 없습니다",
                )
                행 = re.search(
                    rf"^\|\s*{번호}\s*\|\s*{시트명}\s*\|([^\n|]*)\|",
                    self.text, re.M,
                )
                self.assertIsNotNone(
                    행, f"시트 분류표에 시트 {번호}({시트명}) 행이 없습니다",
                )
                self.assertIn(
                    역할, 행.group(1),
                    f"시트 {번호}({시트명}) 의 「누가 채우나」가 {역할} 이 아닙니다",
                )

    def test_답할_상대를_지목하지_않는다(self):
        """양식이 「발주기관에 물어라」로 상대를 지목하면 거짓이 될 수 있다.

        값을 어디서 구할지는 이 파일을 받은 사람이 안다. 착수 협의로 정하기도
        하고 설계자가 판단하기도 한다. 양식이 할 일은 무엇이 비었는지와 어디에
        쓰는지를 알려주는 것까지다.
        """
        self.assertNotIn(
            "발주기관", self.text,
            "확인요청서 양식이 답할 상대를 지목합니다",
        )
        self.assertIn(
            "누구에게 물으라고 지시하지 않는다", self.text,
            "상대를 지목하지 않는다는 규칙이 없습니다",
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
        self.assertRegex(
            절, r"\[가정\][^\n]*\[미확정\][^\n]*합계[^\n]*6건 이상[^\n]*중단",
            "게이트 2 의 발행 기준이 「`[가정]` + `[미확정]` 합계」가 아닙니다 "
            "— 기준어를 보지 않으면 다른 기준으로 바뀌어도 "
            "「6건 이상…중단」 만으로 조용히 통과합니다",
        )
        self.assertRegex(
            절, r"1~5건[^\n]*대화로 묻",
            "게이트 2 에 「1~5건 → 대화로 묻는다」 분기가 없습니다 "
            "— 이 문단이 사라지면 2건 때문에도 무조건 발행·중단합니다",
        )

    def test_게이트가_확인요청서_xlsx_를_실제로_뽑는다(self):
        """경로를 안내만 하고 추출을 안 하면 사람이 채울 파일이 없다.

        연노랑 입력란·드롭다운·「안내」 시트는 전부 xlsx 쪽 장치다
        (`templates/confirmation-request.md` §응답란은 드롭다운이고 배경이
        연노랑이다). export-xlsx.py 를 부르는 자리가 Step 10 뿐이면 게이트 2·3 은
        그 앞에서 중단하므로, 확인요청서 xlsx 는 어느 실행 경로에서도 만들어지지
        않는다 — 왕복 설계 전체가 이 한 줄에 걸린다.
        """
        for 제목 in ("Step 6: 게이트 2", "Step 9: 게이트 3"):
            with self.subTest(게이트=제목):
                절 = self._절(제목)
                self.assertRegex(
                    절, r"export-xlsx\.py[^\n]*--separate[^\n]*--output xlsx",
                    f"{제목} 의 발행 절차에 확인요청서 xlsx 추출 명령이 없습니다 "
                    "— 화면은 xlsx/ 경로를 안내하는데 그 파일을 만드는 지시가 "
                    "어디에도 없습니다",
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
        self.assertRegex(
            절, r"빈칸[^\n]*(그대로 진행|그 값으로 진행)",
            "빈칸이 「그대로 진행」이라는 뜻임이 안내에 없습니다 "
            "— 이 한 줄이 없으면 사용자가 전건을 채워야 하는 줄 알고 거기서 멈춥니다",
        )
        self.assertRegex(
            절, r"/gx-명세일괄.*다시",
            "다시 부르는 방법이 화면에 없습니다",
        )

    def test_게이트3은_2차를_발행한다(self):
        절 = self._절("Step 9: 게이트 3")
        self.assertIn("2차", 절, "게이트 3 이 2차를 발행하지 않습니다")

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
        상태줄 = re.search(r"확인요청서가 있습니다[^\n]*", 절)
        self.assertIsNotNone(
            상태줄,
            "재개 화면에 현재 상태 줄이 없습니다 "
            "— 사용자가 지금 어디까지 왔는지 알 방법이 없습니다",
        )
        self.assertRegex(
            상태줄.group(0), r"\d차",
            "재개 화면이 지금 몇 차인지 보여주지 않습니다",
        )
        self.assertRegex(
            상태줄.group(0), r"\d+건[^\n]*응답",
            "재개 화면이 응답 건수를 보여주지 않습니다",
        )

    def test_반영하지_않고_계속하는_길이_있다(self):
        """급할 때 확인요청서를 건너뛸 수 있어야 한다.

        없으면 확인요청서가 파이프라인을 막는 관문이 된다.
        """
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", self.본문, re.M | re.S)
        self.assertIsNotNone(구간)
        self.assertIn("반영하지 않고 계속", 구간.group(1))

    def test_확인요청서_분기에_처음부터_선택지가_있다(self):
        """세 번째 선택지(처음부터)를 지워도 걸리는 검사가 따로 없었다.

        Step 0 에는 게이트 재개 분기에도 '처음부터' 가 이미 있다
        (이어쓰기/새로쓰기/열기 중 고르는 것 — 0-2 절 맨 앞, 확인요청서 분기보다
        먼저 나온다). Step 0 절 전체에 대고 '처음부터' 만 찾으면 확인요청서
        분기의 3번을 통째로 지워도 그 낱말이 다른 자리에 남아 통과한다 —
        확인요청서 문단으로 범위를 좁혀서 본다.
        """
        구간 = re.search(r"^### Step 0:(.*?)(?=^### |\Z)", self.본문, re.M | re.S)
        self.assertIsNotNone(구간, "Step 0 절을 찾지 못했습니다")
        절 = 구간.group(1)
        분기 = re.search(
            r"확인요청서가 있으면.*?(?=\*\*산출물마다 고른 처리 방식)", 절, re.S
        )
        self.assertIsNotNone(분기, "확인요청서 분기 문단을 찾지 못했습니다")
        self.assertIn(
            "처음부터", 분기.group(0),
            "확인요청서 분기에 3번(처음부터) 선택지가 없습니다 — Step 0 안에는 "
            "게이트 재개 분기의 '처음부터' 가 이미 있어 낱말만 찾으면 이 분기가 "
            "통째로 지워져도 잡히지 않습니다",
        )

    def test_확인요청서_분기가_3분기보다_앞에_온다(self):
        """서술과 위치가 어긋나면 실행이 어느 쪽을 따를지 알 수 없다.

        본문은 "확인요청서가 있으면 3분기보다 먼저 이것을 묻는다" 고 서술한다.
        그런데 문단이 detect-existing-artifact 3분기 **뒤**에 있으면, 자연어
        지시문을 순서대로 읽는 실행은 3분기를 먼저 묻게 된다.

        이 레포는 같은 유형에 당한 적이 있다 — Step 0 에 "프로파일이 없으면
        안내 후 종료한다" 가 있는데도 뒤 Step 들이 이어 쓰여 있어 실행이 계속
        읽어 내려가 프로파일을 대신 만들었다. 그래서 Step 0 을 하위 절로 끊었다.

        낱말의 존재만 보는 검사로는 이 어긋남을 못 잡는다 — 순서를 되돌려도
        전건 통과한다.
        """
        구간 = re.search(r"^#### 0-2\. (.*?)(?=^#### |\Z)", self.본문, re.M | re.S)
        self.assertIsNotNone(구간, "0-2 기존 산출물 감지 절을 찾지 못했습니다")
        절 = 구간.group(1)
        확인요청서 = 절.find("확인요청서가 있으면")
        감지 = 절.find("**detect-existing-artifact**")
        self.assertNotEqual(확인요청서, -1, "확인요청서 분기 문단이 없습니다")
        self.assertNotEqual(감지, -1, "detect-existing-artifact 호출 문장이 없습니다")
        self.assertLess(
            확인요청서, 감지,
            "확인요청서 분기가 3분기 뒤에 있습니다 — 본문은 「3분기보다 먼저」라고 "
            "서술하는데 위치가 반대라, 실행이 3분기를 먼저 묻게 됩니다",
        )

    def test_게이트3도_5건_이하면_멈추지_않는다(self):
        """소수를 위해 왕복을 만들지 않는다는 규칙은 게이트 2·3 이 같아야 한다.

        confirmation-request.md §언제 만드나 는 6건 임계를 라운드 구분 없는
        일반 규칙으로 정한다. 게이트 3 만 "남아 있으면 무조건 중단" 이면
        1차 후 2~3건만 남아도 파일 재작성과 중단이 강제된다 — 이 기능이
        막으려는 왕복을 정확히 그 지점에서 만든다.
        """
        절 = self._절("Step 9: 게이트 3")
        self.assertRegex(
            절, r"\[가정\][^\n]*\[미확정\][^\n]*합계[^\n]*6건 이상[^\n]*중단",
            "게이트 3 의 발행 기준이 「`[가정]` + `[미확정]` 합계」가 아닙니다 "
            "— 정본(confirmation-request.md §언제 만드나)과 게이트 2 가 합계로 "
            "재는데 여기만 「남은 미확정」이면, 미확정 8건에 후속 확인 30건이 "
            "남은 상황에서 정본은 발행·게이트 3 은 미발행으로 갈립니다",
        )
        self.assertRegex(
            절, r"1~5건[^\n]*대화로 묻",
            "게이트 3 에 「1~5건 → 대화로 묻는다」 분기가 없습니다 "
            "— 이 문단이 사라지면 1차 후 2~3건만 남아도 무조건 중단합니다",
        )


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

    def _절(self, 제목):
        구간 = re.search(
            rf"^### {re.escape(제목)}(.*?)(?=^### |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(구간, f"{제목} 절을 찾지 못했습니다")
        return 구간.group(1)

    def test_AskUserQuestion_을_쓰지_않는다(self):
        """문장만 바꾸면 통과하므로 도구 이름의 부재를 직접 본다."""
        self.assertNotIn(
            "AskUserQuestion", self.text,
            "되묻기에 AskUserQuestion 이 남아 있습니다 "
            "— 다음 차수 엑셀 행으로 보내야 왕복이 사라집니다",
        )

    def test_되묻던_네_경우가_다음_차수_행이_된다(self):
        """네 경우 낱말은 옛 「되묻기 — 네 경우뿐」 절에도 그대로 있던 말이라,
        전체 텍스트 검사로는 Step 4 를 안 바꿔도 통과한다. Step 4 절로 범위를
        좁히고, 옛 상한 문구(5건 · [반영 N/5])가 그 절에서 사라졌는지도 함께
        본다 — 그래야 "대화식 되묻기가 실제로는 안 바뀐" 경우를 잡는다.
        """
        절 = self._절("Step 4:")
        self.assertIn("다음 차수", 절, "Step 4 절에 「다음 차수」가 없습니다")
        for 경우 in ("정정값이 비었", "형식", "충돌", "파급"):
            with self.subTest(경우=경우):
                self.assertIn(
                    경우, 절, f"Step 4 절에 되묻던 경우 「{경우}」 가 없습니다"
                )
        self.assertNotIn(
            "5건", 절,
            "Step 4 에 옛 되묻기 상한 문구(5건)가 남아 있습니다 "
            "— 대화식 되묻기 설계가 실제로는 안 바뀐 것입니다",
        )
        self.assertNotIn(
            "[반영", 절,
            "Step 4 에 옛 되묻기 카운터 표기([반영 N/5])가 남아 있습니다",
        )

    def test_값을_대신_정하지_않는다(self):
        """3차까지 답이 없어도 관행값으로 채우면 「전부 해소」 규칙이 무의미해진다.

        채운 값은 해소된 것처럼 보이지만 실은 우리가 정한 값이라, 개발자가
        확정값으로 읽고 착수한다. v4.0.0 이 `[임시확정]` 을 없앤 이유다.
        """
        self.assertIn("3차", self.text)
        self.assertNotIn(
            "임시확정", self.text,
            "값을 대신 정하는 표기가 남아 있습니다",
        )
        self.assertRegex(
            self.text, r"[^\n]*값을 대신 정하지 않는다[^\n]*",
            "값을 대신 정하지 않는다는 규칙이 없습니다",
        )

    def test_요청_이력을_남긴다(self):
        """3차까지 요청했다는 증거가 없으면 「우리가 물었다」를 증명할 수 없다.

        `## 출력` 의 예시 문구에만 두 낱말이 있고 Step 4-1 의 기록 규칙 자체가
        없으면, 실제로는 이번 차수의 요청·미응답이 시트 3 에 쌓이지 않는다 —
        전체 텍스트 검사는 예시 문구만으로도 속는다. 규칙이 선 Step 4-1 절로
        범위를 좁힌다.
        """
        절 = self._절("Step 4-1:")
        self.assertIn("요청 이력", 절, "Step 4-1 절에 「요청 이력」 기록 규칙이 없습니다")
        self.assertIn("미응답", 절, "Step 4-1 절에 「미응답」 기록 규칙이 없습니다")

    def test_시트0_안내를_매_차수_갱신한다(self):
        """confirmation-request.md §시트 0 은 `현재`·건수를 매 차수 다시 쓴다고
        못박는다. 시트 0 은 사람이 파일을 열고 맨 처음 읽는 자리라, Step 4-1 이
        이 갱신을 빠뜨리면 다음 차수 파일을 열었을 때도 이전 차수·건수가 그대로
        보인다 — 이 양식이 없애려던 혼란이 그 자리에서 재발한다.
        """
        절 = self._절("Step 4-1:")
        self.assertIn("시트 0", 절, "Step 4-1 절에 시트 0 갱신 지시가 없습니다")
        self.assertIn("안내", 절, "시트 0 갱신 지시가 「안내」 시트를 가리키지 않습니다")

    def test_확인요청서_양식_정본을_가리킨다(self):
        """이 스킬이 양식 정본을 안 가리키면 둘이 조용히 갈린다.

        Task 2 가 확인요청서를 4시트로 재편했을 때 이 스킬은 그걸 모른 채
        대화식 되묻기 설계를 유지하고 있었다 — 리뷰가 Important 로 잡았다.
        경로 참조가 없으면 같은 어긋남이 다시 생겨도 아무도 모른다.
        """
        self.assertIn(
            "templates/confirmation-request.md", self.text,
            "확인요청서 양식 정본을 가리키지 않습니다 "
            "— 시트 구조가 바뀌어도 이 스킬이 모르게 됩니다",
        )



class ConfirmationCloseoutTest(unittest.TestCase):
    """발행을 건너뛰면 왕복이 끝나는데 파일은 남는다.

    1차 시험에서 실제로 어긋났다. 반영 뒤 남은 것이 1건이라 게이트 3 이 발행을
    건너뛰었는데, 시트 0 은 「게이트 3 이후 2차 발행 예정」인 채로 끝났다.
    **오지 않을 차수를 파일이 약속한다.**

    원인이 둘이라 양쪽을 다 지킨다 — 반영 스킬이 앞으로 낼 차수를 예고했고,
    게이트는 건너뛸 때 안내를 닫지 않았다.
    """

    def _절(self, 파일: str, 제목: str) -> str:
        본문 = (PLUGIN_ROOT / 파일).read_text(encoding="utf-8")
        구간 = re.search(
            rf"^#+ {re.escape(제목)}$(.*?)(?=^#{{1,3}} |\Z)", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, f"{파일} 에 §{제목} 절이 없습니다")
        return 구간.group(1)

    def test_반영_스킬이_다음_차수를_예고하지_않는다(self):
        절 = self._절(
            "skills/apply-confirmations/SKILL.md", "다음 차수를 예고하지 않는다"
        )
        self.assertRegex(
            절, r"[^\n]*발행 여부는[^\n]*게이트[^\n]*정한다",
            "발행을 게이트가 정한다는 근거가 없습니다",
        )
        self.assertRegex(
            절, r"[^\n]*지금 상태만[^\n]*",
            "시트 0 에 지금 상태만 쓰라는 지시가 없습니다",
        )

    def test_게이트가_건너뛸_때_안내를_닫는다(self):
        본문 = (
            PLUGIN_ROOT / "commands" / "gx-명세일괄.md"
        ).read_text(encoding="utf-8")
        닫기 = re.search(r"^[^\n]*시트 0[^\n]*닫는[^\n]*$", 본문, re.M)
        self.assertIsNotNone(
            닫기,
            "발행을 건너뛸 때 시트 0 을 닫으라는 지시가 없습니다",
        )
        self.assertIn(
            "다시 쓴다", 닫기.group(0),
            "닫는다고만 하고 다시 쓰라는 말이 없습니다",
        )



class QuestionThresholdTest(unittest.TestCase):
    """미결 건수가 대화와 파일을 가른다.

    1차 시험에서 미결 9건이 「10건 이하 → 목록으로 갈음」에 걸려 **아무것도 묻지
    않고** 지나갔다. 적어서 물을 수 있는 것이지 적어서 안 물어도 되는 것이 아니다.
    경계를 5와 6 사이로 내리고, 5건 이하는 그 자리에서 대화로 묻게 바꿨다.
    """

    def test_정본이_세_구간을_가른다(self):
        절 = (
            PLUGIN_ROOT / "templates" / "confirmation-request.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^## 언제 만드나$(.*?)(?=^## )", 절, re.M | re.S)
        self.assertIsNotNone(구간, "§언제 만드나 절이 없습니다")
        본문 = 구간.group(1)
        for 표기, 뜻 in (("0건", "물을 것이 없"), ("1~5건", "대화"), ("6건 이상", "중단")):
            with self.subTest(구간=표기):
                # 앞뒤 산문에도 같은 낱말이 나온다. **구간 표의 그 행**만 본다 —
                # 표 행은 `|` 로 시작하고 첫 칸이 그 표기다.
                행 = re.search(
                    rf"^\|[^\n|]*{re.escape(표기)}[^\n|]*\|[^\n]*$", 본문, re.M
                )
                self.assertIsNotNone(행, f"구간 표에 {표기} 행이 없습니다")
                self.assertIn(
                    뜻, 행.group(0),
                    f"{표기} 행이 「{뜻}」 를 말하지 않습니다",
                )

    def test_갈음하지_않는다는_근거가_있다(self):
        본문 = (
            PLUGIN_ROOT / "templates" / "confirmation-request.md"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            본문, r"[^\n]*적어서 물을 수 있는 것이지[^\n]*",
            "적으면 안 물어도 된다는 오해를 막는 문장이 없습니다",
        )

    def test_질문_정책에_하한이_있다(self):
        본문 = (
            PLUGIN_ROOT / "templates" / "pipeline-protocol.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(r"^## 질문 정책$(.*?)(?=^## )", 본문, re.M | re.S)
        self.assertIsNotNone(구간)
        절 = 구간.group(1)
        self.assertRegex(
            절, r"[^\n]*1~5건[^\n]*대화로 묻는다[^\n]*",
            "네 번째 층의 하한(1~5건은 대화)이 질문 정책에 없습니다",
        )


class UnitTestInputTest(unittest.TestCase):
    """시험은 이 문서 하나로 끝나야 한다.

    1차 시험에서 DE-13 이 ID 만 나와 무엇을 시험하는지 알 수 없었고,  이
    추상적이라 테스터가 값을 지어내야 했다. 요구사항명을 열로 세우고, 입력은
    항목명과 값을 짝지어 적게 하고, 파일이 입력이면 실제로 만들게 한다.
    """

    def setUp(self):
        self.정본 = (
            PLUGIN_ROOT / "templates" / "DE-13-unit-test-plan.md"
        ).read_text(encoding="utf-8")

    def test_요구사항명이_열로_있다(self):
        행 = re.search(r"^\|\s*4\s*\|\s*요구사항명\s*\|([^\n|]*)\|", self.정본, re.M)
        self.assertIsNotNone(행, "DE-13 정본 4번 열이 요구사항명이 아닙니다")
        self.assertIn(
            "AN-02", 행.group(1),
            "요구사항명을 어디서 가져오는지가 값 규칙에 없습니다",
        )

    def test_입력이_그대로_넣을_수_있어야_한다(self):
        구간 = re.search(
            r"^## 입력은 그대로 넣을 수 있어야 한다$(.*?)(?=^## )",
            self.정본, re.M | re.S,
        )
        self.assertIsNotNone(구간, "§입력은 그대로 넣을 수 있어야 한다 절이 없습니다")
        절 = 구간.group(1)
        self.assertRegex(
            절, r"[^\n]*항목명과 값을 짝지어[^\n]*",
            "항목명과 값을 짝지으라는 규칙이 없습니다",
        )
        self.assertIn(
            "testdata/", 절,
            "파일 입력을 어디에 만드는지가 없습니다",
        )
        self.assertRegex(
            절, r"[^\n]*{테스트ID}[^\n]*",
            "테스트 데이터 파일명 규칙이 없습니다",
        )

    def test_스킬이_파일을_실제로_만든다(self):
        본문 = (
            PLUGIN_ROOT / "skills" / "generate-unit-test-plan" / "SKILL.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(
            r"^### Step 4-2: 파일이 입력이면 실제로 만든다$(.*?)(?=^### )",
            본문, re.M | re.S,
        )
        self.assertIsNotNone(구간, "파일 생성 Step 이 없습니다")
        절 = 구간.group(1)
        self.assertIn("testdata/", 절, "만들 자리가 없습니다")
        self.assertRegex(
            절, r"[^\n]*한 곳만 망가뜨려[^\n]*",
            "정상 파일을 한 곳만 바꿔 만들라는 규칙이 없습니다",
        )
        self.assertRegex(
            절, r"[^\n]*\[미확정\][^\n]*만들지 않는다",
            "컬럼 구성이 미확정이면 만들지 않는다는 규칙이 없습니다",
        )

    def test_testdata_폴더가_규약에_있다(self):
        본문 = (
            PLUGIN_ROOT / "templates" / "project-profile-schema.md"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            본문, r"[^\n]*testdata/[^\n]*DE-13[^\n]*",
            "testdata/ 가 프로젝트 폴더 구조에 없습니다",
        )



class FinalOutputGateTest(unittest.TestCase):
    """미확정이 남으면 최종본(xlsx)을 내지 않는다.

    v3.x 는 미확정이 남아도 xlsx 를 냈다. 3차까지 답이 없으면 관행값을 채우고
    `[임시확정]` 으로 표시했다. 그러면 개발자가 그 값을 확정값으로 읽고 착수한다.

    v4.0.0 은 값을 대신 정하지 않는다. 대신 **최종본에만 도장을 안 찍는다** —
    마크다운 5종은 게이트마다 저장되므로 작업은 막히지 않는다.
    """

    def test_정본이_최종본_보류를_정한다(self):
        본문 = (
            PLUGIN_ROOT / "templates" / "confirmation-request.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(
            r"^## 미확정이 0이어야 최종본을 낸다$(.*?)(?=^## )", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "§미확정이 0이어야 최종본을 낸다 절이 없습니다")
        절 = 구간.group(1)
        self.assertRegex(
            절, r"[^\n]*1건이라도 남아 있으면[^\n]*xlsx 를 뽑지 않는다",
            "보류 조건이 없습니다",
        )
        # 이 문장은 줄바꿈을 넘어간다. 줄이 아니라 **한 문장** 으로 좁힌다 —
        # 마침표를 넘지 않게 해서 절 안 다른 문장의 낱말에 걸리지 않게 한다.
        self.assertRegex(
            절, r"마크다운[^.]*막히지 않는다",
            "마크다운은 막지 않는다는 단서가 없습니다 — 없으면 작업 자체가 "
            "멈추는 것으로 읽힌다",
        )

    def test_Step10_이_보류를_실행한다(self):
        본문 = (
            PLUGIN_ROOT / "commands" / "gx-명세일괄.md"
        ).read_text(encoding="utf-8")
        구간 = re.search(
            r"^#### 미확정이 0인지 먼저 본다$(.*?)(?=^#### |^### )", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "Step 10 에 미확정 검사 절이 없습니다")
        절 = 구간.group(1)
        self.assertIn(
            "templates/confirmation-request.md", 절,
            "보류 규칙의 정본을 가리키지 않습니다",
        )
        self.assertRegex(
            절, r"[^\n]*1~5건[^\n]*묻는다",
            "1~5건이면 그 자리에서 묻는다는 분기가 없습니다",
        )

    def test_임시확정_표기가_레포에_없다(self):
        """표기를 없앴으면 규칙문 어디에도 남으면 안 된다.

        한 곳이라도 남으면 실행이 그것을 근거로 값을 대신 정한다 —
        이 레포는 정본과 실행부가 갈린 결함을 여섯 번 겪었다.
        """
        남은 = []
        for path in list((PLUGIN_ROOT / "templates").glob("*.md")) +                     list((PLUGIN_ROOT / "commands").glob("*.md")) +                     list((PLUGIN_ROOT / "skills").glob("*/SKILL.md")):
            if "임시확정" in path.read_text(encoding="utf-8"):
                남은.append(path.name)
        self.assertEqual(
            남은, [],
            f"임시확정 표기가 남아 있습니다: {남은}",
        )



class RequestHistoryTest(unittest.TestCase):
    """요청 이력이 값·답변·결론을 전부 남겨야 한다.

    시트 1·2 는 「지금 답해야 할 것」만 보여주므로 차수가 올라가면 지난 값이
    거기서 사라진다. 시트 3 이 그 값이 남는 **유일한 자리**다. 세 가지가
    지켜지지 않으면 이력이 반쪽이 된다 — 차수마다 새 행 · 시트 1 항목도 포함 ·
    마지막 행이 최종 결론.
    """

    def setUp(self):
        self.정본 = (
            PLUGIN_ROOT / "templates" / "confirmation-request.md"
        ).read_text(encoding="utf-8")
        self.스킬 = (
            PLUGIN_ROOT / "skills" / "apply-confirmations" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_처리값이_네_갈래다(self):
        """`반영`/`이월` 둘만으로는 「끝났나 진행 중인가」를 알 수 없다."""
        행 = re.search(r"^\|\s*6\s*\|\s*처리\s*\|([^\n|]*)\|", self.정본, re.M)
        self.assertIsNotNone(행, "시트 3 정본에 `처리` 열이 없습니다")
        for 값 in ("반영", "이월", "미해소", "철회"):
            with self.subTest(값=값):
                self.assertIn(값, 행.group(1), f"`처리` 값에 {값} 이 없습니다")

    def test_시트1도_이력에_남는다(self):
        구간 = re.search(
            r"^### 시트 1 과 시트 2 를 \*\*둘 다\*\* 받는다$(.*?)(?=^### )",
            self.정본, re.M | re.S,
        )
        self.assertIsNotNone(구간, "시트 1 도 이력에 남긴다는 절이 없습니다")
        self.assertRegex(
            구간.group(1), r"가정 확인[^.]*요청이다",
            "가정 확인도 요청이라는 근거가 없습니다",
        )

    def test_행을_덮어쓰지_않는다(self):
        구간 = re.search(
            r"^### 행을 덮어쓰지 않고 쌓는다$(.*?)(?=^### )", self.정본, re.M | re.S
        )
        self.assertIsNotNone(구간, "행을 쌓는다는 절이 없습니다")
        self.assertRegex(
            구간.group(1), r"차수마다[^\n]*새 행",
            "차수마다 새 행이라는 규칙이 없습니다",
        )

    def test_이월로_끝나는_항목이_없다(self):
        """마지막 행이 `이월` 이면 그 항목이 끝났는지 진행 중인지 알 수 없다."""
        self.assertRegex(
            self.정본, r"`이월` 로 끝나는 항목은 없다",
            "이월로 끝나지 않는다는 규칙이 정본에 없습니다",
        )
        self.assertRegex(
            self.스킬, r"3차인데 답이 없는 것[^\n]*미해소",
            "3차 미응답을 `미해소` 로 닫는 지시가 스킬에 없습니다",
        )

    def test_스킬이_이력_규칙을_정본으로_넘긴다(self):
        구간 = re.search(
            r"^### 시트 3 은 지우지 않고 쌓는다$(.*?)(?=^### )", self.스킬, re.M | re.S
        )
        self.assertIsNotNone(구간, "스킬에 시트 3 누적 규칙 절이 없습니다")
        self.assertIn(
            "templates/confirmation-request.md", 구간.group(1),
            "이력 규칙의 정본을 가리키지 않습니다",
        )



class CounterQuestionTest(unittest.TestCase):
    """값 대신 질문이 오면 파일로 답한다.

    1차 시험에서 `[미확정]` 두 건에 값이 아니라 자유 텍스트 요청이 달려 왔다 —
    「설명을 다시해줘」·「너가 직접 정해줘」. 분기표에 그 경우가 없어서 답변이
    **대화로만 나가고 파일에는 안 남았다.** 다음에 파일을 여는 사람은 질문만
    보고 답은 못 본다. 이 양식이 대화를 대신하려던 이유가 무너진다.
    """

    def setUp(self):
        self.스킬 = (
            PLUGIN_ROOT / "skills" / "apply-confirmations" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.정본 = (
            PLUGIN_ROOT / "templates" / "confirmation-request.md"
        ).read_text(encoding="utf-8")

    def test_분기표가_되질문을_다룬다(self):
        구간 = re.search(
            r"^### Step 2: 분기$(.*?)(?=^### )", self.스킬, re.M | re.S
        )
        self.assertIsNotNone(구간, "Step 2 분기 절이 없습니다")
        절 = 구간.group(1)
        행 = re.search(r"^\|[^\n|]*값 대신 질문[^\n|]*\|[^\n]*$", 절, re.M)
        self.assertIsNotNone(행, "분기표에 「값 대신 질문」 행이 없습니다")
        self.assertIn(
            "파일로 답한다", 행.group(0),
            "되질문에 대화로 답하지 않는다는 것이 분기표에 없습니다",
        )

    def test_되질문_절이_세_성격을_가른다(self):
        구간 = re.search(
            r"^### 되질문에 답한다$(.*?)(?=^### )", self.스킬, re.M | re.S
        )
        self.assertIsNotNone(구간, "§되질문에 답한다 절이 없습니다")
        절 = 구간.group(1)
        self.assertRegex(
            절, r"대화로 답하지 않는다",
            "대화로 답하지 않는다는 규칙이 없습니다",
        )
        for 성격, 처리 in (("설명해달라", "답을 먼저 적고"), ("네가 정해라", "가정"),
                          ("선택지", "근거")):
            with self.subTest(성격=성격):
                행 = re.search(rf"^\|[^\n|]*{re.escape(성격)}[^\n|]*\|[^\n]*$", 절, re.M)
                self.assertIsNotNone(행, f"「{성격}」 갈래가 없습니다")
                self.assertIn(
                    처리, 행.group(0),
                    f"「{성격}」 갈래의 처리가 「{처리}」 를 말하지 않습니다",
                )

    def test_정본_처리값에_되질문이_있다(self):
        행 = re.search(r"^\|\s*6\s*\|\s*처리\s*\|([^\n|]*)\|", self.정본, re.M)
        self.assertIsNotNone(행, "시트 3 정본에 `처리` 열이 없습니다")
        self.assertIn(
            "되질문", 행.group(1),
            "`처리` 값에 되질문이 없어 주고받은 것이 이력에 안 남습니다",
        )


if __name__ == "__main__":
    unittest.main()
