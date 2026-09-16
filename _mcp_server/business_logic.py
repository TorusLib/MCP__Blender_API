"""
Common business logic for Blender API Documentation.
Shared by both MCP (stdio) and HTTP (REST/SSE) transports.

Этот модуль НЕ зависит от MCP или HTTP — только от database.py.
"""

from __future__ import annotations

from functools import lru_cache

import database as db


@lru_cache(maxsize=1)
def _cached_versions() -> tuple[str, ...]:
    """Cached list of indexed versions (avoids per-request DB scan).

    Invalidated automatically when the server restarts; reindexing runs in
    a separate process, so start the server again after adding a version.
    """
    return tuple(db.get_versions())


# ─── Version helpers ──────────────────────────────────────────────────────────


def resolve_version(version: str) -> str | None:
    """Resolve a version parameter to a concrete version string.

    Returns:
        'latest'/'*'/'all-versions' → newest version like '5_1',
        'all' → None (caller searches all versions),
        concrete version like '3_6' → itself.
    """
    if version in ("latest", "*", "all-versions"):
        versions = _cached_versions()
        if not versions:
            return None
        return versions[-1]  # last = newest
    if version == "all":
        return None
    return version


def search_scope_version(version: str) -> str | None:
    """Normalize a version param for DB search calls.

    'all', '*' and 'all-versions' → None (all versions).
    Anything else → resolved concrete version (or itself).
    """
    if version in ("all", "*", "all-versions"):
        return None
    return resolve_version(version)


def get_symbol_detail(name: str, version: str) -> dict | list[dict] | None:
    """Get detailed content for a specific symbol, resolving 'latest'/'all'."""
    # Multi-version lookup
    if version.lower() in ("all", "*", "all-versions"):
        versions = db.get_versions()
        if not versions:
            return None
        all_results = []
        for v in versions:
            detail = db.get_symbol_detail(name, v)
            if detail:
                result = dict(detail)
                result["version"] = v
                all_results.append(result)
        return all_results if all_results else None

    # Resolve 'latest'
    if version == "latest":
        versions = db.get_versions()
        if not versions:
            return None
        version = versions[-1]

    detail = db.get_symbol_detail(name, version)
    if not detail:
        return None

    result = dict(detail)
    result["version"] = version
    return result


# ─── Search ───────────────────────────────────────────────────────────────────


def search_by_module(
    module: str, version: str | None = None, limit: int = 100
) -> list[dict]:
    """List all symbols in a module (resolves 'latest'/'all')."""
    v = None
    if version is not None:
        v = search_scope_version(version)
    results = db.list_symbols_by_module(module, v)
    return results[:limit]


def get_page_content(uri: str, version: str) -> list[dict]:
    """Get all symbols from a specific HTML page."""
    from parser_html import get_full_page_content

    return get_full_page_content(version, uri)


# ─── Category-specific search ────────────────────────────────────────────────


def _search_by_prefix(search: str, version: str, prefix: str, limit: int) -> list[dict]:
    """Generic search filtered by module prefix."""
    v = search_scope_version(version)
    results = db.search_symbols(search, v, limit * 3)
    return [r for r in results if r.get("module", "").startswith(prefix)]


def search_operators(
    search: str, version: str = "latest", limit: int = 20
) -> list[dict]:
    """Search specifically for Blender operators (bpy.ops.*)."""
    return _search_by_prefix(search, version, "bpy.ops", limit)


def search_types(search: str, version: str = "latest", limit: int = 20) -> list[dict]:
    """Search specifically for Blender types (bpy.types.*)."""
    return _search_by_prefix(search, version, "bpy.types", limit)


def search_properties(
    search: str, version: str = "latest", limit: int = 20
) -> list[dict]:
    """Search for Blender properties (bpy.props.*)."""
    return _search_by_prefix(search, version, "bpy.props", limit)


# ─── Version comparison ──────────────────────────────────────────────────────


def diff_versions(symbol_name: str, version_a: str, version_b: str) -> dict:
    """Compare a symbol across two Blender versions."""
    detail_a = db.get_symbol_detail(symbol_name, version_a)
    detail_b = db.get_symbol_detail(symbol_name, version_b)

    if not detail_a and not detail_b:
        return {"error": f"Symbol not found in either version: {symbol_name}"}

    def _serialize(detail: dict | None) -> dict:
        if not detail:
            return {
                "found": False,
                "description": "",
                "params_count": 0,
                "defaults": {},
            }
        return {
            "found": True,
            "description": detail.get("description", ""),
            "params_count": len(detail.get("params", [])),
            "defaults": detail.get("defaults", {}),
        }

    return {
        "symbol": symbol_name,
        "version_a": {"version": version_a, **_serialize(detail_a)},
        "version_b": {"version": version_b, **_serialize(detail_b)},  # noqa: F841
    }


# ─── Metadata ────────────────────────────────────────────────────────────────
