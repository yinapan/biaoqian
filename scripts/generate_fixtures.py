#!/usr/bin/env python3
"""Generate 4 fixture JSON files for integration tests.

Outputs:
  tests/e2e/fixtures/models.fixture.json      (~50 records)
  tests/e2e/fixtures/animator.fixture.json    (~30 records)
  tests/e2e/fixtures/effects.fixture.json     (~30 records)
  tests/e2e/fixtures/icons.fixture.json       (~40 records)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
FIXTURES_DIR = ROOT / "tests" / "e2e" / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

SVN_TEMPLATE = {
    "last_changed_revision": "1395001",
    "last_changed_author": "xiaomi-ai",
    "last_changed_date": "2024-05-10 15:30:25",
}

GENERATED_AT = "2026-06-27 10:00:00"


def svn(rev_offset: int = 0) -> dict:
    return {
        "last_changed_revision": str(1395001 + rev_offset),
        "last_changed_author": "xiaomi-ai",
        "last_changed_date": "2024-05-10 15:30:25",
    }


# ---------------------------------------------------------------------------
# Module 1 — models (~50 records)
# ---------------------------------------------------------------------------

def generate_models() -> dict:
    resources = []
    idx = 0

    species_values = ["人类", "精灵", "兽人", "魔族", "龙族"]
    gender_values = ["男性", "女性"]
    body_type_values = ["壮硕", "纤细", "标准"]
    region_values = ["中原", "西域", "北境", "南疆", "东海"]
    faction_values = ["正道", "邪道", "中立"]
    profession_values = ["剑客", "法师", "弓手", "战士", "刺客"]
    age_values = ["青年", "中年", "老年", "少年"]
    clothing_values = ["铠甲", "布衣", "长袍", "轻甲"]
    features_values = ["威严", "秀气", "魁梧", "苗条"]
    factions_npc = ["否", "是"]

    # Ensure full coverage of species × gender × body_type (5×2×3 = 30 combos)
    for species in species_values:
        for gender in gender_values:
            for body_type in body_type_values:
                idx += 1
                num = f"{idx:03d}"
                resources.append({
                    "resource_id": f"data/sources/model/pngs/m{num}.png",
                    "source_path": f"data/sources/model/pngs/m{num}.png",
                    "size_bytes": 51200 + idx * 512,
                    "svn": svn(idx),
                    "result": {
                        "status": "ok",
                        "png_rel_path": f"pngs/m{num}.png",
                        "tags": {
                            "物种": [species],
                            "性别": [gender],
                            "地域": [region_values[idx % len(region_values)]],
                            "势力": [faction_values[idx % len(faction_values)]],
                            "职业": [profession_values[idx % len(profession_values)]],
                            "体型": [body_type],
                            "年龄": [age_values[idx % len(age_values)]],
                            "衣着": [clothing_values[idx % len(clothing_values)]],
                            "特征": [features_values[idx % len(features_values)]],
                            "专属NPC": [factions_npc[idx % 2]],
                            "备注": [f"测试模型{num}"],
                        },
                    },
                })

    # Add 5 records WITH no png_rel_path (missing preview test case)
    for i in range(5):
        idx += 1
        num = f"{idx:03d}"
        resources.append({
            "resource_id": f"data/sources/model/pngs/m{num}_noprev.png",
            "source_path": f"data/sources/model/pngs/m{num}_noprev.png",
            "size_bytes": 40960,
            "svn": svn(idx),
            "result": {
                "status": "ok",
                # png_rel_path intentionally omitted
                "tags": {
                    "物种": [species_values[i % len(species_values)]],
                    "性别": [gender_values[i % 2]],
                    "体型": [body_type_values[i % 3]],
                    "备注": [f"无预览图测试{i + 1}"],
                },
            },
        })

    # Pad to ~50 records with varied data
    while len(resources) < 50:
        idx += 1
        num = f"{idx:03d}"
        sp = species_values[idx % len(species_values)]
        gd = gender_values[idx % 2]
        bt = body_type_values[idx % 3]
        resources.append({
            "resource_id": f"data/sources/model/pngs/m{num}_extra.png",
            "source_path": f"data/sources/model/pngs/m{num}_extra.png",
            "size_bytes": 49152 + idx * 128,
            "svn": svn(idx),
            "result": {
                "status": "ok",
                "png_rel_path": f"pngs/m{num}_extra.png",
                "tags": {
                    "物种": [sp],
                    "性别": [gd],
                    "地域": [region_values[idx % len(region_values)]],
                    "势力": [faction_values[idx % len(faction_values)]],
                    "职业": [profession_values[idx % len(profession_values)]],
                    "体型": [bt],
                    "年龄": [age_values[idx % len(age_values)]],
                    "衣着": [clothing_values[idx % len(clothing_values)]],
                    "特征": [features_values[idx % len(features_values)]],
                    "专属NPC": ["否"],
                    "备注": [f"补充模型{num}"],
                },
            },
        })

    return {
        "version": 1,
        "generated_at": GENERATED_AT,
        "meta": {
            "module": "model",
            "description": "models fixture for integration tests",
            "total": len(resources),
        },
        "resources": resources,
    }


# ---------------------------------------------------------------------------
# Module 2 — animator (~30 records)
# ---------------------------------------------------------------------------

def generate_animator() -> dict:
    resources = []

    resource_types = ["角色动作", "骑乘动作", "技能动作"]
    body_types = ["壮硕", "纤细", "标准"]
    action_types = ["攻击", "防御", "移动", "技能", "待机", "死亡"]
    schools = ["少林", "武当", "峨眉", "丐帮", "明教"]
    weapon_types = ["剑", "刀", "棍", "弓", "拳"]
    core_actions = ["挥砍", "突刺", "格挡", "跳跃", "翻滚"]
    file_types = ["FBX", "MAX"]
    mount_types = ["马", "飞鸟", "异兽"]
    qinggong_types = ["轻身", "御剑", "踏云"]
    common_actions = ["普攻", "技能1", "技能2", "被击", "死亡"]

    # 27 records with front + left dual view
    for i in range(27):
        num = f"{i + 1:03d}"
        action_id = i + 1  # 1..27 for number_range coverage (boundary test)
        resources.append({
            "resource_id": f"data/sources/animator/gifs/a{num}_front.gif",
            "source_path": f"data/sources/animator/gifs/a{num}_front.gif",
            "size_bytes": 102400 + i * 2048,
            "svn": svn(i),
            "result": {
                "status": "ok",
                "gif_rel_path_front": f"gifs/a{num}_front.gif",
                "gif_rel_path_left": f"gifs/a{num}_left.gif",
                "tags": {
                    "资源类型": [resource_types[i % len(resource_types)]],
                    "体型": [body_types[i % len(body_types)]],
                    "动作类型": [action_types[i % len(action_types)]],
                    "特殊系统": [],
                    "门派": [schools[i % len(schools)]],
                    "武器类型": [weapon_types[i % len(weapon_types)]],
                    "通用动作分类": [common_actions[i % len(common_actions)]],
                    "骑乘类型": [mount_types[i % len(mount_types)]] if i % 5 == 0 else [],
                    "轻功类型": [qinggong_types[i % len(qinggong_types)]] if i % 4 == 0 else [],
                    "核心动作": [core_actions[i % len(core_actions)]],
                    "文件类型": [file_types[i % len(file_types)]],  # hidden field
                    "AI分析的标签": [f"ai标签{i + 1}a", f"ai标签{i + 1}b"],
                },
                "action_id": action_id,
                "description": f"动作序列{num}，角色执行{action_types[i % len(action_types)]}动作",
            },
        })

    # 3 records with ONLY front view (no left view)
    for i in range(3):
        num = f"{i + 28:03d}"
        resources.append({
            "resource_id": f"data/sources/animator/gifs/a{num}_front_only.gif",
            "source_path": f"data/sources/animator/gifs/a{num}_front_only.gif",
            "size_bytes": 81920,
            "svn": svn(100 + i),
            "result": {
                "status": "ok",
                "gif_rel_path_front": f"gifs/a{num}_front.gif",
                # gif_rel_path_left intentionally omitted
                "tags": {
                    "资源类型": ["角色动作"],
                    "体型": [body_types[i % len(body_types)]],
                    "动作类型": ["待机"],
                    "门派": [schools[i % len(schools)]],
                    "武器类型": ["剑"],
                    "核心动作": ["待机"],
                    "文件类型": ["FBX"],
                    "AI分析的标签": [f"仅正视角{i + 1}"],
                },
            },
        })

    return {
        "version": 1,
        "generated_at": GENERATED_AT,
        "meta": {
            "module": "animator",
            "description": "animator fixture for integration tests",
            "total": len(resources),
        },
        "resources": resources,
    }


# ---------------------------------------------------------------------------
# Module 3 — effects (~30 records)
# ---------------------------------------------------------------------------

def generate_effects() -> dict:
    resources = []

    colors = ["红色", "蓝色", "绿色", "紫色", "金色", "白色", "黑色"]
    form_structures = ["粒子", "光束", "圆形", "爆炸", "波动"]
    time_dynamics = ["爆发", "持续", "消散", "循环"]
    elements = ["火系", "冰系", "雷系", "风系", "土系", "光系", "暗系"]
    combat_skills = ["攻击", "防御", "治疗", "控制", "位移"]
    scene_envs = ["战场", "城镇", "野外", "地下城", "空中"]
    status_buffs = ["灼烧", "冰冻", "麻痹", "沉默", "无"]
    magic_circles = ["普通阵法", "召唤阵", "封印阵", "无"]
    ui_hints = ["获得", "消耗", "强化", "提示", "无"]
    biz_usages = ["技能特效", "UI特效", "环境特效", "剧情特效"]
    char_actions = ["释放", "受击", "移动", "待机"]
    item_props = ["武器光效", "道具闪光", "材料光晕", "无"]

    # 22 records with all 12 tag categories + full quantitative fields
    for i in range(22):
        num = f"{i + 1:03d}"
        resources.append({
            "resource_id": f"data/source/other/hd特效/ui_m/pss/e{num}.pss",
            "source_path": f"data/source/other/hd特效/ui_m/pss/e{num}.pss",
            "size_bytes": 18938 + i * 1024,
            "svn": svn(i),
            "result": {
                "status": "ok",
                "gif_rel_path": f"gifs/e{num}.gif",
                "gif_grid_rel_path": f"gifs/e{num}_grid.gif",
                "length_cm": round(2100.0 + i * 50, 1),
                "width_cm": round(1000.0 + i * 30, 1),
                "height_cm": round(1000.0 + i * 20, 1),
                "effect_duration_sec": round(2.0 + i * 0.1, 2),
                "gif_duration_sec": round(2.0 + i * 0.1, 2),
                "camera_distance": round(2211.92 + i * 10, 2),
                "camera_scale": round(0.638 - i * 0.005, 3),
                "focus_offset": round(-0.42 + i * 0.01, 3),
                "area_ratio": round(0.195 + i * 0.003, 3),
                "span_max": round(0.874 - i * 0.005, 3),
                "center_x": round(0.519 + i * 0.002, 3),
                "center_y": round(0.481 - i * 0.002, 3),
                "clipped": i % 3 == 0,
                "fit_attempts": 10 + i,
                "fit_stop_reason": "best_effort" if i % 2 == 0 else "exact_fit",
                "description": f"特效{num}：{elements[i % len(elements)]}系{form_structures[i % len(form_structures)]}特效，用于{biz_usages[i % len(biz_usages)]}",
                "tags": {
                    "颜色": [colors[i % len(colors)], colors[(i + 1) % len(colors)]],
                    "形态结构": [form_structures[i % len(form_structures)]],
                    "时间动态": [time_dynamics[i % len(time_dynamics)]],
                    "元素属性": [elements[i % len(elements)]],
                    "战斗技能": [combat_skills[i % len(combat_skills)]],
                    "场景环境": [scene_envs[i % len(scene_envs)]],
                    "状态Buff": [status_buffs[i % len(status_buffs)]],
                    "法阵地面": [magic_circles[i % len(magic_circles)]],
                    "UI提示": [ui_hints[i % len(ui_hints)]],
                    "业务用途": [biz_usages[i % len(biz_usages)]],
                    "角色动作": [char_actions[i % len(char_actions)]],
                    "道具物品": [item_props[i % len(item_props)]],
                },
            },
        })

    # 5 records with PARTIAL quantitative fields (test null handling)
    partial_sets = [
        {"length_cm": 1500.0},
        {"width_cm": 800.0, "height_cm": 600.0},
        {"effect_duration_sec": 1.5, "camera_distance": 1800.0},
        {"length_cm": 2000.0, "area_ratio": 0.25},
        {},  # no quantitative fields at all
    ]
    for i, partial in enumerate(partial_sets):
        num = f"{i + 23:03d}"
        result = {
            "status": "ok",
            "gif_rel_path": f"gifs/e{num}.gif",
            "description": f"部分量化字段缺失测试{i + 1}",
            "tags": {
                "颜色": [colors[(i + 3) % len(colors)]],
                "形态结构": [form_structures[i % len(form_structures)]],
                "时间动态": [time_dynamics[i % len(time_dynamics)]],
                "元素属性": [elements[i % len(elements)]],
                "战斗技能": [combat_skills[i % len(combat_skills)]],
                "场景环境": [scene_envs[i % len(scene_envs)]],
                "状态Buff": [status_buffs[i % len(status_buffs)]],
                "法阵地面": [magic_circles[i % len(magic_circles)]],
                "UI提示": [ui_hints[i % len(ui_hints)]],
                "业务用途": [biz_usages[i % len(biz_usages)]],
                "角色动作": [char_actions[i % len(char_actions)]],
                "道具物品": [item_props[i % len(item_props)]],
            },
        }
        result.update(partial)
        resources.append({
            "resource_id": f"data/source/other/hd特效/ui_m/pss/e{num}.pss",
            "source_path": f"data/source/other/hd特效/ui_m/pss/e{num}.pss",
            "size_bytes": 16384,
            "svn": svn(200 + i),
            "result": result,
        })

    # 3 records with empty tags (test no-tags path)
    for i in range(3):
        num = f"{i + 28:03d}"
        resources.append({
            "resource_id": f"data/source/other/hd特效/ui_m/pss/e{num}_notag.pss",
            "source_path": f"data/source/other/hd特效/ui_m/pss/e{num}_notag.pss",
            "size_bytes": 12288,
            "svn": svn(300 + i),
            "result": {
                "status": "ok",
                "gif_rel_path": f"gifs/e{num}_notag.gif",
                "length_cm": 1000.0,
                "effect_duration_sec": 1.0,
                "tags": {},  # empty tags — test no-tags path
            },
        })

    return {
        "version": 1,
        "generated_at": GENERATED_AT,
        "meta": {
            "module": "effect",
            "description": "effects fixture for integration tests",
            "total": len(resources),
        },
        "resources": resources,
    }


# ---------------------------------------------------------------------------
# Module 4 — icons (~40 records)
# ---------------------------------------------------------------------------

def generate_icons() -> dict:
    resources = []

    predefined_values = ["武器", "防具", "道具", "材料", "技能", "任务", "其他"]
    color_values = ["红色", "蓝色", "绿色", "紫色", "金色", "白色", "黑色"]
    semantic_values = ["攻击", "防御", "辅助", "特效", "系统", "角色", "环境"]

    # 7×7 = 49 combos but we want ~40 — do predefined × (color + semantic cycling)
    # Strategy: 7 predefined × (5 color+semantic combos each) = 35 base records
    # Then 5 long description records, then pad to 40

    idx = 0
    for predefined in predefined_values:
        for j in range(5):
            idx += 1
            num = f"{idx:03d}"
            color = color_values[(idx + j) % len(color_values)]
            semantic = semantic_values[(idx + j) % len(semantic_values)]
            resources.append({
                "resource_id": f"data/sources/icon/pngs/i{num}.png",
                "source_path": f"data/sources/icon/pngs/i{num}.png",
                "size_bytes": 8192 + idx * 64,
                "svn": svn(idx),
                "result": {
                    "status": "ok",
                    "rel_path": f"pngs/i{num}.png",
                    "width_px": 64,
                    "height_px": 64,
                    "framed": idx % 3 == 0,
                    "tags": {
                        "预定义标签": [predefined],
                        "颜色": [color],
                        "语义": [semantic],
                    },
                    "description": f"测试图标{num} — 一个{color}的{predefined}图标，代表{semantic}类物品，用于游戏界面显示",
                },
            })

    # 5 records with VERY LONG description (>200 chars)
    long_desc_base = (
        "这是一个超长描述用于测试截断功能。"
        "该图标在游戏中广泛使用，涵盖多个不同场景和系统模块。"
        "其设计风格严格符合游戏整体美术规范，色彩搭配和谐统一，线条流畅自然。"
        "在角色装备界面、商城展示、任务追踪、成就系统等多处均有出现。"
        "特别针对高分辨率屏幕进行了优化处理，支持2x和3x缩放显示，确保清晰度。"
        "该图标经过多轮美术评审，通过了严格的质量把关流程，可以放心使用。"
        "如有疑问请联系美术部门或查阅内部资源管理文档以获得更多信息。"
    )
    for i in range(5):
        idx += 1
        num = f"{idx:03d}"
        predefined = predefined_values[i % len(predefined_values)]
        color = color_values[i % len(color_values)]
        semantic = semantic_values[i % len(semantic_values)]
        resources.append({
            "resource_id": f"data/sources/icon/pngs/i{num}_long.png",
            "source_path": f"data/sources/icon/pngs/i{num}_long.png",
            "size_bytes": 10240,
            "svn": svn(500 + i),
            "result": {
                "status": "ok",
                "rel_path": f"pngs/i{num}_long.png",
                "width_px": 128,
                "height_px": 128,
                "framed": True,
                "tags": {
                    "预定义标签": [predefined],
                    "颜色": [color],
                    "语义": [semantic],
                },
                "description": long_desc_base + f"（图标编号：{num}，超长描述测试记录{i + 1}）",
            },
        })

    # Ensure all 7 colors are covered
    for i, color in enumerate(color_values):
        if not any(
            r["result"]["tags"].get("颜色") == [color]
            for r in resources
        ):
            idx += 1
            num = f"{idx:03d}"
            resources.append({
                "resource_id": f"data/sources/icon/pngs/i{num}_color.png",
                "source_path": f"data/sources/icon/pngs/i{num}_color.png",
                "size_bytes": 8192,
                "svn": svn(600 + i),
                "result": {
                    "status": "ok",
                    "rel_path": f"pngs/i{num}_color.png",
                    "width_px": 64,
                    "height_px": 64,
                    "framed": False,
                    "tags": {
                        "预定义标签": [predefined_values[i % len(predefined_values)]],
                        "颜色": [color],
                        "语义": [semantic_values[i % len(semantic_values)]],
                    },
                    "description": f"颜色覆盖补充记录：{color}",
                },
            })

    # Ensure all 7 semantics covered
    for i, semantic in enumerate(semantic_values):
        if not any(
            r["result"]["tags"].get("语义") == [semantic]
            for r in resources
        ):
            idx += 1
            num = f"{idx:03d}"
            resources.append({
                "resource_id": f"data/sources/icon/pngs/i{num}_sem.png",
                "source_path": f"data/sources/icon/pngs/i{num}_sem.png",
                "size_bytes": 8192,
                "svn": svn(700 + i),
                "result": {
                    "status": "ok",
                    "rel_path": f"pngs/i{num}_sem.png",
                    "width_px": 64,
                    "height_px": 64,
                    "framed": False,
                    "tags": {
                        "预定义标签": [predefined_values[i % len(predefined_values)]],
                        "颜色": [color_values[i % len(color_values)]],
                        "语义": [semantic],
                    },
                    "description": f"语义覆盖补充记录：{semantic}",
                },
            })

    # 5 records with empty description (test null handling)
    for i in range(5):
        idx += 1
        num = f"{idx:03d}"
        predefined = predefined_values[i % len(predefined_values)]
        color = color_values[i % len(color_values)]
        semantic = semantic_values[i % len(semantic_values)]
        resources.append({
            "resource_id": f"data/sources/icon/pngs/i{num}_nodesc.png",
            "source_path": f"data/sources/icon/pngs/i{num}_nodesc.png",
            "size_bytes": 7168,
            "svn": svn(800 + i),
            "result": {
                "status": "ok",
                "rel_path": f"pngs/i{num}_nodesc.png",
                "width_px": 64,
                "height_px": 64,
                "framed": False,
                "tags": {
                    "预定义标签": [predefined],
                    "颜色": [color],
                    "语义": [semantic],
                },
                # description intentionally omitted — null handling test
            },
        })

    return {
        "version": 1,
        "generated_at": GENERATED_AT,
        "meta": {
            "module": "icon",
            "description": "icons fixture for integration tests",
            "total": len(resources),
        },
        "resources": resources,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    files = {
        "models.fixture.json": generate_models(),
        "animator.fixture.json": generate_animator(),
        "effects.fixture.json": generate_effects(),
        "icons.fixture.json": generate_icons(),
    }

    for filename, data in files.items():
        path = FIXTURES_DIR / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        count = len(data["resources"])
        size_kb = path.stat().st_size // 1024
        print(f"  {filename:35s}  {count:3d} records  {size_kb:4d} KB")

    print(f"\nAll fixtures written to {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
