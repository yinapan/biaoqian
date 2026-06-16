# 标乔资产搜索平台 - 系统设计文档

## 项目概述

构建一个游戏资产搜索网站，支持模型、特效、动作、图标四大模块的资源检索。用户可通过自然语言搜索栏或左侧筛选面板查找资源，系统自动将自然语言解析为结构化标签 + 剩余关键词，实现精准筛选与模糊搜索的结合。

### 核心需求

- **4 个资源模块**：模型（一期）、特效（一期）、动作（一期）、图标（预留）
- **数据量**：约 10 万条资源记录
- **并发**：100 人同时使用
- **搜索方式**：筛选面板精确筛选 + 自然语言解析 + 模糊关键词搜索 + 数值条件查询
- **部署**：公司内网服务器，LLM 解析请求允许走外网
- **一期不含**：预览图/缩略图

### 数据来源

- 模型模块：Excel 表格（资源标签对照表.xlsx），分布在 15+ 个 Sheet 中，每个资源包含 11 个标签维度（物种、性别、地域、势力、职业、体型、年龄、衣着、特征、专属NPC）
- 动作模块：Excel 中"动作模组"Sheet，按体型 + 动作模组分组
- 特效模块：GIF 预览文件 + 已定义标签维度（时长、颜色、形状、大小、属性、循环、场景、强度等，后续可扩展）
- 图标模块：尚未提供，需预留扩展

---

## 第一部分：系统整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                        用户浏览器 (Vue 3)                      │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 搜索栏          │  │ 筛选面板      │  │ 结果列表/网格    │  │
│  │ 输入+Tag展示    │  │ 动态渲染      │  │ 分页+排序        │  │
│  │ +剩余关键词编辑 │  │ (带聚合计数)  │  │ (卡片/列表切换)  │  │
│  └───────┬────────┘  └──────┬───────┘  └────────▲─────────┘  │
│          │ 自然语言          │ 筛选条件           │ 搜索结果    │
└──────────┼──────────────────┼───────────────────┼────────────┘
           │                  │                   │
           └──────────┬───────┘                   │
                      ▼                           │
