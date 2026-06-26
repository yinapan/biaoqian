# 美术资产检索工作台 — 测试套件设计

**日期**：2026-06-26
**状态**：待用户审阅
**交付方式**：一次性全做完再交付

## 1. 目标

为 biaoqian 项目设计一套完整的自动化测试体系，覆盖功能与性能问题，作为后续所有改动的发布闸门——代码改动必须通过全部测试才能合并到 master 并发布到平台。

**关键诉求**：
- 功能正确性：搜索、筛选、详情、模块切换、分页、预览图加载、视觉质量
- 性能基准：搜索延迟、首屏加载、并发吞吐、错误率
- 视觉与图片质量：宽高比、`object-fit`、CLS、视觉回归
- 强制闸门：CI 必须全绿才能 merge；本地脚本支持快速验证

## 2. 架构总览

### 2.1 测试金字塔

```
       ┌─────────────────────┐
       │  k6 性能（基准+压测）   │   ← 跑 dev 环境
       ├─────────────────────┤
       │  Playwright E2E      │   ← 跑 fixture 环境
       ├─────────────────────┤
       │  pytest 后端集成       │   ← 跑 fixture 环境
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
│       ├── (existing 14 modules)            # 保留现有 mock 单元测试
│       ├── conftest.py                       # 新增：fixture env fixtures
│       └── integration/                      # 新增：真连 PG+ES 的 API 测试
│           ├── test_health_api.py
│           ├── test_filter_api.py
│           ├── test_search_api.py
│           ├── test_suggestions_api.py
│           └── test_admin_api.py
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
│   │       ├── responsive.spec.ts
│   │       ├── error-states.spec.ts
│   │       ├── accessibility.spec.ts
│   │       └── visual-quality.spec.ts        # 视觉与图片质量
│   └── performance/
│       ├── k6-baseline.js                     # 延迟基准（断言阈值）
│       ├── k6-load.js                          # 压测（50/200 并发）
│       └── reports/                            # 历史报告
├── docker-compose.test.yml                    # 新增：fixture 环境
├── scripts/
│   └── run_tests.bat                           # 一键脚本
└── .github/workflows/test.yml                 # CI 闸门
```

### 2.3 技术栈

| 层 | 工具 | 版本 |
|----|------|------|
| 前端单元 | Vitest + @vue/test-utils | 3.x / 2.x |
| 后端集成 | pytest + pytest-asyncio + httpx | 已有 |
| E2E | Playwright + TypeScript | 1.50+ |
| 性能 | k6 | 最新稳定版 |
| 视觉回归 | Playwright 内置 toHaveScreenshot | — |
| 覆盖率 | vitest --coverage / pytest --cov | — |

### 2.4 用例总数

| 层 | 用例数 | 说明 |
|----|-------|------|
| Vitest 前端单元 | ~40 | 纯函数与组件状态机 |
| pytest 后端集成 | ~30 | 真连 PG+ES 的 API 测试 |
| Playwright E2E | ~60 | 含视觉质量 12 |
| k6 性能场景 | ~20 | 基准 + 压测 |
| **合计** | **~150** | |

## 3. 用例清单

### 3.1 Vitest 前端单元（~40 个）

| 模块 | 测试目标 | 用例数 |
|------|---------|-------|
| `searchStore.ts` | setModuleType 重置 filters/query/page；setFilter 合并 enum_multi；doSearch AbortController 取消旧请求；latestSearchId 防竞态；分页边界 | 12 |
| `SearchBar.vue` | 500ms 防抖；输入清空触发 search；parse-info chip 显示与移除；exclude 建议点击 | 6 |
| `FilterGroup.vue` | enum_single 单选；enum_multi 多选 + 全选；number_range min/max 互相约束；boolean 切换；search-within 过滤 | 8 |
| `AssetCard.vue` | 预览图加载失败回退 SVG placeholder；模型/动作/特效/图标四类预览 URL 正确；icon 才显示 ID 行 | 6 |
| `AssetDetailModal.vue` | 复制路径；复制 icon ID（仅 icon 模块）；clipboard fallback；ESC 关闭；点遮罩关闭 | 5 |
| `ModuleTabs.vue` | 4 个 tab 切换；当前 tab 高亮；切换触发 reset | 3 |

