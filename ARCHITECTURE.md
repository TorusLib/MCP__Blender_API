# Архитектура проекта

## Обзор

```
AI Client (Zed, Cursor)
    │ JSON-RPC (MCP) / HTTP (REST)
    ▼
MCP Server (FastMCP) / HTTP Server (FastAPI)
    │
    ▼
Database Layer (SQLite + WAL)
    │
    ▼
Indexer (indexer.py)
    │
    ▼
API_DOC/3_6/4_5/5_1/*.html + objects.inv
```

## Файлы проекта

| Файл | Назначение |
|------|-----------|
| `pyrightconfig.json` | Настройка basedpyright для Zed (указание `.venv`) |
| `config.py` | Глобальные пути (ROOT, DB_PATH, API_DOC_DIR) |
| `database.py` | SQLite-слой: схемы, INSERT, поиск, кэш (TTL+LIMIT), FTS5 |
| `parser_inv.py` | Парсинг Sphinx `objects.inv` |
| `parser_html.py` | Парсинг HTML: параметры, описания, дефолты |
| `indexer.py` | Оркестратор: версии → inv → HTML → БД |
| `server.py` | MCP-сервер (10 инструментов, вызывает `db.*` напрямую) |
| `business_logic.py` | Общий слой для MCP + HTTP (resolve_version, diff, search_by_prefix) |
| `api_server.py` | HTTP REST сервер (FastAPI, вызывает `db.*` напрямую) |
| `utils.py` | Общие утилиты (compute_md5) |

## Схема БД

```sql
symbols (name, module, symbol_name, role, domain, priority, uri, display_name, version, has_content)
    PK: (name, version)
    IDX: module, role, version, symbol_name

content (id, name, description, params, defaults, has_params, version)
    PK: (id, version)
    IDX: version

content_fts — FTS5 (name, description, version)

file_hashes (version, filename, md5hash, modified_at)
    PK: (version, filename)

search_cache (query, version, cache_key, results, created_at, hits)
    PK: (query, version, cache_key)
```

## Поиск — SQL

```sql
SELECT * FROM symbols
WHERE (name LIKE ? OR symbol_name LIKE ? OR module LIKE ?)
  AND version = ?
ORDER BY CASE
    WHEN LOWER(name) = ? THEN 1
    WHEN name LIKE ? THEN 2
    WHEN symbol_name LIKE ? THEN 3
    ELSE 4
END, priority DESC
LIMIT ?
```

> `LOWER(name) = ?` — точное совпадение с игнорированием регистра (например `bpy.types.Scene` находится первым при поиске `bpy.types.scene`).

## Индексация

1. **objects.inv** — zlib → разбор строк → `symbols`
2. **HTML** — BeautifulSoup → параметры/описания → `content`
3. **FTS5** — автозаполнение `content_fts` для полнотекстового поиска
4. **file_hashes** — MD5 для инкрементальной индексации

**Инкрементальный режим**: проверяет MD5 файлов → обновляет только изменившиеся (~0.1 сек).

## Кэш поиска

Ключ: `query|version|limit`. При пропуске — автозаполнение. Статистика через `get_cache_stats()`.

## Производительность

- SQLite WAL — параллельное чтение/запись
- Batch inserts (500 элементов) — `insert_content`, `insert_symbols`
- INSERT OR REPLACE — идеален для переиндексации
- Индексы покрывают 95% запросов

## Батники — портативность

Каждый `.bat`-файл определяет глобальную переменную `VENV_PYTHON`:

```batch
set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"
set "VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe"
```

Все вызовы питона идут **только** через `"%VENV_PYTHON%"`:
- `"%VENV_PYTHON%" -m pip install ...`
- `"%VENV_PYTHON%" _mcp_server\server.py`
- `"%VENV_PYTHON%" _mcp_server\indexer.py`

Никогда не используется системный `python` или `pip` напрямую.

## Кэш поиска — автоочистка

Параметры в `database.py`:
- `CACHE_TTL_SECONDS = 600` (10 минут)
- `CACHE_MAX_ENTRIES = 500` (максимум записей)

При каждом сохранении кэша вызывается `_cleanup_cache()` — удаляет просроченные записи и лишние. Ручная очистка: `POST /api/cache/clear`.

## Конфиг

```python
ROOT      = Path(__file__).resolve().parent.parent
DB_PATH   = ROOT / "BD_BASE" / "blender_api.db"
API_DOC_DIR = ROOT / "API_DOC"
HTTP_HOST = "127.0.0.1"
HTTP_PORT = 18723
```

Все пути портативные — вычисляются от расположения проекта. Фолбэков нет — структура фиксирована.

## Новые версии Blender

1. Создать папку `API_DOC/X_Y/` с `objects.inv` + `*.html`
2. Запустить: `BD_BASE\start_indexer.bat`

## HTTP API

Все эндпоинты: [http://127.0.0.1:18723/docs](http://127.0.0.1:18723/docs)

Ключевые: `/api/search`, `/api/symbol`, `/api/operators`, `/api/types`, `/api/diff`

## Контекст проекта

Подробная структура и что попадает в git — см. [CONTEXT.md](../CONTEXT.md).
