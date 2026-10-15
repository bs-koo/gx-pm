#!/usr/bin/env python3
"""단위테스트 수행 증적 도구 — Python 3.10 표준 라이브러리 전용.

apply-test-results 스킬이 쓴다. 이 스크립트는 **판단하지 않는다.** 테스트와 DE-13 행을
짝짓는 것은 스킬(모델)의 몫이고, 여기서는 그 판단에 쓸 사실을 정확히 모으고
승인된 결과를 표 모양을 깨지 않고 쓴다.

  index : 개발 레포의 테스트 메서드를 색인한다 — 이름·설명·본문 값·마지막 커밋, 그리고 실행 근거
          (빌드 도구가 남긴 JUnit XML, gx-tdd 를 썼으면 verify 기록). 레포 여러 개를 함께 받는다
  plan  : DE-13 계획서 행을 읽는다 (〃 해소, 행 지문, 칸 수 검사, 다음 테스트ID). 계획서는 읽기만 한다.
          --result 를 주면 결과서의 지금 수행 칸을, --ledger 를 주면 지난 판정과 견준 사실(누가 썼나·
          케이스 변경·승계)을 행마다 붙인다
  write : 승인된 판정으로 단위테스트결과서(계획서 행 + 수행 칸)와 수행대장을 함께 쓴다.
          행 지문·건수·수행률은 도구가 센다. --dry-run 은 쓰지 않고 바뀔 내용만 알린다

예시:
  python test-evidence.py index --source D:/projects/reb-api --source D:/projects/reb-web --out tests.json
  python test-evidence.py plan --de13 REB-단위테스트계획서.md --result REB-단위테스트결과서.md --ledger 증적/REB-단위테스트수행대장.md --out plan.json
  python test-evidence.py write --de13 REB-단위테스트계획서.md --result REB-단위테스트결과서.md --ledger 증적/REB-단위테스트수행대장.md --changes changes.json [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

DITTO = "〃"
CASE_FIELDS = ("사전조건", "입력", "기대결과", "사후조건")
EXCLUDED_MARK = re.compile(r"제외\s*[—–-]\s*위험\s*수용|위험\s*수용으로\s*제외")
AC_LINE = re.compile(r"^\s*[-*]?\s*(~~)?\s*\**\s*(AC-\d+)\s*\**\s*[:.]\s*(.*)$")
# gx-tdd trust-ledger 의 위험 수용 중 verify 가 테스트를 돌리지 않고 통과한 경우
NO_TEST_RUN = re.compile(r"검증 명령 미감지|테스트 실행 0건|테스트 부재|TDD 미이행")
GWT_LINE = re.compile(r"^\s*[-*]?\s*\**\s*(Given|When|Then|And)\s*\**\s*[:：]\s*(.*)$", re.I)
TASK_KEY = re.compile(r"RGR T(\d+)\s*\(([^)]*)\)")
TEST_FILE = re.compile(r"test-file\s*:\s*([^,}\s]+)")
TOP_KEY = re.compile(r"^([A-Za-z][\w-]*)\s*:\s*(.*)$")
DUBIOUS = re.compile(r"dubious ownership in repository at '([^']+)'")


class InputError(Exception):
    """입력 경로·형식 오류 (종료 코드 2)."""


# ---------- collect ----------

def _exec(args: list[str], cwd: Path, timeout: int = 60) -> tuple[int, str, str] | None:
    if shutil.which(args[0]) is None:
        return None
    # git 메시지를 영어로 받는다 — 소유권 거부를 문구로 알아본다
    env = {**os.environ, "LC_ALL": "C", "LANGUAGE": "C"} if args[0] == "git" else None
    try:
        out = subprocess.run(args, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace",
                             timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.returncode, out.stdout.strip(), out.stderr.strip()


def _run(args: list[str], cwd: Path, timeout: int = 60) -> str | None:
    out = _exec(args, cwd, timeout)
    return out[1] if out and out[0] == 0 else None


def _local(at: datetime) -> datetime:
    """비교용 — 시간대가 있으면 이 PC 의 현지 시각으로 바꿔 시간대를 뗀다."""
    return at.astimezone().replace(tzinfo=None) if at.tzinfo else at


def _iso(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _svn_commit(entry: ET.Element) -> dict | None:
    at = _iso(entry.findtext("commit/date") or "")
    if at is None:
        return None
    # svn 날짜는 UTC 다 — 현지 날짜로 적어야 하루 어긋나지 않는다
    return {"date": _local(at).strftime("%Y.%m.%d"), "author": entry.findtext("commit/author") or "", "at": at}


def _vcs(source: Path) -> tuple[str, list[str], list[str]]:
    """(vcs, git 명령 앞부분, 경고)."""
    git = ["git"]
    out = _exec(git + ["rev-parse", "--is-inside-work-tree"], source)
    owner = DUBIOUS.search(out[2]) if out and out[0] else None
    if owner:
        # Codex 샌드박스처럼 다른 계정으로 돌면 소유권 검사에 걸린다 — 이 저장소 하나만 명령마다 허용한다
        git = ["git", "-c", f"safe.directory={owner.group(1)}"]
        out = _exec(git + ["rev-parse", "--is-inside-work-tree"], source)
    if out and out[0] == 0 and out[1] == "true":
        return "git", git, []
    warnings = []
    if out and out[0] and "not a git repository" not in out[2]:
        warnings.append(f"git 을 읽지 못해 수행일·담당자·verify 뒤 AC 변경을 알 수 없음: {out[2].splitlines()[0]}")
    if _run(["svn", "info", "--show-item", "wc-root"], source):
        return "svn", git, warnings
    return "none", git, warnings


def _last_change(source: Path, vcs: str, git: list[str], rel: str) -> tuple[str, str, datetime | None]:
    """state.md 를 마지막으로 바꾼 커밋의 (날짜 YYYY.MM.DD, 작성자, 커밋 시각)."""
    if vcs == "git":
        out = _run(git + ["log", "-1", "--format=%ad%x1f%an%x1f%cI", "--date=format:%Y.%m.%d", "--", rel], source)
        if out and out.count("\x1f") == 2:
            date, author, at = out.split("\x1f")
            return date, author, _iso(at)
    elif vcs == "svn":
        out = _run(["svn", "info", "--xml", rel], source)
        if out:
            try:
                entry = ET.fromstring(out).find("entry")
                commit = _svn_commit(entry) if entry is not None else None
                if commit:
                    return commit["date"], commit["author"], commit["at"]
            except ET.ParseError:
                pass
    return "", "", None


def _verified_text(source: Path, vcs: str, git: list[str], state_rel: str, doc_rel: str) -> str | None:
    """state.md 를 마지막으로 바꾼 커밋 시점의 AC 문서. 알 수 없으면 None."""
    if vcs != "git":
        return None
    commit = _run(git + ["log", "-1", "--format=%H", "--", state_rel], source)
    if not commit:
        return None
    # 그 커밋에 AC 문서가 없으면 AC 는 verify 뒤에 생긴 것이다 — 빈 문서로 보고 전부 바뀐 것으로 친다.
    # ./ 를 붙여야 소스가 저장소 하위 폴더여도 현재 폴더 기준으로 찾는다
    return _run(git + ["show", f"{commit}:./{doc_rel}"], source) or ""


def _top_keys(text: str) -> dict[str, str]:
    keys = {}
    for line in text.splitlines():
        m = TOP_KEY.match(line)
        if m and m.group(1) not in keys:
            keys[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return keys


def _section(text: str, heading: re.Pattern) -> tuple[str, str]:
    """(제목 앞 본문, 제목 아래 같은 수준 이하의 다음 제목 전까지)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = heading.match(line)
        if not m:
            continue
        level = len(m.group(1))
        body = []
        for nxt in lines[i + 1:]:
            h = re.match(r"^(#+)\s", nxt)
            if h and len(h.group(1)) <= level:
                break
            body.append(nxt)
        return "\n".join(lines[:i]), "\n".join(body)
    return text, ""


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _parse_acs(section: str) -> list[dict]:
    acs, cur, last, key_indent, blocks = [], None, None, 0, []
    for line in section.splitlines():
        m = AC_LINE.match(line)
        if m:
            # ~~AC-N~~ 은 지운 AC 다 — 그 G-W-T 가 앞 AC 를 덮지 않게 별도 AC 로 받고 제외로 둔다
            cur = {"id": m.group(2), "title": m.group(3).strip().strip("*~ ").strip(), "given": "", "when": "", "then": "",
                   "excluded": bool(m.group(1))}
            acs.append(cur)
            blocks.append([line])
            last = None
            continue
        if cur is None:
            continue
        blocks[-1].append(line)
        g = GWT_LINE.match(line)
        if g:
            key = g.group(1).lower()
            if key == "and":
                key = last or "then"
                cur[key] = f"{cur[key]}, {g.group(2).strip()}".strip(", ")
            else:
                cur[key] = g.group(2).strip()
            last, key_indent = key, _indent(line)
        elif last and line.strip() and _indent(line) > key_indent:
            cur[last] = f"{cur[last]} {line.strip()}"  # 키보다 깊게 들여쓴 줄은 앞 값의 이어지는 줄
    for ac, block in zip(acs, blocks):
        ac["excluded"] = ac["excluded"] or bool(EXCLUDED_MARK.search("\n".join(block)))
    return acs


