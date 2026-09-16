---
name: blender-docs-html
description: Специалист по HTML-документации Blender API. Парсит HTML-файлы, понимает структуру Sphinx (3.x/4.x+), извлекает символы, параметры, описания, enum-значения. Отлаживает парсинг, добавляет новые версии.
---

Триггеры: парсить HTML, парсер, parser, HTML-структура, Sphinx, content area, sig-object, field-list, enum items, bpy_types_enum_items, параметры, defaults, has_params, парсинг HTML, парсить символы

Загружать: при работе с HTML-файлами документации Blender API, парсинге символов, отладке парсера, добавлении новых версий, анализе HTML-структуры

Роль: специалист по HTML-документации Blender API и парсеру parser_html.py

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

**Пути:**
- `_mcp_server/parser_html.py` — основной парсер
- `_mcp_server/parser_inv.py` — парсер objects.inv
- `_mcp_server/DOC_PARSER.md` — полная документация
- `_mcp_server/HTML_STRUCTURES_REFERENCE.md` — справочник HTML-структур

---

## 1. Sphinx темы и контент-область

Sphinx 3.x (ReadTheDocs) и 4.x+ (PyData) используют разные контейнеры.

### Приоритет поиска контент-области

```python
# Новая Sphinx (4.x+)
article = soup.find("article", {"role": "main"})
if article: return article

main = soup.find("main")
if main: return main

# Старая Sphinx (3.x, ReadTheDocs)
doc = soup.find("div", class_="document")
if doc: return doc

rst = soup.find("div", class_="rst-content")
if rst: return rst

# Fallback
return soup
```

### Как определить тему Sphinx

| Признак | Sphinx 3.x | Sphinx 4.x+ |
|---------|------------|-------------|
| Контейнер | `div.document` или `div.rst-content` | `article[role=main]` или `main` |
| Параметры | `ul.simple > li` | `dt/dd` пары в field-list |
| Класс dt | `sig sig-object py` | `sig sig-object py` |

---

## 2. Основные символы (parse_html_file)

### 2.1 dt — тег определения символа

| Атрибут | Значение | Пример |
|---------|----------|--------|
| `class` | `['sig', 'sig-object', 'py']` | Всегда эти 3 класса |
| `id` | Полное имя символа | `bpy.ops.mesh.bevel` |
| `span.sig-prename` | Префикс модуля | `bpy.ops.mesh.` |
| `span.sig-name` | Короткое имя | `bevel` |

**Селектор:** `dt` с `class_=re.compile(r"sig-object")`

### 2.4 Sphinx 8.x — Новая структура сигнатур

Blender 5.1 использует Sphinx 8.2.3 — сигнатуры разбиты на под-элементы:

```html
<dt class="sig sig-object py" id="bpy.ops.mesh.bevel">
  <span class="sig-prename descclassname"><span class="pre">bpy.ops.mesh.</span></span>
  <span class="sig-name descname"><span class="pre">bevel</span></span>
  <span class="sig-paren">(</span>
  <em class="sig-param">
    <span class="keyword-only-separator o"><abbr>...</abbr><span class="pre">*</span></span>
  </em>
  <em class="sig-param">
    <span class="n">value_float</span>
    <span class="o">=</span>
    <span class="default_value">0.0</span>
  </em>
  <span class="sig-paren">)</span>
</dt>
```

**Новые классы:**
- `keyword-only-separator` — PEP 3102 `*` для keyword-only параметров
- `n` — имя параметра (было слитно с текстом)
- `o` — операторы (`=`, `*`, `,`)
- `default_value` — значение по умолчанию (вынесено отдельно)
- `sig-paren` — отдельные скобки
- `descclassname` — префикс модуля (был `prename`)

**Результат:** Regex для defaults должен учитывать новые классы:
```python
# Старый: sig_text = "bevel(offset=0.0)"
# Новый: sig_text = "bevel(*, value_float=0.0, value_int=0)"
# keyword-only separator * нужно игнорировать
defaults = re.findall(r"(\w+)\s*=\s*([^,)]+?)(?=\s*[,)])", sig_text)
```

### 2.2 Алгоритм извлечения

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

### 2.3 Regex для defaults

```python
# name = value, где value = число, строка, кортеж, булево
# Останавливается на , ) ]
re.findall(r"(\w+)\s*=\s*([^,\)\]\)]+?)(?=\s*[,\)])", sig_text)
```

**Пример:** `bpy.ops.mesh.bevel(offset_type='OFFSET', offset=0.0)`
**Результат:** `{offset_type: "'OFFSET'", offset: "0.0"}`

---

## 3. Параметры — 4 ФОРМАТА

### Формат A: `<ul><li>` (старая Sphinx)

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

**Парсинг:**
1. `dd.find("dl", class_=re.compile(r"field-list"))`
2. `field_list.find("ul", class_="simple")`
3. `ul.find_all("li")` → каждый li = один параметр
4. `li.find("p")` → `p.find("strong")` = имя параметра
5. Текст после `–` = описание
6. Текст в скобках `(...)` = тип

**Regex для типа:**
```python
clean = re.sub(r",?\s*\(optional\)\s*", "", type_part).strip()
first_open = clean.find("(")
last_close = clean.rfind(")")
param_type = clean[first_open + 1:last_close].strip()
```

### Формат B: `<p><strong>` прямо в `<dd>` (старая Sphinx)

**Где:** `bpy.ops.console.html`, `bpy.ops.object.*.html`, `bpy_extras.*.html`

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

### Формат C: только Type (без параметров)

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

### Формат D: dt/dd пары (новая Sphinx 4.x+)

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

