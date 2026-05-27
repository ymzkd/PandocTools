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
from typing import Dict, List, Any

from common import BASE_DIR

PROFILE_DIR = BASE_DIR / 'profiles'
PROFILE_DIR.mkdir(exist_ok=True)

SCHEMA_VERSION = 2


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
