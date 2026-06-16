# 美术标签搜索平台 - 系统设计文档

## 方案概述

为游戏美术团队提供模型/特效/动作/图标四大模块的资源搜索系统。

**架构**：Vue 3 前端 → Nginx → FastAPI 后端 → PostgreSQL 16（数据存储）+ Elasticsearch 8（搜索引擎），Docker Compose 一键部署。缓存使用 Python 进程内 TTLCache（此规模无需 Redis）。

**数据库核心设计**：PG 为数据真相源，单表 `assets` + `tags JSONB` 存储；ES 为搜索引擎，同步 PG 数据并提供全文检索、结构化筛选、聚合统计。`tag_definitions` 表驱动前端筛选面板渲染、查询构建、LLM prompt 生成——新增标签维度只需 INSERT 一行配置，零代码改动。

**搜索方式**：

1. **左侧筛选面板** — 动态渲染，精确筛选，ES term/terms 查询，< 20ms
2. **自然语言搜索栏** — 两层解析：
   - 第一层：内存词典匹配（< 5ms），预估覆盖 ~70% 查询（上线后依据 search_logs 验证）
   - 第二层：仅剩余未匹配文本发给 LLM（3s 超时，失败降级为模糊搜索）
   - 结果缓存 24h，二次查询 < 5ms
3. **数值条件** — 如"播放时长 > 5s"，ES range 查询
4. **模糊关键词** — ES IK 中文分词 + match 全文检索 + highlight 高亮

**性能**：10 万数据量，100 并发无瓶颈。纯筛选 < 20ms，自然语言首次 1-2s（含 LLM），缓存命中 < 5ms，聚合统计 < 10ms。

**数据导入**：Excel 自动解析入库 PG，同步索引到 ES。Sheet 名映射模块，列名映射标签字段，多值自动拆数组。

**二期可选升级**：

| 方向 | 当前方案 | 可升级为 |
|------|----------|----------|
| 词典匹配算法 | 正向最长匹配 | Aho-Corasick 多模式匹配 |
| 热门搜索/搜索历史 | search_logs 记录但未利用 | 基于日志做热门推荐 |
| 监控告警 | 无 | Prometheus + Grafana |
| 搜索纠错 | 无 | ES suggest API 拼写纠正 |

---

## 项目概述

构建一个游戏资产搜索网站，支持模型、特效、动作、图标四大模块的资源检索。用户可通过自然语言搜索栏或左侧筛选面板查找资源，系统自动将自然语言解析为结构化标签 + 剩余关键词，实现精准筛选与模糊搜索的结合。

### 核心需求

- **4 个资源模块**：模型（一期）、特效（一期）、动作（一期）、图标（预留）
- **数据量**：约 10 万条资源记录
- **并发**：100 人同时使用
- **搜索方式**：筛选面板精确筛选 + 自然语言解析 + 模糊关键词搜索 + 数值条件查询
- **部署**：公司内网服务器，LLM 解析请求允许走外网
- **一期预览**：模型（截图缩略图）、特效（GIF 预览），动作/图标暂不含预览

### 数据来源

- 模型模块：Excel 表格（资源标签对照表.xlsx），18 个 Sheet（P080、P081、M1、M2、F1、F2、A 等），共 6,478 条资源记录，11 个标签维度。**注意**：每个 Sheet 第 2 行为选项枚举行（列出所有可选值），非真实数据，导入时跳过
- 动作模块：Excel 中"动作模组"Sheet，429 条记录，按体型 + 动作模组分组
- 特效模块：HTML 标签目录（`特效/effect_gif_catalog_embed_20260615_111542.html`），含 120 条特效记录，每条包含资源路径 + 已标注标签（464 个独立标签，覆盖场景、尺寸、时长、颜色、描述等维度）+ 256px APNG 预览（base64 内嵌）。导入时解析 HTML 提取结构化数据
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
│        静态资源(前端) + API转发 + 预览文件 + 限流               │
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
│  │  ┌──────────┐  直接构建ES查询                         │   │
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
│  │  │⑤ ES 查询构建器               │                    │   │
│  │  │  bool filter(标签) + range   │                    │   │
│  │  │  + match(IK分词) + aggs     │                    │   │
│  │  │  + highlight + 加权排序      │                    │   │
│  │  └─────┬────────────────────────┘                    │   │
│  │        │                                             │   │
│  │        ▼                                             │   │
│  │  ┌──────────────────────────────┐                    │   │
│  │  │⑥ ES 单次请求返回              │                    │   │
│  │  │  结果 + 总数 + 聚合 + 高亮    │                    │   │
│  │  └──────────────────────────────┘                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐   │
│  │ 数据导入服务     │  │ 标签管理服务    │  │ 筛选配置服务  │   │
│  │ Excel→PG→ES    │  │ 维度/值/同义词  │  │ 动态渲染驱动  │   │
│  └────────────────┘  └────────────────┘  └──────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              进程内缓存 (TTLCache)                      │   │
│  │  LLM解析结果(24h) | 标签选项(1h) | 词典(内存常驻)       │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────┬──────────────────┬───────────────────────────────┘
           │                  │
           ▼                  ▼
