# 美术标签搜索平台 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建游戏美术资源搜索平台，支持模型/特效/动作三大模块的标签筛选、自然语言搜索、模糊关键词搜索和数值条件查询。

**架构：** Vue 3 前端 → Nginx → FastAPI 后端 → PostgreSQL 16（数据存储）+ Elasticsearch 8 + IK（搜索引擎）。Python 进程内 TTLCache 缓存。Docker Compose 一键部署。

**技术栈：** Python 3.12, FastAPI, asyncpg, elasticsearch-py, cachetools, openpyxl, Pillow, Vue 3, Element Plus, Pinia, TypeScript, Docker Compose

**设计规格：** `docs/superpowers/specs/2026-06-16-biaoqiao-search-platform-design.md`

---

## 文件结构

### 后端

| 文件 | 职责 |
|------|------|
| `backend/app/main.py` | FastAPI 应用入口，挂载路由，启动事件（加载词典、初始化 ES） |
| `backend/app/config.py` | 配置项（PG/ES 连接、LLM key、admin key 等） |
| `backend/app/models/database.py` | asyncpg 连接池管理 |
| `backend/app/models/schemas.py` | Pydantic 请求/响应模型 |
| `backend/app/services/cache.py` | TTLCache 封装（LLM 结果、标签配置） |
| `backend/app/services/dictionary_matcher.py` | 内存词典匹配器（空格分词 + 正向最长匹配） |
| `backend/app/services/llm_parse_service.py` | LLM 解析（prompt 构建、3s 超时、降级） |
| `backend/app/services/parse_validator.py` | LLM 结果校验修正（标签池校验、类型检查） |
| `backend/app/services/parse_service.py` | 解析编排（缓存→词典→LLM→校验→合并） |
| `backend/app/services/es_query_builder.py` | ES bool 查询构建（filter+range+match+aggs+highlight+function_score） |
| `backend/app/services/es_sync_service.py` | PG→ES 同步（bulk index、alias 切换 reindex、check-sync） |
| `backend/app/services/es_mapping.py` | 从 tag_definitions 生成 ES 显式 mapping |
| `backend/app/services/search_service.py` | 搜索编排（解析→合并筛选→ES 查询→格式化响应） |
| `backend/app/routers/search.py` | 搜索 API（POST /query, GET /suggestions） |
| `backend/app/routers/filter.py` | 筛选 API（GET /definitions, GET /counts） |
| `backend/app/routers/assets.py` | 资源 API（GET /{id}） |
| `backend/app/routers/admin.py` | 管理 API（reindex-es, import-excel, check-sync, refresh-dictionary） |
| `backend/app/importers/excel_importer.py` | Excel 导入（模型+动作，含 WPS 图片提取） |
| `backend/app/importers/html_importer.py` | HTML 特效导入（解析标签+提取 base64 APNG） |
| `backend/app/importers/wps_image_extractor.py` | WPS DISPIMG 图片提取链路 |
| `backend/app/importers/tag_initializer.py` | 初始化 tag_definitions + tag_values |
| `backend/requirements.txt` | Python 依赖 |
| `backend/Dockerfile` | 后端容器 |

### 前端

| 文件 | 职责 |
|------|------|
| `frontend/src/App.vue` | 根组件 |
| `frontend/src/views/SearchPage.vue` | 搜索页面主布局 |
| `frontend/src/components/ModuleTabs.vue` | 模块切换标签页 |
| `frontend/src/components/SearchBar.vue` | 搜索输入框 + 已识别标签展示 |
| `frontend/src/components/FilterPanel.vue` | 左侧筛选面板（动态渲染） |
| `frontend/src/components/FilterGroup.vue` | 单个筛选维度（按 field_type 分发子组件） |
| `frontend/src/components/ResultGrid.vue` | 网格视图 |
| `frontend/src/components/ResultList.vue` | 列表视图 |
| `frontend/src/components/AssetCard.vue` | 资源卡片（含缩略图） |
| `frontend/src/components/AssetDetailModal.vue` | 详情弹窗 |
| `frontend/src/components/Pagination.vue` | 分页组件 |
| `frontend/src/stores/searchStore.ts` | Pinia 搜索状态管理 |
| `frontend/src/api/search.ts` | API 请求封装 |
| `frontend/src/types/index.ts` | TypeScript 类型定义 |

### 基础设施

| 文件 | 职责 |
|------|------|
| `sql/001_init_schema.sql` | PG 建表 + 索引 + 约束 |
| `sql/002_init_tags.sql` | 初始 tag_definitions + tag_values + tag_synonyms 数据 |
| `docker-compose.yml` | PG + ES + 后端 + 前端 + Nginx |
| `docker/elasticsearch/Dockerfile` | ES + IK 分词插件 |
| `nginx.conf` | Nginx 配置（静态资源 + API 转发 + 预览文件） |

---

## 阶段 1：基础设施与项目脚手架

### 任务 1：Docker Compose + PG + ES 环境搭建

**文件：**
- 创建：`docker-compose.yml`
- 创建：`docker/elasticsearch/Dockerfile`
- 创建：`sql/001_init_schema.sql`
- 创建：`nginx.conf`

- [ ] **步骤 1：创建 ES 自定义 Dockerfile（预装 IK 分词插件）**

```dockerfile
# docker/elasticsearch/Dockerfile
FROM elasticsearch:8.15.0
RUN elasticsearch-plugin install analysis-ik
```

- [ ] **步骤 2：创建 docker-compose.yml**

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: biaoqiao
      POSTGRES_USER: biaoqiao
      POSTGRES_PASSWORD: biaoqiao_dev
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./sql:/docker-entrypoint-initdb.d
    command: >
      postgres
        -c shared_buffers=512MB
        -c effective_cache_size=4GB
        -c work_mem=64MB
        -c max_connections=200
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U biaoqiao"]
      interval: 5s
      retries: 5

  elasticsearch:
    build: ./docker/elasticsearch
    restart: always
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms2g -Xmx2g
      - xpack.security.enabled=false
    volumes:
      - es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 10s
      retries: 10

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --reload
    volumes:
      - ./backend:/app
      - ./previews:/data/previews
    environment:
      - DATABASE_URL=postgresql://biaoqiao:biaoqiao_dev@postgres:5432/biaoqiao
      - ES_URL=http://elasticsearch:9200
      - ADMIN_API_KEY=dev-admin-key-change-in-prod
    depends_on:
      postgres:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./previews:/data/previews:ro
    depends_on: [backend]

volumes:
  pg_data:
  es_data:
```

- [ ] **步骤 3：创建 nginx.conf**

```nginx
# nginx.conf
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    client_max_body_size 500M;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 30s;
    }

    location /static/previews/ {
        alias /data/previews/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **步骤 4：创建 SQL schema 文件 `sql/001_init_schema.sql`**

完整内容直接从设计规格中的建表 SQL 复制，包含：
- `assets` 表（含索引）
- `tag_definitions` 表
- `tag_values` 表
- `tag_synonyms` 表（含索引）
- `search_logs` 表（含索引）
- `user_favorites` 表（预留）
- `import_errors` 表（含索引）
- 所有 CHECK 约束（`chk_assets_module` 等 4 个）

见设计规格第 227-364 行的完整 SQL。

- [ ] **步骤 5：启动并验证基础设施**

```bash
docker compose up -d postgres elasticsearch
docker compose logs -f postgres  # 确认 schema 初始化成功
curl http://localhost:9200  # 确认 ES 启动 + IK 插件
```

预期：PG 建表成功，ES 返回 cluster info 且 `plugins` 含 `analysis-ik`。

- [ ] **步骤 6：Commit**

```bash
git add docker-compose.yml docker/ sql/ nginx.conf
git commit -m "infra: add Docker Compose with PG 16, ES 8 + IK, Nginx"
```

---

### 任务 2：后端项目脚手架

**文件：**
- 创建：`backend/requirements.txt`
- 创建：`backend/Dockerfile`
- 创建：`backend/app/__init__.py`
- 创建：`backend/app/config.py`
- 创建：`backend/app/models/__init__.py`
- 创建：`backend/app/models/database.py`
- 创建：`backend/app/main.py`
- 测试：`backend/tests/test_health.py`

- [ ] **步骤 1：创建 requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
asyncpg==0.30.0
elasticsearch[async]==8.15.1
cachetools==5.5.0
openpyxl==3.1.5
Pillow==11.1.0
beautifulsoup4==4.12.3
defusedxml==0.7.1
httpx==0.28.1
pydantic==2.10.3
pydantic-settings==2.7.0
python-multipart==0.0.18
pytest==8.3.4
pytest-asyncio==0.24.0
```

- [ ] **步骤 2：创建 backend/Dockerfile**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **步骤 3：创建 config.py**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao"
    es_url: str = "http://localhost:9200"
    es_index_alias: str = "assets"
    admin_api_key: str = "dev-admin-key-change-in-prod"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "qwen-turbo"
    llm_timeout: float = 3.0
    llm_enabled: bool = True
    parse_cache_maxsize: int = 5000
    parse_cache_ttl: int = 86400
    tag_cache_ttl: int = 3600
    dict_refresh_interval: int = 600
    page_size_max: int = 100
    page_offset_max: int = 10000

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **步骤 4：创建 database.py（asyncpg 连接池）**

```python
# backend/app/models/database.py
import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=5,
            max_size=20,
        )
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

- [ ] **步骤 5：创建 main.py（最小可启动应用）**

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.models.database import get_pool, close_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()

app = FastAPI(title="美术标签搜索平台", lifespan=lifespan)

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

- [ ] **步骤 6：编写健康检查测试**

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

- [ ] **步骤 7：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_health.py -v
```

预期：PASS

- [ ] **步骤 8：Commit**

```bash
git add backend/
git commit -m "feat: backend scaffold with FastAPI, asyncpg, config"
```

---

## 阶段 2：数据模型与初始化

### 任务 3：Pydantic Schemas

**文件：**
- 创建：`backend/app/models/schemas.py`
- 测试：`backend/tests/test_schemas.py`

- [ ] **步骤 1：编写 schema 验证测试**

```python
# backend/tests/test_schemas.py
import pytest
from app.models.schemas import SearchRequest, SearchResponse, ParseInfo

