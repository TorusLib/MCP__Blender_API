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
echo  Blender API Docs - Проверка БД
echo ========================================
echo.

REM Проверяем что venv существует
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Run BD_BASE\init.bat first to set up the project.
    pause >nul
    exit /b 1
)

REM Запускаем проверку
set PYTHONPATH=%ROOT_DIR%\_mcp_server;%PYTHONPATH%
"%VENV_PYTHON%" "BD_BASE\check_db.py"

echo.
echo ========================================
echo  Проверка завершена
echo ========================================
echo.
pause >nul