def _risks(slug_dir: Path) -> list[str]:
    """trust-ledger.md 의 `### 위험 수용` 항목 줄."""
    path = slug_dir / "trust-ledger.md"
    if not path.is_file():
        return []
    _, body = _section(path.read_text(encoding="utf-8", errors="replace"), re.compile(r"^(#+)\s*위험\s*수용"))
    return [line.strip() for line in body.splitlines() if line.strip().startswith(("-", "*"))]


def _task_tests(state: str, root: Path) -> tuple[dict[str, list[dict]], dict[str, list[str]]]:
    """state.md 의 "RGR T{N} (AC-…)" 태스크에서 (AC → 테스트 파일, 태스크 번호 → AC)."""
    tasks, cur = [], None
    for line in state.splitlines():
        m = TASK_KEY.search(line)
        if m:
            cur = {"n": m.group(1), "acs": re.findall(r"AC-\d+", m.group(2)), "text": line, "indent": _indent(line)}
            tasks.append(cur)
        elif cur is not None and line.strip() and _indent(line) <= cur["indent"]:
            cur = None  # 태스크와 같거나 얕은 들여쓰기 = 다음 항목·형제 키 — 그 안의 test-file 은 이 태스크 것이 아니다
        elif cur is not None:
            cur["text"] += "\n" + line
    out: dict[str, list[dict]] = {}
    for t in tasks:
        f = TEST_FILE.search(t["text"])
        if not f:
            continue
        entry = {"file": f.group(1), "exists": (root / f.group(1)).is_file(), "red_report": f"reports/t{t['n']}-red.md"}
        for ac in t["acs"]:
            out.setdefault(ac, []).append(entry)
    return out, {t["n"]: t["acs"] for t in tasks}


