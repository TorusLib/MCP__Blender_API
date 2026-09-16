# Документация HTML-парсера (parser_html.py + parser_inv.py)

> Полное руководство по парсеру Blender API HTML-документации. Sphinx 3.x (ReadTheDocs) + 4.x+ (PyData).

---

## Архитектура парсера

```
indexer.py: index_version()
    │
    ├── parser_inv.py: get_all_symbols(version)
    │   ├── parse_inv_file(Path)          ← парсит binary objects.inv
    │   │   ├── читаем header (строки #)
    │   │   ├── zlib.decompress()         ← сжимаем остаток
    │   │   └── парсим строки: name domain:role priority uri [desc]
    │   └── возвращает list[dict]         ← symbols из inventory
    │
    └── parser_html.py: parse_all_html(version, symbol_list)
        ├── parse_html_file(html_path)    ← Основные символы (dt.sig-object)
        │   ├── _find_content_area()      ← article/main/div.document/div.rst-content
        │   ├── find_all("dt.sig-object") ← все символы на странице
        │   ├── _parse_params(dd)         ← параметры (авто-определение Sphinx)
        │   │   ├── _parse_new_sphinx_params()  ← dt/dd в field-list
        │   │   └── _parse_old_sphinx_params()  ← ul.simple / p>strong
        │   ├── _extract_enum_values()    ← enum-значения из вложенных ul
        │   └── _parse_signature_defaults() ← regex defaults из сигнатуры
        │
        └── _parse_enum_items_html(enum_dir) ← bpy_types_enum_items/*.html
            └── dt.field-odd/field-even (НЕ sig-object!)
```

**Вход:** `version` (3_6/4_5/5_1) + `symbol_list` из `objects.inv`
**Выход:** `(content_dict, enum_symbols_list)` — словарь `{id: data}` + список enum-символов

---

## 1. Parser Inv — objects.inv (parser_inv.py)

### 1.1 Что такое objects.inv

Инвентарный файл Sphinx, содержащий метаданные ВСЕХ символов API. Бинарный формат:
- **Header:** строки, начинающиеся с `#`
- **Payload:** zlib-сжатые строки с данными символов

### 1.2 Формат строки

```
name domain:role priority uri [description]

Примеры:
  bpy.ops.mesh.add_circle  py:func  -1  bpy.ops.mesh.html  add_circle
  bpy.types.Scene          py:class  1  bpy.types.Scene.html#$  -
```

### 1.3 Разбор строки

```python
parts = line.split(None, 4)
# parts[0] = name              → "bpy.ops.mesh.add_circle"
# parts[1] = domain:role       → "py:func" → domain="py", role="func"
# parts[2] = priority          → "-1" (int)
# parts[3] = uri               → "bpy.ops.mesh.html" (fragment #...#$ stripped)
# parts[4] = description       → "add_circle" (опционально)
```

### 1.4 Вычисляемые поля (SymbolEntry)

| Поле | Формула | Пример |
|------|---------|--------|
| `module` | `".".join(parts[:-1])` | `"bpy.ops.mesh"` |
| `symbol_name` | `name.rsplit(".", 1)[-1]` | `"add_circle"` |
| `is_method` | `role in (func, method) and domain == py` | `True` |

### 1.5 URI → файл

URI = filename.html (без префикса `API_DOC/3_6/`).
Для поиска HTML-файла: `base_path / uri` → `API_DOC/3_6/bpy.ops.mesh.html`

---

## 2. Parser HTML — основной парсер (parser_html.py)

### 2.1 Контент-область (_find_content_area)

Sphinx 3.x (ReadTheDocs) и 4.x+ (PyData) используют разные контейнеры.

| Sphinx | Селектор | Класс |
|--------|----------|-------|
| 4.x+ | `<article>` | `role="main"` |
| 4.x+ | `<main>` | — |
| 3.x | `<div>` | `class="document"` |
| 3.x | `<div>` | `class="rst-content"` |

**Приоритет:** `article[role=main]` → `main` → `div.document` → `div.rst-content` → `soup`