**Парсинг:**
1. `dd.find("dl", class_=re.compile(r"field-list"))`
2. `field_list.find_all("dt")` — каждый dt (кроме заголовков) = параметр
3. `dt.get_text(strip=True)` = имя параметра
4. `dt.find_next_sibling("dd").get_text(strip=True)` = "Type – description"

### Как определяется формат (_parse_params)

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

**Парсинг:**
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

### Структура файла

```html
<dl class="field-list">
  <dt class="field-odd">VERT</dt>
  <dd class="field-odd">Vertex selection mode.</dd>
  <dt class="field-even">EDGE</dt>
  <dd class="field-even">Edge selection mode.</dd>
</dl>
```

### Генерация имени символа

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

### Важно

- Селектор: `dt` с `class_=re.compile(r"field-")` (НЕ `sig-object`!)
- Нет `id` атрибута — имя генерируется из имени файла
- role = `"data"`, module = `"bpy.types.enum_items"`

---

## 6. Структура данных (что записывается в БД)

### Символ (из parse_html_file)

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

### Enum Symbol (из _parse_enum_items_html)

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

### get_symbol_details(version, symbol_name)

Получить детальную информацию о символе, перебором HTML-файлов.

```python
individual_uri = symbol_name.replace(".", "/") + ".html"
# "bpy.ops.mesh.bevel" → "bpy/ops/mesh/bevel.html"
individual_path = base_path / individual_uri
```

### get_full_page_content(version, uri)

Получить все символы с конкретной HTML-страницы.

```python
html_path = base_path / uri
return parse_html_file(html_path)
```

### parse_all_html(version, symbol_list)

Оркестратор: парсит все HTML-файлы для символов и возвращает lookup-словарь + enum-символы.

```python
content_dict, enum_symbols = parse_all_html("3_6", symbol_list)
# content_dict: {"bpy.ops.mesh.bevel": {...}, ...}
# enum_symbols: [{"id": "...", ...}, ...]
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

## 9. Быстрый справочник HTML-селекторов

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

## 10. Зависимости

| Библиотека | Назначение |
|------------|-----------|
| `bs4` (BeautifulSoup) | Парсинг HTML |
| `lxml` | HTML-парсер для BS4 |
| `re` (std) | Regex для defaults и парсинга типов |
| `zlib` (std) | Декомпрессия objects.inv |
| `pathlib.Path` (std) | Работа с путями |

---

## 11. Проверка работоспособности

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

---

## 12. Отладка парсера

### Диагностика проблем

```bash
# Запустить инкрементальную индексацию (покажет ошибки)
BD_BASE\start_indexer.bat

# Проверить конкретный файл
python -c "from parser_html import parse_html_file; print(parse_html_file('API_DOC/3_6/bpy.ops.mesh.html'))"

# Проверить objects.inv
python -c "from parser_inv import get_all_symbols; print(len(get_all_symbols('3_6')))"
```

### Типичные проблемы

| Проблема | Причина | Решение |
|----------|---------|---------|
| 0 символов найдено | Нет dt.sig-object или нет content_area | Проверить HTML-структуру вручную |
| has_params=True при пустых params | Только Type в field-list | Проверить _parse_params() |
| Пустые описания | Первый <p> пустой или нет <p> | Проверить структуру HTML |
| Ошибка zlib | objects.inv повреждён | Перекачать архив Blender |
| Кодировка UTF-8 | HTML не UTF-8 | Конвертировать файл |

### Сброс

```bash
# Удалить БД и пересоздать
BD_BASE\force_reindex.bat
```

---

## 13. Структуры файлов

| Категория | Кол-во | Примеры | Структура |
|-----------|--------|---------|-----------|
| operators | 75 | bpy.ops.mesh.html | Формат A (ul>li) |
| types | 1420 | bpy.types.Scene.html | Класс + атрибуты (dt.dd) |
| props | 1 | bpy.props.html | Формат A (ul>li) |
| modules | 4 | mathutils.html | Классы + методы |
| bmesh | 4 | bmesh.ops.html | Формат A (ul>li) |
| bpy_extras | 10 | bpy_extras.mesh_utils.html | Формат B (p>strong) |
| enum_items | 179 | mesh_select_mode_items.html | Только field-list |
| other | 86 | bgl.html, bpy.app.html | Разные |

---

## 14. Запуск парсера вручную

### Парсинг одного файла

```python
from pathlib import Path
import sys; sys.path.insert(0, '_mcp_server')
from parser_html import parse_html_file

result = parse_html_file(Path("API_DOC/3_6/bpy.ops.mesh.html"))
for sym in result:
    print(f"{sym['name']}: {sym['description'][:50]}...")
```

### Парсинг всех файлов версии

```python
from pathlib import Path
import sys; sys.path.insert(0, '_mcp_server')
from parser_inv import get_all_symbols
from parser_html import parse_all_html

symbols = get_all_symbols("3_6")
content, enums = parse_all_html("3_6", symbols)
print(f"Парсено {len(content)} символов, {len(enums)} enum")
```

### Поиск по URI

```python
from pathlib import Path
import sys; sys.path.insert(0, '_mcp_server')
from parser_html import get_full_page_content

result = get_full_page_content("3_6", "bpy.ops.mesh.html")
print(f"Найдено {len(result)} символов")
```

---

## 15. Восстановление парсера

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

---

## Запрещено

- ❌ Модифицировать objects.inv (бинарник, zlib!)
- ❌ Удалять HTML-файлы после индексации
- ❌ Запускать indexer.py без проверки objects.inv
- ❌ Парсить HTML напрямую вместо парсера (если не отладка)
- ❌ Использовать hardcoded пути вместо config.py

Я вывожу сообщения в чат:
✅ Загрузил скилл: blender-docs-html
