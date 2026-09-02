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
    return [(path, text) for path, text in docs if path.name != "CHANGELOG.md"]


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
                with self.subTest(문서=doc_label(path), 스킬=name):
                    self.assertIn(name, self.skills)

    def test_백틱으로_참조된_커맨드가_모두_존재한다(self):
        # CHANGELOG 는 개명 대응표에서 구 이름을 인용하므로 검사 대상에서 뺀다.
        for path, text in self.specs:
            for match in re.finditer(r"`/(gx-[가-힣A-Za-z-]+)`", text):
                with self.subTest(문서=doc_label(path), 커맨드=match.group(1)):
                    self.assertIn(match.group(1), self.commands)

    def test_참조된_템플릿_경로가_모두_존재한다(self):
        for path, text in self.docs:
            for match in re.finditer(r"templates/([A-Za-z0-9\-]+\.md)", text):
                with self.subTest(문서=doc_label(path), 템플릿=match.group(1)):
                    self.assertIn(match.group(1), self.templates)

    def test_참조된_스킬_경로가_모두_존재한다(self):
        for path, text in self.docs:
            for match in re.finditer(r"skills/([a-z0-9-]+)/SKILL\.md", text):
                with self.subTest(문서=doc_label(path), 스킬=match.group(1)):
                    self.assertIn(match.group(1), self.skills)

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
        사용자가 보는 것은 진입점 3종뿐이므로, 그 합집합이 전체 커맨드를 덮어야 한다.
        """
        진입점 = ("gx-프로젝트설정", "gx-spec", "gx-testplan")
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
        self.assertIn("화면ID", self.text)

    def test_이월_금지_항목에_화면_분리_미결정이_있다(self):
        """§이월 금지 항목 **절 안에서만** 검사한다.

        파일 전체를 substring 으로 훑으면 §재생성 파급 규칙의 '화면ID' 표기가
        조건을 채워버려, 이 항목이 이월 금지 목록에서 통째로 빠져도 통과한다.
        빠지면 /gx-spec 이 이 중단점을 게이트 1 로 미뤄도 아무도 모른다 —
        그때는 화면ID가 이미 채번된 뒤라 되돌리는 비용이 전건 재채번이다.
        """
        구간 = re.search(
            r"^## 이월 금지 항목$(.*?)(?=^## |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(
            구간,
            "pipeline-protocol.md 에서 '## 이월 금지 항목' 절을 찾지 못했습니다 "
            "— 절이 삭제됐거나 제목이 바뀌었습니다",
        )
        절 = 구간.group(1)
        항목 = re.findall(r"^\d+\. \*\*(.+?)\*\*", 절, re.M)
        self.assertEqual(
            len(항목), 5,
            f"이월 금지 항목이 5개가 아닙니다: {항목}",
        )
        self.assertTrue(
            any("화면 분리" in v for v in 항목),
            f"'화면 분리' 미결정 중단점이 이월 금지 항목에 없습니다: {항목}",
        )

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
        self.assertEqual(len(항목), 5, f"이월 금지 항목이 5개가 아닙니다: {항목}")
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
                     "화면 분리 미결정 중단점", "입력 수집 중단점"):
            with self.subTest(중단점=중단점):
                self.assertIn(
                    중단점, 본문,
                    f"'{중단점}' 이 단독/파이프라인 대조표에 없습니다",
                )

    def test_파생_ID가_모두_재생성_파급_규칙에_있다(self):
        """§재생성 파급 규칙 표 **안에서만** 검사한다.

        파일 전체를 substring 으로 훑으면 §이월 금지 항목의 산문
        ("화면ID가 바뀌면 PG_·U_·TC_ 가 전부 재채번된다") 이 조건을 채워버려,
        이 테스트가 지킨다고 선언한 파급 표가 통째로 사라져도 통과한다.
        """
        rules = (PLUGIN_ROOT / "templates" / "id-naming-rules.md").read_text(
            encoding="utf-8"
        )
        파생 = re.findall(r"\|\s*`(\w+_)`\s*\|[^|]*\|\s*\*\*화면ID", rules)
        self.assertEqual(
            set(파생), {"PG_", "U_", "TC_"},
            "id-naming-rules.md 의 화면ID 파생 목록이 바뀌었습니다",
        )

        구간 = re.search(
            r"^## 재생성 파급 규칙$(.*?)(?=^## |\Z)", self.text, re.M | re.S
        )
        self.assertIsNotNone(
            구간,
            "pipeline-protocol.md 에서 '## 재생성 파급 규칙' 절을 찾지 못했습니다 "
            "— 절이 삭제됐거나 제목이 바뀌었습니다",
        )
        표 = 구간.group(1)
        for 접두 in 파생:
            with self.subTest(접두=접두):
                self.assertIn(
                    접두, 표,
                    f"화면ID 파생 ID `{접두}` 가 재생성 파급 규칙 표에 없습니다 "
                    "— 화면ID 변경 시 무엇을 다시 만들지 규정되지 않습니다",
                )

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

    def test_화면목록표_커맨드가_유형별_동작을_복제하지_않는다(self):
        """유형별 동작의 정본은 skills/generate-screen-list/SKILL.md §3-2 다.

        커맨드에 동작을 축약해 적어두면 §3-2 가 바뀔 때 조용히 낡는다.
        최종 리뷰 전 실제로 그렇게 적혀 있어 한 번 걷어냈다 — 다시 들어오는 것을 막는다.
        커맨드는 '유형별 동작은 스킬 Step 3 이 정본이다' 라고만 적는다.
        """
        text = (PLUGIN_ROOT / "commands" / "gx-화면목록표.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(
            "묻지 않는다", text,
            "커맨드가 유형별 동작을 복제하고 있습니다 — "
            "skills/generate-screen-list/SKILL.md §3-2 를 참조로 두세요",
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


PIPELINE_ARTIFACTS = {
    "gx-spec": [
        "gx-요구사항정의서",
        "gx-화면목록표",
        "gx-프로그램정의서",
        "gx-인터페이스정의서",
        "gx-테이블정의서",
    ],
    "gx-testplan": [
        "gx-총괄테스트계획서",
        "gx-단위테스트계획서",
        "gx-통합테스트시나리오",
        "gx-시스템테스트",
    ],
}


class PipelineCommandTest(unittest.TestCase):
    """파이프라인은 묶은 산출물을 빠짐없이 만들고, 게이트를 2개 유지해야 한다."""

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

    def test_파이프라인에_필수_중단점이_2개_있다(self):
        for 이름 in PIPELINE_ARTIFACTS:
            if 이름 not in command_names():
                continue
            with self.subTest(파이프라인=이름):
                게이트 = re.findall(
                    r"^### Step \d+:.*\[필수 중단점", self._본문(이름), re.M
                )
                self.assertEqual(
                    len(게이트), 2,
                    f"게이트가 2개가 아닙니다: {게이트}",
                )

    def test_필수_중단점이_게이트_단계에만_붙어_있다(self):
        """개수만 세면 라벨을 엉뚱한 Step 으로 옮겨도 통과한다.

        게이트는 '무엇을 확정하는가' 로 이름이 붙는다 — 게이트 1 은 ID·종료기준 확정,
        게이트 2 는 일괄 검토다. 저장·xlsx 처럼 판단이 없는 단계로 라벨이 옮겨 붙으면
        사용자가 멈춰서 확인할 지점이 사라지는데, 개수는 그대로라 아무도 모른다.
        """
        for 이름 in PIPELINE_ARTIFACTS:
            if 이름 not in command_names():
                continue
            제목들 = re.findall(
                r"^### Step \d+:(.*?)\[필수 중단점\]", self._본문(이름), re.M
            )
            with self.subTest(파이프라인=이름):
                self.assertEqual(
                    len(제목들), 2,
                    f"[필수 중단점] 이 2개가 아닙니다: {제목들}",
                )
                for 순번, 제목 in enumerate(제목들, start=1):
                    self.assertIn(
                        f"게이트 {순번}", 제목,
                        f"{순번}번째 [필수 중단점] 이 '게이트 {순번}' 단계가 아닙니다 "
                        f"— 라벨이 판단 없는 단계로 옮겨졌습니다: {제목.strip()!r}",
                    )

    def test_파이프라인_산출물이_파생_순서대로_나온다(self):
        """산출물 순서는 이 기능의 전제다.

        화면목록표가 확정돼야 `PG_`·`U_`·`TC_` 가 파생되고, 총괄 테스트계획서의
        종료기준이 확정돼야 뒤 3종의 판정 기준이 정해진다. 참조 '존재' 만 검사하면
        순서를 뒤집어도 통과하는데, 뒤집힌 순서는 파이프라인을 무의미하게 만든다.
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

    def test_gx_spec_이_화면_분리_중단점을_선언한다(self):
        """이 중단점은 라벨(`[필수 중단점]`)을 달 수 없다 — 게이트가 3개가 되기 때문이다.

        라벨이 없으니 게이트 개수 정규식이 세지 못하고, 문단을 지워도 아무 테스트도
        걸리지 않았다. 문단이 사라지면 /gx-spec 은 화면 분리 미결정에서 멈추지 않고
        게이트 1 까지 간다 — 그때는 화면ID가 이미 채번된 뒤다.
        """
        본문 = self._본문("gx-spec")
        구간 = re.search(
            r"^### Step 3:(.*?)(?=^### |\Z)", 본문, re.M | re.S
        )
        self.assertIsNotNone(구간, "gx-spec.md 에서 '### Step 3:' 절을 찾지 못했습니다")
        절 = 구간.group(1)
        self.assertIn(
            "skills/generate-screen-list/SKILL.md", 절,
            "Step 3 이 화면 분리 판정의 정본을 참조하지 않습니다",
        )
        self.assertRegex(
            절, r"결정하지 않은[^\n]*중단한다",
            "Step 3 에 화면 분리 미결정 중단 선언이 없습니다",
        )