┌─────────────────────────────────────────────────────────────┐
│                      Nginx (反向代理)                         │
│              静态资源(前端) + API转发 + 限流                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 后端 API (Python FastAPI)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    搜索编排服务                         │   │
│  │                                                      │   │
│  │   用户输入                                            │   │
│  │      │                                               │   │
│  │      ▼                                               │   │
│  │  ┌──────────────────┐                                │   │
│  │  │ ① 词典匹配 (<5ms) │ ← 同义词表 + 标签值表          │   │
│  │  │   "女"→gender:女   │                               │   │
│  │  │   "刺客"→profession│                               │   │
│  │  └────────┬─────────┘                                │   │
│  │           │                                          │   │
│  │     有剩余文本?                                       │   │
│  │      ╱        ╲                                      │   │
│  │    有            无                                   │   │
│  │    ▼              ▼                                   │   │
│  │  ┌──────────┐  直接构建SQL                            │   │
│  │  │② LLM解析  │  (跳过LLM)                             │   │
│  │  │ 带3s超时   │                                       │   │
│  │  │ 带降级容错 │                                       │   │
│  │  └─────┬────┘                                        │   │
│  │        │                                             │   │
│  │        ▼                                             │   │
│  │  ┌──────────┐                                        │   │
│  │  │③ 校验修正 │ ← 标签池校验，非法值降级为keyword       │   │
│  │  └─────┬────┘                                        │   │
│  │        │                                             │   │
│  │        ▼                                             │   │
│  │  ┌──────────────────┐                                │   │
│  │  │④ 合并筛选条件     │ 面板筛选 > NLP解析 > 关键词     │   │
│  │  └─────┬────────────┘                                │   │
│  │        │                                             │   │
│  │        ▼                                             │   │
│  │  ┌──────────────────────────────┐                    │   │
│  │  │⑤ 查询构建器 (QueryBuilder)    │                    │   │
│  │  │  精确筛选(JSONB) + 数值条件   │                    │   │
│  │  │  + 模糊搜索(trgm) + 加权排序  │                    │   │
│  │  └─────┬────────────────────────┘                    │   │
│  │        │                                             │   │
│  │        ▼                                             │   │
│  │  ┌──────────────────────────────┐                    │   │
│  │  │⑥ 并行执行                     │                    │   │
│  │  │  查结果 ∥ 查总数 ∥ 查聚合计数  │                    │   │
│  │  └──────────────────────────────┘                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐   │
│  │ 数据导入服务     │  │ 标签管理服务    │  │ 筛选配置服务  │   │
│  │ Excel解析入库   │  │ 维度/值/同义词  │  │ 动态渲染驱动  │   │
│  └────────────────┘  └────────────────┘  └──────────────┘   │
└──────────┬──────────────────┬──────────────────┬────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                     Redis 6                                  │
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌───────────────────┐    │
│  │ LLM解析缓存   │ │ 标签选项缓存  │ │ 同义词词典缓存     │    │
│  │ 24h TTL      │ │ 1h TTL       │ │ 变更时主动失效     │    │
│  │ ~70%命中率    │ │ 启动时预热    │ │ 启动时加载到内存   │    │
│  └──────────────┘ └──────────────┘ └───────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    PostgreSQL 16                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ assets (资源主表)                                       │  │
│  │   通用列 + tags JSONB + search_text + tag_vector        │  │
│  │   索引: GIN(jsonb) + 表达式索引 + GIN(trgm) + GIN(fts) │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ tag_definitions  │ tag_values  │ tag_synonyms           │  │
│  │ (标签维度配置)    │ (固定标签值) │ (同义词/别名)          │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ tag_counts (物化视图)            │ search_logs          │  │
│  │ 无筛选时<1ms返回聚合数据         │ (搜索日志，分析用)    │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ user_favorites (收藏，预留)                              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  扩展: pg_trgm + zhparser(中文分词，可选)                     │
└──────────────────────────────────────────────────────────────┘

外网 (仅搜索解析请求):
┌──────────────────┐
│ LLM API           │
│ Claude / 通义千问  │
│ (词典未命中时调用) │
│ (3s超时 + 降级)   │
└──────────────────┘
```

### 技术栈

| 层级 | 技术 | 理由 |
|------|------|------|
| 前端 | Vue 3 + Element Plus | 筛选面板/Tag组件/表格/分页齐全 |
| 后端 | Python 3.12 + FastAPI + asyncpg | 异步高并发，LLM SDK 生态好 |
| 数据库 | PostgreSQL 16 | JSONB + pg_trgm + 全文检索 + 物化视图 |
| 缓存 | Redis 7 | LLM结果缓存 + 词典缓存 + 标签缓存 |
| 反向代理 | Nginx | 静态资源 + API转发 + 基础限流 |
| LLM | Claude API / 通义千问 | 词典未命中时才调用，带降级 |
| 容器化 | Docker Compose | PG + Redis + 后端 + 前端一键部署 |

### 搜索性能预估

| 场景 | 响应时间 | 说明 |
|------|----------|------|
| 纯面板筛选 | < 30ms | JSONB GIN 索引 + 并行聚合 |
| 自然语言（词典全命中） | < 50ms | 无 LLM 调用 |
| 自然语言（需 LLM） | 1-2s 首次，<50ms 缓存命中 | 24h 缓存，~70% 命中率 |
| 聚合计数（无筛选） | < 1ms | 物化视图 |
| 聚合计数（有筛选） | < 50ms | 实时计算，并行查各维度 |

### 并发能力

| 组件 | 配置 | 承载 |
|------|------|------|
| FastAPI | 4 workers x 异步 | 轻松 500+ QPS |
| PostgreSQL | shared_buffers=2GB, max_connections=200 | 10w 数据无瓶颈 |
| Redis | 默认配置 | 10w+ QPS |
| Nginx | worker_processes=4 | 转发无瓶颈 |

最低硬件：4核 16GB 内存 100GB SSD。推荐：8核 32GB 200GB SSD。

---

## 第二部分：数据库设计

### 数据库扩展

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
```

