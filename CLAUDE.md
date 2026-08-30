# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PandocTools is a Windows GUI application for Pandoc document conversion, built with Python and PyQt6. It provides an intuitive interface for converting Markdown files to PDF, TeX, and DOCX formats using Pandoc, with support for complex LaTeX matrices, file merging, configuration profiles, and project file management.

## Development Environment Setup

### Prerequisites
- Python 3.9+
- Pandoc (installed separately)
- uv package manager

### Setup Commands
```powershell
# Create virtual environment
uv venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
uv pip install PyQt6 pypandoc pyyaml

# For building executables
uv pip install pyinstaller
```

### Running the Application
```powershell
python src/main.py
```

### Building Executable
```powershell
python -m PyInstaller --name "Pandoc GUI Converter" --onefile --noconsole --add-data "profiles;profiles" --add-data "src/filters;filters" --add-data "src/templates;templates" src/main.py
```

## Architecture

### Core Components
- **src/main.py**: Main application entry point and MainWindow class with GUI event handling
- **src/ui_main.py**: Generated PyQt6 UI definitions (auto-generated, do not edit manually)
- **src/pandoc_process.py**: Asynchronous Pandoc process execution using QProcess
- **src/config.py**: YAML profile management (load/save/delete configurations)
- **src/defaults.py**: Pandoc defaults file (project file) processing and conversion

### Key Features Implementation
- **File Management**: Drag & drop support, batch processing, file ordering, automatic .bib file recognition
- **Conversion Modes**: Single file, merged files, or individual batch conversion
- **LaTeX Matrix Support**: Automatic MaxMatrixCols setting via built-in header files
- **Profile System**: YAML-based configuration saving/loading in profiles/ directory
- **Project Files**: Pandoc defaults file support for multi-file project management
- **Real-time Output**: Live process output display using Qt signals

### Data Flow
1. User selects files via GUI (MainWindow)
2. Configuration collected from UI elements into extra_args
3. PandocWorker executes pandoc subprocess asynchronously
4. Output/errors streamed back to GUI via Qt signals
5. Temporary files cleaned up on completion

## File Structure

```
src/
├── main.py              # Main application logic
├── ui_main.py           # PyQt6 UI definitions
├── pandoc_process.py    # Async process execution
├── config.py            # Profile management
├── defaults.py          # Pandoc defaults file processing
├── filters/
│   ├── default_filter.lua   # Built-in Lua filter (LaTeX only)
│   ├── inline_svg.lua       # Inline <svg> / .svg references (both engines)
│   ├── typst_tag.lua        # Restore \tag equation numbers (typst)
│   ├── typst_crossref_tag.lua # Map crossref numbers onto \tag (typst)
│   └── eq_number.lua        # Wrap display math in equation (LaTeX only)
└── templates/
    ├── latex_header_base.tex # LaTeX header with MaxMatrixCols
    └── default.csl          # Default citation style

profiles/                # YAML configuration files
├── default.yml          # App default (typst engine)
├── typst.yml            # Same as default.yml (kept for explicit selection)
├── xelatex.yml          # LaTeX path (bxjsarticle)
└── compact.yml          # Compact document (small font, narrow margins)
```

## Configuration

### Default Pandoc Arguments
The application always applies these base arguments:
- `--lua-filter=src/filters/default_filter.lua` (built-in filter; LaTeX only)
- `--lua-filter=src/filters/inline_svg.lua` (both engines): Markdown に直書きされた
  `<svg>...</svg>` (raw HTML) と `![](x.svg)` を PDF に載せる。latex/typst writer は
  raw HTML の `<svg>` を黙って捨て、`.svg` 参照も pandoc が `rsvg-convert` に丸投げ
  するため未インストール環境では画像だけ消える (終了コードは 0 のまま)。このフィルタが
  typst では SVG ソースを `#image(bytes(...), format: "svg")` として埋め込み、LaTeX では
  SVG を PDF に変換して `\includegraphics` に渡す。変換器は
  `rsvg-convert` → `inkscape` → `typst` の順に自動検出する。
  生成物は `%TEMP%/pandoctools-svg` に内容ハッシュ名でキャッシュされる
  (`PANDOCTOOLS_SVG_DIR` で変更可)。
- `--columns=999` (engines.py `DEFAULT_COLUMNS`): prevents Pandoc from fixing pipe-table column widths from the separator-row dash counts, which would otherwise wrap cells and produce uneven row heights. Overridden if the user supplies `--columns` in custom args.
- User-configurable options via GUI tabs

### 式番号 (eq_numbers)

