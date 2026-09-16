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
echo  Blender API Docs - Принудительная переиндексация
echo ========================================
echo.

REM Предупреждение
echo ВНИМАНИЕ! Это удалит старую базу данных и создаст новую.
echo.
set /p confirm="Продолжить? (y/n): "
if /i not "!confirm!"=="y" (
    echo Отменено.
    pause >nul
    exit /b 0
)

REM Проверяем venv
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found!
    echo Run BD_BASE\init.bat first.
    pause >nul
    exit /b 1
)

echo.
echo [Step 1/2] Удаление старой БД...
if exist "BD_BASE\blender_api.db" (
    del "BD_BASE\blender_api.db"
    echo [OK] Старая БД удалена
) else (
    echo [SKIP] БД не найдена, нечего удалять
)

REM Удаляем WAL/SHM (могут восстановить данные из старой БД)
if exist "BD_BASE\blender_api.db-wal" del "BD_BASE\blender_api.db-wal"
if exist "BD_BASE\blender_api.db-shm" del "BD_BASE\blender_api.db-shm"

echo.
echo [Step 2/2] Запуск индексации...
echo.

REM Запускаем индексатор
set PYTHONPATH=%ROOT_DIR%\_mcp_server;%PYTHONPATH%
"%VENV_PYTHON%" _mcp_server\indexer.py

echo.
echo ========================================
echo  Принудительная переиндексация завершена
echo ========================================

echo.
pause >nul