### 模块类型枚举

| module_type | 模块 | 说明 |
|-------------|------|------|
| 1 | 模型 | 角色/NPC/怪物模型 |
| 2 | 特效 | 技能/场景特效 |
| 3 | 动作 | 角色动作动画 |
| 4 | 图标 | UI图标（预留） |

### 表 1：assets（资源主表）

```sql
CREATE TABLE assets (
    id              BIGSERIAL PRIMARY KEY,
    module_type     SMALLINT NOT NULL,
    name            VARCHAR(255) NOT NULL,
    resource_path   VARCHAR(500) NOT NULL,
    thumbnail_path  VARCHAR(500),
    tags            JSONB NOT NULL DEFAULT '{}',
    search_text     TEXT,
    tag_vector      TSVECTOR,
    version         VARCHAR(20),
    file_size       BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX uk_assets_module_path ON assets (module_type, resource_path);
```

### 表 2：tag_definitions（标签维度定义）

```sql
CREATE TABLE tag_definitions (
    id              SERIAL PRIMARY KEY,
    module_type     SMALLINT NOT NULL,
    field_name      VARCHAR(50) NOT NULL,
    display_name    VARCHAR(50) NOT NULL,
    field_type      VARCHAR(20) NOT NULL,
    -- field_type 可选值:
    --   'enum_single':  单选 → radio/下拉
    --   'enum_multi':   多选 → checkbox
    --   'number_range': 数值范围 → slider/输入框
    --   'boolean':      布尔 → switch
    --   'text':         自由文本 → 输入框
    is_fixed        BOOLEAN DEFAULT FALSE,
    is_filterable   BOOLEAN DEFAULT TRUE,
    is_searchable   BOOLEAN DEFAULT TRUE,
    sort_order      INTEGER DEFAULT 0,
    config          JSONB DEFAULT '{}',
    -- config 结构按 field_type 不同:
    --   enum_single/enum_multi: {"show_count":true}（是否显示聚合计数）
    --   number_range: {"min":0,"max":100,"step":0.1,"unit":"s"}
    --   boolean: {"true_label":"是","false_label":"否"}
    --   text: {"placeholder":"输入关键词"}
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(module_type, field_name)
);
```

### 表 3：tag_values（固定标签可选值）

```sql
CREATE TABLE tag_values (
    id              SERIAL PRIMARY KEY,
    definition_id   INTEGER NOT NULL REFERENCES tag_definitions(id) ON DELETE CASCADE,
    value           VARCHAR(100) NOT NULL,
    display_name    VARCHAR(100),
    sort_order      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    UNIQUE(definition_id, value)
);
```

### 表 4：tag_synonyms（同义词/别名映射）

```sql
CREATE TABLE tag_synonyms (
    id              SERIAL PRIMARY KEY,
    module_type     SMALLINT NOT NULL,
    field_name      VARCHAR(50) NOT NULL,
    target_value    VARCHAR(100) NOT NULL,
    synonym         VARCHAR(100) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(module_type, synonym)
);

CREATE INDEX idx_synonyms_module ON tag_synonyms (module_type);
```

### 表 5：search_logs（搜索日志）

```sql
CREATE TABLE search_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER,
    module_type     SMALLINT NOT NULL,
    raw_query       TEXT,
    parsed_filter   JSONB,
    parsed_keyword  TEXT,
    parse_source    VARCHAR(20),
    result_count    INTEGER,
    parse_time_ms   INTEGER,
    query_time_ms   INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_logs_time ON search_logs (created_at DESC);
CREATE INDEX idx_search_logs_query ON search_logs USING GIN (raw_query gin_trgm_ops);
```

