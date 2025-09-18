"""
PyQt6 による GUI メインウィンドウ定義
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit, QCheckBox,
    QFileDialog, QGroupBox, QSplitter, QProgressBar, QMessageBox,
    QListWidget, QTabWidget, QSpinBox, QFormLayout, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QAction
import os
from pathlib import Path


class Ui_MainWindow:
    """メインウィンドウのUI定義クラス"""
    
    def setupUi(self, MainWindow):
        """UI コンポーネントを設定"""
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowTitle("Pandoc GUI Converter")
        MainWindow.resize(1000, 600)  # 高さを縮小
        
        # 中央ウィジェット
        self.centralwidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(self.centralwidget)
        
        # メインレイアウト
        self.main_layout = QVBoxLayout(self.centralwidget)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # 基本設定タブ
        self._setup_basic_tab()
        
        # 詳細設定タブ
        self._setup_advanced_tab()
        
        # プロファイル管理タブ
        self._setup_profile_tab()
        
        # 実行・ログエリア
        self._setup_execution_area()
        
        # ステータスバー
        self._setup_status_bar(MainWindow)
        
        
    def _setup_basic_tab(self):
        """基本設定タブの設定"""
        self.basic_tab = QWidget()
        self.tab_widget.addTab(self.basic_tab, "基本設定")
        
        layout = QVBoxLayout(self.basic_tab)
        
        # 入力ファイル設定
        input_group = QGroupBox("入力ファイル")
        input_layout = QVBoxLayout(input_group)
        
        # ファイル操作ボタン
        file_buttons_layout = QHBoxLayout()
        self.btn_select_files = QPushButton("ファイル選択")
        self.btn_select_folder = QPushButton("フォルダ選択")
        self.btn_clear_files = QPushButton("全クリア")

        self.btn_select_files.setMinimumWidth(100)
        self.btn_select_folder.setMinimumWidth(100)
        self.btn_clear_files.setMinimumWidth(100)

        file_buttons_layout.addWidget(self.btn_select_files)
        file_buttons_layout.addWidget(self.btn_select_folder)
        file_buttons_layout.addWidget(self.btn_clear_files)
        file_buttons_layout.addStretch()
        input_layout.addLayout(file_buttons_layout)
        
        # ファイルリストと操作ボタン
        list_and_controls_layout = QHBoxLayout()
        
        # ファイル一覧
        list_layout = QVBoxLayout()
        list_layout.addWidget(QLabel("選択されたファイル:"))
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(150)
        self.file_list.setMaximumHeight(200)
        # ドラッグ&ドロップで順序変更を有効化
        self.file_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        list_layout.addWidget(self.file_list)
        
        # リスト操作ボタン
        list_controls_layout = QVBoxLayout()
        self.btn_move_up = QPushButton("↑ 上へ")
        self.btn_move_down = QPushButton("↓ 下へ")
        self.btn_remove_file = QPushButton("削除")
        
        self.btn_move_up.setMinimumWidth(80)
        self.btn_move_down.setMinimumWidth(80)
        self.btn_remove_file.setMinimumWidth(80)
        
        list_controls_layout.addWidget(self.btn_move_up)
        list_controls_layout.addWidget(self.btn_move_down)
        list_controls_layout.addWidget(self.btn_remove_file)
        list_controls_layout.addStretch()
        
        list_and_controls_layout.addLayout(list_layout)
        list_and_controls_layout.addLayout(list_controls_layout)
        input_layout.addLayout(list_and_controls_layout)
        
        # 複数ファイル処理オプション
        multi_option_layout = QHBoxLayout()
        self.merge_files = QCheckBox("複数ファイルを結合して一つのファイルに変換")
        self.merge_files.setChecked(True)  # デフォルトで有効
        multi_option_layout.addWidget(self.merge_files)
        multi_option_layout.addStretch()
        input_layout.addLayout(multi_option_layout)
        
        layout.addWidget(input_group)

        # プロジェクトファイル設定
        project_group = QGroupBox("プロジェクトファイル（Pandoc defaults file）")
        project_layout = QFormLayout(project_group)

        # 現在のプロジェクトファイル表示
        self.current_project_file = QLineEdit()
        self.current_project_file.setReadOnly(True)
        self.current_project_file.setPlaceholderText("プロジェクトファイルが読み込まれていません")
        project_layout.addRow("現在のファイル:", self.current_project_file)

        # プロジェクトファイル操作ボタン
        project_buttons_layout = QHBoxLayout()
        self.btn_load_project = QPushButton("読み込み")
        self.btn_save_project = QPushButton("保存")
        self.btn_save_project_as = QPushButton("名前を付けて保存")

        self.btn_load_project.setMinimumWidth(100)
        self.btn_save_project.setMinimumWidth(100)
        self.btn_save_project_as.setMinimumWidth(120)

        project_buttons_layout.addWidget(self.btn_load_project)
        project_buttons_layout.addWidget(self.btn_save_project)
        project_buttons_layout.addWidget(self.btn_save_project_as)
        project_buttons_layout.addStretch()

        project_layout.addRow("操作:", project_buttons_layout)

        layout.addWidget(project_group)

        # 出力設定
        output_group = QGroupBox("出力設定")
        output_layout = QFormLayout(output_group)
        
        # 出力形式
        self.output_format = QComboBox()
        self.output_format.addItems(["pdf", "tex", "docx"])
        output_layout.addRow("出力形式:", self.output_format)
        
        # 出力ディレクトリ
        output_dir_layout = QHBoxLayout()
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("出力ディレクトリ（空の場合は入力ファイルと同じディレクトリ）")
        self.btn_select_output_dir = QPushButton("選択")
        output_dir_layout.addWidget(self.output_dir)
        output_dir_layout.addWidget(self.btn_select_output_dir)
        
        output_layout.addRow("出力ディレクトリ:", output_dir_layout)
        
        # 出力ファイル名
        output_name_layout = QHBoxLayout()
        self.output_filename = QLineEdit()
        self.output_filename.setPlaceholderText("出力ファイル名（空の場合は自動生成）")
        output_name_layout.addWidget(self.output_filename)
        output_layout.addRow("出力ファイル名:", output_name_layout)
        
        
        
        layout.addWidget(output_group)
        
        layout.addStretch()
        
    def _setup_advanced_tab(self):
        """詳細設定タブの設定"""
        self.advanced_tab = QWidget()
        self.tab_widget.addTab(self.advanced_tab, "オプション設定")
        
        # スクロールエリアを作成
        scroll_area = QScrollArea()
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        
        # 基本オプション
        basic_options_group = QGroupBox("基本オプション")
        basic_options_layout = QFormLayout(basic_options_group)
        
        # PDF エンジン
        self.pdf_engine = QComboBox()
        self.pdf_engine.addItems(["xelatex", "pdflatex", "lualatex", "tectonic", "wkhtmltopdf", "weasyprint"])
        basic_options_layout.addRow("PDFエンジン:", self.pdf_engine)
        
        # ドキュメントクラス
        self.document_class = QLineEdit("bxjsarticle")
        basic_options_layout.addRow("ドキュメントクラス:", self.document_class)
        
        # クラスオプション
        self.class_option = QLineEdit("pandoc")
        basic_options_layout.addRow("クラスオプション:", self.class_option)
        
        # Markdown拡張
        self.markdown_extensions = QLineEdit("markdown+hard_line_breaks")
        basic_options_layout.addRow("Markdown拡張:", self.markdown_extensions)
        
        # フォントサイズ
        self.font_size = QComboBox()
        self.font_size.addItems(["", "8pt", "9pt", "10pt", "11pt", "12pt", "14pt", "17pt", "20pt", "25pt"])
        self.font_size.setCurrentText("")  # デフォルトは未設定
        basic_options_layout.addRow("フォントサイズ:", self.font_size)
        
        # 用紙サイズ
        self.paper_size = QComboBox()
        self.paper_size.addItems(["", "a3paper", "a4paper", "a5paper", "b4paper", "b5paper", "letterpaper"])
        self.paper_size.setCurrentText("")  # デフォルトは未設定
        basic_options_layout.addRow("用紙サイズ:", self.paper_size)
        
        # 余白設定（詳細）
        margin_group = QGroupBox("余白設定")
        margin_layout = QGridLayout(margin_group)
        
        self.margin_top = QLineEdit()
        self.margin_top.setPlaceholderText("例: 20mm")
        margin_layout.addWidget(QLabel("上:"), 0, 0)
        margin_layout.addWidget(self.margin_top, 0, 1)
        
        self.margin_bottom = QLineEdit()
        self.margin_bottom.setPlaceholderText("例: 20mm")
        margin_layout.addWidget(QLabel("下:"), 0, 2)
        margin_layout.addWidget(self.margin_bottom, 0, 3)
        
        self.margin_left = QLineEdit()
        self.margin_left.setPlaceholderText("例: 25mm")
        margin_layout.addWidget(QLabel("左:"), 1, 0)
        margin_layout.addWidget(self.margin_left, 1, 1)
        
        self.margin_right = QLineEdit()
        self.margin_right.setPlaceholderText("例: 25mm")
        margin_layout.addWidget(QLabel("右:"), 1, 2)
        margin_layout.addWidget(self.margin_right, 1, 3)
        
        # フッター間隔（footskip）
        self.footskip = QLineEdit()
        self.footskip.setPlaceholderText("例: 20pt, 25pt")
        margin_layout.addWidget(QLabel("フッター間隔:"), 2, 0)
        margin_layout.addWidget(self.footskip, 2, 1)
        
        layout.addWidget(margin_group)
        
        
        layout.addWidget(basic_options_group)
        
        # フィルター設定
        filter_group = QGroupBox("追加フィルターとテンプレート")
        filter_layout = QFormLayout(filter_group)
        
        # 追加 Lua フィルター（default_filter.luaは内蔵のため表示のみ）
        filter_info_layout = QVBoxLayout()
        filter_info_layout.addWidget(QLabel("内蔵フィルター: default_filter.lua (常に適用)"))
        
        lua_layout = QHBoxLayout()
        self.lua_filter = QLineEdit()
        self.lua_filter.setPlaceholderText("追加のLuaフィルターファイルのパス (オプション)")
        self.btn_select_lua = QPushButton("選択")
        lua_layout.addWidget(self.lua_filter)
        lua_layout.addWidget(self.btn_select_lua)
        filter_info_layout.addLayout(lua_layout)
        
        filter_layout.addRow("Luaフィルター:", filter_info_layout)
        
        # テンプレート
        template_layout = QHBoxLayout()
        self.template_file = QLineEdit()
        self.template_file.setPlaceholderText("テンプレートファイルのパス")
        self.btn_select_template = QPushButton("選択")
        template_layout.addWidget(self.template_file)
        template_layout.addWidget(self.btn_select_template)
        filter_layout.addRow("テンプレート:", template_layout)
        
        
        
        layout.addWidget(filter_group)
        
        # チェックボックスオプション
        checkbox_group = QGroupBox("オプション")
        checkbox_layout = QGridLayout(checkbox_group)
        
        self.wrap_preserve = QCheckBox("改行を保持 (--wrap=preserve)")
        self.wrap_preserve.setChecked(True)
        checkbox_layout.addWidget(self.wrap_preserve, 0, 0)
        
        self.table_of_contents = QCheckBox("目次を生成 (--toc)")
        checkbox_layout.addWidget(self.table_of_contents, 0, 1)

        self.number_sections = QCheckBox("セクション番号 (--number-sections)")
        checkbox_layout.addWidget(self.number_sections, 1, 0)

        self.citeproc = QCheckBox("引用処理 (--citeproc)")
        checkbox_layout.addWidget(self.citeproc, 1, 1)

        self.standalone = QCheckBox("スタンドアロン出力 (--standalone)")
        self.standalone.setChecked(True)
        checkbox_layout.addWidget(self.standalone, 2, 0)
        
        layout.addWidget(checkbox_group)
        
        # カスタム引数
        custom_group = QGroupBox("カスタム引数")
        custom_layout = QVBoxLayout(custom_group)
        
        custom_layout.addWidget(QLabel("追加のPandoc引数 (1行に1つずつ):"))
        self.custom_args = QTextEdit()
        self.custom_args.setMaximumHeight(100)
        self.custom_args.setPlaceholderText("例:\n--dpi=300\n-V geometry:margin=2cm")
        custom_layout.addWidget(self.custom_args)
        
        layout.addWidget(custom_group)
        
        layout.addStretch()
        
        # スクロールエリアの設定
        scroll_area.setWidget(scroll_content)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # タブにスクロールエリアを追加
        tab_layout = QVBoxLayout(self.advanced_tab)
        tab_layout.addWidget(scroll_area)
        
    def _setup_profile_tab(self):
        """プロファイル管理タブの設定"""
        self.profile_tab = QWidget()
        self.tab_widget.addTab(self.profile_tab, "プロファイル")
        
        layout = QVBoxLayout(self.profile_tab)
        
        # プロファイル選択・管理
        profile_group = QGroupBox("プロファイル管理")
        profile_layout = QFormLayout(profile_group)
        
        # プロファイル選択
        profile_select_layout = QHBoxLayout()
        self.profile_select = QComboBox()
        self.btn_load_profile = QPushButton("読み込み")
        self.btn_refresh_profiles = QPushButton("更新")
        profile_select_layout.addWidget(self.profile_select)
        profile_select_layout.addWidget(self.btn_load_profile)
        profile_select_layout.addWidget(self.btn_refresh_profiles)
        profile_layout.addRow("プロファイル選択:", profile_select_layout)
        
        # プロファイル保存
        save_layout = QHBoxLayout()
        self.profile_name = QLineEdit()
        self.profile_name.setPlaceholderText("新しいプロファイル名")
        self.btn_save_profile = QPushButton("保存")
        self.btn_delete_profile = QPushButton("削除")
        save_layout.addWidget(self.profile_name)
        save_layout.addWidget(self.btn_save_profile)
        save_layout.addWidget(self.btn_delete_profile)
        profile_layout.addRow("プロファイル保存:", save_layout)
        
        layout.addWidget(profile_group)
        
        # プロファイル内容プレビュー
        preview_group = QGroupBox("プロファイル内容")
        preview_layout = QVBoxLayout(preview_group)
        
        self.profile_preview = QTextEdit()
        self.profile_preview.setReadOnly(True)
        self.profile_preview.setMaximumHeight(200)
        preview_layout.addWidget(self.profile_preview)
        
        layout.addWidget(preview_group)
        
        layout.addStretch()
        
    def _setup_execution_area(self):
        """実行・ログエリアの設定"""
        execution_group = QGroupBox("実行")
        execution_layout = QVBoxLayout(execution_group)
        
        # 実行ボタンとプログレスバー
        control_layout = QHBoxLayout()
        
        self.btn_run = QPushButton("変換実行")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.setStyleSheet("QPushButton { font-weight: bold; background-color: #4CAF50; color: white; }")
        
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setEnabled(False)
        
        self.btn_open_output = QPushButton("出力先を開く")
        self.btn_open_output.setMinimumHeight(40)
        self.btn_open_output.setEnabled(False)
        
        self.btn_open_pdf = QPushButton("PDFを開く")
        self.btn_open_pdf.setMinimumHeight(40)
        self.btn_open_pdf.setEnabled(False)
        
        control_layout.addWidget(self.btn_run)
        control_layout.addWidget(self.btn_stop)
        control_layout.addWidget(self.btn_open_output)
        control_layout.addWidget(self.btn_open_pdf)
        control_layout.addStretch()
        
        execution_layout.addLayout(control_layout)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        execution_layout.addWidget(self.progress_bar)
        
        # ログ表示
        log_layout = QVBoxLayout()
        log_layout.addWidget(QLabel("実行ログ:"))
        
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(200)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        # ログクリアボタン
        self.btn_clear_log = QPushButton("ログクリア")
        log_layout.addWidget(self.btn_clear_log)
        
        execution_layout.addLayout(log_layout)
        
        self.main_layout.addWidget(execution_group)
        
    def _setup_status_bar(self, MainWindow):
        """ステータスバーの設定"""
        self.statusbar = MainWindow.statusBar()
        self.statusbar.showMessage("準備完了") 