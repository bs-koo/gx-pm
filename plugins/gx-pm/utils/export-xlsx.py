#!/usr/bin/env python3
"""
gx-pm 산출물 마크다운 표 → xlsx 변환 유틸리티

Usage:
    python export-xlsx.py <input.md> [--output output.xlsx]
    python export-xlsx.py --dir <폴더> [--output output.xlsx]

Examples:
    python export-xlsx.py ACT-요구사항정의서.md
    python export-xlsx.py --dir ../결과물/ --output ACT-산출물.xlsx
    python export-xlsx.py ACT-요구사항정의서.md ACT-화면목록표.md --output merged.xlsx
"""

import sys
import re
import os
import io
import argparse
from pathlib import Path

# 목록 표지는 마커 뒤에 공백이 온다("- 항목", "1. 항목").
# 공백을 요구해야 볼드 강조("**부적합 목록**")를 목록으로 오인하지 않는다.
_BULLET_PREFIX = re.compile(r"^([-*+]|\d+\.)\s")

# Windows cp949 인코딩 문제 방지
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ──────────────────────────────────────
# 의존성 자동 설치
# ──────────────────────────────────────

def ensure_openpyxl():
    try:
        import openpyxl
        return openpyxl
    except ImportError:
        import subprocess
        print("[gx-pm] openpyxl 설치 중...", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "openpyxl", "-q"],
            stdout=subprocess.DEVNULL,
        )
        import openpyxl
        return openpyxl


# ──────────────────────────────────────
# 산출물별 컬럼 매핑 (공공 양식 순서)
# ──────────────────────────────────────

