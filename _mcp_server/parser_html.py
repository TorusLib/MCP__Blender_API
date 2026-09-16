"""
Новый парсер Blender API HTML документации.
Работает с обеими Sphinx темами:
  - Старая ReadTheDocs (Sphinx 3.x): div.rst-content, ul.simple для параметров
  - Новая PyData (Sphinx 4.x+): article[role=main], dl.field-list simple для параметров
"""

import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from config import version_dir


def _find_content_area(soup: BeautifulSoup) -> Tag:
    """Найти основной контент HTML — поддерживает старые и новые Sphinx."""
    # Новая Sphinx (4.x+)
    article = soup.find("article", {"role": "main"})
    if article:
        return article

    main = soup.find("main")
    if main:
        return main

    # Старая Sphinx (3.x, ReadTheDocs)
    doc = soup.find("div", class_="document")
    if doc:
        return doc

    rst = soup.find("div", class_="rst-content")
    if rst:
        return rst

    return soup


def _parse_signature_defaults(sig_text: str) -> dict:
    """Извлечь дефолтные значения из текста сигнатуры."""
    defaults = {}
    # Паттерн: name = value, где value может быть числом, строкой, кортежем, булем
    matches = re.findall(r"(\w+)\s*=\s*([^,\)\]\)]+?)(?=\s*[,\)])", sig_text)
    for param_name, default_val in matches:
        defaults[param_name.strip()] = default_val.strip()
    return defaults


def _parse_param_p(p_tag: Tag) -> dict | None:
    """Извлечь параметр из <p><strong>name</strong> (type) – description</p>."""
    strong = p_tag.find("strong")
    if not strong:
        return None

    param_name = strong.get_text(strip=True)
    raw_text = p_tag.get_text(strip=True)

    # Ищем "–" (em-dash) как разделитель типа и описания
    dash_match = re.match(r"^(.+?)\s*[–—]\s*(.*)$", raw_text)
    if dash_match:
        type_part = dash_match.group(1).strip()
        description = dash_match.group(2).strip()
        # Извлекаем тип из скобок: "value_float(float in[-inf,inf],(optional))"
        # Сначала уберём (optional)
        clean = re.sub(r",?\s*\(optional\)\s*", "", type_part).strip()
        first_open = clean.find("(")
        last_close = clean.rfind(")")
        if first_open > 0 and last_close > first_open:
            param_type = clean[first_open + 1 : last_close].strip()
        else:
            param_type = clean
    else:
        param_type = raw_text
        description = ""

    return {"name": param_name, "type": param_type, "description": description}


def _extract_enum_values(ul_simple) -> list[dict]:
    """Извлечь enum-значения из вложенных <ul> внутри <li>."""
    enums = []
    for li in ul_simple.find_all("li"):
        nested_ul = li.find("ul")
        if nested_ul:
            for nested_li in nested_ul.find_all("li"):
                p_tag = nested_li.find("p")
                if p_tag:
                    text = p_tag.get_text(strip=True)

                    # Формат: EnumName – Description
                    dash_match = re.match(r"^(.+?)\s*[–—]\s*(.*)$", text)
                    if dash_match:
                        enum_val_clean = dash_match.group(1).strip()
                        enum_desc = dash_match.group(2).strip()
                        enums.append(
                            {
                                "name": f"__enum__{enum_val_clean}",
                                "type": "enum value",
                                "description": enum_desc,
                            }
                        )
    return enums


