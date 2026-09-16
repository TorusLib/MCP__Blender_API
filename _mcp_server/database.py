"""
SQLite database layer for Blender API documentation.
Stores symbols, their metadata, and parsed content.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from config import DB_PATH

# ─── Search cache настройки ──────────────────────────────────────────────
CACHE_TTL_SECONDS = 600  # 10 минут
CACHE_MAX_ENTRIES = 500

# ─── Утилиты ──────────────────────────────────────────────────────────────


def _escape_like(value: str) -> tuple[str, str]:
    """Escape special LIKE characters (% and _) in user input.

    Escapes the escape char itself first, then % and _.

    Returns:
        (escaped_value, escape_char) - tuple for use with ESCAPE clause
    """
    escaped = value.replace("|", "||").replace("%", "|%").replace("_", "|_")
    return escaped, "|"


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row to dict."""
    return dict(row)


def _symbols_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    """Convert list of sqlite3.Row to list of dict with standard keys."""
    return [
        {
            "name": r["name"],
            "module": r["module"],
            "symbol_name": r["symbol_name"],
            "role": r["role"],
            "domain": r["domain"],
            "priority": r["priority"],
            "uri": r["uri"],
            "display_name": r["display_name"],
            "version": r["version"],
            "has_content": r["has_content"],
        }
        for r in rows
    ]


