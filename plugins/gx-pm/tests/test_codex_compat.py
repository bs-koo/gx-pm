"""Codex 하네스 호환 계약 테스트.

근거: oh-my-gx `.claude/rules/harness-codex.md` (Codex CLI 0.130.0 실측)
와 그 저장소의 동작하는 매니페스트 실물.

Codex 는 Claude Code 의 플러그인 규격을 그대로 채택했지만 매니페스트 위치와
지원 컴포넌트가 다르다. 한쪽만 갱신되면 Codex UI 에 옛 버전이 표시되거나
등록 자체가 실패하는데, 사람이 두 파일을 대조하는 방식으로는 반드시 어긋난다.
"""

import json
import re
import unittest

from helpers import (
    PLUGIN_ROOT,
    REPO_ROOT,
    command_names,
    doc_label,
    runtime_docs,
    skill_names,
)

CODEX_PLUGIN = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CODEX_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
CLAUDE_PLUGIN = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"


class CodexManifestTest(unittest.TestCase):
    """Codex 매니페스트가 Claude 매니페스트와 어긋나지 않는지."""

    def setUp(self):
        self.codex = json.loads(CODEX_PLUGIN.read_text(encoding="utf-8"))
        self.claude = json.loads(CLAUDE_PLUGIN.read_text(encoding="utf-8"))
        self.codex_market = json.loads(CODEX_MARKETPLACE.read_text(encoding="utf-8"))
        self.claude_market = json.loads(CLAUDE_MARKETPLACE.read_text(encoding="utf-8"))

    def test_codex_매니페스트에_commands_필드가_없다(self):
        """Codex plugin.json 이 지원하는 컴포넌트는 skills·hooks·mcpServers·apps 넷이다.

        commands 를 남겨두면 Codex 는 모르는 필드로 무시하지만, 남아 있는 것 자체가
        '커맨드가 Codex 에서 동작한다' 는 오해를 만든다. 커맨드 16개는 실리지 않는다.
        """
        self.assertNotIn(
            "commands", self.codex,
            "Codex 는 commands 컴포넌트를 지원하지 않습니다 — 필드를 지우세요",
        )

    def test_두_매니페스트가_같은_스킬_경로를_가리킨다(self):
        """스킬 본문은 단일 소스다. 하네스별로 복제하지 않는다."""
        self.assertEqual(
            self.codex["skills"], self.claude["skills"],
            "스킬 경로가 갈라졌습니다 — 스킬 본문은 한 벌만 유지합니다",
        )

    def test_두_매니페스트의_이름과_설명이_같다(self):
        """설명이 갈라지면 Codex UI 에만 옛 문구가 남는다.

        같게 묶어두면 test_설명문의_스킬_커맨드_수가_실제와_같다 의 개수 검사도
        Codex 쪽에 자동으로 적용된다 — 검사를 복제하지 않고 값을 묶는 쪽을 택했다.
        """
        self.assertEqual(self.codex["name"], self.claude["name"])
        self.assertEqual(self.codex["description"], self.claude["description"])

    def test_두_매니페스트의_공통_메타데이터가_같다(self):
        """이름·설명 말고도 네 필드가 글자 단위로 복제돼 있다.

        갈라져도 기능은 안 깨지고 Codex UI 에만 낡은 값이 뜬다 — 그래서 더
        오래 방치된다. keywords 는 14개짜리 리스트라 손으로 맞추면 반드시 어긋난다.
        license 는 일부러 뺐다: 참조 구현(oh-my-gx)도 Codex 쪽에만 두므로
        비대칭 자체가 규격이다.
        """
        for 필드 in ("author", "homepage", "repository", "keywords"):
            with self.subTest(필드=필드):
                self.assertEqual(
                    self.codex[필드], self.claude[필드],
                    f"{필드} 가 두 매니페스트에서 갈라졌습니다",
                )

    def test_codex_매니페스트에_interface_블록이_있다(self):
        """Codex TUI 의 플러그인 카드가 읽는 블록이다. 없으면 표시가 빈다.

        Claude 매니페스트에는 없는 필드라 '복사 후 commands 만 제거' 로는 생기지 않는다.
        """
        self.assertIn("interface", self.codex)
        for 필드 in ("displayName", "shortDescription", "category", "capabilities"):
            with self.subTest(필드=필드):
                self.assertIn(필드, self.codex["interface"])

    def test_codex_마켓플레이스가_플러그인_디렉터리를_가리킨다(self):
        """참조 구현(oh-my-gx)의 url 은 './' 다 — 저장소 루트가 곧 플러그인 루트라서다.

        gx-pm 은 플러그인이 plugins/gx-pm 아래에 있다. './' 를 그대로 베끼면
        Codex 가 저장소 루트에서 plugin.json 을 찾다 실패한다.
        """
        entry = next(
            p for p in self.codex_market["plugins"] if p["name"] == self.claude["name"]
        )
        claude_entry = next(
            p for p in self.claude_market["plugins"] if p["name"] == self.claude["name"]
        )
        self.assertEqual(entry["name"], self.claude["name"])
        self.assertEqual(
            entry["source"]["url"],
            claude_entry["source"],
            "Codex 마켓플레이스의 url 이 Claude 쪽 source 와 다른 곳을 가리킵니다",
        )

    def test_codex_마켓플레이스의_source_가_객체다(self):
        """Claude 는 문자열('./plugins/gx-pm'), Codex 는 {source, url} 객체다.

        스키마 차이라 문자열을 그대로 두면 파싱에서 걸린다.
        """
        entry = next(
            p for p in self.codex_market["plugins"] if p["name"] == self.claude["name"]
        )
        source = entry["source"]
        self.assertIsInstance(source, dict)
        self.assertEqual(source["source"], "url")