def _parse_old_sphinx_params(dd: Tag) -> tuple[list[dict], bool]:
    """Парсить параметры для старой Sphinx (ul.simple внутри dd)."""
    params = []

    field_list = dd.find("dl", class_=re.compile(r"field-list"))
    if not field_list:
        return params, False

    # Формат 1: Параметры в <ul class="simple"><li>
    ul_simple = field_list.find("ul", class_="simple")
    if ul_simple:
        for li in ul_simple.find_all("li"):
            p = li.find("p")
            if p:
                result = _parse_param_p(p)
                if result:
                    params.append(result)

        # Enum-значения
        params.extend(_extract_enum_values(ul_simple))

    # Формат 2: Параметры прямо в <dd> как <p><strong>name</strong>...</p>
    # (без ul-обёртки)
    else:
        # Пропускаем <p> описания (первый p в dd — это описание функции)
        all_ps = dd.find_all("p")
        for p in all_ps[1:]:  # пропускаем первый <p> (описание)
            strong = p.find("strong")
            if strong and strong.get_text(strip=True) in (
                "Type",
                "Parameters",
                "Returns",
                "Return type",
            ):
                continue
            result = _parse_param_p(p)
            if result:
                params.append(result)

    has_params = len(params) > 0
    return params, has_params


def _parse_new_sphinx_params(dd: Tag) -> tuple[list[dict], bool]:
    """Парсить параметры для новой Sphinx (dl.field-list simple с dt/dd парами)."""
    params = []

    field_list = dd.find("dl", class_=re.compile(r"field-list"))
    if not field_list:
        return params, False

    for dt_item in field_list.find_all("dt"):
        text = dt_item.get_text(strip=True)
        # Пропускаем заголовки
        if text in ("Type", "Parameters", "Returns", "Return type", "Yields"):
            continue

        dd_item = dt_item.find_next_sibling("dd")
        if dd_item:
            param_text = dd_item.get_text(strip=True)
            # Формат: Type – description
            type_match = re.match(r"(\S.+?)\s*[–—]\s*(.*)$", param_text)
            if type_match:
                param_type = type_match.group(1).strip()
                param_desc = type_match.group(2).strip()
            else:
                param_type = ""
                param_desc = param_text

            params.append(
                {
                    "name": text,
                    "type": param_type,
                    "description": param_desc,
                }
            )

    has_params = len(params) > 0
    return params, has_params


def _parse_params(dd: Tag) -> tuple[list[dict], bool]:
    """Автоматически определить тему Sphinx и парсить параметры."""
    # Пробуем новую Sphinx (dt/dd пары в field-list)
    new_params, new_has = _parse_new_sphinx_params(dd)
    if new_has and len(new_params) > 0:
        # Проверим — если есть dt без заголовка Type/Parameters, значит новая тема
        field_list = dd.find("dl", class_=re.compile(r"field-list"))
        if field_list:
            dts = field_list.find_all("dt")
            real_params = [
                dt
                for dt in dts
                if dt.get_text(strip=True)
                not in ("Type", "Parameters", "Returns", "Return type", "Yields")
            ]
            if real_params:
                return new_params, new_has

    # Старая Sphinx (ul.simple)
    return _parse_old_sphinx_params(dd)


def parse_html_file(html_path: Path) -> list[dict]:
    """Парсить один HTML-файл и извлечь определения символов."""
    symbols = []

    if not html_path.exists():
        return symbols

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return symbols

    soup = BeautifulSoup(content, "lxml")
    main_content = _find_content_area(soup)

    # Находим все dt.sig-object элементы
    for sig_dt in main_content.find_all("dt", class_=re.compile(r"sig-object")):
        symbol_id = sig_dt.get("id", "")
        if not symbol_id:
            continue

        # name = полное имя символа (для поиска в БД)
        # short_name = короткое имя (для отображения)
        sig_name_span = sig_dt.find("span", class_="sig-name")
        short_name = sig_name_span.get_text(strip=True) if sig_name_span else symbol_id
        name = symbol_id  # full dotted name

        # Описание и параметры из dd
        dd = sig_dt.find_next_sibling("dd")
        description = ""
        params = []
        has_params = False

        if dd:
            # Первый <p> — описание
            first_p = dd.find("p")
            if first_p:
                description = first_p.get_text(strip=True)

            # Параметры
            params, has_params = _parse_params(dd)

        # Дефолтные значения из сигнатуры
        sig_text = sig_dt.get_text()
        defaults = _parse_signature_defaults(sig_text)

        # Записываем только если есть описание (фильтр мусора)
        if symbol_id and description:
            symbols.append(
                {
                    "id": symbol_id,
                    "name": name,
                    "short_name": short_name,
                    "description": description,
                    "params": params,
                    "defaults": defaults,
                    "has_params": has_params or len(params) > 0,
                }
            )

    return symbols