DOCUMENT_PROFILES = {
    "개정이력": {
        "sheet_name": "개정이력",
        # 참조 양식은 표 위에 이 제목을 병합 셀로 얹는다. 이 키가 있는 프로필만
        # 시트 1행에 제목을 쓰고 표를 2행부터 시작한다 — 다른 산출물은 건드리지 않는다.
        "sheet_title": "개 정 이 력",
        # 컬럼 정본은 templates/revision-history.md 의 「개정이력 컬럼 (정본)」 절이다.
        "columns": [[
            "버전", "개정일", "개정 사유", "개정 내용", "작성자", "승인자",
        ]],
        "merge_columns": [],
        # "개정 사유" 는 값이 "신규"(2자)뿐인 경우가 많아 자동 계산 너비가
        # 지나치게 좁아진다 — 참조 양식만큼 최소 너비를 강제한다.
        "min_widths": {"개정 사유": 14, "개정일": 12, "작성자": 12, "승인자": 12},
        # 서술형 열만 좌측 정렬, 나머지(버전·개정일 등)는 중앙 정렬.
        "left_align": ["개정 내용"],
    },
    "요구사항정의서": {
        "sheet_name": "요구사항 명세",
        # 컬럼 정본은 templates/AN-02-requirements-definition.md 의
        # 「본문 컬럼 (정본)」 절이다. 여기서 이름을 바꾸면 계약 테스트가 잡는다.
        "columns": [[
            "번호", "요구사항ID", "대분류", "중분류", "요구사항명",
            "요구사항 상세내용", "비고", "상태", "요구사항 근거", "변경 근거",
        ]],
        "merge_columns": ["대분류", "중분류"],
        # "요구사항 근거"·"변경 근거"는 사용자 요청상 중앙정렬 후보였으나, 문장형
        # 근거("과업지시서 BR-01" 등)가 들어가 중앙정렬하면 읽기 어려워 좌측에 남긴다.
        "left_align": [
            "요구사항명", "요구사항 상세내용", "비고", "요구사항 근거", "변경 근거",
        ],
        # 값 정본은 templates/AN-02-requirements-definition.md 「상태 판정」이다.
        # 여기 목록이 정본과 갈라지면 test_드롭다운_값이_템플릿_정본과_같다 가 잡는다.
        "dropdowns": [{"상태": ["유지", "변경", "삭제"]}],
    },
    "기능명세서": {
        "sheet_name": "기능명세",
        # 컬럼 정본은 templates/AN-03-function-spec.md 의 「본문 컬럼 (정본)」 절이다.
        "columns": [[
            "기능ID", "대분류", "중분류", "기능명", "기능설명",
            "입력항목", "처리내용(로직)", "출력결과", "연계요구사항ID", "비고",
        ]],
        "merge_columns": ["대분류", "중분류"],
        "left_align": [
            "기능명", "기능설명", "입력항목", "처리내용(로직)", "출력결과", "비고",
        ],
    },
    "테이블정의서": {
        "sheet_name": "테이블정의",
        # 컬럼 정본은 templates/DE-08-table-definition.md 의 「본문 컬럼 (정본)」 절이다.
        "columns": [[
            "테이블명", "테이블 논리명", "컬럼명", "컬럼 논리명",
            "데이터타입", "길이", "소수점", "PK", "NotNull", "기본값",
            "구분", "표준 판정", "표준 권고명", "근거", "연계기능ID",
        ]],
        "merge_columns": ["테이블명"],
        "left_align": ["테이블 논리명", "컬럼 논리명", "표준 권고명", "근거"],
        "dropdowns": [{
            "구분": ["기존", "신규", "변경"],
            "표준 판정": ["표준준수", "현행유지", "신규적용"],
        }],
    },
    "단위테스트계획서": {
        "sheet_name": "단위테스트계획",
        # 컬럼 정본은 templates/DE-13-unit-test-plan.md 의 「본문 컬럼 (정본)」 절이다.
        "columns": [[
            "테스트ID", "연계기능ID", "연계요구사항ID", "요구사항명",
            "사전조건", "입력", "기대결과", "사후조건", "의존성",
            "테스트담당자", "수행일", "결과",
        ]],
        "merge_columns": [],
        "left_align": ["요구사항명", "사전조건", "입력", "기대결과", "사후조건"],
        # 계획서는 `결과` 가 공란이 정상이므로 allow_blank 로 건다.
        "dropdowns": [{"결과": ["Pass", "Fail"]}],
    },
    "확인요청서": {
        # 5종 산출물이 아니라 미결사항 관리대장이라 산출물 코드를 갖지 않는다.
        # 컬럼 정본은 templates/confirmation-request.md 의 네 「본문 컬럼 (정본)」 절이다.
        # 현역 프로필 중 유일하게 컬럼 세트가 넷이다 — sheet_names 가 없으면
        # 둘째 시트부터 "확인요청서_1" 로 밀려 개정이력_1~_4 와 같은 모양이 된다.
        "sheet_name": "안내",
        "sheet_names": ["안내", "가정 확인", "미확정 확인", "요청 이력"],
        "columns": [
            ["구분", "안내"],
            ["#", "차수", "위치", "AI 가 정한 값", "근거", "판정", "정정값", "비고"],
            ["#", "차수", "위치", "무엇이 없나", "왜 못 정했나", "상태", "응답", "확정일"],
            ["차수", "발행일", "위치", "물은 것", "받은 답", "처리"],
        ],
        "merge_columns": [],
        "left_align": [
            "안내", "위치", "근거", "비고", "무엇이 없나", "왜 못 정했나", "응답",
            "물은 것", "받은 답",
        ],
        "dropdowns": [
            {},
            {"판정": ["맞음", "수정", "미확정으로"]},
            {"상태": ["대기", "확정", "해당없음"]},
            {},
        ],
        # 사람이 채울 칸. 안내·요청 이력은 읽기 전용이라 비운다.
        "input_columns": [
            [],
            ["판정", "정정값", "비고"],
            ["상태", "응답", "확정일"],
            [],
        ],
    },
    "추적매트릭스": {
        "sheet_name": "추적매트릭스",
        # 컬럼 정본은 templates/AN-05-traceability-matrix.md 의
        # 「본문 컬럼 (정본)」 절이다. 양방향 계약 테스트가 묶고 있다.
        "columns": [[
            "요구사항ID", "요구사항명", "상태", "기능ID", "기능명",
            "테이블·컬럼", "테스트 수", "Pass/Fail", "누락",
        ]],
        "merge_columns": ["요구사항ID"],
        "left_align": ["요구사항명", "기능명", "테이블·컬럼", "누락"],
        # `누락` 은 `실패 3건` 처럼 가변값이 섞여 드롭다운을 걸지 않는다.
        "dropdowns": [{"상태": ["유지", "변경", "삭제"]}],
    },
}


# ──────────────────────────────────────
# 마크다운 파싱
# ──────────────────────────────────────

