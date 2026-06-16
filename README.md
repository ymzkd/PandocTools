# Pandoc GUI Converter

Windows用のPandoc GUIアプリケーション - MarkdownファイルをPDF、TeX、DOCXに変換

## 概要

Pandoc GUI Converterは、コマンドラインでのPandoc操作を直感的なGUIで実行できるWindowsデスクトップアプリケーションです。複雑なPandocオプションの管理、複数ファイルの一括変換、設定のプロファイル保存などが可能です。

## 主な機能

- **直感的なGUI**: タブ形式で整理された分かりやすいユーザーインターフェース
- **高度なファイル管理**: 順序変更、追加、削除、リスト内ドラッグ&ドロップ対応
- **ドラッグ&ドロップ**: ファイルを直接ドラッグして追加可能
- **プロファイル管理**: よく使うオプション組み合わせをYAMLで保存・読み込み
- **リアルタイム出力**: 変換中の進行状況とエラーをリアルタイム表示
- **豊富なオプション**: Pandocの主要オプションをGUIで設定可能
- **複数エンジン対応**: PDFエンジンとしてxelatex等のLaTeX系に加えTypstも選択可能
- **CLI版**: GUIと同じプリセット・変換ロジックをコマンドライン（`pandoctools`）からも利用可能

## 必要な環境

- Python 3.9以上
- Pandoc (別途インストールが必要)
- TeX Live または MiKTeX (PDF/LaTeX出力時)
- Typst (Optional, Typst出力時)
- pandoc-crossref (Optional)

## インストール・実行方法

```powershell
# uv をインストール
pip install uv

# 環境・パッケージセットアップ
uv sync

# GUIアプリケーションの実行
uv run src/main.py
```

> `.venv` が壊れている場合（別マシンでの作成物がクラウド同期されたとき等）は、`.venv` を削除して `uv sync` で作り直してください。

## CLI（コマンドライン版）

GUIと同じプリセット（プロファイル）・変換ロジックを、コマンドラインからも利用できます。GUIのカスタム設定で変換が失敗するケースを再現・切り分けしたり、AIエージェントに修正を依頼したりする用途に向いています。CLIはQtに依存せず、`pandoc` / `typst` / `xelatex` がPATHにあれば動作します。

### インストール

`pandoctools` コマンドをPATHに導入します（隔離環境にインストールされ、GUI用の`.venv`とは独立します）。

```powershell
# 開発（editable）インストール
uv tool install --editable .
#   または pipx install -e .
```

### 使い方

```powershell
# 既定プロファイル（xelatex）で変換
pandoctools convert input.md

# Typstデフォルト設定で変換
pandoctools convert input.md --profile typst

# プロファイルをベースに一部だけ上書き
pandoctools convert input.md --profile compact --engine lualatex --fontsize 12pt --toc

# 実行せず、組み立てたpandocフルコマンドと設定を確認（切り分け用）
pandoctools convert input.md --dry-run

# 中間ソース（.tex/.typ）を出力して原因を調査
pandoctools convert input.md --to tex   -o out.tex
pandoctools convert input.md --engine typst --to typst -o out.typ

# 利用可能なプロファイル一覧
pandoctools profiles
```

複数の入力ファイルは既定で結合（merge）され、`--batch`で個別変換になります。`.bib`ファイルは参考文献として自動認識されます。変換失敗時は、エラー行が中間ソース（.tex/.typ）の行であることや`--to`での調査方法を案内するヒントを表示します。

## 使用方法

### 基本的な変換

1. **基本設定**タブで**ファイル選択**ボタンからMarkdownファイルを選択
2. ファイルリストで順序を調整（↑上へ、↓下へボタンまたは直接ドラッグ）
3. 出力形式（PDF、TeX、DOCX）を選択
4. 必要に応じて出力ディレクトリと出力ファイル名を設定
5. **変換実行**ボタンをクリック

### ファイル管理機能

**ファイル追加・管理**:
- **ファイル選択**: ファイルを選択してリストに追加（重複チェック付き）
- **フォルダ選択**: フォルダ内のMarkdownファイルを一括追加
- **全クリア**: ファイルリストを全消去
- **参考文献ファイル**: .bibファイルは自動的に認識され、変換時に--bibliographyオプションが適用されます

**リスト操作**:
- **↑上へ/↓下へ**: ファイルの順序を変更
- **削除**: 選択したファイルをリストから削除
- **ドラッグ&ドロップ**: ファイルを直接リストに追加
- **リスト内ドラッグ**: ファイルアイテムを直接ドラッグして順序変更

### 出力設定

**出力ディレクトリ**: 変換されたファイルの保存先を指定

**出力ファイル名（結合変換時）**:
- **自動生成（デフォルト）**: `最初のファイル名_merged.pdf`
- **カスタム名**: 出力ファイル名テキストボックスに任意の名前を入力

