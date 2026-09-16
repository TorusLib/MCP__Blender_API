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
echo  Blender API Docs - Индексация
echo ========================================
echo.

REM Проверяем виртуальное окружение
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Run BD_BASE\init.bat first to set up the project.
    pause >nul
    exit /b 1
)

echo Starting indexer...
echo.

REM Проверяем аргументы
set FORCE_FLAG=
if /i "%~1"=="--force" set FORCE_FLAG=--force

REM Добавляем _mcp_server в PYTHONPATH для импортов
set PYTHONPATH=%ROOT_DIR%\_mcp_server;%PYTHONPATH%

"%VENV_PYTHON%" _mcp_server\indexer.py !FORCE_FLAG!

echo.
echo ========================================
echo  Indexing complete
echo ========================================

echo.
pause >nul
