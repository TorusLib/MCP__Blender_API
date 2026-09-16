"""
HTTP API Server for Blender API Documentation (FastAPI).
Для WebUI и любых HTTP-клиентов.

Запуск:
    python api_server.py              # REST на :18723
    python api_server.py --host 0.0.0.0 --port 8080

Endpoints:
    REST:
        GET /api/search?q=...&version=all&limit=20
        GET /api/symbol?name=bpy.ops.mesh.add_circle&version=latest
        GET /api/module?module=bpy.ops.mesh&version=latest&limit=100
        GET /api/page?uri=bpy.ops.mesh.html&version=latest
        GET /api/versions
        GET /api/stats
        GET /api/cache-stats
        POST /api/cache/clear
        GET /api/operators?q=...&version=latest&limit=20
        GET /api/types?q=...&version=latest&limit=20
        GET /api/properties?q=...&version=latest&limit=20
        GET /api/diff?symbol=...&v1=5_1&v2=4_5
"""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import business_logic as bl
import database as db
from config import HTTP_HOST, HTTP_PORT
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize DB on startup."""
    print("Initializing Blender API Documentation HTTP Server...")
    db.init_db()
    versions = db.get_versions()
    if versions:
        print(f"Found {len(versions)} indexed versions: {', '.join(versions)}")
    else:
        print("No indexed versions found. Run: python indexer.py")
    yield
    print("HTTP Server stopped.")


app = FastAPI(
    title="Blender API Docs",
    description="REST API for Blender Python API Documentation (3.6, 4.5, 5.1)",
    version="0.3.2",
    lifespan=lifespan,
)

# CORS — чтобы WebUI с любого origin мог обращаться
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── REST Endpoints ───────────────────────────────────────────────────────────


@app.get("/api/health")
async def health() -> dict:
    """Health check."""
    return {"status": "ok", "transport": "http"}


@app.get("/api/search")
async def api_search(
    q: str = Query(..., description="Search query"),
    version: Optional[str] = Query(
        "all", description="Version: 3_6, 4_5, 5_1, latest, or all"
    ),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
) -> list[dict]:
    """Search for symbols by name/module."""
    results = db.search_symbols(q, bl.search_scope_version(version), limit)
    return results


@app.get("/api/symbol")
async def api_symbol(
    name: str = Query(..., description="Symbol name, e.g. bpy.ops.mesh.add_circle"),
    version: str = Query("latest", description="Version: 3_6, 4_5, 5_1, latest"),
) -> dict | list[dict] | None:
    """Get detailed info about a symbol."""
    result = bl.get_symbol_detail(name, version)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol not found: {name} (version: {version})",
        )
    return result


@app.get("/api/module")
async def api_module(
    module: str = Query(..., description="Module, e.g. bpy.ops.mesh"),
    version: str = Query("latest", description="Version"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
) -> list[dict]:
    """List all symbols in a module."""
    return bl.search_by_module(module, version, limit)


@app.get("/api/page")
async def api_page(
    uri: str = Query(..., description="HTML URI, e.g. bpy.ops.mesh.html"),
    version: str = Query("latest", description="Version"),
) -> list[dict]:
    """Get all symbols from a specific HTML page."""
    return bl.get_page_content(uri, bl.resolve_version(version) or version)


@app.get("/api/versions")
async def api_versions() -> list[str]:
    """Get list of indexed versions."""
    return db.get_versions()


@app.get("/api/stats")
async def api_stats() -> dict:
    """Get database statistics."""
    return db.get_stats()


@app.get("/api/cache-stats")
async def api_cache_stats() -> dict:
    """Get search cache statistics."""
    return db.get_cache_stats()


@app.post("/api/cache/clear")
async def api_clear_cache() -> dict:
    """Clear search cache."""
    db.clear_search_cache()
    return {"status": "ok", "message": "Cache cleared"}


@app.get("/api/operators")
async def api_operators(
    q: str = Query(..., description="Search query"),
    version: str = Query("latest", description="Version"),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
) -> list[dict]:
    """Search bpy.ops.* operators."""
    return bl.search_operators(q, version, limit)


@app.get("/api/types")
async def api_types(
    q: str = Query(..., description="Search query"),
    version: str = Query("latest", description="Version"),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
) -> list[dict]:
    """Search bpy.types.* types."""
    return bl.search_types(q, version, limit)


@app.get("/api/properties")
async def api_properties(
    q: str = Query(..., description="Search query"),
    version: str = Query("latest", description="Version"),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
) -> list[dict]:
    """Search bpy.props.* properties."""
    return bl.search_properties(q, version, limit)


@app.get("/api/diff")
async def api_diff(
    symbol: str = Query(..., description="Symbol name"),
    v1: str = Query(..., description="First version, e.g. 5_1"),
    v2: str = Query(..., description="Second version, e.g. 4_5"),
) -> dict:
    """Compare symbol across two versions."""
    return bl.diff_versions(symbol, v1, v2)


# ─── CLI Entry Point ──────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Blender API Docs HTTP Server")
    parser.add_argument(
        "--host", default=HTTP_HOST, help=f"Bind address (default: {HTTP_HOST})"
    )
    parser.add_argument(
        "--port", type=int, default=HTTP_PORT, help=f"Bind port (default: {HTTP_PORT})"
    )
    args = parser.parse_args()

    print(f"Starting HTTP API server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