### 表 6：user_favorites（收藏，预留）

```sql
CREATE TABLE user_favorites (
    user_id         INTEGER NOT NULL,
    asset_id        BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, asset_id)
);
```

### 物化视图：tag_counts

```sql
CREATE MATERIALIZED VIEW tag_counts AS
SELECT
    a.module_type, td.field_name,
    a.tags->>td.field_name AS field_value,
    COUNT(*) AS cnt
FROM assets a
CROSS JOIN tag_definitions td
WHERE td.field_type = 'enum_single' AND td.is_filterable = TRUE
  AND a.module_type = td.module_type
  AND a.tags->>td.field_name IS NOT NULL
GROUP BY a.module_type, td.field_name, a.tags->>td.field_name
UNION ALL
SELECT
    a.module_type, td.field_name,
    elem::TEXT AS field_value,
    COUNT(*) AS cnt
FROM assets a
CROSS JOIN tag_definitions td,
LATERAL jsonb_array_elements_text(
    CASE WHEN jsonb_typeof(a.tags->td.field_name) = 'array'
         THEN a.tags->td.field_name ELSE '[]'::jsonb END
) AS elem
WHERE td.field_type = 'enum_multi' AND td.is_filterable = TRUE
  AND a.module_type = td.module_type
GROUP BY a.module_type, td.field_name, elem::TEXT
WITH DATA;

CREATE UNIQUE INDEX idx_tag_counts_pk ON tag_counts (module_type, field_name, field_value);
```

### 索引策略

```sql
-- 第一层：必建索引
CREATE INDEX idx_assets_module ON assets (module_type);
CREATE INDEX idx_assets_tags ON assets USING GIN (tags jsonb_path_ops);
CREATE INDEX idx_assets_search_trgm ON assets USING GIN (search_text gin_trgm_ops);
CREATE INDEX idx_assets_fts ON assets USING GIN (tag_vector);
CREATE INDEX idx_assets_updated ON assets (updated_at DESC);

-- 第二层：高频字段表达式索引
CREATE INDEX idx_tags_gender ON assets ((tags->>'gender')) WHERE tags->>'gender' IS NOT NULL;
CREATE INDEX idx_tags_species ON assets ((tags->>'species')) WHERE tags->>'species' IS NOT NULL;
CREATE INDEX idx_tags_body_type ON assets ((tags->>'body_type')) WHERE tags->>'body_type' IS NOT NULL;
CREATE INDEX idx_tags_age_group ON assets ((tags->>'age_group')) WHERE tags->>'age_group' IS NOT NULL;
CREATE INDEX idx_tags_duration ON assets (((tags->>'duration')::NUMERIC)) WHERE tags ? 'duration';

-- 第三层：复合索引（按search_logs分析后按需添加）
CREATE INDEX idx_assets_module_gender ON assets (module_type, (tags->>'gender'));
CREATE INDEX idx_assets_module_gender_body ON assets (module_type, (tags->>'gender'), (tags->>'body_type'));
```

### 触发器

```sql
CREATE OR REPLACE FUNCTION update_search_text() RETURNS TRIGGER AS $$
DECLARE
    parts       TEXT[] := ARRAY[]::TEXT[];
    key         TEXT;
    val         JSONB;
    def_row     RECORD;
BEGIN
    parts := array_append(parts, NEW.name);
    FOR def_row IN
        SELECT field_name FROM tag_definitions
        WHERE module_type = NEW.module_type AND is_searchable = TRUE
    LOOP
        val := NEW.tags->def_row.field_name;
        IF val IS NULL THEN CONTINUE; END IF;
        CASE jsonb_typeof(val)
            WHEN 'array' THEN
                parts := array_append(parts,
                    (SELECT string_agg(e, ' ') FROM jsonb_array_elements_text(val) AS e));
            WHEN 'string' THEN parts := array_append(parts, val #>> '{}');
            WHEN 'number' THEN parts := array_append(parts, val::TEXT);
            WHEN 'boolean' THEN
                IF val::BOOLEAN THEN parts := array_append(parts, def_row.field_name); END IF;
            ELSE NULL;
        END CASE;
    END LOOP;
    NEW.search_text := array_to_string(parts, ' ');
    NEW.tag_vector  := to_tsvector('simple', COALESCE(NEW.search_text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_search_text
    BEFORE INSERT OR UPDATE OF name, tags ON assets
    FOR EACH ROW EXECUTE FUNCTION update_search_text();
```

