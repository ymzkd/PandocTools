"""
YAML プロファイル管理モジュール

Phase 2 で v2 スキーマ (論理値ベース) に移行。後方互換のため v1 (extra_args ベース)
の読込もサポートする。

v2 形式 (新):
    schema_version: 2
    output_format: pdf
    engine: xelatex
    fontsize: 10pt
    paper: a4paper
    ...
    custom_args: []
    merge_files: true

v1 形式 (旧、互換読込):
    output_format: pdf
    extra_args: [--pdf-engine=xelatex, -V, documentclass=bxjsarticle, ...]
    merge_files: true
"""
import yaml
from pathlib import Path
from typing import Dict, List, Any, Tuple

from common import BASE_DIR
from engines import LogicalConfig

PROFILE_DIR = BASE_DIR / 'profiles'
PROFILE_DIR.mkdir(exist_ok=True)

SCHEMA_VERSION = 2

# プロファイルに記述が無い項目の「省略時ベースライン」。
# GUI の MainWindow._reset_ui_to_defaults() と完全に一致させること。
# (CLI が GUI と同じデフォルト挙動を再現するために必要)
PROFILE_BASELINE: Dict[str, Any] = {
    "output_format": "pdf",
    "engine": "xelatex",
    "fontsize": None,
    "paper": None,
    "linestretch": None,
    "margin_top": None,
    "margin_bottom": None,
    "margin_left": None,
    "margin_right": None,
    "footskip": None,
    "markdown_extensions": "markdown+hard_line_breaks",
    "wrap_preserve": True,
    "toc": False,
    "number_sections": False,
    "standalone": True,
    "citeproc": False,
    "pandoc_crossref": False,
    "documentclass": "bxjsarticle",
    "classoption": "pandoc",
    "lua_filter": None,
    "template": None,
    "custom_args": [],
    # UI 専用 (LogicalConfig には含めない)
    "merge_files": True,
    "output_filename": "",
}


def load_profile(name: str) -> Dict[str, Any]:
    """指定された名前のプロファイルを読み込む."""
    profile_path = PROFILE_DIR / f'{name}.yml'
    if not profile_path.exists():
        return get_default_profile()

    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data if data else get_default_profile()
    except Exception as e:
        print(f"プロファイル読み込みエラー: {e}")
        return get_default_profile()


def save_profile(name: str, data: Dict[str, Any]) -> bool:
    """プロファイルを保存する."""
    try:
        profile_path = PROFILE_DIR / f'{name}.yml'
        with open(profile_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"プロファイル保存エラー: {e}")
        return False


def get_available_profiles() -> List[str]:
    """利用可能なプロファイル一覧を取得."""
    profiles = []
    for profile_path in PROFILE_DIR.glob('*.yml'):
        profiles.append(profile_path.stem)
    return sorted(profiles)


def get_default_profile() -> Dict[str, Any]:
    """デフォルトプロファイル (v2 スキーマ) を返す."""
    return {
        "schema_version": SCHEMA_VERSION,
        "output_format": "pdf",
        "engine": "xelatex",
        "fontsize": "10pt",
        "paper": "a4paper",
        "margin_top": "20mm",
        "margin_bottom": "20mm",
        "margin_left": "15mm",
        "margin_right": "15mm",
        "footskip": "25pt",
        "wrap_preserve": True,
        "standalone": True,
        "markdown_extensions": "markdown+hard_line_breaks",
        "documentclass": "bxjsarticle",
        "classoption": "pandoc",
        "merge_files": True,
    }


def is_v2_profile(data: Dict[str, Any]) -> bool:
    """プロファイル辞書が v2 スキーマかを判定."""
    return data.get("schema_version") == SCHEMA_VERSION or "engine" in data


def delete_profile(name: str) -> bool:
    """指定されたプロファイルを削除する."""
    try:
        profile_path = PROFILE_DIR / f'{name}.yml'
        if profile_path.exists():
            profile_path.unlink()
            return True
        return False
    except Exception as e:
        print(f"プロファイル削除エラー: {e}")
        return False


# --- CLI 向け: プロファイル辞書 → LogicalConfig 変換 (Qt 非依存) ---------------
# GUI では「プロファイル辞書 → UI ウィジェット → LogicalConfig」という経路をたどるが、
# CLI では UI を経由せず直接 LogicalConfig を組み立てる必要がある。以下はその純粋関数。


def resolve_profile(name_or_path: str) -> Dict[str, Any]:
    """プロファイル名 (profiles/ 内) または任意の yml/yaml パスを読み込む."""
    p = Path(name_or_path)
    if p.suffix.lower() in ('.yml', '.yaml') and p.exists():
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"プロファイルの読み込みに失敗しました ({p}): {e}")
    # 名前として profiles/ から読み込む (存在しなければ get_default_profile が返る)
    return load_profile(name_or_path)


def profile_extras(data: Dict[str, Any]) -> Dict[str, Any]:
    """LogicalConfig に含まれない UI 専用項目 (merge_files / output_filename) を取り出す."""
    return {
        "merge_files": bool(data.get("merge_files", True)),
        "output_filename": str(data.get("output_filename", "") or ""),
    }


def profile_to_logical_config(data: Dict[str, Any]) -> LogicalConfig:
    """プロファイル辞書 (v1/v2) を LogicalConfig に変換する."""
    if is_v2_profile(data):
        return _v2_to_logical(data)
    return _v1_to_logical(data)