def _skip_dir(name: str) -> bool:
    return name.startswith((".", "logs-")) or ".backup-" in name or name == "architecture"


def _record(slug_dir: Path, source: Path, vcs: str, git: list[str]) -> dict | None:
    state_path = slug_dir / "state.md"
    if not state_path.is_file():
        return None
    state = state_path.read_text(encoding="utf-8", errors="replace")
    keys = _top_keys(state)
    pipeline, origin, verify = keys.get("pipeline", ""), keys.get("origin", ""), keys.get("verify-status", "")
    # 같은 브랜치에서 core 를 돌린 뒤 full 로 다시 돌리면 낡은 ac.md 가 남는다 — mode 가 정한 문서를 먼저 본다
    order = ("ac.md", "prd.md") if keys.get("mode") == "core" and pipeline != "gx-ralph" else ("prd.md", "ac.md")
    ac_file = next((slug_dir / n for n in order if (slug_dir / n).is_file()), slug_dir / order[0])
    doc = ac_file.read_text(encoding="utf-8", errors="replace") if ac_file.is_file() else ""
    heading = re.compile(r"^(#+)\s*요구사항\s*\(AC\)") if ac_file.name == "ac.md" else re.compile(r"^(#+)\s*수용\s*기준")
    before, section = _section(doc, heading)
    acs = _parse_acs(section)
    tests, task_acs = _task_tests(state, source)
    risks = _risks(slug_dir)
    passes: dict[str, bool] = {}
    if pipeline == "gx-ralph":
        try:
            data = json.loads((slug_dir / "ac-status.json").read_text(encoding="utf-8"))
            passes = {a.get("id"): bool(a.get("passes")) for a in data.get("acs", [])}
        except (OSError, ValueError):
            passes = {}
    rel = state_path.relative_to(source).as_posix()
    # verify 뒤에 바뀐 AC 는 그 verify 가 증명하지 않는다 — 커밋 시점 AC 와 지금 AC 를 비교한다
    old = _verified_text(source, vcs, git, rel, ac_file.relative_to(source).as_posix()) if doc else None
    old_acs = {a["id"]: a for a in _parse_acs(_section(old, heading)[1])} if old is not None else None
    tasked = {a for ids in task_acs.values() for a in ids}
    for ac in acs:
        ac["tests"] = tests.get(ac["id"], [])
        ac["passes"] = passes.get(ac["id"]) if pipeline == "gx-ralph" else None
        # RGR 태스크가 없는 AC 는 구현 단계에서 빠진 것이다 (ralph 는 태스크를 state.md 에 남기지 않는다)
        ac["has_task"] = ac["id"] in tasked if pipeline == "gx-tdd" else None
        own = re.compile(rf"{re.escape(ac['id'])}(?!\d)")
        tasks_of = {n for n, ids in task_acs.items() if ac["id"] in ids}
        ac["risks"] = [r for r in risks if own.search(r)
                       or any(re.search(rf"(?<![A-Za-z])T{n}(?!\d)", r) for n in tasks_of)]
        ac["changed_after_verify"] = None if old_acs is None else old_acs.get(ac["id"]) != {
            k: ac[k] for k in ("id", "title", "given", "when", "then", "excluded")}
    if pipeline == "gx-tdd":
        status = "evidence" if verify == "passed" else "incomplete"
        reason = "verify 통과" if status == "evidence" else f"verify-status: {verify or '없음'}"
    elif pipeline == "gx-ralph" and origin == "gx-tdd":
        status = "evidence" if any(passes.values()) else "incomplete"
        reason = "ralph 루프(gx-tdd) — AC별 passes 기준, 테스트 파일 기록 없음"
    else:
        status = "insufficient"
        reason = "gx-tdd 기록이 아님 (verify 증적 없음)" if not pipeline else f"pipeline: {pipeline}/{origin}"
    if not acs and status == "evidence":
        status, reason = "insufficient", "AC 를 찾지 못함 (ac.md·prd.md 수용 기준)"
    untested = next((r for r in risks if NO_TEST_RUN.search(r)), None)
    if untested and status == "evidence":
        status, reason = "insufficient", f"verify 가 테스트 실행 없이 통과 — trust-ledger 위험 수용: {untested}"
    date, author, at = _last_change(source, vcs, git, rel)
    changed = None if old_acs is None else any(a["changed_after_verify"] for a in acs)
    return {"slug": slug_dir.name, "pipeline": pipeline, "origin": origin, "verify": verify,
            "mode": keys.get("mode", ""), "branch": keys.get("branch", ""), "status": status, "reason": reason,
            "date": date, "author": author, "committed_at": at.isoformat() if at else "",
            "ac_source": ac_file.name if doc else "",
            "ac_changed_after_verify": changed, "risk_acceptances": risks,
            "context": before.strip()[:1200], "acs": acs}


