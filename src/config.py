"""
YAML プロファイル管理モジュール
"""
import yaml
from pathlib import Path
import sys
from typing import Dict, List, Any

# アプリケーションのベースディレクトリを取得
if getattr(sys, 'frozen', False):
    # PyInstaller でビルドされた実行ファイルの場合
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # 開発環境の場合
    BASE_DIR = Path(__file__).resolve().parent.parent

PROFILE_DIR = BASE_DIR / 'profiles'
PROFILE_DIR.mkdir(exist_ok=True)


def load_profile(name: str) -> Dict[str, Any]:
    """
    指定された名前のプロファイルを読み込む
    
    Args:
        name: プロファイル名（拡張子なし）
        
    Returns:
        プロファイルデータの辞書
    """
    profile_path = PROFILE_DIR / f'{name}.yml'
    if not profile_path.exists():
        return get_default_profile()
    
    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or get_default_profile()
    except Exception as e:
        print(f"プロファイル読み込みエラー: {e}")
        return get_default_profile()


def save_profile(name: str, data: Dict[str, Any]) -> bool:
    """
    プロファイルを保存する
    
    Args:
        name: プロファイル名（拡張子なし）
        data: 保存するプロファイルデータ
        
    Returns:
        保存成功時 True
    """
    try:
        profile_path = PROFILE_DIR / f'{name}.yml'
        with open(profile_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        print(f"プロファイル保存エラー: {e}")
        return False


def get_available_profiles() -> List[str]:
    """
    利用可能なプロファイル一覧を取得
    
    Returns:
        プロファイル名のリスト
    """
    profiles = []
    for profile_path in PROFILE_DIR.glob('*.yml'):
        profiles.append(profile_path.stem)
    return sorted(profiles)


def get_default_profile() -> Dict[str, Any]:
    """
    デフォルトプロファイルを返す
    
    Returns:
        デフォルト設定の辞書
    """
    return {
        "output_format": "pdf",
        "extra_args": [
            "--wrap=preserve",
            "--pdf-engine=xelatex",
            "-V", "documentclass=bxjsarticle",
            "-V", "classoption=pandoc",
            "--from", "markdown+hard_line_breaks"
        ],
        "lua_filter": "",  # 追加フィルター用（内蔵フィルターは自動適用）
        "template": "",
        "css_file": "",
        "bibliography": "",
        "merge_files": True,  # 複数ファイル結合オプション（デフォルト有効）
        "use_custom_filename": False,  # カスタムファイル名使用オプション
        "output_filename": "",  # カスタム出力ファイル名
        "max_matrix_cols": 20,  # LaTeX行列の最大列数（デフォルト20）
        "metadata": {}
    }


def delete_profile(name: str) -> bool:
    """
    指定されたプロファイルを削除する
    
    Args:
        name: 削除するプロファイル名
        
    Returns:
        削除成功時 True
    """
    try:
        profile_path = PROFILE_DIR / f'{name}.yml'
        if profile_path.exists():
            profile_path.unlink()
            return True
        return False
    except Exception as e:
        print(f"プロファイル削除エラー: {e}")
        return False 