@contextmanager
def get_db_connection(db_path: Optional[Path] = None):
    """Context manager for safe database connections.
    Ensures connection is always closed, even on exceptions.
    """
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    # PRAGMA foreign_keys не нужен — в схеме нет FOREIGN KEY
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize the database schema."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Symbols table: from objects.inv (metadata only)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                name TEXT NOT NULL,
                module TEXT NOT NULL,
                symbol_name TEXT NOT NULL,
                role TEXT NOT NULL,
                domain TEXT NOT NULL,
                priority INTEGER NOT NULL,
                uri TEXT NOT NULL,
                display_name TEXT NOT NULL,
                version TEXT NOT NULL,
                has_content INTEGER DEFAULT 0,
                PRIMARY KEY (name, version)
            )
        """)

        # Content table: parsed HTML content (detailed info)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                params TEXT,
                defaults TEXT,
                has_params INTEGER DEFAULT 0,
                version TEXT NOT NULL,
                PRIMARY KEY (id, version)
            )
        """)

        # Indexes for fast lookup
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbols_module ON symbols(module)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbols_role ON symbols(role)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbols_version ON symbols(version)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(symbol_name)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_id ON content(id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_version ON content(version)"
        )

        # FTS5 virtual table for full-text search
        # Columns: name, description, version — simple, no external content
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS content_fts
            USING fts5(name, description, version)
        """)

        # Populating FTS5 must be done externally (e.g., fix_fts.py or indexer)
        # because FTS5 doesn't support triggers with simple column layout.

        # File hashes table for incremental indexing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_hashes (
                version TEXT NOT NULL,
                filename TEXT NOT NULL,
                md5hash TEXT NOT NULL,
                modified_at REAL NOT NULL,
                PRIMARY KEY (version, filename)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_hashes_version ON file_hashes(version)"
        )

        # Search cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query TEXT NOT NULL,
                version TEXT NOT NULL,
                cache_key TEXT NOT NULL,
                results TEXT NOT NULL,
                created_at REAL NOT NULL,
                hits INTEGER DEFAULT 1,
                PRIMARY KEY (query, version, cache_key)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_search_cache_key ON search_cache(cache_key)"
        )


def insert_symbols(symbols: list[dict]) -> None:
    """Insert symbols from objects.inv into the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Batch insert — executemany быстрее построчного
        batch = [
            (
                sym["name"],
                sym["module"],
                sym["symbol_name"],
                sym["role"],
                sym["domain"],
                sym["priority"],
                sym["uri"],
                sym["display_name"],
                sym["version"],
            )
            for sym in symbols
        ]
        cursor.executemany(
            """
            INSERT OR REPLACE INTO symbols
            (name, module, symbol_name, role, domain, priority, uri, display_name, version, has_content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
            batch,
        )


def insert_enum_symbols(enum_symbols: list[dict], version: str) -> None:
    """Вставить enum-символы из bpy_types_enum_items/ в таблицу symbols."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        batch = [
            (
                sym["name"],
                "bpy.types.enum_items",
                sym["short_name"],
                "data",  # role
                "py",
                0,
                f"bpy_types_enum_items/{sym['short_name'].lower()}.html",
                sym["short_name"],
                version,
            )
            for sym in enum_symbols
        ]
        cursor.executemany(
            """
            INSERT OR REPLACE INTO symbols
            (name, module, symbol_name, role, domain, priority, uri, display_name, version, has_content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
            batch,
        )


def insert_content(symbols_content: dict, version: str):
    """Insert parsed HTML content into the database and FTS5."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Batch insert — по 500 элементов (лимит SQLite 999 плейсхолдеров)
        batch = []
        all_ids = []

        for sym_id, data in symbols_content.items():
            # Store all symbols with a description (not empty/placeholder text)
            desc = data.get("description", "")
            if not desc or desc in (sym_id, data.get("name", "")):
                continue

            params_json = json.dumps(data.get("params", []), ensure_ascii=False)
            defaults_json = json.dumps(data.get("defaults", {}), ensure_ascii=False)
            has_params = 1 if data.get("has_params", False) else 0
            batch.append(
                (
                    sym_id,
                    data["name"],
                    data["description"],
                    params_json,
                    defaults_json,
                    has_params,
                    version,
                )
            )
            all_ids.append(sym_id)

            if len(batch) >= 500:
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO content
                    (id, name, description, params, defaults, has_params, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    batch,
                )
                batch = []

        # Оставшиеся элементы
        if batch:
            cursor.executemany(
                """
                INSERT OR REPLACE INTO content
                (id, name, description, params, defaults, has_params, version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                batch,
            )

        # Update has_content flag in symbols table — батчим по 500,
        # с учётом версии (символ мог существовать в других версиях)
        for i in range(0, len(all_ids), 500):
            chunk = all_ids[i : i + 500]
            placeholders = ",".join(["?" for _ in chunk])
            cursor.execute(
                f"""
                UPDATE symbols SET has_content = 1
                WHERE name IN ({placeholders}) AND version = ?
            """,
                (*chunk, version),
            )


def update_has_content_flag(db_path: Optional[Path] = None):
    """Mark symbols as having content in the database."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE symbols SET has_content = 1
            WHERE name || ',' || version IN (
                SELECT id || ',' || version FROM content
            )
        """)


def search_symbols(
    query: str, version: Optional[str] = None, limit: int = 50, use_cache: bool = True
) -> list[dict]:
    """Search symbols by name/module (with optional cache)."""
    # Escape LIKE special chars and normalize
    query_safe, escape_char = _escape_like(query.lower().strip())
    # Exact match uses original (case-insensitive)
    query_exact = query.lower()

    # Create cache key early (needed for both cache check and save)
    cache_key = make_cache_key(query, version or "all", limit)

    # Check cache first
    if use_cache:
        cached = get_cached_result(cache_key)
        if cached is not None:
            return cached

    # Unified query with optional version filter
    sql = f"""
        SELECT name, module, symbol_name, role, domain, priority, uri,
               display_name, version, has_content
        FROM symbols
        WHERE (name LIKE ? ESCAPE ? OR symbol_name LIKE ? ESCAPE ? OR
               module LIKE ? ESCAPE ? OR display_name LIKE ? ESCAPE ?)
          AND (? IS NULL OR version = ?)
        ORDER BY
            CASE
                WHEN LOWER(name) = ? THEN 1
                WHEN name LIKE ? THEN 2
                WHEN symbol_name LIKE ? THEN 3
                ELSE 4
            END,
            priority DESC
        LIMIT ?
    """

    with get_db_connection() as conn:
        rows = conn.execute(
            sql,
            (
                f"%{query_safe}%",
                escape_char,
                f"%{query_safe}%",
                escape_char,
                f"%{query_safe}%",
                escape_char,
                f"%{query_safe}%",
                escape_char,
                version,
                version,
                query_exact,
                f"{query_safe}%",
                f"%{query_safe}%",
                limit,
            ),
        ).fetchall()

        results = _symbols_to_list(rows)

        # Save to cache
        if use_cache:
            save_search_result(cache_key, query, version or "all", results)

        return results


def get_symbol_detail(name: str, version: str) -> dict | None:
    """Get detailed content for a specific symbol."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, description, params, defaults, has_params
            FROM content
            WHERE id = ? AND version = ?
        """,
            (name, version),
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "params": json.loads(row["params"]) if row["params"] else [],
            "defaults": json.loads(row["defaults"]) if row["defaults"] else {},
            "has_params": row["has_params"],
        }


def list_symbols_by_module(module: str, version: Optional[str] = None) -> list[dict]:
    """List all symbols in a module."""
    sql = """
        SELECT name, module, symbol_name, role, domain, priority, uri,
               display_name, version, has_content
        FROM symbols
        WHERE module LIKE ? AND (? IS NULL OR version = ?)
        ORDER BY name
    """

    with get_db_connection() as conn:
        rows = conn.execute(sql, (f"{module}%", version, version)).fetchall()
        return _symbols_to_list(rows)


def get_versions() -> list[str]:
    """Get list of all available versions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT version FROM symbols ORDER BY version")
        return [row["version"] for row in cursor.fetchall()]


def get_stats() -> dict:
    """Get database statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) as cnt FROM symbols")
        stats["total_symbols"] = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM content")
        stats["total_content"] = cursor.fetchone()["cnt"]

        cursor.execute("SELECT version, COUNT(*) as cnt FROM symbols GROUP BY version")
        stats["by_version"] = {row["version"]: row["cnt"] for row in cursor.fetchall()}

        cursor.execute(
            "SELECT role, COUNT(*) as cnt FROM symbols GROUP BY role ORDER BY cnt DESC"
        )
        stats["by_role"] = {row["role"]: row["cnt"] for row in cursor.fetchall()}

        return stats


def get_stale_files(version: str, file_hashes: dict) -> list[str]:
    """
    Get list of HTML files that changed since last indexing.

    Args:
        version: Blender version (e.g., '5_1')
        file_hashes: dict {filename: current_md5hash}

    Returns:
        list of filenames that need re-indexing
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT filename, md5hash FROM file_hashes WHERE version = ?",
            (version,),
        )
        old_hashes = {row["filename"]: row["md5hash"] for row in cursor.fetchall()}

        stale = []
        for filename, new_hash in file_hashes.items():
            old_hash = old_hashes.get(filename)
            if old_hash != new_hash:
                stale.append(filename)

        return stale


def save_file_hashes(version: str, file_hashes: dict):
    """Save current file hashes for incremental comparison."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        for filename, md5hash in file_hashes.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO file_hashes (version, filename, md5hash, modified_at)
                VALUES (?, ?, ?, ?)
            """,
                (version, filename, md5hash, time.time()),
            )