def test_search_request_defaults():
    req = SearchRequest(module_type=1)
    assert req.page == 1
    assert req.page_size == 20
    assert req.query is None
    assert req.filters == {}

def test_search_request_page_size_limit():
    with pytest.raises(Exception):
        SearchRequest(module_type=1, page_size=200)

def test_search_request_offset_limit():
    with pytest.raises(Exception):
        SearchRequest(module_type=1, page=501, page_size=20)

def test_parse_info_structure():
    info = ParseInfo(
        parsed_filters={"gender": "女"},
        effective_filters={"gender": "女"},
        keyword="红衣",
        confidence=0.9,
        fallback=False,
        parse_source="dict",
        parse_time_ms=5,
    )
    assert info.ignored_tags == []
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/test_schemas.py -v
```

预期：FAIL - `ModuleNotFoundError: No module named 'app.models.schemas'`

- [ ] **步骤 3：实现 schemas.py**

```python
# backend/app/models/schemas.py
from pydantic import BaseModel, Field, model_validator
from typing import Any
from app.config import settings

class Condition(BaseModel):
    field: str
    op: str  # ">", "<", ">=", "<=", "=="
    value: float

class SortOption(BaseModel):
    field: str = "relevance"
    order: str = "desc"

class SearchRequest(BaseModel):
    module_type: int = Field(ge=1, le=4)
    query: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    conditions: list[Condition] = Field(default_factory=list)
    sort: SortOption = Field(default_factory=SortOption)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=settings.page_size_max)

    @model_validator(mode="after")
    def check_offset(self):
        if self.page * self.page_size > settings.page_offset_max:
            raise ValueError(
                f"page * page_size must be <= {settings.page_offset_max}"
            )
        return self

class IgnoredTag(BaseModel):
    field: str
    value: str
    reason: str

class ParseInfo(BaseModel):
    parsed_filters: dict[str, Any] = Field(default_factory=dict)
    effective_filters: dict[str, Any] = Field(default_factory=dict)
    ignored_tags: list[IgnoredTag] = Field(default_factory=list)
    keyword: str = ""
    confidence: float = 0.0
    fallback: bool = False
    parse_source: str = ""
    parse_time_ms: int = 0

class AssetItem(BaseModel):
    id: int
    name: str
    resource_path: str
    thumbnail_path: str | None = None
    tags: dict[str, Any] = Field(default_factory=dict)
    relevance_score: float = 0.0
    highlight: dict[str, list[str]] = Field(default_factory=dict)

class FacetValue(BaseModel):
    value: str
    count: int

class SearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    parse_info: ParseInfo | None = None
    items: list[AssetItem]
    facets: dict[str, list[FacetValue]] = Field(default_factory=dict)
    query_time_ms: int = 0
    facet_time_ms: int = 0

class SuggestionItem(BaseModel):
    text: str
    field: str
    type: str = "tag"

class SuggestionsResponse(BaseModel):
    suggestions: list[SuggestionItem]

class ImportResult(BaseModel):
    batch_id: str
    success: int = 0
    skipped: int = 0
    failed: int = 0
    es_sync_failed: int = 0
    unknown_tags: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)

class TagDefinitionOut(BaseModel):
    id: int
    field_name: str
    display_name: str
    field_type: str
    is_filterable: bool
    is_searchable: bool
    sort_order: int
    config: dict[str, Any]
    values: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_schemas.py -v
```

预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add backend/app/models/schemas.py backend/tests/test_schemas.py
git commit -m "feat: add Pydantic schemas for search request/response"
```

---

### 任务 4：tag_definitions / tag_values 初始化数据

**文件：**
- 创建：`sql/002_init_tags.sql`
- 创建：`backend/app/importers/tag_initializer.py`
- 测试：`backend/tests/test_tag_initializer.py`

- [ ] **步骤 1：创建 002_init_tags.sql（模型模块 11 个标签维度 + 动作模块 + 特效模块）**

包含：
- 模型(module_type=1)：species, gender, region, faction, profession, body_type, age_group, clothing, features, exclusive_npc（其中 species/gender/body_type/age_group 为 enum_single，其余 enum_multi，exclusive_npc 为 text）
- 动作(module_type=3)：body_type(enum_single), action_module(enum_single), action_type(enum_single), action_id(number_range), remark(text), slot_name(text, not filterable), slot_path(text, not filterable/searchable), effect_path(text, not filterable/searchable)
- 特效(module_type=2)：scene(enum_multi), size(enum_single), shape(enum_single), duration(number_range), duration_label(enum_single), color(enum_multi), description(text), source_name(text, not filterable)
- 每个 enum 类型维度的 tag_values（从 Excel 枚举行和 HTML 标签中提取的实际可选值）
- 常用 tag_synonyms（如"和尚"→profession:僧侣, "壮"→body_type:壮硕 等）

```sql
-- sql/002_init_tags.sql
-- 模型模块标签维度
INSERT INTO tag_definitions (module_type, field_name, display_name, field_type, is_fixed, sort_order) VALUES
(1, 'species',       '物种', 'enum_single', true,  1),
(1, 'gender',        '性别', 'enum_single', true,  2),
(1, 'region',        '地域', 'enum_multi',  true,  3),
(1, 'faction',       '势力', 'enum_multi',  true,  4),
(1, 'profession',    '职业', 'enum_multi',  true,  5),
(1, 'body_type',     '体型', 'enum_single', true,  6),
(1, 'age_group',     '年龄', 'enum_single', true,  7),
(1, 'clothing',      '衣着', 'enum_multi',  true,  8),
(1, 'features',      '特征', 'enum_multi',  false, 9),
(1, 'exclusive_npc', '专属NPC', 'text',     false, 10);

-- 模型标签值（从 Excel 枚举行提取）
-- species
INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['人','老虎','狮子','狼','马','牛','熊','鸟','鹿','龙','虫','鱼']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'species';

-- gender
INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['男','女']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'gender';

-- body_type
INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['标准','壮硕','瘦子','胖子','侏儒','异种']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'body_type';

-- age_group
INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['小孩','青年','中年','老年']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'age_group';

-- clothing
INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['护甲','劲装','布衣','华服','冬衣']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'clothing';

-- region/faction/profession/features 值很多，由 tag_initializer.py 从 Excel 枚举行动态提取后 INSERT

-- 动作模块标签维度
INSERT INTO tag_definitions (module_type, field_name, display_name, field_type, is_fixed, is_filterable, is_searchable, sort_order) VALUES
(3, 'body_type',     '体型',     'enum_single',  true,  true,  true,  1),
(3, 'action_module', '动作模组', 'enum_single',  true,  true,  true,  2),
(3, 'action_type',   '动作类型', 'enum_single',  true,  true,  true,  3),
(3, 'action_id',     '动作ID',   'number_range', false, true,  false, 4),
(3, 'remark',        '备注',     'text',         false, false, true,  5),
(3, 'slot_name',     '插槽',     'text',         false, false, false, 6),
(3, 'slot_path',     '插槽路径', 'text',         false, false, false, 7),
(3, 'effect_path',   '特效资源', 'text',         false, false, false, 8);

-- 特效模块标签维度
INSERT INTO tag_definitions (module_type, field_name, display_name, field_type, is_fixed, is_filterable, is_searchable, sort_order, config) VALUES
(2, 'scene',          '场景',   'enum_multi',   true,  true,  true,  1, '{}'),
(2, 'size',           '尺寸',   'enum_single',  true,  true,  true,  2, '{}'),
(2, 'shape',          '形状',   'enum_single',  true,  true,  true,  3, '{}'),
(2, 'duration',       '时长',   'number_range', false, true,  false, 4, '{"min":0,"max":30,"step":0.1,"unit":"s"}'),
(2, 'duration_label', '时长级别','enum_single', true,  true,  true,  5, '{}'),
(2, 'color',          '颜色',   'enum_multi',   true,  true,  true,  6, '{}'),
(2, 'description',    '描述标签','text',        false, false, true,  7, '{}'),
(2, 'source_name',    '资源名',  'text',        false, false, false, 8, '{}');

-- 特效标签值
INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['技能','子弹','被击','蓄力','buff','场景']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 2 AND td.field_name = 'scene';

INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['小型特效','中型特效','大型特效','贴地/扁平特效','长条/细长']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 2 AND td.field_name = 'size';

INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['短时长','中等时长','长时长','超长时长']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 2 AND td.field_name = 'duration_label';

INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['红色','蓝色','金色','紫色','白色','黑色','绿色','黄色','橙色','青色','灰色','粉色']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 2 AND td.field_name = 'color';

-- 常用同义词
INSERT INTO tag_synonyms (module_type, field_name, target_value, synonym, priority) VALUES
(1, 'profession', '僧侣', '和尚', 10),
(1, 'profession', '僧侣', '出家人', 10),
(1, 'profession', '侠客', '大侠', 10),
(1, 'body_type',  '壮硕', '壮', 5),
(1, 'body_type',  '瘦子', '瘦', 5),
(1, 'body_type',  '胖子', '胖', 5),
(1, 'gender',     '女', '女性', 5),
(1, 'gender',     '男', '男性', 5),
(1, 'age_group',  '老年', '老人', 5),
(1, 'age_group',  '青年', '年轻', 5),
(1, 'age_group',  '小孩', '儿童', 5);
```

- [ ] **步骤 2：创建 tag_initializer.py（从 Excel 枚举行提取剩余标签值）**

```python
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
```

- [ ] **步骤 3：编写测试**

```python
# backend/tests/test_tag_initializer.py
from app.importers.tag_initializer import COLUMN_MAP, SKIP_SHEETS

def test_column_map_covers_all_model_fields():
    expected = {"species","gender","region","faction","profession",
                "body_type","age_group","clothing","features","exclusive_npc"}
    assert set(COLUMN_MAP.values()) == expected

def test_skip_sheets():
    assert "通用规则" in SKIP_SHEETS
    assert "动作模组" in SKIP_SHEETS
    assert "P080【完成】" not in SKIP_SHEETS
```

