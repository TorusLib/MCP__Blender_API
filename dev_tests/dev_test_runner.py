"""Dev-тесты. Укажи версию для тестирования."""

# ─── Выбери версию ───────────────────────────────────────────────────────
TEST_VERSION = "3_6"  # ← поменяй: "3_6", "4_5", "5_1" или "all"
# ──────────────────────────────────────────────────────────────────────────

import sys
from pathlib import Path

# UTF-8 вывод (Windows консоль по умолчанию cp1251)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Добавить _mcp_server в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "_mcp_server"))

import business_logic as bl
import database as db

db.init_db()

print("=== DEV ТЕСТ на версии " + TEST_VERSION + " ===\n")

# === 1. Проверка LIKE escape ===
print("1. LIKE escape тест")
with db.get_db_connection() as conn:
    q = "bpy.ops.mesh"
    safe, esc = db._escape_like(q)
    rows = conn.execute(
        "SELECT COUNT(*) as cnt FROM symbols WHERE name LIKE ? ESCAPE ? AND version = ?",
        ("%" + safe, esc, TEST_VERSION),
    ).fetchone()["cnt"]
    print(
        "   '"
        + q
        + "' -> safe='"
        + safe
        + "', esc='"
        + esc
        + "' -> "
        + str(rows)
        + " results"
    )

    q = "bpy.ops.mesh%"
    safe, esc = db._escape_like(q)
    rows = conn.execute(
        f"SELECT COUNT(*) as cnt FROM symbols WHERE name LIKE ? ESCAPE ? AND version = ?",
        (f"%{safe}%", esc, TEST_VERSION),
    ).fetchone()["cnt"]
    print(
        f"   '{q}' -> safe='{safe}' -> {rows} results (должно быть 0 — % экранирован)"
    )

# === 2. Проверка поиска ===
print("\n2. Поиск (с очисткой кэша)")
with db.get_db_connection() as conn:
    conn.execute("DELETE FROM search_cache")
    conn.commit()

tests = [
    ("primitive_circle_add", 1),
    ("bpy.ops.mesh", 3),
    ("select_circle", 3),
    ("bpy.types.Scene", 2),
    ("add", 5),
]

all_ok = True
for query, expected_min in tests:
    r = db.search_symbols(query, TEST_VERSION if TEST_VERSION != "all" else None, 10)
    status = "✅" if len(r) >= expected_min else "❌"
    if len(r) < expected_min:
        all_ok = False
    print(f"   {status} '{query}' -> {len(r)} (min {expected_min})")

# === 3. Проверка get_symbol_detail ===
print("\n3. get_symbol_detail")
detail = db.get_symbol_detail("bpy.ops.mesh.primitive_circle_add", TEST_VERSION)
if detail:
    print(f"   ✅ description: {detail['description'][:60]}...")
    print(f"   ✅ params: {len(detail.get('params', []))}")
    print(f"   ✅ defaults: {len(detail.get('defaults', {}))}")
else:
    print(f"   ❌ not found")
    all_ok = False

# === 4. Проверка exact match (case-insensitive) ===
print("\n4. Exact match (case-insensitive)")
cases = [
    "bpy.ops.mesh.primitive_circle_add",
    "Bpy.OPS.Mesh.Primitive_Circle_Add",
]
for q in cases:
    with db.get_db_connection() as conn:
        rows = conn.execute(
            "SELECT COUNT(*) as cnt FROM symbols WHERE LOWER(name) = ? AND version = ?",
            (q.lower(), TEST_VERSION),
        ).fetchone()["cnt"]
        status = "✅" if rows > 0 else "❌"
        print(f"   {status} LOWER(name) = '{q.lower()}' -> {rows}")

# === 5. Проверка кэша ===
print("\n5. Кэш")
r = db.search_symbols("primitive_circle_add", TEST_VERSION, 5)
print(f"   Запрос 1: {len(r)} результатов")
r = db.search_symbols("primitive_circle_add", TEST_VERSION, 5)
print(f"   Запрос 2 (из кэша): {len(r)} результатов")
with db.get_db_connection() as conn:
    cnt = conn.execute("SELECT COUNT(*) as n FROM search_cache").fetchone()["n"]
    print(f"   Записей в кэше: {cnt}")

# === 6. Проверка TTL кэша (автоматическая очистка) ===
print("\n6. Cache TTL и LIMIT")
stats = db.get_cache_stats()
print(f"   Всего записей: {stats.get('total_entries', 0)}")
print(f"   Всего хитов: {stats.get('total_hits', 0)}")

# === 7. Проверка FTS5 ===
print("\n7. FTS5 полнотекстовый поиск")
fts_results = db.fts5_search(
    "add_circle", TEST_VERSION if TEST_VERSION != "all" else None, 10
)
print(f"   FTS 'add_circle': {len(fts_results)} результатов")
if fts_results:
    print(f"   ✅ {fts_results[0]['name']}: {fts_results[0]['description'][:50]}")

# === 8. Проверка category search ===
print("\n8. Category search")
import business_logic as bl

# search_operators с конкретной версией (баг: resolve_version возвращал None)
ops = bl.search_operators("primitive_circle_add", TEST_VERSION, 5)
status = "✅" if len(ops) > 0 else "❌"
if len(ops) == 0:
    all_ok = False
print(f"   {status} search_operators('primitive_circle_add', '{TEST_VERSION}'): {len(ops)}")
if len(ops) > 0:
    print(f"      → {ops[0]['name']}")

# search_operators с latest (резолв в самую новую версию)
ops_latest = bl.search_operators("primitive_circle_add", "latest", 5)
print(f"   search_operators('primitive_circle_add', 'latest'): {len(ops_latest)}")

types = bl.search_types("bpy.types.Scene", TEST_VERSION, 20)
status = "✅" if len(types) > 0 else "❌"
if len(types) == 0:
    all_ok = False
print(f"   {status} search_types('bpy.types.Scene', '{TEST_VERSION}'): {len(types)}")
if len(types) > 0:
    print(f"      → {types[0]['name']}")

# search_operators по всем версиям ('all')
ops_all = bl.search_operators("primitive_circle_add", "all", 5)
print(f"   search_operators('primitive_circle_add', 'all'): {len(ops_all)}")

# === 9. Проверка diff_versions ===
print("\n9. diff_versions")
if TEST_VERSION != "3_6":
    other = "4_5" if TEST_VERSION == "5_1" else "5_1"
    diff = bl.diff_versions("bpy.ops.mesh.primitive_circle_add", TEST_VERSION, other)
    if "error" in diff:
        print(f"   ❌ {diff['error']}")
        all_ok = False
    else:
        print(f"   ✅ {TEST_VERSION}: {diff['version_a']['description'][:40]}...")
        print(f"   ✅ {other}: {diff['version_b']['description'][:40]}...")
else:
    print(f"   ⏭️  пропускаем (нет второй версии для сравнения)")

# Итог
print(f"\n{'=' * 40}")
if all_ok:
    print(f"✅ DEV-ТЕСТ ПРОЙДЕН на {TEST_VERSION}")
else:
    print(f"❌ ЧТО-ТО НЕ РАБОТАЕТ на {TEST_VERSION}")
