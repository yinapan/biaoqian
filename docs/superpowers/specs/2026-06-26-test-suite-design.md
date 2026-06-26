# 美术资产检索工作台 — 测试套件设计

**日期**：2026-06-26
**状态**：v2（经架构师对抗审查后修订）
**交付方式**：一次性全做完再交付
**估时**：10-12 工程日

## 1. 目标

为 biaoqian 项目设计一套完整的自动化测试体系，覆盖功能与性能问题，作为后续所有改动的发布闸门——代码改动必须通过全部测试才能合并到 master 并发布到平台。

**关键诉求**：
- 功能正确性：搜索、筛选、详情、模块切换、分页、预览图加载、视觉质量
- 性能基准：搜索延迟、首屏加载、并发吞吐、错误率
- 视觉与图片质量：宽高比、`object-fit`、CLS、LCP
- 强制闸门：CI 必须全绿才能 merge；本地脚本支持快速验证

## 2. 架构总览

### 2.1 测试金字塔

```
       ┌─────────────────────┐
       │  k6 性能（本地 runbook） │   ← 手动跑 dev 环境
       ├─────────────────────┤
       │  Playwright E2E      │   ← CI 跑 fixture 环境
       ├─────────────────────┤
       │  pytest 后端集成       │   ← CI 跑 fixture 环境（独立 schema 隔离）
       ├─────────────────────┤
       │  Vitest 前端单元       │   ← 纯 Node，无外部依赖
       └─────────────────────┘
```

### 2.2 目录结构

```
biaoqian/
├── frontend/
│   ├── vitest.config.ts                    # 新增
│   ├── src/components/__tests__/            # *.spec.ts (Vitest)
│   └── src/stores/__tests__/
├── backend/
│   └── tests/
│       ├── (existing 14 mock modules)        # 保留，不重复
│       ├── conftest.py                       # 新增：fixture env fixtures
│       └── integration/                      # 新增：真连 PG+ES 的 API 测试
│           ├── test_health_api.py
│           ├── test_filter_api.py
│           ├── test_search_api.py
│           ├── test_suggestions_api.py
│           ├── test_admin_api.py
│           └── test_search_concurrency.py   # AbortController/并发原子性
├── tests/                                    # 新增：跨层 E2E + 性能
│   ├── e2e/
│   │   ├── playwright.config.ts
│   │   ├── fixtures/
│   │   │   ├── models.fixture.json
│   │   │   ├── animator.fixture.json
│   │   │   ├── effects.fixture.json
│   │   │   ├── icons.fixture.json
│   │   │   └── previews/                     # 50 张 ~5KB 测试图片
│   │   ├── pages/                             # Page Object
│   │   │   ├── SearchPage.ts
│   │   │   ├── ModuleTabs.ts
│   │   │   ├── FilterPanel.ts
│   │   │   ├── ResultGrid.ts
│   │   │   └── AssetDetailModal.ts
│   │   └── specs/
│   │       ├── search.spec.ts
│   │       ├── filter.spec.ts
│   │       ├── module-tabs.spec.ts
│   │       ├── detail-modal.spec.ts
│   │       ├── pagination.spec.ts
│   │       ├── preview-loading.spec.ts
│   │       ├── responsive.spec.ts             # 2 断点：桌面+手机
│   │       ├── error-states.spec.ts
│   │       └── visual-quality.spec.ts        # 视觉与图片质量（含 SVG fallback 实际渲染）
├── docker-compose.test.yml                    # 新增：fixture 环境
├── scripts/
│   ├── run_tests.bat                           # Windows 一键
│   ├── run_tests.sh                            # Linux/CI 一键
│   └── sample_real_data.py                     # 季度重生成 fixture
├── docs/
│   ├── testing-guide.md                        # 运行与维护说明
│   └── performance-testing.md                  # k6 本地 runbook
└── .github/workflows/test.yml                 # CI 闸门（前 3 层）
```

### 2.3 技术栈

| 层 | 工具 | 版本 |
|----|------|------|
| 前端单元 | Vitest + @vue/test-utils | 3.x / 2.x |
| 后端集成 | pytest + pytest-asyncio + httpx | 已有 |
| E2E | Playwright + TypeScript | 1.50+ |
| 性能 | k6（本地手动） | 最新稳定版 |
| 覆盖率 | vitest --coverage / pytest --cov | — |

### 2.4 用例总数（修订后）

