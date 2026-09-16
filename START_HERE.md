# Руководство пользователя

## Быстрый старт (3 команды)

```cmd
BD_BASE\init.bat          ← настройка (1 раз)
BD_BASE\start_indexer.bat ← индексация (~10 мин)
start_mcp_server.bat      ← запуск HTTP сервера
```

Проще всего: **просто `start_mcp_server.bat`** — он сам создаст .venv, сам проиндексирует если нужно, сам запустит сервер.

## Все .bat-скрипты

| Скрипт | Когда | Что делает | Время |
|--------|-------|------------|-------|
| `start_mcp_server.bat` | Каждый раз | Запуск HTTP сервера (авто-.venv → авто-БД → авто-сервер) | ~1 сек |
| `BD_BASE\init.bat` | Один раз | Создаёт venv, ставит зависимости | ~15 сек |
| `BD_BASE\start_indexer.bat` | При обновлении HTML | Инкрементальная индексация | ~0.1 сек |
| `BD_BASE\start_indexer.bat --force` | Принудительно | Полная переиндексация всех файлов | ~10 мин |
| `BD_BASE\check_db.bat` | При подозрении | Сводка по версиям, MD5, даты | ~1 сек |
| `BD_BASE\force_reindex.bat` | БД сломалась | Удаляет БД и пересоздаёт | ~10 мин |

## Типичные сценарии

### Первый запуск
```cmd
BD_BASE\init.bat
BD_BASE\start_indexer.bat
start_mcp_server.bat
```

### Ежедневная работа
```cmd
start_mcp_server.bat      ← сервер готов за 1 сек
```

### Обновлённые доки Blender
```cmd
# Заменить HTML в API_DOC/
BD_BASE\check_db.bat      ← проверить расхождения
BD_BASE\start_indexer.bat ← пересоздать БД
start_mcp_server.bat      ← обновлённый сервер
```

### БД сломалась
```cmd
BD_BASE\force_reindex.bat
```

### Перенос на другую машину
```cmd
# Скопировать весь проект
start_mcp_server.bat      ← всё сделает сам
```

## Как скачать документацию Blender

Откройте https://docs.blender.org/api/current/index.html — там выбор всех версий.

1. Выберите нужную версию (3_6, 4_5, 5_1, ...)
2. Скачайте архив HTML-доков (ссылка на странице версии)
3. Распакуйте → найдите `docs/python_api`
4. Скопируйте содержимое в `API_DOC/X_Y/` (создайте папку, где X_Y — версия: `3_6`, `4_5`, `5_1`)
5. Запустите: `BD_BASE\start_indexer.bat`

## Подключение в Zed Editor

1. Убедитесь, что проект настроен: `BD_BASE\init.bat`
2. Откройте Zed → Settings (Command Palette → "Preferences: Open Settings (JSON)")
3. Добавьте в `context_servers`:

```json
"context_servers": {
    "blender-api-docs": {
        "enabled": true,
        "command": ".venv/Scripts/python.exe",
        "args": [
            "_mcp_server/server.py"
        ],
        "env": {
            "PYTHONPATH": "_mcp_server"
        }
    }
}
```

> **Важно:** Используйте относительные пути (`_mcp_server/`, `.venv/`), а не абсолютные. Они работают на любой машине после клонирования репозитория.

4. Перезапустите Zed
5. Проверьте: в чате напишите `blender-api-docs: search for bpy.ops.mesh`

## Подключение в Cursor / Windsurf / другие MCP-клиенты

Аналогично — укажите путь к `_mcp_server/server.py` и установите `PYTHONPATH=_mcp_server`.

### MCP через HTTP (альтернатива)

Если MCP-клиент не поддерживает stdio-серверы:

1. Запустите: `start_mcp_server.bat` (запустит HTTP сервер)
2. Или используйте MCP Proxy для конвертации HTTP → stdio:
   - https://github.com/wong2/mcp-proxy

## Как добавить новые доки Blender

1. Откройте https://docs.blender.org/api/current/index.html
2. Выберите новую версию, скачайте архив доков
3. Распакуйте → скопируйте `docs/python_api` в `API_DOC/X_Y/`
4. Запустите: `BD_BASE\start_indexer.bat`

## Ручной запуск (без .bat)

```cmd
call .venv\Scripts\activate.bat
python _mcp_server\indexer.py
python _mcp_server\api_server.py
```

## Портативность

- Все пути относительные, вычисляются от `config.py`
- `.venv/` — свой Python, свои пакеты
- Скопируй проект → запусти `start_mcp_server.bat` → готово
- Не требует установки Python в систему
- `.venv/`, `__pycache__/`, `*.db-wal`, `*.db-shm` — игнорируются git

## Что умеет сервер

**HTTP REST API** (10 эндпоинтов):
- `GET /api/search?q=...` — поиск по имени/модулю
- `GET /api/symbol?name=...` — параметры, описания, дефолты
- `GET /api/module?module=...` — все символы в модуле
- `GET /api/page?uri=...` — контент HTML-страницы
- `GET /api/operators?q=...` — только `bpy.ops.*`
- `GET /api/types?q=...` — только `bpy.types.*`
- `GET /api/properties?q=...` — только `bpy.props.*`
- `GET /api/diff?symbol=...&v1=...&v2=...` — сравнить символ между версиями
- `GET /api/versions` — метаданные БД
- `GET /api/stats` — статистика
- `GET /api/cache-stats` — статистика кэша
- `POST /api/cache/clear` — очистить кэш (TTL 10 мин, LIMIT 500)

Для HTTP-API: [http://127.0.0.1:18723/docs](http://127.0.0.1:18723/docs) — Swagger UI

Чтобы запустить на другом порту: `start_mcp_server.bat 8080`

*Версия: 0.3.3 | Обновлено: 2026-09-16*
