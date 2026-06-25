"""Host-side data import, canonical archive, reindex, and preview verification."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncpg

from canonical_data import (
    ensure_runtime_dirs,
    read_canonical_records,
    runtime_root,
    upsert_canonical_records,
    write_error,
)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def infer_effects_gifs_dir(json_path: Path) -> Path:
    candidates = [
        json_path.parent.parent / "gifs",
        json_path.parent / "gifs",
        project_root() / "runtime_data" / "effect" / "gifs",
    ]
    return next((p for p in candidates if p.exists()), candidates[0])


def infer_icons_pngs_dir(json_path: Path) -> Path:
    candidates = [
        json_path.parent / "pngs",
        json_path.parent.parent / "pngs",
        project_root() / "runtime_data" / "ui" / "pngs",
        project_root() / "icon_png_results" / "pngs",
    ]
    return next((p for p in candidates if p.exists()), candidates[0])


def infer_models_pngs_dir(json_path: Path) -> Path:
    candidates = [
        json_path.parent / "pngs",
        json_path.parent.parent / "pngs",
        project_root() / "runtime_data" / "model" / "previews",
        project_root() / "model" / "merged" / "pngs",
    ]
    return next((p for p in candidates if p.exists()), candidates[0])


def infer_animator_gifs_dir(json_path: Path) -> Path:
    candidates = [
        json_path.parent / "gifs",
        json_path.parent.parent / "gifs",
        project_root() / "runtime_data" / "animator" / "previews",
        project_root() / "animator" / "gifs",
    ]
    return next((p for p in candidates if p.exists()), candidates[0])


def normalize_tags(tags) -> dict:
    if isinstance(tags, dict):
        return tags
    if isinstance(tags, str) and tags.strip():
        try:
            value = json.loads(tags)
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def manifest_resource_paths(json_path: Path, module_type: int) -> set[str]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    resources = data.get("resources", []) if isinstance(data, dict) else data
    paths: set[str] = set()
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        result = resource.get("result", {}) or {}
        if module_type == 2:
            if result.get("status") != "ok":
                continue
            resource_path = resource.get("resource_id")
        else:
            status = result.get("status", "")
            if isinstance(status, str) and status.startswith("error"):
                continue
            resource_path = resource.get("source_path") or resource.get("resource_id")
        if resource_path:
            paths.add(str(resource_path))
    return paths


async def delete_stale_assets_for_manifest(
    pool: asyncpg.Pool,
    module_type: int,
    json_path: Path,
    *,
    apply: bool,
) -> dict:
    keep_paths = manifest_resource_paths(json_path, module_type)
    if not keep_paths:
        print(f"Stale delete skipped for module {module_type}: manifest has no importable resources.")
        return {"module_type": module_type, "kept": 0, "stale": 0, "deleted": 0, "samples": []}

    async with pool.acquire() as conn:
        stale_rows = await conn.fetch(
            """SELECT id, resource_path, thumbnail_path
               FROM assets
               WHERE module_type = $1
                 AND NOT (resource_path = ANY($2::text[]))
               ORDER BY resource_path""",
            module_type,
            sorted(keep_paths),
        )
        stale_ids = [row["id"] for row in stale_rows]
        deleted = 0
        if apply and stale_ids:
            await conn.execute(
                "DELETE FROM assets WHERE id = ANY($1::int[])",
                stale_ids,
            )
            deleted = len(stale_ids)

    samples = [row["resource_path"] for row in stale_rows[:10]]
    mode = "APPLY" if apply else "DRY-RUN"
    print(
        f"Stale delete {mode}: module={module_type}, "
        f"kept={len(keep_paths)}, stale={len(stale_rows)}, deleted={deleted}"
    )
    if samples:
        print(f"Stale delete samples: {samples}")
    return {
        "module_type": module_type,
        "kept": len(keep_paths),
        "stale": len(stale_rows),
        "deleted": deleted,
        "samples": samples,
    }


async def archive_assets_from_db(pool: asyncpg.Pool, module_types: tuple[int, ...]) -> int:
    root = project_root()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT module_type, name, resource_path, thumbnail_path, tags
               FROM assets
               WHERE module_type = ANY($1::int[])
               ORDER BY module_type, resource_path""",
            list(module_types),
        )
    by_module: dict[int, list[dict]] = {}
    for row in rows:
        module_type = int(row["module_type"])
        by_module.setdefault(module_type, []).append(
            {
                "module_type": int(row["module_type"]),
                "name": row["name"],
                "resource_path": row["resource_path"],
                "thumbnail_path": row["thumbnail_path"],
                "tags": normalize_tags(row["tags"]),
            }
        )
    for records in by_module.values():
        upsert_canonical_records(root, records)
    return len(rows)


