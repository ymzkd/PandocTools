"""
Pandoc defaults file 管理モジュール
"""
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import sys

# 共通モジュールから定数をインポート
from common import BASE_DIR


def load_defaults_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Pandoc defaults fileを読み込む

    Args:
        file_path: defaults fileのパス

    Returns:
        defaults fileの内容
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Defaults file not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise ValueError(f"Failed to load defaults file: {e}")


def save_defaults_file(file_path: Union[str, Path], data: Dict[str, Any]) -> bool:
    """
    Pandoc defaults fileを保存する

    Args:
        file_path: 保存先パス
        data: 保存するdefaults data

    Returns:
        保存成功時 True
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"Defaults file保存エラー: {e}")
        return False


def defaults_to_app_config(defaults_data: Dict[str, Any], project_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Pandoc defaults形式から内部アプリケーション設定形式に変換

    Args:
        defaults_data: Pandoc defaults fileの内容
        project_dir: プロジェクトファイルのディレクトリ（相対パス解決用）

    Returns:
        アプリケーション内部形式の設定データ
    """
    app_config = {
        'input_files': [],
        'output_file': '',
        'output_format': 'pdf',
        'extra_args': [],
        'lua_filter': '',
        'template': '',
        'bibliography': '',
        'merge_files': True,
        'output_filename': '',
        'metadata': {}
    }

    # 入力ファイル
    all_input_files = []
    if 'input-files' in defaults_data:
        input_files = defaults_data['input-files']
        if isinstance(input_files, list):
            all_input_files.extend(input_files)

    # 参考文献ファイルも入力ファイルに含める
    if 'bibliography' in defaults_data:
        bibliography = defaults_data['bibliography']
        if isinstance(bibliography, list):
            all_input_files.extend(bibliography)
        elif isinstance(bibliography, str):
            all_input_files.append(bibliography)

    if all_input_files:
        if project_dir:
            # 相対パスをプロジェクトディレクトリを基準に解決
            app_config['input_files'] = [
                str((project_dir / file).resolve()) if not Path(file).is_absolute()
                else str(file) for file in all_input_files
            ]
        else:
            app_config['input_files'] = [str(file) for file in all_input_files]

    # 出力ファイル名（ファイル名のみ）
    if 'output-file' in defaults_data:
        output_file = defaults_data['output-file']
        output_path = Path(output_file)
        # ファイル名のみを保存
        app_config['output_filename'] = output_path.name
        # 出力形式を拡張子から推測
        if output_path.suffix:
            app_config['output_format'] = output_path.suffix[1:]  # 先頭の.を除去

    # 基本的なフラグをextra_argsに変換
    extra_args = []

    # 目次
    if defaults_data.get('toc', False):
        extra_args.append('--toc')

    # セクション番号
    if defaults_data.get('number-sections', False):
        extra_args.append('--number-sections')

    # 引用処理
    if defaults_data.get('citeproc', False):
        extra_args.append('--citeproc')

    # スタンドアロン
    if defaults_data.get('standalone', False):
        extra_args.append('--standalone')

    # PDF エンジン
    if 'pdf-engine' in defaults_data:
        extra_args.extend(['--pdf-engine', defaults_data['pdf-engine']])

    # テンプレート
    if 'template' in defaults_data:
        template_path = defaults_data['template']
        if project_dir and not Path(template_path).is_absolute():
            template_path = str((project_dir / template_path).resolve())
        app_config['template'] = str(template_path)
        extra_args.extend(['--template', str(template_path)])

    # 参考文献
    if 'bibliography' in defaults_data:
        bibliography = defaults_data['bibliography']
        if isinstance(bibliography, list) and bibliography:
            bib_file = bibliography[0]  # 最初のファイルを使用
            if project_dir and not Path(bib_file).is_absolute():
                bib_file = str((project_dir / bib_file).resolve())
            app_config['bibliography'] = str(bib_file)
            extra_args.extend(['--bibliography', str(bib_file)])
        elif isinstance(bibliography, str):
            if project_dir and not Path(bibliography).is_absolute():
                bibliography = str((project_dir / bibliography).resolve())
            app_config['bibliography'] = str(bibliography)
            extra_args.extend(['--bibliography', str(bibliography)])


    # Variables
    if 'variables' in defaults_data:
        variables = defaults_data['variables']
        for key, value in variables.items():
            if key == 'geometry' and isinstance(value, list):
                # geometryがリスト形式の場合
                geometry_str = ','.join(value)
                extra_args.extend(['-V', f'geometry:{geometry_str}'])
            else:
                extra_args.extend(['-V', f'{key}={value}'])

    # Filters
    if 'filters' in defaults_data:
        filters = defaults_data['filters']
        if isinstance(filters, list):
            for filter_item in filters:
                if isinstance(filter_item, str):
                    # Lua filter
                    if filter_item.endswith('.lua'):
                        if project_dir and not Path(filter_item).is_absolute():
                            filter_item = str((project_dir / filter_item).resolve())
                        app_config['lua_filter'] = str(filter_item)
                        extra_args.extend(['--lua-filter', str(filter_item)])
                    else:
                        # Other filters
                        extra_args.extend(['--filter', filter_item])

    # Input/Output formats
    if 'from' in defaults_data:
        extra_args.extend(['--from', defaults_data['from']])

    if 'to' in defaults_data:
        extra_args.extend(['--to', defaults_data['to']])

    # Metadata
    if 'metadata' in defaults_data:
        app_config['metadata'] = defaults_data['metadata'].copy()
        for key, value in defaults_data['metadata'].items():
            extra_args.extend(['-M', f'{key}={value}'])

    app_config['extra_args'] = extra_args

    return app_config


