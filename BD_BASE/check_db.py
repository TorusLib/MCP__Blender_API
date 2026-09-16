"""
Проверка целостности БД и сравнение с API_DOC/
Добавлена проверка обновлений HTML-файлов.
"""

import sys
from pathlib import Path

# Добавить _mcp_server в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "_mcp_server"))

import sqlite3
import time

from config import API_DOC_DIR, DB_PATH
from utils import compute_md5


def get_html_files_hash() -> dict:
    """
    Хеш всех HTML-файлов в API_DOC/.
    Возвращает dict: {version: {filename: hash, ...}}
    """
    result = {}
    if not API_DOC_DIR.exists():
        return result
    for version in sorted(d.name for d in API_DOC_DIR.iterdir() if d.is_dir()):
        version_dir = API_DOC_DIR / version
        files = {}
        for fname in sorted(version_dir.iterdir()):
            if fname.is_file() and fname.suffix == ".html":
                files[fname.name] = compute_md5(fname)
        if files:
            result[version] = files
    return result


def main() -> None:
    # Проверяем существование
    if not DB_PATH.exists():
        print("[ERROR] БД не найдена: BD_BASE/blender_api.db")
        print("Запусти: BD_BASE\\start_indexer.bat")
        sys.exit(1)

    if not API_DOC_DIR.exists():
        print("[ERROR] Папка API_DOC/ не найдена!")
        sys.exit(1)

    # Данные из БД
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM symbols")
    symbols = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM content")
    content = c.fetchone()[0]
    c.execute("SELECT DISTINCT version FROM symbols ORDER BY version")
    db_versions = [r[0] for r in c.fetchall()]
    conn.close()

    print("--- Данные из БД ---")
    print(f"  Символов: {symbols}")
    print(f"  Описаний: {content}")
    print(f"  Версий: {len(db_versions)} ({', '.join(db_versions)})")

    # Данные на диске
    print()
    print("--- Данные на диске ---")
    api_versions = []
    for d in sorted(API_DOC_DIR.iterdir()):
        if d.is_dir():
            inv = d / "objects.inv"
            html_count = len(
                [f for f in d.iterdir() if f.is_file() and f.suffix == ".html"]
            )
            api_versions.append(d.name)
            print(
                f"    {d.name}: {html_count} HTML-файлов, objects.inv: {'да' if inv.exists() else 'нет'}"
            )
    print(f"  Версий в API_DOC/: {len(api_versions)} ({', '.join(api_versions)})")

    # Сравнение версий
    print()
    print("--- Статус версий ---")
    db_set = set(db_versions)
    api_set = set(api_versions)

    missing = api_set - db_set
    extra = db_set - api_set

    if not missing and not extra:
        print("  [OK] Все версии совпадают!")
    else:
        if missing:
            print(f"  [WARN] Версии в API_DOC но не в БД: {sorted(missing)}")
            print("         Запусти: BD_BASE\\start_indexer.bat")
        if extra:
            print(f"  [WARN] Версии в БД но не в API_DOC: {sorted(extra)}")

    # Проверка обновлений HTML-файлов (сводка)
    print()
    print("--- Сводка по версиям ---")
    for version in db_versions:
        version_dir = API_DOC_DIR / version
        if not version_dir.is_dir():
            continue
        html_count = len(
            [f for f in version_dir.iterdir() if f.is_file() and f.suffix == ".html"]
        )
        inv_path = version_dir / "objects.inv"
        inv_size = inv_path.stat().st_size if inv_path.exists() else 0
        inv_hash = compute_md5(inv_path) if inv_path.exists() else ""

        # Последние даты изменения HTML и inv
        html_dates = []
        for fname in version_dir.iterdir():
            if fname.is_file() and fname.suffix == ".html":
                mtime = fname.stat().st_mtime
                html_dates.append(time.strftime("%Y-%m-%d", time.localtime(mtime)))

        latest_html = max(html_dates) if html_dates else ""
        inv_mtime = (
            time.strftime("%Y-%m-%d %H:%M", time.localtime(inv_path.stat().st_mtime))
            if inv_path.exists()
            else ""
        )

        print(f"  {version}:")
        print(f"    HTML: {html_count} файлов, последний: {latest_html}")
        print(f"    objects.inv: {inv_size:,} байт, MD5: {inv_hash[:12]}")
        if inv_mtime:
            print(f"    objects.inv изменён: {inv_mtime}")

    print()
    print("--- Итог ---")
    if missing:
        print("  [ACTION] Добавлены новые версии → запусти BD_BASE\\start_indexer.bat")
    elif extra:
        print("  [ACTION] Удалены версии с диска → запусти BD_BASE\\force_reindex.bat")
    else:
        print("  [OK] Всё в порядке, БД актуальна")


if __name__ == "__main__":
    main()