def collect(source: Path) -> dict:
    source = Path(source)
    if not source.is_dir():
        raise InputError(f"소스 경로가 없습니다: {source}")
    vcs, git, warnings = _vcs(source)
    head = branch = ""
    if vcs == "git":
        branch = _run(git + ["rev-parse", "--abbrev-ref", "HEAD"], source) or ""
        head = _run(git + ["rev-parse", "--short", "HEAD"], source) or ""
    records = []
    dev = source / ".dev"
    if dev.is_dir():
        for d in sorted(p for p in dev.iterdir() if p.is_dir() and not _skip_dir(p.name)):
            rec = _record(d, source, vcs, git)
            if rec:
                records.append(rec)
    return {"source": source.as_posix(), "vcs": vcs, "branch": branch, "head": head,
            "warnings": warnings, "records": records}


# ---------- index ----------
# 근거는 레포에 지금 있는 테스트 메서드다. 누가 어떤 도구로 썼든 상관없다.

SKIP_DIRS = {"node_modules", "build", "target", "dist", "out", "bin", "coverage", "vendor"}
JVM_TEST_NAME = re.compile(r"(Tests?|IT|Spec)\.(java|kt)$")
JS_TEST_NAME = re.compile(r"\.(test|spec)\.(js|jsx|ts|tsx|mjs|cjs)$")
JS_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
REPORT_DIRS = ("test-results", "surefire-reports", "failsafe-reports")
REPORT_NAME = re.compile(r"^(TEST-.*|junit.*|test-results?.*)\.xml$", re.I)
TEST_ANNOT = {"Test", "ParameterizedTest", "RepeatedTest", "TestFactory", "TestTemplate"}
ANNOT = re.compile(r"@(\w+)(\((?:[^()\"]|\"(?:[^\"\\]|\\.)*\")*\))?")
DISPLAY_NAME = re.compile(r'@DisplayName\(\s*"((?:[^"\\]|\\.)*)"')
CLASS_DECL = re.compile(r"\b(?:class|object|interface)\s+(\w+)")
JS_CALL = re.compile(r"\b(x?(?:describe|it|test))(?:\.(skip|only|todo|concurrent))?\s*\(\s*(['\"`])((?:\\.|(?!\3).)*)\3")
ASSERT_CALL = re.compile(r"\b(assert\w*|verify\w*|expect|then)\s*[(<{]")
STRING_LIT = re.compile(r"\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)'")
NUMBER_LIT = re.compile(r"(?<![\w.])(\d[\d_,]*)(?:\.\d+)?[lLfFdD]?(?![\w])")


