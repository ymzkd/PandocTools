"""EngineAdapter の単体テスト."""
from pathlib import Path

import pytest

from engines import (
    LatexAdapter,
    LogicalConfig,
    TypstAdapter,
    get_adapter,
    is_typst_mode,
)


RESOURCE_DIR = Path(__file__).resolve().parent.parent / "src"


# --- is_typst_mode / get_adapter ---


def test_is_typst_mode_by_engine():
    cfg = LogicalConfig(engine="typst", output_format="pdf")
    assert is_typst_mode(cfg)


def test_is_typst_mode_by_output_format():
    cfg = LogicalConfig(engine="xelatex", output_format="typst")
    assert is_typst_mode(cfg)


def test_is_typst_mode_neither():
    cfg = LogicalConfig(engine="xelatex", output_format="pdf")
    assert not is_typst_mode(cfg)


def test_get_adapter_typst():
    assert isinstance(get_adapter(LogicalConfig(engine="typst")), TypstAdapter)


def test_get_adapter_latex():
    assert isinstance(get_adapter(LogicalConfig(engine="xelatex")), LatexAdapter)


# --- output_extension ---


def test_typst_output_extension_typst():
    cfg = LogicalConfig(output_format="typst")
    assert TypstAdapter().output_extension(cfg) == "typ"


def test_typst_output_extension_pdf():
    cfg = LogicalConfig(output_format="pdf", engine="typst")
    assert TypstAdapter().output_extension(cfg) == "pdf"


def test_latex_output_extension_pdf():
    cfg = LogicalConfig(output_format="pdf")
    assert LatexAdapter().output_extension(cfg) == "pdf"


# --- LatexAdapter._engine_specific ---


def test_latex_pdf_engine_pdf_output():
    cfg = LogicalConfig(output_format="pdf", engine="xelatex")
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    assert "--pdf-engine=xelatex" in args
    assert "--pdf-engine-opt=-shell-escape" in args


def test_latex_pdf_engine_not_pdf_output():
    """tex / docx 出力時は --pdf-engine を渡さない (A-2-d 汎用化)."""
    cfg = LogicalConfig(output_format="tex", engine="xelatex")
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    assert not any(a.startswith("--pdf-engine") for a in args)


def test_latex_documentclass():
    cfg = LogicalConfig(output_format="pdf", documentclass="bxjsarticle")
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    assert "-V" in args
    assert "documentclass=bxjsarticle" in args


def test_latex_paper_passthrough():
    """LaTeX では a4paper をそのまま渡す."""
    cfg = LogicalConfig(paper="a4paper")
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    assert "papersize=a4paper" in args


def test_latex_geometry_compound():
    """個別 margin が 1 つの -V geometry: に集約される."""
    cfg = LogicalConfig(
        margin_top="20mm", margin_bottom="20mm",
        margin_left="25mm", margin_right="25mm", footskip="10mm",
    )
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    geom = next(a for a in args if a.startswith("geometry:"))
    assert "top=20mm" in geom
    assert "bottom=20mm" in geom
    assert "left=25mm" in geom
    assert "right=25mm" in geom
    assert "footskip=10mm" in geom


def test_latex_filters_include_pandoc_crossref():
    cfg = LogicalConfig(pandoc_crossref=True)
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    assert "pandoc-crossref" in args


def test_latex_filters_include_default_lua():
    cfg = LogicalConfig()
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    has_default_filter = any("default_filter.lua" in a for a in args)
    assert has_default_filter


# --- TypstAdapter._engine_specific ---


def test_typst_paper_mapping():
    cfg = LogicalConfig(engine="typst", paper="a4paper")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert "papersize=a4" in args


def test_typst_letterpaper_mapping():
    cfg = LogicalConfig(engine="typst", paper="letterpaper")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert "papersize=us-letter" in args


def test_typst_individual_margins():
    cfg = LogicalConfig(
        engine="typst",
        margin_top="20mm", margin_bottom="20mm",
        margin_left="25mm", margin_right="25mm",
    )
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert "margin-top=20mm" in args
    assert "margin-bottom=20mm" in args
    assert "margin-left=25mm" in args
    assert "margin-right=25mm" in args
    # geometry は使われない
    assert not any(a.startswith("geometry:") for a in args)


def test_typst_pdf_engine_typst_only_on_pdf():
    """typst output (.typ) では --pdf-engine を渡さない."""
    cfg = LogicalConfig(engine="typst", output_format="typst")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert not any(a.startswith("--pdf-engine") for a in args)


def test_typst_pdf_engine_on_pdf_output():
    cfg = LogicalConfig(engine="typst", output_format="pdf")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert "--pdf-engine=typst" in args