- [ ] **步骤 4：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_tag_initializer.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add sql/002_init_tags.sql backend/app/importers/tag_initializer.py backend/tests/
git commit -m "feat: add tag_definitions/tag_values init data + Excel enum extractor"
```

---

## 阶段 3：ES 索引管理与数据同步

### 任务 5：ES Mapping 生成 + 索引创建

**文件：**
- 创建：`backend/app/services/es_mapping.py`
- 创建：`backend/app/services/es_sync_service.py`
- 测试：`backend/tests/test_es_mapping.py`

- [ ] **步骤 1：编写 ES mapping 生成测试**

```python
# backend/tests/test_es_mapping.py
from app.services.es_mapping import generate_tag_properties

def test_generate_tag_properties_enum():
    definitions = [
        {"field_name": "gender", "field_type": "enum_single"},
        {"field_name": "region", "field_type": "enum_multi"},
    ]
    props = generate_tag_properties(definitions)
    assert props["tags.gender"] == {"type": "keyword"}
    assert props["tags.region"] == {"type": "keyword"}

def test_generate_tag_properties_number():
    definitions = [{"field_name": "duration", "field_type": "number_range"}]
    props = generate_tag_properties(definitions)
    assert props["tags.duration"] == {"type": "float"}

def test_generate_tag_properties_boolean():
    definitions = [{"field_name": "loop", "field_type": "boolean"}]
    props = generate_tag_properties(definitions)
    assert props["tags.loop"] == {"type": "boolean"}

def test_generate_tag_properties_text():
    definitions = [{"field_name": "remark", "field_type": "text"}]
    props = generate_tag_properties(definitions)
    assert props["tags.remark"]["type"] == "keyword"
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/test_es_mapping.py -v
```

- [ ] **步骤 3：实现 es_mapping.py**

```python
# backend/app/services/es_mapping.py

FIELD_TYPE_TO_ES = {
    "enum_single": {"type": "keyword"},
    "enum_multi": {"type": "keyword"},
    "number_range": {"type": "float"},
    "boolean": {"type": "boolean"},
    "text": {"type": "keyword"},
}

def generate_tag_properties(
    definitions: list[dict],
) -> dict[str, dict]:
    props = {}
    for d in definitions:
        es_type = FIELD_TYPE_TO_ES.get(d["field_type"], {"type": "keyword"})
        props[f"tags.{d['field_name']}"] = es_type
    return props

def build_index_settings_and_mappings(
    tag_definitions: list[dict],
) -> dict:
    tag_props = generate_tag_properties(tag_definitions)
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "ik_smart_analyzer": {"type": "custom", "tokenizer": "ik_smart"},
                    "ik_max_analyzer": {"type": "custom", "tokenizer": "ik_max_word"},
                }
            },
        },
        "mappings": {
            "properties": {
                "id": {"type": "long"},
                "module_type": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "analyzer": "ik_max_analyzer",
                    "search_analyzer": "ik_smart_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "resource_path": {"type": "keyword", "index": False},
                "thumbnail_path": {"type": "keyword", "index": False},
                "tags": {"type": "object", "dynamic": True},
                "version": {"type": "keyword"},
                "file_size": {"type": "long"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "search_text": {
                    "type": "text",
                    "analyzer": "ik_max_analyzer",
                    "search_analyzer": "ik_smart_analyzer",
                },
                **tag_props,
            },
            "dynamic_templates": [
                {
                    "tags_strings": {
                        "path_match": "tags.*",
                        "match_mapping_type": "string",
                        "mapping": {"type": "keyword"},
                    }
                },
                {
                    "tags_numbers": {
                        "path_match": "tags.*",
                        "match_mapping_type": "long",
                        "mapping": {"type": "float"},
                    }
                },
                {
                    "tags_booleans": {
                        "path_match": "tags.*",
                        "match_mapping_type": "boolean",
                        "mapping": {"type": "boolean"},
                    }
                },
            ],
        },
    }
```

- [ ] **步骤 4：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_es_mapping.py -v
```

- [ ] **步骤 5：实现 es_sync_service.py（bulk index + alias reindex + check-sync）**

```python
# backend/app/services/es_sync_service.py
import time
from elasticsearch import AsyncElasticsearch
from app.config import settings

_es: AsyncElasticsearch | None = None

async def get_es() -> AsyncElasticsearch:
    global _es
    if _es is None:
        _es = AsyncElasticsearch(settings.es_url)
    return _es

async def close_es():
    global _es
    if _es:
        await _es.close()
        _es = None

def flatten_tag_values(tags: dict) -> list[str]:
    values = []
    for v in tags.values():
        if isinstance(v, list):
            values.extend(str(x) for x in v)
        elif isinstance(v, bool):
            continue
        elif v is not None:
            values.append(str(v))
    return values

def build_es_doc(row: dict) -> dict:
    return {
        "id": row["id"],
        "module_type": str(row["module_type"]),
        "name": row["name"],
        "resource_path": row["resource_path"],
        "thumbnail_path": row.get("thumbnail_path"),
        "tags": row["tags"],
        "version": row.get("version"),
        "file_size": row.get("file_size"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        "search_text": f"{row['name']} {' '.join(flatten_tag_values(row['tags']))}",
    }

async def bulk_index(docs: list[dict]) -> dict:
    es = await get_es()
    actions = []
    for doc in docs:
        actions.append({"index": {"_index": settings.es_index_alias, "_id": doc["id"]}})
        actions.append(doc)
    if not actions:
        return {"errors": False, "items": []}
    return await es.bulk(body=actions, refresh="wait_for")

async def reindex_with_alias(pool, index_body: dict) -> dict:
    """alias 切换模式全量重建"""
    es = await get_es()
    new_index = f"assets_v{int(time.time())}"
    await es.indices.create(index=new_index, body=index_body)

    batch_size = 500
    offset = 0
    total = 0
    async with pool.acquire() as conn:
        while True:
            rows = await conn.fetch(
                "SELECT * FROM assets ORDER BY id LIMIT $1 OFFSET $2",
                batch_size, offset,
            )
            if not rows:
                break
            docs = [build_es_doc(dict(r)) for r in rows]
            actions = []
            for doc in docs:
                actions.append({"index": {"_index": new_index, "_id": doc["id"]}})
                actions.append(doc)
            await es.bulk(body=actions)
            total += len(rows)
            offset += batch_size

    await es.indices.update_aliases(body={
        "actions": [
            {"remove": {"index": "*", "alias": settings.es_index_alias}},
            {"add": {"index": new_index, "alias": settings.es_index_alias}},
        ]
    })
    return {"new_index": new_index, "total_indexed": total}

async def check_sync(pool) -> dict:
    es = await get_es()
    async with pool.acquire() as conn:
        pg_count = await conn.fetchval("SELECT COUNT(*) FROM assets")
    es_resp = await es.count(index=settings.es_index_alias)
    es_count = es_resp["count"]
    return {
        "pg_count": pg_count,
        "es_count": es_count,
        "diff": pg_count - es_count,
        "in_sync": pg_count == es_count,
    }
```

- [ ] **步骤 6：Commit**

```bash
git add backend/app/services/es_mapping.py backend/app/services/es_sync_service.py backend/tests/
git commit -m "feat: add ES mapping generator + sync service (bulk, alias reindex, check-sync)"
```

---

## 阶段 4：数据导入

### 任务 6：Excel 导入器（模型 + 动作）

**文件：**
- 创建：`backend/app/importers/excel_importer.py`
- 创建：`backend/app/importers/wps_image_extractor.py`
- 测试：`backend/tests/test_excel_importer.py`

- [ ] **步骤 1：编写 Excel 导入测试**

```python
# backend/tests/test_excel_importer.py
from app.importers.excel_importer import (
    parse_multi_value, normalize_path, classify_sheet, COLUMN_MAP,
)

def test_parse_multi_value_newline():
    assert parse_multi_value("中原\n东海\n西南") == ["中原", "东海", "西南"]

def test_parse_multi_value_slash():
    assert parse_multi_value("中原 / 东海") == ["中原", "东海"]

def test_parse_multi_value_single():
    assert parse_multi_value("人") == ["人"]

def test_parse_multi_value_empty():
    assert parse_multi_value("") == []
    assert parse_multi_value(None) == []

def test_normalize_path():
    assert normalize_path("data\\source\\NPC_source\\P080\\模型\\P080.mdl") == \
           "data/source/NPC_source/P080/模型/P080.mdl"

def test_classify_sheet_model():
    assert classify_sheet("P080【完成】") == 1
    assert classify_sheet("M1【完成】") == 1
    assert classify_sheet("F2【完成】") == 1
    assert classify_sheet("A") == 1

def test_classify_sheet_action():
    assert classify_sheet("动作模组") == 3

def test_classify_sheet_skip():
    assert classify_sheet("通用规则") is None
    assert classify_sheet("进度统计") is None
    assert classify_sheet("WpsReserved_CellImgList") is None
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/test_excel_importer.py -v
```

- [ ] **步骤 3：实现 excel_importer.py**

