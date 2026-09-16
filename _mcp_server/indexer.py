"""
Indexer: orchestrates parsing of all Blender API documentation versions.

Supports incremental indexing — only re-parses changed HTML files.

Usage:
    python indexer.py                  # auto-detect versions from API_DOC/
    python indexer.py 3_6 4_5 5_1      # specific versions only
    python indexer.py --force          # force full re-index
"""

import os
import sys
import time

import database as db
from config import API_DOC_DIR
from parser_html import parse_all_html
from parser_inv import get_all_symbols
from utils import compute_md5


def populate_fts(version: str, html_content: dict) -> int:
    """Populate FTS5 search index with parsed content."""
    with db.get_db_connection() as conn:
        cursor = conn.cursor()

        # Batch insert
        batch = []
        for sym_id, data in html_content.items():
            desc = data.get("description", "")
            if not desc or desc in (sym_id, data.get("name", "")):
                continue
            name = data.get("name", sym_id)
            batch.append((name, desc, version))

        if batch:
            cursor.executemany(
                "INSERT OR REPLACE INTO content_fts (name, description, version) VALUES (?, ?, ?)",
                batch,
            )
            # Optimize FTS5
            cursor.execute("INSERT INTO content_fts(content_fts) VALUES('optimize')")

        return len(batch)


def collect_file_hashes(version):
    """Collect MD5 hashes for all HTML files in a version directory."""
    version_dir = API_DOC_DIR / version
    if not version_dir.is_dir():
        return {}

    hashes = {}
    for fname in os.listdir(version_dir):
        if fname.endswith(".html"):
            fpath = version_dir / fname
            hashes[fname] = compute_md5(fpath)
    return hashes


def index_version(version: str, force: bool = False) -> None:
    """Index a single Blender version (with incremental support)."""
    print(f"\n{'=' * 60}")
    print(f"Indexing version: {version}")
    print(f"{'=' * 60}")

    version_dir = API_DOC_DIR / version
    if not version_dir.is_dir():
        print(f"  [ERROR] Version directory not found: {version_dir}")
        return

    # Step 1: Parse objects.inv
    print("\n[Step 1/4] Parsing objects.inv...")
    start = time.time()
    symbols = get_all_symbols(version)
    inv_time = time.time() - start

    if not symbols:
        print(f"  [SKIP] No symbols found for {version}")
        return

    print(f"  Found {len(symbols)} symbols ({inv_time:.1f}s)")

    # Ensure DB schema is up to date
    db.init_db()

    # Step 2: Collect HTML file hashes
    print("\n[Step 2/4] Collecting HTML file hashes...")
    file_hashes = collect_file_hashes(version)
    print(f"  Found {len(file_hashes)} HTML files")

    # Step 3: Check for changes (incremental)
    if not force:
        print("\n[Step 3/4] Checking for changes...")
        stale_files = db.get_stale_files(version, file_hashes)

        if not stale_files:
            print("  [SKIP] No HTML files changed. Already up to date.")
            print(f"  [DONE] {version} is current ({inv_time:.1f}s)")
            return

        print(f"  Changed: {len(stale_files)} files out of {len(file_hashes)}")

        # Filter symbols to only those whose HTML files changed
        changed_uris = set(stale_files)
        changed_symbols = [s for s in symbols if s["uri"] in changed_uris]

        if not changed_symbols:
            print("  [SKIP] Changed files have no matching symbols.")
            print(f"  [DONE] {version} is current ({inv_time:.1f}s)")
            return

        print(f"  [UPDATE] {len(changed_symbols)} symbols to update")
    else:
        stale_files = list(file_hashes.keys())
        changed_symbols = symbols
        print("\n[Step 3/4] Force mode — full re-index")

    # Step 4: Parse HTML and insert
    print("\n[Step 4/4] Parsing HTML and updating database...")
    start = time.time()

    # Build symbols dict for parse_all_html
    symbols_dict = {s["name"]: s for s in changed_symbols}
    html_content, enum_symbols = parse_all_html(version, list(symbols_dict.values()))
    html_time = time.time() - start

    if html_content:
        db.insert_symbols(changed_symbols)
        # Вставляем enum-символы в таблицу symbols
        if enum_symbols:
            db.insert_enum_symbols(enum_symbols, version)
        db.insert_content(html_content, version)
        db.update_has_content_flag()
        print(f"  Updated {len(html_content)} entries ({html_time:.1f}s)")

        # Populate FTS5 for full-text search
        print("\n  [FTS5] Populating full-text search index...")
        start = time.time()
        fts_count = populate_fts(version, html_content)
        print(f"  [FTS5] {fts_count} entries indexed ({time.time() - start:.1f}s)")

    # Save file hashes for next comparison
    db.save_file_hashes(version, file_hashes)
    print("  Saved file hashes for next run")

    print(f"\n  [DONE] {version} processed in {inv_time + html_time:.1f}s total")


def show_stats():
    """Show database statistics."""
    db.init_db()
    stats = db.get_stats()
    versions = db.get_versions()

    print("\n" + "=" * 60)
    print("Blender API Documentation Index")
    print("=" * 60)
    print(f"\nVersions: {', '.join(versions) if versions else 'None'}")
    print(f"Total symbols: {stats.get('total_symbols', 0)}")
    print(f"Total detailed content: {stats.get('total_content', 0)}")

    print("\nBy version:")
    for v, c in stats.get("by_version", {}).items():
        print(f"  {v}: {c}")

    print("\nBy role:")
    for r, c in stats.get("by_role", {}).items():
        print(f"  {r}: {c}")

    print("=" * 60)


def main():
    # Parse arguments
    force = False
    versions_arg = []
    for arg in sys.argv[1:]:
        if arg == "--force":
            force = True
        else:
            versions_arg.append(arg)

    if versions_arg:
        # Index specific versions
        for v in versions_arg:
            index_version(v, force=force)
    else:
        # Auto-detect versions from API_DOC/ subfolder
        auto_versions = []
        if API_DOC_DIR.exists():
            for d in sorted(API_DOC_DIR.iterdir()):
                if d.is_dir() and (d / "objects.inv").exists():
                    auto_versions.append(d.name)

        if not auto_versions:
            print(f"[ERROR] No versions found in {API_DOC_DIR}")
            print("Specify versions: python indexer.py <version1> <version2> ...")
            sys.exit(1)

        print(f"Auto-detected versions: {', '.join(auto_versions)}")
        for v in auto_versions:
            index_version(v, force=force)

    show_stats()


if __name__ == "__main__":
    main()