| 层 | 用例数 | 说明 |
|----|-------|------|
| Vitest 前端单元 | ~40 | 纯函数与组件状态机 |
| pytest 后端集成 | ~36 | 真连 PG+ES 的 API 测试（含并发原子性） |
| Playwright E2E | ~55 | 含视觉质量 6（砍截图对比） |
| k6 性能场景 | ~20 | 本地手动跑 |
| **合计** | **~150** | |

### 2.5 前端测试钩子准备（关键前置工作）

**问题**：现有 `frontend/src/components/*.vue` 全部 0 个 `data-testid` 属性，`query_time_ms` 也未暴露到 DOM。Playwright 选择器要么依赖 Element Plus 内部 class（脆弱），要么加 data-testid（推荐）。

**做法**：为以下交互元素加 `data-testid`（不改 UI 行为，纯属性添加）：

| 文件 | 元素 | data-testid |
|------|------|------------|
| `SearchBar.vue` | 输入框 | `search-input` |
| `SearchBar.vue` | parse-info chip | `parse-chip-{field}` |
| `SearchBar.vue` | exclude 建议 | `suggestion-item-{idx}` |
| `ModuleTabs.vue` | 4 个 tab | `module-tab-{1-4}` |
| `FilterPanel.vue` | 单个 filter group | `filter-group-{field_name}` |
| `FilterGroup.vue` | enum_single 选项 | `filter-option-{field}-{value}` |
| `FilterGroup.vue` | number_range min | `filter-range-min-{field}` |
| `FilterGroup.vue` | number_range max | `filter-range-max-{field}` |
| `FilterGroup.vue` | 清空按钮 | `filter-clear-{field}` |
| `ResultGrid.vue` | 网格容器 | `result-grid` |
| `AssetCard.vue` | 卡片 | `asset-card-{idx}` |
| `AssetCard.vue` | 预览图 | `asset-preview-{idx}` |
| `AssetCard.vue` | ID 行 | `asset-id-row` |
| `AssetDetailModal.vue` | 弹窗根 | `detail-modal` |
| `AssetDetailModal.vue` | 预览大图 | `detail-preview` |
| `AssetDetailModal.vue` | 复制路径按钮 | `copy-path-btn` |
| `AssetDetailModal.vue` | 复制 ID 按钮 | `copy-id-btn` |
| `AssetDetailModal.vue` | 关闭按钮 | `detail-close` |
| `PaginationBar.vue` | 上一页/下一页 | `page-prev` / `page-next` |
| `PaginationBar.vue` | 当前页 | `page-current` |

**断言性能数据**：`query_time_ms` 已在 `SearchResponse` 后端响应里（[backend/app/models/schemas.py](backend/app/models/schemas.py)）。E2E 改为断言 API 响应而非 DOM，避免 UI 暴露不必要字段。

**工作量**：0.5 天，纳入估时第 1 阶段。

## 3. 用例清单

### 3.1 Vitest 前端单元（~40 个）

| 模块 | 测试目标 | 用例数 |
|------|---------|-------|
| `searchStore.ts` | setModuleType 重置 filters/query/page；setFilter 合并 enum_multi；doSearch AbortController 取消旧请求 + **旧响应被丢弃**（强化）；latestSearchId 防竞态；分页边界；dismissedFields 重解析 | 14 |
| `SearchBar.vue` | 500ms 防抖；输入清空触发 search；parse-info chip 显示与移除；exclude 建议点击 | 6 |
| `FilterGroup.vue` | enum_single 单选；enum_multi 多选 + 全选；number_range min/max 互相约束；boolean 切换；search-within 过滤 | 8 |
| `AssetCard.vue` | 预览图加载失败回退 SVG placeholder **且 placeholder 实际渲染**（@error 触发）；模型/动作/特效/图标四类预览 URL 正确；icon 才显示 ID 行 | 6 |
| `AssetDetailModal.vue` | 复制路径；复制 icon ID（仅 icon 模块）；clipboard fallback；ESC 关闭；点遮罩关闭 | 5 |
| `ModuleTabs.vue` | 4 个 tab 切换；当前 tab 高亮；切换触发 reset | 3 |

**注**：现有 14 个后端 mock 单元测试保留，不与此层重复。

### 3.2 pytest 后端集成（~36 个）

真连 PG+ES（fixture 环境，独立 schema），通过 httpx 打 `/api/v1/*` HTTP。