### 各模块 tags JSONB 结构

**模型模块 (module_type=1)**：
```json
{
    "species": "人", "gender": "女",
    "region": ["中原","东海"], "faction": ["藏剑"],
    "profession": ["刺客","打手"], "body_type": "标准",
    "age_group": "青年", "clothing": ["劲装"],
    "features": ["蒙面","战损"], "exclusive_npc": "叶英"
}
```

**特效模块 (module_type=2)**：
```json
{
    "duration": 5.2, "color": ["红","金"],
    "shape": "圆形扩散", "size": "大",
    "attribute": "火", "loop": true,
    "scene": ["战斗","Boss技能"], "intensity": "强"
}
```

**动作模块 (module_type=3)**：
```json
{
    "body_type": "P080", "action_module": "强势",
    "action_type": "普通待机", "action_id": 30,
    "remark": "抱臂", "slot_name": "",
    "slot_path": "", "effect_path": ""
}
```

**图标模块 (module_type=4，预留)**：
```json
{
    "category": "技能图标", "style": "写实",
    "resolution": "128x128", "color_tone": "暖色"
}
```

### 设计要点

| 决策 | 理由 |
|------|------|
| 单表 assets + JSONB | 避免4表UNION；新增模块/标签零DDL变更 |
| GIN + 表达式索引分层 | GIN通用兜底；热门字段表达式索引提速5-10x |
| tag_definitions 驱动一切 | 前端筛选面板、查询构建、LLM prompt全从此读配置 |
| tag_synonyms | 提升词典匹配命中率，减少LLM调用 |
| 物化视图 tag_counts | 无筛选时聚合计数<1ms |
| 触发器自动维护 search_text | 写入时自动生成，查询时零成本 |

---

## 第三部分：搜索解析服务

### 解析流程

```
用户输入
   │
   ▼
① Redis 缓存查询 ──命中──→ 直接返回
   │ 未命中
   ▼
② 分词（空格分割 + 最长匹配扫描）
   │
   ▼
③ 词典匹配 (< 5ms)
   │ 词典来源：tag_values + tag_synonyms + 开放标签高频值
   │
   ├─ 有剩余文本 → ④ LLM 解析（3s超时）→ ⑤ 校验修正
   │                    │ 失败/超时 → ⑥ 降级（剩余文本作为keyword）
   │
   └─ 无剩余 → 直接返回（< 10ms）
   │
   ▼
⑦ 合并结果 + 写缓存(24h) + 异步写搜索日志
```

### 词典匹配器

基于内存的快速标签匹配，启动时从数据库加载全量数据：

- **数据来源**：tag_values（固定标签值）+ tag_synonyms（同义词）+ assets 中高频开放标签值（出现>=3次）
- **匹配策略**：空格分词 → 对每个片段做正向最长匹配（处理"女刺客"粘连→"女"+"刺客"）
- **内存占用**：约数千条 token，< 1MB
- **热更新**：管理端 API 触发 / 每 10 分钟定时刷新，无需重启服务

分词示例：

