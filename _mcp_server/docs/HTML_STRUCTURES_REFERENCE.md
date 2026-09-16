# HTML Структуры Sphinx Documentation (Blender API)

> Полная карта HTML-структур для парсинга Blender API документации.
> Sphinx 3.x тема ReadTheDocs + Sphinx 4.x+ тема PyData.

---

## 1. Контент-область (Content Area)

### Sphinx 4.x+ (PyData)

```python
article = soup.find("article", {"role": "main"})
if not article:
    article = soup.find("main")
```

### Sphinx 3.x (ReadTheDocs)

```python
doc = soup.find("div", class_="
document")
if not doc:
    doc = soup.find("div", class_="rst-content")
```

### Общий fallback

```python
article or main or div.document or div.rst-content or soup
```

---

## 2. Символы (Symbols)

### 2.1 Базовая структура (Sphinx 3.x — ReadTheDocs)

```html
<dt class="sig sig-object py" id="bpy.ops.mesh.bevel">
  <span class="sig-name pre">bpy.ops.mesh.bevel</span>(params...)
  <a class="headerlink" ...>¶</a>
</dt>
<dd>
  <p>Описание символа.</p>
  <dl class="field-list simple">
    <dt class="field-odd">Parameters</dt>
    <dd class="field-odd">
      <ul class="simple">
        <li><p><strong>param_name</strong> (<em>type</em>) – description</p></li>
      </ul>
    </dd>
  </dl>
</dd>
```

### 2.2 Новая Sphinx (4.x+ — PyData)

```html
<dt class="sig sig-object py" id="bpy.ops.mesh.bevel">
  <span class="sig-name pre">bpy.ops.mesh.bevel</span>(params...)
  <a class="headerlink" ...>¶</a>
</dt>
<dd>
  <p>Описание символа.</p>
  <dl class="field-list simple">
    <dt class="field-odd">Parameters</dt>
    <dd class="field-odd">
      <dl class="simple">
        <dt><strong>param_name</strong></dt>
        <dd><p>type – description</p></dd>
      </dl>
    </dd>
  </dl>
</dd>
```

### 2.3 Ключевые селекторы

| Что | Селектор | Пример |
|-----|----------|--------|
| dt символа | `dt.sig-object` | `id=bpy.ops.mesh.bevel` |
| Классы dt | `['sig', 'sig-object', 'py']` | Всегда эти 3 |
| ID символа | `dt['id']` | Полное имя: `bpy.types.Scene.active_clip` |
| span.sig-name | `span.sig-name` | Короткое имя: `active_clip` |
| dd описания | `dd` (next sibling dt) | Первый `<p>` внутри |
| Первое описание | `dd > p:first-of-type` | Текст описания |

### 2.4 Исключения — dt БЕЗ id

Файл `bgl.html`: некоторые dt НЕ имеют `id`:

```html
<dt class="sig sig-object py">
  <span class="sig-name pre">glBindTexture</span>(target,texture):
</dt>
```

**Решение:** брать `span.sig-name` и парсить из сигнатуры.

---

## 3. Параметры — 3 формата (старая Sphinx)

Параметры всегда внутри `dl.field-list`, но структура разная.

### Формат A: `<ul><li>` в field-list (основной)

**Где:** `bpy.ops.*.html`, `bpy.props.html`, `bmesh.*.html`

```html
<dl class="field-list simple">
  <dt class="field-odd">Parameters</dt>
  <dd class="field-odd">
    <ul class="simple">
      <li>
        <p><strong>offset_type</strong> (<em>enum in</em>...) – description</p>
        <ul>
          <li><p><code>OFFSET</code> Offset – Amount is offset...</p></li>
        </ul>
      </li>
    </ul>
  </dd>
</dl>
```

**Парсинг:**
- `dl.field-list simple` → `ul.simple` → `li` → `p` → `strong`
- `<strong>` = имя параметра
- `<p>` текст после `–` = описание
- `<p>` текст в скобках `(...)` = тип

### Формат B: `<p><strong>` прямо в `<dd>` (без ul)

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
- `dd > dl.field-list > dd > p` (первый p — описание, остальные — параметры)
- `<p>` с `<strong>` = параметр
- skip первые `<p>` (описание функции)

### Формат C: только Type (без параметров)

**Где:** `bpy.types.*.html` (атрибуты классов), `mathutils.*.html`

```html
<dd>
  <p>Attribute description.</p>
  <p>MovieClip</p>
  <dl class="field-list simple">
    <dt class="field-odd">Type</dt>
    <dd class="field-odd">MovieClip</dd>
  </dl>
</dd>
```

**Парсинг:**
- `dl.field-list` есть, но только `<dt>Type</dt>` — НЕ параметр
- `has_params = False`

---

## 4. Enum-значения (Enum Values)

**Где:** внутри `<li>` в Формате A

