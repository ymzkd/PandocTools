# Pandoc GUI Converter

Windows用のPandoc GUIアプリケーション - MarkdownファイルをPDF、HTML、DOCXなどに変換

## 概要

Pandoc GUI Converterは、コマンドラインでのPandoc操作を直感的なGUIで実行できるWindowsデスクトップアプリケーションです。複雑なPandocオプションの管理、複数ファイルの一括変換、設定のプロファイル保存などが可能です。

## 主な機能

- **直感的なGUI**: タブ形式で整理された分かりやすいユーザーインターフェース
- **高度なファイル管理**: 順序変更、追加、削除、リスト内ドラッグ&ドロップ対応
- **ドラッグ&ドロップ**: ファイルを直接ドラッグして追加可能
- **プロファイル管理**: よく使うオプション組み合わせをYAMLで保存・読み込み
- **リアルタイム出力**: 変換中の進行状況とエラーをリアルタイム表示
- **豊富なオプション**: Pandocの主要オプションをGUIで設定可能

## 必要な環境

- Windows 10/11
- Python 3.9以上
- Pandoc (別途インストールが必要)

## インストール・実行方法

### 1. 依存ツールのインストール

```powershell
# uv をインストール
pip install uv

# Pandoc をインストール (公式サイトからダウンロード)
# https://pandoc.org/installing.html
```

### 2. プロジェクトのセットアップ

```powershell
# プロジェクトディレクトリに移動
cd pandoc-gui

# 仮想環境を作成
uv venv

# 仮想環境をアクティベート
.\.venv\Scripts\Activate.ps1

# 依存パッケージをインストール
uv pip install PyQt6 pypandoc pyyaml
```

### 3. アプリケーションの実行

```powershell
python src/main.py
```

## 使用方法

### 基本的な変換

1. **基本設定**タブで**ファイル選択**ボタンからMarkdownファイルを選択
2. ファイルリストで順序を調整（↑上へ、↓下へボタンまたは直接ドラッグ）
3. 出力形式（PDF、HTML、DOCX等）を選択
4. 必要に応じて出力ディレクトリとカスタムファイル名を設定
5. **変換実行**ボタンをクリック

### ファイル管理機能

**ファイル追加・管理**:
- **ファイル選択**: 新規にファイルを選択（既存リストを置き換え）
- **フォルダ選択**: フォルダ内のMarkdownファイルを一括選択
- **ファイル追加**: 既存リストにファイルを追加（重複チェック付き）
- **全クリア**: ファイルリストを全消去

**リスト操作**:
- **↑上へ/↓下へ**: ファイルの順序を変更
- **削除**: 選択したファイルをリストから削除
- **ドラッグ&ドロップ**: ファイルを直接リストに追加
- **リスト内ドラッグ**: ファイルアイテムを直接ドラッグして順序変更

### 出力設定

**出力ディレクトリ**: 変換されたファイルの保存先を指定

**出力ファイル名（結合変換時）**:
- **自動生成（デフォルト）**: `最初のファイル名_merged.pdf`
- **カスタム名**: 「カスタムファイル名を使用」にチェックして任意の名前を指定

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

### 実行される実際のコマンド例

**単一ファイル変換時**:
```bash
pandoc input.md -o output.pdf --lua-filter=src/filters/default_filter.lua --wrap=preserve --pdf-engine=xelatex -V documentclass=bxjsarticle -V classoption=pandoc --from markdown+hard_line_breaks
```

**複数ファイル結合時（自動ファイル名）**:
```bash
pandoc chapter1.md chapter2.md chapter3.md -o chapter1_merged.pdf --lua-filter=src/filters/default_filter.lua --wrap=preserve --pdf-engine=xelatex -V documentclass=bxjsarticle -V classoption=pandoc --from markdown+hard_line_breaks
```

