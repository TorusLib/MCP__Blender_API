---
name: blender-docs-mcp
description: Специалист по MCP-серверу Blender API. Запускает сервер, вызывает инструменты, отлаживает MCP-клиентов
---

Триггеры: mcp server, mcp сервер, blender mcp, запустить mcp, mcp tool, mcp инструменты, fastmcp, mcp client, mcp-сервер

Загружать: при работе с MCP-сервером Blender API, запуске сервера, вызове инструментов MCP, отладке MCP-клиентов

Роль: специалист по MCP-серверу Blender API Documentation

## Запуск MCP-сервера

```
start_mcp_server.bat
```

Сервер работает в HTTP-режиме на порту 18723. Автономен — сам проверит .venv, БД, запустит сервер.

## Инструменты MCP

### Основной поиск

**search_symbol(query, version, limit)**
```
search_symbol("add_circle")                    # все версии
search_symbol("add_circle", "5_1")             # конкретная версия
search_symbol("bpy.ops.mesh", "5_1", 50)       # в модуле
```
Возвращает: `list[dict]` с полями name, module, symbol_name, role, display_name, version

**get_symbol_details(name, version)**
```
get_symbol_details("bpy.ops.mesh.add_circle")
get_symbol_details("bpy.ops.mesh.add_circle", "all")  # все версии
```
Возвращает: `dict` с полями description, params, defaults, has_params

### Категоризированный поиск

**search_operators(search, version, limit)**
```
search_operators("subdivide")
```
Фильтрует только `bpy.ops.*`

**search_types(search, version, limit)**
```
search_types("Mesh")
```
Фильтрует только `bpy.types.*`

**search_properties(search, version, limit)**
```
search_properties("StringProperty")
```
Фильтрует только `bpy.props.*`

### Browse и метаданные

**list_module(module, version, limit)**
```
list_module("bpy.ops.mesh")
```

**get_versions()**
```
get_versions()  # ["3_6", "4_5", "5_1"]
```

**get_stats()**
```
get_stats()  # {total_symbols, total_content, by_version, by_role}
```

### FTS5 полнотекстовый поиск

**fts5_search(query, version, limit)**
```
fts5_search("add circle", "5_1", 20)  # находит add_circle, primitive_bezier_circle_add
```
Поиск по name + description с ранжированием по релевантности.

### Сравнение версий

**diff_versions(symbol_name, v1, v2)**
```
diff_versions("bpy.ops.mesh.add_circle", "5_1", "4_5")
```

## Версии

- `"latest"` — последняя из `get_versions()[-1]`
- `"all"` — поиск по всем версиям
- Конкретная: `"3_6"`, `"4_5"`, `"5_1"`

## Кэширование

Поиск автоматически кэшируется. Повторные запросы ~0мс вместо ~50мс.

```python
#
 Статистика кэша
import sys; sys.path.insert(0, '_mcp_server')
import database as db
db.get_cache_stats()  # {total_entries, total_hits, top_queries}
db.clear_search_cache()
```

## Типичные сценарии

### Найти оператор и посмотреть параметры
```
1. search_symbol("subdivide", limit=5)
2. get_symbol_details("bpy.ops.mesh.subdivide", "5_1")
```

### Сравнить тип между версиями
```
1. get_symbol_details("bpy.types.Scene", "all")
2. diff_versions("bpy.types.Scene", "5_1", "4_5")
```

## Запрещено

- ❌ Парсить HTML напрямую вместо MCP
- ❌ Читать БД напрямую (если есть MCP)
- ❌ Игнорировать version (всегда указывать явно или использовать "latest")
- ❌ Запускать сервер без init.bat (сначала настроить окружение)

Я вывожу сообщения в чат:
✅ Загрузил скилл: blender-docs-mcp
