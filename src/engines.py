"""
EngineAdapter: 論理的な組版設定 (LogicalConfig) を engine 別の Pandoc 引数に変換する層。

- LogicalConfig : UI 状態を保持する engine 非依存の論理値
- LatexAdapter  : 従来の xelatex / lualatex / pdflatex / tectonic などの LaTeX 系
- TypstAdapter  : --pdf-engine=typst または output_format=typst のとき

主な責務:
  1. LaTeX / Typst で命名の異なる Pandoc 変数 (-V foo=bar) のマッピング
  2. 各 engine で対応外の項目を黙って無視 (C-2-c)
  3. 出力ファイルの拡張子決定 (output_extension)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# LaTeX 風 papersize (a4paper 等) → Typst paper 名
_TYPST_PAPER_MAP = {
    "a3paper": "a3",
    "a4paper": "a4",
    "a5paper": "a5",
    "letterpaper": "us-letter",
}

# output_format 名 → 出力ファイル拡張子 (Pandoc 互換)
_OUTPUT_EXT_MAP = {"typst": "typ"}


@dataclass
class LogicalConfig:
    """エンジン非依存の論理組版設定 (UI 状態の値オブジェクト)."""

    # 出力コンテキスト
    output_format: str = "pdf"
    engine: str = "xelatex"

    # 共通組版
    fontsize: Optional[str] = None
    paper: Optional[str] = None
    margin_top: Optional[str] = None
    margin_bottom: Optional[str] = None
    margin_left: Optional[str] = None
    margin_right: Optional[str] = None
    footskip: Optional[str] = None
    linestretch: Optional[str] = None

    # 共通フラグ
    toc: bool = False
    number_sections: bool = False
    standalone: bool = False
    citeproc: bool = False
    pandoc_crossref: bool = False
    wrap_preserve: bool = False

    # 入力 / フィルター / テンプレート
    markdown_extensions: Optional[str] = None
    lua_filter: Optional[str] = None
    template_file: Optional[str] = None
    custom_args: List[str] = field(default_factory=list)
    bibliography_files: List[str] = field(default_factory=list)

    # LaTeX 専用詳細
    documentclass: Optional[str] = None
    classoption: Optional[str] = None


def is_typst_mode(cfg: LogicalConfig) -> bool:
    """typst モード判定 (engine=typst もしくは output_format=typst)."""
    return cfg.engine == "typst" or cfg.output_format == "typst"


def get_adapter(cfg: LogicalConfig) -> "EngineAdapter":
    """LogicalConfig から適切な EngineAdapter インスタンスを返す."""
    if is_typst_mode(cfg):
        return TypstAdapter()
    return LatexAdapter()


class EngineAdapter:
    """論理設定 → Pandoc 引数列 を組み立てる抽象基底."""

    name: str = ""

    def output_extension(self, cfg: LogicalConfig) -> str:
        """生成ファイルの拡張子 (Pandoc が writer を推定できる形)."""
        return _OUTPUT_EXT_MAP.get(cfg.output_format, cfg.output_format)

    def build_args(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        args: List[str] = []
        args.extend(self._common_args(cfg))
        args.extend(self._engine_specific(cfg, resource_dir))
        args.extend(self._filters(cfg, resource_dir))
        args.extend(self._template(cfg, resource_dir))
        args.extend(self._csl(cfg, resource_dir))
        args.extend(self._bibliography(cfg))
        args.extend(cfg.custom_args)
        return args

    # --- フック (engine 別にオーバライド) ---
    def _common_args(self, cfg: LogicalConfig) -> List[str]:
        args: List[str] = []
        if cfg.wrap_preserve:
            args.append("--wrap=preserve")
        if cfg.toc:
            args.append("--toc")
        if cfg.number_sections:
            args.append("--number-sections")
        if cfg.standalone:
            args.append("--standalone")
        if cfg.citeproc:
            args.append("--citeproc")
        if cfg.markdown_extensions:
            args.extend(["--from", cfg.markdown_extensions])
        if cfg.fontsize:
            args.extend(["-V", f"fontsize={cfg.fontsize}"])
        if cfg.linestretch:
            args.extend(["-V", f"linestretch={cfg.linestretch}"])
        return args

    def _engine_specific(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        return []

    def _filters(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        return []

    def _template(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        return []

    def _csl(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        return []

    def _bibliography(self, cfg: LogicalConfig) -> List[str]:
        args: List[str] = []
        for bib in cfg.bibliography_files:
            args.extend(["--bibliography", bib])
        return args


class LatexAdapter(EngineAdapter):
    """LaTeX 系 engine 向けの args 組み立て."""

    name = "latex"

    def _engine_specific(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        args: List[str] = []
        # --pdf-engine は PDF 出力時のみ意味を持つ (A-2-d)
        if cfg.output_format == "pdf" and cfg.engine:
            args.append(f"--pdf-engine={cfg.engine}")
            args.append("--pdf-engine-opt=-shell-escape")
        if cfg.documentclass:
            args.extend(["-V", f"documentclass={cfg.documentclass}"])
        if cfg.classoption:
            args.extend(["-V", f"classoption={cfg.classoption}"])
        if cfg.paper:
            args.extend(["-V", f"papersize={cfg.paper}"])

        # geometry: 個別 margin を 1 引数に集約
        parts: List[str] = []
        if cfg.margin_top:
            parts.append(f"top={cfg.margin_top}")
        if cfg.margin_bottom:
            parts.append(f"bottom={cfg.margin_bottom}")
        if cfg.margin_left:
            parts.append(f"left={cfg.margin_left}")
        if cfg.margin_right:
            parts.append(f"right={cfg.margin_right}")
        if cfg.footskip:
            parts.append(f"footskip={cfg.footskip}")
        if parts:
            args.extend(["-V", f"geometry:{','.join(parts)}"])
        return args

    def _filters(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        args: List[str] = []
        builtin = resource_dir / "filters" / "default_filter.lua"
        if builtin.exists():
            args.extend(["--lua-filter", str(builtin)])
        if cfg.lua_filter:
            args.extend(["--lua-filter", cfg.lua_filter])
        if cfg.pandoc_crossref:
            args.extend(["--filter", "pandoc-crossref"])
        return args

    def _template(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        args: List[str] = []
        if cfg.template_file:
            args.append(f"--template={cfg.template_file}")
        header = resource_dir / "templates" / "latex_header_base.tex"
        if header.exists():
            args.extend(["--include-in-header", str(header)])
        return args

    def _csl(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        # CSL は実際に bibliography が指定されているときのみ適用
        # (citeproc チェック時の補助スタイル指定としても扱う)
        if not (cfg.bibliography_files or cfg.citeproc):
            return []
        args: List[str] = []
        csl = resource_dir / "templates" / "default.csl"
        if csl.exists():
            args.extend(["--csl", str(csl)])
        return args


class TypstAdapter(EngineAdapter):
    """Typst engine 向け args 組み立て.

    - LaTeX 専用項目 (documentclass / classoption / footskip / shell-escape) は黙って無視
    - paper は _TYPST_PAPER_MAP で変換
    - margin は個別 -V margin-XXX 変数で渡す
    - default_filter.lua と pandoc-crossref は LaTeX 専用なのでスキップ (A-2-e, A-2-f)
    - CSL パスは Windows でも `\\` を `/` に正規化 (A-2-g)
    - ユーザー指定テンプレが無いときのみ default_typst.typ を適用
    """

    name = "typst"

    def _engine_specific(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        args: List[str] = []
        # --pdf-engine は PDF 出力時のみ
        if cfg.output_format == "pdf":
            args.append("--pdf-engine=typst")

        if cfg.paper:
            mapped = _TYPST_PAPER_MAP.get(cfg.paper, cfg.paper)
            args.extend(["-V", f"papersize={mapped}"])

        if cfg.margin_top:
            args.extend(["-V", f"margin-top={cfg.margin_top}"])
        if cfg.margin_bottom:
            args.extend(["-V", f"margin-bottom={cfg.margin_bottom}"])
        if cfg.margin_left:
            args.extend(["-V", f"margin-left={cfg.margin_left}"])
        if cfg.margin_right:
            args.extend(["-V", f"margin-right={cfg.margin_right}"])
        # documentclass / classoption / footskip は Typst では未対応 → 無視
        return args

    def _filters(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        args: List[str] = []
        # default_filter.lua は LaTeX 数式環境を RawInline("latex") に変換するため Typst では適用しない
        if cfg.lua_filter:
            args.extend(["--lua-filter", cfg.lua_filter])
        # pandoc-crossref は Typst writer 未対応のためスキップ
        return args

    def _template(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        args: List[str] = []
        if cfg.template_file:
            # ユーザー指定優先
            args.append(f"--template={cfg.template_file}")
            return args
        typst_tpl = resource_dir / "templates" / "default_typst.typ"
        if typst_tpl.exists():
            args.append(f"--template={typst_tpl}")
            args.extend(["-V", "lang=ja"])
        return args

    def _csl(self, cfg: LogicalConfig, resource_dir: Path) -> List[str]:
        # CSL は実際に bibliography が指定されているときのみ適用
        # (Typst が #set bibliography(...) を生成する際の sandbox 制約を回避するため)
        if not (cfg.bibliography_files or cfg.citeproc):
            return []
        args: List[str] = []
        csl = resource_dir / "templates" / "default.csl"
        if csl.exists():
            # Typst 文字列内の `\` がエスケープ扱いされるため forward slash に正規化 (A-2-g)
            # NOTE: Windows では `C:/...` で動くが、Linux/macOS の絶対パスは Typst の path sandbox
            #       で project root 配下と解釈されるため、CSL ファイルを project 外に置くと解決
            #       できない既知の制約あり (Typst 0.13 時点)
            normalized = str(csl).replace("\\", "/")
            args.extend(["--csl", normalized])
        return args