```python
# backend/app/importers/excel_importer.py
import re
import uuid
import openpyxl
import asyncpg
from app.importers.wps_image_extractor import extract_wps_images
from app.services.es_sync_service import build_es_doc, bulk_index

COLUMN_MAP = {
    "资源完整路径": "resource_path", "截图": "_thumbnail",
    "物种": "species", "性别": "gender", "地域": "region",
    "势力": "faction", "职业": "profession", "体型": "body_type",
    "年龄": "age_group", "衣着": "clothing", "特征": "features",
    "专属NPC": "exclusive_npc", "备注": "remark",
}

ACTION_COLUMN_MAP = {
    "体型": "body_type", "动作模组": "action_module",
    "备注": "remark", "动作ID": "action_id", "动作类型": "action_type",
    "动作资源": "resource_path", "插槽": "slot_name",
    "插槽路径": "slot_path", "特效资源": "effect_path",
    "动作说明": "remark",
}

SKIP_SHEETS = {"通用规则", "进度统计", "需要新增的动作",
               "特效标签", "问题模型记录区", "WpsReserved_CellImgList"}

MULTI_VALUE_FIELDS = {"region", "faction", "profession", "clothing",
                      "features", "scene", "color", "description"}


def classify_sheet(name: str) -> int | None:
    if name in SKIP_SHEETS:
        return None
    if name == "动作模组":
        return 3
    if re.match(r'^[PMFA]\d{0,3}', name):
        return 1
    return None


def parse_multi_value(val) -> list[str]:
    if not val:
        return []
    s = str(val).strip()
    if not s:
        return []
    if "\n" in s:
        parts = s.split("\n")
    elif " / " in s:
        parts = s.split(" / ")
    else:
        parts = [s]
    return [p.strip() for p in parts if p.strip()]


def normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/").rstrip("\n").strip()


async def import_excel(
    filepath: str, pool: asyncpg.Pool, previews_dir: str,
) -> dict:
    batch_id = str(uuid.uuid4())[:8]
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    wps_images = extract_wps_images(filepath)

    stats = {"success": 0, "skipped": 0, "failed": 0, "es_sync_failed": 0}
    errors = []
    es_batch = []

    for sheet_name in wb.sheetnames:
        module_type = classify_sheet(sheet_name)
        if module_type is None:
            continue

        ws = wb[sheet_name]
        headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        col_map = ACTION_COLUMN_MAP if module_type == 3 else COLUMN_MAP

        for row_idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
            try:
                mapped = {}
                for col_idx, header in enumerate(headers):
                    if not header or header not in col_map:
                        continue
                    field = col_map[header]
                    val = row[col_idx] if col_idx < len(row) else None
                    if field == "_thumbnail":
                        continue
                    if field == "resource_path":
                        mapped["resource_path"] = normalize_path(str(val)) if val else ""
                        continue
                    if field == "action_id" and val is not None:
                        try:
                            mapped[field] = int(val)
                        except (ValueError, TypeError):
                            mapped[field] = None
                        continue
                    if field in MULTI_VALUE_FIELDS:
                        mapped[field] = parse_multi_value(val)
                    else:
                        mapped[field] = str(val).strip() if val else ""

                if not mapped.get("resource_path"):
                    stats["skipped"] += 1
                    continue

                resource_path = mapped.pop("resource_path")
                name = resource_path.rsplit("/", 1)[-1] if "/" in resource_path else resource_path
                tags = {k: v for k, v in mapped.items() if v}

                async with pool.acquire() as conn:
                    row_result = await conn.fetchrow(
                        """INSERT INTO assets (module_type, name, resource_path, tags)
                           VALUES ($1, $2, $3, $4::jsonb)
                           ON CONFLICT (module_type, resource_path)
                           DO UPDATE SET tags = $4::jsonb, updated_at = NOW()
                           RETURNING id, module_type, name, resource_path, thumbnail_path, tags, created_at, updated_at""",
                        module_type, name, resource_path,
                        __import__("json").dumps(tags, ensure_ascii=False),
                    )
                    es_batch.append(build_es_doc(dict(row_result)))
                    stats["success"] += 1

                    if len(es_batch) >= 500:
                        resp = await bulk_index(es_batch)
                        if resp.get("errors"):
                            for item in resp["items"]:
                                if "error" in item.get("index", {}):
                                    stats["es_sync_failed"] += 1
                        es_batch = []

            except Exception as e:
                stats["failed"] += 1
                errors.append({
                    "sheet": sheet_name, "row": row_idx,
                    "error": str(e),
                })

    if es_batch:
        resp = await bulk_index(es_batch)
        if resp.get("errors"):
            for item in resp["items"]:
                if "error" in item.get("index", {}):
                    stats["es_sync_failed"] += 1

    wb.close()
    return {"batch_id": batch_id, **stats, "errors": errors[:50]}
```

- [ ] **步骤 4：实现 wps_image_extractor.py**

```python
# backend/app/importers/wps_image_extractor.py
import re
import zipfile
import defusedxml.ElementTree as ET


def extract_wps_images(xlsx_path: str) -> dict[str, dict]:
    """
    提取 WPS DISPIMG 图片映射。
    返回 {sheet_name: {row_number: media_path}} 的嵌套字典。
    """
    result = {}
    try:
        with zipfile.ZipFile(xlsx_path) as zf:
            if "xl/cellimages.xml" not in zf.namelist():
                return result

            # Step 1: image_name → rId
            ci_xml = zf.read("xl/cellimages.xml").decode("utf-8")
            name_to_rid = {}
            ci_root = ET.fromstring(ci_xml)
            for elem in ci_root.iter():
                if elem.tag.endswith("cellImage"):
                    name = None
                    rid = None
                    for child in elem.iter():
                        if child.tag.endswith("cNvPr"):
                            name = child.get("name")
                        if child.tag.endswith("blip"):
                            for attr_name, attr_val in child.attrib.items():
                                if attr_name.endswith("}embed"):
                                    rid = attr_val
                    if name and rid:
                        name_to_rid[name] = rid

            # Step 2: rId → media path
            rels_xml = zf.read("xl/_rels/cellimages.xml.rels").decode("utf-8")
            rels_root = ET.fromstring(rels_xml)
            rid_to_path = {}
            for rel in rels_root.iter():
                if rel.tag.endswith("Relationship"):
                    rid_to_path[rel.get("Id")] = rel.get("Target")

            # Step 3: per-sheet DISPIMG formulas → row mapping
            for fname in zf.namelist():
                if not fname.startswith("xl/worksheets/sheet") or not fname.endswith(".xml"):
                    continue
                sheet_xml = zf.read(fname).decode("utf-8")
                matches = re.findall(
                    r'<c r="([A-Z]+)(\d+)"[^>]*>.*?<f[^>]*>.*?DISPIMG\("([^"]+)"',
                    sheet_xml, re.DOTALL,
                )
                if not matches:
                    continue
                sheet_name = fname.split("/")[-1].replace(".xml", "")
                sheet_map = {}
                for col, row_str, img_name in matches:
                    row_num = int(row_str)
                    rid = name_to_rid.get(img_name)
                    if rid:
                        media_path = rid_to_path.get(rid)
                        if media_path:
                            sheet_map[row_num] = f"xl/{media_path}"
                result[sheet_name] = sheet_map

    except Exception:
        pass

    return result
```

- [ ] **步骤 5：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_excel_importer.py -v
```

- [ ] **步骤 6：Commit**

```bash
git add backend/app/importers/
git commit -m "feat: add Excel importer (models+actions) + WPS image extractor"
```

---

### 任务 7：HTML 特效导入器

**文件：**
- 创建：`backend/app/importers/html_importer.py`
- 测试：`backend/tests/test_html_importer.py`

- [ ] **步骤 1：编写标签分类测试**

```python
# backend/tests/test_html_importer.py
from app.importers.html_importer import classify_tag, extract_duration

def test_classify_tag_size():
    assert classify_tag("中型特效") == ("size", "中型特效")
    assert classify_tag("贴地/扁平特效") == ("size", "贴地/扁平特效")
    assert classify_tag("长条/细长") == ("size", "长条/细长")

def test_classify_tag_duration_label():
    assert classify_tag("中等时长") == ("duration_label", "中等时长")
    assert classify_tag("超长时长") == ("duration_label", "超长时长")

def test_classify_tag_color():
    assert classify_tag("红色") == ("color", "红色")
    assert classify_tag("蓝白闪光") is None  # 描述性，不是纯颜色

def test_classify_tag_scene():
    assert classify_tag("技能") == ("scene", "技能")
    assert classify_tag("被击") == ("scene", "被击")

def test_classify_tag_shape():
    assert classify_tag("近方形/圆形占位") == ("shape", "近方形/圆形占位")
    assert classify_tag("横向延展") == ("shape", "横向延展")

def test_extract_duration():
    assert extract_duration("时长约2.5秒") == 2.5
    assert extract_duration("时长约10.0秒") == 10.0
    assert extract_duration("中等时长") is None
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/test_html_importer.py -v
```

- [ ] **步骤 3：实现 html_importer.py**

```python
# backend/app/importers/html_importer.py
import re
import base64
import uuid
from pathlib import Path
from PIL import Image
from io import BytesIO
import asyncpg
from app.services.es_sync_service import build_es_doc, bulk_index

SIZE_KEYWORDS = {"小型特效", "中型特效", "大型特效", "贴地/扁平特效", "长条/细长"}
DURATION_LABELS = {"短时长", "中等时长", "长时长", "超长时长"}
SCENE_KEYWORDS = {"技能", "子弹", "被击", "蓄力", "buff", "场景"}
SHAPE_KEYWORDS = {"近方形/圆形占位", "横向延展", "2x45矩形"}
COLOR_EXACT = {"红色","蓝色","金色","紫色","白色","黑色","绿色","黄色","橙色","青色","灰色","粉色"}
DURATION_RE = re.compile(r"时长约([\d.]+)秒")


def classify_tag(tag: str) -> tuple[str, str] | None:
    if tag in SIZE_KEYWORDS:
        return ("size", tag)
    if tag in DURATION_LABELS:
        return ("duration_label", tag)
    if tag in COLOR_EXACT:
        return ("color", tag)
    if tag in SCENE_KEYWORDS:
        return ("scene", tag)
    if tag in SHAPE_KEYWORDS:
        return ("shape", tag)
    return None


def extract_duration(tag: str) -> float | None:
    m = DURATION_RE.match(tag)
    return float(m.group(1)) if m else None


def parse_effect_tags(flat_tags: list[str]) -> dict:
    tags = {
        "scene": [], "color": [], "description": [],
        "size": "", "shape": "", "duration": None,
        "duration_label": "", "source_name": "",
    }
    for t in flat_tags:
        dur = extract_duration(t)
        if dur is not None:
            tags["duration"] = dur
            continue
        classified = classify_tag(t)
        if classified:
            field, val = classified
            if field in ("scene", "color"):
                tags[field].append(val)
            else:
                tags[field] = val
        else:
            tags["description"].append(t)

    if tags["description"]:
        tags["source_name"] = tags["description"][0]
    tags = {k: v for k, v in tags.items() if v}
    return tags