### 変換モード

**結合変換（デフォルト）**:
- 複数ファイルを順序通りに結合して一つのPDFを生成
- カスタムファイル名または自動生成名で出力

**個別変換**:
- 「複数ファイルを結合して一つのファイルに変換」のチェックを外す
- 各ファイルを個別のPDFに変換

### プロファイルの活用

1. **プロファイル**タブでよく使う設定を保存
2. 次回以降は**読み込み**で設定を復元
3. デフォルトプロファイルが用意済み

### プロジェクトファイル（Pandoc Defaults File）

複数ファイルと設定をプロジェクトとして管理できます：

**プロジェクトファイルの作成**:
1. 入力ファイルと設定を行う
2. **プロジェクト保存**ボタンでYAMLファイルを保存
3. 次回は**プロジェクト読み込み**で一括復元

**プロジェクトファイルの特徴**:
- Pandoc defaults file形式（YAML）で保存
- 入力ファイル、出力設定、Pandocオプションを一括管理
- 相対パスで保存され、プロジェクトフォルダ間での移動が可能
- .bibファイルは自動的に参考文献として認識

### 高度な設定

**オプション設定**タブで以下を設定可能（縦スクロール対応）：
- 基本オプション（PDFエンジン、ドキュメントクラス、Markdown拡張等）
- 追加Luaフィルター（内蔵のdefault_filter.luaは常時適用）
- テンプレートファイル
- チェックボックスオプション（改行保持、目次生成等）
- カスタムPandoc引数

### LaTeX行列のサポート

LaTeXでは、デフォルトで行列の列数が10列に制限されています。このアプリケーションでは、MaxMatrixColsを自動的に設定して大きな行列をサポートします。

**特徴**:
- 12列以上の大きな行列が自動的に処理されます
- 内蔵ヘッダーファイルでMaxMatrixColsが設定されています
- 元のMarkdownファイルには影響を与えません

**使用例**:
```markdown
$$
\begin{bmatrix}
a_{11} & a_{12} & a_{13} & a_{14} & a_{15} & a_{16} & a_{17} & a_{18} & a_{19} & a_{20} & a_{21} & a_{22} \\
b_{11} & b_{12} & b_{13} & b_{14} & b_{15} & b_{16} & b_{17} & b_{18} & b_{19} & b_{20} & b_{21} & b_{22}
\end{bmatrix}
$$
```

### 文字サイズ・余白・レイアウトの調整

**文字サイズの調整**:
**オプション設定**タブの「カスタムPandoc引数」欄に以下のような引数を追加できます：

```
-V fontsize=12pt    # 12ポイント（標準）
-V fontsize=10pt    # 10ポイント（小さめ）
-V fontsize=14pt    # 14ポイント（大きめ）
```

**余白の調整**:
```
-V geometry:margin=2cm                          # 上下左右すべて2cm
-V geometry:top=2cm,bottom=2cm,left=3cm,right=3cm  # 個別指定
-V geometry:margin=1in                          # 上下左右すべて1インチ
-V geometry:margin=15mm                         # 上下左右すべて15mm
```

**紙サイズの指定**:
```
-V papersize=a4        # A4サイズ（デフォルト）
-V papersize=letter    # レターサイズ
-V papersize=a3        # A3サイズ
-V papersize=b4        # B4サイズ
```

**行間の調整**:
```
-V linestretch=1.2     # 行間を1.2倍に設定
-V linestretch=1.5     # 行間を1.5倍に設定（広め）
```

**その他のレイアウトオプション**:
```
-V classoption=10pt,a4paper,twoside    # 10pt、A4、両面印刷用
-V classoption=12pt,b5paper            # 12pt、B5サイズ
```

**使用例**（コンパクトな文書の場合）:
```
-V fontsize=10pt
-V geometry:margin=15mm
-V linestretch=1.1
-V classoption=10pt,a4paper
```

**使用例**（読みやすい文書の場合）:
```
-V fontsize=12pt
-V geometry:margin=25mm
-V linestretch=1.3
-V classoption=12pt,a4paper
```

### bxjsarticle ドキュメントクラスのオプション

現在デフォルトで使用している`bxjsarticle`は日本語LaTeX用のドキュメントクラスです。以下のオプションが利用可能です：

**文字サイズオプション**:
- `10pt`, `11pt`, `12pt`, `14pt`, `17pt`, `20pt`, `25pt`

**紙サイズオプション**:
- `a3paper`, `a4paper`, `a5paper`, `b4paper`, `b5paper`
- `letterpaper`, `legalpaper`, `executivepaper`