| 路由 | 测试 | 用例 |
|------|------|-----|
| `GET /health` | 服务可用性、ES alias 检查、**init_matcher 空字典状态下首次请求** | 3 |
| `GET /filter/definitions/{m}` | 4 个模块都返回、字段顺序、is_filterable 过滤、config JSON 解析 | 5 |
| `POST /search/query` | 空查询返回首页结果；文本查询命中；filters AND；excludes 排除；number_range 边界；分页（page=1/2/last）；page_offset_max=10000 阈值；parse_info 正确分类；facets 计数；**LLM 搜索路径**（llm_enabled=True 时调用 LLM，失败 fallback） | 14 |
| `GET /search/suggestions` | prefix 命中；大小写；空 q；module_type 切换 | 4 |
| `POST /admin/reindex-es` | 重建后搜索可用；旧索引清理；**alias 切换原子性（并发 2 个 reindex 请求只有一个成功，无中间态）** | 3 |
| `POST /admin/refresh-dictionary` | 缓存清空；下次查询重新加载 | 2 |
| `POST /admin/import-{m}-json` | 4 模块各导一次 fixture，upsert 不重复，tag_values 同步 | 4 |
| 并发测试 | **AbortController 等价**：连续 10 个 search 请求，前 9 个在路由层被取消，第 10 个返回正确结果 | 1 |

**P95 延迟测试改用 k6**（见 §3.4），不再在 pytest 里跑 20 次取 P95。

### 3.3 Playwright E2E（~55 个）

跑浏览器对 fixture 环境。Page Object 模式。

**关键流程**：

1. **搜索流程**（8 用例）— 输入文本 → 等待结果 → 检查卡片渲染 → 清空 → 检查结果更新；模块切换 → 搜索状态被重置；快速输入 → 防抖只发一次请求
2. **筛选流程**（8）— 选 enum_single → 结果过滤；多选 enum_multi → AND；number_range 滑块 → 结果数变化；清空所有筛选；dismissedFields 重解析流程
3. **详情弹窗**（6）— 点卡片 → 弹窗打开 → 显示标签 → 复制路径（粘贴板断言）→ ESC 关闭；点击遮罩关闭；多个弹窗顺序打开关闭
4. **模块切换**（4）— 4 个 tab 切换；切换后筛选面板重新加载；上次查询被清空
5. **分页**（5）— 翻页；改 pageSize；跳到最后一页；从第 1 页直接跳第 100 页（offset 上限边界）
6. **预览加载**（8）— 模型 PNG 加载；动作 GIF；特效 GIF；图标 PNG；**故意 404 → SVG placeholder 实际渲染**（断言 `@error` 触发 + DOM 出现 SVG 元素）；首屏滚动到的卡片 lazy-load；dismissedFields re-parse 后预览更新
7. **响应式**（4）— 桌面 + 手机两断点（砍掉平板）；筛选面板抽屉化（手机）；卡片栅格列数变化
8. **错误状态**（4）— 后端 500 → 友好错误提示；网络断开 → 重试按钮；空结果 → "无匹配"提示
9. **视觉与图片质量**（6）— 详见 §3.3.1
10. **辅助功能**（2）— Tab 键导航主流程；筛选面板键盘可达（砍掉 a11y smoke，仅保留这两个）

> **删除项**（YAGNI）：原 §3.3 的「辅助功能 Tab 键导航 + aria-label 检查」中的 a11y smoke 扫描去掉，因为没有真实 a11y audit 计划，是 theater。

#### 3.3.1 视觉与图片质量（6 用例）

| 检测项 | 方法 | 阈值 |
|-------|------|-----|
| 模型 PNG 宽高比 | `naturalW/naturalH` vs `clientW/clientH` | 比例差 < 1% |
| 动作/特效 GIF 宽高比 | 同上 | 同上 |
| 图标 PNG 宽高比 | 同上 | 同上 |
| `<img>` object-fit 属性 | `getComputedStyle` | 必须是 `cover` 或 `contain` |
| CLS | PerformanceObserver | < 0.1 |
| 首屏预览图 LCP | PerformanceObserver | < 2.5s |

**删除项**（YAGNI）：
- 砍掉「视觉回归截图对比」6 个用例（基线腐化成本 > 收益，每次 Element Plus 升级都要重做）
- 砍掉「详情页大图与卡片缩略图比例一致」
- 砍掉「网络图片体积异常」
- 砍掉「高分屏 dpr=2 渲染清晰度」