**複数ファイル結合時（カスタムファイル名）**:
```bash
pandoc chapter1.md chapter2.md chapter3.md -o "完全なマニュアル.pdf" --lua-filter=src/filters/default_filter.lua --wrap=preserve --pdf-engine=xelatex -V documentclass=bxjsarticle -V classoption=pandoc --from markdown+hard_line_breaks
```

**個別変換時**:
```bash
pandoc chapter1.md -o chapter1.pdf --lua-filter=src/filters/default_filter.lua --wrap=preserve --pdf-engine=xelatex -V documentclass=bxjsarticle -V classoption=pandoc --from markdown+hard_line_breaks
pandoc chapter2.md -o chapter2.pdf --lua-filter=src/filters/default_filter.lua --wrap=preserve --pdf-engine=xelatex -V documentclass=bxjsarticle -V classoption=pandoc --from markdown+hard_line_breaks
...
```

### 高度な設定

**オプション設定**タブで以下を設定可能（縦スクロール対応）：
- 基本オプション（PDFエンジン、ドキュメントクラス、Markdown拡張等）
- 追加Luaフィルター（内蔵のdefault_filter.luaは常時適用）
- テンプレートファイル
- CSSファイル (HTML出力用)
- 参考文献ファイル
- チェックボックスオプション（改行保持、目次生成等）
- カスタムPandoc引数

## プロファイル例

### PDF出力 (デフォルト)
```yaml
output_format: pdf
extra_args:
  - --wrap=preserve
  - --pdf-engine=xelatex
  - -V
  - documentclass=bxjsarticle
  - -V
  - classoption=pandoc
  - --from
  - markdown+hard_line_breaks
```

### HTML出力
```yaml
output_format: html
extra_args:
  - --wrap=preserve
  - --standalone
  - --toc
  - --number-sections
```

## 実行ファイルの作成

スタンドアロンの実行ファイル（.exe）を作成して、Python環境がないPCでも動作させることができます。

### 1. PyInstallerのインストール

```powershell
# 仮想環境をアクティベート
.\.venv\Scripts\Activate.ps1

# PyInstallerをインストール
uv pip install pyinstaller
```

### 2. 実行ファイルのビルド

```powershell
# 基本的な実行ファイル作成
pyinstaller --name pandoc-gui --onefile --noconsole --add-data "profiles;profiles" --add-data "src/filters;filters" src/main.py

# より詳細なオプション付き（推奨）
pyinstaller ^
  --name "Pandoc GUI Converter" ^
  --onefile ^
  --noconsole ^
  --add-data "profiles;profiles" ^
  --add-data "src/filters;filters" ^
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

### 6. トラブルシューティング

**ビルドエラーが発生する場合:**
```powershell
# キャッシュをクリア
pyinstaller --clean --onefile src/main.py
```

**実行ファイルが起動しない場合:**
```powershell
# コンソール表示有りでデバッグ
pyinstaller --onefile --console src/main.py
```

**ファイルサイズを小さくしたい場合:**
```powershell
# UPX圧縮を使用（別途UPXのインストールが必要）
pyinstaller --onefile --upx-dir=C:\upx src/main.py
```

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

## ライセンス

MIT License

## 開発者向け情報

### プロジェクト構成

```
pandoc-gui/
├─ .venv/                    # uv管理の仮想環境
├─ profiles/                 # YAML設定ファイル
│   ├─ default.yml          # デフォルトプロファイル
│   └─ sample_html.yml      # HTMLサンプルプロファイル
├─ src/
│   ├─ main.py              # メインアプリケーション
│   ├─ ui_main.py           # GUI定義
│   ├─ pandoc_process.py    # 非同期Pandoc実行
│   ├─ config.py            # プロファイル管理
│   └─ filters/             # 内蔵フィルター
│       └─ default_filter.lua  # 数式処理フィルター（常時適用）
└─ pyproject.toml           # プロジェクト設定
```

### 技術スタック

- **PyQt6**: GUIフレームワーク
- **QProcess**: 非同期プロセス実行
- **uv**: 高速パッケージ管理
- **YAML**: 設定ファイル形式
- **PyInstaller**: 実行ファイル作成 