def app_config_to_defaults(app_config: Dict[str, Any], input_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    アプリケーション内部設定形式からPandoc defaults形式に変換

    Args:
        app_config: アプリケーション内部設定
        input_files: 入力ファイルリスト（指定された場合）

    Returns:
        Pandoc defaults形式のデータ
    """
    defaults_data = {}

    # 入力ファイルと参考文献ファイルを分離
    files_to_process = input_files if input_files else app_config.get('input_files', [])

    regular_files = []
    bibliography_files = []

    for file_path in files_to_process:
        path = Path(file_path)
        if path.suffix.lower() in ['.bib', '.json', '.yaml', '.yml']:
            # YAMLやJSONファイルの場合、拡張子だけでは判別困難なため、.bibのみを参考文献とする
            if path.suffix.lower() == '.bib':
                bibliography_files.append(file_path)
            else:
                regular_files.append(file_path)
        else:
            regular_files.append(file_path)

    if regular_files:
        defaults_data['input-files'] = regular_files

    if bibliography_files:
        defaults_data['bibliography'] = bibliography_files

    # 出力ファイル名（ファイル名のみ）
    if app_config.get('output_filename'):
        defaults_data['output-file'] = app_config['output_filename']

    # extra_argsを解析してdefaults形式に変換
    extra_args = app_config.get('extra_args', [])
    i = 0
    while i < len(extra_args):
        arg = extra_args[i]

        if arg == '--toc':
            defaults_data['toc'] = True
        elif arg == '--number-sections':
            defaults_data['number-sections'] = True
        elif arg == '--citeproc':
            defaults_data['citeproc'] = True
        elif arg == '--standalone':
            defaults_data['standalone'] = True
        elif arg == '--pdf-engine' and i + 1 < len(extra_args):
            defaults_data['pdf-engine'] = extra_args[i + 1]
            i += 1
        elif arg == '--template' and i + 1 < len(extra_args):
            defaults_data['template'] = extra_args[i + 1]
            i += 1
        elif arg == '--bibliography' and i + 1 < len(extra_args):
            defaults_data['bibliography'] = [extra_args[i + 1]]
            i += 1
        elif arg == '-V' and i + 1 < len(extra_args):
            # Variables
            var_setting = extra_args[i + 1]
            if '=' in var_setting:
                key, value = var_setting.split('=', 1)
                # documentclassとclassoptionは除外
                if key not in ['documentclass', 'classoption']:
                    if 'variables' not in defaults_data:
                        defaults_data['variables'] = {}
                    # geometry設定は特別処理
                    if key.startswith('geometry:'):
                        # geometry:以降の部分を取得
                        geometry_str = key.split(':', 1)[1] + '=' + value
                        geometry_parts = geometry_str.split(',')
                        # 重複を除去してリスト形式で保存
                        unique_parts = []
                        seen = set()
                        for part in geometry_parts:
                            part = part.strip()
                            if part and part not in seen:
                                unique_parts.append(part)
                                seen.add(part)
                        defaults_data['variables']['geometry'] = unique_parts
                    else:
                        defaults_data['variables'][key] = value
            i += 1
        elif arg == '-M' and i + 1 < len(extra_args):
            # Metadata
            meta_setting = extra_args[i + 1]
            if '=' in meta_setting:
                key, value = meta_setting.split('=', 1)
                if 'metadata' not in defaults_data:
                    defaults_data['metadata'] = {}
                defaults_data['metadata'][key] = value
            i += 1
        # from, to, lua-filterは除外（不要なフィールド）

        i += 1

    # その他の設定
    if app_config.get('bibliography'):
        defaults_data['bibliography'] = [app_config['bibliography']]

    if app_config.get('template'):
        defaults_data['template'] = app_config['template']


    if app_config.get('lua_filter'):
        if 'filters' not in defaults_data:
            defaults_data['filters'] = []
        defaults_data['filters'].append(app_config['lua_filter'])

    # Metadata
    if app_config.get('metadata'):
        if 'metadata' not in defaults_data:
            defaults_data['metadata'] = {}
        defaults_data['metadata'].update(app_config['metadata'])

    return defaults_data


def get_defaults_file_template() -> Dict[str, Any]:
    """
    新しいdefaults fileのテンプレートを返す

    Returns:
        テンプレートデータ
    """
    return {
        'input-files': [],
        'output-file': 'output.pdf',
        'from': 'markdown',
        'to': 'pdf',
        'toc': True,
        'number-sections': True,
        'citeproc': True,
        'variables': {
            'fontsize': '12pt',
            'papersize': 'a4paper',
            'geometry': 'margin=25mm'
        },
        'metadata': {
            'title': 'Document Title'
        }
    }