class HarnessCompatTest(unittest.TestCase):
    """Codex 호환을 유지하는 조건. 지금 0건인 것을 0건으로 묶는다.

    oh-my-gx 는 아래 세 패턴 때문에 27곳·44곳·17개를 고쳐야 했다. gx-pm 은
    처음부터 깨끗하므로 재발만 막으면 된다.

    검사 대상은 runtime_docs() — 런타임에 '지시'로 읽히는 문서뿐이다.
    read_docs() 를 쓰면 이 패턴을 *설명하는* 문서(CHANGELOG·docs/)가
    이 패턴을 *쓰는* 문서로 오인돼 실패한다.
    """

    def setUp(self):
        self.docs = runtime_docs()

    def test_런타임_문서가_비어있지_않다(self):
        """세 디렉터리가 모두 사라져도 위 세 검사는 0건을 훑고 통과한다.

        templates/ 이동이 후속 작업으로 예고돼 있어 실현 가능성이 높은 시나리오다.
        """
        self.assertGreater(len(self.docs), 0, "런타임 문서를 하나도 찾지 못했습니다")

    def test_절대경로_조립_변수를_쓰지_않는다(self):
        """${CLAUDE_PLUGIN_ROOT} 는 Codex 스킬 루트에서 설정된다는 보장이 없다.

        변수가 비면 플러그인이 아니라 작업 중인 프로젝트 루트를 뒤지다 파일을
        찾지 못한다. 파일 위치 기준 상대경로를 쓴다 — 파일 사이의 상대 위치는
        설치 위치와 무관하므로 두 하네스에서 모두 해석된다.
        """
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertNotIn(
                    "CLAUDE_PLUGIN_ROOT", text,
                    "절대경로 조립 변수가 들어왔습니다 "
                    "— 이 파일 위치 기준 상대경로로 바꾸세요",
                )

    def test_Skill_도구로_다른_스킬을_호출하지_않는다(self):
        """Codex 에는 Skill() 에 해당하는 도구가 없다.

        gx-pm 은 '**스킬명** 스킬로 …' 라는 산문 지시만 쓴다 — 그 형태는
        양쪽에서 같이 동작한다. 도구 호출 형태가 들어오는 순간 Codex 에서 죽는다.
        oh-my-gx 는 44곳을 '해당 SKILL.md 를 읽고 절차를 따른다' 로 옮겨야 했다.
        """
        패턴 = re.compile(r"\bSkill\s*\(")
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertEqual(
                    패턴.findall(text), [],
                    "Skill() 도구 호출이 들어왔습니다 "
                    "— '스킬명 스킬로 …' 산문 지시로 바꾸세요",
                )

    def test_Task_로_서브에이전트를_띄우지_않는다(self):
        """Codex plugin.json 에 agents 필드가 없어 에이전트 정의를 실을 수 없다.

        ~/.codex/agents/ 수동 배치도 0.130 에서 로드되지 않았다(노출 0건, 실측).
        gx-pm 은 서브에이전트를 쓰지 않으므로 이 제약에 걸리지 않는다 — 그 상태를
        유지한다. 들어오면 Codex 사용자에게는 그 단계가 통째로 사라진다.
        """
        패턴 = re.compile(r"\bTask\s*\(")
        for path, text in self.docs:
            with self.subTest(문서=doc_label(path)):
                self.assertEqual(
                    패턴.findall(text), [],
                    "서브에이전트 디스패치가 들어왔습니다 "
                    "— Codex 는 agents 컴포넌트를 배포하지 못합니다",
                )


COMMAND_MAP = PLUGIN_ROOT / "docs" / "codex-harness.md"


