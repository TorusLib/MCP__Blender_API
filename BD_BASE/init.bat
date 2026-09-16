@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM ============================================================
REM Определяем корень проекта
REM ============================================================
set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

REM Глобальная переменная — ВСЕ скрипты используют этот питон
set "VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe"

echo ========================================
echo  Blender API Docs - Настройка окружения
echo ========================================
echo.

REM Создаём venv если нет
if not exist "%VENV_PYTHON%" (
    echo [Step 1/2] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv
        pause >nul
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [SKIP] Virtual environment already exists
)

REM Устанавливаем зависимости через venv/python -m pip
echo.
echo [Step 2/2] Installing dependencies...
"%VENV_PYTHON%" -m pip install -r _mcp_server\requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause >nul
    exit /b 1
)
echo [OK] Dependencies installed

echo.
echo ========================================
echo  Setup complete
========================================
echo.
echo Next steps:
echo  1. Run: start_mcp_server.bat (для запуска сервера)
echo  2. Or: BD_BASE\start_indexer.bat (для индексации)
echo.
pause >nul