async def run_model_import(json_path: str, pool: asyncpg.Pool):
    from app.importers.model_importer import import_models_json
    from app.importers.tag_initializer import sync_model_tag_values

    result = await import_models_json(
        json_path,
        str(infer_models_pngs_dir(Path(json_path))),
        pool,
        project_root=str(project_root()),
    )
    await sync_model_tag_values(pool)
    await archive_assets_from_db(pool, (1,))
    print_import_summary("Model", json_path, result)
    return result


async def run_effects_import(json_path: str, pool: asyncpg.Pool, previews_dir: str):
    from app.importers.effects_importer import import_effects_json
    from app.importers.tag_initializer import sync_effect_tag_values

    result = await import_effects_json(
        json_path,
        str(infer_effects_gifs_dir(Path(json_path))),
        pool,
        previews_dir,
        project_root=str(project_root()),
    )
    await sync_effect_tag_values(pool)
    print_import_summary("Effects", json_path, result)
    return result


async def run_animator_import(json_path: str, pool: asyncpg.Pool):
    from app.importers.animator_importer import import_animator_json
    from app.importers.tag_initializer import sync_animator_tag_values

    result = await import_animator_json(
        json_path,
        str(infer_animator_gifs_dir(Path(json_path))),
        pool,
        project_root=str(project_root()),
    )
    await sync_animator_tag_values(pool)
    await archive_assets_from_db(pool, (3,))
    print_import_summary("Animator", json_path, result)
    return result


async def run_icons_import(json_path: str, pool: asyncpg.Pool):
    from app.importers.icon_importer import import_icons_json
    from app.importers.tag_initializer import sync_icon_tag_values

    result = await import_icons_json(
        json_path,
        pool,
        project_root=str(project_root()),
        icons_source_dir=str(infer_icons_pngs_dir(Path(json_path))),
    )
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


def load_admin_key(explicit: str | None) -> str:
    if explicit:
        return explicit
    env_path = project_root() / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("ADMIN_API_KEY="):
                return line.split("=", 1)[1].strip()
    return "dev-admin-key-change-in-prod"


async def call_reindex(admin_key: str, backend_url: str = "http://localhost"):
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


async def restore_from_canonical(pool: asyncpg.Pool) -> dict:
    root = project_root()
    records = read_canonical_records(root)
    stats = {"success": 0, "failed": 0, "skipped": 0, "es_sync_failed": 0}
    async with pool.acquire() as conn:
        for record in records:
            try:
                await conn.fetchrow(
                    """INSERT INTO assets
                           (module_type, name, resource_path, thumbnail_path, tags)
                       VALUES ($1, $2, $3, $4, $5::jsonb)
                       ON CONFLICT (module_type, resource_path)
                       DO UPDATE SET tags = $5::jsonb,
                                     thumbnail_path = COALESCE($4, assets.thumbnail_path),
                                     updated_at = NOW()
                       RETURNING id""",
                    int(record["module_type"]),
                    record.get("name") or Path(record["resource_path"]).stem,
                    record["resource_path"],
                    record.get("thumbnail_path"),
                    json.dumps(record.get("tags") or {}, ensure_ascii=False),
                )
                stats["success"] += 1
            except Exception as exc:
                stats["failed"] += 1
                write_error(
                    root,
                    "canonical",
                    "restore",
                    "upsert_db",
                    exc,
                    module_type=record.get("module_type"),
                    resource_path=record.get("resource_path"),
                )
    print_import_summary("Canonical", str(runtime_root(root)), stats)
    return stats


def preview_url(module_type: int, thumbnail_path: str) -> str:
    if module_type == 2:
        return f"/data/gifs/{thumbnail_path}"
    if module_type == 4:
        return f"/data/icons/{thumbnail_path}"
    return f"/static/previews/{thumbnail_path}"