### 2.2 Основные символы (parse_html_file)

Каждый символ в HTML — это пара `dt` + `dd`.

#### 2.2.1 dt — тег определения символа

| Атрибут | Значение | Пример |
|---------|----------|--------|
| `class` | `['sig', 'sig-object', 'py']` | Всегда эти 3 класса |
| `id` | Полное имя символа | `bpy.ops.mesh.bevel` |
| `span.sig-name` | Короткое имя | `bevel` |

**Селектор:** `dt` с `class_=re.compile(r"sig-object")`

#### 2.2.2 dd — тег описания

Первый `<p>` внутри `<dd>` — **описание** символа.
Дальше — параметры и типы.

#### 2.2.3 Алгоритм извлечения данных

```python
# 1. ID символа (обязательный, пропуск если пустой)
symbol_id = dt.get("id", "")
if not symbol_id:
    continue

# 2. Полное имя (для БД)
name = symbol_id

# 3. Короткое имя (для отображения)
short_name = dt.find("span", class_="sig-name").get_text(strip=True)

# 4. Описание (первый <p> в <dd>)
dd = dt.find_next_sibling("dd")
first_p = dd.find("p")
description = first_p.get_text(strip=True) if first_p else ""

# 5. Дефолты (из сигнатуры в dt)
sig_text = dt.get_text()
defaults = _parse_signature_defaults(sig_text)

# 6. Параметры
params, has_params = _parse_params(dd)
```

#### 2.2.4 Regex для defaults

```python
# Паттерн: name = value
# value = число, строка, кортеж, булево
# Останавливается на , ) ]
re.findall(r"(\w+)\s*=\s*([^,\)\]\)]+?)(?=\s*[,\)])", sig_text)
```

**Пример:** `bpy.ops.mesh.bevel(offset_type='OFFSET', offset=0.0)`
**Результат:** `{offset_type: "'OFFSET'", offset: "0.0"}`

---

## 3. Параметры — 3 ФОРМАТА + 2 темы Sphinx

Параметры всегда внутри `dl.field-list`, но структура разная в зависимости от темы Sphinx.

### 3.1 Формат A: `<ul><li>` (основной, старая Sphinx)

**Где:** `bpy.ops.*.html`, `bpy.props.html`, `bmesh.*.html`

```html
<dl class="field-list simple">
  <dt class="field-odd">Parameters</dt>
  <dd class="field-odd">
    <ul class="simple">
      <li>
        <p>
          <strong>offset_type</strong>
          (<em>enum in</em>...) – Width Type, The method...
        </p>
        <ul>
          <li><p><code>OFFSET</code> Offset – Amount...</p></li>
        </ul>
      </li>
    </ul>
  </dd>
</dl>
```

**Парсинг (_parse_old_sphinx_params):**
1. `dd.find("dl", class_=re.compile(r"field-list"))`
2. `field_list.find("ul", class_="simple")`
3. `ul.find_all("li")` → каждый li = один параметр
4. `li.find("p")` → `p.find("strong")` = имя параметра
5. Текст после `–` = описание
6. Текст в скобках `(...)` = тип

**Regex для типа:**
```python
# "offset_type(enum in['OFFSET'],(optional))" → "enum in['OFFSET']"
clean = re.sub(r",?\s*\(optional\)\s*", "", type_part)
first_open = clean.find("(")
last_close = clean.rfind(")")
param_type = clean[first_open+1:last_close]
```

### 3.2 Формат B: `<p><strong>` прямо в `<dd>` (старая Sphinx)

**Где:** `bpy.ops.console.html`, некоторые `bpy.ops.object.*.html`, `bpy_extras.*.html`

```html
<dd>
  <p>Description text.</p>
  <dl class="field-list simple">
    <dt class="field-odd">Parameters</dt>
    <dd class="field-odd">
      <p><strong>type</strong> (<em>enum in</em>...) – Type, Which part...</p>
    </dd>
  </dl>
</dd>
```