def _mask(line: str, state: dict, quotes: str) -> str:
    """문자열 안쪽과 주석을 공백으로 지운다 — 길이는 그대로라 위치가 원문과 맞는다."""
    out, i, n = [], 0, len(line)
    while i < n:
        if state.get("block"):
            end = line.find("*/", i)
            if end < 0:
                out.append(" " * (n - i))
                return "".join(out)
            out.append(" " * (end + 2 - i))
            i, state["block"] = end + 2, False
            continue
        ch = line[i]
        if line.startswith("//", i):
            out.append(" " * (n - i))
            break
        if line.startswith("/*", i):
            state["block"] = True
            out.append("  ")
            i += 2
            continue
        if ch in quotes:
            j = i + 1
            while j < n and line[j] != ch:
                j += 2 if line[j] == "\\" else 1
            out.append(ch + " " * (min(j, n) - i - 1) + (ch if j < n else ""))
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def _literals(body: list[str]) -> list[str]:
    found: list[str] = []
    for line in body:
        for m in STRING_LIT.finditer(line):
            text = _unescape(m.group(1) if m.group(1) is not None else m.group(2)).strip()
            if 1 < len(text) <= 80:
                found.append(text)
        for m in NUMBER_LIT.finditer(re.sub(STRING_LIT, "", line)):
            digits = re.sub(r"[_,]", "", m.group(1))
            if len(digits) >= 3:
                found.append(digits)
    return list(dict.fromkeys(found))[:20]


def _body_end(masked: list[str], start: int) -> int:
    depth, opened = 0, False
    for j in range(start, min(len(masked), start + 400)):
        depth += masked[j].count("{") - masked[j].count("}")
        opened = opened or "{" in masked[j]
        if opened and depth <= 0:
            return j
    return start


def _entry(lines: list[str], masked: list[str], i: int, **fields) -> dict:
    body = lines[i:_body_end(masked, i) + 1]
    return {**fields, "line": i + 1, "asserts": sum(len(ASSERT_CALL.findall(m)) for m in masked[i:i + len(body)]),
            "literals": _literals(body)}


def _jvm_tests(text: str, lang: str) -> list[dict]:
    lines = text.splitlines()
    state: dict = {}
    masked = [_mask(line, state, "\"'") for line in lines]
    tests, pending, display, classes, depth = [], [], "", [], 0
    for i, (line, code) in enumerate(zip(lines, masked)):
        annots = [m.group(1) for m in ANNOT.finditer(code)]
        if annots:
            pending += annots
            m = DISPLAY_NAME.search(line)
            display = _unescape(m.group(1)) if m and "@DisplayName" in code else display
        rest = ANNOT.sub("", code).strip()
        if rest:
            name = None
            if TEST_ANNOT & set(pending):
                m = re.search(r"\bfun\s+`([^`]+)`", line) or re.search(r"\bfun\s+(\w+)\s*\(", rest) \
                    or re.search(r"(\w+)\s*\(", rest)
                name = m.group(1) if m else None
            if name:
                tests.append(_entry(lines, masked, i, lang=lang, **{"class": classes[-1][0] if classes else ""},
                                    name=name, display=display, disabled=bool({"Disabled", "Ignore"} & set(pending))))
            pending, display = [], ""
            decl = CLASS_DECL.search(rest)
            if decl:
                classes.append([decl.group(1), depth, False])  # [이름, 선언 깊이, 본문이 열렸나]
        depth += code.count("{") - code.count("}")
        for c in classes:
            c[2] = c[2] or depth > c[1]
        while classes and classes[-1][2] and depth <= classes[-1][1]:
            classes.pop()
    return tests


def _js_tests(text: str) -> list[dict]:
    lines = text.splitlines()
    state: dict = {}
    masked = [_mask(line, state, "\"'`") for line in lines]
    tests, describes, depth = [], [], 0
    for i, (line, code) in enumerate(zip(lines, masked)):
        for m in JS_CALL.finditer(line):
            if code[m.start():m.start() + len(m.group(1))] != m.group(1):
                continue  # 문자열 안의 글자다
            kind, mod, title = m.group(1), m.group(2), _unescape(m.group(4))
            off = kind.startswith("x") or mod in ("skip", "todo")
            if kind.lstrip("x") == "describe":
                describes.append((title, depth, off or any(d[2] for d in describes)))
            else:
                tests.append(_entry(lines, masked, i, lang="js", **{"class": " > ".join(d[0] for d in describes)},
                                    name=title, display="", disabled=off or any(d[2] for d in describes)))
        depth += code.count("{") - code.count("}")
        while describes and depth <= describes[-1][1]:
            describes.pop()
    return tests


def _test_files(source: Path) -> list[tuple[Path, str]]:
    found = []
    for root, dirs, files in os.walk(source):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        rel_dir = Path(root).relative_to(source).as_posix()
        in_test_dir = "/test/" in f"/{rel_dir}/" or "__tests__" in rel_dir.split("/")
        for name in sorted(files):
            if name.endswith((".java", ".kt")) and (in_test_dir or JVM_TEST_NAME.search(name)):
                found.append((Path(root) / name, "kotlin" if name.endswith(".kt") else "java"))
            elif name.endswith(JS_EXT) and (JS_TEST_NAME.search(name) or "__tests__" in rel_dir.split("/")):
                found.append((Path(root) / name, "js"))
    return found


