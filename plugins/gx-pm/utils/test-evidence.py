#!/usr/bin/env python3
"""로컬 프로젝트 실측 증적 검증·단위테스트결과 기록 — Python 3.10 표준 라이브러리.

에이전트가 실행한 API·브라우저 관측을 계획서 원문과 대조한다. 이 도구는 앱을
실행하지 않으며 원본 증적 파일·해시·행 범위·관측 완전성을 검증한 뒤 기록한다.

  plan  : DE-13 행, 〃 해소, 지문, 기존 결과서와 수행대장의 변경을 읽는다.
  write : --evidence 실행 증적을 검증하고 승인된 결과서·수행대장을 함께 쓴다.
          --dry-run 은 파일을 쓰지 않고 변경량과 필요한 개정을 알린다.

예시:
  python test-evidence.py plan --de13 계획서.md --result 결과서.md --ledger 증적/수행대장.md --out plan.json
  python test-evidence.py write --de13 계획서.md --result 결과서.md --ledger 증적/수행대장.md --changes changes.json --evidence 증적/run.json [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit

DITTO = "〃"
CASE_FIELDS = ("사전조건", "입력", "기대결과", "사후조건")


class InputError(Exception):
    """입력 경로·형식 오류 (종료 코드 2)."""


# ---------- plan ----------

def _split_row(line: str) -> list[str]:
    s = line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    cells, cur, i = [], [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if s[i] == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(s[i])
        i += 1
    cells.append("".join(cur).strip())
    return [c.replace("<br>", "\n") for c in cells]


def _cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def _join_row(cells: list[str]) -> str:
    # 빈 칸은 `| |` — 원문 표기와 같게 써야 바꾼 칸 말고는 diff 가 생기지 않는다
    return "|" + "|".join(f" {_cell(c)} " if _cell(c) else " " for c in cells) + "|"


def _table(lines: list[str]) -> tuple[list[str], list[tuple[int, list[str], bool]], int]:
    """테스트ID·연계기능ID 머리글이 있는 첫 표의 (열 이름, [(줄 번호, 셀, 칸 수가 머리글과 다른가)], 머리글 줄 번호)."""
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        head = _split_row(line)
        if "테스트ID" in head and "연계기능ID" in head:
            rows = []
            for j in range(i + 1, len(lines)):
                if not lines[j].lstrip().startswith("|"):
                    break
                cells = _split_row(lines[j])
                if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
                    continue
                rows.append((j, (cells + [""] * len(head))[:len(head)], len(cells) != len(head)))
            return head, rows, i
    raise InputError("DE-13 본문 표(테스트ID·연계기능ID 머리글)를 찾을 수 없습니다")


def _resolve(head: list[str], rows: list[tuple[int, list[str], bool]]) -> list[dict]:
    out, prev = [], None
    for line_no, cells, malformed in rows:
        rec = dict(zip(head, cells))
        raw = dict(rec)
        for h in head:
            if rec[h] == DITTO and prev and prev.get("연계기능ID") == rec.get("연계기능ID"):
                rec[h] = prev[h]
        # 이스케이프 안 된 | 등으로 칸이 밀린 행 — 읽은 값을 믿을 수 없고, 고쳐 쓰면 다른 칸을 지운다
        rec["_line"], rec["_raw"], rec["_malformed"] = line_no, raw, malformed
        out.append(rec)
        prev = rec
    return out


def fingerprint(rec: dict) -> str:
    parts = [re.sub(r"\s+", " ", rec.get(f, "") or "").strip() for f in CASE_FIELDS]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:8]


def _next_id(ids: list[str], texts: list[str]) -> str:
    """다음 테스트ID. 지운 번호는 다시 쓰지 않으므로 개정이력·backup 에 남은 번호(`~` 범위 끝 포함)도 센다."""
    found: dict[str, list[str]] = {}
    for tid in ids:
        m = re.match(r"^(.*?)(\d+)$", tid)
        if m:
            found.setdefault(m.group(1), []).append(m.group(2))
    if not found:
        return ""
    prefix = max(found, key=lambda k: len(found[k]))
    nums = [int(n) for n in found[prefix]]
    used = re.compile(re.escape(prefix) + r"(\d+)(?:\s*~\s*(\d+))?")
    for text in texts:
        nums += [int(g) for m in used.finditer(text) for g in m.groups() if g]
    return f"{prefix}{str(max(nums) + 1).zfill(max(len(n) for n in found[prefix]))}"


def _last_version(lines: list[str]) -> str:
    version = ""
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        head = _split_row(line)
        if head[:2] == ["버전", "개정일"]:
            for nxt in lines[i + 1:]:
                if not nxt.lstrip().startswith("|"):
                    break
                cells = _split_row(nxt)
                if cells and cells[0] and not re.fullmatch(r":?-{3,}:?", cells[0]):
                    version = cells[0]
            break
    return version


def _load(md: Path) -> dict:
    """표가 있는 산출물 md 를 읽는다. 줄바꿈 변환 없이 읽어야 원래 줄바꿈을 지킬 수 있다."""
    with Path(md).open(encoding="utf-8", newline="") as fh:
        text = fh.read()
    lines = text.splitlines()
    head, rows, head_line = _table(lines)
    end = head_line + 1
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    return {"text": text, "lines": lines, "head": head, "head_line": head_line, "table_end": end,
            "recs": _resolve(head, rows), "newline": "\r\n" if "\r\n" in text else "\n"}


def _hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def _basis_version(lines: list[str]) -> str:
    for line in lines:
        m = re.match(r"^>\s*근거:.*?DE-13\s*v(\d+(?:\.\d+)?)", line)
        if m:
            return m.group(1)
    return ""


def _revisions(lines: list[str]) -> list[tuple[str, str]]:
    """개정이력 표의 (버전, 개정 내용)."""
    out = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and _split_row(line)[:2] == ["버전", "개정일"]:
            head = _split_row(line)
            for nxt in lines[i + 1:]:
                if not nxt.lstrip().startswith("|"):
                    break
                cells = dict(zip(head, _split_row(nxt)))
                if cells.get("버전") and not re.fullmatch(r":?-{3,}:?", cells["버전"]):
                    out.append((cells["버전"], cells.get("개정 내용", "")))
            break
    return out


def _mentions(tid: str, text: str) -> bool:
    """개정 내용이 이 테스트ID 를 가리키나 — `REB-UT-001~003` 같은 범위도 센다."""
    if tid in text:
        return True
    m = re.match(r"^(.*?)(\d+)$", tid)
    if not m:
        return False
    prefix, num = m.group(1), int(m.group(2))
    return any(int(a) <= num <= int(b) for a, b in re.findall(re.escape(prefix) + r"(\d+)\s*~\s*(?:" + re.escape(prefix) + r")?(\d+)", text))


def read_plan(md: Path, result: Path | None = None, ledger: Path | None = None) -> dict:
    """DE-13 계획서 행을 읽는다 — 읽기만 한다. 결과서를 주면 행마다 지금 결과서의 수행 칸을, 수행대장을
    주면 지난 판정과 견준 사실(누가 썼나·케이스 변경·승계)을 붙인다."""
    md = Path(md)
    if not md.is_file():
        raise InputError(f"DE-13 파일이 없습니다: {md}")
    doc = _load(md)
    out_rows = []
    for r in doc["recs"]:
        row = {h: r[h] for h in doc["head"]}
        row["fingerprint"] = fingerprint(r)
        row["malformed"] = r["_malformed"]
        out_rows.append(row)
    backup = md.parent / "backup"
    older = [p.read_text(encoding="utf-8", errors="replace") for p in sorted(backup.iterdir())
             if p.suffix == ".md" and p.name.startswith(md.stem)] if backup.is_dir() else []
    ids = [r["테스트ID"] for r in doc["recs"]]
    data = {"columns": doc["head"], "rows": out_rows, "last_version": _last_version(doc["lines"]),
            "next_id": _next_id(ids, [doc["text"], *older]),
            "malformed": [r["테스트ID"] for r in doc["recs"] if r["_malformed"]],
            "duplicates": sorted({t for t in ids if ids.count(t) > 1}), "plan_hash": _hash(md),
            "revisions": _revisions(doc["lines"])}
    if result is not None:
        _attach_result(data, Path(result))
    if ledger is not None:
        _compare(data, Path(ledger))
    return data


# ---------- 결과서·수행대장 ----------

RESULTS = ("Pass", "Fail", "미구현", "미검증")  # 결과 칸이 받는 값 (templates/IM-03-unit-test-result.md §결과 상태)
STATES = RESULTS
RESULT_COLS = ("테스트담당자", "수행일", "결과", "사유", "실제결과")  # 결과서에서 수행이 채우는 칸 — 나머지는 계획서 원문
REVISION_HEAD = ["버전", "개정일", "개정 사유", "개정 내용", "작성자", "승인자"]
REVISION_REASONS = ("신규", "추가", "변경", "삭제", "보완")  # templates/revision-history.md
HUMAN_NO_REASON = "기존 기입 — 사유 미기재"
CONTROL = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")  # 줄바꿈 말고는 표 칸에 들어갈 수 없다
LEDGER_COLS = ["테스트ID", "상태", "사유", "근거", "수행일", "담당자", "행 지문", "비고", "실제결과"]
HISTORY_COLS = ["반영일", "계획서 버전", "결과서 버전", "Pass", "Fail", "미구현", "미검증", "수행률",
                "신규 후보", "보강 후보", "소스 기준"]
NOT_UNIT = ("비기능", "기준값 미확정", "제외")  # 수행률 분모에서 빼는 사유 첫머리 — 단위 시험으로 판정하지 않는 행
INHERITED = ("제외",)  # 다음 반영에 넘겨받는 사람의 판단


def _required_text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or CONTROL.search(value):
        raise InputError(f"{label}: 비어 있지 않은 문자열이어야 하며 제어 문자를 포함할 수 없습니다")
    return value


def _evidence_file(root: Path, value, label: str) -> Path:
    rel = _required_text(value, label)
    # Windows 드라이브·UNC 경로도 다른 운영체제에서 동일하게 거부한다.
    portable = PureWindowsPath(rel)
    path = Path(rel)
    if path.is_absolute() or portable.drive or portable.root or ".." in portable.parts or ":" in rel:
        raise InputError(f"{label}: 증적 JSON 폴더 안의 상대경로여야 합니다")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.stat().st_size == 0:
        raise InputError(f"{label}: 증적 폴더 안의 비어 있지 않은 파일이 필요합니다: {rel}")
    return resolved


def _verified_file(root: Path, rel, digest, label: str) -> Path:
    file = _evidence_file(root, rel, label)
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise InputError(f"{label}: 전체 SHA256 이 필요합니다")
    if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
        raise InputError(f"{label}: 증적 파일 SHA256 가 다릅니다: {rel}")
    return file


def _execution_time(value, label: str) -> datetime:
    text = _required_text(value, label)
    try:
        at = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"{label}: 시간대가 포함된 ISO 시각이 필요합니다") from exc
    if at.tzinfo is None or at.utcoffset() is None or "T" not in text:
        raise InputError(f"{label}: 시간대가 포함된 ISO 시각이 필요합니다")
    return at


def _execution_object(pairs: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise InputError(f"실행 증적 JSON 에 중복 키가 있습니다: {key}")
        out[key] = value
    return out


def validate_execution(plan: dict, evidence_path: Path) -> dict:
    """실측 증적을 검증하고 행별 판정을 도출한다. 관측 의미의 진위는 실행 에이전트가 책임진다."""
    evidence_path = Path(evidence_path).resolve()
    try:
        raw = evidence_path.read_bytes()
        evidence = json.loads(raw.decode("utf-8"), object_pairs_hook=_execution_object)
    except (OSError, ValueError) as exc:
        raise InputError(f"실행 증적 JSON 을 읽을 수 없습니다: {exc}") from exc
    if not isinstance(evidence, dict) or type(evidence.get("schema_version")) is not int or evidence["schema_version"] != 1:
        raise InputError("실행 증적 schema_version 은 1이어야 합니다")
    if plan["malformed"] or plan["duplicates"]:
        raise InputError("계획서의 깨진 행·중복 ID 를 먼저 수정해야 합니다")
    if evidence.get("plan_hash") != plan["plan_hash"]:
        raise InputError("실행 증적과 현재 계획서의 plan_hash 가 다릅니다 — 다시 실행하세요")
    run_id = _required_text(evidence.get("run_id"), "run_id")
    operator = _required_text(evidence.get("operator"), "operator")
    started = _execution_time(evidence.get("started_at"), "started_at")
    finished = _execution_time(evidence.get("finished_at"), "finished_at")
    if started > finished:
        raise InputError("실행 종료 시각이 시작 시각보다 빠릅니다")
    sources, targets = evidence.get("sources"), evidence.get("targets")
    if not isinstance(sources, list) or not sources:
        raise InputError("실행 증적 sources 가 비었습니다")
    for source in sources:
        if not isinstance(source, dict) or type(source.get("dirty")) is not bool:
            raise InputError("각 source 에 path·revision·dirty(bool)가 필요합니다")
        _required_text(source.get("path"), "source.path")
        _required_text(source.get("revision"), "source.revision")
    rows = evidence.get("rows")
    ids = {row["테스트ID"] for row in plan["rows"]}
    if not isinstance(rows, dict) or set(rows) != ids:
        raise InputError("실행 증적 rows 는 현재 계획서의 전체 테스트ID 와 정확히 일치해야 합니다")
    all_blocked = all(isinstance(row, dict) and row.get("execution") == "blocked" and row.get("channel") == "none"
                      for row in rows.values())
    if not isinstance(targets, list) or (not targets and not all_blocked):
        raise InputError("모든 행이 blocked/none 인 경우에만 targets 를 비울 수 있습니다")
    root = evidence_path.parent
    evidence_files = set()
    for target in targets:
        if not isinstance(target, dict):
            raise InputError("각 target 은 base_url·startup_evidence·startup_sha256 객체여야 합니다")
        url = _required_text(target.get("base_url"), "target.base_url")
        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname or ""
            local = hostname.lower() == "localhost" or ipaddress.ip_address(hostname).is_loopback
            port = parsed.port
        except ValueError:
            local, port = False, None
        if (not local or parsed.scheme not in ("http", "https") or parsed.username or parsed.password
                or parsed.query or parsed.fragment or port == 0):
            raise InputError(f"target.base_url 은 로컬 loopback HTTP(S) 주소여야 합니다: {url}")
        evidence_files.add(_verified_file(root, target.get("startup_evidence"), target.get("startup_sha256"), "target.startup_evidence"))
    judgments = {}
    for planned in plan["rows"]:
        tid = planned["테스트ID"]
        row = rows[tid]
        if not isinstance(row, dict) or row.get("fingerprint") != planned["fingerprint"]:
            raise InputError(f"{tid}: 실행 증적 행 지문이 현재 계획서와 다릅니다")
        execution, channel = row.get("execution"), row.get("channel")
        if execution not in ("completed", "blocked", "not_implemented") or channel not in ("api", "browser", "mixed", "none"):
            raise InputError(f"{tid}: execution 또는 channel 값이 올바르지 않습니다")
        actual = _required_text(row.get("actual"), f"{tid}.actual")
        artifacts = row.get("artifacts")
        if not isinstance(artifacts, list):
            raise InputError(f"{tid}: artifacts 는 배열이어야 합니다")
        paths = set()
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise InputError(f"{tid}: artifact 는 path·sha256 객체여야 합니다")
            rel = artifact.get("path")
            evidence_files.add(_verified_file(root, rel, artifact.get("sha256"), f"{tid}.artifact"))
            if rel in paths:
                raise InputError(f"{tid}: 중복 증적 파일입니다: {rel}")
            paths.add(rel)
        if execution == "not_implemented" and not paths:
            raise InputError(f"{tid}: 미구현 판정에는 실제 확인 근거 파일이 필요합니다")
        checks = row.get("checks")
        if not isinstance(checks, list):
            raise InputError(f"{tid}: checks 는 배열이어야 합니다")
        checked = {}
        for check in checks:
            if not isinstance(check, dict):
                raise InputError(f"{tid}: check 는 객체여야 합니다")
            field = check.get("field")
            if not isinstance(field, str) or field not in CASE_FIELDS or field in checked:
                raise InputError(f"{tid}: 알 수 없거나 중복된 check.field 입니다: {field}")
            if check.get("expected") != planned.get(field, ""):
                raise InputError(f"{tid}: {field} expected 는 〃 해소한 계획서 원문과 같아야 합니다")
            _required_text(check.get("observed"), f"{tid}.{field}.observed")
            if "matched" not in check or (check["matched"] is not None and type(check["matched"]) is not bool):
                raise InputError(f"{tid}: matched 는 true·false·null 중 하나여야 합니다")
            if not isinstance(check.get("artifact"), str) or check["artifact"] not in paths:
                raise InputError(f"{tid}: check.artifact 는 해당 행의 artifacts 파일이어야 합니다")
            checked[field] = check["matched"]
        unresolved = any("[미확정]" in planned.get(f, "") for f in CASE_FIELDS)
        outcome_fields = [f for f in ("기대결과", "사후조건") if planned.get(f, "").strip()]
        valid = (execution == "completed" and channel != "none" and bool(paths) and not unresolved
                 and bool(outcome_fields) and all(checked.get(f) is True for f in ("사전조건", "입력")))
        state = "미검증"
        if execution == "not_implemented":
            state = "미구현"
        elif valid and any(checked.get(f) is False for f in outcome_fields):
            state = "Fail"
        elif valid and all(checked.get(f) is True for f in CASE_FIELDS if planned.get(f, "").strip()):
            state = "Pass"
        judgments[tid] = {"상태": state, "실제결과": actual,
                          "수행일": finished.strftime("%Y.%m.%d") if state in ("Pass", "Fail") else "",
                          "담당자": operator if state in ("Pass", "Fail") else "",
                          "근거": f"{evidence_path.as_posix()} · run_id={run_id} · " + ", ".join(sorted(paths))}
    return {"rows": judgments, "run_id": run_id, "evidence_hash": hashlib.sha256(raw).hexdigest(),
            "evidence_files": sorted(str(path) for path in evidence_files)}


def _attach_result(data: dict, path: Path) -> None:
    info = {"path": path.as_posix(), "exists": path.is_file(), "hash": "", "last_version": "", "basis_version": "",
            "malformed": [], "only": [], "xlsx_newer": False}
    current: dict[str, dict] = {}
    if info["exists"]:
        doc = _load(path)
        info.update(hash=_hash(path), last_version=_last_version(doc["lines"]), basis_version=_basis_version(doc["lines"]))
        for r in doc["recs"]:
            if r["_malformed"]:
                info["malformed"].append(r["테스트ID"])
            else:
                current[r["테스트ID"]] = r
        plan_ids = {row["테스트ID"] for row in data["rows"]}
        info["only"] = [t for t in current if t not in plan_ids]
        # md 가 원본이다 — xlsx 를 직접 고친 내용은 다음 추출 때 사라진다
        md_time = path.stat().st_mtime
        info["xlsx_newer"] = any(x.is_file() and x.stat().st_mtime > md_time + 2
                                 for x in (path.parent / "xlsx" / f"{path.stem}.xlsx", path.with_suffix(".xlsx")))
    cases = [h for h in data["columns"] if h not in RESULT_COLS and h != "테스트ID"]
    for row in data["rows"]:
        got = current.get(row["테스트ID"])
        row["in_result"] = got is not None
        # 결과서의 케이스 칸은 다음 쓰기에서 계획서 원문으로 돌아간다 — 바꾸려면 계획서를 고쳐야 한다
        row["result_case_edited"] = [h for h in cases if got is not None and h in got and got[h] != row.get(h, "")]
        row["result_fingerprint"] = fingerprint(got) if got is not None else ""
        source = got if got is not None else row
        for c in RESULT_COLS:
            row[c] = source.get(c, "")
    data["result"] = info


def read_ledger(path: Path) -> dict:
    """수행대장을 읽는다. 파일이 없으면 빈 대장이다 — 첫 반영."""
    path = Path(path)
    out = {"path": path.as_posix(), "exists": path.is_file(), "project": "", "mapping": {}, "rows": {},
           "history": [], "history_head": [], "history_lines": []}
    if not out["exists"]:
        return out
    section, head = "", None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# ") and "수행대장" in line:
            out["project"] = re.sub(r"^#\s*단위테스트 수행대장\s*[—–-]?\s*", "", line).strip()
        if line.startswith("## "):
            section, head = line[3:].strip(), None
            continue
        if section == "반영 이력" and (line.strip() or out["history_lines"]):
            out["history_lines"].append(line)  # 지난 이력은 고치지 않고 그대로 옮긴다
        if not line.lstrip().startswith("|"):
            head = None
            continue
        cells = _split_row(line)
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            continue
        if head is None:
            head = cells
            if section == "반영 이력":
                out["history_head"] = cells
            continue
        rec = dict(zip(head, cells + [""] * len(head)))
        if section == "담당자 매핑" and rec.get("작성자"):
            out["mapping"][rec["작성자"]] = rec.get("실명", "")
        elif section == "수행 현황" and rec.get("테스트ID"):
            out["rows"][rec["테스트ID"]] = rec
        elif section == "반영 이력":
            out["history"].append(rec)
    return out


def _written_by(row: dict, prev: dict | None) -> str:
    """수행 칸이 지난 수행대장과 같을 때만 자동 기록이다. 옛 문서의 실제결과는 빈 값이다."""
    mine = tuple(row.get(c, "") for c in ("결과", "사유", "수행일", "테스트담당자", "실제결과"))
    if not any(mine):
        return "empty"
    if prev and mine == (prev.get("상태", ""), prev.get("사유", ""), prev.get("수행일", ""), prev.get("담당자", ""), prev.get("실제결과", "")):
        return "tool"
    return "human"


def _compare(data: dict, ledger: Path) -> None:
    led = read_ledger(ledger)
    ids = set()
    for row in data["rows"]:
        ids.add(row["테스트ID"])
        prev = led["rows"].get(row["테스트ID"])
        row["prev"] = {k: v for k, v in prev.items() if k != "테스트ID"} if prev else None
        row["written_by"] = _written_by(row, prev)
        row["case_changed"] = bool(prev and prev.get("행 지문") and prev["행 지문"] != row["fingerprint"])
        first = re.split(r"\s[—–-]\s", (prev or {}).get("사유", ""), maxsplit=1)[0].strip()
        row["inherit"] = first if first in INHERITED and not row["case_changed"] else ""
        # 결과서의 케이스 칸이 지난 쓰기 때와 같으면 계획서와 다른 것은 계획서가 바뀐 탓이다 — 결과서 손 수정이 아니다
        if prev and prev.get("행 지문") and row.get("result_fingerprint") == prev["행 지문"]:
            row["result_case_edited"] = []
    data["ledger"] = {k: led[k] for k in ("path", "exists", "project", "mapping", "history")}
    data["ledger"]["ledger_only"] = [t for t in led["rows"] if t not in ids]
    # 결과서가 수행대장의 마지막 기록보다 앞서 있다 — 손으로 고쳤거나 지난 반영이 끝까지 가지 못했다
    last = (led["history"][-1].get("결과서 버전", "") if led["history"] else "")
    res = data.get("result") or {}
    data["ledger"]["stale"] = bool(last and res.get("exists") and res.get("last_version")
                                   and last != res["last_version"])
    # 지난 반영 뒤 고친 케이스인데 그 뒤의 계획서 개정이력 어디에도 그 ID 가 없다 — PM 이 손으로 고쳤다
    base = led["history"][-1].get("계획서 버전", "") if led["history"] else ""
    newer = [text for ver, text in data.get("revisions", []) if _version(ver) > _version(base)] if base else []
    data["ledger"]["unrecorded"] = [row["테스트ID"] for row in data["rows"]
                                    if row["case_changed"] and not any(_mentions(row["테스트ID"], t) for t in newer)] if base else []


def _version(text: str) -> float:
    try:
        return float(text)
    except ValueError:
        return 0.0


def _rate(states: list[str], reasons: list[str]) -> tuple[dict, str]:
    counts = {s: states.count(s) for s in STATES}
    denom = len(states) - sum(1 for state, why in zip(states, reasons) if state == "미검증" and why.startswith(NOT_UNIT))
    rate = f"{int(100 * counts['Pass'] / denom + 0.5)}% ({counts['Pass']}/{denom})" if denom else "-"
    return counts, rate


def _doc_name(lines: list[str]) -> str:
    title = next((l for l in lines if l.startswith("# ")), "")
    return title.split(" — ", 1)[1].strip() if " — " in title else ""


def _result_heading(lines: list[str], head_line: int) -> str:
    heading = next((lines[i] for i in range(head_line - 1, -1, -1) if lines[i].startswith("## ")), "")
    return heading.replace("단위테스트계획", "단위테스트결과") if "단위테스트계획" in heading else "## 단위테스트결과"


def _set_basis(lines: list[str], basis: str) -> None:
    for i, line in enumerate(lines):
        if re.match(r"^>\s*근거:", line):
            lines[i] = basis
            return
    at = next((i + 1 for i, l in enumerate(lines) if l.startswith("> 생성:")), None)
    if at is None:
        at = next((i + 1 for i, l in enumerate(lines) if l.startswith("# ")), 0)
        lines[at:at] = ["", basis]
        return
    lines.insert(at, basis)


def _append_revision(lines: list[str], row: str) -> None:
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and _split_row(line)[:2] == REVISION_HEAD[:2]:
            j = i + 1
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            lines.insert(j, row)
            return
    at = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
    lines[at:at] = ["## 개정이력", "", _join_row(REVISION_HEAD), "|------|--------|----------|----------|--------|--------|", row, ""]


def _ledger_text(led: dict, project: str, changes: dict, rows: list[list[str]], counts: dict, rate: str,
                 plan_ver: str, res_ver: str) -> str:
    mapping = dict(led["mapping"])
    for author, name in (changes.get("mapping") or {}).items():
        mapping.setdefault(author, name)  # 쌓기만 한다 — 지난 매핑은 고치지 않는다
    candidates = changes.get("candidates") or {}
    entry = _join_row([changes["date"], plan_ver, res_ver, *(str(counts[s]) for s in STATES), rate,
                       str(candidates.get("new", 0)), str(candidates.get("boost", 0)), changes.get("basis", "")])
    history = list(led["history_lines"])
    while history and not history[-1].strip():
        history.pop()
    if not history or led["history_head"] != HISTORY_COLS:  # 열이 바뀐 옛 이력은 그대로 두고 새 표를 연다
        history += ([""] if history else []) + [_join_row(HISTORY_COLS), "|" + "---|" * len(HISTORY_COLS)]
    history.append(entry)
    header = f"> 근거: DE-13 v{plan_ver} · 결과서 v{res_ver} · 소스 {changes.get('sources', '')} · 반영 {changes['date']}"
    if changes.get("note"):
        header += f" · {changes['note']}"
    lines = [f"# 단위테스트 수행대장 — {project}", "", header, "", "## 담당자 매핑", "",
             _join_row(["작성자", "실명"]), "|--------|------|", *(_join_row([a, n]) for a, n in mapping.items()),
             "", "## 수행 현황", "", _join_row(LEDGER_COLS), "|" + "---|" * len(LEDGER_COLS),
             *(_join_row(r) for r in rows), "", "## 반영 이력", "", *history]
    return "\n".join(lines) + "\n"


def write_result(plan_md: Path, result_md: Path, ledger_md: Path, changes: dict, evidence_path: Path, dry_run: bool = False) -> dict:
    """승인된 판정으로 단위테스트결과서와 수행대장을 함께 쓴다. 계획서는 읽기만 한다.

    결과서 행은 매번 지금 계획서에 맞춘다 — 케이스 칸은 계획서 원문을 옮기고, 수행 칸만 판정으로 채운다.
    둘을 한 번에 쓰는 까닭: 결과서만 바뀌고 수행대장이 따라오지 못하면 다음 반영 때 이 도구가 쓴 값을
    사람 값으로 잘못 가린다. 검증에 하나라도 걸리면 아무 파일도 건드리지 않는다."""
    plan_md, result_md, ledger_md = Path(plan_md), Path(result_md), Path(ledger_md)
    if len({p.resolve() for p in (plan_md, result_md, ledger_md)}) != 3:
        raise InputError("계획서·결과서·수행대장은 서로 다른 경로여야 합니다")
    if Path(evidence_path).resolve() in {result_md.resolve(), ledger_md.resolve()}:
        raise InputError("실행 증적 경로를 결과서·수행대장으로 덮어쓸 수 없습니다")
    facts = read_plan(plan_md, result=result_md, ledger=ledger_md)
    execution = validate_execution(facts, evidence_path)
    if {str(result_md.resolve()), str(ledger_md.resolve())} & set(execution["evidence_files"]):
        raise InputError("원본 증적 파일을 결과서·수행대장으로 덮어쓸 수 없습니다")
    plan_doc = _load(plan_md)
    res = facts["result"]
    res_doc = _load(result_md) if res["exists"] else None
    led = read_ledger(ledger_md)
    changes = {**changes, "rows": {k: dict(v) if isinstance(v, dict) else v for k, v in (changes.get("rows") or {}).items()}}
    rows = changes["rows"]
    ids = [r["테스트ID"] for r in facts["rows"]]
    date = str(changes.get("date", ""))
    # 결과서 제목과 같은 사업명 — 수행대장이 이미 있으면 그 제목을 지킨다
    project = led["project"] or changes.get("project") or _doc_name(plan_doc["lines"])
    errors = []
    texts = [changes.get(k, "") for k in ("date", "project", "sources", "note", "basis")]
    texts += [v for row in rows.values() if isinstance(row, dict) for v in row.values() if isinstance(v, str)]
    texts += [v for kv in (changes.get("mapping") or {}).items() for v in kv]
    texts += [v for v in (changes.get("revision") or {}).values() if isinstance(v, str)]
    if any(isinstance(v, str) and CONTROL.search(v) for v in texts):
        errors.append("값에 제어 문자가 있습니다 — 역슬래시 경로가 이스케이프로 풀렸는지 확인하세요 (JSON 은 \\\\ 로 적는다)")
    if changes.get("plan_hash") != facts["plan_hash"]:
        errors.append("승인 뒤 계획서가 바뀌었습니다 — 다시 대조하세요")
    if changes.get("evidence_hash") != execution["evidence_hash"]:
        errors.append("승인 뒤 실행 증적이 바뀌었거나 evidence_hash 가 없습니다 — 다시 검토하세요")
    if (changes.get("result_hash") or "") != res["hash"]:
        errors.append("승인 뒤 결과서가 바뀌었습니다 — 다시 대조하세요")
    if facts["malformed"]:
        errors.append("계획서에 칸 수가 머리글과 다른 행이 있습니다 — 계획서를 먼저 고치세요: " + ", ".join(facts["malformed"]))
    if facts["duplicates"]:
        errors.append("계획서에 같은 테스트ID 가 두 번 이상 있습니다 — 계획서를 먼저 고치세요: " + ", ".join(facts["duplicates"]))
    if res["malformed"]:
        errors.append("결과서에 칸 수가 머리글과 다른 행이 있습니다 — 결과서 md 를 먼저 고치세요: " + ", ".join(res["malformed"]))
    if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", date):
        errors.append(f"반영일은 YYYY.MM.DD 여야 합니다: '{date}'")
    if not project:
        errors.append("사업명이 없습니다 (changes.json 의 project)")
    missing, extra = [t for t in ids if t not in rows], [t for t in rows if t not in ids]
    if missing:
        more = f" 외 {len(missing) - 10}건" if len(missing) > 10 else ""
        errors.append("판정이 빠진 행: " + ", ".join(missing[:10]) + more)
    if extra:
        errors.append("계획서에 없는 행: " + ", ".join(extra[:10]))
    for tid in dict.fromkeys(ids):
        got = rows.get(tid)
        if not isinstance(got, dict):
            errors.append(f"{tid}: 판정은 객체여야 합니다")
            continue
        if not all(isinstance(v, str) for k, v in got.items() if k != "keep") or not isinstance(got.get("keep", False), bool):
            errors.append(f"{tid}: 값의 형식이 맞지 않습니다")
            continue
        if got.get("상태") not in STATES:
            errors.append(f"{tid}: 상태는 {'/'.join(STATES)} 중 하나여야 합니다: '{got.get('상태', '')}'")
        if not got.get("사유", "").strip():
            errors.append(f"{tid}: 사유가 비었습니다")
        current = next(r for r in facts["rows"] if r["테스트ID"] == tid)
        if got.get("keep") and current["case_changed"]:
            errors.append(f"{tid}: 케이스가 바뀐 행은 keep 으로 과거 결과를 유지할 수 없습니다 — 새 증적을 반영하세요")
        if got.get("keep") and current["written_by"] != "human":
            errors.append(f"{tid}: keep 은 사람이 직접 기입한 값에만 사용할 수 있습니다")
        measured = execution["rows"][tid]
        state = measured["상태"]
        if got.get("상태") != state:
            errors.append(f"{tid}: 증적 판정({state})과 승인 판정({got.get('상태')})이 다릅니다")
        if got.get("사유", "").startswith("기준값 미확정") and state in ("Pass", "Fail"):
            errors.append(f"{tid}: 기준값 미확정 행은 Pass/Fail 로 판정할 수 없습니다")
        for key in ("실제결과", "수행일", "담당자", "근거"):
            # 생략·빈 값은 증적에서 채우되, 입력한 값이 다르면 잘못된 승인이다.
            if got.get(key) and got[key] != measured[key]:
                errors.append(f"{tid}: {key} 값이 실행 증적과 다릅니다")
            got[key] = measured[key]
    if errors:
        raise InputError("; ".join(errors))

    head = list(plan_doc["head"])
    for col in ("테스트담당자", "수행일", "결과"):
        if col not in head:
            head.append(col)
    if "사유" not in head:
        head.insert(head.index("결과") + 1, "사유")
    if "실제결과" not in head:
        head.append("실제결과")
    by_id = {r["테스트ID"]: r for r in facts["rows"]}
    table, ledger_rows = [], []
    for rec in plan_doc["recs"]:
        tid = rec["테스트ID"]
        got, cur = rows[tid], {c: by_id[tid].get(c, "") for c in RESULT_COLS}
        judged = {"테스트담당자": got.get("담당자", ""), "수행일": got.get("수행일", ""), "결과": got["상태"], "사유": got["사유"], "실제결과": got["실제결과"]}
        note = got.get("비고", "")
        kept = [v for v in (cur["결과"], cur["테스트담당자"], cur["수행일"], cur["실제결과"]) if v]
        if got.get("keep") and kept:
            if cur["결과"]:  # 사람이 적은 수행 칸을 그대로 보존한다
                out = {**cur, "사유": cur["사유"] or HUMAN_NO_REASON}
            else:  # 배정 담당자처럼 결과 없이 적힌 칸만 지키고 결과·사유는 판정으로
                out = {c: cur[c] or judged[c] for c in RESULT_COLS}
                out["결과"], out["사유"] = judged["결과"], judged["사유"]
            if "유지" not in note:
                note = (f"{note} · " if note else "") + f"기존 기입 유지({', '.join(kept)})"
            if out["결과"] not in STATES:
                errors.append(f"{tid}: 결과서에 남길 결과 '{out['결과']}' 가 네 상태가 아닙니다 — PM 에게 바꿀 값을 물으세요")
        else:
            out = judged
        table.append((tid, [out[h] if h in RESULT_COLS else rec["_raw"].get(h, "") for h in head]))
        ledger_rows.append([tid, got["상태"], got["사유"], got.get("근거", ""), got.get("수행일", ""),
                            got.get("담당자", ""), by_id[tid]["fingerprint"], note, got["실제결과"]])

    old = {r["테스트ID"]: r["_raw"] for r in res_doc["recs"]} if res_doc else {}
    old_head = res_doc["head"] if res_doc else []
    new_ids = [tid for tid, _ in table]
    added = [t for t in new_ids if t not in old]
    dropped = [t for t in old if t not in set(new_ids)]
    # Compare what the Markdown reader will recover. Padding around observations
    # is table whitespace, so it must not manufacture a revision on every write.
    changed = [tid for tid, cells in table if tid in old
               and (old_head != head or any(old[tid].get(h, "") != c
                    for h, c in zip(head, _split_row(_join_row(cells)))))]
    reordered = bool(old) and [t for t in old if t in set(new_ids)] != [t for t in new_ids if t in old]
    plan_ver = facts["last_version"]
    basis_changed = bool(res_doc) and res["basis_version"] != plan_ver
    touched = res_doc is None or bool(added or dropped or changed or reordered or basis_changed)
    rev = changes.get("revision")
    last = res["last_version"] if res_doc else ""
    if touched and not rev and not dry_run:  # dry-run 은 개정이력을 정하기 전에 바뀔 내용을 보려고 부른다
        errors.append("결과서가 바뀌는데 개정이력 행(revision)이 없습니다")
    if not touched and rev:
        errors.append("결과서가 바뀌지 않는데 개정이력 행이 왔습니다 — revision 을 빼세요")
    if rev:
        if not isinstance(rev, dict) or not all(isinstance(rev.get(k, ""), str) for k in REVISION_HEAD[:5]):
            errors.append("개정이력 행의 값이 문자열이 아닙니다")
        else:
            if not re.fullmatch(r"\d+\.0", rev.get("버전", "")):
                errors.append(f"개정이력 버전은 1.0·2.0 처럼 적습니다: '{rev.get('버전', '')}'")
            if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", rev.get("개정일", "")):
                errors.append(f"개정일은 YYYY.MM.DD 여야 합니다: '{rev.get('개정일', '')}'")
            if rev.get("개정 사유") not in REVISION_REASONS:
                errors.append(f"개정 사유는 {'/'.join(REVISION_REASONS)} 중 하나입니다: '{rev.get('개정 사유', '')}'")
            if not rev.get("개정 내용", "").strip() or not rev.get("작성자", "").strip():
                errors.append("개정이력 행의 개정 내용·작성자가 비었습니다")
            if res_doc is None and (rev.get("버전") != "1.0" or rev.get("개정 사유") != "신규"):
                errors.append("새 결과서의 첫 개정이력은 1.0 신규입니다")
            if res_doc is not None and _version(rev.get("버전", "")) <= _version(last):
                errors.append(f"개정이력 버전은 결과서의 마지막 버전({last or '없음'})보다 커야 합니다")
    if errors:
        raise InputError("; ".join(errors))

    counts, rate = _rate([cells[head.index("결과")] for _, cells in table], [cells[head.index("사유")] for _, cells in table])
    res_ver = rev["버전"] if rev else last
    # 이어받아야 할 판단(제외)을 이번 판정이 버린 행 — 새 실행 결과나 PM 판정이면 맞고, 아니면 실수다
    dropped_inherit = [r["테스트ID"] for r in facts["rows"]
                       if r["inherit"] and not rows[r["테스트ID"]]["사유"].startswith(r["inherit"])]
    summary = {"changed": changed, "added": added, "dropped": dropped, "reordered": reordered,
               "basis_changed": basis_changed, "rows": len(table), "counts": counts, "rate": rate,
               "plan_version": plan_ver, "result_version": res_ver, "needs_revision": touched,
               "next_version": "1.0" if res_doc is None else f"{int(_version(last)) + 1}.0",
               "inherit_dropped": dropped_inherit, "written": False, "backup": ""}
    if dry_run:
        return summary

    nl = res_doc["newline"] if res_doc else "\n"
    table_lines = [_join_row(head), "|" + "---|" * len(head), *(_join_row(cells) for _, cells in table)]
    rev_line = _join_row([rev[k] for k in REVISION_HEAD[:5]] + [""]) if rev else ""
    basis = f"> 근거: DE-13 v{plan_ver}" if plan_ver else "> 근거: DE-13"
    if res_doc:
        lines = list(res_doc["lines"])
        lines[res_doc["head_line"]:res_doc["table_end"]] = table_lines
        _set_basis(lines, basis)
        if rev_line:
            _append_revision(lines, rev_line)
    else:
        name = _doc_name(plan_doc["lines"])
        lines = [f"# IM-03 단위테스트결과서 — {name}" if name else "# IM-03 단위테스트결과서", "",
                 f"> 생성: /gx-단위테스트결과반영 · {datetime.now():%Y-%m-%d %H:%M}", basis, "",
                 "## 개정이력", "", _join_row(REVISION_HEAD), "|------|--------|----------|----------|--------|--------|",
                 rev_line, "", _result_heading(plan_doc["lines"], plan_doc["head_line"]), "", *table_lines]
    try:  # 파일을 열기 전에 인코딩한다 — 열고 나서 실패하면 빈 파일이 남는다
        result_bytes = (nl.join(lines) + nl).encode("utf-8")
        ledger_bytes = _ledger_text(led, project, changes, ledger_rows, counts, rate, plan_ver, res_ver).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise InputError(f"UTF-8 로 쓸 수 없는 값이 있습니다: {exc}") from exc
    if touched:
        if res_doc:
            # 반영 전 결과서를 남긴다. 같은 날 사본이 있으면 그날 처음 원본이라 덮지 않는다
            copy = result_md.parent / "backup" / f"{result_md.stem}_{datetime.now():%y%m%d}.md"
            if not copy.exists():
                copy.parent.mkdir(exist_ok=True)
                copy.write_bytes(res_doc["text"].encode("utf-8"))
            summary["backup"] = f"backup/{copy.name}"
        result_md.write_bytes(result_bytes)  # 바이트로 쓴다 — Windows 텍스트 모드가 \n 을 \r\n 으로 바꾸지 않게
    ledger_md.parent.mkdir(parents=True, exist_ok=True)
    ledger_md.write_bytes(ledger_bytes)
    summary["written"] = touched
    return summary


# ---------- CLI ----------

def _write_json(path: str | None, data) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")
    else:
        print(text)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(prog="test-evidence", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--de13", required=True)
    pl.add_argument("--result", help="단위테스트결과서 — 없는 파일이면 첫 반영")
    pl.add_argument("--ledger", help="수행대장 — 주면 행마다 지난 판정과 견준다 (없는 파일이면 첫 반영)")
    pl.add_argument("--out")
    wr = sub.add_parser("write")
    wr.add_argument("--de13", required=True)
    wr.add_argument("--result", required=True)
    wr.add_argument("--ledger", required=True)
    wr.add_argument("--changes", required=True)
    wr.add_argument("--evidence", required=True, help="로컬 API·브라우저 실행 증적 JSON")
    wr.add_argument("--dry-run", action="store_true", help="쓰지 않고 바뀔 내용만 알린다")
    args = p.parse_args(argv)
    try:
        if args.cmd == "plan":
            data = read_plan(Path(args.de13), Path(args.result) if args.result else None,
                             Path(args.ledger) if args.ledger else None)
            _write_json(args.out, data)
            print(f"계획서 {len(data['rows'])}건 (v{data['last_version'] or '?'})", file=sys.stderr)
            for label, ids in (("계획서 칸 수가 맞지 않는 행", data["malformed"]), ("계획서에 겹치는 테스트ID", data["duplicates"])):
                if ids:
                    print(f"경고: {label} — {', '.join(ids)}", file=sys.stderr)
            if args.result:
                r = data["result"]
                state = f"v{r['last_version'] or '?'} (근거 계획서 v{r['basis_version'] or '?'})" if r["exists"] else "없음 — 새로 만든다"
                print(f"결과서 {state}", file=sys.stderr)
                edited = [row["테스트ID"] for row in data["rows"] if row["result_case_edited"]]
                for label, ids in (("결과서 칸 수가 맞지 않는 행", r["malformed"]), ("계획서에서 빠진 행", r["only"]),
                                   ("결과서에서 케이스 칸을 고친 행(계획서 원문으로 돌아감)", edited)):
                    if ids:
                        print(f"경고: {label} — {', '.join(ids)}", file=sys.stderr)
                if r["xlsx_newer"]:
                    print("경고: 결과서 xlsx 가 md 보다 나중에 바뀌었습니다 — xlsx 를 직접 고친 내용은 반영되지 않습니다", file=sys.stderr)
            if args.ledger:
                who = [row["written_by"] for row in data["rows"]]
                print(f"지난 수행대장 {'있음' if data['ledger']['exists'] else '없음'} — 반영이 쓴 값 {who.count('tool')} · "
                      f"사람 값 {who.count('human')} · 케이스 변경 {sum(row['case_changed'] for row in data['rows'])} · "
                      f"승계 {sum(bool(row['inherit']) for row in data['rows'])}", file=sys.stderr)
                if data["ledger"].get("unrecorded"):
                    print(f"경고: 계획서 개정이력 없이 고친 케이스 — {', '.join(data['ledger']['unrecorded'])}", file=sys.stderr)
                if data["ledger"].get("stale"):
                    print("경고: 결과서 버전이 수행대장의 마지막 반영 기록과 다릅니다 — 손으로 고쳤거나 지난 반영이 끝까지 가지 못했습니다",
                          file=sys.stderr)
        else:
            changes = json.loads(Path(args.changes).read_text(encoding="utf-8"))
            s = write_result(Path(args.de13), Path(args.result), Path(args.ledger), changes, Path(args.evidence), dry_run=args.dry_run)
            c = s["counts"]
            head = "시험 실행(쓰지 않음)" if args.dry_run else ("결과서 갱신" if s["written"] else "결과서 변경 없음 — 수행대장만 기록")
            tail = f", 반영 전 사본 {s['backup']}" if s["backup"] else ""
            print(f"{head} — 바뀐 행 {len(s['changed'])} · 추가 {len(s['added'])} · 계획서에서 빠짐 {len(s['dropped'])} | "
                  f"Pass {c['Pass']} · Fail {c['Fail']} · 미구현 {c['미구현']} · 미검증 {c['미검증']}, 수행률 {s['rate']}{tail}")
            for label, ids in (("바뀐 행", s["changed"]), ("추가", s["added"]), ("계획서에서 빠짐", s["dropped"])):
                if ids:
                    print(f"  {label}: {', '.join(ids)}")
            if args.dry_run:
                print(f"  개정이력: {'필요 — 다음 버전 ' + s['next_version'] if s['needs_revision'] else '필요 없음 (결과서가 바뀌지 않는다)'}")
            if s["inherit_dropped"]:
                print(f"  경고: 이어받을 판단(제외)을 이번 판정이 버린 행 — {', '.join(s['inherit_dropped'])}")
    except InputError as exc:
        print(f"test-evidence: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"test-evidence: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