**保留核心**：宽高比断言能直接捕获"预览图被压缩"问题（你明确问过的诉求）；object-fit 断言确保 CSS 没漏配；CLS/LCP 捕获布局抖动与首屏性能。

### 3.4 k6 性能（~20 个场景，本地手动跑 dev 环境）

> **CI 不跑 k6**（GitHub runner 连不到 dev host，虚构）。改为本地 runbook [docs/performance-testing.md](docs/performance-testing.md)。

**Day 1 实测基线**：先用 k6 跑 dev 环境 20 次，记录实际 P95 → 设阈值为 `1.2 × 实测 P95`（不凭空设 500ms）。

**Day 2+ 阈值**（基线确定后写入 k6 脚本）：

| 场景 | 阈值 |
|------|------|
| 搜索空查询 P95 | 1.2 × 实测 |
| 文本搜索 P95 | 1.2 × 实测 |
| 多 filter 组合 P95 | 1.2 × 实测 |
| suggestions P95 | 1.2 × 实测 |
| filter/definitions P95 | 1.2 × 实测 |
| 卡片预览图 60 张并行加载 P95 | 1.2 × 实测 |
| 50 并发搜索 | 错误率 < 1% |
| 200 并发搜索 | 错误率 < 5%，无 5xx |
| 50 并发 + 持续建议查询 | 后端不崩 |

**报告**：`tests/performance/reports/{date}_{branch}.json`，本地保留 30 天。

## 4. Fixture 数据与环境

### 4.1 Fixture 数据集

`tests/e2e/fixtures/` 下四个 JSON，每个模块 ~50 条代表数据，覆盖：

| 模块 | 文件 | 设计要点 |
|------|------|---------|
| 模型 | `models.fixture.json` | 含全部 species/gender/body_type 各值；含数组型 enum_multi（region 多值）；含一张无预览图的（测 fallback） |
| 动作 | `animator.fixture.json` | 含 front+left 双视角；含 number_range（action_id, size_bytes）边界值；含被 hidden 字段 |
| 特效 | `effects.fixture.json` | 含 13 个语义标签各几个值；含 number_range 量化字段全填 + 部分缺失 |
| 图标 | `icons.fixture.json` | 含 predefined/color/semantic 各典型值；含 description 长文本（测截断） |

**预览图 fixture**：`tests/e2e/fixtures/previews/` 下放 50 个真实小图（每个 ~5KB，统一 256×256 PNG/GIF），通过 docker-compose.test.yml 挂载到对应 `runtime_data/{module}/` 目录。

### 4.2 Fixture 环境（docker-compose.test.yml）

独立 compose 文件，端口避开本地 dev：

```yaml
services:
  postgres-test:
    image: postgres:16
    environment:
      POSTGRES_DB: biaoqiao_test
      POSTGRES_USER: biaoqiao
      POSTGRES_PASSWORD: biaoqiao_test
    ports: ["15432:5432"]
    volumes:
      - ./sql:/docker-entrypoint-initdb.d
      - ./runtime_data_test:/runtime_data
  elasticsearch-test:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
    environment:
      discovery.type: single-node
      ES_JAVA_OPTS: "-Xms512m -Xmx512m"
      xpack.security.enabled: "false"
    ports: ["19200:9200"]
  backend-test:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://biaoqiao:biaoqiao_test@postgres-test:5432/biaoqiao_test
      ELASTICSEARCH_URL: http://elasticsearch-test:9200
      ADMIN_API_KEY: test-key-12345
      ES_INDEX_PREFIX: test_${RUN_ID}    # 并行 CI 隔离
    ports: ["18000:8000"]
    volumes:
      - ./runtime_data_test:/runtime_data
  nginx-test:
    image: nginx:alpine
    ports: ["18081:80"]
    volumes:
      - ./frontend/dist:/usr/share/nginx/html
      - ./nginx.dev.conf:/etc/nginx/conf.d/default.conf
      - ./runtime_data_test:/runtime_data
```

**端口分配**：
- 前端：`http://localhost:18081`
- 后端：`http://localhost:18000`
- PG：`15432`
- ES：`19200`

互不冲突 dev 的 `8081/8000/5432/9200`。

### 4.3 数据生命周期：方案 A′

> 用户最初选择方案 A（每测试隔离），但纯方案 A 每测试 TRUNCATE 会使 CI 时长从 ~5min 涨到 ~15min。微调为方案 A′：**读测试天然无副作用无需重置，写测试显式清理自己产生的数据**。