class VersionConsistencyTest(unittest.TestCase):
    """버전과 개수 표기가 11개 지점에 흩어져 있어 한쪽만 갱신되기 쉽다.

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
        self.codex_plugin_json = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.skill_count = len(skill_names())
        self.command_count = len(command_names())

    def test_모든_매니페스트의_버전이_같다(self):
        version = self.plugin_json["version"]
        self.assertEqual(self.marketplace["plugins"][0]["version"], version)
        self.assertEqual(re.search(r"version-([\d.]+)-blue", self.readme).group(1), version)
        self.assertEqual(re.search(r"## \[([\d.]+)\]", self.changelog).group(1), version)
        self.assertEqual(
            self.codex_plugin_json["version"], version,
            ".codex-plugin/plugin.json 의 버전이 다릅니다 "
            "— Codex UI 에 옛 버전이 표시됩니다",
        )

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


class ScreenSplitRuleTest(unittest.TestCase):
    """화면 분리 미결정 규칙의 정본은 generate-screen-list/SKILL.md Step 3 다.

    문서가 화면 수를 말하지 않는데 추론표를 그냥 적용하면, 그 수가 화면ID가 되고
    pipeline-protocol.md §재생성 파급 규칙이 통째로 발동한다 — PG_·U_·TC_ 전건이
    나중에 재채번된다. 그래서 '추정 전에 판정한다' 는 규칙이 문서에 살아 있어야 한다.
    """

    def setUp(self):
        self.text = (
            PLUGIN_ROOT / "skills" / "generate-screen-list" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def _step3(self) -> str:
        구간 = re.search(r"^### Step 3:(.*?)(?=^### |\Z)", self.text, re.M | re.S)
        self.assertIsNotNone(
            구간,
            "generate-screen-list/SKILL.md 에서 '### Step 3:' 절을 찾지 못했습니다 "
            "— 절이 삭제됐거나 제목이 바뀌었습니다",
        )
        return 구간.group(1)

    def _표_행(self, 머리조건) -> list[list[str]]:
        """머리행 조건을 만족하는 표의 본문 행을 (구분선 제외) 반환한다."""
        줄들 = self._step3().splitlines()
        시작 = next(
            (
                i
                for i, l in enumerate(줄들)
                if l.strip().startswith("|") and 머리조건(l)
            ),
            None,
        )
        self.assertIsNotNone(시작, "표의 머리행을 찾지 못했습니다")
        행: list[list[str]] = []
        for l in 줄들[시작 + 1 :]:
            if not l.strip().startswith("|"):
                break
            칸 = [c.strip() for c in l.strip().strip("|").split("|")]
            if set("".join(칸)) <= set("-: "):
                continue  # 구분선
            행.append(칸)
        return 행

    def test_미결정_판정이_양쪽으로_나뉘어_있다(self):
        """한쪽만 있으면 판정이 아니라 목록이다.

        '미결정이다' 만 있으면 무엇이 결정된 것인지 알 수 없어 전건이 미결정이 되고,
        '결정돼 있다' 만 있으면 판정 자체가 사라진다.
        """
        행 = self._표_행(lambda l: "미결정이다" in l and "결정돼 있다" in l)
        self.assertGreaterEqual(
            len(행), 3,
            f"미결정 판정표의 본문 행이 3개 미만입니다: {len(행)}개",
        )
        for 왼, 오 in (r[:2] for r in 행):
            with self.subTest(행=왼[:20]):
                self.assertTrue(왼, "판정표 '미결정이다' 칸이 비어 있습니다")
                self.assertTrue(오, "판정표 '결정돼 있다' 칸이 비어 있습니다")

    def test_프로젝트_유형_네_가지의_동작이_모두_정의돼_있다(self):
        """A·B·C·D 중 하나라도 빠지면 그 유형은 규칙 없이 실행된다."""
        행 = self._표_행(lambda l: "유형" in l and "동작" in l and "근거" in l)
        유형들 = [r[0] for r in 행]
        for 유형 in ("A", "B", "C", "D"):
            with self.subTest(유형=유형):
                self.assertTrue(
                    any(f"**{유형}**" in v for v in 유형들),
                    f"유형 {유형} 의 동작이 정의돼 있지 않습니다: {유형들}",
                )

    def test_D_유형은_화면_분리를_묻지_않는다(self):
        """D(변경 관리)에서 화면 분리를 물으면 답에 따라 기존 화면ID가 바뀔 수 있다.

        화면ID가 바뀌면 PG_·U_·TC_ 전건이 재채번된다 — 운영 중 시스템의 변경 건에서
        그 파급은 변경 범위를 통째로 벗어난다.
        """
        행 = self._표_행(lambda l: "유형" in l and "동작" in l and "근거" in l)
        D행 = [r for r in 행 if "**D**" in r[0]]
        self.assertEqual(len(D행), 1, f"유형 D 행이 1개가 아닙니다: {len(D행)}개")
        self.assertIn(
            "묻지 않는다", D행[0][1],
            "D(변경 관리)가 화면 분리를 묻게 돼 있습니다 "
            f"— 기존 화면ID가 바뀌면 후속 산출물이 전부 재채번됩니다: {D행[0][1]!r}",
        )

    def test_A_와_C_유형은_화면_분리를_묻는다(self):
        """D 만 고정돼 있고 A·C 는 무방비였다.

        A 행의 '묻는다' 를 '묻지 않는다' 로 바꿔도 전 스위트가 통과했다.
        A(신규 구축)는 이 기능의 주 대상이다 — RFP 밖에 화면 분리의 근거가 없으므로
        묻지 않으면 조용히 추정하게 되고, 그것이 이 판정이 막으려던 일이다.
        """
        행 = self._표_행(lambda l: "유형" in l and "동작" in l and "근거" in l)
        for 유형 in ("A", "C"):
            with self.subTest(유형=유형):
                해당 = [r for r in 행 if f"**{유형}**" in r[0]]
                self.assertEqual(
                    len(해당), 1, f"유형 {유형} 행이 1개가 아닙니다: {len(해당)}개"
                )
                self.assertIn(
                    "묻는다", 해당[0][1],
                    f"유형 {유형} 가 화면 분리를 묻지 않게 돼 있습니다 "
                    f"— 근거 없이 화면 수를 추정하게 됩니다: {해당[0][1]!r}",
                )

    def test_미결정_판정이_추론표보다_앞선다(self):
        """'추정하기 전에 판정한다' 가 이 규칙의 전부다 (설계서 §2.1).

        판정 블록을 통째로 추론표 뒤로 옮겨도 다른 테스트는 전부 통과한다 —
        표가 존재하는지만 보고 순서는 아무도 보지 않기 때문이다. 뒤에 있으면
        Claude 는 추론표로 화면 수를 먼저 정한 뒤에 판정을 읽는다. 이미 추정한
        뒤라 판정이 아무 일도 하지 않는다.
        """
        step3 = self._step3()
        판정 = step3.find("미결정이다")
        추론 = step3.find("요구사항 패턴")
        self.assertNotEqual(판정, -1, "미결정 판정표를 찾지 못했습니다")
        self.assertNotEqual(추론, -1, "화면 수 추론표를 찾지 못했습니다")
        self.assertLess(
            판정, 추론,
            "미결정 판정이 화면 수 추론표보다 뒤에 있습니다 "
            "— 추정한 뒤에 판정하면 판정이 아무 일도 하지 않습니다",
        )

    def test_기록_규칙이_DE_03_의_실제_컬럼을_지목한다(self):
        """기록 규칙이 없는 컬럼을 지목하면 xlsx 추출에서 조용히 사라진다.

        화면 수의 근거는 감리 대상이고 xlsx 가 납품물이다. 규칙이 지목한 컬럼명과
        templates/DE-03-screen-list.md 의 컬럼 목록을 묶어 갈라질 수 없게 한다.
        """
        칸 = re.search(r"해당 행의 `([^`]+)` 열", self._step3())
        self.assertIsNotNone(
            칸,
            "기록 규칙에서 '해당 행의 `{컬럼}` 열' 표기를 Step 3 안에서 찾지 못했습니다 "
            "— 기록할 자리가 정의되지 않았습니다",
        )
        컬럼 = 칸.group(1)
        템플릿 = (
            PLUGIN_ROOT / "templates" / "DE-03-screen-list.md"
        ).read_text(encoding="utf-8")
        # DE-03 템플릿의 컬럼 정의표는 세로형이다 — 각 행의 첫 칸이 컬럼명이고,
        # 둘째 칸이 설명이다. 머리행(`| 컬럼 | 설명 |`)과 구분선은 제외한다.
        컬럼명들 = []
        for 줄 in 템플릿.splitlines():
            벗긴줄 = 줄.strip()
            if not (벗긴줄.startswith("|") and 벗긴줄.endswith("|")):
                continue
            칸 = [c.strip() for c in 벗긴줄.strip("|").split("|")]
            if len(칸) < 2 or set("".join(칸)) <= set("-: "):
                continue  # 구분선
            if 칸[0] == "컬럼":
                continue  # 머리행
            컬럼명들.append(칸[0])
        self.assertIn(
            컬럼, 컬럼명들,
            f"기록 규칙이 지목한 `{컬럼}` 이 DE-03 템플릿의 컬럼이 아닙니다 "
            "— 기록해도 xlsx 추출에서 사라집니다",
        )

    def test_이미_기록된_기준은_다시_묻지_않는다(self):
        """재질문 금지 규칙이 없으면 이어쓰기·재실행 때마다 같은 것을 다시 묻는다.

        B(추가 개발)와 D(변경 관리)가 기존 기준을 따른다는 §3-2 의 규정도
        '기록된 기준을 읽는다' 는 이 규칙 위에 서 있다.
        """
        step3 = self._step3()
        self.assertIn(
            "화면 분리 기준:", step3,
            "기록 형식 '화면 분리 기준:' 이 Step 3 에 없습니다",
        )
        self.assertRegex(
            step3, r"이미 있으면[^\n]*묻지 않는다",
            "재질문 금지 규칙이 없습니다 — 재실행 때마다 같은 것을 다시 묻게 됩니다",
        )


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


if __name__ == "__main__":
    unittest.main()