def _file_changes(source: Path, vcs: str, git: list[str]) -> dict[str, dict]:
    """파일마다 마지막 커밋 {date, author, at}. 한 번의 VCS 호출로 모은다."""
    changes: dict[str, dict] = {}
    if vcs == "git":
        out = _run(git + ["log", "--relative", "--no-renames", "--name-only", "--date=format:%Y.%m.%d",
                          "--format=%x1e%ad%x1f%an%x1f%cI"], source, timeout=300) or ""
        for chunk in out.split("\x1e"):
            head, _, names = chunk.partition("\n")
            if head.count("\x1f") != 2:
                continue
            date, author, at = head.split("\x1f")
            for name in filter(None, (n.strip() for n in names.splitlines())):
                changes.setdefault(name, {"date": date, "author": author, "at": _iso(at)})
    elif vcs == "svn":
        out = _run(["svn", "info", "-R", "--xml", "."], source, timeout=300) or ""
        try:
            for entry in ET.fromstring(out).iter("entry") if out else []:
                commit = _svn_commit(entry)
                if entry.get("kind") == "file" and commit:
                    changes[entry.get("path", "").replace("\\", "/").removeprefix("./")] = commit
        except ET.ParseError:
            pass
    return changes


def _reports(source: Path) -> list[dict]:
    """빌드 도구가 남긴 JUnit XML (Gradle·Maven·jest-junit 등). 커밋되지 않는 파일이라 있는 그대로 읽는다."""
    found = []
    for root, dirs, files in os.walk(source):
        dirs[:] = sorted(d for d in dirs if d != "node_modules" and not d.startswith("."))
        in_report_dir = any(part in REPORT_DIRS for part in Path(root).relative_to(source).parts)
        for name in sorted(files):
            if not name.endswith(".xml") or not (in_report_dir or REPORT_NAME.match(name)):
                continue
            path = Path(root) / name
            try:
                tree = ET.parse(path)
            except (ET.ParseError, OSError):
                continue
            suites = [tree.getroot()] if tree.getroot().tag == "testsuite" else list(tree.getroot().iter("testsuite"))
            for suite in suites:
                at = _iso(suite.get("timestamp", "")) or datetime.fromtimestamp(path.stat().st_mtime)
                for case in suite.findall("testcase"):
                    bad = case.find("failure")
                    bad = bad if bad is not None else case.find("error")
                    status = "failed" if bad is not None else "skipped" if case.find("skipped") is not None else "passed"
                    entry = {"classname": case.get("classname", ""), "name": case.get("name", ""),
                             "status": status, "at": _local(at), "source": path.relative_to(source).as_posix()}
                    if bad is not None:  # Fail 사유에 그대로 옮길 한 줄 — message 속성이 없으면 본문 첫 줄
                        text = bad.get("message") or (bad.text or "").strip()
                        entry["message"] = (text.splitlines() or [""])[0].strip()[:300]
                    found.append(entry)
    return found


def _report_matches(test: dict, case: dict) -> bool:
    name = case["name"]
    if test["lang"] == "js":
        last = test["class"].split(" > ")[-1] if test["class"] else ""
        return (name == test["name"] or name.endswith(f" {test['name']}")) and (
            not last or last in f"{case['classname']} {name}")
    if re.split(r"[.$]", case["classname"])[-1] != test["class"]:
        return False
    return name in (test["name"], f"{test['name']}()") or name.startswith(f"{test['name']}(") or (
        bool(test["display"]) and name == test["display"])


def _run_of(case_runs: list[dict]) -> dict | None:
    if not case_runs:
        return None
    latest = max(r["at"] for r in case_runs)
    same = [r for r in case_runs if r["at"] == latest]
    status = next((s for s in ("failed", "passed", "skipped") if any(r["status"] == s for r in same)), "passed")
    run = {"status": status, "at": latest, "by": "report", "source": same[0]["source"]}
    messages = [r["message"] for r in same if r["status"] == "failed" and r.get("message")]
    if messages:
        run["message"] = messages[0]
    return run


