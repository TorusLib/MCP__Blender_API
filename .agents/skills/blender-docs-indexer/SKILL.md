---
name: blender-docs-indexer
description: Специалист по индексации HTML-документации Blender API. Запускает индексатор, добавляет версии, переиндексировывает, отлаживает парсинг
---

Триггеры: indexer, индексация, добавить версию, reindex, переиндексация, парсить документацию, запустить indexer, индексатор

Загружать: при запуске индексации, добавлении новой версии Blender, переиндексации, отладке парсинга

Роль: специалист по индексации HTML-документации Blender API

## Запуск индексатора

### Основной способ (инкрементальный)
```
BD_BASE\start_indexer.bat
```
При повторном запуске проверяет MD5 хеши HTML-файлов и обновляет только изменившиеся (~0.1 сек вместо ~10 мин).

### Ручной способ
```cmd
.venv/Scripts/python.exe _mcp_server/indexer.py
```

### Индексация конкретной версии
```cmd
set PYTHONPATH=%cd%\_mcp_server;%PYTHONPATH%
.venv/Scripts/python.exe _mcp_server/indexer.py 3_6
```

### Принудительная полная переиндексация
```
BD_BASE\start_indexer.bat --force
```

## Что делает indexer

1. **Находит все версии** — сканирует `API_DOC/` в поисках `objects.inv`
2. **Парсит objects.inv** — извлекает метаданные через `parser_inv.py`
3. **Вставляет в БД** — bulk INSERT в таблицу `symbols`
4. **Парсит HTML** — для каждого URI парсит HTML через `parser_html.py`
5. **Вставляет контент** — bulk INSERT в таблицу `content`
6. **Заполняет FTS5** — полнотекстовый поиск
7. **Сохраняет хеши** — MD5 файлов для инкрементальной индексации

## Добавление новой версии

1. Скопировать HTML-документацию в `$PROJECT_ROOT/API_DOC/X_Y/`
2. В папке должны быть `objects.inv` + `*.html` файлы
3. Запустить `BD_BASE\start_indexer.bat` — автоматически определит новую папку
4. Проверить: `BD_BASE\check_db.bat` — должно показать `[OK]`

## Отладка

### Проблемы с objects.inv
- Проверить: `ls API_DOC/3_6/objects.inv` (должен быть бинарник)
- Проверить zlib: `python -c "import zlib; print(zlib.decompress(open('API_DOC/3_6/objects.inv', 'rb').read()[-100:]))"`

### Проблемы с HTML
- Проверить: `ls API_DOC/3_6/bpy.ops.mesh.html` (должен существовать)
- Кодировка: HTML должен быть UTF-8

### Проблемы с БД
- Проверить: `BD_BASE/check_db.bat`
- Символы: `python -c "import sqlite3; c=sqlite3.connect('BD_BASE/blender_api.db'); print(c.execute('SELECT count(*) FROM symbols').fetchone())"`

## Производительность

| Версия | HTML-файлов | Символов | Полная | Инкрементальная |
|--------|-------------|----------|--------|-----------------|
| 3_6 | ~1 600 | ~20 332 | ~35 сек | ~0.1 сек |
| 4_5 | ~1 851 | ~22 779 | ~5 мин | ~0.1 сек |
| 5_1 | ~1 899 | ~22 992 | ~5 мин | ~0.1 сек |

## Запрещено

- ❌ Модифицировать objects.inv (бинарник, zlib!)
- ❌ Удалять HTML-файлы после индексации
- ❌ Запускать indexer.py без проверки objects.inv

Я вывожу сообщения в чат:
✅ Загрузил скилл: blender-docs-indexer
