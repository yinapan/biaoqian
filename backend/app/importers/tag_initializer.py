# backend/app/importers/tag_initializer.py
import openpyxl
import asyncpg

COLUMN_MAP = {
    "物种": "species", "性别": "gender", "地域": "region",
    "势力": "faction", "职业": "profession", "体型": "body_type",
    "年龄": "age_group", "衣着": "clothing", "特征": "features",
    "专属NPC": "exclusive_npc",
}

SKIP_SHEETS = {"通用规则", "进度统计", "动作模组", "需要新增的动作",
               "特效标签", "问题模型记录区", "WpsReserved_CellImgList"}


async def extract_enum_values_from_excel(
    filepath: str, pool: asyncpg.Pool
) -> dict[str, list[str]]:
    """从 Excel 第 2 行（枚举行）提取各维度可选值，补充写入 tag_values"""
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    all_values: dict[str, set[str]] = {}

    for sheet_name in wb.sheetnames:
        if sheet_name in SKIP_SHEETS:
            continue
        ws = wb[sheet_name]
        headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        enum_row = list(ws.iter_rows(min_row=2, max_row=2, values_only=True))[0]

        for col_idx, header in enumerate(headers):
            if not header or header not in COLUMN_MAP:
                continue
            field_name = COLUMN_MAP[header]
            cell_val = enum_row[col_idx] if col_idx < len(enum_row) else None
            if not cell_val:
                continue
            values = {v.strip() for v in str(cell_val).split("\n") if v.strip()}
            all_values.setdefault(field_name, set()).update(values)

    wb.close()

    async with pool.acquire() as conn:
        for field_name, values in all_values.items():
            def_id = await conn.fetchval(
                "SELECT id FROM tag_definitions WHERE module_type=1 AND field_name=$1",
                field_name,
            )
            if not def_id:
                continue
            for i, val in enumerate(sorted(values)):
                await conn.execute(
                    """INSERT INTO tag_values (definition_id, value, sort_order)
                       VALUES ($1, $2, $3)
                       ON CONFLICT (definition_id, value) DO NOTHING""",
                    def_id, val, i,
                )

    return {k: sorted(v) for k, v in all_values.items()}
