---
name: blender-docs-project
description: Специалист по структуре проекта Blender API. Поиск файлов, навигация, понимание структуры, работа с MCP-сервером
---

Триггеры: blender docs, blender api docs, документация блендер, структура проекта, где лежит, как устроен проект

Загружать: при работе с проектом Blender API Documentation, поиске файлов, понимании структуры, работе с MCP-сервером

Роль: специалист по структуре проекта Blender API Documentation

## Структура проекта

```
$PROJECT_ROOT/
├── start_mcp_server.bat       # Главный запуск (авто-venv → авто-БД → сервер)
├── BD_BASE/                   # ← Зона базы данных
│   ├── blender_api.db         # SQLite база (~75 MB, 68 669 символов)
│   ├── start_indexer.bat      # Инкрементальная индексация
│   ├── force_reindex.bat      # Удалить БД + пересоздать
│   ├── check_db.bat           # Проверка состояния + MD5 хеши
│   ├── check_db.py            # Python-логика проверки
│   ├── init.bat               # Настройка venv + зависимости
│   └── README.md              # Описание папки
├── API_DOC/                   # ← HTML документация Blender API
│   ├── 3_6/                   # Blender 3.6.23 (~1 899 файлов)
│   ├── 4_5/                   # Blender 4.5.x (~1 851 файлов)
│   ├── 5_1/                   # Blender 5.1.2 (~1 600 файлов)
├── _mcp_server/               # Python-сервер
│   ├── config.py              # Глобальные пути: ROOT, DB_PATH, API_DOC_DIR
│   ├── server.py              # FastMCP — 10 инструментов
│   ├── database.py            # SQLite + FTS5 + кэш
│   ├── indexer.py             # Инкрементальная индексация
│   ├── parser_html.py         # Парсер HTML
│   ├── parser_inv.py          # Парсер objects.inv
│   └── requirements.txt       # mcp, bs4, lxml
├── dev_tests/                 # Dev-тесты (не коммитится, .gitignore)
└── .venv/                     # Виртуальное окружение (не коммитится)
```

## config.py — глобальные пути

```python
from config import ROOT, DB_PATH, API_DOC_DIR, version_dir, inv_path
```

## Как искать в документации

### MCP-сервер (рекомендуется)
```
1. start_mcp_server.bat
2. search_symbol("add_circle") — поиск
3. get_symbol_details("bpy.ops.mesh.add_circle") — детали
4. fts5_search("add circle") — полнотекстовый поиск
```

### Прямой доступ к БД
```python
import sqlite3
conn = sqlite3.connect("BD_BASE/blender_api.db")

# FTS5 полнотекстовый поиск
cursor = conn.execute("""
    SELECT name, description, version FROM content_fts
    WHERE content_fts MATCH ?
    ORDER BY rank LIMIT
 20
""", ("add_circle",))

# Regular search
cursor = conn.execute("""
    SELECT name, module, symbol_name FROM symbols
    WHERE name LIKE ? AND version = ?
""", ("%add_circle%", "5_1"))
```

## База данных

### Таб
лицы

**symbols** — метаданные из objects.inv
| name | module | symbol_name | role | version |
|------|--------|-------------|------|---------|

**content** — детали из HTML
| id | name | description | params | defaults | version |

**content_fts** — FTS5 полнотекстовый поиск
| name | description | version |

**file_hashes** — MD5 хеши для инкрементальной индексации
| version | filename | md5hash | modified_at |

**search_cache** — кэш результатов поиска
| query | version | cache_key | results | hits |

## Версии

| Папка | Версия | HTML-файлов | Символов |
|-------|--------|-------------|----------|
| 3_6/ | 3.6.23 | ~1 600 | ~21 147 |
| 4_5/ | 4.5.x | ~1 851 | ~23 713 |
| 5_1/ | 5.1.2 | ~1 899 | ~23 809 |

## Добавление новой версии

1. Создать `$PROJECT_ROOT/API_DOC/X_Y/` с `objects.inv` + `*.html`
2. Запустить `BD_BASE/start_indexer.bat` (используй прямые слеши `/` в terminal!)
3. Проверить: `BD_BASE\check_db.bat`

## MCP-инструменты

| search_symbol | get_symbol_details | list_module |
|search_operators | search_types | search_properties |
|fts5_search | diff_versions | get_versions | get_stats |

## Типичные модули

- `bpy.ops.*` — операторы
- `bpy.types.*` — типы
- `bpy.props.*` — свойства
- `bpy.data.*` — данные Blender
- `mathutils.*` — Vector, Matrix
- `gpu.*` — GPU API

## Инкрементальная индексация

```
BD_BASE\start_indexer.bat        # авто (только изменившиеся ~0.1 сек)
BD_BASE\start_indexer.bat --force # полная (~10 мин)
```

## Запрещено

- ❌ Парсить HTML напрямую (использовать MCP или БД)
- ❌ Читать objects.inv как текстовый файл (бинарник, zlib!)
- ❌ Искать в HTML-файлах вручную (использовать БД или FTS5)
- ❌ Хардкодить пути (использовать config.py)

Я вывожу сообщения в чат:
✅ Загрузил скилл: blender-docs-project