def _parse_enum_items_html(enum_dir: Path) -> list[dict]:
    """Парсить bpy_types_enum_items/ — файлы enum значений без dt.sig-object.

    Структура: dl.field-list с dt.field-odd/field-even и dd.
    Пример: attribute_curves_domain_items.html -> POINT, CURVE, ...
    """
    symbols = []
    if not enum_dir.exists():
        return symbols

    for f in enum_dir.glob("*.html"):
        try:
            content = open(f, encoding="utf-8").read()
        except Exception:
            continue

        soup = BeautifulSoup(content, "lxml")
        doc = (
            soup.find("div", class_="document")
            or soup.find("div", class_="rst-content")
            or soup
        )

        # Ищем dt.field-odd/field-even (не sig-object!)
        dts = doc.find_all("dt", class_=re.compile(r"field-"))
        if not dts:
            continue

        # Определяем имя файла -> префикс
        # attribute_curves_domain_items.html -> bpy.types.enum_items.AttributeCurvesDomainItems
        stem = f.stem  # e.g. attribute_curves_domain_items
        # Преобразуем snake_case -> PascalCase
        parts = stem.split("_")
        class_name = "".join(p.capitalize() for p in parts)
        # Удаляем "items" suffix
        if class_name.endswith("Items"):
            class_name = class_name[:-5]

        for dt in dts:
            value = dt.get_text(strip=True)
            dd = dt.find_next_sibling("dd")
            description = dd.get_text(strip=True) if dd else ""

            if value and description:
                symbol_id = f"bpy.types.enum_items.{class_name}.{value.upper()}"
                symbols.append(
                    {
                        "id": symbol_id,
                        "name": symbol_id,
                        "short_name": value.upper(),
                        "description": description,
                        "params": [],
                        "defaults": {},
                        "has_params": False,
                    }
                )

    return symbols


def parse_all_html(version: str, symbol_list: list[dict]) -> tuple[dict, list[dict]]:
    """
    Парсить HTML-файлы для символов и вернуть lookup-словарь + enum-символы.

    Args:
        version: Версия (3_6, 4_5, 5_1)
        symbol_list: Список символов из objects.inv

    Returns:
        (content_dict, enum_symbols_list)
    """
    base_path = version_dir(version)
    if not base_path.exists():
        return {}, []

    # Собираем URI из symbol_list
    uris_to_parse = set()
    for sym in symbol_list:
        uri = sym.get("uri", "")
        if uri and uri.endswith(".html"):
            uris_to_parse.add(uri)

    parsed = {}
    total = len(uris_to_parse)

    for i, uri in enumerate(sorted(uris_to_parse), 1):
        if i % 200 == 0:
            print(f"    [{i}/{total}] Parsing {uri}...")

        html_path = base_path / uri

        if html_path in parsed:
            continue

        symbols = parse_html_file(html_path)
        for sym in symbols:
            parsed[sym["id"]] = sym

    # Парсим bpy_types_enum_items/
    enum_dir = base_path / "bpy_types_enum_items"
    enum_symbols = []
    if enum_dir.exists():
        enum_symbols = _parse_enum_items_html(enum_dir)
        for sym in enum_symbols:
            parsed[sym["id"]] = sym
        print(f"  [ENUM] Parsed {len(enum_symbols)} enum items")

    print(f"  [OK] Parsed {len(parsed)} symbols from {version}")
    return parsed, enum_symbols


def get_full_page_content(version: str, uri: str) -> list[dict]:
    """Получить все символы с конкретной HTML-страницы."""
    base_path = version_dir(version)
    html_path = base_path / uri

    if not html_path.exists():
        return []

    return parse_html_file(html_path)