def index(sources: list[Path]) -> dict:
    out: dict = {"sources": [], "tests": [], "gx_tdd": []}
    names: dict[str, int] = {}
    for source in map(Path, sources):
        if not source.is_dir():
            raise InputError(f"소스 경로가 없습니다: {source}")
        names[source.name] = names.get(source.name, 0) + 1
        repo = source.name if names[source.name] == 1 else f"{source.name}#{names[source.name]}"
        vcs, git, warnings = _vcs(source)
        changes = _file_changes(source, vcs, git)
        reports = _reports(source)
        records = collect(source)["records"] if (source / ".dev").is_dir() else []
        tests = []
        for path, lang in _test_files(source):
            rel = path.relative_to(source).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            for t in _js_tests(text) if lang == "js" else _jvm_tests(text, lang):
                change = changes.get(rel)
                t.update(repo=repo, file=rel, last_change={"date": change["date"], "author": change["author"]}
                         if change else {"date": "", "author": ""})
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                runs = []
                report = _run_of([c for c in reports if _report_matches(t, c)])
                if report:
                    # 결과 파일이 만들어진 뒤에 테스트 파일이 바뀌었으면 그 결과는 지금 코드의 결과가 아니다
                    runs.append({**report, "stale": mtime.timestamp() > report["at"].timestamp() + 2})
                for rec in records:
                    verified = _iso(rec["committed_at"]) if rec["committed_at"] else None
                    linked = {x["file"] for a in rec["acs"] for x in a["tests"]}
                    if rec["status"] == "evidence" and verified and rel in linked:
                        later = bool(change and change["at"] and change["at"] > verified)
                        runs.append({"status": "passed", "at": _local(verified), "date": rec["date"],
                                     "by": "gx-tdd verify", "source": f".dev/{rec['slug']}/state.md", "stale": later})
                run = max(runs, key=lambda r: r["at"]) if runs else None
                t["run"] = ({**run, "at": run["at"].isoformat(timespec="seconds"),
                             "date": run.get("date") or run["at"].strftime("%Y.%m.%d")} if run else {"status": "none"})
                tests.append(t)
        reported = {}
        for t in tests:
            if t["run"].get("by") == "report":
                reported[t["file"]] = reported.get(t["file"], True) and t["run"]["stale"]
        if len(reported) >= 2 and all(reported.values()):
            # 수정 시각을 보존하지 않고 폴더를 복사하면 모든 결과가 낡아 보인다
            warnings = warnings + ["결과 파일이 있는 테스트 파일이 모두 결과보다 나중에 바뀌었습니다 — 폴더를 복사했거나 "
                                   "새로 받았다면 테스트를 돌린 원래 폴더를 경로로 주세요"]
        branch = head = ""
        if vcs == "git":
            branch = _run(git + ["rev-parse", "--abbrev-ref", "HEAD"], source) or ""
            head = _run(git + ["rev-parse", "--short", "HEAD"], source) or ""
        out["sources"].append({"path": source.as_posix(), "repo": repo, "vcs": vcs, "branch": branch, "head": head,
                               "warnings": warnings, "test_files": len({t["file"] for t in tests}),
                               "reports": sorted({c["source"] for c in reports})})
        out["tests"] += tests
        out["gx_tdd"] += [{**r, "repo": repo} for r in records]
    return out


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

RESULTS = ("Pass", "Fail", "미구현", "미검증")  # 결과 칸이 받는 값 (templates/DE-13-unit-test-result.md §결과 상태)
STATES = RESULTS
RESULT_COLS = ("테스트담당자", "수행일", "결과", "사유")  # 결과서에서 수행이 채우는 칸 — 나머지는 계획서 원문
REVISION_HEAD = ["버전", "개정일", "개정 사유", "개정 내용", "작성자", "승인자"]
REVISION_REASONS = ("신규", "추가", "변경", "삭제", "보완")  # templates/revision-history.md
HUMAN_NO_REASON = "기존 기입 — 사유 미기재"
CONTROL = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")  # 줄바꿈 말고는 표 칸에 들어갈 수 없다
LEDGER_COLS = ["테스트ID", "상태", "사유", "근거", "수행일", "담당자", "행 지문", "비고"]
HISTORY_COLS = ["반영일", "계획서 버전", "결과서 버전", "Pass", "Fail", "미구현", "미검증", "수행률",
                "신규 후보", "보강 후보", "소스 기준"]
NOT_UNIT = ("비기능", "기준값 미확정", "제외")  # 수행률 분모에서 빼는 사유 첫머리 — 단위 시험으로 판정하지 않는 행
INHERITED = ("제외", "PM 확인")  # 다음 반영에 넘겨받는 사람의 판단


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
    """결과·사유·수행일·담당자를 누가 썼나. 지난 수행대장과 네 칸이 같을 때만 반영이 쓴 값이다."""
    mine = tuple(row.get(c, "") for c in ("결과", "사유", "수행일", "테스트담당자"))
    if not any(mine):
        return "empty"
    if prev and mine == (prev.get("상태", ""), prev.get("사유", ""), prev.get("수행일", ""), prev.get("담당자", "")):
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
    denom = len(states) - sum(1 for why in reasons if why.startswith(NOT_UNIT))
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


