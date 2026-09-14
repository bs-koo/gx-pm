"""Codex 등록과 Claude 커맨드 어댑터의 연결 계약."""

import json
import re
import unittest

from helpers import PLUGIN_ROOT, REPO_ROOT, command_names


class CodexCompatibilityTest(unittest.TestCase):
    def test_release_metadata_matches_both_platforms_and_site(self):
        claude = json.loads((PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        codex = json.loads((PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((REPO_ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (PLUGIN_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        site = (REPO_ROOT / "_config.yml").read_text(encoding="utf-8")
        versions = {
            claude["version"], codex["version"], marketplace["plugins"][0]["version"],
            re.search(r"version-([\d.]+)-blue", readme).group(1),
            re.search(r"## \[([\d.]+)\]", changelog).group(1),
        }
        self.assertEqual(versions, {"4.2.0"})
        self.assertIn("Codex", site)

    def test_매니페스트가_현재_플러그인을_등록한다(self):
        claude = json.loads((PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        codex = json.loads((PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((REPO_ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual((codex["name"], codex["version"]), (claude["name"], claude["version"]))
        self.assertEqual(codex["skills"], "./skills/")
        self.assertNotIn("commands", codex)
        self.assertEqual(marketplace["name"], "gx-pm")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "gx-pm")
        self.assertEqual(entry["source"], {"source": "local", "path": "./plugins/gx-pm"})
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")

    def test_어댑터가_모든_현재_커맨드와_중단점을_연결한다(self):
        adapter = (PLUGIN_ROOT / "skills/gx-pm-workflow/SKILL.md").read_text(encoding="utf-8")
        mapped = set(re.findall(r"commands/(gx-[^`\s|]+)\.md", adapter))
        self.assertEqual(mapped, command_names(), "Codex 진입표와 실제 커맨드가 다릅니다")
        self.assertIn("AskUserQuestion", adapter)
        self.assertIn("request_user_input_async", adapter)
        self.assertIn("실제 응답", adapter)
        self.assertIn("templates/", adapter)
        self.assertIn("sqi-comn-term", adapter)

    def test_두_하네스의_유지보수_지침이_같은_정본을_가리킨다(self):
        guide = "docs/development/dual-harness-maintenance.md"
        for path in (REPO_ROOT / "AGENTS.md", REPO_ROOT / "CLAUDE.md"):
            with self.subTest(path=path):
                self.assertIn(guide, path.read_text(encoding="utf-8"))
        maintenance = (REPO_ROOT / guide).read_text(encoding="utf-8")
        for required in ("gx-pm-workflow", "AskUserQuestion", "request_user_input_async", "sqi-comn-term", "python -m unittest"):
            self.assertIn(required, maintenance)
        self.assertIn(guide, (REPO_ROOT / "README.md").read_text(encoding="utf-8"))

    def test_codex_mcp_recovery_uses_the_documented_server(self):
        guide = (PLUGIN_ROOT / "docs" / "표준용어-mcp-연계.md").read_text(encoding="utf-8")
        claude_url = re.search(r"claude mcp add -s user --transport http sqi-comn-term (https?://\S+)", guide)
        self.assertIsNotNone(claude_url)
        self.assertIn(f"codex.cmd mcp add sqi-comn-term --url {claude_url.group(1)}", guide)
        self.assertIn("codex.cmd mcp list", guide)
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("codex.cmd mcp add sqi-comn-term --url", readme)

    def test_readme가_codex_설치와_제약을_안내한다(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("codex.cmd plugin marketplace add", readme)
        self.assertIn("codex.cmd plugin add gx-pm@gx-pm", readme)
        self.assertIn("$gx-pm-workflow", readme)
        self.assertIn("sqi-comn-term", readme)


if __name__ == "__main__":
    unittest.main()
