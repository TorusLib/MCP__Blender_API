# Blender Python API Documentation

Локальная база данных Python API Blender (3.6, 4.5, 5.1) с поиском через MCP-сервер.

**68 669 символов, 65 567 описаний.** Автономно — без интернета.

## ⚠️ Важное

**Без HTML-доков Blender проект не работает.** Без `API_DOC/` нет данных для поиска.

Скачать доки с нужной версией: https://docs.blender.org/api/current/index.html — распаковать в `API_DOC/X_Y/`

## Быстрый старт

```cmd
BD_BASE\init.bat          ← настройка (1 раз)
BD_BASE\start_indexer.bat ← индексация (10 мин)
start_mcp_server.bat      ← запуск MCP-сервера
```

Или просто `start_mcp_server.bat` — он всё сделает сам (venv, БД, сервер).

## Что умеет

10 инструментов поиска: символы, модули, операторы (`bpy.ops`), типы (`bpy.types`), свойства, сравнение версий.

## Режимы запуска

| Режим | Команда | Для чего |
|-------|---------|----------|
| HTTP (REST) | `start_mcp_server.bat` | Zed, Cursor, curl, WebUI (по умолчанию) |

## Стек

Python + SQLite (WAL) · MCP (FastMCP) · BS4 + lxml · Sphinx objects.inv

## Портативность

Все батники используют **только** питон из `.venv/`. Никогда не трогают системный Python.

- Каждый скрипт определяет `VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe`
- Все вызовы идут через `"%VENV_PYTHON%"`
- Скопируй проект → запусти `start_mcp_server.bat` → готово

## Документация

| Файл | Содержание |
|------|-----------|
| [START_HERE](START_HERE.md) | Полное руководство по запуску |
| [ARCHITECTURE](ARCHITECTURE.md) | Архитектура, код, SQL |
| [CONTEXT](CONTEXT.md) | Структура проекта, что в git, что нет |

## Структура

```
blender_python/
├── start_mcp_server.bat      ← главный запуск (HTTP сервер)
├── BD_BASE/                  ← БД + инструменты
│   ├── blender_api.db        ← SQLite (~75 MB)
│   ├── init.bat              ← venv + зависимости
│   ├── start_indexer.bat     ← переиндексация
│   ├── check_db.bat          ← проверка состояния
│   └── force_reindex.bat     ← удалить + пересоздать
├── API_DOC/                  ← HTML-доки Blender (3_6, 4_5, 5_1)
├── _mcp_server/              ← код сервера (9 файлов)
├── .venv/                    ← виртуальное окружение
├── pyrightconfig.json        ← настройка IDE (basedpyright)
└── *.md                      ← документация
```

*Версия: 0.3.3 | Обновлено: 2026-09-16*
