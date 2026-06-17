"""
Host-side data import script.
Connects directly to PostgreSQL at localhost:5432 (requires PG port exposed).
Usage: python scripts/import_data.py [--excel PATH] [--effects-json PATH] [--reindex]
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import asyncpg


async def run_excel_import(excel_path: str, pool: asyncpg.Pool):
    from app.importers.excel_importer import import_excel
    result = await import_excel(excel_path, pool, "previews")
    print(f"Excel import done: {result}")
    return result


async def run_effects_import(json_path: str, pool: asyncpg.Pool):
    from app.importers.effects_importer import import_effects_json
    result = await import_effects_json(json_path, "特效/merged/gifs", pool, "previews")
    print(f"Effects import done: {result}")
    return result


async def call_reindex(admin_key: str, backend_url: str = "http://localhost"):
    import urllib.request
    import json
    req = urllib.request.Request(
        f"{backend_url}/api/v1/admin/reindex-es",
        method="POST",
        headers={"X-Admin-Key": admin_key},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read())
    print(f"Reindex done: {result}")
    return result


async def call_refresh_dict(admin_key: str, backend_url: str = "http://localhost"):
    import urllib.request
    import json
    req = urllib.request.Request(
        f"{backend_url}/api/v1/admin/refresh-dictionary",
        method="POST",
        headers={"X-Admin-Key": admin_key},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    print(f"Dictionary refresh done: {result}")
    return result


async def main():
    parser = argparse.ArgumentParser(description="Import data into biaoqiao platform")
    parser.add_argument("--excel", help="Path to Excel file (资源标签对照表.xlsx)")
    parser.add_argument("--effects-json", help="Path to effects JSON file")
    parser.add_argument("--reindex", action="store_true", help="Trigger ES reindex after import")
    parser.add_argument("--pg-url", default="postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao")
    parser.add_argument("--admin-key", default=None, help="Admin API key (reads from .env if not provided)")
    parser.add_argument("--backend-url", default="http://localhost", help="Backend URL for API calls")
    args = parser.parse_args()

    if not args.excel and not args.effects_json and not args.reindex:
        parser.print_help()
        sys.exit(1)

    admin_key = args.admin_key
    if not admin_key:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ADMIN_API_KEY="):
                    admin_key = line.split("=", 1)[1].strip()
                    break
        if not admin_key:
            admin_key = "dev-admin-key-change-in-prod"

    pool = None
    if args.excel or args.effects_json:
        pool = await asyncpg.create_pool(args.pg_url)
    try:
        if args.excel:
            await run_excel_import(args.excel, pool)
        if args.effects_json:
            await run_effects_import(args.effects_json, pool)
    finally:
        if pool:
            await pool.close()

    if args.reindex:
        await call_reindex(admin_key, args.backend_url)
        await call_refresh_dict(admin_key, args.backend_url)


if __name__ == "__main__":
    asyncio.run(main())