def detect_document_type(filename: str) -> str | None:
    """파일명에서 산출물 유형을 감지"""
    for key in DOCUMENT_PROFILES:
        if key in filename:
            return key
    return None


def parse_markdown_tables(text: str) -> list[tuple[str, list[str]]]:
    """마크다운 텍스트에서 (제목, 표 라인 리스트) 쌍을 추출"""
    tables = []
    lines = text.split("\n")
    current_table: list[str] = []
    table_title = ""

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if not current_table:
                # 표 직전의 제목(### 등)을 찾는다.
                # 코드펜스(``` / ~~~) 블록은 여는/닫는 펜스 사이를 통째로
                # 건너뛴다 — 탐색 창(budget)도 소모하지 않는다. 코드 블록이
                # 길어도 그 위의 상위 헤딩까지 거슬러 올라갈 수 있어야 한다.
                j = i - 1
                budget = 30
                while j >= 0 and budget > 0:
                    candidate = lines[j].strip()
                    if candidate.startswith(("```", "~~~")):
                        fence = candidate[:3]
                        j -= 1
                        while j >= 0 and not lines[j].strip().startswith(fence):
                            j -= 1
                        j -= 1
                        continue
                    budget -= 1
                    if candidate.startswith("#"):
                        table_title = candidate.lstrip("#").strip()
                        break
                    # 인용문·표·목록은 제목이 아니다 — 계속 거슬러 올라간다.
                    # 목록 마커는 뒤에 공백이 온다("- 항목"). 공백이 없으면
                    # 볼드 강조("**부적합 목록**")이므로 라벨로 인정한다.
                    if candidate.startswith((">", "|")) or _BULLET_PREFIX.match(candidate):
                        j -= 1
                        continue
                    # 산문 한 줄이 시트명이 되는 것을 막는다.
                    # 짧고 문장으로 끝나지 않는 라인만 라벨로 인정한다.
                    if candidate and len(candidate) <= 30 and not candidate.endswith((".", "다", "요", "!", "?")):
                        table_title = candidate
                        break
                    j -= 1
            current_table.append(stripped)
        else:
            if current_table:
                tables.append((table_title, current_table))
                current_table = []
                table_title = ""

    if current_table:
        tables.append((table_title, current_table))

    return tables