┌────────────────┐  ┌──────────────────────────────────────────┐
│ PostgreSQL 16   │  │ Elasticsearch 8 + IK 中文分词              │
│ (数据真相源)    │  │ (搜索引擎)                                 │
│                │  │                                            │
│ assets         │→│ assets 索引                                 │
│ tag_definitions│  │   keyword 字段(标签精确筛选)                │
│ tag_values     │  │   text+ik 字段(中文全文检索)                │
│ tag_synonyms   │  │   numeric 字段(数值范围查询)                │
│ search_logs    │  │   aggs(聚合统计，替代物化视图)              │
│ import_errors  │  │   highlight(搜索结果高亮)                   │
│ user_favorites │  │                                            │
└────────────────┘  └──────────────────────────────────────────┘

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
| 数据存储 | PostgreSQL 16 | 数据真相源，JSONB 存标签，管理表 |
| 搜索引擎 | Elasticsearch 8 + IK 分词 | 全文检索 + 结构化筛选 + 聚合统计 + 高亮 |
| 缓存 | Python cachetools.TTLCache | 进程内缓存，此规模无需 Redis |
| 反向代理 | Nginx | 静态资源 + API转发 + 基础限流 |
| LLM | Claude API / 通义千问 | 词典未命中时才调用，带降级 |
| 容器化 | Docker Compose | PG + ES + 后端 + 前端一键部署 |

### 搜索性能预估

| 场景 | 响应时间 | 说明 |
|------|----------|------|
| 纯面板筛选 | < 20ms | ES term filter，无需打分 |
| 自然语言（词典全命中） | < 30ms | 无 LLM，直接 ES 查询 |
| 自然语言（需 LLM） | 1-2s 首次，<30ms 缓存命中 | 24h 缓存，预估 ~70% 命中率 |
| 模糊关键词搜索 | < 30ms | ES IK 分词 + match 查询 |
| 聚合计数 | < 10ms | ES aggs，无论是否有筛选条件 |
| 搜索结果高亮 | 0 额外开销 | ES highlight 随查询一起返回 |

### 并发能力

| 组件 | 配置 | 承载 |
|------|------|------|
| FastAPI | 4 workers x 异步 | 轻松 500+ QPS |
| PostgreSQL | shared_buffers=512MB, max_connections=200 | 数据写入无瓶颈 |
| Elasticsearch | heap=2GB, 单节点 | 10 万数据搜索无瓶颈 |
| Nginx | worker_processes=4 | 转发无瓶颈 |

最低硬件：4核 16GB 内存 100GB SSD。推荐：8核 32GB 200GB SSD。

---

## 第二部分：数据库设计

### 数据库扩展

```sql
-- PG 仅做数据存储和管理查询，搜索由 ES 负责
-- 不再需要 pg_trgm 扩展
```

### 模块类型约束

| module_type | 模块 | 说明 |
|-------------|------|------|
| 1 | 模型 | 角色/NPC/怪物模型 |
| 2 | 特效 | 技能/场景特效 |
| 3 | 动作 | 角色动作动画 |
| 4 | 图标 | UI图标（预留） |

所有使用 `module_type` 的表统一加 CHECK 约束：
```sql
ALTER TABLE assets ADD CONSTRAINT chk_assets_module CHECK (module_type IN (1,2,3,4));
ALTER TABLE tag_definitions ADD CONSTRAINT chk_tagdef_module CHECK (module_type IN (1,2,3,4));
ALTER TABLE tag_synonyms ADD CONSTRAINT chk_synonym_module CHECK (module_type IN (1,2,3,4));
ALTER TABLE search_logs ADD CONSTRAINT chk_logs_module CHECK (module_type IN (1,2,3,4));
```