async def import_html_effects(
    html_path: str, pool: asyncpg.Pool, previews_dir: str,
) -> dict:
    batch_id = str(uuid.uuid4())[:8]
    html = Path(html_path).read_text(encoding="utf-8")

    rows = re.findall(
        r'<tr><td class="path">(.*?)</td><td class="tags">(.*?)</td><td>(.*?)</td></tr>',
        html, re.DOTALL,
    )

    stats = {"success": 0, "failed": 0, "es_sync_failed": 0}
    es_batch = []
    preview_dir = Path(previews_dir) / "2"
    preview_dir.mkdir(parents=True, exist_ok=True)

    for path_html, tags_html, img_html in rows:
        try:
            resource_path = path_html.strip()
            flat_tags = re.findall(r'<span class="tag">(.*?)</span>', tags_html)
            tags = parse_effect_tags(flat_tags)
            name = resource_path.rsplit("/", 1)[-1] if "/" in resource_path else resource_path

            async with pool.acquire() as conn:
                row_result = await conn.fetchrow(
                    """INSERT INTO assets (module_type, name, resource_path, tags)
                       VALUES (2, $1, $2, $3::jsonb)
                       ON CONFLICT (module_type, resource_path)
                       DO UPDATE SET tags = $3::jsonb, updated_at = NOW()
                       RETURNING id, module_type, name, resource_path, thumbnail_path, tags, created_at, updated_at""",
                    name, resource_path,
                    __import__("json").dumps(tags, ensure_ascii=False),
                )
                asset_id = row_result["id"]

                # Extract base64 APNG preview
                b64_match = re.search(r'src="data:image/png;base64,([^"]+)"', img_html)
                if b64_match:
                    img_data = base64.b64decode(b64_match.group(1))
                    apng_path = preview_dir / f"{asset_id}.apng"
                    apng_path.write_bytes(img_data)
                    thumb_path = preview_dir / f"{asset_id}_thumb.png"
                    img = Image.open(BytesIO(img_data))
                    img.seek(0)
                    img.save(str(thumb_path), "PNG")
                    img.close()
                    thumb_rel = f"2/{asset_id}_thumb.png"
                    await conn.execute(
                        "UPDATE assets SET thumbnail_path=$1 WHERE id=$2",
                        thumb_rel, asset_id,
                    )
                    row_result = await conn.fetchrow(
                        "SELECT * FROM assets WHERE id=$1", asset_id,
                    )

                es_batch.append(build_es_doc(dict(row_result)))
                stats["success"] += 1

        except Exception as e:
            stats["failed"] += 1

    if es_batch:
        resp = await bulk_index(es_batch)
        if resp.get("errors"):
            for item in resp["items"]:
                if "error" in item.get("index", {}):
                    stats["es_sync_failed"] += 1

    return {"batch_id": batch_id, **stats}
```

- [ ] **步骤 4：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_html_importer.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add backend/app/importers/html_importer.py backend/tests/test_html_importer.py
git commit -m "feat: add HTML effects importer with tag classification + APNG extraction"
```

---

## 阶段 5：搜索引擎核心

### 任务 8：TTLCache 封装

**文件：**
- 创建：`backend/app/services/cache.py`

- [ ] **步骤 1：实现 cache.py**

```python
# backend/app/services/cache.py
from cachetools import TTLCache
from app.config import settings

parse_cache: TTLCache = TTLCache(
    maxsize=settings.parse_cache_maxsize,
    ttl=settings.parse_cache_ttl,
)

tag_defs_cache: TTLCache = TTLCache(maxsize=100, ttl=settings.tag_cache_ttl)

def get_parse_cache_key(module_type: int, query: str) -> tuple:
    return (module_type, query)

def clear_all_caches():
    parse_cache.clear()
    tag_defs_cache.clear()
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/services/cache.py
git commit -m "feat: add TTLCache for parse results and tag definitions"
```

---

### 任务 9：词典匹配器

**文件：**
- 创建：`backend/app/services/dictionary_matcher.py`
- 测试：`backend/tests/test_dictionary_matcher.py`

- [ ] **步骤 1：编写词典匹配测试**

```python
# backend/tests/test_dictionary_matcher.py
from app.services.dictionary_matcher import DictionaryMatcher

def make_matcher():
    m = DictionaryMatcher()
    m.load_from_data(
        tag_values={
            (1, "gender"): ["男", "女"],
            (1, "profession"): ["刺客", "僧侣", "战士", "书生"],
            (1, "region"): ["中原", "东海", "西南"],
            (1, "faction"): ["少林", "藏剑", "七秀"],
            (1, "body_type"): ["标准", "壮硕", "瘦子"],
        },
        synonyms=[
            {"module_type": 1, "field_name": "profession",
             "target_value": "僧侣", "synonym": "和尚", "priority": 10},
            {"module_type": 1, "field_name": "body_type",
             "target_value": "壮硕", "synonym": "壮", "priority": 5},
        ],
    )
    return m

def test_full_match():
    m = make_matcher()
    result = m.match(1, "女 刺客 中原")
    assert result.matched == {"gender": "女", "profession": ["刺客"], "region": ["中原"]}
    assert result.remaining == ""

def test_partial_match_with_remaining():
    m = make_matcher()
    result = m.match(1, "红衣女刺客 中原")
    assert "gender" in result.matched
    assert "profession" in result.matched
    assert "红衣" in result.remaining

def test_synonym_match():
    m = make_matcher()
    result = m.match(1, "壮老和尚 少林")
    assert result.matched.get("body_type") == "壮硕"
    assert "僧侣" in result.matched.get("profession", [])
    assert result.matched.get("faction") == ["少林"]

def test_prefix_search():
    m = make_matcher()
    suggestions = m.prefix_search(1, "刺")
    assert any(s["text"] == "刺客" for s in suggestions)
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/test_dictionary_matcher.py -v
```

- [ ] **步骤 3：实现 dictionary_matcher.py**

```python
# backend/app/services/dictionary_matcher.py
from dataclasses import dataclass, field

@dataclass
class MatchResult:
    matched: dict = field(default_factory=dict)
    remaining: str = ""

class DictionaryMatcher:
    def __init__(self):
        self._tokens: dict[int, dict[str, list[tuple[str, str, int]]]] = {}
        self._all_values: dict[int, list[dict]] = {}

    def load_from_data(
        self,
        tag_values: dict[tuple[int, str], list[str]],
        synonyms: list[dict],
    ):
        self._tokens = {}
        self._all_values = {}
        for (mod, field_name), values in tag_values.items():
            mod_tokens = self._tokens.setdefault(mod, {})
            mod_vals = self._all_values.setdefault(mod, [])
            for val in values:
                entries = mod_tokens.setdefault(val, [])
                entries.append((field_name, val, 0))
                mod_vals.append({"text": val, "field": field_name})

        for syn in synonyms:
            mod = syn["module_type"]
            mod_tokens = self._tokens.setdefault(mod, {})
            entries = mod_tokens.setdefault(syn["synonym"], [])
            entries.append((syn["field_name"], syn["target_value"], syn["priority"]))

    async def load_from_db(self, pool):
        async with pool.acquire() as conn:
            defs = await conn.fetch(
                "SELECT module_type, field_name FROM tag_definitions"
            )
            vals = await conn.fetch(
                """SELECT td.module_type, td.field_name, tv.value
                   FROM tag_values tv
                   JOIN tag_definitions td ON tv.definition_id = td.id
                   WHERE tv.is_active = true"""
            )
            syns = await conn.fetch("SELECT * FROM tag_synonyms")

        tag_values = {}
        for v in vals:
            key = (v["module_type"], v["field_name"])
            tag_values.setdefault(key, []).append(v["value"])

        self.load_from_data(
            tag_values=tag_values,
            synonyms=[dict(s) for s in syns],
        )

    def match(self, module_type: int, query: str) -> MatchResult:
        tokens = self._tokens.get(module_type, {})
        if not tokens:
            return MatchResult(remaining=query)

        segments = query.split()
        matched: dict[str, list | str] = {}
        remaining_parts = []

        for segment in segments:
            seg_matched, seg_remaining = self._match_segment(segment, tokens)
            for field_name, value in seg_matched.items():
                if field_name in matched:
                    existing = matched[field_name]
                    if isinstance(existing, list):
                        if value not in existing:
                            existing.append(value)
                    else:
                        if existing != value:
                            matched[field_name] = [existing, value]
                else:
                    matched[field_name] = value
            if seg_remaining:
                remaining_parts.append(seg_remaining)

        # Normalize: multi-value fields always lists
        MULTI_FIELDS = {"region","faction","profession","clothing","features",
                        "scene","color","description"}
        for k, v in matched.items():
            if k in MULTI_FIELDS and not isinstance(v, list):
                matched[k] = [v]

        return MatchResult(matched=matched, remaining=" ".join(remaining_parts))

    def _match_segment(
        self, text: str, tokens: dict
    ) -> tuple[dict[str, str], str]:
        matched = {}
        remaining = []
        i = 0
        while i < len(text):
            best_len = 0
            best_field = None
            best_value = None
            for length in range(min(len(text) - i, 10), 0, -1):
                candidate = text[i : i + length]
                entries = tokens.get(candidate)
                if entries:
                    top = max(entries, key=lambda e: e[2])
                    best_len = length
                    best_field = top[0]
                    best_value = top[1]
                    break
            if best_len > 0:
                matched[best_field] = best_value
                i += best_len
            else:
                remaining.append(text[i])
                i += 1
        return matched, "".join(remaining)

    def prefix_search(self, module_type: int, prefix: str, limit: int = 10) -> list[dict]:
        vals = self._all_values.get(module_type, [])
        results = []
        for item in vals:
            if item["text"].startswith(prefix):
                results.append(item)
                if len(results) >= limit:
                    break
        return results
```

- [ ] **步骤 4：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_dictionary_matcher.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add backend/app/services/dictionary_matcher.py backend/tests/test_dictionary_matcher.py
git commit -m "feat: add dictionary matcher with forward longest match + synonym support"
```

---

### 任务 10：LLM 解析服务 + 校验层

**文件：**
- 创建：`backend/app/services/llm_parse_service.py`
- 创建：`backend/app/services/parse_validator.py`
- 创建：`backend/app/services/parse_service.py`
- 测试：`backend/tests/test_parse_validator.py`

- [ ] **步骤 1：编写校验层测试**

```python
# backend/tests/test_parse_validator.py
from app.services.parse_validator import validate_llm_result

