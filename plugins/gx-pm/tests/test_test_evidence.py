"""utils/test-evidence.py — 개발 레포 테스트 색인·DE-13 읽기·기입.

이 스크립트는 판단하지 않는다. 테스트와 계획서 행을 짝짓는 것은 apply-test-results
스킬(모델)의 몫이고, 스크립트는 그 판단에 쓸 사실을 정확히 모으고(index·plan)
승인된 결과를 표 모양을 깨지 않고 쓰는(apply) 일만 한다.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from helpers import load_util

ev = load_util("test-evidence.py")

CORE_AC = """# 메모 관리

## 배경
건물별 메모를 등록한다.

## 요구사항 (AC)
- AC-1: 빈 메모 거부
  Given: 건물 1건
  When: 내용이 공백인 메모 저장
  Then: "메모를 입력하세요" 안내, 저장 없음
- AC-2: 2,000자 초과 거부 (제외 — 위험 수용)
  Given: 건물 1건
  When: 2,001자 메모 저장
  Then: 거부
- AC-3: 정상 저장
  Given: 건물 1건
  When: 10자 메모 저장
  Then: 메모 1건 저장
"""

CORE_STATE = """phase: complete
status: in_progress
pipeline: gx-tdd
verify-status: passed
verify-fingerprint: "abc1234:0123456789ab"
mode: core
branch: feat/memo
steps:
  implement:
    - "RGR T1 (AC-1)": { red: completed, test-file: src/test/java/MemoTest.java, test-file-hash: 3ca9, test-count: 3, report: reports/t1-impl.md, impl: completed }
    - "RGR T2 (AC-3)":
        red: completed
        test-file: src/test/java/MemoSaveTest.java
        impl: completed
"""

FULL_PRD = """## PRD: 원천 데이터 등록
### 배경
원천파일을 회차로 등록한다.
### 요구사항
#### 기능 요구사항
- [Must] FR-1: 4종 파일 등록
### 수용 기준
AC-1: 정상 등록
  Given: 회차 없음
  When: 4종 파일(각 500MB) 등록
  Then: 회차 생성, 상태 '등록완료'
AC-2: 용량 초과 차단 → [FR-1]
  Given: 회차 없음
  When: 1,001MB 파일 등록
  Then: "파일 용량 초과" 안내, 저장 없음
### 제외 범위
- 없음
"""

PLAN_MD = """# DE-13 단위테스트계획서 — 테스트

> 생성: /gx-명세일괄 · 2026-09-09 16:22

## 개정이력

| 버전 | 개정일 | 개정 사유 | 개정 내용 | 작성자 | 승인자 |
|------|--------|----------|----------|--------|--------|
| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |

## 단위테스트계획 — 테스트