def strip_markdown(text: str) -> str:
    """셀 안의 마크다운 강조 표기를 걷어낸다.

    엑셀은 마크다운을 모른다. `**PM 이 답합니다.**` 를 그대로 쓰면 별표가
    글자로 보인다 — 사람이 읽는 안내 시트에서 특히 나쁘다. 굵게·기울임·
    코드 표기를 걷어내고 알맹이만 남긴다. `[가정]` 같은 대괄호 표식은
    산출물의 뜻이므로 건드리지 않는다.
    """
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    # 굵게를 먼저 걷어낸 뒤라 남은 홑표는 기울임이다. 앞뒤로 같은 기호가
    # 붙지 않은 것만 잡아 `a*b*c` 같은 수식 표기를 건드리지 않는다.
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)
    # 밑줄 기울임은 낱말 안(`TB_USER_ID`)에서 쓰이므로 낱말 경계를 요구한다.
    text = re.sub(r"(?<![\w_])_([^_\n]+?)_(?![\w_])", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def table_lines_to_rows(table_lines: list[str]) -> list[list[str]]:
    """마크다운 표 라인 → 2D 배열 (구분선 제거)"""
    rows = []
    for line in table_lines:
        # 구분선 ( |---|---| ) 건너뛰기
        cells = [strip_markdown(c.strip()) for c in line.split("|")[1:-1]]
        if cells and not all(re.match(r"^[\s\-:]+$", c) for c in cells):
            rows.append(cells)
    return rows


def is_metadata_table(rows: list[list[str]]) -> bool:
    """메타 정보 표(항목/내용 2열, 판정기준 등)인지 판별 — 산출물 데이터 표와 분리"""
    if not rows:
        return True
    header = [h.strip() for h in rows[0]]
    # 2열짜리 "항목 | 내용" 스타일의 문서 헤더 메타 표
    if len(header) == 2 and header[0] in ("항목", "항목명"):
        return True
    # 2열짜리 참조 표 (판정 | 의미, 키워드 | 값 등)
    if len(header) == 2 and header[0] in ("판정", "키워드", "유형"):
        return True
    # 데이터 행이 2개 이하 (헤더 포함 총 3행 이하)이면 의미 없는 소형 표
    if len(rows) <= 2 and len(header) <= 3:
        return True
    return False


# ──────────────────────────────────────
# xlsx 생성
# ──────────────────────────────────────

def _header_key(rows: list[list[str]]) -> str:
    """표의 헤더를 정규화한 키 — 동일 구조 표 병합용"""
    if not rows:
        return ""
    return "|".join(h.strip() for h in rows[0])


# 프로필 컬럼과 이만큼 일치해야 산출물 본문 표로 본다.
# 미만이면 근거·통계 같은 보조 표이므로 시트명도 컬럼 순서도 물려받지 않는다.
_MATCH_THRESHOLD = 0.5


def resolve_doc_type(header: list[str], file_doc_type: str | None) -> str | None:
    """이 표 하나에 쓸 프로필을 고른다.

    `detect_document_type` 은 **파일명**만 본다. 그런데 개정이력은 독립 파일이 아니라
    5종 산출물 **안에 들어 있는 표**다. 파일명으로만 고르면 `REB-요구사항정의서.md`
    안의 개정이력 표가 `요구사항정의서` 프로필로 처리되어, `개정이력` 프로필의
    `sheet_title`·`min_widths`·`left_align` 이 하나도 걸리지 않는다 — 그 프로필이
    사실상 죽은 코드가 된다.

    그래서 헤더로 한 번 더 판정한다. 헤더가 `개정이력` 컬럼 정본과 임계값 이상
    맞으면 그 표만 `개정이력` 프로필로 처리하고, 아니면 파일명이 정한 것을 쓴다.
    """
    if not header:
        return file_doc_type
    index, _ = _best_column_set(header, "개정이력")
    if index is not None:
        return "개정이력"
    return file_doc_type


def _best_column_set(
    header: list[str], doc_type: str | None
) -> tuple[int | None, list[str]]:
    """헤더에 가장 잘 맞는 프로필 컬럼 세트의 (인덱스, 컬럼 목록)을 돌려준다.

    시트명 결정(_matched_set_index)과 컬럼 재배열(_reorder_columns)이 같은 판단을
    필요로 한다. 두 벌로 두면 한쪽 임계값만 고쳤을 때 시트가 A 세트의 이름을 달고
    B 세트의 순서로 나온다 — 판단은 여기 한 곳에만 둔다.
    """
    if not doc_type or doc_type not in DOCUMENT_PROFILES or not header:
        return None, []
    있는_컬럼 = set(header)
    best_index: int | None = None
    best_columns: list[str] = []
    best_ratio = 0.0
    for index, target in enumerate(DOCUMENT_PROFILES[doc_type]["columns"]):
        if not target:
            continue
        ratio = len([c for c in target if c in 있는_컬럼]) / len(target)
        if ratio >= _MATCH_THRESHOLD and ratio > best_ratio:
            best_index, best_columns, best_ratio = index, target, ratio
    return best_index, best_columns


def _matched_set_index(rows: list[list[str]], doc_type: str | None) -> int | None:
    """이 표가 산출물 본문 표라면 매칭된 컬럼 세트의 인덱스를, 아니면 None 을 반환한다."""
    if not rows:
        return None
    index, _ = _best_column_set([h.strip() for h in rows[0]], doc_type)
    return index


def _reorder_columns(
    rows: list[list[str]], doc_type: str | None
) -> list[list[str]]:
    """DOCUMENT_PROFILES에 정의된 공공 양식 컬럼 순서로 재배열한다.

    프로필에 정의된 컬럼이 마크다운 헤더에 존재하면 해당 순서로 재배열하고,
    프로필에 없는 추가 컬럼은 뒤에 붙인다.
    매칭되는 컬럼이 절반 미만이면 재배열하지 않고 원본을 반환한다.
    """
    if not rows:
        return rows

    header = [h.strip() for h in rows[0]]

    # 산출물이 여러 시트 구조를 가질 수 있으므로 가장 잘 맞는 컬럼 세트를 고른다.
    # 판단은 _best_column_set 한 곳에만 있다 — 시트명 결정과 같은 세트를 쓴다.
    _, target_columns = _best_column_set(header, doc_type)
    if not target_columns:
        return rows

    # 마크다운 헤더 → 인덱스 매핑
    header_index: dict[str, int] = {}
    for idx, col in enumerate(header):
        header_index[col] = idx

    ordered_indices = [header_index[c] for c in target_columns if c in header_index]

    # 프로필에 없는 추가 컬럼을 뒤에 붙인다
    used = set(ordered_indices)
    for idx in range(len(header)):
        if idx not in used:
            ordered_indices.append(idx)

    # 모든 행에 재배열 적용
    reordered: list[list[str]] = []
    for row in rows:
        new_row = []
        for idx in ordered_indices:
            new_row.append(row[idx] if idx < len(row) else "")
        reordered.append(new_row)

    return reordered


def merge_ranges(
    rows: list[list[str]], merge_columns: list[str]
) -> list[tuple[int, int, int]]:
    """연속으로 같은 값이 이어지는 칸을 세로 병합 범위로 돌려준다.

    반환값은 (0기준 열 인덱스, 시작 시트행, 끝 시트행) 이다.
    rows[0] 이 헤더라 시트 1행이고, rows[i] 는 시트 i+1 행이다.

    빈 값은 묶지 않는다 — 빈칸이 이어지는 것은 "같은 값" 이 아니라 "값이 없는 것" 이다.
    떨어져 있는 같은 값도 묶지 않는다 — 정렬이 깨진 표를 이어 붙이면 없는 사실을 만든다.
    """
    if len(rows) < 3:  # 헤더 + 데이터 2행 미만이면 묶을 것이 없다
        return []

    header = [h.strip() for h in rows[0]]
    ranges: list[tuple[int, int, int]] = []

    for col_name in merge_columns:
        if col_name not in header:
            continue
        col = header.index(col_name)

        start = 1
        while start < len(rows):
            value = rows[start][col].strip() if col < len(rows[start]) else ""
            end = start
            while end + 1 < len(rows):
                nxt = rows[end + 1][col].strip() if col < len(rows[end + 1]) else ""
                if nxt != value:
                    break
                end += 1
            if value and end > start:
                ranges.append((col, start + 1, end + 1))
            start = end + 1

    return ranges


INPUT_FILL_RGB = "FFF9E3"


def _apply_input_fill(ws, doc_profile, set_index, header_names, first_row, last_row):
    """사람이 채울 칸에 연노랑 배경을 준다.

    확인요청서는 8열 중 3열만 입력란이라 색이 없으면 어디를 채울지 모른다.
    드롭다운이 걸린 열과 겹치지만, 드롭다운이 없는 `정정값`·`응답` 도 칠해야
    "여기 뭔가 써야 하는구나" 가 보인다.

    **헤더는 칠하지 않는다.** 헤더에는 이미 헤더 색이 있고, 덮으면 표 머리가
    사라져 보인다. 호출부가 데이터 첫 행부터 넘긴다.
    """
    if not doc_profile or set_index is None or last_row < first_row:
        return
    목록 = doc_profile.get("input_columns") or []
    if set_index >= len(목록):
        return

    from openpyxl.styles import PatternFill
    from openpyxl.utils import get_column_letter as _letter

    fill = PatternFill("solid", start_color=INPUT_FILL_RGB, end_color=INPUT_FILL_RGB)
    for 컬럼 in 목록[set_index] or []:
        if 컬럼 not in header_names:
            continue
        letter = _letter(header_names.index(컬럼) + 1)
        for row in range(first_row, last_row + 1):
            ws[f"{letter}{row}"].fill = fill


def _apply_dropdowns(ws, doc_profile, set_index, header_names, first_row, last_row):
    """열거형 열에 데이터 검증(드롭다운)을 건다.

    값 목록은 DOCUMENT_PROFILES 의 `dropdowns` 에서 온다. `columns` 와 같은
    인덱스의 리스트라 시트가 여럿인 프로필도 시트마다 다른 목록을 갖는다.

    **범위는 데이터 행만이다.** 열 전체(`C:C`)로 걸면 헤더와 제목 병합 셀까지
    검사 대상이 되어 목록 밖 값이라며 막힌다. 개정이력처럼 표 위 제목 행이 있는
    시트는 `row_offset` 만큼 밀려 있으므로 호출부가 보정한 행 번호를 넘긴다.

    `allow_blank` 를 켠다 — DE-13 `결과` 는 계획서 단계에서 전건 공란이 정상이다.
    """
    if not doc_profile or set_index is None or last_row < first_row:
        return
    목록 = doc_profile.get("dropdowns") or []
    if set_index >= len(목록):
        return

    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.utils import get_column_letter as _letter

    for 컬럼, 값들 in (목록[set_index] or {}).items():
        if 컬럼 not in header_names or not 값들:
            continue
        letter = _letter(header_names.index(컬럼) + 1)
        dv = DataValidation(
            type="list",
            formula1='"{}"'.format(",".join(값들)),
            allow_blank=True,
            showErrorMessage=True,
        )
        dv.errorTitle = "값이 목록에 없습니다"
        dv.error = "{} 은(는) 다음 중 하나여야 합니다: {}".format(
            컬럼, " / ".join(값들)
        )
        ws.add_data_validation(dv)
        dv.add(f"{letter}{first_row}:{letter}{last_row}")


def _column_width(values: list[str], min_width: int = 0) -> int:
    """열의 자동 계산 너비와 최소 너비 중 큰 값을 60 이내로 돌려준다.

    자동 계산은 각 값의 표시 폭(전각 2 · 반각 1)에 여백 4를 더한 값이다.
    `min_width` 는 DOCUMENT_PROFILES 의 `min_widths` 에서 온다 — "신규"처럼
    짧은 값만 있는 열이 지나치게 좁아지는 것을 막는다.
    """
    max_len = 0
    for value in values:
        length = sum(2 if ord(c) > 127 else 1 for c in str(value))
        max_len = max(max_len, length)
    return min(max(max_len + 4, min_width), 60)


def create_xlsx(
    file_tables: list[tuple[str, list[tuple[str, list[str]]]]],
    output_path: str,
) -> str:
    """
    file_tables: [(파일명, [(표제목, 표라인[]), ...]), ...]

    동일 파일 내 같은 컬럼 구조의 표는 하나의 시트로 병합한다.
    """
    openpyxl = ensure_openpyxl()
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # 스타일 정의
    header_font = Font(name="맑은 고딕", bold=True, size=10)
    header_fill = PatternFill(
        start_color="D9E2F3", end_color="D9E2F3", fill_type="solid"
    )
    cell_font = Font(name="맑은 고딕", size=10)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    # 서술형 열(left_align 목록)만 좌측, 나머지 데이터 열은 중앙 정렬한다.
    wrap_align_left = Alignment(wrap_text=True, vertical="top", horizontal="left")
    wrap_align_center = Alignment(wrap_text=True, vertical="top", horizontal="center")
    header_align = Alignment(
        wrap_text=True, vertical="center", horizontal="center"
    )
    title_font = Font(name="맑은 고딕", bold=True, size=14)
    title_align = Alignment(horizontal="center", vertical="center")

    for filename, tables in file_tables:
        file_doc_type = detect_document_type(filename)

        # ── 1단계: 유효한 표만 추출하고, 동일 헤더끼리 병합 ──
        merged: dict[str, list[list[str]]] = {}  # header_key → 병합된 행들
        merged_titles: dict[str, str] = {}  # header_key → 대표 제목

        for title, table_lines in tables:
            rows = table_lines_to_rows(table_lines)
            if not rows or is_metadata_table(rows):
                continue

            key = _header_key(rows)
            if key not in merged:
                merged[key] = list(rows)  # 헤더 포함
                merged_titles[key] = title
            else:
                # 헤더(첫 행) 제외하고 데이터만 추가
                merged[key].extend(rows[1:])

        # ── 2단계: 컬럼 재배열 + 시트 생성 ──
        for key, rows in merged.items():
            # 표마다 프로필을 다시 고른다. 개정이력은 5종 산출물 안에 들어 있는
            # 표라, 파일명으로만 고르면 부모 문서의 프로필에 묻힌다.
            doc_type = resolve_doc_type(rows[0] if rows else [], file_doc_type)

            rows = _reorder_columns(rows, doc_type)
            title = merged_titles[key]

            # 시트 이름 결정
            set_index = _matched_set_index(rows, doc_type)
            doc_profile = DOCUMENT_PROFILES.get(doc_type) if doc_type else None
            if set_index is not None:
                # 본문 데이터 표 — 공공 양식 시트명을 쓴다
                profile = DOCUMENT_PROFILES[doc_type]
                names = profile.get("sheet_names")
                base_name = (
                    names[set_index]
                    if names and set_index < len(names)
                    else profile["sheet_name"]
                )
            elif title:
                # 근거·통계 등 보조 표 — 마크다운 제목을 시트명으로 쓴다
                base_name = title
            else:
                base_name = "Data"

            # 시트 이름 정제 (Excel 제한: 31자, 특수문자 금지)
            sheet_name = re.sub(r'[\\/*?\[\]:]', "", base_name)[:31]
            if not sheet_name:
                sheet_name = "Data"

            # 중복 방지
            original = sheet_name
            dup = 1
            while sheet_name in wb.sheetnames:
                sheet_name = f"{original[:27]}_{dup}"
                dup += 1

            ws = wb.create_sheet(title=sheet_name)

            # 표 위 제목 행 — sheet_title 이 있는 프로필(개정이력)의 본문 표에만 붙는다.
            # 제목 행이 생기면 헤더가 한 행 밀리므로, 아래 병합·고정·필터가 전부
            # row_offset 만큼 보정해야 한다.
            sheet_title = doc_profile.get("sheet_title") if (doc_profile and set_index is not None) else None
            row_offset = 1 if sheet_title else 0
            if sheet_title:
                last_col_letter = get_column_letter(len(rows[0]))
                ws.merge_cells(f"A1:{last_col_letter}1")
                title_cell = ws["A1"]
                title_cell.value = sheet_title
                title_cell.font = title_font
                title_cell.alignment = title_align

            left_align_cols = set(doc_profile.get("left_align", [])) if doc_profile else set()
            min_widths = doc_profile.get("min_widths", {}) if doc_profile else {}
            header_names = rows[0]

            # 데이터 쓰기
            for row_idx, row in enumerate(rows):
                sheet_row = row_idx + 1 + row_offset
                for col_idx, value in enumerate(row):
                    cell = ws.cell(
                        row=sheet_row, column=col_idx + 1, value=value
                    )
                    cell.border = thin_border

                    if row_idx == 0:
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_align
                    else:
                        cell.font = cell_font
                        col_name = header_names[col_idx] if col_idx < len(header_names) else ""
                        cell.alignment = (
                            wrap_align_left if col_name in left_align_cols else wrap_align_center
                        )

            # 연속 동일값 세로 병합 (참조 양식 형태) — 가로도 중앙 정렬한다.
            if doc_type and doc_type in DOCUMENT_PROFILES:
                for col, row_start, row_end in merge_ranges(
                    rows, DOCUMENT_PROFILES[doc_type].get("merge_columns", [])
                ):
                    row_start += row_offset
                    row_end += row_offset
                    letter = get_column_letter(col + 1)
                    ws.merge_cells(f"{letter}{row_start}:{letter}{row_end}")
                    ws[f"{letter}{row_start}"].alignment = Alignment(
                        wrap_text=True, vertical="center", horizontal="center"
                    )

            # 열 너비 자동 조정 (min_widths 가 있으면 자동 계산값과 비교해 큰 쪽)
            for col_idx in range(len(rows[0])):
                col_letter = get_column_letter(col_idx + 1)
                col_name = header_names[col_idx] if col_idx < len(header_names) else ""
                values = [row[col_idx] for row in rows if col_idx < len(row)]
                ws.column_dimensions[col_letter].width = _column_width(
                    values, min_widths.get(col_name, 0)
                )

            # 헤더 행 고정 + 필터 — 제목 행이 있으면 한 행씩 밀어 제목은 제외한다.
            header_row = 1 + row_offset
            last_row = len(rows) + row_offset
            last_col_letter = get_column_letter(len(rows[0]))
            ws.freeze_panes = f"A{header_row + 1}"
            ws.auto_filter.ref = f"A{header_row}:{last_col_letter}{last_row}"

            # 열거형 열에 드롭다운(데이터 검증)을 건다.
            # 범위는 데이터 행만이다 — 열 전체로 걸면 제목 병합 셀과 헤더까지
            # 검사해서 목록 밖 값이라며 막는다. row_offset 만큼 밀려 있다.
            _apply_dropdowns(
                ws, doc_profile, set_index, header_names, header_row + 1, last_row
            )
            _apply_input_fill(
                ws, doc_profile, set_index, header_names, header_row + 1, last_row
            )

    if not wb.sheetnames:
        ws = wb.create_sheet(title="빈 시트")
        ws.cell(row=1, column=1, value="표 데이터가 없습니다")

    wb.save(output_path)
    return output_path, len(wb.sheetnames)


# ──────────────────────────────────────
# 메인
# ──────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="gx-pm 마크다운 산출물 → xlsx 변환",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python export-xlsx.py ACT-요구사항정의서.md
  python export-xlsx.py --dir ../결과물/
  python export-xlsx.py file1.md file2.md --output merged.xlsx
  python export-xlsx.py --separate --output xlsx ACT-확인요청서.md
        """,
    )
    parser.add_argument(
        "files", nargs="*", help="변환할 마크다운 파일 (복수 가능)"
    )
    parser.add_argument(
        "--dir", help="마크다운 파일이 있는 폴더 (폴더 내 모든 .md 처리)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="출력 경로. 합본이면 xlsx 파일 경로, --separate 면 출력 폴더 "
        "(미지정 시 합본은 자동 생성, --separate 는 .md 옆)",
    )
    parser.add_argument(
        "--separate",
        action="store_true",
        help="각 md 파일을 별도 xlsx로 생성 (기본: 하나의 xlsx에 통합)",
    )

    args = parser.parse_args()

    # 입력 파일 수집
    md_files: list[Path] = []

    if args.dir:
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            print(f"오류: '{args.dir}'은(는) 유효한 폴더가 아닙니다", file=sys.stderr)
            sys.exit(1)
        md_files = sorted(dir_path.glob("*.md"))
    elif args.files:
        for f in args.files:
            p = Path(f)
            if p.is_file():
                md_files.append(p)
            else:
                print(f"경고: '{f}' 파일을 찾을 수 없습니다", file=sys.stderr)
    else:
        # stdin에서 읽기
        print("마크다운 텍스트를 입력하세요 (Ctrl+D로 종료):", file=sys.stderr)
        text = sys.stdin.read()
        tables = parse_markdown_tables(text)
        out = args.output or "output.xlsx"
        result, total_sheets = create_xlsx([("stdin", tables)], out)
        print(f"✅ 생성 완료: {result} ({total_sheets}개 시트)")
        return

    if not md_files:
        print("오류: 변환할 .md 파일이 없습니다", file=sys.stderr)
        sys.exit(1)

    if args.separate:
        # 각 파일을 별도 xlsx로 생성.
        # --separate 는 필연적으로 결과가 여럿이라 --output 은 파일명일 수 없다.
        # 출력 **폴더**로 해석한다 — 프로젝트 폴더 규약의 xlsx/ 가 그 자리다
        # (templates/project-profile-schema.md).
        out_dir = Path(args.output) if args.output else None
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
        for md_file in md_files:
            text = md_file.read_text(encoding="utf-8")
            tables = parse_markdown_tables(text)
            if out_dir is not None:
                out = out_dir / f"{md_file.stem}.xlsx"
            else:
                out = md_file.with_suffix(".xlsx")
            if tables:
                result, total_sheets = create_xlsx([(md_file.name, tables)], str(out))
                print(f"✅ {md_file.name} → {result} ({total_sheets}개 시트)")
            else:
                print(f"⚠ {md_file.name}: 표가 없어 건너뜁니다")
    else:
        # 통합 xlsx 생성
        all_tables = []
        for md_file in md_files:
            text = md_file.read_text(encoding="utf-8")
            tables = parse_markdown_tables(text)
            if tables:
                all_tables.append((md_file.name, tables))

        if not all_tables:
            print("오류: 어떤 파일에서도 표를 찾지 못했습니다", file=sys.stderr)
            sys.exit(1)

        if args.output:
            out = args.output
        else:
            # 첫 파일의 시스템코드에서 출력 파일명 생성
            first_name = md_files[0].stem
            prefix_match = re.match(r"^([A-Z]+)-", first_name)
            prefix = prefix_match.group(1) if prefix_match else "output"
            out = f"{prefix}-산출물.xlsx"

        result, total_sheets = create_xlsx(all_tables, out)
        print(f"✅ 생성 완료: {result} ({total_sheets}개 시트)")


if __name__ == "__main__":
    main()
