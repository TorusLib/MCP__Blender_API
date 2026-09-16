# CONTEXT.md — Контекст проекта

## Статус проекта

**Версия:** 0.3.2
**Последнее обновление:** 2026-08-02
**Статус:** Готов к использованию

## Описание

Локальная база данных Python API Blender (версии 3.6, 4.5, 5.1) с поиском через MCP-сервер и HTTP REST API.

**68 669 символов, 65 567 описаний.** Работает автономно — без интернета.

## Структура проекта

```
MCP__Blender_API/
├── start_mcp_server.bat      ← Главный запуск (HTTP сервер + авто-настройка)
├── pyrightconfig.json        ← Настройка basedpyright для Zed
├── .gitattributes            ← Правила для git (переводы строк)
├── .gitignore                ← Исключения из git
│
├── _mcp_server/              ← Исходный код сервера
│   ├── server.py             ← MCP сервер (stdio, FastMCP)
│   ├── api_server.py         ← HTTP REST сервер (FastAPI)
│   ├── business_logic.py     ← Общий слой логики (MCP + HTTP)
│   ├── database.py           ← SQLite слой (схемы, поиск, кэш, FTS5)
│   ├── indexer.py            ← Оркестратор индексации
│   ├── parser_html.py        ← Парсер HTML-документации
│   ├── parser_inv.py         ← Парсер objects.inv (Sphinx)
│   ├── config.py             ← Глобальные пути и настройки
│   ├── utils.py              ← Утилиты (MD5 хеширование)
│   ├── requirements.txt      ← Зависимости Python
│   └── docs/                 ← Внутренняя документация
│       ├── DOC_PARSER.md
│       ├── HTML_STRUCTURES_REFERENCE.md
│       └── MULTI-TRANSPORT.md
│
├── BD_BASE/                  ← База данных и инструменты
│   ├── blender_api.db        ← SQLite БД (~75 MB, не в git)
│   ├── init.bat              ← Настройка venv + зависимости
│   ├── start_indexer.bat     ← Индексация HTML → БД
│   ├── check_db.bat          ← Проверка состояния БД
│   └── force_reindex.bat     ← Полная переиндексация
│
├── API_DOC/                  ← HTML-документация Blender (не в git)
│   ├── 3_6/                  ← Blender 3.6 API docs
│   ├── 4_5/                  ← Blender 4.5 API docs
│   └── 5_1/                  ← Blender 5.1 API docs
│
├── dev_tests/                ← Папка для dev-тестов (пустая, не в git)
│   └── .gitkeep              ← Маркер для создания пустой папки в git
│
├── README.md                 ← Основная документация
├── START_HERE.md             ← Руководство пользователя
├── ARCHITECTURE.md           ← Архитектура и код
│
└── .agents/skills/           ← Скиллы для Zed agent
    ├── blender-docs-html/
    ├── blender-docs-indexer/
    ├── blender-docs-mcp/
    └── blender-docs-project/
```

## Ключевые решения архитектуры

### Портативность
- Все пути вычисляются от `config.py` относительно корня проекта
- `.venv/` — своё виртуальное окружение, не требует системного Python
- Все `.bat`-файлы используют `VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe`

### Два режима работы
1. **HTTP REST** (FastAPI, порт 18723) — для WebUI, curl, мобильных приложений
2. **MCP stdio** (FastMCP) — для Zed, Cursor, Claude Desktop

Оба режима используют одну бизнес-логику (`business_logic.py`).

### Инкрементальная индексация
- MD5 хеши файлов в `file_hashes` таблице
- Изменённые файлы переиндексируются за ~0.1 сек
- Полная переиндексация — ~10 мин

### Кэш поиска
- TTL: 10 минут (`CACHE_TTL_SECONDS = 600`)
- Лимит: 500 записей (`CACHE_MAX_ENTRIES = 500`)
- Автоочистка при каждом сохранении

## Зависимости

```
mcp>=1.0.0          # MCP протокол
beautifulsoup4>=4.12.0  # Парсинг HTML
lxml>=5.0.0         # XML/HTML парсер
fastapi>=0.110.0    # HTTP сервер
uvicorn>=0.29.0     # ASGI сервер
```

## Как добавить новую версию Blender

1. Скачать доки: https://docs.blender.org/api/current/index.html
2. Распаковать → скопировать `docs/python_api` в `API_DOC/X_Y/`
3. Запустить: `BD_BASE\start_indexer.bat`

## Что НЕ в git

- `API_DOC/` — 1.4 GB HTML-документации (скачивается отдельно)
- `BD_BASE/blender_api.db` — база данных (~75 MB)
- `.venv/` — виртуальное окружение
- `__pycache__/`, `*.pyc` — кэш Python
- `TODO.md`, `CHANGELOG.md` — рабочая документация
- `dev_tests/` — содержимое (папка создана через `.gitkeep`)

## Что в git

- Исходный код `_mcp_server/`
- Батники `BD_BASE/*.bat`, `start_mcp_server.bat`
- Документация `README.md`, `START_HERE.md`, `ARCHITECTURE.md`
- Скиллы `.agents/skills/`
- `.gitignore`, `.gitattributes`, `pyrightconfig.json`
