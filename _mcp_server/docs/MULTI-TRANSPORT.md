# 🔄 Мульти-транспортный сервер

Сервер Blender API Documentation поддерживает **два режима работы**:

1. **stdio** (stdin/stdout) — для MCP-клиентов (Zed, Cursor, Claude Desktop)
2. **HTTP** (REST + SSE) — для WebUI, мобильных приложений, любых HTTP-клиентов

Оба режима используют **одну и ту же бизнес-логику** (`business_logic.py`).

---

## 📌 Зачем два режима?

| Режим | Для чего | Примеры |
|-------|----------|---------|
| **stdio** | AI-клиенты, IDE | Zed, Cursor, Claude Desktop, Claude Code |
| **HTTP** | Веб-интерфейсы, API, сторонние сервисы | WebUI, React-приложение, мобильное приложение |

---

## 🖥️ Режим 1: stdio (для Zed/Cursor)

### Как это работает

Сервер запускается как **локальный процесс**. Zed сам его стартует и общается через **stdin/stdout pipes**.

**Никаких IP, портов, HTTP — процесс живёт внутри Zed.**

```
┌──────────────┐
│  Zed Editor  │
├──────────────┤
│  MCP Client  │
│  (stdin)     │◄────┐
│  (stdout)    │◄────┘ pipes (JSON-RPC)
└──────────────┘
       │
       ▼
┌──────────────┐
│ python       │
│ server.py    │  ← FastMCP процесс
│  (stdio mode)│
└──────────────┘
       │
       ▼
┌──────────────┐
│ SQLite DB    │
│ blender.db   │
└──────────────┘
```

### Настройка в Zed

1. Открой Zed
2. Открой Settings (File → Settings или `Cmd+,` / `Ctrl+,`)
3. Перейди в вкладку **Extensions** → найди **MCP**
4. Или редактируй `settings.json` напрямую

**Путь к settings.json в Zed:**
- **Windows:** `%APPDATA%\Zed\settings.json` (C:\Users\ТвоёИмя\AppData\Roaming\Zed\settings.json)

### Файл settings.json

Добавь этот JSON **внутрь** объекта настроек (не в корень!):

```json
{
  "mcp": {
    "servers": {
      "blender-api-docs": {
        "command": "C:\\_blender__DATA\\blender_python\\venv\\Scripts\\python.exe",
        "args": [
          "C:\\_blender__DATA\\blender_python\\_mcp_server\\server.py"
        ],
        "env": {
          "PYTHONPATH": "C:\\_blender__DATA\\blender_python\\_mcp_server"
        }
      }
    }
  }
}
```

> ⚠️ **Важно:** замени пути на свои! Используй двойные бэкслэши `\\` в JSON.

### Или через Zed UI (проще)

1. File → Settings → Extensions → MCP Servers
2. Нажми **Add MCP Server**
3. Заполни:
   - **Name:** `blender-api-docs`
   - **Command:** `C:\_blender__DATA\blender_python\venv\Scripts\python.exe`
   - **Args:** `C:\_blender__DATA\blender_python\_mcp_server\server.py`
   - **Env:** `PYTHONPATH` = `C:\_blender__DATA\blender_python\_mcp_server`

### Портативный вариант (относительные пути)

Если хочешь копировать проект на другую машину — **не используй абсолютные пути!**

В Zed нет поддержки относительных путей в MCP-конфиге (пока что), поэтому:

1. **Для себя** — абсолютные пути (удобнее)
2. **Для распространения** — скрипт, который генерирует `zed-mcp-config.json` с правильными путями

### Проверка подключения

После добавления сервера:
1. Перезапусти Zed (или `Cmd+Shift+P` → "Zed: Restart Language Server")
2. В чате (Cmd+L / Ctrl+L) напиши: "какие версии Blender API доступны?"
3. Зед должен вызвать `get_versions` → увидишь: `["3_6", "4_5", "5_1"]`

### Примеры запросов в чате Zed

```
Найди оператор создания круга в bpy.ops
```
→ Zed вызовет `search_operators("add circle", "latest", 20)`

```
Детали bpy.ops.mesh.add_circle
```
→ Zed вызовет `get_symbol_details("bpy.ops.mesh.add_circle", "latest")`

```
Сравни bpy.types.Scene в версиях 5_1 и 4_5
```
→ Zed вызовет `diff_versions("bpy.types.Scene", "5_1", "4_5")`

### Возможные проблемы

| Проблема | Решение |
|----------|---------|
| Сервер не запустился | Проверь путь к `python.exe` — открой терминал и набери `venv\Scripts\python.exe --version` |
| Ошибка "transport closed" | Сервер упал. Проверь консоль Zed (View → Activity Bar → MCP) |
| "No tools found" | `PYTHONPATH` не установлен. Задуй вручную |
| Сервер работает, но ничего не отвечает | Завис. Перезапусти Zed |

---

## 🌐 Режим 2: HTTP (для WebUI)

### Как это работает

Сервер запускается как **отдельный HTTP-сервер** на порту (по умолчанию 18723).

```
┌──────────────┐
│  WebUI       │  ← React, Vue, любой фронтенд
│  (browser)   │
└──────┬───────┘
       │ HTTP REST API
       │ (json)
       ▼
┌──────────────────────┐
│  FastAPI + uvicorn   │  ← HTTP сервер :18723
│  api_server.py       │  ← бизнес-логика
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  SQLite DB           │
│  blender_api.db      │
└──────────────────────┘
```

### Запуск

```bash
# Через venv
venv\Scripts\python.exe _mcp_server\api_server.py

# С кастомным портом
venv\Scripts\python.exe _mcp_server\api_server.py --port 3000

# Для сети (чтобы с другой машины подключиться)
venv\Scripts\python.exe _mcp_server\api_server.py --host 0.0.0.0 --port 18723
```