### 3.2 pytest 后端集成（~30 个）

真连 PG+ES（fixture 环境），通过 httpx 打 `/api/v1/*` HTTP。

| 路由 | 测试 | 用例 |
|------|------|-----|
| `GET /health` | 服务可用性、ES alias 检查 | 2 |
| `GET /filter/definitions/{m}` | 4 个模块都返回、字段顺序、is_filterable 过滤、config JSON 解析 | 5 |
| `POST /search/query` | 空查询返回首页结果；文本查询命中；filters AND；excludes 排除；number_range 边界；分页（page=1/2/last）；page_offset_max=10000 阈值；parse_info 正确分类；facets 计数 | 12 |
| `GET /search/suggestions` | prefix 命中；大小写；空 q；module_type 切换 | 4 |
| `POST /admin/reindex-es` | 重建后搜索可用；旧索引清理；alias 切换原子性 | 3 |
| `POST /admin/refresh-dictionary` | 缓存清空；下次查询重新加载 | 2 |
| `POST /admin/import-{m}-json` | 4 模块各导一次 fixture，upsert 不重复，tag_values 同步 | 4 |

### 3.3 Playwright E2E（~60 个）

跑浏览器对 fixture 环境。Page Object 模式。

**关键流程**：

1. **搜索流程**（8 用例）— 输入文本 → 等待结果 → 检查卡片渲染 → 清空 → 检查结果更新；模块切换 → 搜索状态被重置；快速输入 → 防抖只发一次请求
2. **筛选流程**（8）— 选 enum_single → 结果过滤；多选 enum_multi → AND；number_range 滑块 → 结果数变化；清空所有筛选；dismissed_fields 重新解析
3. **详情弹窗**（6）— 点卡片 → 弹窗打开 → 显示标签 → 复制路径（粘贴板断言）→ ESC 关闭；点击遮罩关闭；多个弹窗顺序打开关闭
4. **模块切换**（4）— 4 个 tab 切换；切换后筛选面板重新加载；上次查询被清空
5. **分页**（5）— 翻页；改 pageSize；跳到最后一页；从第 1 页直接跳第 100 页（offset 上限边界）
6. **预览加载**（6）— 模型 PNG 加载；动作 GIF；特效 GIF；图标 PNG；故意 404 → SVG fallback；首屏滚动到的卡片 lazy-load
7. **响应式**（4）— 桌面/平板/手机断点；筛选面板抽屉化；卡片栅格列数变化
8. **错误状态**（4）— 后端 500 → 友好错误提示；网络断开 → 重试按钮；空结果 → "无匹配"提示
9. **辅助功能**（3）— Tab 键导航；筛选面板键盘可达；搜索框 aria-label
10. **视觉与图片质量**（12）— 详见 §3.3.1

#### 3.3.1 视觉与图片质量（12 用例）

| 检测项 | 方法 | 阈值 |
|-------|------|-----|
| 模型 PNG 宽高比 | `naturalW/naturalH` vs `clientW/clientH` | 比例差 < 1% |
| 动作 GIF 宽高比 | 同上 | 同上 |
| 特效 GIF 宽高比 | 同上 | 同上 |
| 图标 PNG 宽高比 | 同上 | 同上 |
| `<img>` object-fit 属性 | `getComputedStyle` | 必须是 `cover` 或 `contain` |
| 详情页大图与卡片缩略图比例一致 | 对比两处 | 一致 |
| CLS | PerformanceObserver | < 0.1 |
| 首屏预览图 LCP | PerformanceObserver | < 2.5s |
| 视觉回归 — 详情页 | 截屏对比基线 | 像素差异 < 0.5% |
| 视觉回归 — 卡片栅格 | 同上 | 同上 |
| 网络图片体积异常 | 抓 response 的 content-length | PNG < 5KB 视为可疑 |
| 高分屏（dpr=2）渲染清晰度 | 检查 `currentSrc` 是否含 2x 资源 | 有 2x 或 SVG |

