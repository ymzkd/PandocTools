"""
共通定数とユーティリティ関数
"""
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import Optional

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

RSVG_CONVERT = "rsvg-convert.exe" if sys.platform == "win32" else "rsvg-convert"

# exe 版 (dist/bin/) と、インストールせず src/ から動かす開発時 (src/bin/) の
# rsvg-convert の置き場所。scripts/fetch_rsvg_convert.py が取得して置く。
# pip / uv でインストールした場合は、他のコマンドと同じく環境の Scripts に入る。
BIN_DIR = RESOURCE_DIR / "bin"


def installed_scripts_dir() -> Optional[Path]:
    """pip / uv が rsvg-convert を入れた Scripts (bin) ディレクトリ.

    wheel の RECORD から探す (--user などの配置でも実際の場所が分かる)。
    exe 版やインストールせずに動かしている場合は None。
    """
    try:
        files = metadata.distribution("pandoc-gui").files or []
    except metadata.PackageNotFoundError:
        return None
    for f in files:
        if f.name == RSVG_CONVERT:
            return Path(f.locate()).resolve().parent
    return None


def _contains(path: str, directory: Path) -> bool:
    key = os.path.normcase(os.path.normpath(str(directory)))
    return any(p and os.path.normcase(os.path.normpath(p)) == key for p in path.split(os.pathsep))


def with_bundled_bin(path: str, bin_dir: Optional[Path] = None,
                     scripts_dir: Optional[Path] = None) -> str:
    """PATH 文字列に rsvg-convert の置き場所を足した値を返す.

    - bin_dir (exe 版・開発時) は先頭に足す。rsvg-convert しか入っていないので
      他のコマンドを隠さない。
    - scripts_dir (pip / uv の Scripts) は PATH に無いときだけ末尾に足す。
      python など他のコマンドも入っているので、既存の PATH より前には置かない。
      venv を activate せずにアプリを起動した場合の補い。
    存在しないディレクトリや、既に PATH にあるディレクトリは足さない。
    """
    entries = path.split(os.pathsep) if path else []
    if scripts_dir is not None and scripts_dir.is_dir() and not _contains(path, scripts_dir):
        entries.append(str(scripts_dir))
    if bin_dir is not None and bin_dir.is_dir() and not _contains(path, bin_dir):
        entries.insert(0, str(bin_dir))
    return os.pathsep.join(entries)


def use_bundled_tools() -> None:
    """同梱の rsvg-convert を inline_svg.lua と pandoc から使えるようにする.

    - inline_svg.lua には絶対パスを環境変数 PANDOCTOOLS_RSVG_CONVERT で渡す。
      PATH の並びによらず、環境に古い rsvg-convert (choco の 2.40 等) があっても
      同梱版で描画を揃えるため (既に設定されていれば尊重する)。
    - pandoc 本体も rsvg-convert を PATH から探す (docx の PNG 代替画像など) ので、
      自プロセスの PATH にも足す。子プロセスは環境変数を引き継ぐので、pandoc と
      その先のフィルタまで届く (OS の PATH 設定は変えない)。
    """
    # 実物があるときだけ使う。通常の pip インストールでは RESOURCE_DIR が
    # site-packages になり、他のパッケージが置いた無関係な bin/ を拾いうるため
    bin_dir = BIN_DIR if (BIN_DIR / RSVG_CONVERT).is_file() else None
    scripts_dir = installed_scripts_dir()
    # PATH が未設定なら既定の検索パスから始める (bin_dir だけにして pandoc を見失わないよう)
    os.environ["PATH"] = with_bundled_bin(os.environ.get("PATH", os.defpath),
                                          bin_dir, scripts_dir)
    exe_dir = bin_dir or scripts_dir
    if exe_dir is not None:
        os.environ.setdefault("PANDOCTOOLS_RSVG_CONVERT", str(exe_dir / RSVG_CONVERT))