def test_typst_no_shell_escape():
    cfg = LogicalConfig(engine="typst", output_format="pdf")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert not any("shell-escape" in a for a in args)


def test_typst_drops_documentclass():
    """typst では documentclass / classoption は無視 (C-2-c)."""
    cfg = LogicalConfig(
        engine="typst", documentclass="bxjsarticle", classoption="pandoc"
    )
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert not any("documentclass" in a for a in args)
    assert not any("classoption" in a for a in args)


def test_typst_drops_footskip():
    cfg = LogicalConfig(engine="typst", footskip="10mm")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert not any("footskip" in a for a in args)


# --- TypstAdapter._filters ---


def test_typst_skips_default_filter():
    """typst モードでは default_filter.lua をスキップ (A-2-e)."""
    cfg = LogicalConfig(engine="typst")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert not any("default_filter.lua" in a for a in args)


def test_typst_skips_pandoc_crossref():
    """typst モードでは pandoc-crossref をスキップ (A-2-f)."""
    cfg = LogicalConfig(engine="typst", pandoc_crossref=True)
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert "pandoc-crossref" not in args


def test_typst_user_lua_filter_kept():
    cfg = LogicalConfig(engine="typst", lua_filter="/tmp/user.lua")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert "/tmp/user.lua" in args


# --- TypstAdapter._template ---


def test_typst_builtin_template_used_when_no_user_template():
    cfg = LogicalConfig(engine="typst")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    has_typst_tpl = any("default_typst.typ" in a for a in args)
    assert has_typst_tpl
    assert "lang=ja" in args


def test_typst_user_template_overrides_builtin():
    cfg = LogicalConfig(engine="typst", template_file="/tmp/my.typ")
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    assert "--template=/tmp/my.typ" in args
    # built-in もデフォルト lang も使われない
    assert not any("default_typst.typ" in a for a in args)
    assert "lang=ja" not in args


# --- TypstAdapter._csl ---


def test_typst_csl_forward_slash_normalized():
    """typst モードで bibliography があるとき、CSL パスは forward slash 正規化される."""
    cfg = LogicalConfig(engine="typst", bibliography_files=["/tmp/refs.bib"])
    args = TypstAdapter().build_args(cfg, RESOURCE_DIR)
    csl_idx = args.index("--csl")
    csl_path = args[csl_idx + 1]
    assert "\\" not in csl_path  # forward slash only


def test_csl_skipped_when_no_bibliography():
    """bibliography 無しでは --csl を渡さない (typst の path sandbox 回避)."""
    for adapter in [LatexAdapter(), TypstAdapter()]:
        cfg = LogicalConfig(engine=adapter.name)
        args = adapter.build_args(cfg, RESOURCE_DIR)
        assert "--csl" not in args


def test_csl_active_with_citeproc():
    """citeproc チェック時は bibliography 無しでも CSL を適用."""
    cfg = LogicalConfig(citeproc=True)
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    assert "--csl" in args


def test_csl_active_with_bibliography():
    cfg = LogicalConfig(bibliography_files=["/tmp/a.bib"])
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    assert "--csl" in args


# --- 共通項目 (linestretch / fontsize 等) ---


def test_linestretch_common():
    """linestretch は両 engine で同じ -V linestretch=X 形式."""
    cfg_latex = LogicalConfig(engine="xelatex", linestretch="1.2")
    cfg_typst = LogicalConfig(engine="typst", linestretch="1.2")
    args_l = LatexAdapter().build_args(cfg_latex, RESOURCE_DIR)
    args_t = TypstAdapter().build_args(cfg_typst, RESOURCE_DIR)
    assert "linestretch=1.2" in args_l
    assert "linestretch=1.2" in args_t


def test_fontsize_common():
    for adapter, engine in [(LatexAdapter(), "xelatex"), (TypstAdapter(), "typst")]:
        cfg = LogicalConfig(engine=engine, fontsize="11pt")
        args = adapter.build_args(cfg, RESOURCE_DIR)
        assert "fontsize=11pt" in args


def test_toc_common():
    for adapter, engine in [(LatexAdapter(), "xelatex"), (TypstAdapter(), "typst")]:
        cfg = LogicalConfig(engine=engine, toc=True)
        args = adapter.build_args(cfg, RESOURCE_DIR)
        assert "--toc" in args


def test_bibliography_appended():
    cfg = LogicalConfig(bibliography_files=["/tmp/a.bib", "/tmp/b.bib"])
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    assert args.count("--bibliography") == 2
    assert "/tmp/a.bib" in args
    assert "/tmp/b.bib" in args


def test_custom_args_passthrough():
    cfg = LogicalConfig(custom_args=["--metadata=author:foo"])
    args = LatexAdapter().build_args(cfg, RESOURCE_DIR)
    assert "--metadata=author:foo" in args