async def verify_previews(pool: asyncpg.Pool, backend_url: str, sample_size: int) -> dict:
    root = project_root()
    stats = {"checked": 0, "failed": 0}
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT module_type, resource_path, thumbnail_path
               FROM assets
               WHERE thumbnail_path IS NOT NULL AND thumbnail_path != ''
               ORDER BY random()
               LIMIT $1""",
            sample_size,
        )
    for row in rows:
        stats["checked"] += 1
        url = backend_url.rstrip("/") + preview_url(int(row["module_type"]), row["thumbnail_path"])
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    raise RuntimeError(f"HTTP {resp.status}")
        except Exception as exc:
            stats["failed"] += 1
            write_error(
                root,
                "preview",
                "verify",
                "verify_preview",
                exc,
                module_type=int(row["module_type"]),
                resource_path=row["resource_path"],
                thumbnail_path=row["thumbnail_path"],
                url=url,
            )
    print(f"Preview verify summary: checked={stats['checked']}, failed={stats['failed']}")
    if stats["failed"]:
        sys.exit(1)
    return stats


async def main():
    parser = argparse.ArgumentParser(description="Import data into biaoqian platform")
    parser.add_argument("--models-json", help="Path to model JSON file")
    parser.add_argument("--animator-json", help="Path to animator JSON file")
    parser.add_argument("--effects-json", help="Path to effects JSON file")
    parser.add_argument("--icons-json", help="Path to icon JSON file")
    parser.add_argument("--from-canonical", action="store_true", help="Restore DB rows from runtime_data JSONL")
    parser.add_argument(
        "--delete-stale",
        action="store_true",
        help="Compare provided JSON files and report DB assets missing from them",
    )
    parser.add_argument(
        "--apply-delete-stale",
        action="store_true",
        help="Actually delete stale DB assets. Must be used with --delete-stale.",
    )
    parser.add_argument("--reindex", action="store_true", help="Trigger ES reindex after import")
    parser.add_argument("--verify-previews", action="store_true", help="Verify random preview URLs")
    parser.add_argument("--verify-sample-size", type=int, default=10)
    parser.add_argument("--pg-url", default="postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao")
    parser.add_argument("--admin-key", default=None, help="Admin API key (reads from .env if not provided)")
    parser.add_argument("--backend-url", default="http://localhost", help="Backend URL for API calls")
    args = parser.parse_args()

    if not any(
        [
            args.models_json,
            args.animator_json,
            args.effects_json,
            args.icons_json,
            args.from_canonical,
            args.delete_stale,
            args.reindex,
            args.verify_previews,
        ]
    ):
        parser.print_help()
        sys.exit(1)
    if args.apply_delete_stale and not args.delete_stale:
        print("Error: --apply-delete-stale requires --delete-stale.", file=sys.stderr)
        sys.exit(1)

    admin_key = load_admin_key(args.admin_key)
    if not admin_key or admin_key == "dev-admin-key-change-in-prod":
        print(
            "WARNING: ADMIN_API_KEY is using default value! "
            "Set a secure key in .env for shared deployments.",
            file=sys.stderr,
        )

    root = project_root()
    ensure_runtime_dirs(root)
    previews_dir = str(root / "runtime_data")

    for source, label in [
        (args.models_json, "Model JSON"),
        (args.animator_json, "Animator JSON"),
        (args.effects_json, "Effects JSON"),
        (args.icons_json, "Icons JSON"),
    ]:
        if source and not Path(source).exists():
            print(f"Error: {label} file not found: {source}", file=sys.stderr)
            sys.exit(1)

    needs_db = any(
        [
            args.models_json,
            args.animator_json,
            args.effects_json,
            args.icons_json,
            args.from_canonical,
            args.delete_stale,
            args.verify_previews,
        ]
    )
    pool = await asyncpg.create_pool(args.pg_url) if needs_db else None
    try:
        should_import = not args.delete_stale

        if should_import and args.models_json:
            await run_model_import(args.models_json, pool)
        if should_import and args.animator_json:
            await run_animator_import(args.animator_json, pool)
        if should_import and args.effects_json:
            await run_effects_import(args.effects_json, pool, previews_dir)
        if should_import and args.icons_json:
            await run_icons_import(args.icons_json, pool)
        if args.from_canonical:
            await restore_from_canonical(pool)

        if args.delete_stale:
            delete_targets = [
                (args.models_json, 1),
                (args.effects_json, 2),
                (args.animator_json, 3),
                (args.icons_json, 4),
            ]
            if not any(source for source, _module_type in delete_targets):
                print(
                    "Error: --delete-stale requires at least one module JSON file.",
                    file=sys.stderr,
                )
                sys.exit(1)
            for source, module_type in delete_targets:
                if source:
                    await delete_stale_assets_for_manifest(
                        pool,
                        module_type,
                        Path(source),
                        apply=args.apply_delete_stale,
                    )

        if args.reindex:
            await call_reindex(admin_key, args.backend_url)
            await call_refresh_dict(admin_key, args.backend_url)

        if args.verify_previews:
            await verify_previews(pool, args.backend_url, args.verify_sample_size)
    finally:
        if pool:
            await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
