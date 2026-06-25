import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from canonical_data import canonical_jsonl_path, ensure_runtime_dirs, upsert_canonical_records


def test_upsert_canonical_records_merges_existing_rows(tmp_path):
    upsert_canonical_records(
        tmp_path,
        [
            {
                "module_type": 4,
                "name": "QuestItem",
                "resource_path": "mui/Resource/icon/System/quest/QuestItem.png",
                "thumbnail_path": "System/quest/QuestItem.png",
                "tags": {"color": ["blue"]},
            }
        ],
    )
    upsert_canonical_records(
        tmp_path,
        [
            {
                "module_type": 4,
                "name": "QuestItem",
                "resource_path": "mui/Resource/icon/System/quest/QuestItem.png",
                "thumbnail_path": "System/quest/QuestItem.png",
                "tags": {"color": ["blue", "green"], "semantic": ["quest"]},
            },
            {
                "module_type": 4,
                "name": "Mail",
                "resource_path": "mui/Resource/icon/System/mail/Mail.png",
                "thumbnail_path": "System/mail/Mail.png",
                "tags": {"semantic": ["mail"]},
            },
        ],
    )

    rows = [
        json.loads(line)
        for line in canonical_jsonl_path(tmp_path, 4).read_text(encoding="utf-8").splitlines()
    ]

    assert len(rows) == 2
    quest = next(row for row in rows if row["name"] == "QuestItem")
    assert quest["tags"]["color"] == ["blue", "green"]
    assert quest["tags"]["semantic"] == ["quest"]


def test_ensure_runtime_dirs_copies_legacy_icon_and_action_dirs(tmp_path):
    (tmp_path / "runtime_data" / "icon" / "pngs").mkdir(parents=True)
    (tmp_path / "runtime_data" / "icon" / "pngs" / "a.png").write_bytes(b"png")
    (tmp_path / "runtime_data" / "action").mkdir(parents=True)
    (tmp_path / "runtime_data" / "action" / "data.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "runtime_data" / "previews").mkdir(parents=True)
    (tmp_path / "runtime_data" / "previews" / "model.png").write_bytes(b"model")

    ensure_runtime_dirs(tmp_path)

    assert (tmp_path / "runtime_data" / "ui" / "pngs" / "a.png").exists()
    assert (tmp_path / "runtime_data" / "animator" / "data.jsonl").exists()
    assert (tmp_path / "runtime_data" / "model" / "previews" / "model.png").exists()
    assert (tmp_path / "runtime_data" / "animator" / "previews").exists()
    assert (tmp_path / "runtime_data" / "icon" / "pngs" / "a.png").exists()