| 테스트ID | 연계기능ID | 연계요구사항ID | 사전조건 | 입력 | 기대결과 | 사후조건 | 의존성 | 테스트담당자 | 수행일 | 결과 |
|---|---|---|---|---|---|---|---|---|---|---|
| REB-UT-001 | REB-FN-001 | REB-RE-001 | 회차 없음 | 4종 파일 등록 | 회차 생성 | TB_CYCL 1건 | 없음 | | | |
| REB-UT-002 | REB-FN-001 | REB-RE-001 | 〃 | 1,001MB 파일 | "파일 용량 초과" 안내 | 저장 없음 | 없음 | | | |
| REB-UT-003 | REB-FN-001 | REB-RE-001 | 〃 | 1,000MB 파일 | 정상 등록 | 1건 저장 | 없음 | | | |
| REB-UT-004 | REB-FN-002 | REB-RE-002 | 회차 5건 | 목록 조회 | 5건 표시 | 변화 없음 | 없음 | | | |
| REB-UT-005 | | REB-RE-050 | 900만 건 | 조회 | 3초 이내 | 변화 없음 | 없음 | | | |
"""


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))  # OS 줄바꿈 변환 없이 — 줄바꿈 보존 검사가 의미를 갖게
    return path


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="evidence 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def by_slug(self, result):
        return {r["slug"]: r for r in result["records"]}

    def test_core_mode_acs_tests_and_exclusion(self):
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        write(self.root, "src/test/java/MemoTest.java", "class MemoTest {}")
        rec = self.by_slug(ev.collect(self.root))["feat-memo"]
        self.assertEqual((rec["pipeline"], rec["status"], rec["mode"]), ("gx-tdd", "evidence", "core"))
        acs = {a["id"]: a for a in rec["acs"]}
        self.assertEqual(sorted(acs), ["AC-1", "AC-2", "AC-3"])
        self.assertEqual(acs["AC-1"]["then"], '"메모를 입력하세요" 안내, 저장 없음')
        self.assertTrue(acs["AC-2"]["excluded"])
        self.assertFalse(acs["AC-1"]["excluded"])
        self.assertEqual(acs["AC-1"]["tests"], [{"file": "src/test/java/MemoTest.java", "exists": True,
                                                  "red_report": "reports/t1-red.md"}])
        self.assertEqual(acs["AC-3"]["tests"][0]["file"], "src/test/java/MemoSaveTest.java")
        self.assertFalse(acs["AC-3"]["tests"][0]["exists"])
        self.assertIn("건물별 메모", rec["context"])

    def test_full_mode_reads_acceptance_criteria_section(self):
        write(self.root, ".dev/feat-source/prd.md", FULL_PRD)
        write(self.root, ".dev/feat-source/state.md", CORE_STATE.replace("mode: core", "mode: all"))
        rec = self.by_slug(ev.collect(self.root))["feat-source"]
        acs = {a["id"]: a for a in rec["acs"]}
        self.assertEqual(sorted(acs), ["AC-1", "AC-2"])
        self.assertEqual(acs["AC-2"]["title"], "용량 초과 차단 → [FR-1]")
        self.assertEqual(acs["AC-2"]["when"], "1,001MB 파일 등록")
        self.assertIn("원천파일을 회차로", rec["context"])

    def test_unverified_gx_dev_and_ralph_records_are_classified(self):
        write(self.root, ".dev/feat-wip/ac.md", CORE_AC)
        write(self.root, ".dev/feat-wip/state.md", CORE_STATE.replace("verify-status: passed", "verify-status: pending"))
        write(self.root, ".dev/feat-dev/ac.md", CORE_AC)
        write(self.root, ".dev/feat-dev/state.md", "phase: complete\nstatus: completed\nmode: core\n")
        write(self.root, ".dev/feat-loop/prd.md", FULL_PRD)
        write(self.root, ".dev/feat-loop/state.md", "pipeline: gx-ralph\norigin: gx-tdd\nverify-status: pending\n")
        write(self.root, ".dev/feat-loop/ac-status.json", json.dumps({"version": 1, "acs": [
            {"id": "AC-1", "title": "정상 등록", "passes": True}, {"id": "AC-2", "title": "용량", "passes": False}]}))
        records = self.by_slug(ev.collect(self.root))
        self.assertEqual(records["feat-wip"]["status"], "incomplete")
        self.assertEqual(records["feat-dev"]["status"], "insufficient")
        loop = records["feat-loop"]
        self.assertEqual(loop["status"], "evidence")
        self.assertEqual({a["id"]: a["passes"] for a in loop["acs"]}, {"AC-1": True, "AC-2": False})

    def test_skips_non_record_directories(self):
        write(self.root, ".dev/plan.md", "# plan")
        write(self.root, ".dev/.active", "feat-memo")
        write(self.root, ".dev/architecture/map.md", "x")
        write(self.root, ".dev/feat-memo.backup-1700000000/state.md", CORE_STATE)
        write(self.root, ".dev/feat-memo/logs-20261001-101010/state.md", CORE_STATE)
        self.assertEqual(ev.collect(self.root)["records"], [])

    def test_git_commit_date_and_author_of_state(self):
        if shutil.which("git") is None:
            self.skipTest("git 없음")
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        run = lambda *a: subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True)
        run("init", "-q")
        run("-c", "user.name=kim.dev", "-c", "user.email=k@example.com", "add", "-A")
        run("-c", "user.name=kim.dev", "-c", "user.email=k@example.com",
            "commit", "-q", "-m", "feat", "--date", "2026-10-12T10:00:00")
        result = ev.collect(self.root)
        rec = self.by_slug(result)["feat-memo"]
        self.assertEqual((rec["author"], rec["date"]), ("kim.dev", "2026.10.12"))
        self.assertEqual(result["vcs"], "git")

    def test_acs_changed_after_verify_commit_are_flagged(self):
        """2차 평가에서 발견: verify 뒤 ac.md 만 고친 커밋이 들어오면 옛 AC 의 verify 가 새 AC 의 증적처럼 보였다."""
        if shutil.which("git") is None:
            self.skipTest("git 없음")
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        run = lambda *a: subprocess.run(["git", "-C", str(self.root), "-c", "user.name=kim.dev",
                                         "-c", "user.email=k@example.com", *a], check=True, capture_output=True)
        run("init", "-q")
        run("add", "-A")
        run("commit", "-q", "-m", "verify")
        self.assertFalse(self.by_slug(ev.collect(self.root))["feat-memo"]["ac_changed_after_verify"])
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC.replace("Then: 메모 1건 저장", "Then: 메모 2건 저장"))
        run("commit", "-q", "-am", "AC-3 변경")
        rec = self.by_slug(ev.collect(self.root))["feat-memo"]
        self.assertTrue(rec["ac_changed_after_verify"])
        self.assertEqual({a["id"]: a["changed_after_verify"] for a in rec["acs"]},
                         {"AC-1": False, "AC-2": False, "AC-3": True})
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC.replace("Then: 메모 1건 저장", "Then: 메모 2건 저장")
              .replace("공백인 메모", "빈 메모"))  # 커밋하지 않은 변경도 verify 뒤의 변경이다
        rec = self.by_slug(ev.collect(self.root))["feat-memo"]
        self.assertTrue({a["id"]: a["changed_after_verify"] for a in rec["acs"]}["AC-1"])

    def test_git_is_read_when_repository_owner_differs(self):
        """Codex 실측: 샌드박스가 다른 계정으로 돌아 git 이 소유권 검사로 거부했고, 도구는 조용히 vcs none 이 됐다."""
        if shutil.which("git") is None:
            self.skipTest("git 없음")
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        run = lambda *a: subprocess.run(["git", "-C", str(self.root), "-c", "user.name=kim.dev",
                                         "-c", "user.email=k@example.com", *a], check=True, capture_output=True)
        run("init", "-q")
        run("add", "-A")
        run("commit", "-q", "-m", "verify", "--date", "2026-10-12T10:00:00")
        with mock.patch.dict(os.environ, {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}):
            result = ev.collect(self.root)
        self.assertEqual((result["vcs"], result["warnings"]), ("git", []))
        rec = self.by_slug(result)["feat-memo"]
        self.assertEqual((rec["author"], rec["date"]), ("kim.dev", "2026.10.12"))
        self.assertFalse(rec["ac_changed_after_verify"])

    def test_unreadable_git_is_reported_not_silent(self):
        if shutil.which("git") is None:
            self.skipTest("git 없음")
        write(self.root, ".git", "깨진 gitfile")
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        result = ev.collect(self.root)
        self.assertEqual(result["vcs"], "none")
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("git", result["warnings"][0])

    def test_ac_doc_missing_at_verify_commit_counts_as_changed(self):
        """최종 리뷰: verify 커밋에 AC 문서가 없으면 알 수 없음(null)이 되어 증적으로 쓰였다 — 나중에 생긴 AC 다."""
        if shutil.which("git") is None:
            self.skipTest("git 없음")
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        run = lambda *a: subprocess.run(["git", "-C", str(self.root), "-c", "user.name=kim.dev",
                                         "-c", "user.email=k@example.com", *a], check=True, capture_output=True)
        run("init", "-q")
        run("add", "-A")
        run("commit", "-q", "-m", "verify")
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        run("add", "-A")
        run("commit", "-q", "-m", "AC 나중에 추가")
        rec = self.by_slug(ev.collect(self.root))["feat-memo"]
        self.assertTrue(rec["ac_changed_after_verify"])
        self.assertTrue(all(a["changed_after_verify"] for a in rec["acs"]))

    def test_task_block_ends_at_sibling_key(self):
        """최종 리뷰: 태스크 끝을 들여쓰기 없는 줄로만 봐서 다음 블록의 test-file 이 앞 태스크에 붙을 수 있었다."""
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", "pipeline: gx-tdd\nverify-status: passed\nsteps:\n  implement:\n"
              "    - \"RGR T1 (AC-1)\":\n        red: completed\n        impl: in_progress\n"
              "  review:\n    test-file: src/test/java/Other.java\n")
        acs = {a["id"]: a for a in self.by_slug(ev.collect(self.root))["feat-memo"]["acs"]}
        self.assertEqual(acs["AC-1"]["tests"], [])

    def test_risk_accepted_acs_and_untested_verify_are_flagged(self):
        """최종 리뷰: gx-tdd 가 trust-ledger 에 위험 수용으로 적은 AC(하네스 부재 제외 등)가 증적으로 나갔다."""
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        ledger = write(self.root, ".dev/feat-memo/trust-ledger.md",
                       "## Trust Ledger\n\n### 통합 감사 (review)\n- [품질/Minor] AC-1 이름 정리\n\n### 위험 수용\n"
                       "- [하네스 부재 AC 제외] AC-1: 프론트 러너 없음 (implement/Step 0.5)\n"
                       "- [태스크 리뷰 미해결] T2: 경계값 누락 (implement/Step 2-V)\n"
                       "- [신규 경고 수용] 경고 2건 (complete/Step -1)\n")
        rec = self.by_slug(ev.collect(self.root))["feat-memo"]
        self.assertEqual(rec["status"], "evidence")
        self.assertEqual(len(rec["risk_acceptances"]), 3)
        acs = {a["id"]: a for a in rec["acs"]}
        self.assertEqual([("AC-1" in r) for r in acs["AC-1"]["risks"]], [True])  # 통합 감사 줄은 세지 않는다
        self.assertEqual(acs["AC-2"]["risks"], [])
        self.assertEqual(len(acs["AC-3"]["risks"]), 1)  # T2 는 AC-3 의 태스크
        ledger.write_bytes((ledger.read_text(encoding="utf-8")
                            + "- [검증 명령 미감지] 테스트 명령 없음 (complete/Step -1)\n").encode("utf-8"))
        rec = self.by_slug(ev.collect(self.root))["feat-memo"]
        self.assertEqual(rec["status"], "insufficient")
        self.assertIn("검증 명령 미감지", rec["reason"])

    def test_acs_without_rgr_task_are_marked(self):
        """최종 리뷰: RGR 태스크가 없는(구현에서 빠진) AC 도 경고 없이 증적이 됐다."""
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        write(self.root, ".dev/feat-loop/prd.md", FULL_PRD)
        write(self.root, ".dev/feat-loop/state.md", "pipeline: gx-ralph\norigin: gx-tdd\nverify-status: pending\n")
        records = self.by_slug(ev.collect(self.root))
        self.assertEqual({a["id"]: a["has_task"] for a in records["feat-memo"]["acs"]},
                         {"AC-1": True, "AC-2": False, "AC-3": True})
        self.assertEqual({a["has_task"] for a in records["feat-loop"]["acs"]}, {None})

    def test_struck_and_en_dash_exclusions(self):
        text = (CORE_AC.replace("- AC-2: 2,000자 초과 거부 (제외 — 위험 수용)", "- ~~AC-2: 2,000자 초과 거부~~")
                .replace("- AC-3: 정상 저장", "- AC-3: 정상 저장 (제외 – 위험 수용)"))
        write(self.root, ".dev/feat-memo/ac.md", text)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        acs = {a["id"]: a for a in self.by_slug(ev.collect(self.root))["feat-memo"]["acs"]}
        self.assertEqual(acs["AC-1"]["when"], "내용이 공백인 메모 저장")  # 지운 AC-2 의 G-W-T 가 덮지 않는다
        self.assertEqual(acs["AC-2"]["title"], "2,000자 초과 거부")
        self.assertTrue(acs["AC-2"]["excluded"])
        self.assertTrue(acs["AC-3"]["excluded"])

    def test_multiline_then_is_kept(self):
        """최종 리뷰: gx-tdd 정본 예시처럼 Then 을 두 줄로 쓰면 둘째 줄(변화 없음 사후조건)이 버려졌다."""
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC.replace(
            'Then: "메모를 입력하세요" 안내, 저장 없음', 'Then:  "메모를 입력하세요" 안내되고\n         저장 요청이 발생하지 않는다'))
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        acs = {a["id"]: a for a in self.by_slug(ev.collect(self.root))["feat-memo"]["acs"]}
        self.assertEqual(acs["AC-1"]["then"], '"메모를 입력하세요" 안내되고 저장 요청이 발생하지 않는다')
        self.assertEqual(acs["AC-2"]["given"], "건물 1건")

    def test_ac_document_follows_mode(self):
        """최종 리뷰: core 로 먼저 돌린 낡은 ac.md 가 남아 있으면 full(mode: all) 기록도 ac.md 를 읽었다."""
        write(self.root, ".dev/feat-source/ac.md", CORE_AC)
        write(self.root, ".dev/feat-source/prd.md", FULL_PRD)
        state = write(self.root, ".dev/feat-source/state.md", CORE_STATE.replace("mode: core", "mode: all"))
        rec = self.by_slug(ev.collect(self.root))["feat-source"]
        self.assertEqual((rec["ac_source"], rec["acs"][0]["title"]), ("prd.md", "정상 등록"))
        state.write_bytes(CORE_STATE.encode("utf-8"))
        self.assertEqual(self.by_slug(ev.collect(self.root))["feat-source"]["ac_source"], "ac.md")

    def test_source_can_be_a_subdirectory_of_the_repository(self):
        """최종 리뷰: 하위 폴더를 소스로 주면 git show 경로가 어긋나 바뀌지 않은 AC 까지 변경으로 빠졌다."""
        if shutil.which("git") is None:
            self.skipTest("git 없음")
        write(self.root, "app/.dev/feat-memo/ac.md", CORE_AC)
        write(self.root, "app/.dev/feat-memo/state.md", CORE_STATE)
        run = lambda *a: subprocess.run(["git", "-C", str(self.root), "-c", "user.name=kim.dev",
                                         "-c", "user.email=k@example.com", *a], check=True, capture_output=True)
        run("init", "-q")
        run("add", "-A")
        run("commit", "-q", "-m", "verify")
        rec = self.by_slug(ev.collect(self.root / "app"))["feat-memo"]
        self.assertEqual((rec["author"], rec["ac_changed_after_verify"]), ("kim.dev", False))

    def test_change_after_verify_is_unknown_without_vcs(self):
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        rec = self.by_slug(ev.collect(self.root))["feat-memo"]
        self.assertIsNone(rec["ac_changed_after_verify"])
        self.assertIsNone(rec["acs"][0]["changed_after_verify"])

    def test_missing_source_is_error(self):
        with self.assertRaises(ev.InputError):
            ev.collect(self.root / "없음")


JAVA_TEST = r'''package kr.reb.source;

import org.junit.jupiter.api.*;

class FileSizeLimitTest {
    private static final long MB = 1024L * 1024;

    @Test
    @DisplayName("1,001MB 파일은 \"파일 용량 초과\"로 차단되고 저장되지 않는다")
    void rejectsOverLimit() {
        var ex = assertThrows(FileTooLargeException.class, () -> service.upload(file(1001L * MB)));
        assertEquals("파일 용량 초과", ex.getMessage());
        verify(repository, never()).save(any());
    }

    @Test void acceptsExactlyLimit() {
        service.upload(file(1000L * MB));
        verify(repository).save(any());
    }

    @Disabled("러너 없음")
    @Test
    void slowCase() { }

    @Nested
    class WhenEmpty {
        @ParameterizedTest
        @ValueSource(strings = {"a.csv"})
        void rejectsZeroByte(String name) {
            assertThatThrownBy(() -> service.upload(empty(name))).hasMessage("빈 파일은 등록할 수 없습니다");
        }
    }

    private Object file(long size) { return null; }
}
'''

KOTLIN_TEST = '''class CycleDeleteServiceTest {
    @Test
    fun `처리중 회차는 삭제할 수 없다`() {
        assertThrows<IllegalStateException> { service.delete(processing) }
    }
}
'''

TS_TEST = """describe('원천 데이터 등록', () => {
  it('0바이트 파일을 거부한다', () => {
    expect(() => upload(emptyFile)).toThrow('빈 파일은 등록할 수 없습니다');
  });
  it.skip('나중에', () => {});
  describe('용량', () => {
    test("1,001MB 차단", () => { expect(upload(big)).rejects.toThrow("파일 용량 초과"); });
  });
});
xit('전역 스킵', () => {});
"""


def junit_xml(classname, cases, timestamp="2026-10-20T10:00:00"):
    body = "".join(f'<testcase classname="{classname}" name="{n}" time="0.1">{extra}</testcase>' for n, extra in cases)
    return f'<?xml version="1.0" encoding="UTF-8"?><testsuite name="{classname}" tests="{len(cases)}" timestamp="{timestamp}">{body}</testsuite>'


class IndexTests(unittest.TestCase):
    """테스트 코드 색인 — 근거는 레포에 실제로 있는 테스트 메서드다 (개발 도구와 무관)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="index 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "reb-api"
        self.root.mkdir()

    def by_name(self, result):
        return {t["name"]: t for t in result["tests"]}

    def git(self, *args, user="kim.dev", date=None):
        env = {**os.environ}
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(["git", "-C", str(self.root), "-c", f"user.name={user}", "-c", "user.email=u@example.com", *args],
                       check=True, capture_output=True, env=env)

    def test_java_methods_with_display_names_literals_and_disabled(self):
        write(self.root, "src/test/java/kr/reb/source/FileSizeLimitTest.java", JAVA_TEST)
        tests = self.by_name(ev.index([self.root]))
        self.assertEqual(sorted(tests), ["acceptsExactlyLimit", "rejectsOverLimit", "rejectsZeroByte", "slowCase"])
        over = tests["rejectsOverLimit"]
        self.assertEqual((over["repo"], over["lang"], over["class"]), ("reb-api", "java", "FileSizeLimitTest"))
        self.assertEqual(over["file"], "src/test/java/kr/reb/source/FileSizeLimitTest.java")
        self.assertEqual(over["display"], '1,001MB 파일은 "파일 용량 초과"로 차단되고 저장되지 않는다')
        self.assertIn("파일 용량 초과", over["literals"])
        self.assertIn("1001", over["literals"])
        self.assertEqual(over["asserts"], 3)
        self.assertEqual(over["line"], 10)
        self.assertFalse(over["disabled"])
        self.assertTrue(tests["slowCase"]["disabled"])
        self.assertEqual(tests["rejectsZeroByte"]["class"], "WhenEmpty")
        self.assertIn("빈 파일은 등록할 수 없습니다", tests["rejectsZeroByte"]["literals"])
        self.assertEqual(tests["acceptsExactlyLimit"]["run"]["status"], "none")

    def test_class_scope_survives_nested_classes_and_next_line_braces(self):
        write(self.root, "src/test/java/OrderTest.java", "class OrderTest\n{\n    @Nested\n    class Inner\n    {\n"
              "        @Test void a() { assertTrue(x); }\n    }\n\n    @Test\n    void b()\n    {\n        assertTrue(y);\n    }\n}\n")
        tests = self.by_name(ev.index([self.root]))
        self.assertEqual((tests["a"]["class"], tests["b"]["class"]), ("Inner", "OrderTest"))

    def test_kotlin_backtick_names(self):
        write(self.root, "src/test/kotlin/CycleDeleteServiceTest.kt", KOTLIN_TEST)
        test = ev.index([self.root])["tests"][0]
        self.assertEqual((test["name"], test["lang"], test["asserts"]), ("처리중 회차는 삭제할 수 없다", "kotlin", 1))

    def test_js_describe_it_and_skips(self):
        write(self.root, "web/src/upload.test.ts", TS_TEST)
        tests = self.by_name(ev.index([self.root]))
        self.assertEqual(sorted(tests), ["0바이트 파일을 거부한다", "1,001MB 차단", "나중에", "전역 스킵"])
        self.assertEqual(tests["1,001MB 차단"]["class"], "원천 데이터 등록 > 용량")
        self.assertIn("파일 용량 초과", tests["1,001MB 차단"]["literals"])
        self.assertEqual([tests[n]["disabled"] for n in ("0바이트 파일을 거부한다", "나중에", "전역 스킵")],
                         [False, True, True])

    def test_build_output_and_dependencies_are_not_scanned_for_tests(self):
        write(self.root, "node_modules/lib/x.test.js", "it('lib', () => { expect(1).toBe(1); });")
        write(self.root, "build/generated/GenTest.java", JAVA_TEST)
        write(self.root, ".dev/feat/reports/FooTest.java", JAVA_TEST)
        self.assertEqual(ev.index([self.root])["tests"], [])

    def test_junit_reports_give_latest_run_and_staleness(self):
        """빌드 도구가 남긴 결과 파일을 있는 그대로 읽는다 — 따로 관리하지 않는다."""
        test_file = write(self.root, "src/test/java/kr/reb/source/FileSizeLimitTest.java", JAVA_TEST)
        write(self.root, "build/test-results/test/TEST-kr.reb.source.FileSizeLimitTest.xml", junit_xml(
            "kr.reb.source.FileSizeLimitTest",
            [("rejectsOverLimit()", ""), ("acceptsExactlyLimit()", '<failure message="x">boom</failure>'),
             ("slowCase()", "<skipped/>")]))
        write(self.root, "build/test-results/test/TEST-kr.reb.source.FileSizeLimitTest$WhenEmpty.xml", junit_xml(
            "kr.reb.source.FileSizeLimitTest$WhenEmpty", [("[1] a.csv", "")]))
        old = datetime(2026, 10, 19, 9, 0).timestamp()
        os.utime(test_file, (old, old))
        tests = self.by_name(ev.index([self.root]))
        over = tests["rejectsOverLimit"]["run"]
        self.assertEqual((over["status"], over["date"], over["by"], over["stale"]), ("passed", "2026.10.20", "report", False))
        self.assertTrue(over["source"].endswith("TEST-kr.reb.source.FileSizeLimitTest.xml"))
        self.assertEqual(tests["acceptsExactlyLimit"]["run"]["status"], "failed")
        self.assertEqual(tests["slowCase"]["run"]["status"], "skipped")
        self.assertEqual(tests["rejectsZeroByte"]["run"]["status"], "none")  # 매개변수 테스트 이름만으로는 짝을 확정하지 않는다
        new = datetime(2026, 10, 21, 9, 0).timestamp()
        os.utime(test_file, (new, new))  # 결과 뒤에 테스트 파일이 바뀌었다
        self.assertTrue(self.by_name(ev.index([self.root]))["rejectsOverLimit"]["run"]["stale"])

    def test_failed_run_keeps_the_failure_message(self):
        """평가 7회차: Fail 사유에 적을 실패 메시지를 결과 파일을 직접 열어 옮겼다."""
        write(self.root, "src/test/java/kr/reb/source/FileSizeLimitTest.java", JAVA_TEST)
        write(self.root, "build/test-results/test/TEST-kr.reb.source.FileSizeLimitTest.xml", junit_xml(
            "kr.reb.source.FileSizeLimitTest",
            [("rejectsOverLimit()", '<failure message="expected 3 saved but was 0">AssertionFailedError</failure>'),
             ("acceptsExactlyLimit()", "<error>java.lang.NullPointerException\n\tat kr.reb.X</error>"),
             ("slowCase()", "")]))
        tests = self.by_name(ev.index([self.root]))
        self.assertEqual(tests["rejectsOverLimit"]["run"]["message"], "expected 3 saved but was 0")
        self.assertEqual(tests["acceptsExactlyLimit"]["run"]["message"], "java.lang.NullPointerException")
        self.assertNotIn("message", tests["slowCase"]["run"])

    def test_summary_counts_stale_passes_apart(self):
        """평가 7회차: 색인 요약의 '통과' 에 실행 뒤 바뀐 테스트의 결과가 섞여 보였다."""
        test_file = write(self.root, "src/test/java/kr/reb/source/FileSizeLimitTest.java", JAVA_TEST)
        write(self.root, "build/test-results/test/TEST-kr.reb.source.FileSizeLimitTest.xml", junit_xml(
            "kr.reb.source.FileSizeLimitTest", [("rejectsOverLimit()", ""), ("acceptsExactlyLimit()", "")]))
        new = datetime(2026, 10, 21, 9, 0).timestamp()
        os.utime(test_file, (new, new))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ev.main(["index", "--source", str(self.root), "--out", str(Path(self.tmp.name) / "t.json")]), 0)
        self.assertIn("통과 2 (그중 실행 뒤 테스트가 바뀐 결과 2)", err.getvalue())

    def test_warns_when_every_reported_test_file_looks_newer_than_its_results(self):
        """평가 v4 보고: 폴더를 수정 시각 보존 없이 복사하면 모든 결과가 낡음으로 보여 Pass 가 0 이 된다 — 알린다."""
        a = write(self.root, "src/test/java/kr/reb/source/FileSizeLimitTest.java", JAVA_TEST)
        b = write(self.root, "src/test/java/kr/reb/OrderTest.java", "class OrderTest {\n    @Test void a() { assertTrue(x); }\n}\n")
        write(self.root, "build/test-results/test/TEST-kr.reb.source.FileSizeLimitTest.xml",
              junit_xml("kr.reb.source.FileSizeLimitTest", [("rejectsOverLimit()", "")]))
        write(self.root, "build/test-results/test/TEST-kr.reb.OrderTest.xml", junit_xml("kr.reb.OrderTest", [("a()", "")]))
        copied = datetime(2026, 10, 21, 9, 0).timestamp()
        for p in (a, b):
            os.utime(p, (copied, copied))
        warnings = ev.index([self.root])["sources"][0]["warnings"]
        self.assertTrue(any("원래 폴더" in w for w in warnings), warnings)
        old = datetime(2026, 10, 19, 9, 0).timestamp()
        os.utime(b, (old, old))  # 한 파일만 나중에 바뀐 것은 정상적인 수정이다
        self.assertEqual(ev.index([self.root])["sources"][0]["warnings"], [])

    def test_report_matches_display_names(self):
        test_file = write(self.root, "src/test/java/kr/reb/source/FileSizeLimitTest.java", JAVA_TEST)
        write(self.root, "target/surefire-reports/TEST-kr.reb.source.FileSizeLimitTest.xml", junit_xml(
            "kr.reb.source.FileSizeLimitTest", [('1,001MB 파일은 &quot;파일 용량 초과&quot;로 차단되고 저장되지 않는다', "")]))
        old = datetime(2026, 10, 19, 9, 0).timestamp()
        os.utime(test_file, (old, old))
        self.assertEqual(self.by_name(ev.index([self.root]))["rejectsOverLimit"]["run"]["status"], "passed")

    def test_jest_junit_report_matches_titles(self):
        test_file = write(self.root, "web/src/upload.test.ts", TS_TEST)
        write(self.root, "web/junit.xml", '<testsuites><testsuite name="upload" timestamp="2026-10-20T10:00:00">'
              '<testcase classname="원천 데이터 등록 0바이트 파일을 거부한다" name="원천 데이터 등록 0바이트 파일을 거부한다"/>'
              '</testsuite></testsuites>')
        old = datetime(2026, 10, 19, 9, 0).timestamp()
        os.utime(test_file, (old, old))
        tests = self.by_name(ev.index([self.root]))
        self.assertEqual(tests["0바이트 파일을 거부한다"]["run"]["status"], "passed")
        self.assertEqual(tests["1,001MB 차단"]["run"]["status"], "none")

    def test_last_change_per_test_file_from_git(self):
        if shutil.which("git") is None:
            self.skipTest("git 없음")
        write(self.root, "src/test/java/kr/reb/source/FileSizeLimitTest.java", JAVA_TEST)
        write(self.root, "src/test/kotlin/CycleDeleteServiceTest.kt", KOTLIN_TEST)
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "tests", date="2026-10-12T10:00:00")
        write(self.root, "src/test/kotlin/CycleDeleteServiceTest.kt", KOTLIN_TEST.replace("processing", "running"))
        self.git("commit", "-q", "-am", "fix", user="park.dev", date="2026-10-15T10:00:00")
        result = ev.index([self.root])
        tests = self.by_name(result)
        self.assertEqual(tests["rejectsOverLimit"]["last_change"], {"date": "2026.10.12", "author": "kim.dev"})
        self.assertEqual(tests["처리중 회차는 삭제할 수 없다"]["last_change"], {"date": "2026.10.15", "author": "park.dev"})
        self.assertEqual(result["sources"][0]["vcs"], "git")

    def test_last_change_from_svn(self):
        if shutil.which("svn") is None or shutil.which("svnadmin") is None:
            self.skipTest("svn 없음")
        repo = Path(self.tmp.name) / "svnrepo"
        subprocess.run(["svnadmin", "create", str(repo)], check=True, capture_output=True)
        wc = Path(self.tmp.name) / "wc"
        subprocess.run(["svn", "checkout", "-q", repo.as_uri(), str(wc)], check=True, capture_output=True)
        write(wc, "src/test/kotlin/CycleDeleteServiceTest.kt", KOTLIN_TEST)
        subprocess.run(["svn", "add", "-q", "--parents", str(wc / "src")], check=True, capture_output=True)
        subprocess.run(["svn", "commit", "-q", "-m", "t", "--username", "lee.dev", str(wc)], check=True, capture_output=True)
        subprocess.run(["svn", "update", "-q", str(wc)], check=True, capture_output=True)
        result = ev.index([wc])
        self.assertEqual(result["sources"][0]["vcs"], "svn")
        self.assertEqual(result["tests"][0]["last_change"]["author"], "lee.dev")
        self.assertRegex(result["tests"][0]["last_change"]["date"], r"^\d{4}\.\d{2}\.\d{2}$")

    def test_gx_tdd_verify_counts_as_run_for_its_test_files(self):
        """gx-tdd 를 쓴 팀이면 verify 통과가 그 태스크 테스트 파일의 실행 근거가 된다 — 없어도 색인은 돈다."""
        if shutil.which("git") is None:
            self.skipTest("git 없음")
        write(self.root, ".dev/feat-memo/ac.md", CORE_AC)
        write(self.root, ".dev/feat-memo/state.md", CORE_STATE)
        write(self.root, "src/test/java/MemoTest.java", "class MemoTest {\n    @Test void blank() { assertTrue(x); }\n}\n")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "verify", date="2026-10-12T10:00:00")
        result = ev.index([self.root])
        run = self.by_name(result)["blank"]["run"]
        self.assertEqual((run["status"], run["by"], run["date"], run["stale"]), ("passed", "gx-tdd verify", "2026.10.12", False))
        self.assertEqual(result["gx_tdd"][0]["slug"], "feat-memo")
        write(self.root, "src/test/java/MemoTest.java", "class MemoTest {\n    @Test void blank() { assertFalse(x); }\n}\n")
        self.git("commit", "-q", "-am", "세션에서 수정", user="park.dev", date="2026-10-14T10:00:00")
        self.assertTrue(self.by_name(ev.index([self.root]))["blank"]["run"]["stale"])

    def test_multiple_sources_keep_repo_names(self):
        web = Path(self.tmp.name) / "reb-web"
        write(self.root, "src/test/kotlin/CycleDeleteServiceTest.kt", KOTLIN_TEST)
        write(web, "src/upload.test.ts", TS_TEST)
        result = ev.index([self.root, web])
        self.assertEqual([s["repo"] for s in result["sources"]], ["reb-api", "reb-web"])
        self.assertEqual({t["repo"] for t in result["tests"]}, {"reb-api", "reb-web"})

    def test_cli_index(self):
        write(self.root, "src/test/kotlin/CycleDeleteServiceTest.kt", KOTLIN_TEST)
        write(self.root, "src/test/java/kr/reb/source/FileSizeLimitTest.java", JAVA_TEST)
        out = Path(self.tmp.name) / "tests.json"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ev.main(["index", "--source", str(self.root), "--out", str(out)]), 0)
        self.assertIn("테스트 5건", err.getvalue())
        self.assertIn("사용 안 함 1", err.getvalue())  # 요약의 건수가 합계와 맞아야 한다 (평가 v3 보고)
        self.assertEqual(len(json.loads(out.read_text(encoding="utf-8"))["tests"]), 5)
        self.assertEqual(ev.main(["index", "--source", str(self.root / "없음"), "--out", str(out)]), 2)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="plan 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.md = write(Path(self.tmp.name), "REB-단위테스트계획서.md", PLAN_MD)

    def test_reads_rows_resolves_ditto_and_fingerprints(self):
        plan = ev.read_plan(self.md)
        rows = {r["테스트ID"]: r for r in plan["rows"]}
        self.assertEqual(rows["REB-UT-002"]["사전조건"], "회차 없음")
        self.assertEqual(rows["REB-UT-005"]["연계기능ID"], "")
        self.assertRegex(rows["REB-UT-001"]["fingerprint"], r"^[0-9a-f]{8}$")
        self.assertEqual(plan["last_version"], "1.0")
        self.assertEqual(plan["next_id"], "REB-UT-006")

    def test_fingerprint_changes_only_with_case_content(self):
        before = {r["테스트ID"]: r["fingerprint"] for r in ev.read_plan(self.md)["rows"]}
        self.md.write_text(PLAN_MD.replace("| 회차 생성 |", "| 회차 신규 생성 |"), encoding="utf-8")
        after = {r["테스트ID"]: r["fingerprint"] for r in ev.read_plan(self.md)["rows"]}
        self.assertNotEqual(before["REB-UT-001"], after["REB-UT-001"])
        self.assertEqual(before["REB-UT-004"], after["REB-UT-004"])

    def test_rows_with_wrong_cell_count_are_reported(self):
        """최종 리뷰: 이스케이프 안 된 | 로 칸이 밀린 행을 조용히 잘라 읽어 지문·판정 입력이 틀렸다."""
        write(Path(self.tmp.name), "REB-단위테스트계획서.md", PLAN_MD.replace('| "파일 용량 초과" 안내 |', '| "파일 | 용량 초과" 안내 |'))
        plan = ev.read_plan(self.md)
        self.assertEqual(plan["malformed"], ["REB-UT-002"])
        self.assertEqual({r["테스트ID"]: r["malformed"] for r in plan["rows"]}["REB-UT-001"], False)

    def test_next_id_skips_numbers_used_elsewhere(self):
        """최종 리뷰: 지운 마지막 번호를 다음 ID 로 다시 냈다 — 개정이력·backup 에 남은 번호도 차지한 것으로 본다."""
        write(Path(self.tmp.name), "REB-단위테스트계획서.md", PLAN_MD.replace(
            "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |",
            "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |\n| 2.0 | 2026.10.01 | 삭제 | 단위테스트 2건 삭제(REB-UT-006~007) | 구본승 | |"))
        self.assertEqual(ev.read_plan(self.md)["next_id"], "REB-UT-008")
        write(Path(self.tmp.name), "backup/REB-단위테스트계획서_261001.md", PLAN_MD.replace("REB-UT-005", "REB-UT-009"))
        self.assertEqual(ev.read_plan(self.md)["next_id"], "REB-UT-010")

    def test_missing_table_is_error(self):
        self.md.write_text("# 빈 문서\n", encoding="utf-8")
        with self.assertRaises(ev.InputError):
            ev.read_plan(self.md)