def test_validate_valid_enum():
    valid_values = {"gender": {"男", "女"}, "body_type": {"标准", "壮硕"}}
    result = {"filter": {"gender": "女", "body_type": "标准"}, "keyword": "", "confidence": 0.9}
    validated = validate_llm_result(result, valid_values)
    assert validated["filter"]["gender"] == "女"
    assert validated["demoted_to_keyword"] == []

def test_validate_invalid_enum_demotes():
    valid_values = {"gender": {"男", "女"}}
    result = {"filter": {"gender": "外星人"}, "keyword": "", "confidence": 0.8}
    validated = validate_llm_result(result, valid_values)
    assert "gender" not in validated["filter"]
    assert "外星人" in validated["keyword"]

def test_validate_number_condition():
    valid_values = {}
    result = {"filter": {"duration": {"op": ">", "value": 5}}, "keyword": "", "confidence": 0.9}
    validated = validate_llm_result(result, valid_values, number_fields={"duration"})
    assert validated["filter"]["duration"] == {"op": ">", "value": 5}

def test_validate_unknown_dimension():
    valid_values = {"gender": {"男", "女"}}
    result = {"filter": {"nonexistent": "abc"}, "keyword": "test", "confidence": 0.5}
    validated = validate_llm_result(result, valid_values)
    assert "nonexistent" not in validated["filter"]
    assert "abc" in validated["keyword"]
```

- [ ] **步骤 2：运行测试确认失败**

- [ ] **步骤 3：实现 parse_validator.py**

```python
# backend/app/services/parse_validator.py

VALID_OPS = {">", "<", ">=", "<=", "=="}

def validate_llm_result(
    result: dict,
    valid_values: dict[str, set[str]],
    number_fields: set[str] | None = None,
    boolean_fields: set[str] | None = None,
) -> dict:
    number_fields = number_fields or set()
    boolean_fields = boolean_fields or set()
    known_fields = set(valid_values.keys()) | number_fields | boolean_fields

    validated_filter = {}
    demoted = []

    for field, value in result.get("filter", {}).items():
        if field not in known_fields:
            demoted.append(str(value))
            continue
        if field in number_fields:
            if isinstance(value, dict) and value.get("op") in VALID_OPS:
                try:
                    value["value"] = float(value["value"])
                    validated_filter[field] = value
                except (ValueError, TypeError):
                    demoted.append(f"{field}:{value}")
            continue
        if field in boolean_fields:
            validated_filter[field] = bool(value)
            continue
        if field in valid_values:
            if isinstance(value, list):
                valid = [v for v in value if v in valid_values[field]]
                invalid = [v for v in value if v not in valid_values[field]]
                if valid:
                    validated_filter[field] = valid
                demoted.extend(invalid)
            elif value in valid_values[field]:
                validated_filter[field] = value
            else:
                demoted.append(str(value))
        else:
            validated_filter[field] = value

    original_keyword = result.get("keyword", "")
    extra = " ".join(demoted)
    keyword = f"{original_keyword} {extra}".strip() if extra else original_keyword

    return {
        "filter": validated_filter,
        "keyword": keyword,
        "confidence": result.get("confidence", 0.0),
        "demoted_to_keyword": demoted,
    }
```

- [ ] **步骤 4：实现 llm_parse_service.py**

```python
# backend/app/services/llm_parse_service.py
import json
import httpx
from app.config import settings

PROMPT_TEMPLATE = """你是一个游戏资产搜索系统的查询解析器。
系统已识别出: {already_matched}
以下是尚未匹配的剩余文本，请尝试从中提取更多标签。

尚未匹配的标签维度:
{unmatched_tag_schema}

规则:
1. 只提取有把握的标签，不确定的放入 keyword
2. 数值条件用 {{"op":">","value":5}} 格式
3. 描述性/模糊性词语放入 keyword
4. 返回严格JSON

剩余文本: {remaining_text}

返回: {{"filter":{{}},"keyword":"","confidence":0.0}}"""


async def call_llm(
    remaining_text: str,
    already_matched: dict,
    unmatched_schema: list[dict],
) -> dict | None:
    if not settings.llm_enabled or not settings.llm_api_key:
        return None

    schema_str = "\n".join(
        f"- {d['field_name']}({d['display_name']}): {d['field_type']}"
        + (f", 可选值: {d.get('values', [])}" if d.get("values") else "")
        for d in unmatched_schema
    )
    prompt = PROMPT_TEMPLATE.format(
        already_matched=json.dumps(already_matched, ensure_ascii=False),
        unmatched_tag_schema=schema_str,
        remaining_text=remaining_text,
    )

    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 256,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(content)
    except Exception:
        return None
```

- [ ] **步骤 5：实现 parse_service.py（搜索解析编排）**

```python
# backend/app/services/parse_service.py
import time
from app.services.cache import parse_cache, get_parse_cache_key
from app.services.dictionary_matcher import DictionaryMatcher, MatchResult
from app.services.llm_parse_service import call_llm
from app.services.parse_validator import validate_llm_result

_matcher = DictionaryMatcher()

def get_matcher() -> DictionaryMatcher:
    return _matcher

async def init_matcher(pool):
    await _matcher.load_from_db(pool)

async def parse_query(
    module_type: int,
    query: str,
    tag_definitions: list[dict],
    valid_values: dict[str, set[str]],
    number_fields: set[str],
    boolean_fields: set[str],
) -> dict:
    start = time.monotonic()
    cache_key = get_parse_cache_key(module_type, query)
    cached = parse_cache.get(cache_key)
    if cached is not None:
        cached["parse_source"] = "cache"
        cached["parse_time_ms"] = 0
        return cached

    dict_result: MatchResult = _matcher.match(module_type, query)
    source = "dict"

    llm_filter = {}
    llm_keyword = ""
    confidence = 1.0

    remaining = dict_result.remaining.strip()
    if remaining and len(remaining) > 1:
        unmatched_dims = [
            d for d in tag_definitions
            if d["field_name"] not in dict_result.matched
            and d["is_searchable"]
        ]
        llm_result = await call_llm(remaining, dict_result.matched, unmatched_dims)
        if llm_result:
            validated = validate_llm_result(
                llm_result, valid_values, number_fields, boolean_fields,
            )
            llm_filter = validated["filter"]
            llm_keyword = validated["keyword"]
            confidence = validated["confidence"]
            source = "dict+llm"
        else:
            llm_keyword = remaining
            confidence = 0.0
            source = "dict+fallback"
    elif remaining:
        llm_keyword = remaining
        confidence = 1.0

    merged = {**dict_result.matched, **llm_filter}
    elapsed_ms = int((time.monotonic() - start) * 1000)

    result = {
        "parsed_filters": merged,
        "keyword": llm_keyword,
        "confidence": confidence,
        "parse_source": source,
        "fallback": source.endswith("fallback"),
        "parse_time_ms": elapsed_ms,
    }
    parse_cache[cache_key] = result
    return result
```

- [ ] **步骤 6：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_parse_validator.py -v
```

- [ ] **步骤 7：Commit**

```bash
git add backend/app/services/llm_parse_service.py backend/app/services/parse_validator.py \
        backend/app/services/parse_service.py backend/tests/test_parse_validator.py
git commit -m "feat: add NLP parse pipeline (LLM + validator + cache + orchestration)"
```

---

### 任务 11：ES 查询构建器

**文件：**
- 创建：`backend/app/services/es_query_builder.py`
- 测试：`backend/tests/test_es_query_builder.py`

- [ ] **步骤 1：编写 ES 查询构建测试**

```python
# backend/tests/test_es_query_builder.py
from app.services.es_query_builder import build_search_query

def test_filter_only():
    q = build_search_query(
        module_type=1,
        filters={"gender": "女", "profession": ["刺客"]},
        page=1, page_size=20,
        filterable_fields=["gender", "profession"],
    )
    bool_filter = q["query"]["function_score"]["query"]["bool"]["filter"]
    assert {"term": {"module_type": "1"}} in bool_filter
    assert {"term": {"tags.gender": "女"}} in bool_filter
    assert {"terms": {"tags.profession": ["刺客"]}} in bool_filter

def test_keyword_search():
    q = build_search_query(
        module_type=1,
        keyword="红衣",
        page=1, page_size=20,
    )
    must = q["query"]["function_score"]["query"]["bool"]["must"]
    assert any("match" in clause for clause in must)

def test_range_condition():
    q = build_search_query(
        module_type=2,
        conditions=[{"field": "duration", "op": ">", "value": 5}],
        page=1, page_size=20,
    )
    bool_filter = q["query"]["function_score"]["query"]["bool"]["filter"]
    assert any("range" in f for f in bool_filter)

def test_pagination():
    q = build_search_query(module_type=1, page=3, page_size=20)
    assert q["from"] == 40
    assert q["size"] == 20

def test_dynamic_function_score():
    q = build_search_query(
        module_type=1,
        filters={"gender": "女", "profession": ["刺客"]},
        page=1, page_size=20,
        filterable_fields=["gender", "profession"],
    )
    functions = q["query"]["function_score"]["functions"]
    filter_funcs = [f for f in functions if "filter" in f]
    assert len(filter_funcs) == 2
```

- [ ] **步骤 2：运行测试确认失败**

- [ ] **步骤 3：实现 es_query_builder.py**

