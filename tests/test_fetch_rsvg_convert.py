"""scripts/fetch_rsvg_convert.py の環境判定の単体テスト (ダウンロードはしない)."""
import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parent.parent / "scripts" / "fetch_rsvg_convert.py"
_spec = importlib.util.spec_from_file_location("fetch_rsvg_convert", _PATH)
fetcher = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetcher)


@pytest.mark.parametrize("plat, machine, kind", [
    ("win32", "AMD64", "x86_64-windows.exe.zst"),
    ("win32", "ARM64", "x86_64-windows.exe.zst"),
    ("darwin", "arm64", "aarch64-darwin.zst"),
    ("darwin", "x86_64", "x86_64-darwin.zst"),
    ("linux", "x86_64", "x86_64-linux.zst"),
    ("linux", "aarch64", "aarch64-linux.zst"),
])
def test_target(plat, machine, kind):
    assert fetcher.target(plat, machine) == kind


def test_unsupported_target():
    assert fetcher.target("win32", "x86") is None
    assert fetcher.target("freebsd14", "amd64") is None


def test_every_target_has_hash():
    for kind in set(fetcher._TARGETS.values()):
        assert len(fetcher.SHA256[kind]) == 64


def test_exe_name():
    assert fetcher.exe_name("win32") == "rsvg-convert.exe"
    assert fetcher.exe_name("linux") == "rsvg-convert"
