## アプリ概要

* **名称（仮）**：Pandoc GUI Converter
* **目的**：Windows 上で Markdown ファイルを選択し、pypandoc 経由で PDF（HTML/DOCX も可）に変換するシンプルなデスクトップ GUI アプリケーション。
* **特徴**：

  * Rust製のパッケージ管理ツール **uv** で依存パッケージ・Pythonバージョン・仮想環境を一元管理し、環境構築を爆速化 ([gihyo.jp][1])。
  * PyQt6 による直感的な UI（ファイル選択、オプション設定、ログ表示）を提供。
  * Pandoc の全オプションを透過的に指定できる `extra_args` 編集機能。
  * `QProcess` を用いた非同期起動で UI をブロックしない。

---

## 要件

### 機能要件

1. **入力管理**

   * Markdown ファイル／フォルダの選択ダイアログ
   * ドラッグ＆ドロップによるファイル追加対応
2. **出力形式選択**

   * プルダウンで「pdf」「html」「docx」等を選択
3. **オプション設定**

   * チェックボックス・テキスト欄で Pandoc オプション（`--wrap=preserve`、`--lua-filter`、`--pdf-engine=xelatex`、`-V documentclass=…`、`--from markdown+hard_line_breaks` 等）を編集
4. **プロファイル管理**

   * YAML 形式での保存／読み込み
   * インストール先直下の `profiles/` フォルダに配置
5. **変換実行**

   * `QProcess` で Pandoc CLI を非同期起動し、標準出力／標準エラーをリアルタイム表示
   * 終了時に「出力先を開く」ボタンを有効化
6. **ログ永続化**

   * 不要（ファイル保存なし）

### 非機能要件

* **プラットフォーム**：Windows のみ対応（将来的にクロスプラットフォーム化検討）
* **仮想環境管理**：uv を利用し、一貫して依存・Python バージョン・仮想環境を管理 ([gihyo.jp][1])。
* **言語**：日本語 UI 固定
* **軽量性**：依存は最小限（PyQt6, pypandoc, pyyaml, uv）
* **拡張性**：後日自動更新機能や多言語対応を追加可能な設計

---

## 実装に必要な情報

### 1. 環境セットアップ（uv 活用）

1. **uv のインストール**

   ```powershell
   # システムに pip があれば
   pip install uv
   ```

   Rust 製で極めて高速な pip 代替およびプロジェクト管理ツール ([gihyo.jp][1])。
2. **プロジェクト初期化**

   ```powershell
   uv init pandoc-gui
   cd pandoc-gui
   ```

   `pyproject.toml` 等のひな形が生成される ([speakerdeck.com][2])。
3. **仮想環境の作成**

   ```powershell
   uv venv
   ```

   デフォルトで `.venv` フォルダを 0.02 秒程度で作成 ([gihyo.jp][1])。
4. **仮想環境のアクティベート**

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   （PowerShell）Windows 環境でも通常の venv と同様に有効化可能 ([gihyo.jp][1])。
5. **依存パッケージのインストール**

   ```powershell
   uv pip install PyQt6 pypandoc pyyaml
   ```

   `uv pip` コマンドは従来の `pip install` より高速・確実にパッケージを解決・インストール ([gihyo.jp][1])。

### 2. ディレクトリ構成例

```
pandoc-gui/                      ← uv init で生成されたルート
├─ .venv/                        ← uv venv による仮想環境
├─ profiles/                     ← YAML プロファイル保存 (例: default.yml)
├─ src/
│   ├─ main.py                   ← アプリ起動／UI初期化
│   ├─ ui_main.py                ← Qt Designer 生成 or 手書き UI 定義
│   ├─ pandoc_process.py         ← QProcess を使った非同期 Pandoc 実行
│   ├─ config.py                 ← YAML プロファイル読み書きロジック
│   └─ resources/                ← アイコン等リソース
├─ pyproject.toml                ← uv init 生成
├─ README.md
└─ requirements.txt              ← uv pip freeze 出力（任意）
```

### 3. 主なコード例

#### `config.py`（YAML プロファイル管理）

```python
import yaml
from pathlib import Path
import sys

BASE_DIR = Path(sys.argv[0]).resolve().parent
PROFILE_DIR = BASE_DIR / 'profiles'
PROFILE_DIR.mkdir(exist_ok=True)

def load_profile(name: str) -> dict:
    with open(PROFILE_DIR / f'{name}.yml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_profile(name: str, data: dict):
    with open(PROFILE_DIR / f'{name}.yml', 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True)
```

#### `pandoc_process.py`（QProcess で非同期 Pandoc 実行）

```python
from PyQt6.QtCore import QObject, QProcess, pyqtSignal

class PandocWorker(QObject):
    stdout_received = pyqtSignal(str)
    stderr_received = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._on_stdout)
        self.proc.readyReadStandardError.connect(self._on_stderr)
        self.proc.finished.connect(self._on_finished)

    def run(self, input_md: str, output_file: str, extra_args: list[str]):
        cmd = ['pandoc', input_md, '-o', output_file] + extra_args
        self.proc.start(cmd[0], cmd[1:])

    def _on_stdout(self):
        self.stdout_received.emit(bytes(self.proc.readAllStandardOutput()).decode())

    def _on_stderr(self):
        self.stderr_received.emit(bytes(self.proc.readAllStandardError()).decode())

    def _on_finished(self, exit_code: int, _status):
        self.finished.emit(exit_code)
```

#### `main.py`（UI と連携）

```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from ui_main import Ui_MainWindow
from pandoc_process import PandocWorker
from config import load_profile, save_profile

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.worker = PandocWorker()
        self.worker.stdout_received.connect(self.ui.appendLog)
        self.worker.stderr_received.connect(self.ui.appendLog)
        self.worker.finished.connect(self.onFinished)

        self.ui.btnSelectInput.clicked.connect(self.selectInput)
        self.ui.btnRun.clicked.connect(self.startConversion)
        self.ui.btnSaveProfile.clicked.connect(self.saveCurrentProfile)
        self.ui.btnLoadProfile.clicked.connect(self.loadProfile)

    def selectInput(self):
        path, _ = QFileDialog.getOpenFileName(self, "Markdown を選択", "", "Markdown (*.md)")
        if path:
            self.ui.inputPath.setText(path)

    def startConversion(self):
        in_md = self.ui.inputPath.text()
        out_file = self.ui.outputPath.text()
        args = self.ui.collectExtraArgs()
        self.worker.run(in_md, out_file, args)

    def onFinished(self, code):
        if code == 0:
            self.ui.enableOpenOutput(True)

    def saveCurrentProfile(self):
        name = self.ui.profileName.text()
        data = {
            "output_format": self.ui.outputFormat.currentText(),
            "extra_args": self.ui.collectExtraArgs()
        }
        save_profile(name, data)

    def loadProfile(self):
        name = self.ui.profileSelect.currentText()
        data = load_profile(name)
        # UI に data を反映する実装を追加

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
```

### 4. プロファイル YAML 例

```yaml
output_format: pdf
extra_args:
  - --wrap=preserve
  - --lua-filter=default_filter.lua
  - --pdf-engine=xelatex
  - -V
  - documentclass=bxjsarticle
  - -V
  - classoption=pandoc
  - --from
  - markdown+hard_line_breaks
```

### 5. ビルド & 配布（Windows 向け）

```powershell
uv pip install pyinstaller
pyinstaller `
  --name pandoc-gui `
  --onefile `
  --add-data "profiles;profiles" `
  src/main.py
```

* 生成された `dist/pandoc-gui.exe` を配布先に配置するだけで動作 ([js2iiu.com][3])。