**捕获范围**：
- ✅ 宽高比破坏（CSS 强行拉伸）
- ✅ `object-fit` 缺失
- ✅ 像素缩小但模糊渲染
- ✅ CLS（布局位移）
- ✅ 视觉回归（截图对比基线）
- ✅ 图片实际请求尺寸异常
- ❌ 纯主观"丑不丑"、颜色平衡、构图

### 3.4 k6 性能（~20 个场景，跑 dev 环境）

**基准测试**（断言阈值，每场景跑 1 轮）：

| 场景 | 阈值 |
|------|------|
| 搜索空查询 P95 | < 500ms |
| 文本搜索 P95 | < 800ms |
| 多 filter 组合 P95 | < 1000ms |
| suggestions P95 | < 200ms |
| filter/definitions P95 | < 300ms |
| 卡片预览图 60 张并行加载 P95 | < 2000ms |

**压测**（50/200 并发，5 分钟）：

| 场景 | 阈值 |
|------|------|
| 50 并发搜索 | 错误率 < 1%，P95 < 1s |
| 200 并发搜索 | 错误率 < 5%（触发限流/连接池上限），无 5xx |
| 50 并发 + 持续建议查询 | 后端不崩 |

**报告**：`tests/performance/reports/{date}_{branch}.json`，CI 上传为 artifact，保留 30 天。

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

### 4.4 Dev 环境（性能测试用）

直接用现有 `docker-compose.yml + docker-compose.dev.yml`，跑真实数据（4 万条）。性能测试前确保 dev 环境已导入数据并 reindex。

## 5. CI 闸门与本地脚本

### 5.1 CI workflow：`.github/workflows/test.yml`

PR 到 master 时触发，4 个 job：

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
    services:
      postgres: { image: postgres:16, env: {...}, ports: ["5432:5432"] }
      elasticsearch: { image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0, ... }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt
      - run: psql -f sql/001_init_schema.sql && psql -f sql/002_init_tags.sql
      - run: cd backend && python -m pytest tests/ -v --cov=app

  e2e:
    runs-on: ubuntu-latest
    needs: [frontend-unit, backend-integration]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd frontend && npm ci && npx vite build
      - run: docker compose -f docker-compose.test.yml up -d --build
      - run: npx playwright install --with-deps chromium
      - run: cd tests/e2e && npx playwright test
      - uses: actions/upload-artifact@v4
        if: failure()
        with: { name: playwright-report, path: tests/e2e/playwright-report/ }

  performance:
    runs-on: ubuntu-latest
    needs: e2e
    if: github.event_name == 'pull_request'
    steps:
      - uses: grafana/k6-action@v0.3
        with:
          filename: tests/performance/k6-baseline.js
          cloud: false
      - run: k6 run tests/performance/k6-load.js --env BASE_URL=http://dev-host
