"""从 dev 环境采样 ~50 条/模块，重生成 fixture JSON。

季度执行流程：
1. 确认 dev 环境已 reindex
2. 跑本脚本：python scripts/sample_real_data.py
3. 人工 review 生成的 fixture
4. 提 PR 更新 fixture
"""
import asyncio
import json
import os
import random
from pathlib import Path
import asyncpg

OUTPUT_DIR = Path(__file__).parent.parent / "tests/e2e/fixtures"
MODULES = [
    (1, "models", "model"),
    (2, "animator", "animator"),
    (3, "effects", "effect"),
    (4, "icons", "icon"),
]
SAMPLE_SIZE = 50

async def sample_module(conn, module_type, output_name, table_name):
    rows = await conn.fetch(f"SELECT * FROM {table_name} ORDER BY random() LIMIT $1", SAMPLE_SIZE)
    # scrub 掉无关字段
    out = []
    for r in rows:
        item = dict(r)
        # 删除内部字段
        for k in list(item.keys()):
            if k.startswith("_") or k in ("created_at", "updated_at"):
                del item[k]
        out.append(item)
    out_path = OUTPUT_DIR / f"{output_name}.fixture.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(out)} rows to {out_path}")

async def main():
    db_url = os.environ.get("DATABASE_URL", "postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao")
    conn = await asyncpg.connect(db_url)
    for module_type, output_name, table_name in MODULES:
        await sample_module(conn, module_type, output_name, table_name)
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