### 表 1：assets（资源主表）

```sql
CREATE TABLE assets (
    id              BIGSERIAL PRIMARY KEY,
    module_type     SMALLINT NOT NULL,
    name            VARCHAR(255) NOT NULL,
    resource_path   VARCHAR(500) NOT NULL,
    thumbnail_path  VARCHAR(500),
    tags            JSONB NOT NULL DEFAULT '{}',
    version         VARCHAR(20),
    file_size       BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX uk_assets_module_path ON assets (module_type, resource_path);
CREATE INDEX idx_assets_module ON assets (module_type);
CREATE INDEX idx_assets_tags ON assets USING GIN (tags jsonb_path_ops);
CREATE INDEX idx_assets_updated ON assets (updated_at DESC);
-- search_text / tag_vector / pg_trgm 索引已移除，全文检索和聚合由 ES 负责
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
    priority        INTEGER DEFAULT 0,
    -- 同一个词可映射到不同字段（如"金"→color:金 和 attribute:金）
    -- 词典匹配时按 priority DESC 取最高优先级
    -- 命中多字段且 priority 相同时，降级为 keyword
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(module_type, field_name, synonym)
);

CREATE INDEX idx_synonyms_module ON tag_synonyms (module_type);
CREATE INDEX idx_synonyms_lookup ON tag_synonyms (module_type, synonym);
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
-- raw_query 索引暂不建：一期只写不查的审计表，需要日志分析时再补
```

### 表 6：user_favorites（收藏，二期预留）

一期不含用户认证体系，此表仅做 DDL 预留。二期可通过 Nginx 注入内网域账号 `X-Remote-User` header 实现用户识别。

```sql
CREATE TABLE user_favorites (
    user_id         INTEGER NOT NULL,
    asset_id        BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, asset_id)
);
```

### 表 7：import_errors（导入错误记录）

```sql
CREATE TABLE import_errors (
    id              BIGSERIAL PRIMARY KEY,
    batch_id        VARCHAR(64) NOT NULL,
    module_type     SMALLINT,
    sheet_name      VARCHAR(100),
    row_number      INTEGER,
    field_name      VARCHAR(50),
    raw_value       TEXT,
    error_type      VARCHAR(50),
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_import_errors_batch ON import_errors (batch_id);
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
    "scene": ["技能","子弹","被击"],
    "size": "中型特效",
    "shape": "近方形/圆形占位",
    "duration": 2.5, "duration_label": "中等时长",
    "color": ["蓝色","白色"],
    "description": ["冰晶爆炸","蓝白碎片","碎片爆裂"],
    "source_name": "B_霸刀_刀被击05_悟"
}
```
> 特效标签来源于 HTML 目录文件中的扁平 `<span class="tag">` 列表。导入时需将扁平标签按规则映射到结构化字段：
> - 含"型特效"/"扁平"/"细长" → `size`
> - 含"时长" → `duration_label`，"时长约X.X秒" → 提取数值写入 `duration`
> - 颜色词（红/蓝/金/紫/白/黑/绿/黄/橙/青/灰/粉） → `color` 数组
> - 技能/子弹/被击/蓄力/buff/场景 → `scene` 数组
> - 其余标签 → `description` 数组（描述性标签，全文搜索用）
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
> `slot_name`、`slot_path`、`effect_path` 为资源路径信息而非标签，在 `tag_definitions` 中应标记 `is_filterable=false, is_searchable=false`，不进入筛选面板和 ES search_text。
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
| PG 存储 + ES 搜索 | PG 保证数据一致性，ES 提供高性能搜索+聚合+高亮 |
| tag_definitions 驱动一切 | 前端筛选面板、ES 查询构建、LLM prompt全从此读配置 |
| tag_synonyms + priority | 支持歧义词多字段映射，提升词典命中率 |
| import_errors 表 | 结构化记录导入错误，保障数据质量 |

### Elasticsearch 索引设计

**索引映射（assets index）**：