def _norm(value: Any) -> Any:
    """空文字を None に正規化 (None/空 = 未指定)."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _v2_to_logical(data: Dict[str, Any]) -> LogicalConfig:
    """v2 スキーマ (論理値ベース). 省略項目は PROFILE_BASELINE で補う."""
    d = {**PROFILE_BASELINE, **data}
    return LogicalConfig(
        output_format=str(d.get("output_format") or "pdf"),
        engine=str(d.get("engine") or "xelatex"),
        fontsize=_norm(d.get("fontsize")),
        paper=_norm(d.get("paper")),
        margin_top=_norm(d.get("margin_top")),
        margin_bottom=_norm(d.get("margin_bottom")),
        margin_left=_norm(d.get("margin_left")),
        margin_right=_norm(d.get("margin_right")),
        footskip=_norm(d.get("footskip")),
        linestretch=_norm(d.get("linestretch")),
        toc=bool(d.get("toc", False)),
        number_sections=bool(d.get("number_sections", False)),
        standalone=bool(d.get("standalone", True)),
        citeproc=bool(d.get("citeproc", False)),
        pandoc_crossref=bool(d.get("pandoc_crossref", False)),
        wrap_preserve=bool(d.get("wrap_preserve", True)),
        markdown_extensions=_norm(d.get("markdown_extensions")),
        lua_filter=_norm(d.get("lua_filter")),
        template_file=_norm(d.get("template")),
        custom_args=list(d.get("custom_args") or []),
        documentclass=_norm(d.get("documentclass")),
        classoption=_norm(d.get("classoption")),
    )


def _v1_to_logical(data: Dict[str, Any]) -> LogicalConfig:
    """v1 スキーマ (extra_args ベース) の互換変換.

    GUI の _apply_profile_v1 と同じく、reset デフォルトから wrap/standalone/
    markdown_extensions/documentclass/classoption を一旦外し、extra_args の内容で
    再構築する。解釈できない引数は custom_args に集約する。
    """
    cfg = LogicalConfig(
        output_format=str(data.get("output_format") or "pdf"),
        engine="xelatex",
        # v1 baseline (reset 後の上書き)
        wrap_preserve=False,
        standalone=False,
        markdown_extensions=None,
        documentclass=None,
        classoption=None,
    )

    extra: List[str] = list(data.get("extra_args") or [])
    custom: List[str] = []
    i = 0
    n = len(extra)
    while i < n:
        arg = extra[i]
        if arg == "--wrap=preserve":
            cfg.wrap_preserve = True
        elif arg == "--toc":
            cfg.toc = True
        elif arg == "--number-sections":
            cfg.number_sections = True
        elif arg == "--standalone":
            cfg.standalone = True
        elif arg == "--citeproc":
            cfg.citeproc = True
        elif arg == "--filter" and i + 1 < n:
            if extra[i + 1] == "pandoc-crossref":
                cfg.pandoc_crossref = True
            else:
                custom.extend([arg, extra[i + 1]])
            i += 1
        elif arg.startswith("--pdf-engine=") and not arg.startswith("--pdf-engine-opt"):
            cfg.engine = arg.split("=", 1)[1]
        elif arg == "--pdf-engine" and i + 1 < n:
            cfg.engine = extra[i + 1]
            i += 1
        elif arg == "-V" and i + 1 < n:
            nxt = extra[i + 1]
            if nxt.startswith("documentclass="):
                cfg.documentclass = nxt.split("=", 1)[1]
            elif nxt.startswith("classoption="):
                cfg.classoption = nxt.split("=", 1)[1]
            elif nxt.startswith("fontsize="):
                cfg.fontsize = nxt.split("=", 1)[1]
            elif nxt.startswith("papersize="):
                cfg.paper = nxt.split("=", 1)[1]
            elif nxt.startswith("linestretch="):
                cfg.linestretch = nxt.split("=", 1)[1]
            elif nxt.startswith("geometry:"):
                _parse_geometry_into(cfg, nxt.split(":", 1)[1])
            else:
                custom.extend([arg, nxt])
            i += 1
        elif arg == "--from" and i + 1 < n:
            cfg.markdown_extensions = extra[i + 1]
            i += 1
        elif arg == "--template" and i + 1 < n:
            cfg.template_file = extra[i + 1]
            i += 1
        elif arg.startswith("--template="):
            cfg.template_file = arg.split("=", 1)[1]
        elif arg == "--lua-filter" and i + 1 < n:
            cfg.lua_filter = extra[i + 1]
            i += 1
        elif arg == "--bibliography" and i + 1 < n:
            cfg.bibliography_files.append(extra[i + 1])
            i += 1
        else:
            custom.append(arg)
        i += 1

    cfg.custom_args = custom
    # プロファイル直下のキー (空文字は None 扱い)
    cfg.template_file = cfg.template_file or _norm(data.get("template"))
    cfg.lua_filter = cfg.lua_filter or _norm(data.get("lua_filter"))
    return cfg


def _parse_geometry_into(cfg: LogicalConfig, geometry: str) -> None:
    """geometry:... 文字列を LogicalConfig の margin/footskip に展開する."""
    geometry = geometry.strip()
    if geometry.startswith("margin="):
        v = geometry.split("=", 1)[1].strip()
        cfg.margin_top = cfg.margin_bottom = cfg.margin_left = cfg.margin_right = v
        return
    for part in geometry.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key, value = key.strip(), value.strip()
        if key == "top":
            cfg.margin_top = value
        elif key == "bottom":
            cfg.margin_bottom = value
        elif key == "left":
            cfg.margin_left = value
        elif key == "right":
            cfg.margin_right = value
        elif key == "footskip":
            cfg.footskip = value
