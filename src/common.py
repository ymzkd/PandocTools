"""
共通定数とユーティリティ関数
"""
import sys
from pathlib import Path

# アプリケーションのベースディレクトリを取得
if getattr(sys, 'frozen', False):
    # PyInstaller でビルドされた実行ファイルの場合
    # EXEファイルと同じディレクトリからリソースを読み込み
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = BASE_DIR
else:
    # 開発環境の場合
    BASE_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = Path(__file__).resolve().parent