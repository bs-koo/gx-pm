"""Codex 하네스 호환 계약 테스트.

근거: oh-my-gx `.claude/rules/harness-codex.md` (Codex CLI 0.130.0 실측)
와 그 저장소의 동작하는 매니페스트 실물.

Codex 는 Claude Code 의 플러그인 규격을 그대로 채택했지만 매니페스트 위치와
지원 컴포넌트가 다르다. 한쪽만 갱신되면 Codex UI 에 옛 버전이 표시되거나
등록 자체가 실패하는데, 사람이 두 파일을 대조하는 방식으로는 반드시 어긋난다.
"""

import json
import unittest

from helpers import PLUGIN_ROOT, REPO_ROOT

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
        entry = self.codex_market["plugins"][0]
        self.assertEqual(entry["name"], self.claude["name"])
        self.assertEqual(
            entry["source"]["url"],
            self.claude_market["plugins"][0]["source"],
            "Codex 마켓플레이스의 url 이 Claude 쪽 source 와 다른 곳을 가리킵니다",
        )

    def test_codex_마켓플레이스의_source_가_객체다(self):
        """Claude 는 문자열('./plugins/gx-pm'), Codex 는 {source, url} 객체다.

        스키마 차이라 문자열을 그대로 두면 파싱에서 걸린다.
        """
        source = self.codex_market["plugins"][0]["source"]
        self.assertIsInstance(source, dict)
        self.assertEqual(source["source"], "url")