```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "ik_smart_analyzer": { "type": "custom", "tokenizer": "ik_smart" },
        "ik_max_analyzer": { "type": "custom", "tokenizer": "ik_max_word" }
      }
    }
  },
  "mappings": {
    "properties": {
      "id":             { "type": "long" },
      "module_type":    { "type": "keyword" },
      "name":           { "type": "text", "analyzer": "ik_max_analyzer", "search_analyzer": "ik_smart_analyzer",
                          "fields": { "keyword": { "type": "keyword" } } },
      "resource_path":  { "type": "keyword", "index": false },
      "thumbnail_path": { "type": "keyword", "index": false },
      "tags":           { "type": "object", "dynamic": true },
      "version":        { "type": "keyword" },
      "file_size":      { "type": "long" },
      "created_at":     { "type": "date" },
      "updated_at":     { "type": "date" },
      "search_text":    { "type": "text", "analyzer": "ik_max_analyzer", "search_analyzer": "ik_smart_analyzer" }
    },
    "dynamic_templates": [
      { "tags_strings":  { "path_match": "tags.*", "match_mapping_type": "string",
                           "mapping": { "type": "keyword" } } },
      { "tags_numbers":  { "path_match": "tags.*", "match_mapping_type": "long",
                           "mapping": { "type": "float" } } },
      { "tags_booleans": { "path_match": "tags.*", "match_mapping_type": "boolean",
                           "mapping": { "type": "boolean" } } }
    ]
  }
}
```

**关键设计**：
- `tags.*` 字段的 ES mapping **由应用启动 / reindex 时根据 `tag_definitions` 表显式生成**：`number_range` → `float`，`boolean` → `boolean`，枚举类 → `keyword`。`dynamic_templates` 仅作为未定义字段的 fallback，不依赖它做关键字段类型推断
- `name` 和 `search_text` 使用 IK 分词器：写入时 `ik_max_word` 最大化切分，搜索时 `ik_smart` 智能切分
- `search_text` 在索引时拼接 name + 所有标签值，用于全文模糊搜索
- 单分片（10 万数据无需分片），零副本（内网单机，ES 容器 restart=always 保障可用性）
- 新增标签维度：INSERT `tag_definitions` → 触发 reindex 自动更新 mapping

**数据同步策略**：

| 场景 | 同步方式 |
|------|----------|
| Excel 批量导入 | PG UPSERT 后，ES bulk index（每 500 条一批） |
| 单条资源增/改 | PG 写入后，同步 ES index（异步队列可选） |
| 资源删除 | PG 删除后，同步 ES delete |
| 全量重建 | `/admin/reindex-es` 接口，alias 切换模式（见下） |
| 数据不一致修复 | `/admin/check-sync` 比对 PG/ES 记录数，差异自动补同步 |

**ES 同步失败恢复**：
- bulk index 返回的 `errors=true` 时，逐条检查失败 item，写入 `import_errors`（`error_type='es_sync_failed'`）
- 导入完成后汇总报告 ES 同步失败数
- `/admin/check-sync` 接口：对比 PG `COUNT(*)` 和 ES `_count`，差异大于阈值告警
- `/admin/reindex-es` 使用 alias 切换：创建新索引 `assets_v{timestamp}` → 全量写入 → 切换 alias `assets` 指向新索引 → 删除旧索引。零停机，失败可回滚

`search_text` 在应用层写入 ES 前拼接（PG 不再存该字段）：
```python
search_text = f"{name} {' '.join(flatten_tag_values(tags))}"
```

---

## 第三部分：搜索解析服务

### 解析流程

```
用户输入
   │
   ▼
① 进程内缓存查询 ──命中──→ 直接返回
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
剩余文本整体作为 keyword → ES match 全文检索
前端标记 fallback=true → 可展示"部分智能解析不可用"提示
```

### 缓存策略

| 缓存项 | 存储 | TTL | 清除时机 |
|--------|------|-----|----------|
| LLM 解析结果 | TTLCache `maxsize=5000` | 24h | 标签池变更时 `cache.clear()` |
| 标签维度配置 | TTLCache | 1h | 管理端修改时主动失效 |
| 聚合计数 | ES aggs 实时计算 | — | 数据变更时自动更新 |
| 词典数据 | 应用内存 dict | - | API触发/每10分钟 |