class CodexCommandMapTest(unittest.TestCase):
    """대조표가 낡으면 커맨드 추출 견적이 조용히 틀려진다.

    이 표의 쓸모는 하나다 — '커맨드를 스킬로 추출하는 데 얼마나 드는가' 에
    답하는 것. 커맨드가 늘거나 줄거나, 커맨드가 부르는 스킬이 바뀌면 답이
    달라지는데 표는 그대로 남는다. 여기서 걸리게 한다.

    구조는 PrerequisiteRegistryTest 와 같다 — 정본 표에 전수가 실려 있고,
    없는 것도 실려 있지 않아야 한다.
    """

    def setUp(self):
        self.text = COMMAND_MAP.read_text(encoding="utf-8")
        self.표 = re.search(
            r"^## 커맨드 16 ↔ 스킬 26$(.*?)(?=^#{1,3} |\Z)",
            self.text, re.M | re.S,
        )
        self.assertIsNotNone(
            self.표, "'## 커맨드 16 ↔ 스킬 26' 절을 찾지 못했습니다"
        )
        self.행 = re.findall(
            r"^\|\s*`/(gx-[가-힣A-Za-z-]+)`\s*\|([^|]*)\|([^|]*)\|",
            self.표.group(1), re.M,
        )
        self.실린커맨드 = {이름 for 이름, _, _ in self.행}

    def test_대조표가_비어있지_않다(self):
        """표 파싱이 조용히 실패하면 아래 두 검사가 공집합끼리 비교해 통과한다.

        (기존 An05ColumnSsotTest 가 같은 이유로 파싱 가드를 갖고 있다.)
        """
        self.assertGreater(len(self.행), 0, "대조표에서 커맨드 행을 하나도 찾지 못했습니다")

    def test_모든_커맨드가_대조표에_있다(self):
        self.assertEqual(
            command_names() - self.실린커맨드, set(),
            "대조표에 없는 커맨드가 있습니다 — 커맨드를 추가했다면 표에도 넣으세요",
        )

    def test_대조표에_없는_커맨드가_실려있지_않다(self):
        self.assertEqual(
            self.실린커맨드 - command_names(), set(),
            "존재하지 않는 커맨드가 대조표에 있습니다",
        )

    def test_대조표의_조립_스킬이_실제_커맨드에_있다(self):
        """'gx-요구사항정의서가 6개를 조립한다' 는 추출 견적의 근거다.

        커맨드 본문이 바뀌어 스킬이 빠져도 표는 그대로 남아, 견적만 조용히
        틀려진다. 개수 대신 이름을 대조해 그 드리프트를 잡는다.
        """
        실존스킬 = skill_names()
        for 이름, 스킬칸, _ in self.행:
            본문 = (PLUGIN_ROOT / "commands" / f"{이름}.md").read_text(encoding="utf-8")
            for 스킬 in re.findall(r"`([a-z][a-z0-9-]+)`", 스킬칸):
                with self.subTest(커맨드=이름, 스킬=스킬):
                    self.assertIn(스킬, 실존스킬, "존재하지 않는 스킬입니다")
                    self.assertIn(
                        f"**{스킬}**", 본문,
                        f"대조표는 {이름} 이 이 스킬을 조립한다고 하는데 "
                        "커맨드 본문에 없습니다",
                    )

    def test_커맨드가_부르는_스킬이_대조표에_다_있다(self):
        """단방향 검사의 짝. 커맨드가 스킬을 '추가'하는 경우를 잡는다.

        표에 실린 것이 본문에 있는지만 보면, 본문에 새로 생긴 스킬은 아무도
        모른다 — 표의 평균 4.1 과 「부르지 않는 스킬 0」이 함께 낡는다.
        """
        실존스킬 = skill_names()
        for 이름, 스킬칸, _ in self.행:
            본문 = (PLUGIN_ROOT / "commands" / f"{이름}.md").read_text(encoding="utf-8")
            표에실린 = set(re.findall(r"`([a-z][a-z0-9-]+)`", 스킬칸))
            본문이부르는 = {s for s in 실존스킬 if f"**{s}**" in 본문}
            with self.subTest(커맨드=이름):
                self.assertEqual(
                    본문이부르는 - 표에실린, set(),
                    f"{이름} 본문이 조립하는 스킬이 대조표에 없습니다 — 견적이 낡습니다",
                )

    def test_대조표의_Step_게이트_수가_실제와_같다(self):
        """이 숫자가 추출 견적의 단위다. 커맨드가 바뀌면 견적도 바뀌어야 한다.

        셈 규칙은 문서의 「셈 규칙」 인용 블록이 정본이다 — `### Step N` 헤딩의
        고유 번호 수와, 그중 `[필수 중단점]` 이 붙은 것.
        """
        for 이름, _, 로직칸 in self.행:
            본문 = (PLUGIN_ROOT / "commands" / f"{이름}.md").read_text(encoding="utf-8")
            맞춤 = re.search(r"Step (\d+) · 게이트 (\d+)", 로직칸)
            with self.subTest(커맨드=이름):
                self.assertIsNotNone(맞춤, "고유 로직 칸의 형식이 다릅니다")
                steps = len(set(re.findall(r"^### Step (\d+)", 본문, re.M)))
                gates = len(re.findall(r"^### Step \d+.*\[필수 중단점", 본문, re.M))
                self.assertEqual(
                    (steps, gates), (int(맞춤[1]), int(맞춤[2])),
                    "대조표의 Step·게이트 수가 커맨드 본문과 다릅니다 — 견적이 낡았습니다",
                )