```

### 5.2 闸门规则

- `frontend-unit`、`backend-integration`、`e2e` 必须全绿才能 merge
- `performance` 默认 informational，但**基准测试 P95 超阈值 1.5× 时 fail**（强制阻塞）
- GitHub Branch Protection：开启 "Require status checks to pass before merging"，勾选前 3 个 job

### 5.3 本地一键脚本：`scripts/run_tests.bat`

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

开发时常用：`run_tests.bat unit`（30s 内跑完，快速反馈）；提 PR 前 `run_tests.bat all`（5-8min）。

### 5.4 性能阈值与报告

| 指标 | 阈值 | 触发动作 |
|------|------|---------|
| 搜索空查询 P95 | < 500ms | 超过 1.5×（750ms）fail |
| 文本搜索 P95 | < 800ms | 超过 1.5× fail |
| suggestions P95 | < 200ms | 超过 1.5× fail |
| filter/definitions P95 | < 300ms | 超过 1.5× fail |
| 50 并发错误率 | < 1% | 超过 fail |
| 200 并发错误率 | < 5% | 超过 fail |
| CLS | < 0.1 | 超过 fail |
| LCP（首屏）| < 2.5s | 超过 fail |

报告：`tests/performance/reports/{date}_{branch}.json`，CI 上传为 artifact，保留 30 天。

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
  get pagination() { return this.page.locator('.el-pagination'); }
  
  async search(text: string) {
    await this.searchInput.fill(text);
    await this.page.waitForLoadState('networkidle');
  }
  
  async expectQueryTimeLessThan(ms: number) {
    const time = await this.page.locator('[data-testid="query-time"]').textContent();
    expect(parseFloat(time!)).toBeLessThan(ms);
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
  
  test('详情页视觉回归', async ({ page }) => {
    const sp = new SearchPage(page);
    await sp.goto();
    await sp.search('测试模型');
    await sp.resultGrid.firstCard().click();
    await sp.detailModal.expectOpen();
    await expect(page).toHaveScreenshot('detail-modal-model.png', {
      maxDiffPixelRatio: 0.005,
    });
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
async def test_search_p95_latency(test_client, seeded_db):
    import time
    latencies = []
    for _ in range(20):
        t = time.perf_counter()
        await test_client.post('/api/v1/search/query', json={
            'module_type': 1, 'query': '战士', 'page': 1, 'page_size': 60,
        })
        latencies.append((time.perf_counter() - t) * 1000)
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    assert p95 < 800, f'P95 latency {p95}ms exceeds 800ms'
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
      vus: 1, iterations: 20,
      thresholds: {
        'http_req_duration{scenario:search_baseline}': ['p(95)<500'],
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
  
  it('doSearch 取消旧请求（AbortController）', async () => {
    const store = useSearchStore();
    const abortSpy = vi.spyOn(AbortController.prototype, 'abort');
    
    store.doSearch({ quiet: true });
    store.doSearch({ quiet: true });
    
    expect(abortSpy).toHaveBeenCalledTimes(1);
  });
});
```

## 7. 实现优先级

**一次性全做完再交付**（用户明确要求）：

| 阶段 | 内容 | 估时 |
|------|------|------|
| 1 | Vitest 配置 + 40 个前端单元测试 + `run_tests.bat unit` | 1 天 |
| 2 | pytest fixtures + 30 个 API 集成测试 + docker-compose.test.yml | 1.5 天 |
| 3 | Playwright 配置 + Page Object + 60 个 E2E + 视觉回归基线 | 2.5 天 |
| 4 | k6 脚本 + GitHub Actions workflow + Branch Protection | 1 天 |
| **合计** | | **6 天** |

一次性交付完成后，整套测试体系立即可用：开发时 `run_tests.bat unit` 快速反馈；提 PR 时 CI 自动跑全 4 层；性能基准超阈值强制阻塞；视觉回归捕获意外 layout 变化。

## 8. 风险与边界

### 8.1 已识别风险

| 风险 | 缓解 |
|------|------|
| 视觉回归基线首次截图可能有偏差 | 首次基线由人眼确认；提供 `--update-snapshots` 流程 |
| k6 在 Windows 上需单独安装 | 文档说明；CI 用 Linux runner 无此问题 |
| fixture 环境与真实环境数据形态有差异 | fixture 设计覆盖典型边界；定期用真实数据 sample 校准 |
| 性能阈值过严可能误报 | 默认 1.5× 容差；可临时调高 |
| E2E 全套时长可能超 5min | 用 Playwright 并行 + shard；CI 分片 |

### 8.2 不在范围内

- 跨浏览器测试（仅测 Chromium；Firefox/Safari 后续可选）
- 真实用户监控（RUM）
- 安全测试（注入/XSS/越权）
- 数据库压测（仅测 API 层）
- 移动端原生 app

## 9. 验收标准

整套测试体系交付完成的标志：

1. ✅ `run_tests.bat all` 本地一键跑完所有 4 层测试
2. ✅ CI workflow 在 PR 上自动触发 4 个 job
3. ✅ 前端单元覆盖率 ≥ 60%
4. ✅ 后端集成覆盖率 ≥ 70%
5. ✅ E2E 覆盖所有 §3.3 列出的 10 类流程
6. ✅ 性能基准全部有阈值断言
7. ✅ 视觉回归基线已建立
8. ✅ Branch Protection 启用，前 3 个 job 必过
9. ✅ 文档：`docs/testing-guide.md` 说明如何运行与维护
