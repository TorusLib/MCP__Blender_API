"""
Глобальные пути проекта. Все пути относительные от корня проекта,
не от диска. Модули импортируют сюда и не думают о filesystem.

Структура:
  root/
  ├── BD_BASE/
  │   └── blender_api.db
  ├── API_DOC/
  │   ├── 3_6/
  │   ├── 4_5/
  │   └── 5_1/
  └── _mcp_server/
      ├── config.py       # <-- ты тут
      ├── server.py
      ├── database.py
      ├── indexer.py
      ├── parser_html.py
      └── parser_inv.py
"""

from pathlib import Path

# ─── Корень проекта (один раз вычисляем отсюда) ───────────────────────────────
# _mcp_server/config.py → parent = _mcp_server → parent = root
ROOT = Path(__file__).resolve().parent.parent

# ─── Пути к данным (относительно ROOT) ────────────────────────────────────────
DB_PATH = ROOT / "BD_BASE" / "blender_api.db"
API_DOC_DIR = ROOT / "API_DOC"

# ─── HTTP Server defaults ─────────────────────────────────────────────────────
HTTP_HOST = "127.0.0.1"
HTTP_PORT = 18723


# ─── Хелперы для получения пути к версии ──────────────────────────────────────
def version_dir(version: str) -> Path:
    """Путь к папке версии: API_DOC/3_6, API_DOC/4_5, и т.д."""
    return API_DOC_DIR / version


def inv_path(version: str) -> Path:
    """Путь к objects.inv для версии."""
    return API_DOC_DIR / version / "objects.inv"
