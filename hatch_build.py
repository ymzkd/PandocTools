"""
hatchling のビルドフック: wheel をビルドするときに rsvg-convert を取得して同梱する.

pip install / uv tool install はソースから wheel をビルドしてから入れるので、
インストール先の OS / CPU に合う rsvg-convert が一緒に入る。置き場所は wheel の
scripts 区分 (= 環境の Scripts / bin) で、pip で入れた他のコマンドと同じく、
PATH の設定を足さなくても rsvg-convert としてどこからでも呼べる。

取得に失敗してもビルドは止めない。rsvg-convert が無くても inline_svg.lua は
inkscape / typst にフォールバックするため。
"""
import importlib.util
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def _load_fetcher(root: str):
    path = Path(root) / "scripts" / "fetch_rsvg_convert.py"
    spec = importlib.util.spec_from_file_location("fetch_rsvg_convert", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RsvgConvertHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # sdist はソースだけにする (バイナリは wheel をビルドする環境で取得する)
        if self.target_name != "wheel":
            return
        try:
            exe = _load_fetcher(self.root).fetch()
        except Exception as e:
            self.app.display_warning(f"rsvg-convert を取得できませんでした: {e}")
            return
        if exe is None:
            self.app.display_warning("この環境向けの rsvg-convert は配布されていません")
            return
        # editable インストール (pip install -e .) でも同じく Scripts に入る
        build_data["shared_scripts"][str(exe)] = exe.name
        # OS ごとに中身が違うので、プラットフォーム固有の wheel にする
        build_data["pure_python"] = False
        build_data["infer_tag"] = True
