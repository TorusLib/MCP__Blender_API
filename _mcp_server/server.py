"""
MCP Server for Blender API Documentation.
Provides search, lookup, and browsing tools for Blender Python API docs.

Usage:
    python server.py                    # starts server
    python server.py --transport stdio  # stdio mode (default for MCP clients)
"""

import business_logic as bl
import database as db
from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP(
    "blender-api-docs",
    instructions="Blender Python API Documentation Server. Search and browse Blender API symbols, types, operators, and properties across multiple versions.",
)


# ─── Core Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
async def search_symbol(
    query: str, version: str = "all", limit: int = 20
) -> list[dict]:
    """
    Search for a Blender API symbol by name, module, or partial match.
    Example: search_symbol("add_circle"), search_symbol("bpy.ops.mesh"), search_symbol("Scene")
    """
    return db.search_symbols(query, bl.search_scope_version(version), limit)


@mcp.tool()
async def get_symbol_details(
    name: str, version: str = "latest"
) -> dict | list[dict] | None:
    """
    Get detailed information about a symbol including parameters and defaults.
    Example: get_symbol_details("bpy.ops.mesh.add_circle")

    If version="all", returns details from every indexed version.
    """
    result = bl.get_symbol_detail(name, version)
    if result is None:
        return {"error": f"Symbol not found: {name} (version: {version})"}
    return result


@mcp.tool()
async def list_module(
    module: str, version: str = "all", limit: int = 100
) -> list[dict]:
    """
    List all symbols in a Blender API module.
    Example: list_module("bpy.ops.mesh"), list_module("bpy.types")
    """
    return bl.search_by_module(module, version, limit)


@mcp.tool()
async def get_page_content(uri: str, version: str = "latest") -> list[dict]:
    """
    Get all symbols from a specific HTML page.
    Example: get_page_content("bpy.ops.mesh.html"), get_page_content("bpy.types.Scene.html")
    """
    if version == "latest":
        versions = db.get_versions()
        if not versions:
            return []
        version = versions[-1]

    return bl.get_page_content(uri, version)


@mcp.tool()
async def get_versions() -> list[str]:
    """Get list of all indexed Blender API versions."""
    return db.get_versions()


@mcp.tool()
async def get_stats() -> dict:
    """Get database statistics - how many symbols, versions, breakdown by role."""
    return db.get_stats()


# ─── Category-Specific Search ─────────────────────────────────────────────────


@mcp.tool()
async def search_operators(
    search: str, version: str = "latest", limit: int = 20
) -> list[dict]:
    """
    Search specifically for Blender operators (bpy.ops.*).
    Example: search_operators("add circle"), search_operators("subdivide")
    """
    return bl.search_operators(search, version, limit)


@mcp.tool()
async def search_types(
    search: str, version: str = "latest", limit: int = 20
) -> list[dict]:
    """
    Search specifically for Blender types (bpy.types.*).
    Example: search_types("Scene"), search_types("Mesh")
    """
    return bl.search_types(search, version, limit)


@mcp.tool()
async def search_properties(
    search: str, version: str = "latest", limit: int = 20
) -> list[dict]:
    """
    Search for Blender properties (bpy.props.*).
    Example: search_properties("StringProperty"), search_properties("IntProperty")
    """
    return bl.search_properties(search, version, limit)


# ─── Version Comparison ───────────────────────────────────────────────────────


@mcp.tool()
async def diff_versions(symbol_name: str, version_a: str, version_b: str) -> dict:
    """
    Compare a symbol across two Blender versions to see what changed.
    Example: diff_versions("bpy.ops.mesh.add_circle", "5_1", "4_5")
    """
    return bl.diff_versions(symbol_name, version_a, version_b)


# ─── Initialization ───────────────────────────────────────────────────────────


def main():
    """Initialize DB and start the MCP server."""
    try:
        print("Initializing Blender API Documentation MCP Server...", flush=True)
        db.init_db()

        versions = db.get_versions()
        if versions:
            print(
                f"Found {len(versions)} indexed versions: {', '.join(versions)}",
                flush=True,
            )
        else:
            print("No indexed versions found. Run: python indexer.py", flush=True)

        print("Server ready. Press Ctrl+C to stop.", flush=True)
        mcp.run()
    except Exception as e:
        import traceback

        print(f"\n[ERROR] Server failed to start: {e}", flush=True)
        traceback.print_exc()
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