**Парсинг:**
1. `dd.find_all("p")` — пропускаем первый `<p>` (описание функции)
2. Каждый последующий `<p>` с `<strong>` = параметр
3. Пропускаем `<strong>` с текстом "Type", "Parameters", "Returns"

### 3.3 Формат C: только Type (без параметров)

**Где:** `bpy.types.*.html` (атрибуты классов), `mathutils.*.html`

```html
<dd>
  <p>Active Movie Clip that can be used...</p>
  <p>MovieClip</p>
  <dl class="field-list simple">
    <dt class="field-odd">Type</dt>
    <dd class="field-odd">MovieClip</dd>
  </dl>
</dd>
```

**Важно:** field-list есть, но только `<dt>Type</dt>` — НЕ параметр!
**Результат:** `has_params = False`, `params = []`

### 3.4 Новая Sphinx (dt/dd пары) — Формат D

**Где:** Sphinx 4.x+ с темой PyData

```html
<dl class="field-list simple">
  <dt class="field-odd">Parameters</dt>
  <dd class="field-odd">
    <dl class="simple">
      <dt><strong>offset_type</strong></dt>
      <dd><p>enum in['OFFSET'] – Width Type</p></dd>
    </dl>
  </dd>
</dl>
```

**Парсинг (_parse_new_sphinx_params):**
1. `dd.find("dl", class_=re.compile(r"field-list"))`
2. `field_list.find_all("dt")` — каждый dt (кроме заголовков) = параметр
3. `dt.get_text(strip=True)` = имя параметра
4. `dt.find_next_sibling("dd").get_text(strip=True)` = "Type – description"

### 3.5 Как определяется формат (_parse_params)

```python
def _parse_params(dd: Tag) -> tuple[list[dict], bool]:
    # Пробуем новую Sphinx (dt/dd пары в field-list)
    new_params, new_has = _parse_new_sphinx_params(dd)
    if new_has and len(new_params) > 0:
        # Проверим — если есть dt без заголовка Type/Parameters,
        # значит новая тема с реальными параметрами
        field_list = dd.find("dl", class_=re.compile(r"field-list"))
        if field_list:
            dts = field_list.find_all("dt")
            real_params = [
                dt for dt in dts
                if dt.get_text(strip=True)
                not in ("Type", "Parameters", "Returns", "Return type", "Yields")
            ]
            if real_params:
                return new_params, new_has

    # Старая Sphinx (ul.simple)
    return _parse_old_sphinx_params(dd)
```

---

## 4. Enum-значения (встроенные)

Вложены внутри `<li>` в Формате A.

```html
<li>
  <p><strong>offset_type</strong> ...</p>
  <ul>
    <li><p><code>OFFSET</code> Offset – Amount...</p></li>
    <li><p><code>WIDTH</code> Width – Amount...</p></li>
  </ul>
</li>
```

**Парсинг (_extract_enum_values):**
```python
for li in ul_simple.find_all("li"):
    nested_ul = li.find("ul")
    if nested_ul:
        for nested_li in nested_ul.find_all("li"):
            code = nested_li.find("code")
            enum_val = code.get_text(strip=True)
            text = nested_li.find("p").get_text(strip=True)
            # Формат: "EnumName – Description"
            dash_match = re.match(r"^(.+?)\s*[–—]\s*(.*)$", text)
            enums.append({
                "name": f"__enum__{enum_val_clean}",
                "type": "enum value",
                "description": enum_desc,
            })
```

---

## 5. Enum Items (bpy_types_enum_items/)

Отдельная директория с особым форматом — НЕТ `dt.sig-object`.

### 5.1 Структура файла

```html
<dl class="field-list">
  <dt class="field-odd">VERT</dt>
  <dd class="field-odd">Vertex selection mode.</dd>
  <dt class="field-even">EDGE</dt>
  <dd class="field-even">Edge selection mode.</dd>
</dl>
```

### 5.2 Генерация имени символа

Файл: `mesh_select_mode_items.html`

