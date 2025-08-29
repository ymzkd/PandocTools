# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PandocTools is a Windows GUI application for Pandoc document conversion, built with Python and PyQt6. It provides an intuitive interface for converting Markdown files to PDF, HTML, DOCX and other formats using Pandoc, with support for complex LaTeX matrices, file merging, and configuration profiles.

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

### Key Features Implementation
- **File Management**: Drag & drop support, batch processing, file ordering
- **Conversion Modes**: Single file, merged files, or individual batch conversion
- **LaTeX Matrix Support**: Dynamic MaxMatrixCols setting via temporary header files
- **Profile System**: YAML-based configuration saving/loading in profiles/ directory
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
└── filters/
    └── default_filter.lua   # Built-in Lua filter (always applied)

profiles/                # YAML configuration files
├── default.yml          # Default PDF conversion settings  
├── sample_html.yml      # HTML conversion example
├── compact.yml          # Compact document (small font, narrow margins)
├── presentation.yml     # Presentation format (large font, wide margins)
└── letter.yml           # Letter paper size format
```

## Configuration

### Default Pandoc Arguments
The application always applies these base arguments:
- `--lua-filter=src/filters/default_filter.lua` (built-in filter)
- User-configurable options via GUI tabs

### Profile Format (YAML)
```yaml
output_format: pdf
extra_args:
  - --wrap=preserve
  - --pdf-engine=xelatex
  - -V
  - documentclass=bxjsarticle
merge_files: true
max_matrix_cols: 20
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