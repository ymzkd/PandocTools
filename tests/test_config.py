"""config.py プロファイル管理の単体テスト."""
import tempfile
from pathlib import Path

import pytest
import yaml


import common  # noqa: F401  (imported for side-effect of setting BASE_DIR)


def _force_isolated_profile_dir(tmp_path, monkeypatch):
    """テスト用に PROFILE_DIR を tmp_path に差し替える."""
    import config as cfg_module
    monkeypatch.setattr(cfg_module, "PROFILE_DIR", tmp_path)
    return cfg_module


def test_is_v2_by_schema_version(tmp_path, monkeypatch):
    cfg = _force_isolated_profile_dir(tmp_path, monkeypatch)
    assert cfg.is_v2_profile({"schema_version": 2, "output_format": "pdf"})


def test_is_v2_by_engine_key(tmp_path, monkeypatch):
    cfg = _force_isolated_profile_dir(tmp_path, monkeypatch)
    assert cfg.is_v2_profile({"engine": "typst", "output_format": "pdf"})


def test_is_v1_when_only_extra_args(tmp_path, monkeypatch):
    cfg = _force_isolated_profile_dir(tmp_path, monkeypatch)
    v1 = {"output_format": "pdf", "extra_args": ["--wrap=preserve"]}
    assert not cfg.is_v2_profile(v1)


def test_get_default_profile_is_v2(tmp_path, monkeypatch):
    cfg = _force_isolated_profile_dir(tmp_path, monkeypatch)
    data = cfg.get_default_profile()
    assert cfg.is_v2_profile(data)
    assert data["schema_version"] == cfg.SCHEMA_VERSION
    assert data["engine"] == "xelatex"
    assert data["output_format"] == "pdf"


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    cfg = _force_isolated_profile_dir(tmp_path, monkeypatch)
    data = {
        "schema_version": 2,
        "output_format": "pdf",
        "engine": "typst",
        "fontsize": "11pt",
        "paper": "a4paper",
        "linestretch": "1.2",
        "margin_top": "20mm",
        "toc": True,
    }
    assert cfg.save_profile("roundtrip_test", data)
    loaded = cfg.load_profile("roundtrip_test")
    for key in data:
        assert loaded[key] == data[key]


def test_load_nonexistent_returns_default(tmp_path, monkeypatch):
    cfg = _force_isolated_profile_dir(tmp_path, monkeypatch)
    loaded = cfg.load_profile("does_not_exist")
    assert cfg.is_v2_profile(loaded)


def test_legacy_v1_profile_loadable(tmp_path, monkeypatch):
    """v1 profile (extra_args 形式) も読み込めることを確認."""
    cfg = _force_isolated_profile_dir(tmp_path, monkeypatch)
    v1 = {
        "output_format": "pdf",
        "extra_args": [
            "--wrap=preserve",
            "--pdf-engine=xelatex",
            "-V", "documentclass=bxjsarticle",
            "-V", "fontsize=10pt",
        ],
        "merge_files": True,
    }
    cfg.save_profile("legacy_v1", v1)
    loaded = cfg.load_profile("legacy_v1")
    assert not cfg.is_v2_profile(loaded)
    assert "extra_args" in loaded
    assert loaded["output_format"] == "pdf"