> **为什么不用 Redis？** 10 万记录 / 100 并发 / 单机部署。三个缓存场景的数据总量 < 5MB，进程内 dict 访问 ~100ns，远快于 Redis 的 ~0.5ms 网络往返。多 worker 各持一份缓存，冷启动几轮请求后即热。省掉一个容器、一套连接池、一类故障模式。

**LLM 缓存 key 设计**：`(module_type, query_text)` 二元组作为 key（直接用原文，不做 MD5 hash，方便调试）。NLP 解析结果不依赖面板筛选状态——解析只提取标签，合并时才考虑面板优先级，因此 key 无需包含 filters。

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
└── admin/                                  # 需 X-Admin-Key header 鉴权
    ├── POST /refresh-dictionary    # 刷新词典
    ├── POST /reindex-es            # 全量重建ES索引（alias切换）
    ├── POST /import-excel          # 导入Excel
    └── GET  /check-sync            # PG/ES 数据一致性检查
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

**分页限制**：`page_size` 上限 100，`page * page_size` 上限 10000（ES `max_result_window` 默认值）。超限返回 400。全量导出走 PG 直接查询，不走分页接口。

**响应**：
```json
{
    "total": 386,
    "page": 1, "page_size": 20,
    "parse_info": {
        "parsed_filters": {"gender":"女","profession":["刺客"],"region":["中原"]},
        "effective_filters": {"gender":"女","profession":["刺客"],"region":["中原"]},
        "ignored_tags": [],
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
    "query_time_ms": 23,
    "facet_time_ms": 12
}
```

### 搜索建议接口

`GET /api/v1/search/suggestions?module_type=1&q=刺`

返回匹配前缀的标签值（**从词典匹配器内存中做前缀匹配**，不查 PG/ES）：
```json
{
    "suggestions": [
        {"text": "刺客", "field": "profession", "type": "tag"},
        {"text": "刺客待机", "field": "action_type", "type": "tag"}
    ]
}
```
词典匹配器启动时已加载全量 tag_values + tag_synonyms 到内存，搜索建议直接复用，响应 < 1ms。前端 debounce 300ms 防抖。

### 搜索编排逻辑

1. 如有 query → 调解析服务（词典+LLM）得到 parsed filter + keyword
2. 合并 parsed filter 与手动 filters（手动优先）
3. ES QueryBuilder 构建 bool 查询：filter(标签精确) + range(数值条件) + must(match 全文) + aggs(聚合) + highlight(高亮)
4. 单次 ES 请求返回：结果 + 总数 + 聚合计数 + 高亮片段

### 加权排序（ES function_score）

```json
{
  "function_score": {
    "query": { "bool": { "..." } },
    "functions": [
      // 由 es_query_builder 根据当前查询命中的 filter 字段动态生成
      // 每个命中的 filter term 加一个 weight=10 的 function
      // 无需枚举字段名，真正配置驱动
      { "filter": {"term": {"tags.<matched_field>": "<value>"}}, "weight": 10 },
      { "linear": { "updated_at": { "origin": "now", "scale": "30d", "decay": 0.5 } } }
    ],
    "score_mode": "sum",
    "boost_mode": "sum"
  }
}
```

- 精确标签命中：每命中一个筛选维度 +10 分（**动态生成**，不硬编码字段名）
- 全文匹配：ES BM25 默认打分（match query 自动计算）
- 新鲜度：linear decay，30 天内权重递减
- ES 原生支持，无需手写 SQL 排序表达式

### 聚合计数（ES Aggregations）

- 所有聚合计数统一由 ES aggs 实时计算，无需物化视图
- 每个筛选维度排除自身条件（post_filter + global aggs 模式）
- 单次 ES 请求同时返回结果 + facets，无需并行多查询
- 响应中返回 `facet_time_ms`，便于定位慢查询

### Excel 数据导入

- 自动映射 Sheet 名 → module_type:
  - 含 M/P 编号的 Sheet（M1, M2, P081 等）→ module_type=1（模型）
  - "动作模组" → module_type=3（动作）
  - "特效标签" → module_type=2（特效）；但实际特效数据从 HTML 目录文件导入（见下方）
  - 跳过"通用规则"、"进度统计"、"问题模型记录区"等非数据 Sheet
- 列名 → tags JSONB key（如"物种"→species，"性别"→gender），映射表在 config 中维护
- 多值字段（" / " 或换行分隔）→ 数组
- 跳过空行和无效路径
- 每 500 条一批 UPSERT PG（根据 module_type + resource_path 去重），同步 bulk index 到 ES
- 导入后自动刷新词典缓存