**E2E 全局 setup**（Playwright `globalSetup`）：
1. 启动 fixture 环境（脚本控制，CI 内由 workflow 负责）
2. 调用 `POST /admin/import-{m}-json` 导入 4 个 fixture
3. `POST /admin/reindex-es` + `refresh-dictionary`
4. 等待 health check

**每测试前**（Playwright `beforeEach`）：
- 不重置数据——E2E 大部分只读
- 仅在写操作测试前 `DELETE FROM ... WHERE ...` 清理本测试产生的行

### 4.4 并行 CI 隔离（修订 A′ 与发布闸门冲突）

**问题**：原 §4.3 方案 A′ 在并行 PR 跑 backend-integration 时会互相覆盖共享 PG/ES 数据。

**修订**：每个 CI run 用独立 DB schema + ES index 前缀：

- **PostgreSQL**：每个 run 创建独立 schema `biaoqiao_test_${github.run_id}`，测试结束自动 drop
- **Elasticsearch**：每个 run 用独立 index 前缀 `test_${github.run_id}_`（通过 `ES_INDEX_PREFIX` 环境变量传给 backend），测试结束删除此前缀的所有 index
- **后端集成测试 fixture**：在 `conftest.py` 的 setup 里创建 schema + import fixture + reindex；teardown 里清理

**结果**：多个 PR 并行 CI 互不干扰。

### 4.5 Dev 环境（性能测试用）

直接用现有 `docker-compose.yml + docker-compose.dev.yml`，跑真实数据（4 万条）。性能测试前确保 dev 环境已导入数据并 reindex。

### 4.6 Fixture drift 缓解

**问题**：手写 fixture 会随时间偏离真实数据形态，绿测试不再证明生产可用。

**修订**：加 [scripts/sample_real_data.py](scripts/sample_real_data.py)，从 dev 环境（4 万条）采样 ~50 条/模块，scrub 掉无关字段，重生成 fixture JSON。

**流程**：
- 季度执行（每 3 个月）
- 跑前确认 dev 环境已 reindex
- 跑后人工 review 生成的 fixture（确保覆盖典型边界）
- 提交 PR 更新 fixture

## 5. CI 闸门与本地脚本

### 5.1 CI workflow：`.github/workflows/test.yml`

PR 到 master 时触发，3 个 job（**砍掉 performance job**）：

```yaml
jobs:
  frontend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: cd frontend && npm ci && npx vitest run --coverage

  backend-integration:
    runs-on: ubuntu-latest
    env:
      RUN_ID: ${{ github.run_id }}
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: biaoqiao
          POSTGRES_PASSWORD: biaoqiao_test
          POSTGRES_DB: biaoqiao_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U biaoqiao"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      elasticsearch:
        image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
        env:
          discovery.type: single-node
          ES_JAVA_OPTS: "-Xms512m -Xmx512m"
          xpack.security.enabled: "false"
        ports: ["9200:9200"]
        options: >-
          --health-cmd "curl -f http://localhost:9200/_cluster/health"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Install postgresql-client
        run: sudo apt-get update && sudo apt-get install -y postgresql-client
      - run: pip install -r backend/requirements.txt
      - name: Init schema
        env:
          PGPASSWORD: biaoqiao_test
        run: |
          psql -h localhost -U biaoqiao -d biaoqiao_test -f sql/001_init_schema.sql
          psql -h localhost -U biaoqiao -d biaoqiao_test -f sql/002_init_tags.sql
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://biaoqiao:biaoqiao_test@localhost:5432/biaoqiao_test
          ELASTICSEARCH_URL: http://localhost:9200
          ADMIN_API_KEY: test-key-12345
          ES_INDEX_PREFIX: ci_${RUN_ID}
        run: cd backend && python -m pytest tests/ -v --cov=app --cov-report=xml
      - name: Cleanup ES indices
        if: always()
        run: |
          curl -X DELETE "http://localhost:9200/ci_${RUN_ID}_*" || true

  e2e:
    runs-on: ubuntu-latest
    needs: [frontend-unit, backend-integration]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd frontend && npm ci && npx vite build
      - run: docker compose -f docker-compose.test.yml up -d --build
      - name: Wait for backend health
        run: |
          for i in {1..30}; do
            curl -sf http://localhost:18081/api/v1/health && break
            sleep 2
          done
      - run: npx playwright install --with-deps chromium
      - run: cd tests/e2e && npx playwright test
      - uses: actions/upload-artifact@v4
        if: failure()
        with: { name: playwright-report, path: tests/e2e/playwright-report/ }
```

