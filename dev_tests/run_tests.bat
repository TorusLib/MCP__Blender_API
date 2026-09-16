@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0.."
set "ROOT_DIR=%~dp0.."
set "VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe"

REM Добавить _mcp_server в PYTHONPATH для импортов
set "PYTHONPATH=%ROOT_DIR%\_mcp_server;%PYTHONPATH%"

echo === Dev Tests Runner ===
echo Root: %ROOT_DIR%
echo Python: %VENV_PYTHON%
echo.

if not exist "%VENV_PYTHON%" (
    echo ERROR: .venv not found. Run BD_BASE\init.bat first.
    pause
    exit /b 1
)

"%VENV_PYTHON%" dev_tests\dev_test_runner.py %*