**数据质量校验**（导入层作为数据质量边界）：
- 所有字段按 `tag_definitions.field_type` 做类型校验
- 数值字段统一存 JSON number，不存字符串
- 布尔字段统一存 true/false
- 固定枚举字段必须归一到 `tag_values.value`，无法匹配的记入 `import_errors`
- 多值字段统一去空格、去空值、去重
- 路径字段统一规范化（反斜杠、大小写、重复分隔符）

**失败处理**：
- 单条解析失败记录到 `import_errors` 表并跳过，不中断整批
- 导入完成后返回四类计数：成功、跳过、失败、未知标签

### 特效数据导入（HTML 目录解析）

特效标签数据来源于 `特效/effect_gif_catalog_embed_20260615_111542.html`（~205MB，内嵌 120 条 base64 APNG），非 Excel。

**解析流程**：

1. 用 BeautifulSoup / regex 解析 HTML `<tr>` 行，提取 `<td class="path">` 和 `<td class="tags">` 内 `<span class="tag">`
2. 扁平标签列表 → 结构化字段映射：
   - 含"型特效"/"扁平"/"细长" → `tags.size`
   - "时长约X.X秒" → 正则提取数值 → `tags.duration`（float）
   - "短时长/中等时长/长时长/超长时长" → `tags.duration_label`
   - 颜色关键词（红/蓝/金/紫/白/黑/绿/黄/橙/青/灰/粉） → `tags.color` 数组
   - 场景关键词（技能/子弹/被击/蓄力/buff） → `tags.scene` 数组
   - 形状关键词（方形/圆形/横向延展） → `tags.shape`
   - 其余 → `tags.description` 数组
3. 提取 `<img class="gif" src="data:image/png;base64,...">` 中的 base64 数据，解码保存为 `static/previews/2/{resource_id}.png`（APNG 格式，可直接作为缩略图）
4. 用 Pillow 从 APNG 提取首帧生成静态 PNG 缩略图
5. UPSERT 到 PG `assets` 表 + 同步 ES 索引

**数据规模**：120 条特效，464 个独立标签值

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
│   │   │   ├── es_query_builder.py
│   │   │   ├── es_sync_service.py
│   │   │   └── cache.py            # TTLCache 封装
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
│   │   │   ├── ThumbnailPreview.vue
│   │   │   ├── AssetDetailModal.vue
│   │   │   └── Pagination.vue
│   │   ├── stores/searchStore.ts
│   │   └── api/search.ts
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── nginx.conf
├── sql/
│   ├── 001_init_schema.sql
│   └── 002_init_tags.sql
└── docs/
```

---

## 预览方案

### 一期预览范围

| 模块 | 预览类型 | 来源 | 展示方式 |
|------|----------|------|----------|
| 模型 | 截图（PNG） | Excel 单元格内嵌图片（WPS DISPIMG） | 搜索结果卡片缩略图 + 详情弹窗大图 |
| 特效 | APNG/GIF 动图 | HTML 目录文件中 base64 内嵌（256px APNG，120 条） | 卡片显示首帧 PNG 缩略图，悬停替换 src 加载动图 |
| 动作 | 无 | 暂无预览素材 | 仅标签和路径信息 |
| 图标 | 无 | 预留 | — |

### 模型截图提取（WPS 单元格图片）

Excel 文件使用 WPS 格式存储单元格内嵌图片，提取链路：

```
Sheet XML 单元格公式
  _xlfn.DISPIMG("ID_579830C7...", 1)     ← 单元格 C7 引用图片 ID
        │
        ▼
xl/cellimages.xml
  <cellImage> name="ID_579830C7..." → r:embed="rId5"   ← ID → rId 映射
        │
        ▼
xl/_rels/cellimages.xml.rels
  <Relationship Id="rId5" Target="media/image5.png"/>   ← rId → 文件路径
        │
        ▼
