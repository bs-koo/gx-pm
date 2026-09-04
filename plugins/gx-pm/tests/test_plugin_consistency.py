"""스킬·커맨드·템플릿·매니페스트 간 계약 테스트.

v1.5.0 에서 수작업으로 찾은 불일치 10건이 재발하지 않도록 고정한다.
실패하면 문서 편집 실수이지 로직 버그가 아니다.
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
        진입점 = ("gx-프로젝트설정", "gx-spec")
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
                "gx-프로젝트설정", "gx-spec",
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
        text = (PLUGIN_ROOT / "commands" / "gx-spec.md").read_text(encoding="utf-8")
        순서 = [
            "/gx-요구사항정의서", "/gx-기능명세서", "/gx-테이블정의서",
            "/gx-단위테스트계획서", "/gx-추적매트릭스",
        ]
        위치 = [text.find(c) for c in 순서]
        self.assertNotIn(-1, 위치, f"파이프라인에 빠진 커맨드가 있습니다: {순서}")
        self.assertEqual(위치, sorted(위치), "파이프라인 산출물이 파생 순서대로가 아닙니다")

    def test_spec_파이프라인에_게이트가_세_개다(self):
        text = (PLUGIN_ROOT / "commands" / "gx-spec.md").read_text(encoding="utf-8")
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

    def test_이월_금지_항목이_세_개다(self):
        """화면 축 제거로 화면 분리·ID 확정 두 항목이 소멸했다."""
        구간 = re.search(
            r"^## 이월 금지 항목$(.*?)(?=^## |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(구간, "이월 금지 항목 절을 찾지 못했습니다")
        번호 = re.findall(r"^\d+\.\s", 구간.group(1), re.M)
        self.assertEqual(
            len(번호), 3,
            f"이월 금지 항목이 3개가 아닙니다: {len(번호)}개",
        )

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
        규약의 어느 표에도 분류돼 있지 않았다. 분류되지 않으면 /gx-spec 실행 중
        Claude 는 거기서 멈춰야 하는지 게이트 1 로 미뤄야 하는지 지시를 받지 못한다.
        """
        구간 = re.search(
            r"^## 이월 금지 항목$(.*?)(?=^## |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(
            구간, "pipeline-protocol.md 에서 '## 이월 금지 항목' 절을 찾지 못했습니다"
        )
        항목 = re.findall(r"^\d+\. \*\*(.+?)\*\*", 구간.group(1), re.M)
        self.assertEqual(len(항목), 3, f"이월 금지 항목이 3개가 아닙니다: {항목}")
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


# v3.0.0 기능 축 전환으로 파이프라인은 `/gx-spec` 하나만 남았다.
# `/gx-testplan` 과 화면 축 산출물은 archive/ 에 있다 — 되살리는 법은 archive/README.md.
PIPELINE_ARTIFACTS = {
    "gx-spec": [
        "gx-요구사항정의서",
        "gx-기능명세서",
        "gx-테이블정의서",
        "gx-단위테스트계획서",
        "gx-추적매트릭스",
    ],
}