```python
# backend/app/services/es_query_builder.py
from app.config import settings

OP_MAP = {">": "gt", "<": "lt", ">=": "gte", "<=": "lte", "==": "gte"}

def build_search_query(
    module_type: int,
    filters: dict | None = None,
    keyword: str = "",
    conditions: list[dict] | None = None,
    sort: dict | None = None,
    page: int = 1,
    page_size: int = 20,
    filterable_fields: list[str] | None = None,
    agg_fields: list[str] | None = None,
) -> dict:
    filters = filters or {}
    conditions = conditions or []
    filterable_fields = filterable_fields or []
    agg_fields = agg_fields or []

    bool_filter = [{"term": {"module_type": str(module_type)}}]
    bool_must = []

    for field, value in filters.items():
        if isinstance(value, list):
            bool_filter.append({"terms": {f"tags.{field}": value}})
        elif isinstance(value, dict) and "op" in value:
            es_op = OP_MAP.get(value["op"], "gte")
            range_q = {f"tags.{field}": {es_op: value["value"]}}
            if value["op"] == "==":
                range_q[f"tags.{field}"]["lte"] = value["value"]
            bool_filter.append({"range": range_q})
        else:
            bool_filter.append({"term": {f"tags.{field}": value}})

    for cond in conditions:
        es_op = OP_MAP.get(cond["op"], "gte")
        range_q = {f"tags.{cond['field']}": {es_op: cond["value"]}}
        if cond["op"] == "==":
            range_q[f"tags.{cond['field']}"]["lte"] = cond["value"]
        bool_filter.append({"range": range_q})

    if keyword:
        bool_must.append({
            "match": {
                "search_text": {
                    "query": keyword,
                    "analyzer": "ik_smart",
                }
            }
        })

    bool_query = {"filter": bool_filter}
    if bool_must:
        bool_query["must"] = bool_must

    # Dynamic function_score: each matched filter adds weight=10
    score_functions = []
    for field, value in filters.items():
        if isinstance(value, list):
            score_functions.append({
                "filter": {"terms": {f"tags.{field}": value}},
                "weight": 10,
            })
        elif not isinstance(value, dict):
            score_functions.append({
                "filter": {"term": {f"tags.{field}": value}},
                "weight": 10,
            })
    score_functions.append({
        "linear": {
            "updated_at": {"origin": "now", "scale": "30d", "decay": 0.5}
        }
    })

    query = {
        "query": {
            "function_score": {
                "query": {"bool": bool_query},
                "functions": score_functions,
                "score_mode": "sum",
                "boost_mode": "sum",
            }
        },
        "from": (page - 1) * page_size,
        "size": page_size,
        "highlight": {
            "fields": {
                "search_text": {"pre_tags": ["<em>"], "post_tags": ["</em>"]},
                "name": {"pre_tags": ["<em>"], "post_tags": ["</em>"]},
            }
        },
    }

    # Aggregations
    if agg_fields:
        aggs = {}
        for field in agg_fields:
            aggs[field] = {"terms": {"field": f"tags.{field}", "size": 50}}
        query["aggs"] = aggs

    return query
```

- [ ] **步骤 4：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_es_query_builder.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add backend/app/services/es_query_builder.py backend/tests/test_es_query_builder.py
git commit -m "feat: add ES query builder with dynamic function_score + aggs + highlight"
```

---

### 任务 12：搜索编排服务

**文件：**
- 创建：`backend/app/services/search_service.py`

- [ ] **步骤 1：实现 search_service.py**

```python
# backend/app/services/search_service.py
import time
from elasticsearch import AsyncElasticsearch
from app.services.es_sync_service import get_es
from app.services.es_query_builder import build_search_query
from app.services.parse_service import parse_query
from app.services.cache import tag_defs_cache
from app.config import settings
from app.models.schemas import (
    SearchRequest, SearchResponse, ParseInfo, AssetItem,
    FacetValue, IgnoredTag,
)

async def get_tag_definitions(pool, module_type: int) -> list[dict]:
    cache_key = f"tag_defs:{module_type}"
    cached = tag_defs_cache.get(cache_key)
    if cached:
        return cached

    async with pool.acquire() as conn:
        defs = await conn.fetch(
            """SELECT td.*, array_agg(tv.value) FILTER (WHERE tv.value IS NOT NULL) as values
               FROM tag_definitions td
               LEFT JOIN tag_values tv ON tv.definition_id = td.id AND tv.is_active
               WHERE td.module_type = $1
               GROUP BY td.id
               ORDER BY td.sort_order""",
            module_type,
        )
    result = [dict(d) for d in defs]
    tag_defs_cache[cache_key] = result
    return result


async def search(req: SearchRequest, pool) -> SearchResponse:
    start = time.monotonic()
    tag_defs = await get_tag_definitions(pool, req.module_type)

    filterable = [d["field_name"] for d in tag_defs if d["is_filterable"]]
    agg_fields = [d["field_name"] for d in tag_defs
                  if d["is_filterable"] and d["field_type"] in ("enum_single", "enum_multi")]
    valid_values = {}
    number_fields = set()
    boolean_fields = set()
    for d in tag_defs:
        if d["field_type"] in ("enum_single", "enum_multi") and d.get("values"):
            valid_values[d["field_name"]] = set(d["values"])
        elif d["field_type"] == "number_range":
            number_fields.add(d["field_name"])
        elif d["field_type"] == "boolean":
            boolean_fields.add(d["field_name"])

    parse_info = None
    effective_filters = dict(req.filters)
    keyword = ""
    ignored_tags = []

    if req.query:
        parsed = await parse_query(
            req.module_type, req.query, tag_defs,
            valid_values, number_fields, boolean_fields,
        )
        keyword = parsed.get("keyword", "")

        for field, value in parsed["parsed_filters"].items():
            if field in req.filters:
                ignored_tags.append(IgnoredTag(
                    field=field,
                    value=str(value),
                    reason="overridden_by_manual_filter",
                ))
            else:
                effective_filters[field] = value

        parse_info = ParseInfo(
            parsed_filters=parsed["parsed_filters"],
            effective_filters=effective_filters,
            ignored_tags=ignored_tags,
            keyword=keyword,
            confidence=parsed.get("confidence", 0.0),
            fallback=parsed.get("fallback", False),
            parse_source=parsed.get("parse_source", ""),
            parse_time_ms=parsed.get("parse_time_ms", 0),
        )

    es_query = build_search_query(
        module_type=req.module_type,
        filters=effective_filters,
        keyword=keyword,
        conditions=[c.model_dump() for c in req.conditions],
        sort=req.sort.model_dump() if req.sort else None,
        page=req.page,
        page_size=req.page_size,
        filterable_fields=filterable,
        agg_fields=agg_fields,
    )

    es = await get_es()
    es_resp = await es.search(index=settings.es_index_alias, body=es_query)

    items = []
    for hit in es_resp["hits"]["hits"]:
        src = hit["_source"]
        items.append(AssetItem(
            id=src["id"],
            name=src["name"],
            resource_path=src["resource_path"],
            thumbnail_path=src.get("thumbnail_path"),
            tags=src.get("tags", {}),
            relevance_score=hit.get("_score", 0),
            highlight=hit.get("highlight", {}),
        ))

    facets = {}
    for field, agg_data in es_resp.get("aggregations", {}).items():
        facets[field] = [
            FacetValue(value=bucket["key"], count=bucket["doc_count"])
            for bucket in agg_data.get("buckets", [])
        ]

    elapsed = int((time.monotonic() - start) * 1000)
    return SearchResponse(
        total=es_resp["hits"]["total"]["value"],
        page=req.page,
        page_size=req.page_size,
        parse_info=parse_info,
        items=items,
        facets=facets,
        query_time_ms=elapsed,
    )
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/services/search_service.py
git commit -m "feat: add search orchestration service"
```

---

## 阶段 6：API 路由

### 任务 13：搜索 + 筛选 + 管理 API 路由

**文件：**
- 创建：`backend/app/routers/search.py`
- 创建：`backend/app/routers/filter.py`
- 创建：`backend/app/routers/assets.py`
- 创建：`backend/app/routers/admin.py`
- 修改：`backend/app/main.py`（挂载路由 + lifespan 初始化词典和 ES）

- [ ] **步骤 1：实现 search.py 路由**

```python
# backend/app/routers/search.py
from fastapi import APIRouter, Depends
from app.models.schemas import SearchRequest, SearchResponse, SuggestionsResponse
from app.models.database import get_pool
from app.services.search_service import search
from app.services.parse_service import get_matcher

router = APIRouter(prefix="/api/v1/search", tags=["search"])

@router.post("/query", response_model=SearchResponse)
async def search_query(req: SearchRequest):
    pool = await get_pool()
    return await search(req, pool)

@router.get("/suggestions", response_model=SuggestionsResponse)
async def suggestions(module_type: int, q: str = ""):
    matcher = get_matcher()
    items = matcher.prefix_search(module_type, q, limit=10)
    return SuggestionsResponse(
        suggestions=[{"text": i["text"], "field": i["field"], "type": "tag"} for i in items]
    )
```

- [ ] **步骤 2：实现 filter.py 路由**

```python
# backend/app/routers/filter.py
from fastapi import APIRouter
from app.models.database import get_pool
from app.services.search_service import get_tag_definitions
from app.models.schemas import TagDefinitionOut

router = APIRouter(prefix="/api/v1/filter", tags=["filter"])

@router.get("/definitions/{module_type}", response_model=list[TagDefinitionOut])
async def get_definitions(module_type: int):
    pool = await get_pool()
    defs = await get_tag_definitions(pool, module_type)
    result = []
    for d in defs:
        if not d["is_filterable"]:
            continue
        result.append(TagDefinitionOut(
            id=d["id"], field_name=d["field_name"],
            display_name=d["display_name"], field_type=d["field_type"],
            is_filterable=d["is_filterable"], is_searchable=d["is_searchable"],
            sort_order=d["sort_order"], config=d.get("config", {}),
            values=[{"value": v, "display_name": v} for v in (d.get("values") or []) if v],
        ))
    return result
```

- [ ] **步骤 3：实现 admin.py 路由（含 X-Admin-Key 鉴权）**

```python
# backend/app/routers/admin.py
from fastapi import APIRouter, Header, HTTPException, UploadFile, File
from app.config import settings
from app.models.database import get_pool
from app.services.es_sync_service import reindex_with_alias, check_sync
from app.services.es_mapping import build_index_settings_and_mappings
from app.services.search_service import get_tag_definitions
from app.services.parse_service import init_matcher
from app.services.cache import clear_all_caches
from app.importers.excel_importer import import_excel
from app.importers.html_importer import import_html_effects
import tempfile, os

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

def verify_admin(x_admin_key: str = Header(...)):
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")

