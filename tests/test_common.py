"""common.py 同梱ツールの PATH 付与の単体テスト."""
import os

from common import with_bundled_bin


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