```
输入: "红衣女刺客 中原 高级一点的角色"
空格分割: ["红衣女刺客", "中原", "高级一点的角色"]
最长匹配:
  "红衣女刺客" → "红衣"(未命中) + "女"(→gender:女) + "刺客"(→profession)
  "中原"       → "中原"(→region)
  "高级一点的角色" → 全部未命中
结果: matched={gender:"女",profession:["刺客"],region:["中原"]}, remaining="红衣 高级一点的角色"

输入: "壮硕老和尚 少林"
最长匹配:
  "壮硕"(→body_type) + "老"(未命中) + "和尚"(同义词→profession:僧侣)
  "少林"(→faction)
结果: matched={body_type:"壮硕",profession:["僧侣"],faction:["少林"]}, remaining="老"
剩余只有1字 → 跳过LLM，直接keyword模糊搜索

输入: "女 刺客 中原"
全部命中 → 跳过LLM，< 10ms 返回
```

### LLM 解析服务

仅在词典匹配有剩余文本且长度 > 1 时调用。

**Prompt 优化**：
- 只发送剩余未匹配文本（非完整用户输入）
- 只包含未匹配维度的标签池（非全量维度）
- 标签池从 tag_definitions + tag_values 动态读取
- max_tokens=256，temperature=0

**Prompt 模板**：
```
你是一个游戏资产搜索系统的查询解析器。
系统已识别出: {already_matched}
以下是尚未匹配的剩余文本，请尝试从中提取更多标签。

尚未匹配的标签维度:
{unmatched_tag_schema}

规则:
1. 只提取有把握的标签，不确定的放入 keyword
2. 数值条件用 {"op":">","value":5} 格式
3. 描述性/模糊性词语放入 keyword
4. 返回严格JSON

剩余文本: {remaining_text}

返回: {"filter":{},"keyword":"","confidence":0.0~1.0}
```

### 校验修正层

防止 LLM 幻觉污染查询：
- 不存在的维度 → 降级到 keyword
- 固定标签值不在标签池内 → 降级到 keyword
- 数值类校验格式和运算符合法性
- 布尔类标准化为 true/false
- 开放标签/文本类 → 直接保留

### 降级容错

```
LLM 调用失败（超时/报错/不可用）
    │
    ▼
剩余文本整体作为 keyword → pg_trgm 模糊搜索
前端标记 fallback=true → 可展示"部分智能解析不可用"提示
```

### 缓存策略

| 缓存项 | 存储 | TTL | 清除时机 |
|--------|------|-----|----------|
| LLM 解析结果 | Redis `parse:{module}:{md5}` | 24h | 标签池变更时 |
| 标签维度配置 | Redis `tag_defs:{module}` | 1h | 管理端修改时 |
| 聚合计数(无筛选) | 物化视图 / Redis | 5min | 定时刷新 |
| 词典数据 | 应用内存 | - | API触发/每10分钟 |

### 各场景性能

| 场景 | 词典 | LLM | 总耗时 |
|------|------|-----|--------|
| "女 刺客 中原" | 全命中 | 跳过 | < 10ms |
| "壮硕老和尚 少林" | 全命中(含同义词) | 跳过 | < 10ms |
| "红衣女刺客 中原" | 部分命中 | 解析"红衣" | ~1.2s首次 |
| "红衣女刺客 中原"(二次) | — | — | < 5ms (缓存) |
| LLM不可用时 | 部分命中 | 降级 | < 10ms |

---

## 第四部分：后端 API 设计

### API 接口

```
/api/v1/
├── search/
│   ├── POST /query              # 统一搜索
│   └── GET  /suggestions        # 搜索建议/自动补全
├── filter/
│   ├── GET  /definitions/{module}  # 筛选维度配置
│   └── GET  /counts/{module}       # 聚合计数
├── assets/
│   ├── GET  /{id}                  # 资源详情
│   └── POST /batch-import          # 批量导入
├── tags/
│   ├── GET  /values/{module}/{field}  # 标签可选值
│   ├── POST /synonyms                 # 新增同义词
│   └── GET  /synonyms/{module}        # 同义词列表
└── admin/
    ├── POST /refresh-counts        # 刷新聚合计数
    ├── POST /refresh-dictionary    # 刷新词典
    └── POST /import-excel          # 导入Excel
```