# ─── Поиск с кэшированием ─────────────────────────────────────────────────────


def make_cache_key(query: str, version: str, limit: int) -> str:
    """Create a deterministic cache key from search parameters."""
    query_normalized = query.lower().strip()
    return f"{query_normalized}|{version}|{limit}"


def get_cached_result(cache_key: str) -> list[dict] | None:
    """Get cached search result. Returns None if not cached."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT results FROM search_cache WHERE cache_key = ?",
            (cache_key,),
        )
        row = cursor.fetchone()

        if row:
            # Increment hits counter in same transaction
            conn.execute(
                "UPDATE search_cache SET hits = hits + 1 WHERE cache_key = ?",
                (cache_key,),
            )
            return json.loads(row["results"])

        return None


def save_search_result(cache_key: str, query: str, version: str, results: list):
    """Cache search result."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO search_cache (query, version, cache_key, results, created_at, hits)
            VALUES (?, ?, ?, ?, ?, 1)
        """,
            (
                query,
                version,
                cache_key,
                json.dumps(results, ensure_ascii=False),
                time.time(),
            ),
        )

    # Автоочистка кеша после сохранения
    _cleanup_cache()


def get_cache_stats() -> dict:
    """Get search cache statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as cnt FROM search_cache")
        total = cursor.fetchone()["cnt"]

        cursor.execute("SELECT SUM(hits) as total_hits FROM search_cache")
        total_hits = cursor.fetchone()["total_hits"] or 0

        cursor.execute(
            "SELECT query, version, hits FROM search_cache ORDER BY hits DESC LIMIT 10"
        )
        top = [
            {"query": r["query"], "version": r["version"], "hits": r["hits"]}
            for r in cursor.fetchall()
        ]

        return {"total_entries": total, "total_hits": total_hits, "top_queries": top}


def _cleanup_cache():
    """Очистка просроченных и лишних записей кеша. Вызывается после save_search_result."""
    now = time.time()
    cutoff = now - CACHE_TTL_SECONDS

    with get_db_connection() as conn:
        # Удаляем просроченные
        conn.execute(
            "DELETE FROM search_cache WHERE created_at < ?",
            (cutoff,),
        )
        # Если всё ещё больше лимита — удаляем самые старые
        excess = conn.execute("SELECT COUNT(*) as cnt FROM search_cache").fetchone()[
            "cnt"
        ]
        if excess > CACHE_MAX_ENTRIES:
            to_remove = excess - CACHE_MAX_ENTRIES
            conn.execute(
                "DELETE FROM search_cache WHERE rowid IN "
                "(SELECT rowid FROM search_cache ORDER BY created_at ASC LIMIT ?)",
                (to_remove,),
            )


def clear_search_cache():
    """Clear all cached search results."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM search_cache")


# ─── FTS5 полнотекстовый поиск ─────────────────────────────────────────────────


def fts5_search(
    query: str, version: Optional[str] = None, limit: int = 50
) -> list[dict]:
    """
    Full-text search using FTS5 virtual table.
    Searches in name + description.

    Args:
        query: Search query (FTS5 syntax)
        version: Optional version filter
        limit: Max results

    Returns:
        List of matching symbols ranked by relevance
    """
    query_normalized = query.lower().strip()

    with get_db_connection() as conn:
        # Use JOIN to avoid N+1: fetch from FTS5 and content in one query
        if version:
            cursor = conn.execute(
                """
                SELECT content.id, content.name, content.description, content.params, content.defaults, content.has_params
                FROM content_fts
                JOIN content ON content_fts.name = content.id AND content_fts.version = content.version
                WHERE content_fts.version = ? AND content_fts MATCH ?
                ORDER BY content_fts.rank
                LIMIT ?
            """,
                (version, query_normalized, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT content.id, content.name, content.description, content.params, content.defaults, content.has_params
                FROM content_fts
                JOIN content ON content_fts.name = content.id AND content_fts.version = content.version
                WHERE content_fts MATCH ?
                ORDER BY content_fts.rank
                LIMIT ?
            """,
                (query_normalized, limit),
            )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "params": json.loads(row["params"]) if row["params"] else [],
                    "defaults": json.loads(row["defaults"]) if row["defaults"] else {},
                    "has_params": row["has_params"],
                }
            )

        return results