```python
stem = "mesh_select_mode_items"       # f.stem
parts = stem.split("_")               # ["mesh", "select", "mode", "items"]
class_name = "".join(p.capitalize() for p in parts)
# "MeshSelectModeItems"
if class_name.endswith("Items"):
    class_name = class_name[:-5]
# "MeshSelectMode"

symbol_id = f"bpy.types.enum_items.{class_name}.{value.upper()}"
# "bpy.types.enum_items.MeshSelectMode.VERT"
```

### 5.3 Важно

- Селектор: `dt` с `class_=re.compile(r"field-")` (НЕ `sig-object`!)
- Нет `id` атрибута — имя генерируется из имени файла
- role = `"data"`, module = `"bpy.types.enum_items"`

---

## 6. Структура данных (что записывается в БД)

### 6.1 Символ (из parse_html_file)

```python
{
    "id": "bpy.ops.mesh.bevel",          # Полное имя = PK
    "name": "bpy.ops.mesh.bevel",         # Полное имя (для поиска)
    "short_name": "bevel",                # Короткое имя (для отображения)
    "description": "Cut into selected items...",
    "params": [                           # Массив параметров
        {
            "name": "offset_type",
            "type": "enum in['OFFSET',...]",
            "description": ""
        },
        {"name": "__enum__OFFSET", "type": "enum value", "description": "..."},
    ],
    "defaults": {
        "offset_type": "'OFFSET'",
        "offset": "0.0",
    },
    "has_params": True,                   # Только если params не пустой!
}
```

### 6.2 Enum Symbol (из _parse_enum_items_html)

```python
{
    "id": "bpy.types.enum_items.MeshSelectMode.VERT",
    "name": "bpy.types.enum_items.MeshSelectMode.VERT",
    "short_name": "VERT",
    "description": "Vertex selection mode.",
    "params": [],
    "defaults": {},
    "has_params": False,
}
```

---

## 7. Дополнительные функции

### 7.1 get_symbol_details(version, symbol_name)

Получить детальную информацию о символе, перебором HTML-файлов.

```python
individual_uri = symbol_name.replace(".", "/") + ".html"
# "bpy.ops.mesh.bevel" → "bpy/ops/mesh/bevel.html"
individual_path = base_path / individual_uri
```

### 7.2 get_full_page_content(version, uri)

Получить все символы с конкретной HTML-страницы.

```python
html_path = base_path / uri
return parse_html_file(html_path)
```

---

## 8. Распространённые ошибки

### ❌ Ошибка 1: has_params захардкожен в 1

```python
# ПЛОХО
batch.append((..., 1, ...))  # Всегда 1

# ХОРОШО
has_params = len(params) > 0
batch.append((..., has_params, ...))
```

### ❌ Ошибка 2: name = короткое имя

```python
# ПЛОХО — поиск по name не работает
name = short_name  # "bevel"

# ХОРОШО — полное имя для поиска
name = symbol_id  # "bpy.ops.mesh.bevel"
```

### ❌ Ошибка 3: search только article[role=main]

```python
# ПЛОХО — Sphinx 3.x не имеет article[role=main]
article = soup.find("article", {"role": "main"})

# ХОРОШО — проверка всех вариантов
article or main or div.document or div.rst-content
```

### ❌ Ошибка 4: has_params=True при поле только "Type"

```python
# ПЛОХО — находит field-list и ставит has_params=True
has_params = True

# ХОРОШО — только если есть реальные параметры
has_params = len(params) > 0
```

### ❌ Ошибка 5: Пропуск bpy_types_enum_items/

Эти файлы НЕ в `objects.inv` и НЕ имеют `dt.sig-object`. Их нужно парсить отдельно.

### ❌ Ошибка 6: regex defaults ловит слишком много

Regex `(\w+)\s*=\s*([^,\)\]\)]+?)` может захватывать лишнее в сложных сигнатурах.
Всегда проверяй результат на конкретных примерах.

---

## 9. Проверка работоспособности

После каждого изменения парсера проверять:

