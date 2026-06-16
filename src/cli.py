"""
PandocTools CLI

GUI と同じプリセット (プロファイル) / 標準書き出し設定を、コマンドラインから利用するための
エントリポイント。GUI の変換ロジック (engines.LogicalConfig + EngineAdapter) と
プロファイル (config) をそのまま共有する。

狙い:
  - GUI のカスタムプリセットで変換が失敗するケースを、CLI で再現・切り分けできるようにする
  - 実行する pandoc フルコマンドを常に表示し、--dry-run で実行せず確認できる
  - これにより AI エージェント等に「このコマンドで失敗する。直して」と依頼しやすくする

使い方の例:
  python src/cli.py convert input.md
  python src/cli.py convert input.md --profile compact -o out.pdf
  python src/cli.py convert input.md --engine typst --dry-run
  python src/cli.py convert a.md b.md --batch --output-dir out/
  python src/cli.py profiles
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# src/ をスクリプトディレクトリとして実行する前提 (python src/cli.py ...)
from common import RESOURCE_DIR
from engines import LogicalConfig, get_adapter, is_typst_mode
from config import (
    get_available_profiles,
    resolve_profile,
    is_v2_profile,
    profile_to_logical_config,
    profile_extras,
)

# bibliography とみなす拡張子 (GUI と同じ挙動)
_BIB_SUFFIXES = {".bib"}


# --- 表示ユーティリティ -------------------------------------------------------

def _quote(arg: str) -> str:
    """コマンド表示用の最小限のクォート (コピーして読みやすい程度)."""
    if arg == "" or any(c in arg for c in ' \t"\''):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg


def _format_command(cmd: List[str]) -> str:
    return " ".join(_quote(a) for a in cmd)


def _eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


# --- pandoc 実行 --------------------------------------------------------------

def _check_pandoc() -> bool:
    try:
        r = subprocess.run(
            ["pandoc", "--version"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return r.returncode == 0
    except FileNotFoundError:
        return False


def _resource_path(input_files: List[str]) -> str:
    """入力ファイル群のディレクトリを os.pathsep 区切りで結合 (重複除去・ソート)."""
    dirs = {str(Path(f).parent.resolve()) for f in input_files}
    return os.pathsep.join(sorted(dirs))


def run_pandoc(input_files: List[str], output_file: str, extra_args: List[str],
               dry_run: bool = False) -> int:
    """pandoc を 1 回実行する。実行コマンドを常に表示する。

    戻り値は pandoc の終了コード (dry-run 時は 0)。
    """
    input_files = [str(Path(f).resolve()) for f in input_files]
    output_file = str(Path(output_file).resolve())
    resource_path = _resource_path(input_files)
    # SVG/Inkscape がローカル画像へ直接アクセスできるよう作業ディレクトリを入力側に置く
    working_dir = str(Path(input_files[0]).parent.resolve())

    cmd = (
        ["pandoc", *input_files, "-o", output_file,
         "--resource-path", resource_path]
        + extra_args
    )

    print("COMMAND:")
    print("  " + _format_command(cmd))
    print(f"CWD: {working_dir}")

    if dry_run:
        print("(--dry-run: pandoc は実行していません)")
        return 0

    if not _check_pandoc():
        _eprint("エラー: pandoc が見つかりません。インストールと PATH 設定を確認してください。")
        return 127

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    print("--- pandoc output ---")
    proc = subprocess.run(cmd, cwd=working_dir)
    print("--- result ---")
    print(f"exit code: {proc.returncode}")
    if Path(output_file).exists():
        print(f"output: {output_file}")
    else:
        print(f"output: {output_file} (生成されませんでした)")
    return proc.returncode


# --- 入力ファイルの仕分け / 出力パス決定 --------------------------------------

def _split_inputs(paths: List[str]) -> tuple[List[str], List[str]]:
    """.bib を bibliography として分離する (GUI と同じ仕分け)."""
    inputs: List[str] = []
    bibs: List[str] = []
    for p in paths:
        if Path(p).suffix.lower() in _BIB_SUFFIXES:
            bibs.append(p)
        else:
            inputs.append(p)
    return inputs, bibs


def _output_path(stem: str, ext: str, output: Optional[str],
                 output_dir: Optional[str], default_dir: str) -> str:
    if output:
        out = Path(output)
        if out.suffix:
            return str(out)
        return str(out.with_suffix("." + ext))
    base = Path(output_dir) if output_dir else Path(default_dir)
    return str(base / f"{stem}.{ext}")


# --- オーバーライド適用 -------------------------------------------------------

def _apply_overrides(cfg: LogicalConfig, args: argparse.Namespace) -> LogicalConfig:
    """コマンドラインの個別フラグ (指定されたものだけ) を LogicalConfig に上書きする."""
    if args.engine is not None:
        cfg.engine = args.engine
    if args.to is not None:
        cfg.output_format = args.to
    if args.fontsize is not None:
        cfg.fontsize = args.fontsize
    if args.paper is not None:
        cfg.paper = args.paper
    if args.margin is not None:
        cfg.margin_top = cfg.margin_bottom = cfg.margin_left = cfg.margin_right = args.margin
    if args.margin_top is not None:
        cfg.margin_top = args.margin_top
    if args.margin_bottom is not None:
        cfg.margin_bottom = args.margin_bottom
    if args.margin_left is not None:
        cfg.margin_left = args.margin_left
    if args.margin_right is not None:
        cfg.margin_right = args.margin_right
    if args.footskip is not None:
        cfg.footskip = args.footskip
    if args.linestretch is not None:
        cfg.linestretch = args.linestretch
    if args.toc is not None:
        cfg.toc = args.toc
    if args.number_sections is not None:
        cfg.number_sections = args.number_sections
    if args.standalone is not None:
        cfg.standalone = args.standalone
    if args.citeproc is not None:
        cfg.citeproc = args.citeproc
    if args.crossref is not None:
        cfg.pandoc_crossref = args.crossref
    if args.wrap_preserve is not None:
        cfg.wrap_preserve = args.wrap_preserve
    if args.documentclass is not None:
        cfg.documentclass = args.documentclass
    if args.classoption is not None:
        cfg.classoption = args.classoption
    if getattr(args, "from_", None) is not None:
        cfg.markdown_extensions = args.from_
    if args.template is not None:
        cfg.template_file = args.template
    if args.lua_filter is not None:
        cfg.lua_filter = args.lua_filter
    # -V key=val (繰り返し) と --arg X (繰り返し) は custom_args 末尾へ追加
    for kv in (args.var or []):
        cfg.custom_args.extend(["-V", kv])
    for raw in (args.arg or []):
        cfg.custom_args.append(raw)
    return cfg


def _print_config(cfg: LogicalConfig) -> None:
    adapter = get_adapter(cfg)
    print("RESOLVED CONFIG:")
    print(f"  adapter        : {adapter.name}  (typst_mode={is_typst_mode(cfg)})")
    fields = [
        ("output_format", cfg.output_format), ("engine", cfg.engine),
        ("fontsize", cfg.fontsize), ("paper", cfg.paper),
        ("margin(t/b/l/r)", f"{cfg.margin_top}/{cfg.margin_bottom}/{cfg.margin_left}/{cfg.margin_right}"),
        ("footskip", cfg.footskip), ("linestretch", cfg.linestretch),
        ("toc", cfg.toc), ("number_sections", cfg.number_sections),
        ("standalone", cfg.standalone), ("citeproc", cfg.citeproc),
        ("pandoc_crossref", cfg.pandoc_crossref), ("wrap_preserve", cfg.wrap_preserve),
        ("markdown_extensions", cfg.markdown_extensions),
        ("documentclass", cfg.documentclass), ("classoption", cfg.classoption),
        ("template_file", cfg.template_file), ("lua_filter", cfg.lua_filter),
        ("bibliography", cfg.bibliography_files), ("custom_args", cfg.custom_args),
    ]
    for name, value in fields:
        print(f"  {name:<18}: {value}")


# --- サブコマンド: convert ----------------------------------------------------

def cmd_convert(args: argparse.Namespace) -> int:
    inputs, bibs = _split_inputs(args.inputs)
    if not inputs:
        _eprint("エラー: 変換対象の入力ファイル (Markdown 等) がありません。")
        return 2
    for f in inputs + bibs:
        if not Path(f).exists():
            _eprint(f"エラー: ファイルが存在しません: {f}")
            return 2

    # プロファイル → LogicalConfig
    try:
        profile_data = resolve_profile(args.profile)
    except ValueError as e:
        _eprint(str(e))
        return 2
    cfg = profile_to_logical_config(profile_data)
    cfg.bibliography_files.extend(bibs)
    cfg = _apply_overrides(cfg, args)

    extras = profile_extras(profile_data)
    schema = "v2" if is_v2_profile(profile_data) else "v1"

    adapter = get_adapter(cfg)
    extra_args = adapter.build_args(cfg, RESOURCE_DIR)
    ext = adapter.output_extension(cfg)

    print("=== PandocTools CLI ===")
    print(f"profile: {args.profile} ({schema})")
    print(f"engine : {cfg.engine}   format: {cfg.output_format} -> .{ext}")
    print(f"inputs : {inputs}")
    if bibs:
        print(f"bib    : {bibs}")
    if args.print_config or args.dry_run:
        _print_config(cfg)

    # マージ判定: 単一入力はそのまま。複数入力は --batch 指定が無ければマージ。
    merge = extras["merge_files"] if args.merge is None else args.merge
    if args.batch:
        merge = False

    default_dir = str(Path(inputs[0]).parent.resolve())

    # 出力ファイル名のベース (プロファイルの output_filename / --output より弱い)
    profile_name = extras["output_filename"]

    rc = 0
    if len(inputs) == 1:
        stem = profile_name or Path(inputs[0]).stem
        out = _output_path(stem, ext, args.output, args.output_dir, default_dir)
        rc = run_pandoc(inputs, out, extra_args, dry_run=args.dry_run)
    elif merge:
        stem = profile_name or (Path(inputs[0]).stem + "_merged")
        out = _output_path(stem, ext, args.output, args.output_dir, default_dir)
        rc = run_pandoc(inputs, out, extra_args, dry_run=args.dry_run)
    else:
        # batch: 各ファイルを個別変換
        for i, f in enumerate(inputs, 1):
            stem = Path(f).stem
            out = _output_path(stem, ext, None, args.output_dir, default_dir)
            print(f"\n--- ({i}/{len(inputs)}) {Path(f).name} ---")
            r = run_pandoc([f], out, extra_args, dry_run=args.dry_run)
            rc = rc or r

    if rc != 0 and not args.dry_run:
        _print_failure_hint(cfg)
    return rc


def _print_failure_hint(cfg: LogicalConfig) -> None:
    """変換失敗時に、原因切り分けの手掛かりをエージェント/人間向けに提示する."""
    _eprint("--- 診断のヒント ---")
    if cfg.output_format == "pdf":
        to = "typst" if is_typst_mode(cfg) else "tex"
        ext = "typ" if is_typst_mode(cfg) else "tex"
        _eprint(
            f"PDF 生成で失敗しました。エラー中の行番号は Markdown ではなく中間ソース (.{ext}) の行です。\n"
            f"  1) 同じ設定に `--to {to}` を足すと中間ソースを出力できます:  ... --to {to} -o out.{ext}\n"
            f"  2) その out.{ext} の該当行を見れば、どの数式/記法が原因か特定できます。\n"
            f"  3) 最小再現には、問題箇所だけを抜き出した小さな .md で試すと速いです。"
        )
    else:
        _eprint(
            "変換に失敗しました。上の pandoc 出力のメッセージを確認してください。\n"
            "  `--dry-run` で実行コマンドだけを表示し、生 pandoc を直接叩いて切り分けることもできます。"
        )


# --- サブコマンド: profiles ---------------------------------------------------

def cmd_profiles(args: argparse.Namespace) -> int:
    names = get_available_profiles()
    if not names:
        print("(プロファイルがありません)")
        return 0
    print("利用可能なプロファイル:")
    for name in names:
        data = resolve_profile(name)
        schema = "v2" if is_v2_profile(data) else "v1"
        fmt = data.get("output_format", "pdf")
        print(f"  {name:<16} [{schema}] output_format={fmt}")
    return 0


# --- argparse -----------------------------------------------------------------

def _add_override_flags(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("プロファイル上書き (指定したものだけ上書き)")
    g.add_argument("--engine", help="pdf-engine / 組版エンジン (xelatex, lualatex, tectonic, typst ...)")
    g.add_argument("-t", "--to", "--output-format", dest="to",
                   help="出力フォーマット (pdf, typst, docx, html, tex ...)")
    g.add_argument("--fontsize")
    g.add_argument("--paper", help="papersize (a4paper, letterpaper ...)")
    g.add_argument("--margin", help="全余白を一括指定 (例: 20mm)")
    g.add_argument("--margin-top")
    g.add_argument("--margin-bottom")
    g.add_argument("--margin-left")
    g.add_argument("--margin-right")
    g.add_argument("--footskip")
    g.add_argument("--linestretch")
    g.add_argument("--documentclass")
    g.add_argument("--classoption")
    g.add_argument("--from", dest="from_", help="入力フォーマット/拡張 (例: markdown+hard_line_breaks)")
    g.add_argument("--template", help="テンプレートファイル")
    g.add_argument("--lua-filter", help="追加 Lua フィルタ")
    g.add_argument("--toc", action=argparse.BooleanOptionalAction, default=None)
    g.add_argument("--number-sections", action=argparse.BooleanOptionalAction, default=None)
    g.add_argument("--standalone", action=argparse.BooleanOptionalAction, default=None)
    g.add_argument("--citeproc", action=argparse.BooleanOptionalAction, default=None)
    g.add_argument("--crossref", action=argparse.BooleanOptionalAction, default=None,
                   help="pandoc-crossref フィルタ")
    g.add_argument("--wrap-preserve", action=argparse.BooleanOptionalAction, default=None)
    g.add_argument("-V", "--var", action="append", metavar="KEY=VAL",
                   help="pandoc 変数を追加 (繰り返し可)")
    g.add_argument("--arg", action="append", metavar="ARG",
                   help="任意の pandoc 引数を末尾に追加 (繰り返し可)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pandoctools",
        description="GUI と同じプリセットで Pandoc 変換を行う CLI",
    )
    sub = parser.add_subparsers(dest="command")

    pc = sub.add_parser("convert", help="ファイルを変換する")
    pc.add_argument("inputs", nargs="+", help="入力ファイル (.md 等。.bib は参考文献として扱う)")
    pc.add_argument("--profile", default="default", help="プロファイル名 or yml パス (既定: default)")
    pc.add_argument("-o", "--output", help="出力ファイルパス (拡張子省略時はフォーマットから補完)")
    pc.add_argument("--output-dir", help="出力ディレクトリ")
    pc.add_argument("--merge", action=argparse.BooleanOptionalAction, default=None,
                    help="複数入力を結合する/しない (既定はプロファイル設定)")
    pc.add_argument("--batch", action="store_true", help="複数入力を個別に変換する")
    pc.add_argument("--dry-run", action="store_true", help="実行せずコマンドと設定だけ表示")
    pc.add_argument("--print-config", action="store_true", help="解決後の LogicalConfig を表示")
    _add_override_flags(pc)
    pc.set_defaults(func=cmd_convert)

    pp = sub.add_parser("profiles", help="利用可能なプロファイル一覧")
    pp.set_defaults(func=cmd_profiles)

    return parser


def _setup_utf8() -> None:
    """Windows コンソールでも日本語が化けないよう stdout/stderr を UTF-8 にする。

    あわせて行バッファに切り替える。パイプ (... 2>&1 | ...) 経由で読まれるときに
    自前の stdout と pandoc サブプロセスの stderr が時系列どおりに混ざるようにするため。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", line_buffering=True)  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main(argv: Optional[List[str]] = None) -> int:
    _setup_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