### API Endpoints

Все эндпоинты отдают **JSON**. CORS включён (можно с любого origin).

#### Health Check

```
GET http://127.0.0.1:18723/api/health
```

Ответ:
```json
{
  "status": "ok",
  "transport": "http"
}
```

#### Поиск

```
GET http://127.0.0.1:18723/api/search?q=add_circle&version=latest&limit=10
```

Ответ: массив результатов поиска.

#### Детали символа

```
GET http://127.0.0.1:18723/api/symbol?name=bpy.ops.mesh.add_circle&version=latest
```

Ответ:
```json
{
  "id": "bpy.ops.mesh.add_circle",
  "name": "add_circle",
  "description": "Add a circle mesh.",
  "params": [
    {"name": "radius", "type": "float", "description": "Radius of the circle"},
    {"name": "fill_type", "type": "enum", "description": "Fill type"}
  ],
  "defaults": {"radius": "1.0", "fill_type": "vertices"},
  "has_params": true,
  "version": "5_1"
}
```

#### По модулю

```
GET http://127.0.0.1:18723/api/module?module=bpy.ops.mesh&version=latest&limit=50
```

#### Версии

```
GET http://127.0.0.1:18723/api/versions
```

Ответ: `["3_6", "4_5", "5_1"]`

#### Статистика

```
GET http://127.0.0.1:18723/api/stats
```

Ответ:
```json
{
  "total_symbols": 68669,
  "total_content": 65567,
  "by_version": {"3_6": 21147, "4_5": 23713, "5_1": 23809},
  "by_role": {"func": 45000, "class": 15000, "attr": 8669}
}
```

#### Категория: операторы

```
GET http://127.0.0.1:18723/api/operators?q=subdivide&version=latest&limit=20
```

#### Категория: типы

```
GET http://127.0.0.1:18723/api/types?q=Scene&version=latest&limit=20
```

#### Категория: свойства

```
GET http://127.0.0.1:18723/api/properties?q=StringProperty&version=latest&limit=20
```

#### Сравнение версий

```
GET http://127.0.0.1:18723/api/diff?symbol=bpy.types.Scene&v1=5_1&v2=4_5
```

### Swagger / OpenAPI документация

FastAPI автоматически генерирует интерактивную документацию:

```
http://127.0.0.1:18723/docs       ← Swagger UI
http://127.0.0.1:18723/redoc      ← ReDoc
http://127.0.0.1:18723/openapi.json ← OpenAPI JSON schema
```

### curl-примеры

```bash
# Поиск
curl "http://127.0.0.1:18723/api/search?q=add_circle&version=latest&limit=5"

# Детали символа
curl "http://127.0.0.1:18723/api/symbol?name=bpy.ops.mesh.add_circle&version=latest"

# Версии
curl "http://127.0.0.1:18723/api/versions"

# Статистика
curl "http://127.0.0.1:18723/api/stats"

# Очистка кэша
curl -X POST "http://127.0.0.1:18723/api/cache/clear"
```

---

## 🔀 Сравнение режимов

| Фича | stdio (MCP) | HTTP (REST) |
|------|-------------|-------------|
| **Протокол** | stdin/stdout (pipes) | TCP/IP (HTTP/1.1) |
| **IP/Порт** | Не нужен | 127.0.0.1:18723 |
| **Для кого** | Zed, Cursor, Claude | WebUI, curl, мобильные |
| **Сложность** | Проще (нет сети) | Чуть сложнее (порт, CORS) |
| **Удалённый доступ** | Нет (только локально) | Да (0.0.0.0) |
| **CORS** | Не нужно | Включён |
| **Dokumentaciya** | Нет | Swagger (/docs) |
| **SSE/WebSocket** | Нет | Да (/api/events) |

---

## 🧪 Как проверить подключение

### Проверка stdio (MCP)

1. Запусти `start_mcp_server.bat` — он запустит server.py в stdio-режиме
2. Если сервер стартовал и пишет `Server ready. Press Ctrl+C to stop.` — всё ок
3. Подключи через Zed → проверь запросом: `get_versions`
4. Должен получить: `["3_6", "4_5", "5_1"]`

### Проверка HTTP

1. Запусти `api_server.py`:
   ```bash
   venv\Scripts\python.exe _mcp_server\api_server.py
   ```
2. Открой браузер: `http://127.0.0.1:18723/api/health`
3. Увидишь: `{"status":"ok","transport":"http"}`
4. Проверь поиск: `http://127.0.0.1:18723/api/search?q=Scene&version=latest&limit=3`
5. Посмотри Swagger: `http://127.0.0.1:18723/docs`

---

## 📁 Структура после рефакторинга

```
_mcp_server/
├── config.py           ← пути (ROOT, DB_PATH, API_DOC_DIR)
├── database.py         ← SQLite слой
├── parser_html.py      ← парсер HTML
├── parser_inv.py       ← парсер objects.inv
├── indexer.py          ← оркестратор индексации
├── business_logic.py   ← общий слой (ОБЪЕДИНЯЕТ оба транспорта)
├── server.py           ← MCP (stdio) — FastMCP
├── api_server.py       ← HTTP (REST/SSE) — FastAPI
└── requirements.txt    ← зависимости (mcp, fastapi, uvicorn, sse-starlette)
```

**Ключевое изменение:** `business_logic.py` содержит ВСЮ бизнес-логику. Ни `server.py`, ни `api_server.py` не повторяют код — оба импортируют из `business_logic.py`.

---

*Последнее обновление: 2026-09-16 | Версия проекта: 0.3.3*
