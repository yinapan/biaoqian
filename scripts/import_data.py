"""
Host-side data import script.
Connects directly to PostgreSQL at localhost:5432 (requires PG port exposed).
Usage: python scripts/import_data.py [--excel PATH] [--effects-json PATH] [--icons-json PATH] [--reindex]
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import asyncpg


async def run_excel_import(excel_path: str, pool: asyncpg.Pool, previews_dir: str):
    from app.importers.excel_importer import import_excel
    from app.importers.tag_initializer import extract_enum_values_from_excel
    result = await import_excel(excel_path, pool, previews_dir)
    await extract_enum_values_from_excel(excel_path, pool)
    print_import_summary("Excel", excel_path, result)
    return result


async def run_effects_import(json_path: str, pool: asyncpg.Pool, previews_dir: str):
    from app.importers.effects_importer import import_effects_json
    from app.importers.tag_initializer import sync_effect_tag_values
    result = await import_effects_json(json_path, "特效/gifs", pool, previews_dir)
    await sync_effect_tag_values(pool)
    print_import_summary("Effects", json_path, result)
    return result


async def run_icons_import(json_path: str, pool: asyncpg.Pool):
    from app.importers.icon_importer import import_icons_json
    from app.importers.tag_initializer import sync_icon_tag_values
    result = await import_icons_json(json_path, pool)
    await sync_icon_tag_values(pool)
    print_import_summary("Icons", json_path, result)
    return result


def print_import_summary(label: str, source_path: str, result: dict):
    total_processed = (
        int(result.get("success", 0))
        + int(result.get("skipped", 0))
        + int(result.get("failed", 0))
    )
    print(f"{label} source: {source_path}")
    print(
        f"{label} summary: total_processed={total_processed}, "
        f"success={result.get('success', 0)}, "
        f"skipped={result.get('skipped', 0)}, "
        f"failed={result.get('failed', 0)}, "
        f"es_sync_failed={result.get('es_sync_failed', 0)}"
    )
    if result.get("errors"):
        print(f"{label} first_errors={result['errors'][:3]}")


async def call_reindex(admin_key: str, backend_url: str = "http://localhost"):
    import urllib.request
    import json
    req = urllib.request.Request(
        f"{backend_url}/api/v1/admin/reindex-es",
        method="POST",
        headers={"X-Admin-Key": admin_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())
        print(f"Reindex done: {result}")
        return result
    except Exception as e:
        print(f"Error calling reindex API: {e}", file=sys.stderr)
        print(f"Is the backend running at {backend_url}?", file=sys.stderr)
        sys.exit(1)


async def call_refresh_dict(admin_key: str, backend_url: str = "http://localhost"):
    import urllib.request
    import json
    req = urllib.request.Request(
        f"{backend_url}/api/v1/admin/refresh-dictionary",
        method="POST",
        headers={"X-Admin-Key": admin_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        print(f"Dictionary refresh done: {result}")
        return result
    except Exception as e:
        print(f"Error calling refresh-dictionary API: {e}", file=sys.stderr)
        print(f"Is the backend running at {backend_url}?", file=sys.stderr)
        sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(description="Import data into biaoqiao platform")
    parser.add_argument("--excel", help="Path to Excel file (资源标签对照表.xlsx)")
    parser.add_argument("--effects-json", help="Path to effects JSON file")
    parser.add_argument("--icons-json", help="Path to icon JSON file")
    parser.add_argument("--reindex", action="store_true", help="Trigger ES reindex after import")
    parser.add_argument("--pg-url", default="postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao")
    parser.add_argument("--admin-key", default=None, help="Admin API key (reads from .env if not provided)")
    parser.add_argument("--backend-url", default="http://localhost", help="Backend URL for API calls")
    args = parser.parse_args()

    if not args.excel and not args.effects_json and not args.icons_json and not args.reindex:
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
    if not admin_key or admin_key == "dev-admin-key-change-in-prod":
        print("WARNING: ADMIN_API_KEY is using default value! "
              "Set a secure key in .env for shared deployments.", file=sys.stderr)

    project_root = Path(__file__).resolve().parent.parent
    previews_dir = str(project_root / "previews")

    if args.excel and not Path(args.excel).exists():
        print(f"Error: Excel file not found: {args.excel}", file=sys.stderr)
        sys.exit(1)
    if args.effects_json and not Path(args.effects_json).exists():
        print(f"Error: Effects JSON file not found: {args.effects_json}", file=sys.stderr)
        sys.exit(1)
    if args.icons_json and not Path(args.icons_json).exists():
        print(f"Error: Icons JSON file not found: {args.icons_json}", file=sys.stderr)
        sys.exit(1)

    pool = None
    if args.excel or args.effects_json or args.icons_json:
        pool = await asyncpg.create_pool(args.pg_url)
    try:
        if args.excel:
            await run_excel_import(args.excel, pool, previews_dir)
        if args.effects_json:
            await run_effects_import(args.effects_json, pool, previews_dir)
        if args.icons_json:
            await run_icons_import(args.icons_json, pool)
    finally:
        if pool:
            await pool.close()

    if args.reindex:
        await call_reindex(admin_key, args.backend_url)
        await call_refresh_dict(admin_key, args.backend_url)


if __name__ == "__main__":
    asyncio.run(main())
