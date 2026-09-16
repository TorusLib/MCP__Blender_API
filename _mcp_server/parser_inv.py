"""
Parser for Sphinx objects.inv files.
Reads the binary inventory and extracts symbol metadata.
"""

import zlib
from dataclasses import dataclass
from pathlib import Path

from config import inv_path


@dataclass
class SymbolEntry:
    """Single entry from objects.inv"""

    domain: str  # "py", "std", etc.
    role: str  # "func", "class", "mod", etc.
    priority: int  # -1 to 5
    name: str  # full name like "bpy.ops.mesh.add_circle"
    uri: str  # page filename like "bpy.ops.mesh.html"
    display_name: str  # same as name usually

    @property
    def module(self) -> str:
        """Extract module path: bpy.ops.mesh from bpy.ops.mesh.add_circle"""
        parts = self.name.split(".")
        if len(parts) >= 3:
            return ".".join(parts[:-1])
        return self.name

    @property
    def symbol_name(self) -> str:
        """Extract symbol name: add_circle from bpy.ops.mesh.add_circle"""
        return self.name.rsplit(".", 1)[-1]


def parse_inv_file(inv_file_path: Path) -> list[SymbolEntry]:
    """Parse a Sphinx objects.inv file and return list of SymbolEntry."""
    entries = []

    with open(inv_file_path, "rb") as f:
        data = f.read()

    # Parse header: lines starting with '#'
    # After the last '#' line, binary zlib data begins
    i = 0
    while i < len(data):
        newline = data.find(b"\n", i)
        if newline == -1:
            break
        line = data[i:newline]
        if len(line) > 0 and line[0:1] == b"#":
            i = newline + 1
        else:
            break

    compressed_start = i
    compressed_data = data[compressed_start:]

    # Sphinx uses raw zlib compression (no wbits)
    try:
        uncompressed = zlib.decompress(compressed_data)
    except zlib.error:
        raise ValueError(f"Cannot decompress objects.inv: {inv_file_path}")

    text = uncompressed.decode("utf-8", errors="replace")

    # Parse each line
    # Format: name domain:role priority uri [description]
    # Example: GeometrySet py:class 1 bpy.types.GeometrySet.html#$ -
    # Example: bpy.ops.mesh.add_circle py:func -1 bpy.ops.mesh.html add_circle
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Split: name | domain:role | priority | uri | [description]
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue

        name = parts[0]
        domain_role = parts[1]

        # Parse domain:role
        colon_pos = domain_role.find(":")
        if colon_pos == -1:
            continue

        domain = domain_role[:colon_pos]
        role = domain_role[colon_pos + 1 :]

        # Priority
        try:
            priority = int(parts[2])
        except ValueError:
            priority = -1

        # URI (parts[3]) — strip fragment (#...#$) for file path matching
        uri = parts[3].split("#")[0]

        # Description (optional, parts[4])
        description = parts[4] if len(parts) > 4 else ""

        # Display name: first word of description, or name
        display_name = name
        if description and description != "-":
            display_name = description.split(None, 1)[0]

        entries.append(
            SymbolEntry(
                domain=domain,
                role=role,
                priority=priority,
                name=name,
                uri=uri,
                display_name=display_name,
            )
        )

    return entries


def get_all_symbols(version: str) -> list[dict]:
    """Parse objects.inv and return list of symbol dicts for indexing."""
    path = inv_path(version)

    if not path.exists():
        print(f"  [WARN] No objects.inv for version {version}")
        return []

    entries = parse_inv_file(path)
    print(f"  [OK] Parsed {len(entries)} entries from {path}")

    result = []
    for entry in entries:
        result.append(
            {
                "domain": entry.domain,
                "role": entry.role,
                "priority": entry.priority,
                "name": entry.name,
                "uri": entry.uri,
                "display_name": entry.display_name,
                "module": entry.module,
                "symbol_name": entry.symbol_name,
                "version": version,
            }
        )

    return result
