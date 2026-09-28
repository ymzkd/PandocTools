@echo off
echo Building PandocTools with PyInstaller...

REM Fetch rsvg-convert into src\bin (skipped if the pinned version is already there).
REM Stop before touching the previous dist: a dist without it would silently lose SVG support.
python scripts\fetch_rsvg_convert.py
if errorlevel 1 (
    echo.
    echo Build failed! Could not fetch rsvg-convert.
    echo Check the network connection and that zstandard is installed ^(uv sync^).
    exit /b 1
)

REM Clean previous build
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

REM Build executable (without bundling resources)
python -m PyInstaller ^
  --name "Pandoc GUI Converter" ^
  --onefile ^
  --noconsole ^
  src/main.py

REM Check if build was successful
if exist "dist\Pandoc GUI Converter.exe" (
    echo.
    echo Build completed successfully!
    
    REM Copy resource directories to dist
    echo Copying resource directories...
    xcopy /E /I /Y "profiles" "dist\profiles\" >nul 2>&1 || echo Warning: Could not copy profiles
    xcopy /E /I /Y "src\filters" "dist\filters\" >nul 2>&1 || echo Warning: Could not copy filters
    xcopy /E /I /Y "src\templates" "dist\templates\" >nul 2>&1 || echo Warning: Could not copy templates
    xcopy /E /I /Y "src\bin" "dist\bin\" >nul 2>&1 || echo Warning: Could not copy bin

    echo.
    echo Executable and resources ready in dist folder:
    echo - dist\Pandoc GUI Converter.exe
    echo - dist\profiles\
    echo - dist\filters\
    echo - dist\templates\ (if exists)
    echo - dist\bin\ (rsvg-convert.exe)
    echo.
    echo You can now run the executable from the dist folder.
    
    REM Explicit success exit
    goto :success
) else (
    echo.
    echo Build failed! Check the output above for errors.
    exit /b 1
)

:success
echo.
echo ===========================================
echo BUILD COMPLETED SUCCESSFULLY!
echo ===========================================
pause
exit /b 0