既定は無効で、`\tag{...}` を書いた式と `{#eq:...}` ラベル付きの式だけに番号が付く。
`--eq-numbers` (CLI) / チェックボックス「式番号を振る」(GUI) / プロファイルの
`eq_numbers: true` を指定すると、すべての display 数式に通し番号を振る。

採番規則は両エンジンで一致させてある。実現手段は engine ごとに異なる。

| 書き方 | 挙動 |
| --- | --- |
| `$$ ... $$` | 通し番号を振る (採番が有効なときのみ)。カウンタを消費する |
| `$$ ... \nonumber $$` | 常に無番号。カウンタを消費しない |
| `$$ ... \tag{X} $$` | 常に原文の `X` を表示。カウンタを消費しない (LaTeX の `\tag` と同じ) |
| `$$ ... $$ {#eq:foo}` | 採番の有無によらず番号が付き、`@eq:foo` で参照できる |
| `\begin{align}` 等 | 環境が自前で採番するため通し番号の対象外 |

- xelatex: `eq_number.lua` が対象の DisplayMath を `\begin{equation}` で包み、
  採番自体は LaTeX の equation カウンタに委ねる。
- typst: 包む先の環境が無いため `typst_crossref_tag.lua` が上記カウンタの挙動を
  Lua で再現し、番号を `\tag{N}` へ集約する (描画は `typst_tag.lua`)。

注意点:
- 番号を抑制するのは `\nonumber` のみ。`\notag` は typst writer の TeX パーサが
  受け付けず、数式が生テキストに化けるため使わないこと。
- `equation*` / `align*` 環境は LaTeX では無番号になるが、typst writer は環境を
  剥がすため両エンジンで揃わない。無番号にしたい式には `\nonumber` を使う。
- `\tag` はカウンタを消費しないので、手動タグの番号 (例 `\tag{4}`) と自動採番の
  番号が重複しうる。手動タグと採番を混在させる文書では番号設計に注意する。
- `align` 等は LaTeX では行ごとに採番されるが、typst writer は環境を剥がすため
  無番号になる。カウンタの進み方も食い違うので**後続の式の番号までずれる**
  (実測: `$$a$$` / align 2 行 / `$$d$$` で xelatex は 1,2,3,4、typst は 1,2)。
  両エンジンで揃えたい文書では align を使わず、`aligned` を `$$...$$` に入れる
  (式全体で 1 番号) か、行ごとに `$$...$$` を分ける。

### Profile Format (YAML)
```yaml
output_format: pdf
extra_args:
  - --wrap=preserve
  - --pdf-engine=xelatex
  - -V
  - documentclass=bxjsarticle
  - -V
  - classoption=pandoc
merge_files: true
```

### Project File Format (Pandoc Defaults)
```yaml
input-files:
  - chapter1.md
  - chapter2.md
bibliography:
  - references.bib
number-sections: true
citeproc: true
variables:
  fontsize: 12pt
  papersize: a4paper
  geometry:
    - margin=25mm
```

### Document Formatting Options
Users can adjust font size, margins, and layout through the custom arguments field:

**Font Size**:
- `-V fontsize=10pt` (small), `-V fontsize=12pt` (standard), `-V fontsize=14pt` (large)

**Margins**:
- `-V geometry:margin=15mm` (narrow), `-V geometry:margin=25mm` (wide)
- `-V geometry:top=2cm,bottom=2cm,left=3cm,right=3cm` (individual margins)

**Paper Size**:
- `-V papersize=a4`, `-V papersize=letter`, `-V papersize=a3`

**Line Spacing**:
- `-V linestretch=1.1` (tight), `-V linestretch=1.4` (loose)

**bxjsarticle Class Options**:
- Font sizes: `10pt`, `11pt`, `12pt`, `14pt`, `17pt`, `20pt`, `25pt`
- Paper sizes: `a3paper`, `a4paper`, `a5paper`, `b4paper`, `b5paper`, `letterpaper`
- Layout: `oneside`/`twoside`, `onecolumn`/`twocolumn`, `landscape`, `draft`

## Development Notes

### UI Updates
- The src/ui_main.py is auto-generated from Qt Designer
- Manual edits to ui_main.py will be lost
- UI logic should be implemented in main.py event handlers

### Process Management
- Uses QProcess for non-blocking Pandoc execution
- Temporary files are created/cleaned automatically for LaTeX headers
- Process termination handled gracefully on app close

### Testing
No automated test framework is currently configured. Test manually by:
1. Running the GUI application
2. Testing various conversion scenarios
3. Verifying profile save/load functionality

### Japanese Language Support  
The application UI and documentation are primarily in Japanese, targeting Japanese LaTeX document processing with bxjsarticle document class.