```python
# 1. Парсер не падает
from parser_html import parse_html_file
r = parse_html_file(Path("API_DOC/3_6/bpy.ops.mesh.html"))
assert len(r) > 0  # > 0 символов

# 2. has_params корректен
for s in r:
    if s["params"]:
        assert s["has_params"] == True
    else:
        assert s["has_params"] == False

# 3. Имена полные
for s in r:
    assert "." in s["name"]  # "bpy.ops.mesh.bevel", не "bevel"

# 4. Описание не пустое
for s in r:
    assert len(s["description"]) > 0
```

### Проверка через БД

```python
import sqlite3
conn = sqlite3.connect("BD_BASE/blender_api.db")
c = conn.cursor()

# 1. Нет ложных has_params
c.execute("""
    SELECT COUNT(*) FROM content
    WHERE has_params=1 AND (params='[]' OR params IS NULL OR params='null')
""")
assert c.fetchone()[0] == 0  # 0 ложноположительных

# 2. Нет дубликатов
c.execute("""
    SELECT COUNT(*) FROM content
    GROUP BY id, version HAVING COUNT(*) > 1
""")
assert c.fetchone() is None  # Нет дубликатов

# 3. Нет пустых описаний
c.execute("SELECT COUNT(*) FROM content WHERE description=''")
assert c.fetchone()[0] == 0

# 4. Coverage
c.execute("SELECT COUNT(*) FROM symbols")
sym = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM content")
cont = c.fetchone()[0]
assert cont / sym > 0.90  # > 90% coverage
```

---

## 10. Быстрый справочник HTML-селекторов

| Элемент | Селектор | Что даёт |
|---------|----------|-----------|
| dt символа | `dt.sig-object` | ID, сигнатуру |
| dt enum | `dt.field-odd`, `dt.field-even` | Enum value |
| span имени | `span.sig-name` | Короткое имя |
| dd описания | `dt ~ dd` (next sibling) | Описание + params |
| Первое описание | `dd > p:first-of-type` | Текст описания |
| Field-list | `dl.field-list` | Блок параметров |
| ul параметров | `ul.simple` | Формат A |
| strong имени | `p > strong` | Имя параметра |
| code enum | `code` | Значение enum |

---

## 11. Иерархия вызовов

```
indexer.py:
  index_version()
    ├── parser_inv.get_all_symbols()       → symbols из objects.inv
    ├── parser_html.parse_all_html()       → content dict + enum list
    │   ├── parser_html.parse_html_file()  → dt.sig-object символы
    │   └── _parse_enum_items_html()       → dt.field-* enum items
    ├── database.insert_symbols()          → symbols таблица
    ├── database.insert_enum_symbols()     → enum в symbols
    ├── database.insert_content()          → content таблица
    ├── database.update_has_content_flag() → has_content в symbols
    └── populate_fts()                     → FTS5 индекс
```

---

## 12. Зависимости

| Библиотека | Назначение |
|------------|-----------|
| `bs4` (BeautifulSoup) | Парсинг HTML |
| `lxml` | HTML-парсер для BS4 |
| `re` (std) | Regex для defaults и парсинга типов |
| `zlib` (std) | Декомпрессия objects.inv |
| `pathlib.Path` (std) | Работа с путями |

---

## 13. Восстановление парсера

Если парсер сломался:

### Шаг 1: Диагностика
```bash
# Запустить инкрементальную индексацию (покажет ошибки)
BD_BASE\start_indexer.bat

# Проверить конкретный файл
python -c "from parser_html import parse_html_file; print(parse_html_file('API_DOC/3_6/bpy.ops.mesh.html'))"
```

### Шаг 2: Сброс
```bash
# Удалить БД и пересоздать
BD_BASE\force_reindex.bat
```

### Шаг 3: Проверка отдельных шагов
```python
# Только objects.inv
python -c "from parser_inv import get_all_symbols; print(len(get_all_symbols('3_6')))"

# Только HTML (без БД)
python -c "from parser_html import parse_html_file; print(len(parse_html_file('API_DOC/3_6/bpy.ops.mesh.html')))"
```

### Шаг 4: Сравнение с известной рабочей версией
```bash
git diff HEAD -- _mcp_server/parser_html.py
git diff HEAD -- _mcp_server/parser_inv.py
```