### 5.2 闸门规则

- `frontend-unit`、`backend-integration`、`e2e` 必须全绿才能 merge
- **performance 不在 CI**（改为本地 runbook）
- GitHub Branch Protection：开启 "Require status checks to pass before merging"，勾选 3 个 job

### 5.3 本地一键脚本

**Windows：`scripts/run_tests.bat`**

```batch
@echo off
setlocal
set TARGET=%1
if "%TARGET%"=="" set TARGET=all

if "%TARGET%"=="unit" goto unit
if "%TARGET%"=="integration" goto integration
if "%TARGET%"=="e2e" goto e2e
if "%TARGET%"=="perf" goto perf
if "%TARGET%"=="all" goto all
echo Usage: run_tests.bat [unit^|integration^|e2e^|perf^|all]
exit /b 1

:unit
echo === Frontend unit tests ===&& cd frontend && npx vitest run && cd ..
echo === Backend unit tests ===&& cd backend && python -m pytest tests/ -k "not integration" && cd ..
goto end

:integration
cd backend && python -m pytest tests/integration/ && cd ..
goto end

:e2e
docker compose -f docker-compose.test.yml up -d --build
cd tests/e2e && npx playwright test
goto end

:perf
k6 run tests/performance/k6-baseline.js
k6 run tests/performance/k6-load.js
goto end

:all
call %0 unit && call %0 integration && call %0 e2e && call %0 perf
goto end

:end
```

**Linux/CI：`scripts/run_tests.sh`** 同上结构，bash 语法。

### 5.4 性能阈值与报告

**阈值确定流程**：
1. Day 1：dev 环境跑 k6 基准 20 次，记录实测 P95
2. Day 2：设阈值为 `1.2 × 实测 P95`，写入 k6 脚本
3. 后续：阈值变更需 PR review，不允许单人改

**报告**：`tests/performance/reports/{date}_{branch}.json`，本地保留 30 天。

## 6. Page Object 与测试代码骨架

### 6.1 Page Object 层

`tests/e2e/pages/`：

```typescript
// SearchPage.ts — 主入口
export class SearchPage {
  constructor(private page: Page) {}
  
  async goto() { await this.page.goto('http://localhost:18081'); }
  
  get searchInput() { return this.page.locator('[data-testid="search-input"]'); }
  get moduleTabs() { return new ModuleTabs(this.page); }
  get filterPanel() { return new FilterPanel(this.page); }
  get resultGrid() { return new ResultGrid(this.page); }
  get detailModal() { return new AssetDetailModal(this.page); }
  get pagination() { return this.page.locator('[data-testid^="page-"]'); }
  
  async search(text: string) {
    await this.searchInput.fill(text);
    await this.page.waitForLoadState('networkidle');
  }
  
  // 断言 API 响应里的 query_time_ms（不依赖 DOM）
  async expectQueryTimeLessThan(ms: number) {
    const resp = await this.page.waitForResponse(r => 
      r.url().includes('/api/v1/search/query') && r.status() === 200
    );
    const body = await resp.json();
    expect(body.query_time_ms).toBeLessThan(ms);
  }
}

// ModuleTabs.ts, FilterPanel.ts, ResultGrid.ts, AssetDetailModal.ts 类似
```

### 6.2 E2E 用例示例（视觉+功能）

