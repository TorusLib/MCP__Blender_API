@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM ============================================================
REM Определяем корень проекта
REM ============================================================
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM Глобальная переменная — ВСЕ скрипты используют этот питон
set "VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe"

echo ========================================
echo  Blender API Docs - HTTP Server
echo ========================================
echo.

echo ============================================================
echo  MCP-сервер (stdio) — конфигурация для Zed / Cursor / Windsurf
echo ============================================================
echo.
echo  command: "%VENV_PYTHON%"
echo  args:    "_mcp_server\server.py"
echo  env:     PYTHONPATH="%ROOT_DIR%\_mcp_server"
echo.
echo  JSON для Zed Settings (context_servers):
echo.
echo    "blender-api-docs": {
echo      "enabled": true,
echo      "command": ".venv/Scripts/python.exe",
echo      "args": ["_mcp_server/server.py"],
echo      "env": {"PYTHONPATH": "_mcp_server"}
echo    }
echo.
echo ---
echo.

REM ─── Шаг 1: Проверка/создание venv ─────────────────────────────────────

if not exist "%VENV_PYTHON%" (
    echo [Step 1/2] Virtual environment not found. Setting up...
    echo.
    call BD_BASE\init.bat
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to setup virtual environment.
        pause >nul
        exit /b 1
    )
    echo.
)

echo [Step 1/2] Virtual environment ready.

REM ─── Шаг 2: Запуск сервера ───────────────────────────────────────────

set PYTHONPATH=%ROOT_DIR%\_mcp_server;%PYTHONPATH%

set "HTTP_PORT="
if not "%~1"=="" set "HTTP_PORT=%~1"

echo.
if defined HTTP_PORT (
    echo [Step 2/2] Starting HTTP API server on port !HTTP_PORT!...
) else (
    echo [Step 2/2] Starting HTTP API server on default port...
)
echo.
echo  Чтобы задать свой порт: start_mcp_server.bat ^<порт^>
echo  Пример: start_mcp_server.bat 8080
echo.

if defined HTTP_PORT (
    "%VENV_PYTHON%" _mcp_server\api_server.py --port "!HTTP_PORT!"
) else (
    "%VENV_PYTHON%" _mcp_server\api_server.py
)

echo.
echo HTTP server stopped. Press any key to exit.
pause >nul