# 파이프라인별 게이트 수. 게이트는 사용자가 멈춰서 판단하는 자리이므로
# 개수가 조용히 줄면 승인 없이 지나가는 산출물이 생긴다.
PIPELINE_GATES = {"gx-spec": 3}


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

    # 이월 금지 중단점이 gx-spec.md 의 어느 Step 에서 지켜지는가.
    # 정본은 templates/pipeline-protocol.md §이월 금지 항목이고, 이 표는 그 항목들이
    # 파이프라인 본문의 어디에 내려앉는지를 적는다. 항목이 늘면 여기도 늘려야 하며,
    # 늘리지 않으면 아래 개수 대조가 잡는다.
    이월금지_중단점 = [
        {
            "step": "2",
            "중단점": ["시안", "표 판정"],
            "정본": ["skills/extract-requirements/SKILL.md"],
        },
        {
            "step": "5",
            "중단점": ["신규 컬럼명"],
            "정본": ["skills/convert-ddl-to-tablespec/SKILL.md"],
        },
    ]

    def test_gx_spec_이_이월_금지_중단점을_선언한다(self):
        """이월 금지 중단점은 `[필수 중단점]` 라벨을 달 수 없다 — 게이트 수가 틀어진다.

        라벨이 없으니 게이트 개수 정규식이 세지 못하고, 문단을 통째로 지워도 아무 테스트도
        걸리지 않는다. 문단이 사라지면 /gx-spec 은 그 자리에서 멈추지 않고 다음 게이트까지
        간다 — 그때는 이미 그 판정 위에 뒤 산출물이 다 만들어진 뒤다.

        **Step 절로 범위를 좁혀서 본다.** 파일 전체에서 낱말의 존재만 세면 결속이 없다.
        `이월하지 않는다` 는 두 Step 에 각각 있으므로 한쪽을 통째로 지워도 파일 어딘가에
        남고, "그 자리에서 묻는다" 를 "게이트에서 함께 본다" 로 바꿔도 — 이 테스트가
        막으려는 바로 그 회귀인데 — 낱말과 정본 경로는 그대로라 초록으로 통과한다.
        그래서 절 안에서 낱말·정본 경로·동작 문장을 **함께** 본다.

        종전에는 화면 분리 미결정 중단점을 같은 취지로 고정하고 있었다. 화면 축이
        사라지면서 그 중단점은 소멸했고, 남은 세 항목이 같은 위험을 물려받는다.
        """
        본문 = self._본문("gx-spec")
        for 항목 in self.이월금지_중단점:
            구간 = re.search(
                rf"^### Step {항목['step']}:(.*?)(?=^### |\Z)", 본문, re.M | re.S
            )
            self.assertIsNotNone(
                구간,
                f"gx-spec.md 에서 '### Step {항목['step']}:' 절을 찾지 못했습니다",
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
        선언된것 = [낱말 for 항목 in self.이월금지_중단점 for 낱말 in 항목["중단점"]]
        self.assertEqual(
            len(선언된것), len(규약항목),
            f"규약의 이월 금지 항목 {len(규약항목)}개 중 gx-spec.md 가 선언하는 것은 "
            f"{len(선언된것)}개입니다: 규약={규약항목} / 선언={선언된것}",
        )
        for 낱말 in 선언된것:
            with self.subTest(중단점=낱말):
                self.assertTrue(
                    any(낱말 in 항목 for 항목 in 규약항목),
                    f"'{낱말}' 이 규약의 이월 금지 항목에 없습니다: {규약항목}",
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

    def test_확인필요가_두_종류로_갈린다(self):
        for 종류 in ("[확인필요:항목]", "[확인필요:제약]"):
            with self.subTest(종류=종류):
                self.assertIn(종류, self.text, f"{종류} 정의가 없습니다")

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

    def test_제약_미상은_자동보강하지_않는다(self):
        self.assertIn("제약 미상", self.text)
        self.assertIn("지어내", self.text)

    def test_AN_03_이_근거_정본을_참조한다(self):
        an03 = (PLUGIN_ROOT / "templates" / "AN-03-function-spec.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("templates/evidence-rules.md", an03)
        self.assertIn("[확인필요:제약]", an03)

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

    def test_기능명세_스킬이_확인필요_두_종류를_모두_안다(self):
        """정본만 고치고 실행부를 안 고치면 규칙이 돌지 않는다."""
        스킬 = (
            PLUGIN_ROOT / "skills" / "generate-function-spec" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for 종류 in ("[확인필요:항목]", "[확인필요:제약]"):
            with self.subTest(종류=종류):
                self.assertIn(종류, 스킬)
        self.assertIn("templates/evidence-rules.md", 스킬)
        for 집계 in ("근거 가용도", "제약 미상"):
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
        self.assertIn("제약 미상", 스킬)
        self.assertIn("templates/evidence-rules.md", 스킬)
        구간 = re.search(
            r"^### Step 6: 충분성 검증$(.*?)(?=^### |\Z)", 스킬, re.M | re.S
        )
        self.assertIsNotNone(구간, "generate-unit-test-plan 의 Step 6 절을 찾지 못했습니다")
        self.assertIn("제약 미상", 구간.group(1))
        self.assertRegex(
            구간.group(1), r"보강하지 않는다|지어내",
            "Step 6 에 '제약이 없으면 보강하지 않는다' 는 지시가 없습니다",
        )

    def test_게이트2가_근거_집계를_보여준다(self):
        """계측하고 안 보여주면 계측하지 않은 것과 같다.

        Step 절로 범위를 좁혀서 본다 — 파일 어딘가에 낱말이 있는 것으로는
        게이트 화면에 실린다는 보장이 안 된다.
        """
        본문 = (PLUGIN_ROOT / "commands" / "gx-spec.md").read_text(encoding="utf-8")
        구간 = re.search(
            r"^### Step 6: 게이트 2(.*?)(?=^### |\Z)", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "gx-spec.md 에서 Step 6(게이트 2) 절을 찾지 못했습니다")
        for 항목 in ("근거 가용도", "[확인필요]", "제약 미상"):
            with self.subTest(항목=항목):
                self.assertIn(항목, 구간.group(1), f"게이트 2 에 '{항목}' 이 없습니다")
        self.assertIn("templates/evidence-rules.md", 구간.group(1))

    def test_게이트3이_제약_미상을_보여준다(self):
        본문 = (PLUGIN_ROOT / "commands" / "gx-spec.md").read_text(encoding="utf-8")
        구간 = re.search(
            r"^### Step 9: 게이트 3(.*?)(?=^### |\Z)", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "gx-spec.md 에서 Step 9(게이트 3) 절을 찾지 못했습니다")
        self.assertIn("제약 미상", 구간.group(1))


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
        self.assertIn("manage-revision-history", self.text)

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
            ("DE-13-unit-test-plan.md", 11),
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


if __name__ == "__main__":
    unittest.main()
