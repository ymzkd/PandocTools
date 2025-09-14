@echo off
echo Building PandocTools with PyInstaller...

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
    if exist "src\templates" (
        xcopy /E /I /Y "src\templates" "dist\templates\" >nul 2>&1 || echo Warning: Could not copy templates
    )
    
    echo.
    echo Executable and resources ready in dist folder:
    echo - dist\Pandoc GUI Converter.exe
    echo - dist\profiles\
    echo - dist\filters\
    echo - dist\templates\ (if exists)
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