@router.post("/reindex-es")
async def reindex_es(x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    pool = await get_pool()
    all_defs = []
    for mod in [1, 2, 3]:
        defs = await get_tag_definitions(pool, mod)
        all_defs.extend(defs)
    index_body = build_index_settings_and_mappings(all_defs)
    result = await reindex_with_alias(pool, index_body)
    return result

@router.get("/check-sync")
async def admin_check_sync(x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    pool = await get_pool()
    return await check_sync(pool)

@router.post("/refresh-dictionary")
async def refresh_dictionary(x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    pool = await get_pool()
    await init_matcher(pool)
    clear_all_caches()
    return {"status": "refreshed"}

@router.post("/import-excel")
async def admin_import_excel(
    file: UploadFile = File(...),
    x_admin_key: str = Header(...),
):
    verify_admin(x_admin_key)
    pool = await get_pool()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = await import_excel(tmp_path, pool, "/data/previews")
        await init_matcher(pool)
        return result
    finally:
        os.unlink(tmp_path)

@router.post("/import-effects-html")
async def admin_import_effects(
    file: UploadFile = File(...),
    x_admin_key: str = Header(...),
):
    verify_admin(x_admin_key)
    pool = await get_pool()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = await import_html_effects(tmp_path, pool, "/data/previews")
        await init_matcher(pool)
        return result
    finally:
        os.unlink(tmp_path)
```

- [ ] **步骤 4：实现 assets.py 路由**

```python
# backend/app/routers/assets.py
from fastapi import APIRouter, HTTPException
from app.models.database import get_pool

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

@router.get("/{asset_id}")
async def get_asset(asset_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM assets WHERE id = $1", asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    return dict(row)
```

- [ ] **步骤 5：更新 main.py（挂载路由 + 初始化）**

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.models.database import get_pool, close_pool
from app.services.es_sync_service import get_es, close_es
from app.services.es_mapping import build_index_settings_and_mappings
from app.services.parse_service import init_matcher
from app.routers import search, filter, assets, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await get_pool()
    es = await get_es()
    # Ensure ES index exists
    if not await es.indices.exists_alias(name="assets"):
        all_defs = []
        for mod in [1, 2, 3]:
            async with pool.acquire() as conn:
                defs = await conn.fetch(
                    "SELECT field_name, field_type FROM tag_definitions WHERE module_type=$1", mod
                )
            all_defs.extend([dict(d) for d in defs])
        body = build_index_settings_and_mappings(all_defs)
        import time
        idx_name = f"assets_v{int(time.time())}"
        await es.indices.create(index=idx_name, body=body)
        await es.indices.put_alias(index=idx_name, name="assets")
    # Load dictionary
    await init_matcher(pool)
    yield
    await close_pool()
    await close_es()

app = FastAPI(title="美术标签搜索平台", lifespan=lifespan)
app.include_router(search.router)
app.include_router(filter.router)
app.include_router(assets.router)
app.include_router(admin.router)

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

- [ ] **步骤 6：Commit**

```bash
git add backend/app/routers/ backend/app/main.py
git commit -m "feat: add all API routes (search, filter, assets, admin) with admin auth"
```

---

## 阶段 7：前端

### 任务 14：Vue 3 项目脚手架

- [ ] **步骤 1：创建 Vue 3 + TypeScript + Vite 项目**

```bash
cd frontend && npm create vite@latest . -- --template vue-ts
npm install element-plus @element-plus/icons-vue pinia axios
```

- [ ] **步骤 2：Commit**

### 任务 15：类型定义 + API 层

**文件：**
- 创建：`frontend/src/types/index.ts`
- 创建：`frontend/src/api/search.ts`

- [ ] **步骤 1：实现 types/index.ts**（从后端 schemas 对应的 TypeScript 接口）

- [ ] **步骤 2：实现 api/search.ts**（axios 封装，所有 API 调用）

- [ ] **步骤 3：Commit**

### 任务 16：Pinia Store

**文件：**
- 创建：`frontend/src/stores/searchStore.ts`

- [ ] **步骤 1：实现 searchStore**（管理 module_type, query, filters, results, facets, loading 状态）

- [ ] **步骤 2：Commit**

### 任务 17：核心组件

**文件：**
- 创建：`frontend/src/views/SearchPage.vue`
- 创建：`frontend/src/components/ModuleTabs.vue`
- 创建：`frontend/src/components/SearchBar.vue`
- 创建：`frontend/src/components/FilterPanel.vue`
- 创建：`frontend/src/components/FilterGroup.vue`
- 创建：`frontend/src/components/ResultGrid.vue`
- 创建：`frontend/src/components/AssetCard.vue`
- 创建：`frontend/src/components/AssetDetailModal.vue`
- 创建：`frontend/src/components/Pagination.vue`

- [ ] **步骤 1-9：逐个实现组件**（每个组件独立实现并测试）

  - SearchPage：主布局（左侧 FilterPanel + 右侧 SearchBar + Results）
  - ModuleTabs：Element Plus el-tabs，切换 module_type
  - SearchBar：el-input + debounce 300ms + ParsedTags 展示
  - FilterPanel：从 /definitions API 动态渲染 FilterGroup
  - FilterGroup：根据 field_type 分发 el-checkbox-group / el-radio-group / el-slider / el-switch
  - ResultGrid：el-row + el-col 网格，每个 AssetCard
  - AssetCard：缩略图 + 名称 + 标签，模型展示 PNG，特效悬停换 APNG src
  - AssetDetailModal：el-dialog 大图 + 完整标签 + 资源路径
  - Pagination：el-pagination

- [ ] **步骤 10：Commit**

```bash
git add frontend/
git commit -m "feat: add Vue 3 frontend with search, filter, results, preview"
```

---

## 阶段 8：集成测试与部署

### 任务 18：端到端集成验证

- [ ] **步骤 1：完整 Docker Compose 启动**

```bash
cd frontend && npm run build
docker compose up -d --build
```

- [ ] **步骤 2：导入测试数据**

```bash
# 导入 Excel（模型+动作）
curl -X POST http://localhost/api/v1/admin/import-excel \
  -H "X-Admin-Key: dev-admin-key-change-in-prod" \
  -F "file=@资源标签对照表.xlsx"

# 导入特效 HTML
curl -X POST http://localhost/api/v1/admin/import-effects-html \
  -H "X-Admin-Key: dev-admin-key-change-in-prod" \
  -F "file=@特效/effect_gif_catalog_embed_20260615_111542.html"
```

- [ ] **步骤 3：验证数据同步**

```bash
curl http://localhost/api/v1/admin/check-sync \
  -H "X-Admin-Key: dev-admin-key-change-in-prod"
# 预期：pg_count ≈ 7027, es_count ≈ 7027, in_sync: true
```

- [ ] **步骤 4：验证搜索功能**

```bash
# 纯筛选
curl -X POST http://localhost/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{"module_type":1,"filters":{"gender":"女"}}'

# 自然语言
curl -X POST http://localhost/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{"module_type":1,"query":"壮硕老和尚 少林"}'

# 数值条件
curl -X POST http://localhost/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{"module_type":2,"conditions":[{"field":"duration","op":">","value":5}]}'
```

- [ ] **步骤 5：浏览器测试**

打开 http://localhost，验证：
- 模块切换正常
- 筛选面板动态渲染
- 搜索栏输入触发 NLP 解析 + 标签展示
- 搜索结果卡片显示缩略图
- 特效卡片悬停播放动图
- 分页正常
- 详情弹窗显示完整信息

- [ ] **步骤 6：Commit**

```bash
git add -A
git commit -m "feat: complete integration with data import and e2e verification"
```

---

## 自检结果

### 规格覆盖度

| 规格章节 | 对应任务 | 状态 |
|----------|----------|------|
| Docker Compose + PG + ES | 任务 1 | 已覆盖 |
| PG Schema（7 张表 + CHECK 约束） | 任务 1 步骤 4 | 已覆盖 |
| ES 索引 + IK + mapping 生成 | 任务 5 | 已覆盖 |
| 数据同步（bulk + alias reindex + check-sync） | 任务 5 | 已覆盖 |
| tag_definitions + tag_values 初始化 | 任务 4 | 已覆盖 |
| Excel 导入（模型+动作） | 任务 6 | 已覆盖 |
| WPS DISPIMG 图片提取 | 任务 6 | 已覆盖 |
| HTML 特效导入 | 任务 7 | 已覆盖 |
| APNG 缩略图生成 | 任务 7 | 已覆盖 |
| TTLCache | 任务 8 | 已覆盖 |
| 词典匹配器 | 任务 9 | 已覆盖 |
| LLM 解析 + 校验 + 降级 | 任务 10 | 已覆盖 |
| ES 查询构建（function_score + aggs + highlight） | 任务 11 | 已覆盖 |
| 搜索编排 | 任务 12 | 已覆盖 |
| API 路由（search/filter/assets/admin） | 任务 13 | 已覆盖 |
| Admin API 鉴权 | 任务 13 | 已覆盖 |
| 搜索建议（内存前缀匹配） | 任务 13 | 已覆盖 |
| 分页限制 | 任务 3 | 已覆盖 |
| Vue 3 + Element Plus 前端 | 任务 14-17 | 已覆盖 |
| 筛选面板动态渲染 | 任务 17 | 已覆盖 |
| 预览（模型 PNG + 特效 APNG 悬停） | 任务 17 | 已覆盖 |
| Nginx 配置 | 任务 1 | 已覆盖 |
| 端到端集成验证 | 任务 18 | 已覆盖 |

### 占位符扫描
- 无 TODO/TBD
- 前端任务 14-17 的步骤描述略有简化（标准 Vue 组件，实现时按 Element Plus 文档即可），但文件路径和职责均已明确

### 类型一致性
- `SearchRequest` / `SearchResponse` / `ParseInfo` 在 schemas → search_service → router 中保持一致
- `DictionaryMatcher.match()` 返回 `MatchResult`，在 `parse_service.py` 中正确使用
- `build_search_query()` 的参数签名在 `es_query_builder.py` 和 `search_service.py` 中一致
- `TagDefinitionOut` 在 `schemas.py` 定义，在 `filter.py` 路由中使用