### 搜索接口

**请求**：
```json
{
    "module_type": 1,
    "query": "红衣女刺客 中原",
    "filters": {"gender": "女"},
    "conditions": [{"field": "duration", "op": ">", "value": 5}],
    "sort": {"field": "relevance", "order": "desc"},
    "page": 1, "page_size": 20
}
```

**响应**：
```json
{
    "total": 386,
    "page": 1, "page_size": 20,
    "parse_info": {
        "recognized_tags": {"gender":"女","profession":["刺客"],"region":["中原"]},
        "keyword": "红衣",
        "confidence": 0.9,
        "fallback": false,
        "parse_source": "dict+llm",
        "parse_time_ms": 8
    },
    "items": [{
        "id": 12345, "name": "P022005_HD",
        "resource_path": "data\\source\\NPC_source\\P022\\模型\\P022005_HD.mdl",
        "tags": {"species":"人","gender":"女","region":["中原"],"faction":["七秀"]},
        "relevance_score": 25.7
    }],
    "facets": {
        "gender": [{"value":"女","count":386},{"value":"男","count":0}],
        "body_type": [{"value":"标准","count":312},{"value":"胖子","count":40}]
    },
    "query_time_ms": 23
}
```

### 搜索建议接口

`GET /api/v1/search/suggestions?module_type=1&q=刺`

返回匹配前缀的标签值（从 tag_values + tag_synonyms 中 LIKE 查询）：
```json
{
    "suggestions": [
        {"text": "刺客", "field": "profession", "type": "tag"},
        {"text": "刺客待机", "field": "action_type", "type": "tag"}
    ]
}
```
用于搜索框输入时的下拉提示，纯数据库查询（pg_trgm 索引加速），无需 LLM。

### 搜索编排逻辑

1. 如有 query → 调解析服务（词典+LLM）得到 parsed filter + keyword
2. 合并 parsed filter 与手动 filters（手动优先）
3. QueryBuilder 构建 SQL：结构化筛选 + 数值条件 + 模糊搜索 + 加权排序
4. 并行执行：查结果 ∥ 查总数 ∥ 查聚合计数

### 加权排序

```sql
-- 精确标签命中: 每命中一个筛选维度得10分
-- 模糊匹配: trgm相似度(0~1) × 5
-- 全文匹配: tsvector匹配关键词时 +3 (用于中文分词场景)
-- 新鲜度: EXTRACT(EPOCH FROM (updated_at - '2020-01-01')) / 86400 × 0.01 (每天0.01分)
(精确标签命中数 × 10 + trgm_similarity × 5 + ts_rank × 3 + freshness × 0.01) DESC
```

`tag_vector`（TSVECTOR 列）作为 `pg_trgm` 的补充：trgm 按字符相似度匹配，tsvector 按词元精确匹配。两者并用覆盖不同搜索场景。

### 聚合计数分层

- 无筛选条件 → 读物化视图 (< 1ms)
- 有筛选条件 → 实时计算（每个维度排除自身条件，并行查询）

### Excel 数据导入

- 自动映射 Sheet 名 → module_type:
  - 含 M/P 编号的 Sheet（M1, M2, P081 等）→ module_type=1（模型）
  - "动作模组" → module_type=3（动作）
  - "特效标签" → module_type=2（特效）
  - 跳过"通用规则"、"进度统计"、"问题模型记录区"等非数据 Sheet
- 列名 → tags JSONB key（如"物种"→species，"性别"→gender），映射表在 config 中维护
- 多值字段（" / " 或换行分隔）→ 数组
- 跳过空行和无效路径
- 每 500 条一批 UPSERT（根据 module_type + resource_path 去重）
- 失败处理：单条解析失败记录到错误日志并跳过，不中断整批；导入完成后返回成功/跳过/失败计数
- 导入后自动刷新物化视图 + 词典

