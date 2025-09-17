"""
QProcess を使った非同期 Pandoc 実行モジュール
"""
import os
import subprocess
from pathlib import Path
from typing import List
from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class PandocWorker(QObject):
    """
    Pandoc を非同期で実行するワーカークラス
    """
    # シグナル定義
    stdout_received = pyqtSignal(str)
    stderr_received = pyqtSignal(str)
    finished = pyqtSignal(int)  # 終了コード
    started = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._on_stdout)
        self.proc.readyReadStandardError.connect(self._on_stderr)
        self.proc.finished.connect(self._on_finished)
        self.proc.started.connect(self._on_started)
        
    def run(self, input_file: str, output_file: str, extra_args: List[str] = None):
        """
        Pandoc を実行する
        
        Args:
            input_file: 入力ファイルパス
            output_file: 出力ファイルパス
            extra_args: 追加引数のリスト
        """
        if extra_args is None:
            extra_args = []
            
        # Pandoc が PATH にあるかチェック
        if not self._check_pandoc_available():
            self.stderr_received.emit("エラー: Pandoc が見つかりません。Pandocがインストールされ、PATHに設定されていることを確認してください。\n")
            self.finished.emit(1)
            return
            
        # 出力ディレクトリが存在しない場合は作成
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # リソースパスを抽出して追加
        resource_paths = self._extract_resource_paths([input_file])
        
        # コマンドライン引数を構築
        cmd = ['pandoc', input_file, '-o', output_file, '--resource-path', resource_paths] + extra_args
        
        # プロセス実行
        self.stdout_received.emit(f"実行コマンド: {' '.join(cmd)}\n")
        self.proc.start('pandoc', cmd[1:])
        
    def run_batch(self, input_files: List[str], output_dir: str, output_format: str, extra_args: List[str] = None):
        """
        複数ファイルを一括変換する
        
        Args:
            input_files: 入力ファイルパスのリスト
            output_dir: 出力ディレクトリ
            output_format: 出力形式（pdf, html, docx等）
            extra_args: 追加引数のリスト
        """
        if extra_args is None:
            extra_args = []
            
        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 各ファイルを順次変換
        self._batch_files = input_files
        self._batch_output_dir = output_dir
        self._batch_format = output_format
        self._batch_extra_args = extra_args
        self._batch_index = 0
        self._run_next_batch_file()
        
    def run_merge(self, input_files: List[str], output_file: str, extra_args: List[str] = None):
        """
        複数ファイルを結合して一つのファイルに変換する
        
        Args:
            input_files: 入力ファイルパスのリスト
            output_file: 出力ファイルパス
            extra_args: 追加引数のリスト
        """
        if extra_args is None:
            extra_args = []
            
        # Pandoc が PATH にあるかチェック
        if not self._check_pandoc_available():
            self.stderr_received.emit("エラー: Pandoc が見つかりません。Pandocがインストールされ、PATHに設定されていることを確認してください。\n")
            self.finished.emit(1)
            return
            
        # 出力ディレクトリが存在しない場合は作成
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # リソースパスを抽出して追加
        resource_paths = self._extract_resource_paths(input_files)
        
        # コマンドライン引数を構築（複数の入力ファイル + 出力ファイル + リソースパス + 追加引数）
        cmd = ['pandoc'] + input_files + ['-o', output_file, '--resource-path', resource_paths] + extra_args
        
        # プロセス実行
        self.stdout_received.emit(f"結合変換を開始:\n")
        self.stdout_received.emit(f"入力ファイル: {len(input_files)}個\n")
        for i, file in enumerate(input_files, 1):
            self.stdout_received.emit(f"  {i}. {Path(file).name}\n")
        self.stdout_received.emit(f"出力ファイル: {Path(output_file).name}\n")
        self.stdout_received.emit(f"リソースパス: {resource_paths}\n")
        self.stdout_received.emit(f"実行コマンド: {' '.join(cmd)}\n\n")
        
        self.proc.start('pandoc', cmd[1:])
        
    def _run_next_batch_file(self):
        """バッチ処理の次のファイルを実行"""
        if self._batch_index >= len(self._batch_files):
            self.stdout_received.emit("\n=== 一括変換完了 ===\n")
            self.finished.emit(0)
            return
            
        input_file = self._batch_files[self._batch_index]
        input_path = Path(input_file)
        output_file = Path(self._batch_output_dir) / f"{input_path.stem}.{self._batch_format}"
        
        self.stdout_received.emit(f"\n--- 変換中 ({self._batch_index + 1}/{len(self._batch_files)}): {input_path.name} ---\n")
        
        # 単一ファイル変換を実行
        self.run(str(input_file), str(output_file), self._batch_extra_args)
        
    def _on_batch_finished(self, exit_code: int):
        """バッチ処理の各ファイル完了時の処理"""
        if exit_code == 0:
            self.stdout_received.emit("✓ 変換成功\n")
        else:
            self.stderr_received.emit(f"✗ 変換失敗 (終了コード: {exit_code})\n")
            
        self._batch_index += 1
        self._run_next_batch_file()
        
    def terminate_process(self):
        """プロセスを強制終了する"""
        if self.proc.state() == QProcess.ProcessState.Running:
            self.proc.kill()
            
    def _extract_resource_paths(self, input_files: List[str]) -> str:
        """
        入力ファイルのディレクトリからリソースパスを抽出
        
        Args:
            input_files: 入力ファイルパスのリスト
            
        Returns:
            Windows形式（;区切り）のリソースパス文字列
        """
        unique_dirs = set()
        for file_path in input_files:
            dir_path = Path(file_path).parent.resolve()
            unique_dirs.add(str(dir_path))
        
        # Windows形式（;区切り）でパス結合、ソート済み
        return ';'.join(sorted(unique_dirs))
            
    def _check_pandoc_available(self) -> bool:
        """Pandoc が利用可能かチェック"""
        try:
            result = subprocess.run(['pandoc', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
            
    def _on_stdout(self):
        """標準出力受信時の処理"""
        data = bytes(self.proc.readAllStandardOutput()).decode('utf-8', errors='replace')
        if data:
            self.stdout_received.emit(data)
            
    def _on_stderr(self):
        """標準エラー受信時の処理"""
        data = bytes(self.proc.readAllStandardError()).decode('utf-8', errors='replace')
        if data:
            self.stderr_received.emit(data)
            
    def _on_finished(self, exit_code: int, exit_status):
        """プロセス終了時の処理"""
        if hasattr(self, '_batch_files'):
            # バッチ処理中の場合
            self._on_batch_finished(exit_code)
        elif hasattr(self, '_latex_mode') and self._latex_mode:
            # LaTeXモードの場合
            self._on_latex_finished(exit_code)
        else:
            # 単一ファイル処理の場合
            if exit_code == 0:
                self.stdout_received.emit("\n=== 変換完了 ===\n")
            else:
                self.stderr_received.emit(f"\n=== 変換失敗 (終了コード: {exit_code}) ===\n")
            self.finished.emit(exit_code)
            
    def _on_latex_finished(self, exit_code: int):
        """LaTeX生成完了時の処理"""
        if exit_code == 0:
            self.stdout_received.emit("✓ LaTeXファイル生成成功\n")
            
            # 次にPDFを生成
            self.stdout_received.emit("PDF生成を開始...\n")
            
            # LaTeXファイルからPDFを生成するコマンド
            latex_file = str(Path(self._pdf_output_file).with_suffix('.tex'))
            
            # PDF生成用の引数から--include-in-headerを除外
            pdf_args = []
            skip_next = False
            for i, arg in enumerate(self._pdf_extra_args):
                if skip_next:
                    skip_next = False
                    continue
                if arg == "--include-in-header":
                    skip_next = True  # 次の引数（ファイルパス）もスキップ
                    continue
                pdf_args.append(arg)
            
            pdf_cmd = ['pandoc', latex_file, '-o', self._pdf_output_file, '--resource-path', self._pdf_resource_paths] + pdf_args
            
            self.stdout_received.emit(f"PDF生成コマンド: {' '.join(pdf_cmd)}\n")
            
            # LaTeXモードを解除してPDF生成を開始
            self._latex_mode = False
            self.proc.start('pandoc', pdf_cmd[1:])
        else:
            self.stderr_received.emit(f"✗ LaTeXファイル生成失敗 (終了コード: {exit_code})\n")
            # LaTeXモードを解除
            self._latex_mode = False
            self.finished.emit(exit_code)
            
        
        

    def _on_started(self):
        """プロセス開始時の処理"""
        self.started.emit() 