**レイアウトオプション**:
- `oneside` / `twoside`: 片面印刷用 / 両面印刷用レイアウト
- `onecolumn` / `twocolumn`: 1段組 / 2段組
- `landscape`: 横向き印刷
- `draft`: ドラフトモード（画像の代わりに枠を表示）

**設定例**:
```
-V documentclass=bxjsarticle
-V classoption=11pt,a4paper,twoside
```

## プロジェクトファイル例

```yaml
input-files:
- introduction.md
- methodology.md
- results.md
- conclusion.md
bibliography:
- references.bib
number-sections: true
citeproc: true
variables:
  fontsize: 11pt
  papersize: a4paper
  geometry:
  - top=25mm
  - bottom=25mm
  - left=30mm
  - right=25mm
```

## 実行ファイルの作成

スタンドアロンの実行ファイル（.exe）を作成して、Python環境がないPCでも動作させることができます。

### 1. PyInstallerのインストール

```powershell
# PyInstallerをインストール
pip install pyinstaller
```

### 2. 実行ファイルのビルド

```powershell
# 基本的な実行ファイル作成
python -m PyInstaller --name pandoc-gui --onefile --noconsole --add-data "profiles;profiles" --add-data "src/filters;filters" --add-data "src/templates;templates" src/main.py

# より詳細なオプション付き（推奨）
python -m PyInstaller ^
  --name "Pandoc GUI Converter" ^
  --onefile ^
  --noconsole ^
  --add-data "profiles;profiles" ^
  --add-data "src/filters;filters" ^
  --add-data "src/templates;templates" ^
  --icon=src/resources/icon.ico ^
  --version-file=version_info.txt ^
  --distpath=release ^
  src/main.py
```

### 3. ビルドオプションの説明

- `--onefile`: 単一の実行ファイルを作成
- `--noconsole`: コンソールウィンドウを表示しない（GUIアプリの場合）
- `--add-data "profiles;profiles"`: プロファイルフォルダを含める
- `--add-data "src/filters;filters"`: 内蔵フィルターを含める
- `--add-data "src/templates;templates"`: LaTeXヘッダーテンプレートを含める
- `--icon`: アプリケーションアイコンを指定（オプション）
- `--distpath`: 出力ディレクトリを指定

### 4. 生成されるファイル

```
release/
└─ Pandoc GUI Converter.exe  # 実行ファイル（約30-50MB）
```

### 5. 配布方法

1. 生成された `.exe` ファイルを配布
2. 配布先のPCに **Pandoc** がインストールされている必要があります
3. **TeX Live** または **MiKTeX** が PDF 生成に必要です

## トラブルシューティング

### Pandocが見つからない場合
- PandocがPATHに設定されているか確認
- コマンドプロンプトで `pandoc --version` が実行できるか確認

### 日本語PDF生成で文字化けする場合
- XeLaTeXと日本語フォントが必要
- TeX Live or MiKTeXのインストールを推奨

### パフォーマンス問題
- 大きなファイルの変換には時間がかかります
- 複数ファイル変換時は順次処理のため待機時間があります

## 開発者向け情報

### プロジェクト構成

```
pandoc-gui/
├─ .venv/                    # uv管理の仮想環境
├─ profiles/                 # YAML設定ファイル（プロファイル）
│   ├─ default.yml          # デフォルト（xelatex）
│   ├─ compact.yml          # コンパクト設定
│   └─ typst.yml            # Typst出力設定
├─ src/
│   ├─ main.py              # GUIメインアプリケーション
│   ├─ cli.py               # CLIエントリ（pandoctools）
│   ├─ ui_main.py           # GUI定義（自動生成）
│   ├─ pandoc_process.py    # 非同期Pandoc実行（GUI用）
│   ├─ engines.py           # EngineAdapter（LaTeX/Typst向け引数生成）
│   ├─ config.py            # プロファイル管理（v1/v2）
│   ├─ common.py            # 共通定数・パス解決
│   ├─ defaults.py          # プロジェクトファイル（Pandoc defaults）処理
│   ├─ filters/             # 内蔵Luaフィルター
│   │   ├─ default_filter.lua   # LaTeX数式環境の処理（LaTeX系で常時適用）
│   │   └─ typst_tag.lua        # Typstで \tag 式番号を右寄せ復元
│   └─ templates/           # LaTeXヘッダ・CSL・Typstテンプレート
└─ pyproject.toml           # プロジェクト設定（GUI/CLIのエントリポイント定義）
```

### 技術スタック

- **PyQt6**: GUIフレームワーク
- **QProcess**: 非同期プロセス実行
- **EngineAdapter**: 論理設定 → エンジン別Pandoc引数の変換層（LaTeX / Typst）
- **uv**: 高速パッケージ管理・CLIツール導入（`uv tool install`）
- **YAML**: 設定ファイル形式
- **PyInstaller**: 実行ファイル作成 