### 项目目录结构

```
biaoqiao/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── database.py
│   │   │   └── schemas.py
│   │   ├── services/
│   │   │   ├── search_service.py
│   │   │   ├── parse_service.py
│   │   │   ├── dictionary_matcher.py
│   │   │   ├── llm_parse_service.py
│   │   │   ├── parse_validator.py
│   │   │   ├── query_builder.py
│   │   │   ├── facet_service.py
│   │   │   └── cache_service.py
│   │   ├── routers/
│   │   │   ├── search.py
│   │   │   ├── filter.py
│   │   │   ├── assets.py
│   │   │   └── admin.py
│   │   └── importers/
│   │       ├── excel_importer.py
│   │       └── tag_initializer.py
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/SearchPage.vue
│   │   ├── components/
│   │   │   ├── SearchBar.vue
│   │   │   ├── ParsedTags.vue
│   │   │   ├── FilterPanel.vue
│   │   │   ├── FilterGroup.vue
│   │   │   ├── EnumSingleFilter.vue
│   │   │   ├── EnumMultiFilter.vue
│   │   │   ├── NumberRangeFilter.vue
│   │   │   ├── BooleanFilter.vue
│   │   │   ├── ResultGrid.vue
│   │   │   ├── ResultList.vue
│   │   │   ├── AssetCard.vue
│   │   │   └── Pagination.vue
│   │   ├── stores/searchStore.ts
│   │   └── api/search.ts
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── nginx.conf
├── sql/
│   ├── 001_init_schema.sql
│   ├── 002_init_tags.sql
│   └── 003_materialized_views.sql
└── docs/
```

---

## 第五部分：前端设计与部署

### 前端组件树

```
App.vue
└── SearchPage.vue
    ├── ModuleTabs.vue              # 模块切换
    ├── SearchBar.vue               # 搜索栏
    │   ├── SearchInput.vue         #   输入框
    │   └── ParsedTags.vue          #   已识别Tag展示
    ├── FilterPanel.vue             # 筛选面板（动态渲染）
    │   └── FilterGroup.vue         #   单个维度
    │       ├── EnumSingleFilter    #     单选
    │       ├── EnumMultiFilter     #     多选+计数
    │       ├── NumberRangeFilter   #     数值范围
    │       └── BooleanFilter       #     布尔开关
    ├── ResultToolbar.vue           # 排序+视图切换
    ├── ResultGrid.vue / ResultList.vue  # 结果展示
    │   └── AssetCard.vue
    └── Pagination.vue
```

### 核心联动逻辑

- **搜索栏输入** → 后端 NLP 解析 → 解析结果同步到筛选面板勾选状态 → 结果
- **筛选面板点选** → 直接构建查询（不经 LLM）→ 结果
- **删除已识别 Tag** → 更新筛选条件 → 重新查询
- **切换模块** → 清空状态 → 加载新模块筛选维度配置 → 初始数据

**前端不硬编码任何标签维度**，所有筛选组件由 tag_definitions API 驱动。

### 部署（Docker Compose）

```yaml
services:
  postgres:
    image: postgres:16
    volumes: [pg_data:/var/lib/postgresql/data, ./sql:/docker-entrypoint-initdb.d]
    command: postgres -c shared_buffers=2GB -c effective_cache_size=6GB
             -c work_mem=64MB -c max_connections=200
  redis:
    image: redis:7-alpine
  backend:
    build: ./backend
    deploy: { replicas: 2 }
    depends_on: [postgres, redis]
  frontend:
    build: ./frontend
  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    depends_on: [backend, frontend]
```

### 硬件要求

| 配置 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| 最低 | 4核 | 16GB | 100GB SSD |
| 推荐 | 8核 | 32GB | 200GB SSD |
