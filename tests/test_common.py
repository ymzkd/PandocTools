"""common.py 同梱ツールの PATH 付与の単体テスト."""
import os

import pytest

import common
from common import with_bundled_bin


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.delenv("PANDOCTOOLS_RSVG_CONVERT", raising=False)
    monkeypatch.setattr(common, "installed_scripts_dir", lambda: None)
    return monkeypatch


def _fake_exe(directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / common.RSVG_CONVERT).write_bytes(b"")
    return directory


def test_prepends_bin_dir(tmp_path):
    path = os.pathsep.join(["/usr/bin", "/bin"])
    result = with_bundled_bin(path, tmp_path)
    assert result.split(os.pathsep) == [str(tmp_path), "/usr/bin", "/bin"]


def test_empty_path(tmp_path):
    assert with_bundled_bin("", tmp_path) == str(tmp_path)


def test_idempotent(tmp_path):
    once = with_bundled_bin("/usr/bin", tmp_path)
    assert with_bundled_bin(once, tmp_path) == once


def test_missing_bin_dir_leaves_path(tmp_path):
    assert with_bundled_bin("/usr/bin", tmp_path / "nope") == "/usr/bin"


def test_appends_scripts_dir(tmp_path):
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    result = with_bundled_bin("/usr/bin", tmp_path / "nope", scripts)
    assert result.split(os.pathsep) == ["/usr/bin", str(scripts)]


def test_scripts_dir_already_on_path(tmp_path):
    path = os.pathsep.join([str(tmp_path), "/usr/bin"])
    assert with_bundled_bin(path, tmp_path / "nope", tmp_path) == path


def test_use_bundled_tools_bin_dir(tmp_path, clean_env):
    bin_dir = _fake_exe(tmp_path / "bin")
    clean_env.setattr(common, "BIN_DIR", bin_dir)
    common.use_bundled_tools()
    assert os.environ["PATH"].split(os.pathsep) == [str(bin_dir), "/usr/bin"]
    assert os.environ["PANDOCTOOLS_RSVG_CONVERT"] == str(bin_dir / common.RSVG_CONVERT)


def test_use_bundled_tools_ignores_unrelated_bin_dir(tmp_path, clean_env):
    # 通常の pip インストールでの site-packages/bin のように、rsvg-convert の無い
    # bin/ は PATH に足さず、pip / uv の Scripts の方を使う
    (tmp_path / "bin").mkdir()
    clean_env.setattr(common, "BIN_DIR", tmp_path / "bin")
    scripts = _fake_exe(tmp_path / "Scripts")
    clean_env.setattr(common, "installed_scripts_dir", lambda: scripts)
    common.use_bundled_tools()
    assert os.environ["PATH"].split(os.pathsep) == ["/usr/bin", str(scripts)]
    assert os.environ["PANDOCTOOLS_RSVG_CONVERT"] == str(scripts / common.RSVG_CONVERT)


def test_use_bundled_tools_respects_existing_setting(tmp_path, clean_env):
    clean_env.setattr(common, "BIN_DIR", _fake_exe(tmp_path / "bin"))
    clean_env.setenv("PANDOCTOOLS_RSVG_CONVERT", "custom-rsvg-convert")
    common.use_bundled_tools()
    assert os.environ["PANDOCTOOLS_RSVG_CONVERT"] == "custom-rsvg-convert"


def test_use_bundled_tools_unset_path_keeps_default(tmp_path, clean_env):
    bin_dir = _fake_exe(tmp_path / "bin")
    clean_env.setattr(common, "BIN_DIR", bin_dir)
    clean_env.delenv("PATH")
    common.use_bundled_tools()
    assert os.environ["PATH"] == str(bin_dir) + os.pathsep + os.defpath
