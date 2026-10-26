"""로컬 실측 증적 검증과 DE-13 읽기·결과서 기록의 회귀 검사."""

import contextlib
import copy
import hashlib
import io
import json
import os
import tempfile
import unittest
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from datetime import datetime
from pathlib import Path

from helpers import load_util

ev = load_util("test-evidence.py")

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


# 실측 결과 — 001·002 통과, 003 환경 차단, 004 제외, 005 비기능
JUDGED = {
    "REB-UT-001": ("Pass", "실측 통과 — 등록 응답과 DB 1건 확인", "2026.10.14", "김개발"),
    "REB-UT-002": ("Pass", "실측 통과 — HTTP 400 안내와 저장 없음 확인", "2026.10.14", "김개발"),
    "REB-UT-003": ("미검증", "실행 차단 — 파일 준비 환경 없음", "", ""),
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
        self.evidence = self.root / "증적" / "run.json"

    def facts(self):
        data = ev.read_plan(self.plan, result=self.result, ledger=self.ledger)
        return data, {r["테스트ID"]: r for r in data["rows"]}

    def changes(self, judged=None, revision=FIRST, keep=(), **over):
        data, _ = self.facts()
        judged = judged or JUDGED
        self.make_evidence(data, judged)
        rows = {t: {"상태": s, "사유": why, "수행일": d, "담당자": who, "근거": "", "비고": "", "keep": t in keep}
                for t, (s, why, d, who) in judged.items()}
        base = {"plan_hash": data["plan_hash"], "result_hash": data["result"]["hash"], "date": "2026.10.14",
                "evidence_hash": hashlib.sha256(self.evidence.read_bytes()).hexdigest(),
                "project": "테스트 사업", "sources": "reb-api D:/projects/reb-api (main · a1b2c3d)", "note": "",
                "mapping": {"kim.dev": "김개발"}, "basis": "reb-api main · a1b2c3d",
                "candidates": {"new": 1, "boost": 0}, "revision": revision, "rows": rows}
        base.update(over)
        return base

    def write_result(self, plan, result, ledger, changes, **kwargs):
        return ev.write_result(plan, result, ledger, changes, self.evidence, **kwargs)

    def save_evidence(self, evidence):
        self.evidence.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
        return evidence

    def make_evidence(self, plan, judged):
        startup = write(self.evidence.parent, "startup.log", "Local app ready at http://127.0.0.1:8080\n")
        rows = {}
        for row in plan["rows"]:
            tid = row["테스트ID"]
            state = judged.get(tid, ("미검증",))[0]
            completed = state in ("Pass", "Fail")
            execution = "completed" if completed else "not_implemented" if state == "미구현" else "blocked"
            raw = json.dumps({"request": row["입력"], "response": "실측 응답", "state": state}, ensure_ascii=False)
            artifact = write(self.evidence.parent, f"raw/{tid}.json", raw)
            rel = artifact.relative_to(self.evidence.parent).as_posix()
            artifacts = [{"path": rel, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}] if completed or state == "미구현" else []
            checks = [{"field": field, "expected": row.get(field, ""), "observed": "실제 관측: " + row.get(field, ""),
                       "matched": not (state == "Fail" and field == "기대결과"), "artifact": rel}
                      for field in ev.CASE_FIELDS] if completed else []
            rows[tid] = {"fingerprint": row["fingerprint"], "execution": execution, "channel": "api" if completed else "none",
                         "actual": f"{tid} 실측: {state}", "checks": checks, "artifacts": artifacts}
        return self.save_evidence({"schema_version": 1, "run_id": "run-20261014-01", "plan_hash": plan["plan_hash"],
                                   "started_at": "2026-10-14T09:00:00+09:00", "finished_at": "2026-10-14T09:10:00+09:00",
                                   "operator": "김개발", "sources": [{"path": str(self.root), "revision": "abc123", "dirty": False}],
                                   "targets": [{"base_url": "http://127.0.0.1:8080", "startup_evidence": "startup.log",
                                                "startup_sha256": hashlib.sha256(startup.read_bytes()).hexdigest()}], "rows": rows})

    def load_evidence(self):
        return json.loads(self.evidence.read_text(encoding="utf-8"))

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
        summary = self.write_result(self.plan, self.result, self.ledger, self.changes())
        self.assertEqual(self.plan.read_bytes(), before)
        text = self.result.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# IM-03 단위테스트결과서 — 테스트\n"))  # 옛 gx-pm 의 단위테스트결과서 코드를 잇는다
        self.assertIn("> 근거: DE-13 v1.0", text)
        self.assertIn("| 1.0 | 2026.10.14 | 신규 | 최초 작성 — 수행 결과 기입 | 구본승 | |", text)
        self.assertIn("## 단위테스트결과 — 테스트", text)
        head, rows = self.result_rows()
        self.assertEqual(head[-5:], ["테스트담당자", "수행일", "결과", "사유", "실제결과"])
        self.assertEqual([rows["REB-UT-002"][c] for c in ("사전조건", "결과", "테스트담당자", "수행일")],
                         ["〃", "Pass", "김개발", "2026.10.14"])  # 케이스 칸은 계획서 원문 그대로 옮긴다
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
        self.write_result(self.plan, self.result, self.ledger, self.changes(keep=("REB-UT-003", "REB-UT-004")))
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
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        before = self.result.read_bytes()
        with self.assertRaises(ev.InputError):  # 바뀐 것이 없는데 개정이력 행이 오면 거부
            self.write_result(self.plan, self.result, self.ledger, self.changes(revision={**FIRST, "버전": "2.0", "개정 사유": "보완"}))
        summary = self.write_result(self.plan, self.result, self.ledger, self.changes(revision=None, date="2026.10.15"))
        self.assertFalse(summary["written"])
        self.assertEqual(self.result.read_bytes(), before)
        self.assertFalse((self.root / "backup").exists())
        data, _ = self.facts()
        self.assertEqual([h["반영일"] for h in data["ledger"]["history"]], ["2026.10.14", "2026.10.15"])

    def test_observation_padding_does_not_create_a_false_revision(self):
        changes = self.changes()
        evidence = self.load_evidence()
        evidence["rows"]["REB-UT-001"]["actual"] = "  HTTP 200; DB 0건, 상태  "
        self.save_evidence(evidence)
        changes["evidence_hash"] = hashlib.sha256(self.evidence.read_bytes()).hexdigest()
        self.write_result(self.plan, self.result, self.ledger, changes)
        before = self.result.read_bytes()
        changes["result_hash"] = self.facts()[0]["result"]["hash"]
        changes["revision"] = None
        summary = self.write_result(self.plan, self.result, self.ledger, changes)
        self.assertEqual(summary["changed"], [])
        self.assertFalse(summary["needs_revision"])
        self.assertFalse(summary["written"])
        self.assertEqual(self.result.read_bytes(), before)

    def test_changes_need_one_higher_revision_and_keep_a_copy(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        first = self.result.read_bytes()
        judged = {**JUDGED, "REB-UT-003": ("Pass", "실측 통과 — 등록 확인", "2026.10.14", "김개발")}
        for bad in (None, {**FIRST, "개정 사유": "보완"}, {**FIRST, "버전": "2.0", "개정 사유": "수정"}):
            with self.assertRaises(ev.InputError):
                self.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision=bad))
        self.assertEqual(self.result.read_bytes(), first)
        summary = self.write_result(self.plan, self.result, self.ledger, self.changes(
            judged=judged, revision={**FIRST, "버전": "2.0", "개정 사유": "보완", "개정 내용": "결과 갱신(REB-UT-003)"}))
        self.assertEqual(summary["changed"], ["REB-UT-003"])
        copy = self.root / "backup" / f"REB-단위테스트결과서_{datetime.now():%y%m%d}.md"
        self.assertEqual(copy.read_bytes(), first)
        self.assertEqual(summary["backup"], "backup/" + copy.name)

    def test_result_follows_rows_added_edited_and_removed_in_the_plan(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
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
        judged["REB-UT-002"] = ("미검증", "케이스 변경 — 기대결과 수정 후 재시험 필요", "", "")
        judged["REB-UT-006"] = ("미구현", "미구현 — 소스와 라우트의 기능 부재 확인", "", "")
        summary = self.write_result(self.plan, self.result, self.ledger, self.changes(
            judged=judged, revision={**FIRST, "버전": "2.0", "개정 사유": "변경", "개정 내용": "계획서 v2.0 반영"}))
        self.assertEqual((summary["added"], summary["dropped"]), (["REB-UT-006"], ["REB-UT-003"]))
        self.assertIn("REB-UT-002", summary["changed"])
        head, rows = self.result_rows()
        self.assertEqual(list(rows), ["REB-UT-001", "REB-UT-002", "REB-UT-004", "REB-UT-006", "REB-UT-005"])
        self.assertEqual(rows["REB-UT-002"]["기대결과"], '"파일 용량(1,000MB)을 초과했습니다" 안내')
        self.assertIn("> 근거: DE-13 v2.0", self.result.read_text(encoding="utf-8"))

    def test_plan_revision_alone_still_updates_the_result_basis(self):
        """계획서 버전만 올라도 결과서 근거가 낡은 채로 남지 않게 한다."""
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.plan, "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |",
                  "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |\n| 2.0 | 2026.10.15 | 보완 | 문구 정리 | 구본승 | |")
        with self.assertRaises(ev.InputError):
            self.write_result(self.plan, self.result, self.ledger, self.changes(revision=None))
        summary = self.write_result(self.plan, self.result, self.ledger, self.changes(revision={**FIRST, "버전": "2.0", "개정 사유": "보완"}))
        self.assertTrue(summary["written"])
        self.assertIn("> 근거: DE-13 v2.0", self.result.read_text(encoding="utf-8"))

    def test_hand_edits_to_the_result_are_seen(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
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
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        judged = {**JUDGED, "REB-UT-003": ("Pass", "실측 통과 — 등록 확인", "2026.10.14", "김개발")}
        rev = {**FIRST, "버전": "2.0", "개정 사유": "보완"}
        approved = self.changes(judged=judged, revision=rev)
        self.edit(self.result, "| 미검증 | 제외 — 통합 환경 필요 |", "| Fail | 수동 시험 실패 |")
        with self.assertRaises(ev.InputError):
            self.write_result(self.plan, self.result, self.ledger, approved)
        approved = self.changes(judged=judged, revision=rev)
        self.edit(self.plan, "| 회차 생성 |", "| 회차 신규 생성 |")
        before = self.result.read_bytes()
        with self.assertRaises(ev.InputError):
            self.write_result(self.plan, self.result, self.ledger, approved)
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
                self.write_result(self.plan, self.result, self.ledger, changes)
        self.assertFalse(self.result.exists() or self.ledger.exists())
        self.edit(self.plan, "| REB-UT-004 |", "| REB-UT-001 |")
        data, _ = self.facts()
        self.assertEqual(data["duplicates"], ["REB-UT-001"])
        with self.assertRaises(ev.InputError):
            self.write_result(self.plan, self.result, self.ledger, self.changes())

    def test_broken_result_table_is_reported_and_not_overwritten(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.result, "| 미검증 | 제외 — 통합 환경 필요 |", "| 미검증 | 제외 | 통합 환경 필요 |")
        data, _ = self.facts()
        self.assertEqual(data["result"]["malformed"], ["REB-UT-004"])
        before = self.result.read_bytes()
        judged = {**JUDGED, "REB-UT-003": ("Pass", "실측 통과 — 등록 확인", "2026.10.14", "김개발")}
        with self.assertRaises(ev.InputError):
            self.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision={**FIRST, "버전": "2.0", "개정 사유": "보완"}))
        self.assertEqual(self.result.read_bytes(), before)

    def test_ledger_behind_the_result_is_flagged(self):
        """결과서만 바뀌고 수행대장이 따라오지 못한 상태(손 수정·끊긴 반영)를 알린다."""
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.result, "| 1.0 | 2026.10.14 | 신규 | 최초 작성 — 수행 결과 기입 | 구본승 | |",
                  "| 1.0 | 2026.10.14 | 신규 | 최초 작성 — 수행 결과 기입 | 구본승 | |\n| 2.0 | 2026.10.15 | 보완 | 손 수정 | 홍길동 | |")
        data, _ = self.facts()
        self.assertTrue(data["ledger"]["stale"])

    def test_missing_ledger_or_missing_result(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        self.ledger.unlink()
        data, facts = self.facts()
        self.assertFalse(data["ledger"]["exists"])
        self.assertEqual({r["written_by"] for r in facts.values()}, {"human"})  # 누가 썼는지 가릴 근거가 없다
        self.write_result(self.plan, self.result, self.ledger, self.changes(revision=None))
        self.result.unlink()
        data, facts = self.facts()
        self.assertFalse(data["result"]["exists"])
        self.assertEqual({r["written_by"] for r in facts.values()}, {"empty"})
        self.write_result(self.plan, self.result, self.ledger, self.changes())  # 결과서를 1.0 신규로 다시 만든다
        data, _ = self.facts()
        self.assertEqual(len(data["ledger"]["history"]), 2)  # 수행대장을 지운 뒤 다시 쌓인 이력

    def test_inherits_only_exclusion_until_the_case_changes(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        _, facts = self.facts()
        self.assertEqual({t: r["inherit"] for t, r in facts.items() if r["inherit"]}, {"REB-UT-004": "제외"})
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
        self.write_result(self.plan, self.result, self.ledger, self.changes(project="", mapping={"kim.dev": "김개발", "park.dev": "박개발"}))
        data, _ = self.facts()
        self.assertEqual(data["ledger"]["project"], "옛 사업")
        self.assertEqual(data["ledger"]["mapping"], {"kim.dev": "김개발(옛)", "lee.dev": "이개발", "park.dev": "박개발"})
        text = self.ledger.read_text(encoding="utf-8")
        self.assertIn("| 반영일 | DE-13 버전 | 수행 | 실패 | 수행률 |\n|---|---|---|---|---|\n| 2026.10.10 | 1.0 | 3 | 1 | 60% |\n", text)
        self.assertEqual(data["ledger"]["history"][-1]["수행률"], "67% (2/3)")

    def test_dry_run_and_unwritable_text_write_nothing(self):
        summary = self.write_result(self.plan, self.result, self.ledger, self.changes(), dry_run=True)
        self.assertEqual((summary["counts"]["Pass"], summary["rate"], summary["written"]), (2, "67% (2/3)", False))
        self.assertFalse(self.result.exists() or self.ledger.exists())
        bad = self.changes()
        bad["rows"]["REB-UT-002"]["사유"] = "테스트 통과 \ud800"
        with self.assertRaises(ev.InputError):
            self.write_result(self.plan, self.result, self.ledger, bad)
        self.assertFalse(self.result.exists() or self.ledger.exists())

    def test_dry_run_comes_before_the_revision(self):
        """평가 8회차: 스킬은 dry-run 숫자로 개정이력을 정하는데 도구가 개정이력 없는 dry-run 을 거부했다."""
        s = self.write_result(self.plan, self.result, self.ledger, self.changes(revision=None), dry_run=True)
        self.assertEqual((s["needs_revision"], s["next_version"], len(s["added"])), (True, "1.0", 5))
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        judged = {**JUDGED, "REB-UT-003": ("Pass", "실측 통과 — 등록 확인", "2026.10.14", "김개발")}
        s = self.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision=None), dry_run=True)
        self.assertEqual((s["needs_revision"], s["next_version"], s["changed"]), (True, "2.0", ["REB-UT-003"]))
        s = self.write_result(self.plan, self.result, self.ledger, self.changes(revision=None), dry_run=True)
        self.assertFalse(s["needs_revision"])
        changes = self.root / "changes.json"
        changes.write_text(json.dumps(self.changes(judged=judged, revision=None), ensure_ascii=False), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(ev.main(["write", "--de13", str(self.plan), "--result", str(self.result), "--ledger", str(self.ledger),
                                      "--changes", str(changes), "--evidence", str(self.evidence), "--dry-run"]), 0)
        self.assertIn("REB-UT-003", out.getvalue())  # 개정 내용에 바뀐 행 ID 를 적어야 한다

    def test_control_characters_are_refused(self):
        """평가 8회차: Windows 경로의 역슬래시가 이스케이프로 풀려 BEL·CR 이 수행대장 머리말에 그대로 들어갔다."""
        for bad in (self.changes(sources="reb-api D:\\projects\x07\reb-api"), self.changes()):
            if bad["sources"].startswith("reb-api D:/"):
                bad["rows"]["REB-UT-002"]["사유"] = "테스트 통과\x0b"
            with self.assertRaises(ev.InputError):
                self.write_result(self.plan, self.result, self.ledger, bad)
        self.assertFalse(self.result.exists() or self.ledger.exists())

    def test_ledger_title_takes_the_plan_name_when_project_is_blank(self):
        """평가 8회차: 결과서 제목은 계획서에서, 수행대장 제목은 프로파일에서 와서 사업명이 달랐다."""
        self.write_result(self.plan, self.result, self.ledger, self.changes(project=""))
        self.assertTrue(self.ledger.read_text(encoding="utf-8").startswith("# 단위테스트 수행대장 — 테스트\n"))

    def test_dropping_an_inherited_exclusion_is_reported(self):
        """새 판단에서 제외 승계를 버린 행을 명시한다."""
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        judged = {**JUDGED, "REB-UT-004": ("미검증", "실행 차단 — 환경 준비 실패", "", "")}
        rev = {**FIRST, "버전": "2.0", "개정 사유": "보완"}
        s = self.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision=rev), dry_run=True)
        self.assertEqual(s["inherit_dropped"], ["REB-UT-004"])
        s = self.write_result(self.plan, self.result, self.ledger, self.changes(revision=None), dry_run=True)
        self.assertEqual(s["inherit_dropped"], [])

    def test_plan_edits_missing_from_the_plan_revisions_are_flagged(self):
        """평가 8회차: 개정이력 없이 고친 계획서 케이스를 실행자가 개정이력을 직접 읽어 가렸다."""
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.plan, '| "파일 용량 초과" 안내 |', '| "파일 용량(1,000MB)을 초과했습니다" 안내 |')
        data, _ = self.facts()
        self.assertEqual(data["ledger"]["unrecorded"], ["REB-UT-002"])
        self.edit(self.plan, "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |",
                  "| 1.0 | 2026.09.09 | 신규 | 최초 작성 | 구본승 | |\n| 2.0 | 2026.10.15 | 변경 | 기대결과 수정(REB-UT-001~002) | 구본승 | |")
        data, _ = self.facts()
        self.assertEqual(data["ledger"]["unrecorded"], [])

    def test_keeps_line_endings_and_title_of_an_existing_result(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        text = self.result.read_text(encoding="utf-8").replace("# IM-03 단위테스트결과서 — 테스트", "# IM-03 단위테스트결과서 — 테스트 (1차)")
        self.result.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        judged = {**JUDGED, "REB-UT-003": ("Pass", "실측 통과 — 등록 확인", "2026.10.14", "김개발")}
        self.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged, revision={**FIRST, "버전": "2.0", "개정 사유": "보완"}))
        raw = self.result.read_bytes().decode("utf-8")
        self.assertNotIn("\n", raw.replace("\r\n", ""))
        self.assertTrue(raw.startswith("# IM-03 단위테스트결과서 — 테스트 (1차)\r\n"))
        self.assertIn("| 2.0 | 2026.10.14 | 보완 |", raw)

    def test_cli(self):
        out = self.root / "plan.json"
        self.assertEqual(ev.main(["plan", "--de13", str(self.plan), "--result", str(self.result), "--ledger", str(self.ledger),
                                  "--out", str(out)]), 0)
        self.assertFalse(json.loads(out.read_text(encoding="utf-8"))["result"]["exists"])
        changes = self.root / "changes.json"
        changes.write_text(json.dumps(self.changes(), ensure_ascii=False), encoding="utf-8")
        args = ["write", "--de13", str(self.plan), "--result", str(self.result), "--ledger", str(self.ledger), "--changes", str(changes), "--evidence", str(self.evidence)]
        self.assertEqual(ev.main(args + ["--dry-run"]), 0)
        self.assertFalse(self.result.exists())
        self.assertEqual(ev.main(args), 0)
        self.assertTrue(self.result.exists())
        self.assertEqual(ev.main(args), 2)  # 같은 승인안을 두 번 쓰면 결과서 지문이 달라 거부

    def test_missing_and_partial_observations_cannot_pass(self):
        changes = self.changes()
        baseline = self.load_evidence()
        for field, matched in (("사전조건", False), ("입력", False), ("기대결과", None), ("사후조건", None)):
            with self.subTest(field=field):
                evidence = copy.deepcopy(baseline)
                row = evidence["rows"]["REB-UT-001"]
                row["checks"] = [c for c in row["checks"] if c["field"] != field]
                if field in ("사전조건", "입력"):
                    original = next(c for c in baseline["rows"]["REB-UT-001"]["checks"] if c["field"] == field)
                    row["checks"].append({**original, "matched": matched})
                self.save_evidence(evidence)
                judged = ev.validate_execution(ev.read_plan(self.plan), self.evidence)
                self.assertEqual(judged["rows"]["REB-UT-001"]["상태"], "미검증")
                changes["evidence_hash"] = judged["evidence_hash"]
                with self.assertRaisesRegex(ev.InputError, "증적 판정"):
                    self.write_result(self.plan, self.result, self.ledger, changes)
        evidence = copy.deepcopy(baseline)
        row = evidence["rows"]["REB-UT-001"]
        row.update(checks=[], artifacts=[], channel="none")
        self.save_evidence(evidence)
        self.assertEqual(ev.validate_execution(ev.read_plan(self.plan), self.evidence)["rows"]["REB-UT-001"]["상태"], "미검증")
        self.assertFalse(self.result.exists() or self.ledger.exists())

    def test_expected_and_postcondition_mismatches_fail_only_with_valid_inputs(self):
        self.changes()
        baseline = self.load_evidence()
        for field in ("기대결과", "사후조건"):
            evidence = copy.deepcopy(baseline)
            checks = evidence["rows"]["REB-UT-001"]["checks"]
            next(c for c in checks if c["field"] == field)["matched"] = False
            self.save_evidence(evidence)
            self.assertEqual(ev.validate_execution(ev.read_plan(self.plan), self.evidence)["rows"]["REB-UT-001"]["상태"], "Fail")
            next(c for c in checks if c["field"] == "사전조건")["matched"] = False
            self.save_evidence(evidence)
            self.assertEqual(ev.validate_execution(ev.read_plan(self.plan), self.evidence)["rows"]["REB-UT-001"]["상태"], "미검증")

    def test_execution_requires_complete_original_checks_and_raw_artifacts(self):
        self.changes()
        baseline = self.load_evidence()
        mutations = [
            lambda r: r.update(actual=" "),
            lambda r: r.update(execution="passed"),
            lambda r: r.update(channel="junit"),
            lambda r: r.update(checks="not an array"),
            lambda r: r.update(artifacts="not an array"),
            lambda r: r["checks"][0].update(expected="다른 사전조건"),
            lambda r: r["checks"][0].update(observed=""),
            lambda r: r["checks"][0].update(matched=1),
            lambda r: r["checks"][0].pop("matched"),
            lambda r: r["checks"][0].update(artifact="unlisted.json"),
            lambda r: r["checks"].append(copy.deepcopy(r["checks"][0])),
            lambda r: r["artifacts"][0].update(sha256="0" * 64),
            lambda r: r["artifacts"][0].update(sha256="abc123"),
            lambda r: r["artifacts"].append(copy.deepcopy(r["artifacts"][0])),
            lambda r: r["artifacts"][0].update(path="../outside.json"),
            lambda r: r["artifacts"][0].update(path="C:/outside.json"),
            lambda r: r["artifacts"][0].update(path="/outside.json"),
            lambda r: r["artifacts"][0].update(path="missing.json"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                evidence = copy.deepcopy(baseline)
                mutate(evidence["rows"]["REB-UT-001"])
                self.save_evidence(evidence)
                with self.assertRaises(ev.InputError):
                    ev.validate_execution(ev.read_plan(self.plan), self.evidence)
        self.save_evidence(baseline)
        (self.evidence.parent / baseline["rows"]["REB-UT-001"]["artifacts"][0]["path"]).write_bytes(b"")
        with self.assertRaises(ev.InputError):
            ev.validate_execution(ev.read_plan(self.plan), self.evidence)

    def test_execution_binds_plan_rows_times_and_local_targets(self):
        self.changes()
        baseline = self.load_evidence()
        mutations = [
            lambda e: e.update(schema_version=True),
            lambda e: e.update(run_id=""),
            lambda e: e.update(operator=""),
            lambda e: e.update(plan_hash="changed"),
            lambda e: e["rows"].pop("REB-UT-005"),
            lambda e: e["rows"].update({"UNKNOWN": e["rows"]["REB-UT-001"]}),
            lambda e: e["rows"]["REB-UT-001"].update(fingerprint="changed"),
            lambda e: e.update(started_at="2026-10-14T09:00:00"),
            lambda e: e.update(finished_at="2026-10-13T09:00:00+09:00"),
            lambda e: e.update(finished_at="2026-02-30T09:00:00+09:00"),
            lambda e: e.update(sources=[]),
            lambda e: e["sources"][0].update(dirty="false"),
            lambda e: e["sources"][0].update(revision=""),
            lambda e: e.update(targets=[]),
            lambda e: e["targets"][0].update(startup_evidence="../outside.log"),
            lambda e: e["targets"][0].update(startup_evidence="missing.log"),
        ]
        for url in ("https://example.com", "http://192.168.0.2", "file:///local", "http://localhost.evil.com", "http://[::2]", "http://user@localhost", "http://localhost:invalid", "http://[bad"):
            mutations.append(lambda e, url=url: e["targets"][0].update(base_url=url))
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                evidence = copy.deepcopy(baseline)
                mutate(evidence)
                self.save_evidence(evidence)
                with self.assertRaises(ev.InputError):
                    ev.validate_execution(ev.read_plan(self.plan), self.evidence)
        for url in ("http://127.0.0.1:8080", "http://127.3.4.5:9000", "https://localhost", "http://[::1]:8080"):
            evidence = copy.deepcopy(baseline)
            evidence["targets"][0]["base_url"] = url
            self.save_evidence(evidence)
            self.assertEqual(ev.validate_execution(ev.read_plan(self.plan), self.evidence)["rows"]["REB-UT-001"]["상태"], "Pass")

    def test_duplicate_json_keys_are_rejected(self):
        self.changes()
        raw = self.evidence.read_text(encoding="utf-8")
        self.evidence.write_text(raw.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'), encoding="utf-8")
        with self.assertRaisesRegex(ev.InputError, "중복 키"):
            ev.validate_execution(ev.read_plan(self.plan), self.evidence)

    def test_all_rows_blocked_before_url_discovery_can_be_recorded_without_targets(self):
        judged = {tid: ("미검증", "실행 차단 — PORT 미설정으로 기동 주소 확인 불가", "", "") for tid in JUDGED}
        changes = self.changes(judged=judged)
        evidence = self.load_evidence()
        evidence["targets"] = []
        self.save_evidence(evidence)
        changes["evidence_hash"] = hashlib.sha256(self.evidence.read_bytes()).hexdigest()
        summary = self.write_result(self.plan, self.result, self.ledger, changes)
        self.assertEqual(summary["counts"]["미검증"], len(JUDGED))
        self.assertEqual({r["결과"] for r in self.result_rows()[1].values()}, {"미검증"})
        evidence["rows"]["REB-UT-001"].update(execution="completed", channel="api")
        self.save_evidence(evidence)
        with self.assertRaisesRegex(ev.InputError, "targets"):
            ev.validate_execution(ev.read_plan(self.plan), self.evidence)

    def test_startup_log_hash_is_required_and_detects_changes_after_approval(self):
        changes = self.changes()
        evidence = self.load_evidence()
        baseline = copy.deepcopy(evidence)
        for digest in (None, "abc123", "0" * 64):
            evidence["targets"][0]["startup_sha256"] = digest
            self.save_evidence(evidence)
            with self.assertRaisesRegex(ev.InputError, "SHA256"):
                ev.validate_execution(ev.read_plan(self.plan), self.evidence)
        self.save_evidence(baseline)
        self.assertEqual(hashlib.sha256(self.evidence.read_bytes()).hexdigest(), changes["evidence_hash"])
        write(self.evidence.parent, "startup.log", "Unexpected other service is running\n")
        for dry_run in (True, False):
            with self.assertRaisesRegex(ev.InputError, "SHA256 가 다릅니다"):
                self.write_result(self.plan, self.result, self.ledger, changes, dry_run=dry_run)
        self.assertFalse(self.result.exists() or self.ledger.exists())

    def test_observed_nonfunctional_passes_stay_in_rate_denominator(self):
        judged = {"REB-UT-001": ("Pass", "비기능 — 응답시간 기준 충족", "2026.10.14", "김개발"),
                  "REB-UT-002": ("Pass", "비기능 — 메모리 기준 충족", "2026.10.14", "김개발"),
                  "REB-UT-003": ("미검증", "비기능 — 부하 환경 미준비", "", ""),
                  "REB-UT-004": ("미검증", "제외 — 승인된 범위 밖", "", ""),
                  "REB-UT-005": ("미검증", "기준값 미확정 — 응답시간 미정", "", "")}
        summary = self.write_result(self.plan, self.result, self.ledger, self.changes(judged=judged))
        self.assertEqual(summary["rate"], "100% (2/2)")
        self.assertEqual(ev.read_ledger(self.ledger)["history"][-1]["수행률"], "100% (2/2)")
        counts, rate = ev._rate(["Pass", "Fail", "미구현", "미검증"],
                                ["비기능 — 충족", "비기능 — 미충족", "제외 — 구현 부재", "비기능 — 미측정"])
        self.assertEqual((counts["Pass"], rate), (1, "33% (1/3)"))

    def test_raw_artifact_and_startup_log_cannot_be_overwritten_by_a_ledger(self):
        changes = self.changes()
        evidence = self.load_evidence()
        paths = [self.evidence.parent / evidence["rows"]["REB-UT-001"]["artifacts"][0]["path"],
                 self.evidence.parent / evidence["targets"][0]["startup_evidence"]]
        for artifact in paths:
            before = artifact.read_bytes()
            for dry_run in (True, False):
                with self.assertRaisesRegex(ev.InputError, "원본 증적 파일"):
                    self.write_result(self.plan, self.result, artifact, changes, dry_run=dry_run)
            self.assertEqual(artifact.read_bytes(), before)
        self.assertFalse(self.result.exists() or self.ledger.exists())

    def test_not_implemented_requires_observed_absence_and_blocked_requires_actual(self):
        judged = {**JUDGED, "REB-UT-003": ("미구현", "미구현 — 라우트와 구현 부재 확인", "", "")}
        changes = self.changes(judged=judged)
        self.write_result(self.plan, self.result, self.ledger, changes, dry_run=True)
        evidence = self.load_evidence()
        evidence["rows"]["REB-UT-003"]["artifacts"] = []
        self.save_evidence(evidence)
        with self.assertRaisesRegex(ev.InputError, "미구현"):
            ev.validate_execution(ev.read_plan(self.plan), self.evidence)
        self.changes()
        evidence = self.load_evidence()
        evidence["rows"]["REB-UT-003"]["actual"] = ""
        self.save_evidence(evidence)
        with self.assertRaisesRegex(ev.InputError, "actual"):
            ev.validate_execution(ev.read_plan(self.plan), self.evidence)

    def test_unknown_plan_values_cannot_pass_and_ordinary_literal_text_can(self):
        self.edit(self.plan, "| 회차 생성 |", "| [미확정] 회차 생성 |")
        changes = self.changes()
        self.assertEqual(ev.validate_execution(ev.read_plan(self.plan), self.evidence)["rows"]["REB-UT-001"]["상태"], "미검증")
        with self.assertRaises(ev.InputError):
            self.write_result(self.plan, self.result, self.ledger, changes)
        self.edit(self.plan, "| [미확정] 회차 생성 |", '| "확인 필요" 안내 |')
        changes = self.changes()
        self.write_result(self.plan, self.result, self.ledger, changes, dry_run=True)
        changes["rows"]["REB-UT-001"]["사유"] = "기준값 미확정 — 응답 미정"
        with self.assertRaisesRegex(ev.InputError, "기준값 미확정"):
            self.write_result(self.plan, self.result, self.ledger, changes)

    def test_execution_supplies_actual_date_operator_and_basis(self):
        changes = self.changes()
        for key in ("수행일", "담당자", "근거", "실제결과"):
            bad = copy.deepcopy(changes)
            bad["rows"]["REB-UT-001"][key] = "다른 값"
            with self.assertRaisesRegex(ev.InputError, "실행 증적과 다릅니다"):
                self.write_result(self.plan, self.result, self.ledger, bad)
        for row in changes["rows"].values():
            row.pop("수행일")
            row.pop("담당자")
        self.write_result(self.plan, self.result, self.ledger, changes)
        _, rows = self.result_rows()
        self.assertEqual((rows["REB-UT-001"]["수행일"], rows["REB-UT-001"]["테스트담당자"]), ("2026.10.14", "김개발"))
        self.assertEqual((rows["REB-UT-003"]["수행일"], rows["REB-UT-003"]["테스트담당자"]), ("", ""))
        ledger = ev.read_ledger(self.ledger)["rows"]["REB-UT-001"]
        self.assertIn("run_id=run-20261014-01", ledger["근거"])
        self.assertIn("raw/REB-UT-001.json", ledger["근거"])
        self.assertEqual(ledger["실제결과"], rows["REB-UT-001"]["실제결과"])

    def test_evidence_edits_after_approval_invalidate_dry_run_and_write(self):
        changes = self.changes()
        evidence = self.load_evidence()
        evidence["rows"]["REB-UT-001"]["actual"] = "승인 뒤 바뀐 관측"
        self.save_evidence(evidence)
        for dry_run in (True, False):
            with self.assertRaisesRegex(ev.InputError, "evidence_hash"):
                self.write_result(self.plan, self.result, self.ledger, changes, dry_run=dry_run)
        self.assertFalse(self.result.exists() or self.ledger.exists())

    def test_human_actual_result_is_preserved_and_current_observation_goes_to_ledger(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.result, "REB-UT-001 실측: Pass", "담당자가 현장에서 확인한 실제 결과")
        _, facts = self.facts()
        self.assertEqual(facts["REB-UT-001"]["written_by"], "human")
        self.write_result(self.plan, self.result, self.ledger, self.changes(keep=("REB-UT-001",), revision=None))
        _, rows = self.result_rows()
        self.assertEqual(rows["REB-UT-001"]["실제결과"], "담당자가 현장에서 확인한 실제 결과")
        self.assertEqual(ev.read_ledger(self.ledger)["rows"]["REB-UT-001"]["실제결과"], "REB-UT-001 실측: Pass")

    def test_changed_case_cannot_keep_a_human_pass_and_backup_preserves_old_value(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        self.edit(self.result, "REB-UT-001 실측: Pass", "담당자가 현장에서 확인한 실제 결과")
        old_result = self.result.read_bytes()
        self.edit(self.plan, "| 회차 생성 |", "| 회차 생성, 상태 등록완료 |")
        _, facts = self.facts()
        self.assertEqual(facts["REB-UT-001"]["written_by"], "human")
        self.assertTrue(facts["REB-UT-001"]["case_changed"])
        judged = {**JUDGED, "REB-UT-001": ("Fail", "실측 실패 — 생성 후 상태가 등록중", "2026.10.14", "김개발")}
        changes = self.changes(judged=judged, keep=("REB-UT-001",),
                               revision={**FIRST, "버전": "2.0", "개정 사유": "변경"})
        for dry_run in (True, False):
            with self.assertRaisesRegex(ev.InputError, "케이스가 바뀐 행"):
                self.write_result(self.plan, self.result, self.ledger, changes, dry_run=dry_run)
        self.assertEqual(self.result.read_bytes(), old_result)
        self.assertFalse((self.root / "backup").exists())
        changes["rows"]["REB-UT-001"]["keep"] = False
        summary = self.write_result(self.plan, self.result, self.ledger, changes)
        row = self.result_rows()[1]["REB-UT-001"]
        self.assertEqual((row["기대결과"], row["결과"]), ("회차 생성, 상태 등록완료", "Fail"))
        self.assertEqual((self.root / summary["backup"]).read_bytes(), old_result)

    def test_missing_both_outcome_criteria_is_unverified(self):
        self.edit(self.plan, "| 회차 생성 | TB_CYCL 1건 |", "| | |")
        changes = self.changes()
        evidence = self.load_evidence()
        row = evidence["rows"]["REB-UT-001"]
        # 빈 결과 칸에 true 를 넣어도, 사전조건·입력만 확인해도 판정 기준이 생기지는 않는다.
        for checks in (row["checks"], [c for c in row["checks"] if c["field"] in ("사전조건", "입력")]):
            row["checks"] = checks
            row["actual"] = "요청을 수행했으나 기대결과와 사후조건의 판정 기준이 없음"
            self.save_evidence(evidence)
            judged = ev.validate_execution(ev.read_plan(self.plan), self.evidence)
            self.assertEqual(judged["rows"]["REB-UT-001"]["상태"], "미검증")
        changes["rows"]["REB-UT-001"].update(상태="미검증", 사유="기준값 미확정 — 결과 판정 기준 없음", 수행일="", 담당자="")
        changes["evidence_hash"] = judged["evidence_hash"]
        self.write_result(self.plan, self.result, self.ledger, changes)
        self.assertEqual(self.result_rows()[1]["REB-UT-001"]["결과"], "미검증")

    def test_blank_precondition_or_input_still_needs_an_explicit_observation(self):
        self.edit(self.plan, "| 회차 없음 | 4종 파일 등록 |", "| | |")
        self.changes()
        baseline = self.load_evidence()
        judged = ev.validate_execution(ev.read_plan(self.plan), self.evidence)
        self.assertEqual(judged["rows"]["REB-UT-001"]["상태"], "Pass")
        for field in ("사전조건", "입력"):
            evidence = copy.deepcopy(baseline)
            row = evidence["rows"]["REB-UT-001"]
            row["checks"] = [c for c in row["checks"] if c["field"] != field]
            self.save_evidence(evidence)
            self.assertEqual(ev.validate_execution(ev.read_plan(self.plan), self.evidence)["rows"]["REB-UT-001"]["상태"], "미검증")

    def test_old_automatic_pass_and_pm_confirmation_cannot_be_inherited(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        for path in (self.result, self.ledger):
            self.edit(path, JUDGED["REB-UT-001"][1], "PM 확인 — 2026.10.14")
        _, facts = self.facts()
        self.assertEqual(facts["REB-UT-001"]["inherit"], "")
        self.assertEqual(facts["REB-UT-001"]["written_by"], "tool")
        judged = {**JUDGED, "REB-UT-001": ("미검증", "실행 차단 — DB 접속 불가", "", "")}
        changes = self.changes(judged=judged, keep=("REB-UT-001",), revision=None)
        with self.assertRaisesRegex(ev.InputError, "keep"):
            self.write_result(self.plan, self.result, self.ledger, changes)
        changes["rows"]["REB-UT-001"]["keep"] = False
        changes["revision"] = {**FIRST, "버전": "2.0", "개정 사유": "보완"}
        self.write_result(self.plan, self.result, self.ledger, changes)
        self.assertEqual(self.result_rows()[1]["REB-UT-001"]["결과"], "미검증")

    def test_legacy_documents_without_actual_column_remain_recognized_as_automatic(self):
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        for path in (self.result, self.ledger):
            lines, column = [], None
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.startswith("|"):
                    column = None
                else:
                    cells = ev._split_row(line)
                    if "실제결과" in cells:
                        column = cells.index("실제결과")
                    if column is not None:
                        cells.pop(column)
                        line = ev._join_row(cells)
                lines.append(line)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _, facts = self.facts()
        self.assertEqual({r["written_by"] for r in facts.values()}, {"tool"})
        summary = self.write_result(self.plan, self.result, self.ledger,
                                    self.changes(revision={**FIRST, "버전": "2.0", "개정 사유": "보완"}))
        self.assertEqual(summary["changed"], list(JUDGED))
        self.assertEqual(self.result_rows()[0][-1], "실제결과")

    def test_current_plan_produces_fourteen_columns_with_actual_last(self):
        doc = ev._load(self.plan)
        head = doc["head"][:3] + ["요구사항명"] + doc["head"][3:]
        table = [ev._join_row(head), "|" + "---|" * len(head)]
        for row in doc["recs"]:
            cells = [row["_raw"].get(h, "원천 데이터 등록") for h in head]
            table.append(ev._join_row(cells))
        lines = doc["lines"]
        lines[doc["head_line"]:doc["table_end"]] = table
        self.plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
        before = self.plan.read_bytes()
        self.write_result(self.plan, self.result, self.ledger, self.changes())
        head, _ = self.result_rows()
        self.assertEqual((len(head), head[-2:]), (14, ["사유", "실제결과"]))
        self.assertEqual(self.plan.read_bytes(), before)

    def test_plan_and_evidence_cannot_be_used_as_output_paths(self):
        changes = self.changes()
        before = self.plan.read_bytes()
        for result, ledger in ((self.plan, self.ledger), (self.result, self.plan), (self.evidence, self.ledger)):
            with self.assertRaises(ev.InputError):
                self.write_result(self.plan, result, ledger, changes)
        self.assertEqual(self.plan.read_bytes(), before)

    def test_old_index_cli_and_write_without_evidence_are_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                ev.main(["index", "--source", str(self.root)])
            self.assertEqual(error.exception.code, 2)
            with self.assertRaises(SystemExit) as error:
                ev.main(["write", "--de13", str(self.plan), "--result", str(self.result), "--ledger", str(self.ledger), "--changes", "changes.json"])
            self.assertEqual(error.exception.code, 2)

    def test_real_loopback_http_error_is_a_pass_and_wrong_postcondition_is_a_fail(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(handler):
                body = handler.rfile.read(int(handler.headers.get("Content-Length", "0")))
                if json.loads(body)["size"] > 1000:
                    handler.send_response(400)
                    response = {"message": "파일 용량 초과", "saved": 0}
                else:
                    handler.send_response(201)
                    response = {"message": "정상 등록", "saved": 0}  # DB 저장 결함을 재현한다.
                handler.send_header("Content-Type", "application/json; charset=utf-8")
                handler.end_headers()
                handler.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))

            def log_message(handler, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            judged = {**JUDGED, "REB-UT-003": ("Fail", "실측 실패 — 정상 응답 뒤 저장 0건", "2026.10.14", "김개발")}
            changes = self.changes(judged=judged)
            evidence = self.load_evidence()
            url = f"http://127.0.0.1:{server.server_port}"
            evidence["targets"][0]["base_url"] = url
            startup = write(self.evidence.parent, "startup.log", f"Local app ready at {url}\n")
            evidence["targets"][0]["startup_sha256"] = hashlib.sha256(startup.read_bytes()).hexdigest()
            for tid, size in (("REB-UT-002", 1001), ("REB-UT-003", 1000)):
                request_body = json.dumps({"size": size}).encode("utf-8")
                request = Request(url + "/files", data=request_body, headers={"Content-Type": "application/json"})
                try:
                    response = urlopen(request, timeout=5)
                except HTTPError as response_error:
                    response = response_error
                with response:
                    status, body = response.status, response.read().decode("utf-8")
                raw = write(self.evidence.parent, f"raw/{tid}.http", f"POST {url}/files\n{request_body.decode()}\nHTTP {status}\n{body}")
                rel = raw.relative_to(self.evidence.parent).as_posix()
                row = evidence["rows"][tid]
                row["actual"] = f"HTTP {status}; {body}"
                row["artifacts"] = [{"path": rel, "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}]
                for check in row["checks"]:
                    check["artifact"] = rel
                    check["observed"] = row["actual"]
                    check["matched"] = not (tid == "REB-UT-003" and check["field"] == "사후조건")
            self.save_evidence(evidence)
            changes["evidence_hash"] = hashlib.sha256(self.evidence.read_bytes()).hexdigest()
            before = self.plan.read_bytes()
            self.write_result(self.plan, self.result, self.ledger, changes)
            _, rows = self.result_rows()
            self.assertEqual(rows["REB-UT-002"]["결과"], "Pass")
            self.assertIn("HTTP 400", rows["REB-UT-002"]["실제결과"])
            self.assertEqual(rows["REB-UT-003"]["결과"], "Fail")
            self.assertIn('"saved": 0', rows["REB-UT-003"]["실제결과"])
            self.assertEqual(self.plan.read_bytes(), before)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