def write_result(plan_md: Path, result_md: Path, ledger_md: Path, changes: dict, dry_run: bool = False) -> dict:
    """승인된 판정으로 단위테스트결과서와 수행대장을 함께 쓴다. 계획서는 읽기만 한다.

    결과서 행은 매번 지금 계획서에 맞춘다 — 케이스 칸은 계획서 원문을 옮기고, 수행 칸만 판정으로 채운다.
    둘을 한 번에 쓰는 까닭: 결과서만 바뀌고 수행대장이 따라오지 못하면 다음 반영 때 이 도구가 쓴 값을
    사람 값으로 잘못 가린다. 검증에 하나라도 걸리면 아무 파일도 건드리지 않는다."""
    plan_md, result_md, ledger_md = Path(plan_md), Path(result_md), Path(ledger_md)
    facts = read_plan(plan_md, result=result_md, ledger=ledger_md)
    plan_doc = _load(plan_md)
    res = facts["result"]
    res_doc = _load(result_md) if res["exists"] else None
    led = read_ledger(ledger_md)
    rows = changes.get("rows") or {}
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
            continue
        if not all(isinstance(v, str) for k, v in got.items() if k != "keep") or not isinstance(got.get("keep", False), bool):
            errors.append(f"{tid}: 값의 형식이 맞지 않습니다")
            continue
        if got.get("상태") not in STATES:
            errors.append(f"{tid}: 상태는 {'/'.join(STATES)} 중 하나여야 합니다: '{got.get('상태', '')}'")
        if not got.get("사유", "").strip():
            errors.append(f"{tid}: 사유가 비었습니다")
    if errors:
        raise InputError("; ".join(errors))

    head = list(plan_doc["head"])
    for col in ("테스트담당자", "수행일", "결과"):
        if col not in head:
            head.append(col)
    if "사유" not in head:
        head.insert(head.index("결과") + 1, "사유")
    by_id = {r["테스트ID"]: r for r in facts["rows"]}
    table, ledger_rows = [], []
    for rec in plan_doc["recs"]:
        tid = rec["테스트ID"]
        got, cur = rows[tid], {c: by_id[tid].get(c, "") for c in RESULT_COLS}
        judged = {"테스트담당자": got.get("담당자", ""), "수행일": got.get("수행일", ""), "결과": got["상태"], "사유": got["사유"]}
        note = got.get("비고", "")
        kept = [v for v in (cur["결과"], cur["테스트담당자"], cur["수행일"]) if v]
        if got.get("keep") and kept:
            if cur["결과"]:  # 사람이 적은 결과는 네 칸 그대로
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
                            got.get("담당자", ""), by_id[tid]["fingerprint"], note])

    old = {r["테스트ID"]: r["_raw"] for r in res_doc["recs"]} if res_doc else {}
    old_head = res_doc["head"] if res_doc else []
    new_ids = [tid for tid, _ in table]
    added = [t for t in new_ids if t not in old]
    dropped = [t for t in old if t not in set(new_ids)]
    changed = [tid for tid, cells in table if tid in old
               and (old_head != head or any(old[tid].get(h, "") != c for h, c in zip(head, cells)))]
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
    # 이어받아야 할 판단(제외·PM 확인)을 이번 판정이 버린 행 — 새 실행 결과나 PM 판정이면 맞고, 아니면 실수다
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
        lines = [f"# 단위테스트결과서 — {name}" if name else "# 단위테스트결과서", "",
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
    ix = sub.add_parser("index")
    ix.add_argument("--source", required=True, action="append", help="개발 레포 경로 (여러 번 줄 수 있다)")
    ix.add_argument("--out")
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
    wr.add_argument("--dry-run", action="store_true", help="쓰지 않고 바뀔 내용만 알린다")
    args = p.parse_args(argv)
    try:
        if args.cmd == "index":
            data = index([Path(s) for s in args.source])
            _write_json(args.out, data)
            runs = [t["run"]["status"] for t in data["tests"]]
            off = sum(t["disabled"] for t in data["tests"])
            stale = sum(1 for t in data["tests"] if t["run"]["status"] == "passed" and t["run"].get("stale"))
            print(f"테스트 {len(runs)}건 — 실행 결과 통과 {runs.count('passed')} (그중 실행 뒤 테스트가 바뀐 결과 {stale}) · "
                  f"실패 {runs.count('failed')} · 건너뜀 {runs.count('skipped')} · 결과 없음 {runs.count('none')} "
                  f"(사용 안 함 {off})", file=sys.stderr)
            for s in data["sources"]:
                for warning in s["warnings"]:
                    print(f"경고({s['repo']}): {warning}", file=sys.stderr)
        elif args.cmd == "plan":
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
            s = write_result(Path(args.de13), Path(args.result), Path(args.ledger), changes, dry_run=args.dry_run)
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
                print(f"  경고: 이어받을 판단(제외·PM 확인)을 이번 판정이 버린 행 — {', '.join(s['inherit_dropped'])}")
    except InputError as exc:
        print(f"test-evidence: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"test-evidence: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
