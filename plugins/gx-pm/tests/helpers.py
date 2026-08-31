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

    .omc 는 런타임 상태 디렉터리라 검사 대상이 아니다.
    """
    docs = []
    for path in sorted(PLUGIN_ROOT.rglob("*.md")):
        if ".omc" in path.parts:
            continue
        docs.append((path, path.read_text(encoding="utf-8")))
    return docs


def skill_names() -> set[str]:
    return {d.name for d in (PLUGIN_ROOT / "skills").iterdir() if d.is_dir()}


def command_names() -> set[str]:
    return {p.stem for p in (PLUGIN_ROOT / "commands").glob("*.md")}


def template_names() -> set[str]:
    return {p.name for p in (PLUGIN_ROOT / "templates").glob("*.md")}