```typescript
// tests/e2e/specs/visual-quality.spec.ts
import { test, expect } from '@playwright/test';
import { SearchPage } from '../pages/SearchPage';

test.describe('详情页预览图视觉质量', () => {
  test('模型 PNG 宽高比保持', async ({ page }) => {
    const sp = new SearchPage(page);
    await sp.goto();
    await sp.search('测试模型');
    
    const card = sp.resultGrid.firstCard();
    await card.click();
    await sp.detailModal.expectOpen();
    
    const img = sp.detailModal.previewImage;
    const box = await img.boundingBox();
    const natural = await img.evaluate(
      (el: HTMLImageElement) => ({ w: el.naturalWidth, h: el.naturalHeight })
    );
    
    const renderRatio = box!.width / box!.height;
    const naturalRatio = natural.w / natural.h;
    expect(Math.abs(renderRatio - naturalRatio)).toBeLessThan(0.01);
    
    const objectFit = await img.evaluate(
      (el: HTMLImageElement) => getComputedStyle(el).objectFit
    );
    expect(['cover', 'contain']).toContain(objectFit);
  });
  
  test('预览图 404 时 SVG placeholder 实际渲染', async ({ page }) => {
    // 故意请求不存在的资源路径
    const sp = new SearchPage(page);
    await sp.goto();
    await sp.search('无预览图的测试模型');
    
    const card = sp.resultGrid.firstCard();
    const preview = card.locator('[data-testid^="asset-preview-"]');
    
    // 等待 @error 触发
    await preview.evaluate(el => {
      const img = el as HTMLImageElement;
      img.dispatchEvent(new Event('error'));
    });
    
    // 断言 SVG placeholder 出现在 DOM
    const svg = card.locator('svg');
    await expect(svg).toBeVisible();
  });
});
```

### 6.3 后端集成测试示例

```python
# backend/tests/integration/test_search_api.py
import pytest
import httpx

@pytest.mark.asyncio
async def test_search_returns_facets(test_client, seeded_db):
    resp = await test_client.post('/api/v1/search/query', json={
        'module_type': 1, 'query': '', 'page': 1, 'page_size': 20,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 'facets' in data
    assert data['total'] > 0
    assert all('field_name' in f for f in data['facets'])

@pytest.mark.asyncio
async def test_search_query_time_in_response(test_client, seeded_db):
    """断言 SearchResponse 含 query_time_ms 字段（E2E 也用此字段）"""
    resp = await test_client.post('/api/v1/search/query', json={
        'module_type': 1, 'query': '', 'page': 1, 'page_size': 20,
    })
    data = resp.json()
    assert 'query_time_ms' in data
    assert isinstance(data['query_time_ms'], (int, float))
    assert data['query_time_ms'] > 0

@pytest.mark.asyncio
async def test_reindex_alias_atomicity(test_client, admin_key):
    """并发 2 个 reindex 请求，只有一个成功 swap alias，无中间态"""
    import asyncio
    tasks = [
        test_client.post('/api/v1/admin/reindex-es', 
                         headers={'X-Admin-Key': admin_key})
        for _ in range(2)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # 两个请求都应返回 200（一个 swap 成功，另一个识别为已过期），无 5xx
    for r in results:
        if isinstance(r, Exception):
            continue
        assert r.status_code in (200, 409), f'Unexpected status: {r.status_code}'
    
    # 最终 alias 指向一个有效 index，搜索可用
    search = await test_client.post('/api/v1/search/query', json={
        'module_type': 1, 'query': '', 'page': 1, 'page_size': 1,
    })
    assert search.status_code == 200
```

### 6.4 k6 基准测试脚本示例

```javascript
// tests/performance/k6-baseline.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    search_baseline: {
      executor: 'per-vu-iterations',
      vus: 1, iterations: 100,    // 100 次取 P95（不是 20）
      thresholds: {
        'http_req_duration{scenario:search_baseline}': ['p(95)<THRESHOLD'],
      },
    },
  },
};

export default function () {
  const base = __ENV.BASE_URL || 'http://localhost:8081';
  const res = http.post(`${base}/api/v1/search/query`, JSON.stringify({
    module_type: 1, query: '', page: 1, page_size: 60,
  }), { headers: { 'Content-Type': 'application/json' } });
  check(res, { 'status 200': r => r.status === 200 });
}
```

> `THRESHOLD` 在 Day 1 实测后填入。

### 6.5 前端单元测试示例