```html
<li>
  <p><strong>offset_type</strong> (<em>enum in</em>...) – </p>
  <ul>
    <li><p><code>OFFSET</code> Offset – Amount is offset of new edges.</p></li>
    <li><p><code>WIDTH</code> Width – Amount is width of new face.</p></li>
  </ul>
</li>
```

**Парсинг:** `li > ul > li > p` → `<code>` = значение, `p` текст после `–` = описание

---

## 5. bpy.types — классы и атрибуты (bpy.types.*.html)

### 5.1 Структура файла

Один файл = один класс. Содержит:
- 1 dt для класса
- Множество dt для атрибутов/методов

```html
<!-- Класс -->
<dt id="bpy.types.Scene">
  <span>classbpy.types.Scene(ID)</span>
</dt>
<dd>
  <p>Scene data-block...</p>
  <!-- Все атрибуты описаны как p без strong -->
  <p>Active Movie Clip...</p>
  <p>MovieClip</p>
  <p>Animation data...</p>
  <p>AnimData, (readonly)</p>
  ...

<!-- Атрибут (отдельный dt.dd) -->
<dt id="bpy.types.Scene.active_clip">
  <span>active_clip</span>
</dt>
<dd>
  <p>Active Movie Clip...</p>
  <p>MovieClip</p>
  <dl class="field-list simple">
    <dt>Type</dt><dd>MovieClip</dd>
  </dl>
</dd>
```

### 5.2 Ключевые особенности

- Первый `<p>` в dd = описание класса/атрибута
- Последующие `<p>` без `<strong>` = описания/типы других атрибутов (только для класса!)
- Атрибуты имеют собственные dt.dd пары
- У атрибутов: dd имеет ровно 2 `<p>`: описание + тип
- `has_params = False` для всех типов (только Type в field-list)

---

## 6. bpy.types Enum Items (bpy_types_enum_items/)

**Структура:**

```html
<dl class="field-list">
  <dt class="field-odd">VERT</dt><dd>Vertex selection mode.</dd>
  <dt class="field-even">EDGE</dt><dd>Edge selection mode.</dd>
  <dt class="field-odd">FACE</dt><dd>Face selection mode.</dd>
</dl>
```

**Символы:** `bpy.types.enum_items.MeshSelectModeItems.VERTEX`, и т.д.
**dt.sig-object:** нет! Просто `dt.field-odd/field-even`.
**id:** нет.

---

## 7. Модули (bpy.html, mathutils.html, bgl.html)

### mathutils.html
- 498 символов (классы + методы)
- Структура: как `bpy.types.*.html`
- Классы: `mathutils.Color`, `mathutils.Vector`, и т.д.
- Методы: `mathutils.Color.copy`, и т.д.

### bgl.html
- 100 символов (C API функции)
- НЕКОТОРЫЕ dt БЕЗ `id` атрибута
- Нужно брать имя из `<span.sig-name>` + сигнатуры

### bpy.html
- Модуль bpy (не операторы!)
- `bpy.app`, `bpy.context`, `bpy.data`, и т.д.

---

## 8. Классы файлов

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

## 9. Алгоритм парсинга (итоговый)

```
1. Найти content_area: article[role=main] OR main OR div.document OR div.rst-content
2. Найти все dt.sig-object
3. Для каждого dt:
   a. symbol_id = dt['id'] (пропустить если пусто, кроме bgl)
   b. name = span.sig-name text
   c. dd = dt.find_next_sibling('dd')
   d. description = dd.p[0].text (первый <p>)
   e. Парсить параметры из dd:
      - Найти dl.field-list
      - Если ul.simple внутри → Формат A: li > p > strong
      - Иначе если p>strong в dd → Формат B
      - Иначе → только Type, has_params=False
   f. defaults = regex из dt text: (\w+) = ([^,)\]]+)
```

---

## 10. Regex для сигнатуры

```python
# Defaults: name = value, где value не содержит ,)
re.findall(r"(\w+)\s*=\s*([^,\)\]\)]+?)(?=\s*[,\)])", sig_text)

# Параметр name: <strong>name</strong>
strong = p.find('strong')
param_name = strong.get_text(strip=True)

# Тип: текст в скобках после имени
# Формат: name(type_info, (optional)) – description
clean = re.sub(r",?\s*\(optional\)\s*", "", type_part)
first_open = clean.find("(")
last_close = clean.rfind(")")
param_type = clean[first_open+1:last_close]
```

---

## 11. Что НЕ нужно парсить

- `.doctrees/*.doctree` — бинарные pickled dicts Sphinx
- `_static/*` — CSS/JS
- `css/*`, `js/*` — стили/скрипты
- `blender_logo.svg` — логотип
- `.buildinfo` — мета-файл

---

## 12. Связь objects.inv → HTML

```
objects.inv строка:
  bpy.ops.mesh.bevel:function bpy.ops.mesh.html #-

Разбор:
  name = bpy.ops.mesh.bevel
  role = function
  uri = bpy.ops.mesh.html
  anchor = #-
```

URI = filename.html (без `API_DOC/3_6/` префикса).
