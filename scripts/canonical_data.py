"""Canonical runtime data helpers for imports and recovery."""
from __future__ import annotations

import json
import shutil
import time
import traceback
from pathlib import Path
from typing import Any


MODULE_NAMES = {
    1: "model",
    2: "effect",
    3: "animator",
    4: "ui",
}


def runtime_root(project_root: Path) -> Path:
    return project_root / "runtime_data"


def module_dir(project_root: Path, module_type: int) -> Path:
    return runtime_root(project_root) / MODULE_NAMES[module_type]


def preview_dir(project_root: Path, module_type: int) -> Path:
    if module_type == 2:
        return module_dir(project_root, module_type) / "gifs"
    if module_type == 4:
        return module_dir(project_root, module_type) / "pngs"
    return runtime_root(project_root) / "previews"


def canonical_jsonl_path(project_root: Path, module_type: int) -> Path:
    return module_dir(project_root, module_type) / "data.jsonl"


def import_log_path(project_root: Path, module_name: str, batch_id: str) -> Path:
    return runtime_root(project_root) / "logs" / "imports" / f"{batch_id}_{module_name}_errors.jsonl"


def ensure_runtime_dirs(project_root: Path) -> None:
    migrate_legacy_runtime_dirs(project_root)
    for module_type in MODULE_NAMES:
        preview_dir(project_root, module_type).mkdir(parents=True, exist_ok=True)
        canonical_jsonl_path(project_root, module_type).parent.mkdir(parents=True, exist_ok=True)
    (runtime_root(project_root) / "logs" / "imports").mkdir(parents=True, exist_ok=True)


def migrate_legacy_runtime_dirs(project_root: Path) -> None:
    root = runtime_root(project_root)
    for old_name, new_name in [("action", "animator"), ("icon", "ui")]:
        old_path = root / old_name
        new_path = root / new_name
        if old_path.exists() and not new_path.exists():
            shutil.copytree(old_path, new_path)


def normalize_rel_path(path: str | None, strip_prefixes: tuple[str, ...] = ()) -> str | None:
    if not path:
        return None
    rel = str(path).replace("\\", "/").lstrip("/")
    for prefix in strip_prefixes:
        clean_prefix = prefix.replace("\\", "/").strip("/")
        if rel == clean_prefix:
            return None
        if rel.startswith(f"{clean_prefix}/"):
            rel = rel[len(clean_prefix) + 1 :]
            break
    return rel or None


def write_error(
    project_root: Path,
    module_name: str,
    batch_id: str,
    stage: str,
    error: BaseException | str,
    **context: Any,
) -> None:
    log_path = import_log_path(project_root, module_name, batch_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(error, BaseException):
        err_text = f"{type(error).__name__}: {error}"
        trace = traceback.format_exc()
    else:
        err_text = str(error)
        trace = None
    payload = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "module": module_name,
        "stage": stage,
        "error": err_text,
        **context,
    }
    if trace and trace != "NoneType: None\n":
        payload["traceback"] = trace
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def copy_preview(
    source_root: Path,
    rel_path: str | None,
    target_root: Path,
    *,
    project_root: Path,
    module_name: str,
    batch_id: str,
    context: dict[str, Any] | None = None,
) -> bool:
    if not rel_path:
        return False
    context = context or {}
    source = source_root / Path(rel_path)
    target = target_root / Path(rel_path)
    try:
        if not source.exists():
            raise FileNotFoundError(str(source))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return True
    except Exception as exc:
        write_error(
            project_root,
            module_name,
            batch_id,
            "copy_preview",
            exc,
            source_file=str(source),
            target_file=str(target),
            thumbnail_path=rel_path,
            **context,
        )
        return False


def _merge_tags(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    merged = dict(old or {})
    for key, value in (new or {}).items():
        if value is None or value == "":
            continue
        existing = merged.get(key)
        if isinstance(existing, list) or isinstance(value, list):
            values = []
            for item in (existing if isinstance(existing, list) else [existing] if existing is not None else []):
                if item not in values:
                    values.append(item)
            for item in (value if isinstance(value, list) else [value]):
                if item not in values:
                    values.append(item)
            merged[key] = values
        else:
            merged[key] = value
    return merged


def upsert_canonical_record(project_root: Path, record: dict[str, Any]) -> None:
    upsert_canonical_records(project_root, [record])


def upsert_canonical_records(project_root: Path, new_records: list[dict[str, Any]]) -> None:
    if not new_records:
        return
    module_types = {int(record["module_type"]) for record in new_records}
    if len(module_types) != 1:
        raise ValueError("Canonical batch must contain one module_type")
    module_type = module_types.pop()
    path = canonical_jsonl_path(project_root, module_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    records: dict[tuple[int, str], dict[str, Any]] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                records[(int(item["module_type"]), item["resource_path"])] = item

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for record in new_records:
        key = (module_type, record["resource_path"])
        old = records.get(key, {})
        merged = {
            **old,
            **{k: v for k, v in record.items() if v is not None and k != "tags"},
            "module_type": module_type,
            "resource_path": record["resource_path"],
            "tags": _merge_tags(old.get("tags", {}), record.get("tags", {})),
            "updated_at": now,
        }
        if not merged.get("created_at"):
            merged["created_at"] = merged["updated_at"]
        records[key] = merged

    with path.open("w", encoding="utf-8") as f:
        for item in sorted(records.values(), key=lambda x: x["resource_path"]):
            f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")


def read_canonical_records(project_root: Path, module_type: int | None = None) -> list[dict[str, Any]]:
    module_types = [module_type] if module_type else list(MODULE_NAMES)
    records: list[dict[str, Any]] = []
    for mod in module_types:
        path = canonical_jsonl_path(project_root, mod)
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    return records