xl/media/image5.png                                     ← 实际图片文件（共 6298 张）
```

**导入时提取流程**：

1. 解析 `cellimages.xml` 构建 `image_name → rId` 映射
2. 解析 `cellimages.xml.rels` 构建 `rId → media/imageN.png` 映射
3. 遍历每个 Sheet XML，解析单元格公式中的 `DISPIMG("image_name", 1)`
4. 根据单元格行号匹配资源记录（同行的 A 列 = resource_path）
5. 从 xlsx zip 包中提取对应 PNG 文件，保存到 `static/previews/1/{resource_id}.png`
6. 写入 assets 表的 `thumbnail_path` 字段

**容错处理**（每步失败均不中断整批导入）：
- `cellimages.xml` 不存在（非 WPS 格式）→ 跳过图片提取，所有资源 `thumbnail_path=NULL`
- 某行无 DISPIMG 公式 → 该资源无缩略图，显示占位图
- image_name 在 cellimages.xml 中找不到对应 rId → 记入 `import_errors`（`error_type='image_extract_failed'`）
- media 文件损坏或缺失 → 记入 `import_errors`，`thumbnail_path=NULL`

### 预览文件管理

- `thumbnail_path` 字段（assets 表已有）存储预览文件的相对路径
- 模型截图：`static/previews/1/{resource_id}.png`
- 特效动图：`static/previews/2/{resource_id}.apng`，缩略图：`static/previews/2/{resource_id}_thumb.png`
- Nginx 直接提供静态文件服务，后端不做文件中转
- 无预览文件的资源显示模块默认占位图

**特效预览缩略图生成**（导入时处理）：
```python
from PIL import Image
# APNG 从 HTML base64 解码后保存为完整动图
apng = Image.open(apng_path)
apng.seek(0)  # 首帧
apng.save(thumb_path, "PNG")
```
- HTML 中内嵌的是 256px APNG（非原始 GIF），体积已压缩
- 导入时解码 base64 保存完整 APNG 动图（用于悬停播放）
- 提取首帧 PNG 作为缩略图（用于卡片默认展示）
- 搜索结果卡片默认显示 PNG 缩略图
- 鼠标悬停时通过替换 `<img src>` 加载 APNG 动图
- 详情弹窗直接加载 APNG 动图

### 前端展示

- **搜索结果卡片（网格视图）**：展示缩略图 + 名称 + 核心标签
  - 模型：显示截图缩略图（懒加载，默认 200×200 裁切）
  - 特效：默认显示首帧 PNG 缩略图，鼠标悬停替换 src 加载完整 GIF
- **搜索结果列表（列表视图）**：左侧小缩略图(80×80) + 右侧标签信息
- **详情弹窗**：点击卡片展开大图预览 + 完整标签信息 + 资源路径

### Nginx 静态文件配置

```nginx
location /static/previews/ {
    alias /data/previews/;
    expires 7d;
    add_header Cache-Control "public, immutable";
}
```

### 搜索响应中的预览字段

items 中已有 `thumbnail_path`，前端拼接为完整 URL：
```
{baseUrl}/static/previews/{thumbnail_path}
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
    │   └── AssetCard.vue           #   含缩略图预览
    │       └── ThumbnailPreview.vue #   模型截图/特效GIF
    ├── AssetDetailModal.vue        # 详情弹窗（大图预览）
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
    command: postgres -c shared_buffers=512MB -c effective_cache_size=4GB
             -c work_mem=64MB -c max_connections=200
  elasticsearch:
    image: elasticsearch:8.15.0
    restart: always
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms2g -Xmx2g
      - xpack.security.enabled=false
    volumes: [es_data:/usr/share/elasticsearch/data]
  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    depends_on: [postgres, elasticsearch]
  frontend:
    build: ./frontend
  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes: [./previews:/data/previews:ro]
    depends_on: [backend, frontend]
volumes:
  pg_data:
  es_data:
```

如需多容器副本可用 `docker compose up --scale backend=2`，同时在 Nginx upstream 中配置负载均衡。

IK 中文分词插件需在 ES 镜像中预装，可通过自定义 Dockerfile：
```dockerfile
FROM elasticsearch:8.15.0
RUN elasticsearch-plugin install analysis-ik
```

### 硬件要求

| 配置 | CPU | 内存 | 磁盘 | 说明 |
|------|-----|------|------|------|
| 最低 | 4核 | 16GB | 100GB SSD | ES heap 2GB + PG 512MB + 系统 |
| 推荐 | 8核 | 32GB | 200GB SSD | ES heap 4GB + PG 2GB + 余量充足 |
