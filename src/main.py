"""
Pandoc GUI Converter - メインアプリケーション
"""
import sys
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QListWidgetItem
)
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QCloseEvent

# 共通モジュールから定数をインポート
from common import BASE_DIR, RESOURCE_DIR

from ui_main import Ui_MainWindow
from pandoc_process import PandocWorker
from config import load_profile, save_profile, get_available_profiles, delete_profile, get_default_profile
from defaults import load_defaults_file, save_defaults_file, defaults_to_app_config, app_config_to_defaults


class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Pandoc ワーカー
        self.worker = PandocWorker()
        self.worker.stdout_received.connect(self.append_log)
        self.worker.stderr_received.connect(self.append_log)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.started.connect(self.on_conversion_started)

        # プロジェクトファイル関連
        self.current_project_path = None
        
        
        # イベント接続
        self._connect_events()
        
        # 初期化
        self._initialize_ui()
        
        # ドラッグ&ドロップ有効化
        self.setAcceptDrops(True)
        
    def _resolve_filter_path(self, filter_path: str) -> Path:
        """
        フィルタファイルのパスを解決する
        
        Args:
            filter_path: フィルタファイルのパス（相対パスまたは絶対パス）
            
        Returns:
            解決されたパス
        """
        path_obj = Path(filter_path)
        
        # 絶対パスの場合はそのまま返す
        if path_obj.is_absolute():
            return path_obj
            
        # 相対パスの場合
        # 1. filters/ディレクトリ内のファイルとして解決
        filters_path = RESOURCE_DIR / "filters" / filter_path
        if filters_path.exists():
            return filters_path
            
        # 2. EXEまたはプロジェクトディレクトリから直接解決
        direct_path = BASE_DIR / filter_path
        if direct_path.exists():
            return direct_path
        
        # ファイルが見つからない場合はそのまま返す（エラーはPandocが出す）
        return path_obj
        
    def _connect_events(self):
        """イベントハンドラーを接続"""
        # 基本設定タブ
        self.ui.btn_select_files.clicked.connect(self.select_files)
        self.ui.btn_select_folder.clicked.connect(self.select_folder)
        self.ui.btn_clear_files.clicked.connect(self.clear_file_list)
        self.ui.btn_move_up.clicked.connect(self.move_file_up)
        self.ui.btn_move_down.clicked.connect(self.move_file_down)
        self.ui.btn_remove_file.clicked.connect(self.remove_file)
        self.ui.btn_select_output_dir.clicked.connect(self.select_output_directory)
        
        # 詳細設定タブ
        self.ui.btn_select_lua.clicked.connect(self.select_lua_filter)
        self.ui.btn_select_template.clicked.connect(self.select_template)
        
        # プロファイル管理
        self.ui.btn_load_profile.clicked.connect(self.load_profile)
        self.ui.btn_save_profile.clicked.connect(self.save_current_profile)
        self.ui.btn_delete_profile.clicked.connect(self.delete_profile)
        self.ui.btn_refresh_profiles.clicked.connect(self.refresh_profiles)
        self.ui.profile_select.currentTextChanged.connect(self.on_profile_selected)

        # プロジェクトファイル管理
        self.ui.btn_load_project.clicked.connect(self.load_project_file)
        self.ui.btn_save_project.clicked.connect(self.save_project_file)
        self.ui.btn_save_project_as.clicked.connect(self.save_project_file_as)

        # 実行関連
        self.ui.btn_run.clicked.connect(self.start_conversion)
        self.ui.btn_stop.clicked.connect(self.stop_conversion)
        self.ui.btn_open_output.clicked.connect(self.open_output_directory)
        self.ui.btn_open_pdf.clicked.connect(self.open_output_pdf)
        self.ui.btn_clear_log.clicked.connect(self.clear_log)
        
    def _initialize_ui(self):
        """UI の初期状態を設定"""
        # プロファイル一覧を更新
        self.refresh_profiles()
        
        # デフォルトプロファイルを読み込み
        try:
            default_profile = load_profile("default")
            self.apply_profile_to_ui(default_profile)
        except Exception as e:
            # default.ymlが存在しない場合はハードコーディングされたデフォルトを使用
            default_profile = get_default_profile()
            self.apply_profile_to_ui(default_profile)
        
        self.ui.statusbar.showMessage("準備完了 - Pandocが利用可能かご確認ください")
        
    def select_files(self):
        """ファイルを選択（リストに追加）"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "ファイルを選択", "",
            "Markdown files (*.md *.markdown *.mdown *.mkd);;Bibliography files (*.bib *.json *.yaml);;All files (*)"
        )
        if file_paths:
            for file_path in file_paths:
                # 重複チェック
                is_duplicate = False
                for i in range(self.ui.file_list.count()):
                    if self.ui.file_list.item(i).data(256) == file_path:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    display_name = self._get_file_display_name(file_path)
                    item = QListWidgetItem(display_name)
                    item.setData(256, file_path)  # フルパスをデータとして保存
                    self.ui.file_list.addItem(item)
                
    def select_folder(self):
        """フォルダを選択してMarkdownファイルを追加"""
        folder_path = QFileDialog.getExistingDirectory(self, "フォルダを選択")
        if folder_path:
            md_files = list(Path(folder_path).glob("*.md"))
            md_files.extend(Path(folder_path).glob("*.markdown"))
            md_files.extend(Path(folder_path).glob("*.mdown"))
            md_files.extend(Path(folder_path).glob("*.mkd"))
            
            if md_files:
                self.ui.file_list.clear()
                for md_file in md_files:
                    display_name = self._get_file_display_name(str(md_file))
                    item = QListWidgetItem(display_name)
                    item.setData(256, str(md_file))
                    self.ui.file_list.addItem(item)
            else:
                QMessageBox.information(self, "情報", "選択したフォルダにMarkdownファイルが見つかりませんでした。")
                
    def clear_file_list(self):
        """ファイルリストをクリア"""
        self.ui.file_list.clear()
        
    def move_file_up(self):
        """選択されたファイルを上に移動"""
        current_row = self.ui.file_list.currentRow()
        if current_row > 0:
            item = self.ui.file_list.takeItem(current_row)
            self.ui.file_list.insertItem(current_row - 1, item)
            self.ui.file_list.setCurrentRow(current_row - 1)
            
    def move_file_down(self):
        """選択されたファイルを下に移動"""
        current_row = self.ui.file_list.currentRow()
        if current_row < self.ui.file_list.count() - 1 and current_row >= 0:
            item = self.ui.file_list.takeItem(current_row)
            self.ui.file_list.insertItem(current_row + 1, item)
            self.ui.file_list.setCurrentRow(current_row + 1)
            
    def remove_file(self):
        """選択されたファイルを削除"""
        current_row = self.ui.file_list.currentRow()
        if current_row >= 0:
            self.ui.file_list.takeItem(current_row)
        
    def select_output_directory(self):
        """出力ディレクトリを選択"""
        dir_path = QFileDialog.getExistingDirectory(self, "出力ディレクトリを選択")
        if dir_path:
            self.ui.output_dir.setText(dir_path)
            
    def select_lua_filter(self):
        """Luaフィルターファイルを選択"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Luaフィルターを選択", "", "Lua files (*.lua);;All files (*)"
        )
        if file_path:
            self.ui.lua_filter.setText(file_path)
            
    def select_template(self):
        """テンプレートファイルを選択"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "テンプレートを選択", "", "All files (*)"
        )
        if file_path:
            self.ui.template_file.setText(file_path)
            

    def _get_file_display_name(self, file_path: str) -> str:
        """ファイルの表示名を生成"""
        path = Path(file_path)
        return path.name
            
    def collect_extra_args(self) -> List[str]:
        """UIから追加引数を収集"""
        args = []
        
        # 基本オプション
        if self.ui.wrap_preserve.isChecked():
            args.extend(["--wrap=preserve"])
            
        if self.ui.table_of_contents.isChecked():
            args.extend(["--toc"])
            
        if self.ui.number_sections.isChecked():
            args.extend(["--number-sections"])
            
        if self.ui.standalone.isChecked():
            args.extend(["--standalone"])

        if self.ui.citeproc.isChecked():
            args.extend(["--citeproc"])
        
        # PDF エンジン
        pdf_engine = self.ui.pdf_engine.currentText()
        if pdf_engine:
            args.extend([f"--pdf-engine={pdf_engine}"])
            
        # ドキュメントクラス
        doc_class = self.ui.document_class.text().strip()
        if doc_class:
            args.extend(["-V", f"documentclass={doc_class}"])
            
        # クラスオプション
        class_opt = self.ui.class_option.text().strip()
        if class_opt:
            args.extend(["-V", f"classoption={class_opt}"])
            
        # フォントサイズ
        font_size = self.ui.font_size.currentText().strip()
        if font_size:
            args.extend(["-V", f"fontsize={font_size}"])
            
        # 用紙サイズ
        paper_size = self.ui.paper_size.currentText().strip()
        if paper_size:
            args.extend(["-V", f"papersize={paper_size}"])
            
        # 余白設定（詳細）
        margin_top = self.ui.margin_top.text().strip()
        margin_bottom = self.ui.margin_bottom.text().strip()
        margin_left = self.ui.margin_left.text().strip()
        margin_right = self.ui.margin_right.text().strip()
        footskip = self.ui.footskip.text().strip()

        margin_parts = []
        if margin_top:
            margin_parts.append(f"top={margin_top}")
        if margin_bottom:
            margin_parts.append(f"bottom={margin_bottom}")
        if margin_left:
            margin_parts.append(f"left={margin_left}")
        if margin_right:
            margin_parts.append(f"right={margin_right}")
        if footskip:
            margin_parts.append(f"footskip={footskip}")

        if margin_parts:
            args.extend(["-V", f"geometry:{','.join(margin_parts)}"])
            
        
        # Markdown拡張
        md_ext = self.ui.markdown_extensions.text().strip()
        if md_ext:
            args.extend(["--from", md_ext])
            
        # 内蔵フィルター（default_filter.lua）を常に適用
        builtin_filter_path = RESOURCE_DIR / "filters" / "default_filter.lua"
        if builtin_filter_path.exists():
            args.extend(["--lua-filter", str(builtin_filter_path)])
        
        # 追加フィルター
        lua_filter = self.ui.lua_filter.text().strip()
        if lua_filter:
            filter_path = self._resolve_filter_path(lua_filter)
            args.extend(["--lua-filter", str(filter_path)])
            
        template = self.ui.template_file.text().strip()
        if template:
            args.extend([f"--template={template}"])

        # 参考文献スタイル（default.csl）を常に適用
        csl_path = RESOURCE_DIR / "templates" / "default.csl"
        if csl_path.exists():
            args.extend(["--csl", str(csl_path)])

            
        # カスタム引数
        custom_args_text = self.ui.custom_args.toPlainText().strip()
        if custom_args_text:
            for line in custom_args_text.split('\n'):
                line = line.strip()
                if line:
                    args.append(line)
                    
        return args
        
    def start_conversion(self):
        """変換を開始"""
        # 入力ファイルの確認と分離
        all_files = []
        input_files = []
        bibliography_files = []

        # ファイルリストから取得
        for i in range(self.ui.file_list.count()):
            item = self.ui.file_list.item(i)
            file_path = item.data(256)
            all_files.append(file_path)

            # ファイル種別で分離
            path = Path(file_path)
            if path.suffix.lower() == '.bib':
                bibliography_files.append(file_path)
            else:
                input_files.append(file_path)

        if not input_files:
            QMessageBox.warning(self, "エラー", "変換対象の入力ファイル（Markdownなど）が選択されていません。")
            return
            
        # 出力設定の確認
        output_format = self.ui.output_format.currentText()
        output_dir = self.ui.output_dir.text().strip()
        
        if not output_dir:
            # 出力ディレクトリが指定されていない場合、最初の入力ファイルと同じディレクトリを使用
            output_dir = str(Path(input_files[0]).parent)
            
        # 追加引数を収集
        extra_args = self.collect_extra_args()

        # 参考文献ファイルを--bibliography引数として追加
        for bib_file in bibliography_files:
            extra_args.extend(["--bibliography", bib_file])
        
        
        # LaTeXヘッダーファイルを直接include
        header_base_path = RESOURCE_DIR / "templates" / "latex_header_base.tex"
        if header_base_path.exists():
            extra_args.extend(["--include-in-header", str(header_base_path)])
        
        # 変換開始
        if len(input_files) == 1:
            # 単一ファイル変換
            input_file = input_files[0]
            output_file = Path(output_dir) / f"{Path(input_file).stem}.{output_format}"
            self.worker.run(input_file, str(output_file), extra_args)
        else:
            # 複数ファイル処理
            if self.ui.merge_files.isChecked():
                # 結合変換：複数ファイルを一つにまとめる
                if self.ui.output_filename.text().strip():
                    # 出力ファイル名が指定されている場合
                    custom_name = self.ui.output_filename.text().strip()
                    # 拡張子を除去（もしあれば）
                    custom_name = custom_name.rsplit('.', 1)[0]
                    output_file = Path(output_dir) / f"{custom_name}.{output_format}"
                else:
                    # デフォルトファイル名を生成
                    first_file_name = Path(input_files[0]).stem
                    output_file = Path(output_dir) / f"{first_file_name}_merged.{output_format}"
                self.worker.run_merge(input_files, str(output_file), extra_args)
            else:
                # 一括変換：各ファイルを個別に変換
                self.worker.run_batch(input_files, output_dir, output_format, extra_args)
            
        self.current_output_dir = output_dir
        
        # PDFファイルのパスを保存（PDF変換の場合）
        if output_format == "pdf":
            if len(input_files) == 1:
                self.current_output_pdf = str(output_file)
            elif self.ui.merge_files.isChecked():
                self.current_output_pdf = str(output_file)
            else:
                # 一括変換時は最後のファイル（実際はworkerで管理）
                self.current_output_pdf = None
        
    def stop_conversion(self):
        """変換を停止"""
        self.worker.terminate_process()
        self.append_log("変換を停止しました。\n")
        
    def on_conversion_started(self):
        """変換開始時の処理"""
        self.ui.btn_run.setEnabled(False)
        self.ui.btn_stop.setEnabled(True)
        self.ui.btn_open_output.setEnabled(False)
        self.ui.btn_open_pdf.setEnabled(False)
        self.ui.progress_bar.setVisible(True)
        self.ui.progress_bar.setRange(0, 0)  # 不定長プログレスバー
        self.ui.statusbar.showMessage("変換実行中...")
        
    def on_conversion_finished(self, exit_code: int):
        """変換終了時の処理"""
        self.ui.btn_run.setEnabled(True)
        self.ui.btn_stop.setEnabled(False)
        self.ui.progress_bar.setVisible(False)
        
        if exit_code == 0:
            self.ui.btn_open_output.setEnabled(True)
            # PDFファイルが生成された場合、PDFを開くボタンを有効化
            if hasattr(self, 'current_output_pdf') and self.current_output_pdf and Path(self.current_output_pdf).exists():
                self.ui.btn_open_pdf.setEnabled(True)
            self.ui.statusbar.showMessage("変換完了")
            QMessageBox.information(self, "完了", "変換が正常に完了しました。")
        else:
            self.ui.statusbar.showMessage("変換失敗")
            QMessageBox.warning(self, "エラー", f"変換に失敗しました。(終了コード: {exit_code})")
            
    def open_output_directory(self):
        """出力ディレクトリを開く"""
        if hasattr(self, 'current_output_dir'):
            if sys.platform == "win32":
                os.startfile(self.current_output_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.current_output_dir])
            else:
                subprocess.run(["xdg-open", self.current_output_dir])
                
    def open_output_pdf(self):
        """生成されたPDFファイルを開く"""
        if hasattr(self, 'current_output_pdf') and Path(self.current_output_pdf).exists():
            try:
                if sys.platform == "win32":
                    os.startfile(str(self.current_output_pdf))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(self.current_output_pdf)])
                else:
                    subprocess.run(["xdg-open", str(self.current_output_pdf)])
                self.append_log(f"PDFファイルを開きました: {Path(self.current_output_pdf).name}\n")
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"PDFファイルを開けませんでした: {e}")
        else:
            QMessageBox.information(self, "情報", "開くPDFファイルが見つかりません。")
                
    def append_log(self, text: str):
        """ログにテキストを追加"""
        from PyQt6.QtGui import QTextCursor
        self.ui.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.ui.log_text.insertPlainText(text)
        self.ui.log_text.moveCursor(QTextCursor.MoveOperation.End)
        
    def clear_log(self):
        """ログをクリア"""
        self.ui.log_text.clear()
        
    def refresh_profiles(self):
        """プロファイル一覧を更新"""
        self.ui.profile_select.clear()
        profiles = get_available_profiles()
        self.ui.profile_select.addItems(profiles)
        
    def on_profile_selected(self, profile_name: str):
        """プロファイル選択時のプレビュー更新"""
        if profile_name:
            try:
                profile_data = load_profile(profile_name)
                import yaml
                preview_text = yaml.dump(profile_data, allow_unicode=True, default_flow_style=False)
                self.ui.profile_preview.setText(preview_text)
            except Exception as e:
                self.ui.profile_preview.setText(f"プロファイル読み込みエラー: {e}")
        else:
            self.ui.profile_preview.clear()
            
    def load_profile(self):
        """選択されたプロファイルを読み込み"""
        profile_name = self.ui.profile_select.currentText()
        if not profile_name:
            QMessageBox.warning(self, "エラー", "プロファイルが選択されていません。")
            return
            
        try:
            profile_data = load_profile(profile_name)
            self.apply_profile_to_ui(profile_data)
            QMessageBox.information(self, "完了", f"プロファイル '{profile_name}' を読み込みました。")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"プロファイルの読み込みに失敗しました: {e}")
            
    def apply_profile_to_ui(self, profile_data: Dict[str, Any]):
        """プロファイルデータをUIに適用"""
        # 出力形式
        output_format = profile_data.get('output_format', 'pdf')
        index = self.ui.output_format.findText(output_format)
        if index >= 0:
            self.ui.output_format.setCurrentIndex(index)
            
        # 追加引数から各UI要素に反映
        extra_args = profile_data.get('extra_args', [])
        
        # チェックボックスの状態をリセット
        self.ui.wrap_preserve.setChecked(False)
        self.ui.table_of_contents.setChecked(False)
        self.ui.number_sections.setChecked(False)
        self.ui.citeproc.setChecked(False)
        self.ui.standalone.setChecked(False)
        
        # テキストフィールドをリセット
        self.ui.document_class.clear()
        self.ui.class_option.clear()
        self.ui.markdown_extensions.clear()
        
        # 詳細マージン設定をリセット
        self.ui.margin_top.clear()
        self.ui.margin_bottom.clear()
        self.ui.margin_left.clear()
        self.ui.margin_right.clear()
        self.ui.footskip.clear()
        
        # コンボボックスをリセット
        self.ui.font_size.setCurrentText("")
        self.ui.paper_size.setCurrentText("")
        
        # カスタム引数フィールドをクリア
        self.ui.custom_args.clear()
        
        # 引数を解析してUIに設定
        unprocessed_args = []  # 未処理の引数を収集
        i = 0
        while i < len(extra_args):
            arg = extra_args[i]
            processed = False
            
            if arg == "--wrap=preserve":
                self.ui.wrap_preserve.setChecked(True)
                processed = True
            elif arg == "--toc":
                self.ui.table_of_contents.setChecked(True)
                processed = True
            elif arg == "--number-sections":
                self.ui.number_sections.setChecked(True)
                processed = True
            elif arg == "--standalone":
                self.ui.standalone.setChecked(True)
                processed = True
            elif arg == "--citeproc":
                self.ui.citeproc.setChecked(True)
                processed = True
            elif arg.startswith("--pdf-engine="):
                engine = arg.split("=", 1)[1]
                index = self.ui.pdf_engine.findText(engine)
                if index >= 0:
                    self.ui.pdf_engine.setCurrentIndex(index)
                processed = True
            elif arg == "-V" and i + 1 < len(extra_args):
                next_arg = extra_args[i + 1]
                if next_arg.startswith("documentclass="):
                    self.ui.document_class.setText(next_arg.split("=", 1)[1])
                    processed = True
                elif next_arg.startswith("classoption="):
                    self.ui.class_option.setText(next_arg.split("=", 1)[1])
                    processed = True
                elif next_arg.startswith("fontsize="):
                    font_size = next_arg.split("=", 1)[1]
                    index = self.ui.font_size.findText(font_size)
                    if index >= 0:
                        self.ui.font_size.setCurrentIndex(index)
                    processed = True
                elif next_arg.startswith("papersize="):
                    paper_size = next_arg.split("=", 1)[1]
                    index = self.ui.paper_size.findText(paper_size)
                    if index >= 0:
                        self.ui.paper_size.setCurrentIndex(index)
                    processed = True
                elif next_arg.startswith("geometry:"):
                    geometry = next_arg.split(":", 1)[1]
                    # geometry設定を解析して各余白フィールドに設定
                    if geometry.startswith("margin="):
                        # margin=15mm の場合は全マージンに同じ値を設定
                        margin_value = geometry.split("=", 1)[1]
                        self.ui.margin_top.setText(margin_value)
                        self.ui.margin_bottom.setText(margin_value)
                        self.ui.margin_left.setText(margin_value)
                        self.ui.margin_right.setText(margin_value)
                    else:
                        # top=2cm,bottom=2cm,left=3cm,right=3cm の形式を解析
                        self._parse_geometry_string_to_ui(geometry)
                    processed = True
                
                if processed:
                    i += 1  # 次の引数もスキップ
                else:
                    # 未処理の-Vオプション
                    unprocessed_args.extend([arg, next_arg])
                    i += 1
            elif arg == "--from" and i + 1 < len(extra_args):
                self.ui.markdown_extensions.setText(extra_args[i + 1])
                i += 1
                processed = True
            
            if not processed:
                unprocessed_args.append(arg)
                
            i += 1
            
        # 未処理の引数をカスタム引数フィールドに設定
        if unprocessed_args:
            custom_args_text = '\n'.join(unprocessed_args)
            self.ui.custom_args.setPlainText(custom_args_text)
            
        # ファイルパス系
        self.ui.lua_filter.setText(profile_data.get('lua_filter', ''))
        self.ui.template_file.setText(profile_data.get('template', ''))
        
        # 結合オプション
        self.ui.merge_files.setChecked(profile_data.get('merge_files', False))
        
        # カスタムファイル名
        self.ui.output_filename.setText(profile_data.get('output_filename', ''))
        
        
    def save_current_profile(self):
        """現在の設定をプロファイルとして保存"""
        profile_name = self.ui.profile_name.text().strip()
        if not profile_name:
            QMessageBox.warning(self, "エラー", "プロファイル名を入力してください。")
            return
            
        # 現在のUI設定を収集
        profile_data = {
            "output_format": self.ui.output_format.currentText(),
            "extra_args": self.collect_extra_args(),
            "lua_filter": self.ui.lua_filter.text().strip(),
            "template": self.ui.template_file.text().strip(),
            "merge_files": self.ui.merge_files.isChecked(),
            "output_filename": self.ui.output_filename.text().strip(),
        }
        
        if save_profile(profile_name, profile_data):
            QMessageBox.information(self, "完了", f"プロファイル '{profile_name}' を保存しました。")
            self.refresh_profiles()
            # 保存したプロファイルを選択
            index = self.ui.profile_select.findText(profile_name)
            if index >= 0:
                self.ui.profile_select.setCurrentIndex(index)
        else:
            QMessageBox.warning(self, "エラー", "プロファイルの保存に失敗しました。")
            
    def delete_profile(self):
        """選択されたプロファイルを削除"""
        profile_name = self.ui.profile_select.currentText()
        if not profile_name:
            QMessageBox.warning(self, "エラー", "削除するプロファイルが選択されていません。")
            return
            
        reply = QMessageBox.question(
            self, "確認", 
            f"プロファイル '{profile_name}' を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if delete_profile(profile_name):
                QMessageBox.information(self, "完了", f"プロファイル '{profile_name}' を削除しました。")
                self.refresh_profiles()
            else:
                QMessageBox.warning(self, "エラー", "プロファイルの削除に失敗しました。")

    def load_project_file(self):
        """プロジェクトファイル（defaults file）を読み込み"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "プロジェクトファイルを選択", "",
            "YAML files (*.yaml *.yml);;All files (*)"
        )

        if not file_path:
            return

        try:
            # defaults fileを読み込み
            defaults_data = load_defaults_file(file_path)
            project_dir = Path(file_path).parent

            # アプリケーション内部形式に変換
            app_config = defaults_to_app_config(defaults_data, project_dir)

            # UIに適用
            self.apply_project_to_ui(app_config, defaults_data)

            # 現在のプロジェクトファイルパスを保存
            self.current_project_path = file_path
            self.ui.current_project_file.setText(str(Path(file_path).name))


        except Exception as e:
            QMessageBox.warning(self, "エラー", f"プロジェクトファイルの読み込みに失敗しました: {e}")

    def apply_project_to_ui(self, app_config: Dict[str, Any], defaults_data: Dict[str, Any]):
        """プロジェクト設定をUIに適用"""
        # 入力ファイルをファイルリストに設定
        input_files = app_config.get('input_files', [])
        if input_files:
            self.ui.file_list.clear()
            for file_path in input_files:
                if Path(file_path).exists():
                    display_name = self._get_file_display_name(file_path)
                    item = QListWidgetItem(display_name)
                    item.setData(256, file_path)
                    self.ui.file_list.addItem(item)
                else:
                    self.append_log(f"警告: ファイルが見つかりません: {file_path}\n")


        # 出力ファイル名のみを設定
        if app_config.get('output_file'):
            output_path = Path(app_config['output_file'])
            # ファイル名のみを設定（ディレクトリは設定しない）
            self.ui.output_filename.setText(output_path.name)

        # 出力形式
        output_format = app_config.get('output_format', 'pdf')
        index = self.ui.output_format.findText(output_format)
        if index >= 0:
            self.ui.output_format.setCurrentIndex(index)

        # 複数ファイルの結合設定（defaults fileでは基本的に結合前提）
        if len(input_files) > 1:
            self.ui.merge_files.setChecked(True)

        # 基本的なフラグ設定
        self.ui.table_of_contents.setChecked(defaults_data.get('toc', False))
        self.ui.number_sections.setChecked(defaults_data.get('number-sections', False))
        self.ui.citeproc.setChecked(defaults_data.get('citeproc', False))
        self.ui.standalone.setChecked(defaults_data.get('standalone', False))

        # Variables設定
        variables = defaults_data.get('variables', {})
        if 'fontsize' in variables:
            font_size = variables['fontsize']
            index = self.ui.font_size.findText(font_size)
            if index >= 0:
                self.ui.font_size.setCurrentIndex(index)

        if 'papersize' in variables:
            paper_size = variables['papersize']
            index = self.ui.paper_size.findText(paper_size)
            if index >= 0:
                self.ui.paper_size.setCurrentIndex(index)

        # クラスオプションをデフォルト値に設定（papersizeはvariablesで管理）
        self.ui.class_option.setText("pandoc")

        # Geometry設定（余白）
        if 'geometry' in variables:
            geometry = variables['geometry']
            self._parse_geometry_to_ui(geometry)

        # PDF エンジン
        if 'pdf-engine' in defaults_data:
            engine = defaults_data['pdf-engine']
            index = self.ui.pdf_engine.findText(engine)
            if index >= 0:
                self.ui.pdf_engine.setCurrentIndex(index)


        # ログ出力
        self.append_log(f"プロジェクトファイルを読み込みました: {len(input_files)}個のファイル\n")

    def _parse_geometry_to_ui(self, geometry):
        """geometry設定をUIの余白フィールドにパース"""
        if isinstance(geometry, list):
            # リスト形式の場合
            for part in geometry:
                if '=' in part:
                    self._parse_geometry_part(part)
        elif isinstance(geometry, str):
            # 文字列形式の場合（旧形式サポート）
            if '=' in geometry:
                if geometry.startswith('margin='):
                    # margin=25mm の場合
                    margin_value = geometry.split('=', 1)[1]
                    self.ui.margin_top.setText(margin_value)
                    self.ui.margin_bottom.setText(margin_value)
                    self.ui.margin_left.setText(margin_value)
                    self.ui.margin_right.setText(margin_value)
                else:
                    # top=20mm,bottom=25mm,left=15mm,right=15mm の形式
                    self._parse_geometry_string_to_ui(geometry)

    def _parse_geometry_string_to_ui(self, geometry_str: str):
        """geometry設定文字列をUIの余白フィールドに解析して設定"""
        parts = [part.strip() for part in geometry_str.split(',')]
        for part in parts:
            if '=' in part:
                self._parse_geometry_part(part)

    def _parse_geometry_part(self, part: str):
        """geometry設定の個別項目をUIに設定"""
        key, value = part.split('=', 1)
        key = key.strip()
        value = value.strip()
        if key == 'top':
            self.ui.margin_top.setText(value)
        elif key == 'bottom':
            self.ui.margin_bottom.setText(value)
        elif key == 'left':
            self.ui.margin_left.setText(value)
        elif key == 'right':
            self.ui.margin_right.setText(value)
        elif key == 'footskip':
            self.ui.footskip.setText(value)

    def save_project_file(self):
        """現在のプロジェクトファイルに保存"""
        if not self.current_project_path:
            # 新規保存
            self.save_project_file_as()
            return

        self._save_project_to_file(self.current_project_path)

    def save_project_file_as(self):
        """プロジェクトファイルを名前を付けて保存"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "プロジェクトファイルを保存", "",
            "YAML files (*.yaml *.yml);;All files (*)"
        )

        if not file_path:
            return

        # 拡張子がない場合は.yamlを追加
        if not file_path.lower().endswith(('.yaml', '.yml')):
            file_path += '.yaml'

        self._save_project_to_file(file_path)
        self.current_project_path = file_path
        self.ui.current_project_file.setText(str(Path(file_path).name))

    def _save_project_to_file(self, file_path: str):
        """プロジェクトファイルを指定パスに保存"""
        try:
            # 現在のUI設定を収集
            input_files = []
            for i in range(self.ui.file_list.count()):
                item = self.ui.file_list.item(i)
                input_files.append(item.data(256))

            if not input_files:
                QMessageBox.warning(self, "エラー", "入力ファイルが選択されていません。")
                return

            # アプリケーション内部形式の設定を作成
            app_config = {
                'input_files': input_files,
                'output_format': self.ui.output_format.currentText(),
                'extra_args': self.collect_extra_args(),
                'template': self.ui.template_file.text().strip(),
                'lua_filter': self.ui.lua_filter.text().strip(),
                'metadata': {}
            }

            # 出力ファイル名のみを設定（ディレクトリは含めない）
            if self.ui.output_filename.text().strip():
                app_config['output_file'] = self.ui.output_filename.text().strip()

            # プロジェクトディレクトリからの相対パスに変換
            project_dir = Path(file_path).parent
            relative_input_files = []
            for file_path_abs in input_files:
                try:
                    rel_path = Path(file_path_abs).relative_to(project_dir)
                    relative_input_files.append(str(rel_path))
                except ValueError:
                    # 相対パスにできない場合は絶対パスを使用
                    relative_input_files.append(file_path_abs)

            # defaults形式に変換
            defaults_data = app_config_to_defaults(app_config, relative_input_files)

            # ファイルに保存
            if save_defaults_file(file_path, defaults_data):
                QMessageBox.information(self, "完了", f"プロジェクトファイル '{Path(file_path).name}' を保存しました。")
            else:
                QMessageBox.warning(self, "エラー", "プロジェクトファイルの保存に失敗しました。")

        except Exception as e:
            QMessageBox.warning(self, "エラー", f"プロジェクトファイルの保存に失敗しました: {e}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        """ドラッグエンター時の処理"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """ドロップ時の処理"""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.md', '.markdown', '.mdown', '.mkd', '.bib', '.json', '.yaml', '.yml')):
                files.append(file_path)

        if files:
            for file_path in files:
                # YAMLファイルの特別処理：Pandoc defaults fileかチェック
                if file_path.lower().endswith(('.yaml', '.yml')):
                    if self.is_pandoc_defaults_file(file_path):
                        # プロジェクトファイルとして読み込み
                        self.load_project_file_direct(file_path)
                        continue

                # その他のファイルは通常の入力ファイルとして処理
                if file_path.lower().endswith(('.md', '.markdown', '.mdown', '.mkd', '.bib', '.json', '.yaml', '.yml')):
                    # 重複チェック
                    is_duplicate = False
                    for i in range(self.ui.file_list.count()):
                        if self.ui.file_list.item(i).data(256) == file_path:
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        display_name = self._get_file_display_name(file_path)
                        item = QListWidgetItem(display_name)
                        item.setData(256, file_path)
                        self.ui.file_list.addItem(item)
    
    def is_pandoc_defaults_file(self, file_path: str) -> bool:
        """
        YAMLファイルがPandoc defaults fileかを判定

        Args:
            file_path: YAMLファイルのパス

        Returns:
            Pandoc defaults fileの場合 True
        """
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                return False

            # Pandoc defaults fileの特徴的なキーをチェック
            pandoc_keys = [
                'input-files', 'output-file', 'variables', 'metadata',
                'from', 'to', 'bibliography', 'toc', 'number-sections',
                'citeproc', 'pdf-engine', 'template', 'filters', 'standalone'
            ]

            # いずれかのキーが存在すればPandoc defaults fileと判定
            return any(key in data for key in pandoc_keys)

        except Exception:
            return False

    def load_project_file_direct(self, file_path: str):
        """
        ファイルパスを直接指定してプロジェクトファイルを読み込み

        Args:
            file_path: プロジェクトファイルのパス
        """
        try:
            # defaults fileを読み込み
            defaults_data = load_defaults_file(file_path)
            project_dir = Path(file_path).parent

            # アプリケーション内部形式に変換
            app_config = defaults_to_app_config(defaults_data, project_dir)

            # UIに適用
            self.apply_project_to_ui(app_config, defaults_data)

            # 現在のプロジェクトファイルパスを保存
            self.current_project_path = file_path
            self.ui.current_project_file.setText(str(Path(file_path).name))

            self.append_log(f"プロジェクトファイルを読み込みました: {Path(file_path).name}\n")

        except Exception as e:
            QMessageBox.warning(self, "エラー", f"プロジェクトファイルの読み込みに失敗しました: {e}")

    def closeEvent(self, event: QCloseEvent):
        """アプリケーション終了時の処理"""
        # 実行中のプロセスを停止
        if self.worker.proc.state() != self.worker.proc.ProcessState.NotRunning:
            self.worker.terminate_process()

        super().closeEvent(event)


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    app.setApplicationName("Pandoc GUI Converter")
    app.setOrganizationName("PandocGUI")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main() 