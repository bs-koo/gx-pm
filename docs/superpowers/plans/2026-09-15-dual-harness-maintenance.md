# Claude·Codex Dual-Harness Maintenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 이후 gx-pm 스킬·커맨드 변경이 Claude와 Codex 모두에서 유지되도록 저장소 지침과 계약 검사를 추가한다.

**Architecture:** 공통 유지보수 문서를 정본으로 만들고 두 하네스의 지침 파일이 이를 가리킨다. 새 테스트는 지침 연결과 Codex 진입표의 실재성을 확인한다.

**Tech Stack:** Markdown, Python 3.10 unittest, Codex plugin validator

**Spec:** `docs/superpowers/specs/2026-09-15-dual-harness-maintenance-design.md`

## Global Constraints

- 기존 4.2.0 업무 규칙, 승인 게이트, 외부 MCP 선행조건을 바꾸지 않는다.
- 두 플랫폼에서 같은 규칙을 두 벌로 복제하지 않는다.
- 루트 작업과 플러그인 하위 작업 양쪽에서 루트 지침 문서가 발견되어야 한다.

---

### Task 1: 유지보수 지침과 진입점

**Files:** Create `docs/development/dual-harness-maintenance.md`, `AGENTS.md`, `CLAUDE.md`; modify `README.md`; test `plugins/gx-pm/tests/test_codex_compat.py`.

**Interfaces:** 두 루트 지침은 `docs/development/dual-harness-maintenance.md`를 참조한다.

- [x] **Step 1: 실패 테스트 작성.** 두 지침 파일의 정본 링크와 README 유지보수 링크를 검사한다.

```python
guide = "docs/development/dual-harness-maintenance.md"
for path in (REPO_ROOT / "AGENTS.md", REPO_ROOT / "CLAUDE.md"):
    self.assertIn(guide, path.read_text(encoding="utf-8"))
self.assertIn(guide, (REPO_ROOT / "README.md").read_text(encoding="utf-8"))
```

- [x] **Step 2: 실패 확인.** 지침 파일 부재로 FAIL을 확인했다.

```powershell
python -m unittest discover -s plugins/gx-pm/tests -p test_codex_compat.py -q
```

- [x] **Step 3: 최소 구현.** 정본에 경로·도구·승인·MCP·진입표·검증 절차를 쓰고 두 루트 지침 파일은 정본을 가리키게 한다. 두 지침의 핵심 문장은 같다.

```markdown
이 저장소에서 `plugins/gx-pm`의 커맨드·스킬·템플릿·등록 정보를 수정할 때 먼저
`docs/development/dual-harness-maintenance.md`를 읽고 그 변경 체크리스트를 적용한다.
```

- [x] **Step 4: 통과 확인.** 같은 테스트에서 6건 PASS를 확인했다.

### Task 2: 변경 시 누락 방지

**Files:** Modify `plugins/gx-pm/tests/test_codex_compat.py`. 현재 연결표가 맞으므로 `plugins/gx-pm/skills/gx-pm-workflow/SKILL.md`는 수정하지 않는다.

**Interfaces:** 현재 `commands/*.md` 7개가 모두 Codex 진입 스킬에 정확히 대응하고, 연결표에 없는 커맨드가 추가되면 테스트가 실패한다.

- [x] **Step 1: 연결표 누락 검사를 양방향 계약으로 강화.** 기존 포함 검사 대신 집합 일치를 검사한다.

```python
mapped = set(re.findall(r"commands/(gx-[^`\s|]+)\.md", adapter))
self.assertEqual(mapped, command_names(), "Codex 진입표와 실제 커맨드가 다릅니다")
```

- [x] **Step 2: 현재 연결표 검증.** 테스트가 7개 커맨드의 정확한 일치를 확인했다.
- [x] **Step 3: 최종 검증.** 전체 unittest, 플러그인 검사기, `git diff --check`를 실행했다.

```powershell
python -m unittest discover -s plugins/gx-pm/tests -q
$validator = Join-Path $env:USERPROFILE ".codex/skills/.system/plugin-creator/scripts/validate_plugin.py"
python $validator plugins/gx-pm
git diff --check
```