# 대조 결과 — 001 은 PM 확인, 004 는 제외, 005 는 비기능
JUDGED = {
    "REB-UT-001": ("Pass", "PM 확인 — 2026.10.11", "2026.10.11", "김개발"),
    "REB-UT-002": ("Pass", "테스트 통과 — FileSizeLimitTest.rejectsOverLimit (2026.10.10)", "2026.10.10", "김개발"),
    "REB-UT-003": ("미검증", "기준 불일치 — 계획 1,000MB ↔ 테스트 500MB", "", ""),
    "REB-UT-004": ("미검증", "제외 — 통합 환경 필요", "", ""),
    "REB-UT-005": ("미검증", "비기능 — 측정 절차로 검증", "", ""),
}
FIRST = {"버전": "1.0", "개정일": "2026.10.14", "개정 사유": "신규", "개정 내용": "최초 작성 — 수행 결과 기입", "작성자": "구본승"}


class ResultTests(unittest.TestCase):
    """요구 변경(2026-10-15): 계획서 원본은 그대로 두고, 계획서 행을 옮긴 단위테스트결과서에 수행 결과를 쓴다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="result 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = write(self.root, "REB-단위테스트계획서.md", PLAN_MD)
        self.result = self.root / "REB-단위테스트결과서.md"
        self.ledger = self.root / "증적" / "REB-단위테스트수행대장.md"

    def facts(self):
        data = ev.read_plan(self.plan, result=self.result, ledger=self.ledger)
        return data, {r["테스트ID"]: r for r in data["rows"]}

    def changes(self, judged=None, revision=FIRST, keep=(), **over):
        data, _ = self.facts()
        judged = judged or JUDGED
        rows = {t: {"상태": s, "사유": why, "수행일": d, "담당자": who, "근거": "", "비고": "", "keep": t in keep}
                for t, (s, why, d, who) in judged.items()}
        base = {"plan_hash": data["plan_hash"], "result_hash": data["result"]["hash"], "date": "2026.10.14",
                "project": "테스트 사업", "sources": "reb-api D:/projects/reb-api (main · a1b2c3d)", "note": "",
                "mapping": {"kim.dev": "김개발"}, "basis": "reb-api main · a1b2c3d",
                "candidates": {"new": 1, "boost": 0}, "revision": revision, "rows": rows}
        base.update(over)
        return base

    def edit(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_bytes(text.replace(old, new).encode("utf-8"))

    def result_rows(self):
        lines = self.result.read_text(encoding="utf-8").splitlines()
        head, rows, _ = ev._table(lines)
        return head, {cells[0]: dict(zip(head, cells)) for _, cells, _ in rows}

    def test_first_write_creates_the_result_and_leaves_the_plan_untouched(self):
        before = self.plan.read_bytes()
        summary = ev.write_result(self.plan, self.result, self.ledger, self.changes())
        self.assertEqual(self.plan.read_bytes(), before)
        text = self.result.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# 단위테스트결과서 — 테스트\n"))
        self.assertIn("> 근거: DE-13 v1.0", text)
        self.assertIn("| 1.0 | 2026.10.14 | 신규 | 최초 작성 — 수행 결과 기입 | 구본승 | |", text)
        self.assertIn("## 단위테스트결과 — 테스트", text)
        head, rows = self.result_rows()
        self.assertEqual(head[-4:], ["테스트담당자", "수행일", "결과", "사유"])
        self.assertEqual([rows["REB-UT-002"][c] for c in ("사전조건", "결과", "테스트담당자", "수행일")],
                         ["〃", "Pass", "김개발", "2026.10.10"])  # 케이스 칸은 계획서 원문 그대로 옮긴다
        self.assertEqual(summary["added"], list(JUDGED))
        self.assertEqual((summary["changed"], summary["dropped"]), ([], []))
        data, facts = self.facts()
        self.assertEqual({r["written_by"] for r in facts.values()}, {"tool"})
        last = data["ledger"]["history"][-1]
        self.assertEqual([last[k] for k in ("계획서 버전", "결과서 버전", "Pass", "Fail", "미구현", "미검증", "수행률", "신규 후보")],
                         ["1.0", "1.0", "2", "0", "0", "3", "67% (2/3)", "1"])

    def test_values_written_by_hand_in_the_plan_seed_the_result_as_human_values(self):
        """계획서에 손으로 적어 둔 결과·배정 담당자는 결과서로 옮겨 사람 값으로 지킨다."""
        self.edit(self.plan, "| 1,000MB 파일 | 정상 등록 | 1건 저장 | 없음 | | | |",
                  "| 1,000MB 파일 | 정상 등록 | 1건 저장 | 없음 | 홍길동 | 2026.10.12 | Fail |")
        self.edit(self.plan, "| 목록 조회 | 5건 표시 | 변화 없음 | 없음 | | | |", "| 목록 조회 | 5건 표시 | 변화 없음 | 없음 | 최개발 | | |")
        _, facts = self.facts()
        self.assertEqual((facts["REB-UT-003"]["written_by"], facts["REB-UT-003"]["결과"]), ("human", "Fail"))
        self.assertEqual(facts["REB-UT-004"]["written_by"], "human")
        ev.write_result(self.plan, self.result, self.ledger, self.changes(keep=("REB-UT-003", "REB-UT-004")))
        _, rows = self.result_rows()
        self.assertEqual([rows["REB-UT-003"][c] for c in ("결과", "사유", "수행일", "테스트담당자")],
                         ["Fail", "기존 기입 — 사유 미기재", "2026.10.12", "홍길동"])
        # 배정 담당자만 있던 행은 결과·사유를 채우되 담당자는 둔다
        self.assertEqual([rows["REB-UT-004"][c] for c in ("결과", "사유", "테스트담당자")], ["미검증", "제외 — 통합 환경 필요", "최개발"])
        data, facts = self.facts()
        self.assertEqual((facts["REB-UT-003"]["written_by"], facts["REB-UT-003"]["prev"]["상태"]), ("human", "미검증"))
        self.assertIn("기존 기입 유지", facts["REB-UT-003"]["prev"]["비고"])
        self.assertEqual(facts["REB-UT-004"]["written_by"], "human")
        self.assertEqual(data["ledger"]["history"][-1]["Fail"], "1")  # 고객 문서에 보이는 값으로 센다

    def test_rerun_without_changes_leaves_the_result_alone(self):
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        before = self.result.read_bytes()
        with self.assertRaises(ev.InputError):  # 바뀐 것이 없는데 개정이력 행이 오면 거부
            ev.write_result(self.plan, self.result, self.ledger, self.changes(revision={**FIRST, "버전": "2.0", "개정 사유": "보완"}))
        summary = ev.write_result(self.plan, self.result, self.ledger, self.changes(revision=None, date="2026.10.15"))
        self.assertFalse(summary["written"])
        self.assertEqual(self.result.read_bytes(), before)
        self.assertFalse((self.root / "backup").exists())
        data, _ = self.facts()
        self.assertEqual([h["반영일"] for h in data["ledger"]["history"]], ["2026.10.14", "2026.10.15"])

    def test_changes_need_one_higher_revision_and_keep_a_copy(self):
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        first = self.result.read_bytes()
        judged = {**JUDGED, "REB-UT-003": ("Pass", "PM 확인 — 2026.10.15", "2026.10.15", "김개발")}
        for bad in (None, {**FIRST, "개정 사유": "보완"}, {**FIRST, "버전": "2.0", "개정 사유": "수정"}):
            with self.assertRaises(ev.InputError):
                ev.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision=bad))
        self.assertEqual(self.result.read_bytes(), first)
        summary = ev.write_result(self.plan, self.result, self.ledger, self.changes(
            judged=judged, revision={**FIRST, "버전": "2.0", "개정 사유": "보완", "개정 내용": "결과 갱신(REB-UT-003)"}))
        self.assertEqual(summary["changed"], ["REB-UT-003"])
        copy = self.root / "backup" / f"REB-단위테스트결과서_{datetime.now():%y%m%d}.md"
        self.assertEqual(copy.read_bytes(), first)
        self.assertEqual(summary["backup"], "backup/" + copy.name)

    def test_result_follows_rows_added_edited_and_removed_in_the_plan(self):
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.plan, "| REB-UT-003 | REB-FN-001 | REB-RE-001 | 〃 | 1,000MB 파일 | 정상 등록 | 1건 저장 | 없음 | | | |\n", "")
        self.edit(self.plan, '| "파일 용량 초과" 안내 |', '| "파일 용량(1,000MB)을 초과했습니다" 안내 |')
        self.edit(self.plan, "| REB-UT-005 |", "| REB-UT-006 | REB-FN-002 | REB-RE-002 | 회차 0건 | 목록 조회 | \"자료 없음\" 안내 | 변화 없음 | 없음 | | | |\n| REB-UT-005 |")
        self.edit(self.plan, "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |",
                  "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |\n| 2.0 | 2026.10.15 | 변경 | 케이스 수정 | 구본승 | |")
        data, facts = self.facts()
        self.assertTrue(facts["REB-UT-002"]["case_changed"])
        # 계획서를 고친 것이지 결과서를 손으로 고친 것이 아니다 — 결과서는 지난 쓰기 그대로다
        self.assertEqual(facts["REB-UT-002"]["result_case_edited"], [])
        self.assertEqual((facts["REB-UT-006"]["in_result"], facts["REB-UT-006"]["written_by"]), (False, "empty"))
        self.assertEqual(data["result"]["only"], ["REB-UT-003"])
        self.assertEqual((data["result"]["basis_version"], data["last_version"]), ("1.0", "2.0"))  # 결과서가 낡았다
        judged = {t: v for t, v in JUDGED.items() if t != "REB-UT-003"}
        judged["REB-UT-002"] = ("미검증", "케이스 변경 — 기대결과 수정, 테스트는 \"파일 용량 초과\" 확인", "", "")
        judged["REB-UT-006"] = ("미구현", "대응 테스트 없음", "", "")
        summary = ev.write_result(self.plan, self.result, self.ledger, self.changes(
            judged=judged, revision={**FIRST, "버전": "2.0", "개정 사유": "변경", "개정 내용": "계획서 v2.0 반영"}))
        self.assertEqual((summary["added"], summary["dropped"]), (["REB-UT-006"], ["REB-UT-003"]))
        self.assertIn("REB-UT-002", summary["changed"])
        head, rows = self.result_rows()
        self.assertEqual(list(rows), ["REB-UT-001", "REB-UT-002", "REB-UT-004", "REB-UT-006", "REB-UT-005"])
        self.assertEqual(rows["REB-UT-002"]["기대결과"], '"파일 용량(1,000MB)을 초과했습니다" 안내')
        self.assertIn("> 근거: DE-13 v2.0", self.result.read_text(encoding="utf-8"))

    def test_plan_revision_alone_still_updates_the_result_basis(self):
        """계획서 버전만 올라도 결과서 근거가 낡은 채로 남지 않게 한다."""
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.plan, "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |",
                  "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |\n| 2.0 | 2026.10.15 | 보완 | 문구 정리 | 구본승 | |")
        with self.assertRaises(ev.InputError):
            ev.write_result(self.plan, self.result, self.ledger, self.changes(revision=None))
        summary = ev.write_result(self.plan, self.result, self.ledger, self.changes(revision={**FIRST, "버전": "2.0", "개정 사유": "보완"}))
        self.assertTrue(summary["written"])
        self.assertIn("> 근거: DE-13 v2.0", self.result.read_text(encoding="utf-8"))

    def test_hand_edits_to_the_result_are_seen(self):
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.result, "| 5건 표시 |", "| 5건 표시(최신순) |")
        self.edit(self.result, "| 미검증 | 제외 — 통합 환경 필요 |", "| Fail | 수동 시험 실패 — 정렬 오류 |")
        xlsx = write(self.root, "xlsx/REB-단위테스트결과서.xlsx", "x")
        later = self.result.stat().st_mtime + 60
        os.utime(xlsx, (later, later))
        data, facts = self.facts()
        self.assertEqual(facts["REB-UT-004"]["result_case_edited"], ["기대결과"])  # 다음 쓰기에서 계획서 값으로 돌아간다
        self.assertEqual((facts["REB-UT-004"]["written_by"], facts["REB-UT-004"]["결과"]), ("human", "Fail"))
        self.assertTrue(data["result"]["xlsx_newer"])

    def test_approval_is_void_once_plan_or_result_changes(self):
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        judged = {**JUDGED, "REB-UT-003": ("Pass", "PM 확인 — 2026.10.15", "2026.10.15", "김개발")}
        rev = {**FIRST, "버전": "2.0", "개정 사유": "보완"}
        approved = self.changes(judged=judged, revision=rev)
        self.edit(self.result, "| 미검증 | 제외 — 통합 환경 필요 |", "| Fail | 수동 시험 실패 |")
        with self.assertRaises(ev.InputError):
            ev.write_result(self.plan, self.result, self.ledger, approved)
        approved = self.changes(judged=judged, revision=rev)
        self.edit(self.plan, "| 회차 생성 |", "| 회차 신규 생성 |")
        before = self.result.read_bytes()
        with self.assertRaises(ev.InputError):
            ev.write_result(self.plan, self.result, self.ledger, approved)
        self.assertEqual(self.result.read_bytes(), before)

    def test_refuses_broken_tables_duplicate_ids_and_bad_rows(self):
        cases = []
        missing = self.changes()
        del missing["rows"]["REB-UT-005"]
        cases.append(missing)
        odd = self.changes()
        odd["rows"]["REB-UT-001"]["상태"] = "보류"
        cases.append(odd)
        blank = self.changes()
        blank["rows"]["REB-UT-002"]["사유"] = " "
        cases.append(blank)
        cases.append(self.changes(date="10/14"))
        cases.append(self.changes(revision={**FIRST, "버전": "2.0"}))  # 새 결과서는 1.0 신규로 시작한다
        for changes in cases:
            with self.assertRaises(ev.InputError):
                ev.write_result(self.plan, self.result, self.ledger, changes)
        self.assertFalse(self.result.exists() or self.ledger.exists())
        self.edit(self.plan, "| REB-UT-004 |", "| REB-UT-001 |")
        data, _ = self.facts()
        self.assertEqual(data["duplicates"], ["REB-UT-001"])
        with self.assertRaises(ev.InputError):
            ev.write_result(self.plan, self.result, self.ledger, self.changes())

    def test_broken_result_table_is_reported_and_not_overwritten(self):
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.result, "| 미검증 | 제외 — 통합 환경 필요 |", "| 미검증 | 제외 | 통합 환경 필요 |")
        data, _ = self.facts()
        self.assertEqual(data["result"]["malformed"], ["REB-UT-004"])
        before = self.result.read_bytes()
        judged = {**JUDGED, "REB-UT-003": ("Pass", "PM 확인 — 2026.10.15", "2026.10.15", "김개발")}
        with self.assertRaises(ev.InputError):
            ev.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision={**FIRST, "버전": "2.0", "개정 사유": "보완"}))
        self.assertEqual(self.result.read_bytes(), before)

    def test_ledger_behind_the_result_is_flagged(self):
        """결과서만 바뀌고 수행대장이 따라오지 못한 상태(손 수정·끊긴 반영)를 알린다."""
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.result, "| 1.0 | 2026.10.14 | 신규 | 최초 작성 — 수행 결과 기입 | 구본승 | |",
                  "| 1.0 | 2026.10.14 | 신규 | 최초 작성 — 수행 결과 기입 | 구본승 | |\n| 2.0 | 2026.10.15 | 보완 | 손 수정 | 홍길동 | |")
        data, _ = self.facts()
        self.assertTrue(data["ledger"]["stale"])

    def test_missing_ledger_or_missing_result(self):
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        self.ledger.unlink()
        data, facts = self.facts()
        self.assertFalse(data["ledger"]["exists"])
        self.assertEqual({r["written_by"] for r in facts.values()}, {"human"})  # 누가 썼는지 가릴 근거가 없다
        ev.write_result(self.plan, self.result, self.ledger, self.changes(revision=None))
        self.result.unlink()
        data, facts = self.facts()
        self.assertFalse(data["result"]["exists"])
        self.assertEqual({r["written_by"] for r in facts.values()}, {"empty"})
        ev.write_result(self.plan, self.result, self.ledger, self.changes())  # 결과서를 1.0 신규로 다시 만든다
        data, _ = self.facts()
        self.assertEqual(len(data["ledger"]["history"]), 2)  # 수행대장을 지운 뒤 다시 쌓인 이력

    def test_inherits_exclusion_and_pm_confirmation_until_the_case_changes(self):
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        _, facts = self.facts()
        self.assertEqual({t: r["inherit"] for t, r in facts.items() if r["inherit"]}, {"REB-UT-001": "PM 확인", "REB-UT-004": "제외"})
        self.edit(self.plan, "| 5건 표시 |", "| 5건 표시, 등록일 역순 |")
        _, facts = self.facts()
        self.assertTrue(facts["REB-UT-004"]["case_changed"])
        self.assertEqual(facts["REB-UT-004"]["inherit"], "")
        self.assertFalse(facts["REB-UT-001"]["case_changed"])

    def test_keeps_name_mapping_and_past_history(self):
        old = ("# 단위테스트 수행대장 — 옛 사업\n\n> 근거: DE-13 v1.0 · 반영 2026.10.10\n\n## 담당자 매핑\n\n"
               "| 작성자 | 실명 |\n|--------|------|\n| kim.dev | 김개발(옛) |\n| lee.dev | 이개발 |\n\n## 수행 현황\n\n"
               "| 테스트ID | 상태 | 사유 | 근거 | 수행일 | 담당자 | 행 지문 | 비고 |\n|---|---|---|---|---|---|---|---|\n\n"
               "## 반영 이력\n\n| 반영일 | DE-13 버전 | 수행 | 실패 | 수행률 |\n|---|---|---|---|---|\n| 2026.10.10 | 1.0 | 3 | 1 | 60% |\n")
        write(self.ledger.parent, self.ledger.name, old)
        ev.write_result(self.plan, self.result, self.ledger, self.changes(project="", mapping={"kim.dev": "김개발", "park.dev": "박개발"}))
        data, _ = self.facts()
        self.assertEqual(data["ledger"]["project"], "옛 사업")
        self.assertEqual(data["ledger"]["mapping"], {"kim.dev": "김개발(옛)", "lee.dev": "이개발", "park.dev": "박개발"})
        text = self.ledger.read_text(encoding="utf-8")
        self.assertIn("| 반영일 | DE-13 버전 | 수행 | 실패 | 수행률 |\n|---|---|---|---|---|\n| 2026.10.10 | 1.0 | 3 | 1 | 60% |\n", text)
        self.assertEqual(data["ledger"]["history"][-1]["수행률"], "67% (2/3)")

    def test_dry_run_and_unwritable_text_write_nothing(self):
        summary = ev.write_result(self.plan, self.result, self.ledger, self.changes(), dry_run=True)
        self.assertEqual((summary["counts"]["Pass"], summary["rate"], summary["written"]), (2, "67% (2/3)", False))
        self.assertFalse(self.result.exists() or self.ledger.exists())
        bad = self.changes()
        bad["rows"]["REB-UT-002"]["사유"] = "테스트 통과 \ud800"
        with self.assertRaises(ev.InputError):
            ev.write_result(self.plan, self.result, self.ledger, bad)
        self.assertFalse(self.result.exists() or self.ledger.exists())

    def test_dry_run_comes_before_the_revision(self):
        """평가 8회차: 스킬은 dry-run 숫자로 개정이력을 정하는데 도구가 개정이력 없는 dry-run 을 거부했다."""
        s = ev.write_result(self.plan, self.result, self.ledger, self.changes(revision=None), dry_run=True)
        self.assertEqual((s["needs_revision"], s["next_version"], len(s["added"])), (True, "1.0", 5))
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        judged = {**JUDGED, "REB-UT-003": ("Pass", "PM 확인 — 2026.10.15", "2026.10.15", "김개발")}
        s = ev.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision=None), dry_run=True)
        self.assertEqual((s["needs_revision"], s["next_version"], s["changed"]), (True, "2.0", ["REB-UT-003"]))
        s = ev.write_result(self.plan, self.result, self.ledger, self.changes(revision=None), dry_run=True)
        self.assertFalse(s["needs_revision"])
        changes = self.root / "changes.json"
        changes.write_text(json.dumps(self.changes(judged=judged, revision=None), ensure_ascii=False), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(ev.main(["write", "--de13", str(self.plan), "--result", str(self.result), "--ledger", str(self.ledger),
                                      "--changes", str(changes), "--dry-run"]), 0)
        self.assertIn("REB-UT-003", out.getvalue())  # 개정 내용에 바뀐 행 ID 를 적어야 한다

    def test_control_characters_are_refused(self):
        """평가 8회차: Windows 경로의 역슬래시가 이스케이프로 풀려 BEL·CR 이 수행대장 머리말에 그대로 들어갔다."""
        for bad in (self.changes(sources="reb-api D:\\projects\x07\reb-api"), self.changes()):
            if bad["sources"].startswith("reb-api D:/"):
                bad["rows"]["REB-UT-002"]["사유"] = "테스트 통과\x0b"
            with self.assertRaises(ev.InputError):
                ev.write_result(self.plan, self.result, self.ledger, bad)
        self.assertFalse(self.result.exists() or self.ledger.exists())

    def test_ledger_title_takes_the_plan_name_when_project_is_blank(self):
        """평가 8회차: 결과서 제목은 계획서에서, 수행대장 제목은 프로파일에서 와서 사업명이 달랐다."""
        ev.write_result(self.plan, self.result, self.ledger, self.changes(project=""))
        self.assertTrue(self.ledger.read_text(encoding="utf-8").startswith("# 단위테스트 수행대장 — 테스트\n"))

    def test_dropping_an_inherited_judgment_is_reported(self):
        """평가 8회차: 이어받아야 할 PM 확인을 '실행 결과 없음' 으로 덮어써도 도구가 말없이 받았다."""
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        judged = {**JUDGED, "REB-UT-001": ("미검증", "실행 결과 없음 — CycleTest.creates", "", "")}
        rev = {**FIRST, "버전": "2.0", "개정 사유": "보완"}
        s = ev.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision=rev), dry_run=True)
        self.assertEqual(s["inherit_dropped"], ["REB-UT-001"])
        s = ev.write_result(self.plan, self.result, self.ledger, self.changes(revision=None), dry_run=True)
        self.assertEqual(s["inherit_dropped"], [])

    def test_plan_edits_missing_from_the_plan_revisions_are_flagged(self):
        """평가 8회차: 개정이력 없이 고친 계획서 케이스를 실행자가 개정이력을 직접 읽어 가렸다."""
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.plan, '| "파일 용량 초과" 안내 |', '| "파일 용량(1,000MB)을 초과했습니다" 안내 |')
        data, _ = self.facts()
        self.assertEqual(data["ledger"]["unrecorded"], ["REB-UT-002"])
        self.edit(self.plan, "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |",
                  "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |\n| 2.0 | 2026.10.15 | 변경 | 기대결과 수정(REB-UT-001~002) | 구본승 | |")
        data, _ = self.facts()
        self.assertEqual(data["ledger"]["unrecorded"], [])

    def test_keeps_line_endings_and_title_of_an_existing_result(self):
        ev.write_result(self.plan, self.result, self.ledger, self.changes())
        text = self.result.read_text(encoding="utf-8").replace("# 단위테스트결과서 — 테스트", "# 단위테스트결과서 — 테스트 (1차)")
        self.result.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        judged = {**JUDGED, "REB-UT-003": ("Pass", "PM 확인 — 2026.10.15", "2026.10.15", "김개발")}
        ev.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision={**FIRST, "버전": "2.0", "개정 사유": "보완"}))
        raw = self.result.read_bytes().decode("utf-8")
        self.assertNotIn("\n", raw.replace("\r\n", ""))
        self.assertTrue(raw.startswith("# 단위테스트결과서 — 테스트 (1차)\r\n"))
        self.assertIn("| 2.0 | 2026.10.14 | 보완 |", raw)

    def test_cli(self):
        out = self.root / "plan.json"
        self.assertEqual(ev.main(["plan", "--de13", str(self.plan), "--result", str(self.result), "--ledger", str(self.ledger),
                                  "--out", str(out)]), 0)
        self.assertFalse(json.loads(out.read_text(encoding="utf-8"))["result"]["exists"])
        changes = self.root / "changes.json"
        changes.write_text(json.dumps(self.changes(), ensure_ascii=False), encoding="utf-8")
        args = ["write", "--de13", str(self.plan), "--result", str(self.result), "--ledger", str(self.ledger), "--changes", str(changes)]
        self.assertEqual(ev.main(args + ["--dry-run"]), 0)
        self.assertFalse(self.result.exists())
        self.assertEqual(ev.main(args), 0)
        self.assertTrue(self.result.exists())
        self.assertEqual(ev.main(args), 2)  # 같은 승인안을 두 번 쓰면 결과서 지문이 달라 거부


if __name__ == "__main__":
    unittest.main()
