"""
rsvg-convert の取得スクリプト

unpins/rsvg-convert が配布する単一バイナリ (librsvg を依存ライブラリごと静的リンク
したもの) を、実行中の OS / CPU に合わせてダウンロードし、sha256 を照合して
src/bin/ に置く。リポジトリにはバイナリを入れず、必要な環境で都度取得する。

呼び出し元:
  - hatch_build.py : pip install / uv tool install で wheel をビルドするとき
  - build.bat      : exe をビルドするとき
  - 手動           : python scripts/fetch_rsvg_convert.py [--force]

版を上げるときは VERSION と SHA256 を、同じリリースの *.sha256 の値に差し替える。
"""
from __future__ import annotations

import argparse
import hashlib
import platform
import sys
import urllib.request
from pathlib import Path
from typing import List, Optional

VERSION = "2.62.3-1"
URL = "https://github.com/unpins/rsvg-convert/releases/download/v{version}/rsvg-convert-{version}-{kind}"

# アセット種別 → 配布元の .sha256 に載っている値 (圧縮された .zst のハッシュ)
SHA256 = {
    "x86_64-windows.exe.zst": "dc89d50ab0cbdd799486080ae92799d033ceac54b732b0b7ba056c2d296517e9",
    "x86_64-darwin.zst": "3b88223a91884d3904f2a328cc3f417eb5fbbdd5874d76da9bf16501e90056cd",
    "aarch64-darwin.zst": "e358cd9af724c451f97f5f01d8df7dffd85333a1791f84a91f251909e9ff202b",
    "x86_64-linux.zst": "49b5be15127a8f611bfa87782508f99e8a7a315c9e4eab0927a46b6c98a6b6ae",
    "aarch64-linux.zst": "189da4e9d533a41bf0aef6cb08afd8f16d62f9e0bea06c0abec3d3599f9005df",
    "armv7l-linux.zst": "55d1141e6ec550cf86c34acf962d76569798612bcdad63b8d6835b7771100d29",
    "i686-linux.zst": "9bcb5f18b23a4c3487b633cbedf6f3676ca8911ce4b2ae528a1989ce13cad364",
    "ppc64le-linux.zst": "7af24df01226358bbc7ca0ee80294282dcaa2e6394c8af63895e22441068c345",
    "riscv64-linux.zst": "ad22841189c8c0b003a8dfe667204e480e472ac664b5ff0f01bcbe55c12926c3",
}

# (OS, platform.machine() の小文字) → アセット種別
_TARGETS = {
    ("win32", "amd64"): "x86_64-windows.exe.zst",
    # Windows on ARM 向けは配布されていないので、x64 エミュレーションで動かす
    ("win32", "arm64"): "x86_64-windows.exe.zst",
    ("darwin", "x86_64"): "x86_64-darwin.zst",
    ("darwin", "arm64"): "aarch64-darwin.zst",
    ("linux", "x86_64"): "x86_64-linux.zst",
    ("linux", "aarch64"): "aarch64-linux.zst",
    ("linux", "armv7l"): "armv7l-linux.zst",
    ("linux", "i686"): "i686-linux.zst",
    ("linux", "ppc64le"): "ppc64le-linux.zst",
    ("linux", "riscv64"): "riscv64-linux.zst",
}

DEFAULT_DEST = Path(__file__).resolve().parent.parent / "src" / "bin"


def target(plat: str = sys.platform, machine: str = platform.machine()) -> Optional[str]:
    """実行環境に合うアセット種別。配布の無い環境では None."""
    os_name = "linux" if plat.startswith("linux") else plat
    return _TARGETS.get((os_name, machine.lower()))


def exe_name(plat: str = sys.platform) -> str:
    return "rsvg-convert.exe" if plat == "win32" else "rsvg-convert"


def _decompress(data: bytes) -> bytes:
    try:
        import zstandard
    except ImportError:
        # zstandard の wheel が無い環境 (armv7l / riscv64) 向け。Python 3.14+ のみ
        from compression import zstd
        return zstd.decompress(data)
    return zstandard.ZstdDecompressor().decompressobj().decompress(data)


def fetch(dest: Path = DEFAULT_DEST, force: bool = False) -> Optional[Path]:
    """rsvg-convert を dest に置き、そのパスを返す。配布の無い環境では None.

    同じ版・同じ種別 (OS / CPU) を取得済みなら何もしない (dest/rsvg-convert.version
    で判定)。種別も記録するのは、Dropbox などでフォルダを共有する別 CPU の PC
    (Intel Mac と Apple Silicon Mac など) が同じファイル名の別物を使い回さないため。
    記録は本体を書き終えてから残すので、途中で失敗しても次回は取り直す。
    """
    kind = target()
    if kind is None:
        return None
    exe = dest / exe_name()
    stamp = dest / "rsvg-convert.version"
    fetched = f"{VERSION} {kind}"
    if not force and exe.exists() and stamp.exists() and stamp.read_text().strip() == fetched:
        return exe

    with urllib.request.urlopen(URL.format(version=VERSION, kind=kind), timeout=60) as r:
        data = r.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256[kind]:
        raise RuntimeError(f"rsvg-convert-{VERSION}-{kind}: sha256 が一致しません ({digest})")

    dest.mkdir(parents=True, exist_ok=True)
    stamp.unlink(missing_ok=True)
    exe.write_bytes(_decompress(data))
    exe.chmod(0o755)
    stamp.write_text(fetched + "\n")
    return exe


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="rsvg-convert を取得して src/bin/ に置く")
    parser.add_argument("dest", nargs="?", type=Path, default=DEFAULT_DEST,
                        help="置き場所 (既定: src/bin)")
    parser.add_argument("--force", action="store_true", help="取得済みでも取り直す")
    args = parser.parse_args(argv)
    exe = fetch(args.dest, args.force)
    if exe is None:
        print(f"この環境 ({sys.platform} / {platform.machine()}) 向けの rsvg-convert は"
              "配布されていません", file=sys.stderr)
        return 1
    print(exe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
