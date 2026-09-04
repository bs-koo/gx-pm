"""테스트 공용 헬퍼.

utils/export-xlsx.py 는 파일명에 하이픈이 있어 일반 import 가 불가능하다.
파일명은 README·approval-protocol 에 CLI 경로로 문서화돼 있어 바꾸지 않고,
importlib 로 로드한다.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXPORT_SCRIPT = PLUGIN_ROOT / "utils" / "export-xlsx.py"
REPO_ROOT = PLUGIN_ROOT.parent.parent

_cached_module: ModuleType | None = None


def load_export_module() -> ModuleType:
    """export-xlsx.py 를 모듈로 로드한다. 한 번 로드하면 캐싱한다."""
    global _cached_module
    if _cached_module is not None:
        return _cached_module
    spec = importlib.util.spec_from_file_location("gx_export_xlsx", EXPORT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈 스펙을 만들 수 없습니다: {EXPORT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _cached_module = module
    return module


def read_docs() -> list[tuple[Path, str]]:
    """플러그인의 모든 마크다운 문서를 (경로, 본문) 쌍으로 반환한다.

    .omc·.dev 는 런타임 상태 디렉터리라 검사 대상이 아니다. .dev 는 훅이 남기는
    의사결정 로그라 아직 만들지 않은 커맨드 이름이 선택지로 그대로 실린다.
    tests/fixtures 는 규칙을 시험하기 위한 입력이라 검사 대상이 아니다 —
    일부러 잘못된 예시를 담는 픽스처가 계약 검사에 걸리면 안 된다.
    저장소 루트 README 도 포함한다 — 사용자의 첫 접점이라 다른 문서와 같은
    계약 검사(개명·백틱·정본 참조 등)를 받아야 한다.
    archive/ 는 커맨드에서 내린 산출물의 보관소라 검사 대상이 아니다.
    """
    docs = []
    for path in sorted(PLUGIN_ROOT.rglob("*.md")):
        if ".omc" in path.parts:
            continue
        if ".dev" in path.parts:
            continue  # .dev 는 훅이 쓰는 런타임 기록(의사결정 로그)이라 검사 대상이 아니다
        if "archive" in path.parts:
            continue  # archive/ 는 보관소다. 옛 컬럼·옛 ID 규칙이 새 계약을 깨뜨린다
        if path.relative_to(PLUGIN_ROOT).parts[:2] == ("tests", "fixtures"):
            continue  # tests/fixtures 는 검사 대상이 아니라 검사 도구다 — 다른 위치의
            # "fixtures" 디렉터리(있다면)는 여전히 검사 대상이어야 한다
        docs.append((path, path.read_text(encoding="utf-8")))
    root_readme = REPO_ROOT / "README.md"
    if root_readme.exists():
        docs.append((root_readme, root_readme.read_text(encoding="utf-8")))
    return docs


def doc_label(path: Path) -> Path:
    """read_docs() 가 반환한 경로를 subTest 표시용 상대경로로 변환한다.

    저장소 루트 README 는 PLUGIN_ROOT 바깥(REPO_ROOT 직속)이라
    path.relative_to(PLUGIN_ROOT) 가 ValueError 를 던진다.
    """
    try:
        return path.relative_to(PLUGIN_ROOT)
    except ValueError:
        return path.relative_to(REPO_ROOT)


def strip_fences(text: str) -> str:
    """``` 코드펜스 안을 걷어낸다.

    펜스 안은 사용자에게 그대로 출력되는 메시지라 백틱이 리터럴로 렌더링된다.
    거기까지 백틱을 강요하면 사용자 화면에 백틱이 노출된다 — 규약이 아니라 사고다.
    """
    남긴줄: list[str] = []
    열린펜스: str | None = None
    for line in text.splitlines():
        표시 = line.strip()
        if 열린펜스 is None:
            if 표시.startswith(("```", "~~~")):
                열린펜스 = 표시[:3]
                continue
            남긴줄.append(line)
        elif 표시.startswith(열린펜스):
            열린펜스 = None
    return "\n".join(남긴줄)


def skill_names() -> set[str]:
    return {d.name for d in (PLUGIN_ROOT / "skills").iterdir() if d.is_dir()}


def command_names() -> set[str]:
    return {p.stem for p in (PLUGIN_ROOT / "commands").glob("*.md")}


def template_names() -> set[str]:
    return {p.name for p in (PLUGIN_ROOT / "templates").glob("*.md")}


def archived_skill_names() -> set[str]:
    """archive/skills 에 보관된 스킬 이름.

    CHANGELOG 는 내린 스킬을 이름째 인용한다 — 그걸 오타로 볼 수는 없다.
    그렇다고 CHANGELOG 를 검사에서 통째로 빼면 진짜 오타도 같이 놓친다.
    보관 목록을 따로 돌려주어, 이력 문서에서만 이 이름들을 허용한다.
    """
    보관 = PLUGIN_ROOT / "archive" / "skills"
    if not 보관.is_dir():
        return set()
    return {d.name for d in 보관.iterdir() if d.is_dir()}


def archived_template_names() -> set[str]:
    """archive/templates 에 보관된 템플릿 파일명. 사유는 archived_skill_names 참조."""
    보관 = PLUGIN_ROOT / "archive" / "templates"
    if not 보관.is_dir():
        return set()
    return {p.name for p in 보관.glob("*.md")}


def parse_column_ssot(template_name: str, section_title: str) -> list[str]:
    """템플릿의 지정 절에서 컬럼 정본 목록을 뽑는다.

    표는 `| # | 컬럼 | 규칙 |` 형태이고 둘째 칸이 컬럼명이다.
    절 제목은 정확히 일치해야 한다 — 제목이 바뀌면 조용히 빈 목록을 내는 대신
    호출부의 길이 검사가 실패하게 둔다.
    """
    import re

    text = (PLUGIN_ROOT / "templates" / template_name).read_text(encoding="utf-8")
    구간 = re.search(
        rf"^#{{1,4}} {re.escape(section_title)}$(.*?)(?=^#{{1,4}} |\Z)",
        text, re.M | re.S,
    )
    if 구간 is None:
        return []
    컬럼: list[str] = []
    for 줄 in 구간.group(1).splitlines():
        벗긴줄 = 줄.strip()
        if not (벗긴줄.startswith("|") and 벗긴줄.endswith("|")):
            continue
        칸 = [c.strip() for c in 벗긴줄.strip("|").split("|")]
        if len(칸) < 2 or set("".join(칸)) <= set("-: "):
            continue
        if 칸[0] == "#":
            continue  # 머리행
        컬럼.append(칸[1])
    return 컬럼
