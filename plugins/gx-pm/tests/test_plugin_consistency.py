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
    read_docs,
    skill_names,
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
            with self.subTest(문서=path.relative_to(PLUGIN_ROOT)):
                self.assertNotIn(
                    "gx-gx-", text,
                    "일괄 치환이 두 번 적용됐습니다",
                )

    def test_접두어_없는_커맨드_참조가_남아있지_않다(self):
        구커맨드 = re.compile(r"`/(?!gx-)[가-힣]+`")
        for path, text in specs_only(read_docs()):
            with self.subTest(문서=path.relative_to(PLUGIN_ROOT)):
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

    def test_참조된_스킬이_모두_존재한다(self):
        pattern = re.compile(r"\*\*([a-z][a-z0-9-]{4,})\*\*\s*스킬|`([a-z][a-z0-9-]{4,})`\s*스킬")
        for path, text in self.docs:
            for match in pattern.finditer(text):
                name = match.group(1) or match.group(2)
                with self.subTest(문서=path.relative_to(PLUGIN_ROOT), 스킬=name):
                    self.assertIn(name, self.skills)

    def test_백틱으로_참조된_커맨드가_모두_존재한다(self):
        # CHANGELOG 는 개명 대응표에서 구 이름을 인용하므로 검사 대상에서 뺀다.
        for path, text in self.specs:
            for match in re.finditer(r"`/(gx-[가-힣A-Za-z-]+)`", text):
                with self.subTest(문서=path.relative_to(PLUGIN_ROOT), 커맨드=match.group(1)):
                    self.assertIn(match.group(1), self.commands)

    def test_참조된_템플릿_경로가_모두_존재한다(self):
        for path, text in self.docs:
            for match in re.finditer(r"templates/([A-Za-z0-9\-]+\.md)", text):
                with self.subTest(문서=path.relative_to(PLUGIN_ROOT), 템플릿=match.group(1)):
                    self.assertIn(match.group(1), self.templates)

    def test_참조된_스킬_경로가_모두_존재한다(self):
        for path, text in self.docs:
            for match in re.finditer(r"skills/([a-z0-9-]+)/SKILL\.md", text):
                with self.subTest(문서=path.relative_to(PLUGIN_ROOT), 스킬=match.group(1)):
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
            "진입점(프로젝트설정·파이프라인 2종)에서 안내되지 않는 커맨드가 있습니다 "
            "— 신규 사용자가 도달할 수 없습니다",
        )


class LegacyReferenceTest(unittest.TestCase):
    def setUp(self):
        self.docs = specs_only(read_docs())

    def test_존재하지_않는_pm_커맨드를_안내하지_않는다(self):
        for path, text in self.docs:
            with self.subTest(문서=path.relative_to(PLUGIN_ROOT)):
                self.assertNotIn(
                    "/pm-", text,
                    "구 커맨드(/pm-design·/pm-test·/pm-trace) 참조가 남아 있습니다",
                )

    def test_예시_ID_가_네이밍_규칙을_따른다(self):
        # 화면ID 는 {접두}_{xx}_{xx}_{xxx}, 시나리오ID 는 {시스템코드}-TE-{순번}
        forbidden = re.compile(r"\bSCR-\d|\bSC-\d|\bSN-\d")
        for path, text in self.docs:
            with self.subTest(문서=path.relative_to(PLUGIN_ROOT)):
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

    def test_파생_ID가_모두_재생성_파급_규칙에_있다(self):
        rules = (PLUGIN_ROOT / "templates" / "id-naming-rules.md").read_text(
            encoding="utf-8"
        )
        파생 = re.findall(r"\|\s*`(\w+_)`\s*\|[^|]*\|\s*\*\*화면ID", rules)
        self.assertEqual(
            set(파생), {"PG_", "U_", "TC_"},
            "id-naming-rules.md 의 화면ID 파생 목록이 바뀌었습니다",
        )
        for 접두 in 파생:
            with self.subTest(접두=접두):
                self.assertIn(접두, self.text)

    def test_중단_후_재개_규칙이_있다(self):
        self.assertIn("detect-existing-artifact", self.text)


class DocumentCodeTest(unittest.TestCase):
    """산출물 코드 정본은 CLAUDE.md 의 '산출물 범위' 표다."""

    def setUp(self):
        self.docs = specs_only(read_docs())

    def test_테이블정의서는_DE_08_이다(self):
        wrong = re.compile(r"테이블정의서\s*\(?DE-09|DE-09\s*테이블정의서")
        for path, text in self.docs:
            with self.subTest(문서=path.relative_to(PLUGIN_ROOT)):
                self.assertIsNone(wrong.search(text), "테이블정의서는 DE-08 입니다")

    def test_인터페이스정의서는_DE_04_이다(self):
        wrong = re.compile(r"인터페이스정의서\s*\|\s*DE-07|DE-07\s*인터페이스정의서")
        for path, text in self.docs:
            with self.subTest(문서=path.relative_to(PLUGIN_ROOT)):
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
                    맨커맨드.findall(본문), [],
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

    def test_파이프라인이_규약_템플릿을_참조한다(self):
        for 이름 in PIPELINE_ARTIFACTS:
            if 이름 not in command_names():
                continue
            with self.subTest(파이프라인=이름):
                본문 = self._본문(이름)
                self.assertIn("templates/pipeline-protocol.md", 본문)
                self.assertIn("templates/prerequisites.md", 본문)


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