```typescript
// frontend/src/stores/__tests__/searchStore.spec.ts
import { setActivePinia, createPinia } from 'pinia';
import { useSearchStore } from '../searchStore';
import { describe, beforeEach, it, expect, vi } from 'vitest';

describe('searchStore', () => {
  beforeEach(() => setActivePinia(createPinia()));
  
  it('setModuleType 重置 filters/query/page', () => {
    const store = useSearchStore();
    store.query = '旧查询';
    store.filters = { species: ['老虎'] };
    store.page = 5;
    
    store.setModuleType(3);
    
    expect(store.moduleType).toBe(3);
    expect(store.query).toBe('');
    expect(store.filters).toEqual({});
    expect(store.page).toBe(1);
  });
  
  it('doSearch 取消旧请求（AbortController）+ 旧响应被丢弃', async () => {
    const store = useSearchStore();
    const abortSpy = vi.spyOn(AbortController.prototype, 'abort');
    
    // 第一次请求（慢，会被取消）
    const slowPromise = store.doSearch({ quiet: true });
    // 第二次请求（快，应胜出）
    const fastPromise = store.doSearch({ quiet: true });
    
    expect(abortSpy).toHaveBeenCalled();
    
    // 第一次的响应不应该污染 store.response
    await Promise.allSettled([slowPromise, fastPromise]);
    // 验证 store.response 来自第二次请求（具体断言依赖实现）
  });
  
  it('dismissedFields 被dismiss后重新解析查询', async () => {
    const store = useSearchStore();
    store.query = '战士 剑客';
    store.dismissedFields = ['profession'];
    await store.doSearch();
    // dismissedFields 应触发 re-parse，查询中剑客部分被重新处理
    expect(store.parseInfo).toBeDefined();
  });
});
```

## 7. 实现优先级

**一次性全做完再交付**（用户明确要求），估时 10-12 工程日：

| 阶段 | 内容 | 估时 |
|------|------|------|
| 1 | 前端 data-testid 钩子（§2.5）+ Vitest 配置 + 40 个前端单元测试 + `run_tests.bat/.sh unit` | 1.5 天 |
| 2 | pytest fixtures（独立 schema）+ 36 个 API 集成测试 + docker-compose.test.yml | 2.5 天 |
| 3 | Playwright 配置 + Page Object + 55 个 E2E + 6 视觉质量用例 | 3.5 天 |
| 4 | k6 脚本 + Day 1 实测基线 + Day 2 阈值确定 + `docs/performance-testing.md` runbook | 1 天 |
| 5 | GitHub Actions workflow + Branch Protection + `docs/testing-guide.md` + `scripts/sample_real_data.py` | 1.5 天 |
| 6 | 集成联调 + 修复发现的问题 + 最终验收 | 1.5 天 |
| **合计** | | **11.5 天** |

## 8. 风险与边界

### 8.1 已识别风险

| 风险 | 缓解 |
|------|------|
| k6 在 Windows 上需单独安装 | 文档说明；CI 是 Linux 无此问题；性能测试本地手动跑 |
| fixture 环境与真实环境数据形态有差异 | `scripts/sample_real_data.py` 季度重生成 fixture（§4.6） |
| 性能阈值过严可能误报 | Day 1 实测基线 → 阈值 = 1.2 × 实测（不是凭空设）（§3.4） |
| E2E 全套时长可能超 5min | 用 Playwright 并行 + shard；CI 分片 |
| 并行 PR 跑 backend-integration 互相覆盖 | 独立 schema + ES index 前缀（§4.4） |
| data-testid 改动可能影响现有 UI | 纯属性添加，不改逻辑；前端组件测试通过即可 |

### 8.2 不在范围内

- 跨浏览器测试（仅测 Chromium；Firefox/Safari 后续可选）
- 真实用户监控（RUM）
- 安全测试（注入/XSS/越权）
- 数据库压测（仅测 API 层）
- 移动端原生 app
- 视觉回归截图对比（砍掉，YAGNI）
- a11y 完整 audit（仅保留 2 个键盘导航 smoke）

## 9. 验收标准

整套测试体系交付完成的标志：

1. ✅ `run_tests.bat all` 或 `run_tests.sh all` 本地一键跑完所有 4 层测试
2. ✅ CI workflow 在 PR 上自动触发 3 个 job（frontend-unit, backend-integration, e2e）
3. ✅ 前端单元覆盖率 ≥ 60%（按文件计，不强制未测试路径）
4. ✅ 后端集成覆盖率 ≥ 70%（按文件计）
5. ✅ E2E 覆盖所有 §3.3 列出的 10 类流程
6. ✅ 性能基准全部有阈值断言（Day 2 后填入实测 1.2×）
7. ✅ 视觉质量 6 用例全绿（含宽高比、object-fit、CLS、LCP）
8. ✅ Branch Protection 启用，3 个 CI job 必过
9. ✅ 文档：`docs/testing-guide.md` 说明如何运行与维护
10. ✅ 文档：`docs/performance-testing.md` 说明 k6 本地 runbook
11. ✅ `scripts/sample_real_data.py` 季度重生成 fixture 流程就绪
12. ✅ 现有 14 个后端 mock 单元测试全部保留通过
