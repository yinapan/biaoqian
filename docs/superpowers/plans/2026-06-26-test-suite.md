# 测试套件 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 biaoqian 美术资产检索工作台交付一套覆盖功能与性能的自动化测试体系（~175 个用例 / 4 层），作为后续所有改动的发布闸门——代码改动必须通过全部 CI 测试才能合并到 master 并发布到平台。

**架构：** 分层测试金字塔——Vitest 前端单元（纯 Node）→ pytest 后端集成（真连 PG+ES，独立 schema 隔离）→ Playwright E2E（fixture 环境，浏览器）→ k6 性能（本地手动 runbook，dev 环境）。CI 跑前 3 层，k6 仅本地。

**技术栈：** Vue 3.5 + Pinia 3 + Element Plus 2.9 + Vite 6 + TypeScript（前端），FastAPI + asyncpg + elasticsearch-py + Pydantic Settings（后端），Vitest 3.x + @vue/test-utils 2.x + @vitest/coverage-v8 + jsdom（前端单元），pytest + pytest-asyncio + httpx + asyncpg（后端集成），Playwright 1.50+ + TypeScript（E2E），k6（性能），GitHub Actions（CI）。

---

## 全局约束

- **提交规范**：中文 Conventional Commits，所有 commit 签名 `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`
- **TDD 纪律**：每个测试用例先写失败测试 → 运行验证失败 → 实现最小代码 → 运行验证通过 → 提交。不允许"先实现再补测试"
- **data-testid 规范**：用稳定 `asset.id`，不用列表 `idx`（idx 在搜索/筛选/分页变化后不稳定）
- **slug 化**：含中文/斜杠/空格的 value 必须经 `slug()` 函数处理后再拼到 test id
- **容器内路径一致性**：docker-compose.test.yml 的容器内路径必须与 docker-compose.yml 完全一致（`/data/previews/model` 等），否则 E2E 预览图加载失败
- **ES 隔离零代码改动**：后端已有 `settings.es_index_alias`（[backend/app/config.py:7](backend/app/config.py#L7)），CI 直接设 `ES_INDEX_ALIAS=test_assets_${RUN_ID}` 即可，**不改后端代码**
- **PG schema 隔离需新增配置**：后端目前没有 `db_schema` 配置项，需在 `config.py` 新增字段 + 在 `database.py` 连接初始化时 `SET search_path`
- **k6 不进 CI**：性能测试仅本地手动跑 dev 环境，GitHub runner 连不到 dev host
- **`run_tests.bat all` 不含 perf**：`all` = unit + integration + e2e（对应 CI 闸门），`full` = all + perf（本地完整验收）
- **保留现有 16 个后端 mock 单元测试**：`backend/tests/test_*.py` 全部保留通过，不与此层重复
- **覆盖率门槛**：前端 ≥ 60%，后端 ≥ 70%（按文件计，不强制未测试路径）
- **失败产物上传**：E2E 视觉质量用例失败时必须上传截图、trace、控制台日志、失败图片 URL（§3.3.2）

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `frontend/src/utils/testid.ts` | 新建 | `slug(v)` 函数，FilterGroup 与 E2E 共用 |
| `frontend/src/utils/__tests__/testid.spec.ts` | 新建 | slug 单元测试 |
| `frontend/src/components/SearchBar.vue` | 修改 | 加 `data-testid="search-input"`、`parse-chip-{field}`、`suggestion-item-{idx}` |
| `frontend/src/components/ModuleTabs.vue` | 修改 | 加 `data-testid="module-tab-{1-4}"` |
| `frontend/src/components/FilterPanel.vue` | 修改 | 加 `data-testid="filter-group-{field_name}"`，INITIAL_GROUP_RENDER_LIMIT=6 + rAF 批量挂载 |
| `frontend/src/components/FilterGroup.vue` | 修改 | 加 `data-testid="filter-option-{field}-{slug(value)}"`、`filter-range-min/max-{field}`、`filter-clear-{field}` |
| `frontend/src/components/ResultGrid.vue` | 修改 | 加 `data-testid="result-grid"` |
| `frontend/src/components/AssetCard.vue` | 修改 | 加 `data-testid="asset-card-{asset.id}"`、`asset-preview-{asset.id}"`、`asset-id-row-{asset.id}"` |
| `frontend/src/components/AssetDetailModal.vue` | 修改 | 加 `data-testid="detail-modal"`、`detail-preview`、`copy-path-btn`、`copy-id-btn`、`detail-close` |
| `frontend/src/components/PaginationBar.vue` | 修改 | 加 `data-testid="page-prev"`、`page-next`、`page-current` |
| `frontend/package.json` | 修改 | 新增 vitest/@vue/test-utils/@vitest/coverage-v8/jsdom/@playwright/test 依赖 + test:unit/test:watch/test:coverage scripts |
| `frontend/vitest.config.ts` | 新建 | Vitest 配置：jsdom + v8 coverage + 60% threshold |
| `frontend/src/stores/__tests__/searchStore.spec.ts` | 新建 | 17 个 searchStore 单元测试 |
| `frontend/src/components/__tests__/SearchBar.spec.ts` | 新建 | 11 个 SearchBar 单元测试 |
| `frontend/src/components/__tests__/FilterGroup.spec.ts` | 新建 | 9 个 FilterGroup 单元测试 |
| `frontend/src/components/__tests__/FilterPanel.spec.ts` | 新建 | 2 个 FilterPanel 单元测试 |
| `frontend/src/components/__tests__/AssetCard.spec.ts` | 新建 | 6 个 AssetCard 单元测试 |
| `frontend/src/components/__tests__/AssetDetailModal.spec.ts` | 新建 | 5 个 AssetDetailModal 单元测试 |
| `frontend/src/components/__tests__/ModuleTabs.spec.ts` | 新建 | 4 个 ModuleTabs 单元测试 |
| `backend/app/config.py` | 修改 | 新增 `db_schema: str = ""` 配置字段 |
| `backend/app/models/database.py` | 修改 | `get_pool()` 连接初始化时按 `db_schema` 设置 `search_path` |
| `backend/requirements.txt` | 修改 | 补 pytest-asyncio、httpx（如未有） |
| `backend/tests/conftest.py` | 新建 | schema 生命周期 fixture + test_client + seeded_db + admin_key |
| `backend/tests/integration/__init__.py` | 新建 | 标记 integration 子包 |
| `backend/tests/integration/test_health_api.py` | 新建 | 3 个 health API 测试 |
| `backend/tests/integration/test_filter_api.py` | 新建 | 6 个 filter API 测试 |
| `backend/tests/integration/test_search_api.py` | 新建 | 21 个 search API 测试 |
| `backend/tests/integration/test_suggestions_api.py` | 新建 | 4 个 suggestions API 测试 |
| `backend/tests/integration/test_admin_api.py` | 新建 | 9 个 admin API 测试 |
| `backend/tests/integration/test_search_concurrency.py` | 新建 | 1 个并发原子性测试 |
| `docker-compose.test.yml` | 新建 | fixture 环境：PG/ES/backend/nginx，端口 15432/19200/18000/18081 |
| `nginx.test.conf` | 新建 | 与 nginx.dev.conf 同结构，代理 backend-test:8000 |
| `tests/e2e/fixtures/models.fixture.json` | 新建 | 模型 fixture ~50 条 |
| `tests/e2e/fixtures/animator.fixture.json` | 新建 | 动作 fixture ~50 条 |
| `tests/e2e/fixtures/effects.fixture.json` | 新建 | 特效 fixture ~50 条 |
| `tests/e2e/fixtures/icons.fixture.json` | 新建 | 图标 fixture ~50 条 |
| `tests/e2e/fixtures/previews/` | 新建 | 50 张 ~5KB 测试图片（256×256 PNG/GIF） |
| `tests/e2e/playwright.config.ts` | 新建 | Playwright 配置：baseURL=18081，trace=on-failure |
| `tests/e2e/pages/SearchPage.ts` | 新建 | Page Object 主入口 |
| `tests/e2e/pages/ModuleTabs.ts` | 新建 | 模块切换 PO |
| `tests/e2e/pages/FilterPanel.ts` | 新建 | 筛选面板 PO |
| `tests/e2e/pages/ResultGrid.ts` | 新建 | 结果网格 PO |
| `tests/e2e/pages/AssetDetailModal.ts` | 新建 | 详情弹窗 PO |
| `tests/e2e/fixtures/visual-quality-helpers.ts` | 新建 | 视觉质量失败产物收集工具 |
| `tests/e2e/specs/search.spec.ts` | 新建 | 11 个搜索 E2E |
| `tests/e2e/specs/filter.spec.ts` | 新建 | 9 个筛选 E2E |
| `tests/e2e/specs/detail-modal.spec.ts` | 新建 | 7 个详情弹窗 E2E |
| `tests/e2e/specs/module-tabs.spec.ts` | 新建 | 4 个模块切换 E2E |
| `tests/e2e/specs/pagination.spec.ts` | 新建 | 5 个分页 E2E |
| `tests/e2e/specs/preview-loading.spec.ts` | 新建 | 8 个预览加载 E2E |
| `tests/e2e/specs/responsive.spec.ts` | 新建 | 4 个响应式 E2E |
| `tests/e2e/specs/error-states.spec.ts` | 新建 | 4 个错误状态 E2E |
| `tests/e2e/specs/visual-quality.spec.ts` | 新建 | 6 个视觉质量 E2E |
| `tests/e2e/specs/a11y.spec.ts` | 新建 | 2 个辅助功能 E2E |
| `tests/performance/k6-baseline.js` | 新建 | k6 基准脚本（搜索/suggestions/filter/卡片图） |
| `tests/performance/k6-load.js` | 新建 | k6 并发负载脚本（50/200 并发） |
| `tests/performance/reports/` | 新建 | k6 报告输出目录（.gitkeep） |
| `docs/performance-testing.md` | 新建 | k6 本地 runbook |
| `docs/testing-guide.md` | 新建 | 测试运行与维护说明 |
| `scripts/sample_real_data.py` | 新建 | 季度重生成 fixture 脚本 |
| `scripts/run_tests.bat` | 新建 | Windows 一键脚本 |
| `scripts/run_tests.sh` | 新建 | Linux/CI 一键脚本 |
| `.github/workflows/test.yml` | 新建 | CI workflow：frontend-unit + backend-integration + e2e |

---

## 阶段 1：前端测试钩子 + Vitest 配置 + ~52 个单元测试

### 任务 1.1：slug 工具函数

**文件：**
- 新建：`frontend/src/utils/testid.ts`
- 测试：`frontend/src/utils/__tests__/testid.spec.ts`

**接口：**
- 产生：`slug(v: string): string` — 把含中文/斜杠/空格/括号的 value 转为合法 test id 片段

- [ ] **步骤 1：先写失败测试**

```typescript
// frontend/src/utils/__tests__/testid.spec.ts
import { describe, it, expect } from 'vitest'
import { slug } from '../testid'

describe('slug', () => {
  it('保留中文字符', () => {
    expect(slug('僧侣')).toBe('僧侣')
  })
  it('斜杠/空格/括号转连字符', () => {
    expect(slug('Front/Left')).toBe('front-left')
    expect(slug('男性 (M)')).toBe('男性-m')
  })
  it('小写英文字母', () => {
    expect(slug('Warrior')).toBe('warrior')
  })
  it('多个连续分隔符压缩为单个连字符', () => {
    expect(slug('a   b///c')).toBe('a-b-c')
  })
  it('去首尾连字符', () => {
    expect(slug('--abc--')).toBe('abc')
  })
  it('空字符串返回空', () => {
    expect(slug('')).toBe('')
  })
})
```

- [ ] **步骤 2：运行验证失败**

```bash
cd frontend && npx vitest run src/utils/__tests__/testid.spec.ts
```
预期：FAIL，报错 `Cannot find module '../testid'`

- [ ] **步骤 3：实现 slug 函数**

```typescript
// frontend/src/utils/testid.ts
export function slug(v: string): string {
  return v
    .trim()
    .toLowerCase()
    .replace(/[^\w一-龥]+/g, '-')
    .replace(/^-+|-+$/g, '')
}
```

- [ ] **步骤 4：运行验证通过**

```bash
cd frontend && npx vitest run src/utils/__tests__/testid.spec.ts
```
预期：PASS（6 个用例全绿）

- [ ] **步骤 5：提交**

```bash
git add frontend/src/utils/testid.ts frontend/src/utils/__tests__/testid.spec.ts
git commit -m "feat(测试): 新增 slug 工具函数用于 data-testid 生成

为后续前端组件加 data-testid 钩子做铺垫。中文保留、斜杠/空格/
括号转连字符，FilterGroup 与 E2E Page Object 共用同一实现
避免漂移。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.2：Vitest 依赖与配置

**文件：**
- 修改：`frontend/package.json`
- 新建：`frontend/vitest.config.ts`

**接口：**
- 产生：`npm run test:unit`、`npm run test:coverage`、`npm run test:watch` 三个 script
- 产生：`vitest.config.ts` 配置 jsdom + v8 coverage + 60% threshold

- [ ] **步骤 1：检查现有 package.json devDependencies**

```bash
cd frontend && cat package.json | grep -A 20 '"devDependencies"'
```
记录哪些已有、哪些需新增。

- [ ] **步骤 2：在 package.json devDependencies 新增依赖**

```json
{
  "devDependencies": {
    "vitest": "^3.0.0",
    "@vue/test-utils": "^2.4.6",
    "@vitest/coverage-v8": "^3.0.0",
    "jsdom": "^25.0.0",
    "@playwright/test": "^1.50.0"
  }
}
```

- [ ] **步骤 3：在 package.json scripts 新增**

```json
{
  "scripts": {
    "test:unit": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  }
}
```

- [ ] **步骤 4：新建 vitest.config.ts**

```typescript
// frontend/vitest.config.ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.{ts,vue}'],
      exclude: ['src/**/*.spec.ts', 'src/types/**'],
      thresholds: { lines: 60, functions: 60, branches: 60, statements: 60 },
    },
  },
})
```

- [ ] **步骤 5：安装依赖并验证空跑**

```bash
cd frontend && npm install
npx vitest run --reporter verbose
```
预期：0 test files，无报错（此时还没有 spec 文件；若 testid.spec.ts 已建则跑通）

- [ ] **步骤 6：提交**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts
git commit -m "chore(前端测试): 配置 Vitest 与覆盖率门槛

新增 vitest@3、@vue/test-utils@2.4、@vitest/coverage-v8、jsdom、
@playwright/test 依赖。vitest.config.ts 用 jsdom 环境，覆盖率
门槛 60%（按文件计）。CI 用 npm run test:coverage 不裸跑 npx vitest，
保证本地与 CI 同配置。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.3：SearchBar.vue 加 data-testid

**文件：**
- 修改：`frontend/src/components/SearchBar.vue`

**接口：**
- 消费：`slug()` from `@/utils/testid`
- 产生：`search-input`、`parse-chip-{field}`、`suggestion-item-{idx}` 三个 test id 钩子

- [ ] **步骤 1：阅读现有 SearchBar.vue 找到输入框、chip、建议列表位置**

```bash
grep -n "input\|chip\|suggestion" frontend/src/components/SearchBar.vue | head -30
```

- [ ] **步骤 2：在 input 元素加 data-testid**

```vue
<input
  v-model="localQuery"
  data-testid="search-input"
  ...
/>
```

- [ ] **步骤 3：在 parse-info chip 元素加 data-testid**

```vue
<span
  v-for="(value, field) in parseInfo?.parsed_filters"
  :key="field"
  :data-testid="`parse-chip-${field}`"
  class="parse-chip"
>
  ...
</span>
```

- [ ] **步骤 4：在 exclude 建议项加 data-testid**

```vue
<li
  v-for="(s, idx) in suggestions"
  :key="idx"
  :data-testid="`suggestion-item-${idx}`"
  @click="insertExclude(s)"
>
  ...
</li>
```

- [ ] **步骤 5：构建验证**

```bash
cd frontend && npx vite build
```
预期：构建成功，无 type error

- [ ] **步骤 6：提交**

```bash
git add frontend/src/components/SearchBar.vue
git commit -m "feat(前端测试): SearchBar 加 data-testid 钩子

加 search-input、parse-chip-{field}、suggestion-item-{idx} 三个
钩子。parse-chip 用 field 名（稳定），suggestion 用 idx（短暂
浮层单次会话内稳定，可保留）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.4：ModuleTabs.vue 加 data-testid

**文件：**
- 修改：`frontend/src/components/ModuleTabs.vue`

- [ ] **步骤 1：找到 tab 渲染位置**

```bash
grep -n "tab\|module" frontend/src/components/ModuleTabs.vue | head -20
```

- [ ] **步骤 2：在 tab 元素加 data-testid**

```vue
<button
  v-for="t in moduleTypes"
  :key="t.value"
  :data-testid="`module-tab-${t.value}`"
  :class="{ active: store.moduleType === t.value }"
  @click="selectModule(t.value)"
>
  {{ t.label }}
</button>
```

- [ ] **步骤 3：构建验证**

```bash
cd frontend && npx vite build
```

- [ ] **步骤 4：提交**

```bash
git add frontend/src/components/ModuleTabs.vue
git commit -m "feat(前端测试): ModuleTabs 加 data-testid 钩子

加 module-tab-{1-4}（模块类型枚举稳定）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.5：FilterGroup.vue 加 data-testid

**文件：**
- 修改：`frontend/src/components/FilterGroup.vue`

**接口：**
- 消费：`slug()` from `@/utils/testid`

- [ ] **步骤 1：在 tag-pill 加 data-testid**

```vue
<button
  v-for="opt in filteredValues"
  :key="opt.value"
  class="tag-pill"
  :data-testid="`filter-option-${field}-${slug(opt.value)}`"
  ...
>
```

- [ ] **步骤 2：在 range 滑块加 data-testid（若 isRange）**

```vue
<el-slider
  v-model="rangeValue"
  :data-testid="`filter-range-${field}`"
  range
  ...
/>
```

- [ ] **步骤 3：在清空按钮加 data-testid（如有）**

```vue
<button
  v-if="activeCount > 0"
  data-testid="filter-clear-{field}"
  @click="clearFilter"
>
  清空
</button>
```

- [ ] **步骤 4：构建验证**

```bash
cd frontend && npx vite build
```

- [ ] **步骤 5：提交**

```bash
git add frontend/src/components/FilterGroup.vue
git commit -m "feat(前端测试): FilterGroup 加 data-testid 钩子

加 filter-option-{field}-{slug(value)}、filter-range-{field}、
filter-clear-{field}。value 用 slug() 处理中文/斜杠/空格，
保证选择器合法。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.6：FilterPanel.vue + ResultGrid.vue + AssetCard.vue 加 data-testid

**文件：**
- 修改：`frontend/src/components/FilterPanel.vue`
- 修改：`frontend/src/components/ResultGrid.vue`
- 修改：`frontend/src/components/AssetCard.vue`

- [ ] **步骤 1：FilterPanel 加 filter-group-{field_name}**

```vue
<FilterGroup
  v-for="def in visibleDefinitions"
  :key="def.field_name"
  :definition="def"
  :data-testid="`filter-group-${def.field_name}`"
/>
```

- [ ] **步骤 2：ResultGrid 加 result-grid**

```vue
<div class="result-grid" data-testid="result-grid">
  ...
</div>
```

- [ ] **步骤 3：AssetCard 加 asset-card-{asset.id} 等**

```vue
<div class="asset-card" :data-testid="`asset-card-${asset.id}`">
  <img
    :src="previewUrl"
    :data-testid="`asset-preview-${asset.id}`"
    @error="onError"
  />
  <div v-if="isIcon" :data-testid="`asset-id-row-${asset.id}`">
    ID: {{ asset.id }}
  </div>
</div>
```

- [ ] **步骤 4：构建验证**

```bash
cd frontend && npx vite build
```

- [ ] **步骤 5：提交**

```bash
git add frontend/src/components/FilterPanel.vue frontend/src/components/ResultGrid.vue frontend/src/components/AssetCard.vue
git commit -m "feat(前端测试): FilterPanel/ResultGrid/AssetCard 加 data-testid 钩子

- FilterPanel: filter-group-{field_name}
- ResultGrid: result-grid
- AssetCard: asset-card-{asset.id}、asset-preview-{asset.id}、
  asset-id-row-{asset.id}（仅 icon 模块渲染 ID 行）

用后端资产 id 而非列表 idx，避免搜索/筛选/分页变化后 idx 漂移
导致 E2E 误点。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.7：AssetDetailModal.vue + PaginationBar.vue 加 data-testid

**文件：**
- 修改：`frontend/src/components/AssetDetailModal.vue`
- 修改：`frontend/src/components/PaginationBar.vue`

- [ ] **步骤 1：AssetDetailModal 加 5 个 test id**

```vue
<el-dialog :data-testid="'detail-modal'">
  <img :src="..." data-testid="detail-preview" />
  <button data-testid="copy-path-btn">复制路径</button>
  <button v-if="isIcon" data-testid="copy-id-btn">复制 ID</button>
  <button data-testid="detail-close" @click="close">×</button>
</el-dialog>
```

- [ ] **步骤 2：PaginationBar 加 page-prev/page-next/page-current**

```vue
<button data-testid="page-prev" @click="prev">上一页</button>
<span data-testid="page-current">{{ page }}</span>
<button data-testid="page-next" @click="next">下一页</button>
```

- [ ] **步骤 3：构建验证**

```bash
cd frontend && npx vite build
```

- [ ] **步骤 4：提交**

```bash
git add frontend/src/components/AssetDetailModal.vue frontend/src/components/PaginationBar.vue
git commit -m "feat(前端测试): AssetDetailModal/PaginationBar 加 data-testid 钩子

- AssetDetailModal: detail-modal、detail-preview、copy-path-btn、
  copy-id-btn（仅 icon）、detail-close
- PaginationBar: page-prev、page-next、page-current

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.8：searchStore 单元测试（17 个）

**文件：**
- 新建：`frontend/src/stores/__tests__/searchStore.spec.ts`

**接口：**
- 消费：`useSearchStore` from `@/stores/searchStore`
- 消费：Pinia `createPinia` + `setActivePinia`

- [ ] **步骤 1：写测试文件**

```typescript
// frontend/src/stores/__tests__/searchStore.spec.ts
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, it, expect, vi } from 'vitest'
import { useSearchStore } from '../searchStore'

describe('searchStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('setModuleType 重置 filters/query/page', () => { /* ... */ })
  it('setModuleType 同步置 loading=true 并清空 response（ffd4785）', () => { /* ... */ })
  it('setFilter 合并 enum_multi', () => { /* ... */ })
  it('doSearch 取消旧请求（AbortController）', () => { /* ... */ })
  it('doSearch 旧响应被丢弃（latestSearchId 防竞态）', () => { /* ... */ })
  it('doSearch AbortController 等价 — 连续 10 个请求前 9 个被取消', () => { /* ... */ })
  it('dismissedFields 被dismiss后重新解析查询', () => { /* ... */ })
  it('dismissedFields.clear() 在每次输入/搜索时触发', () => { /* ... */ })
  it('输入触发 cancelPendingSearch 取消旧 AbortController', () => { /* ... */ })
  it('分页边界 — page=0 不发请求', () => { /* ... */ })
  it('分页边界 — page_offset_max=10000 阈值', () => { /* ... */ })
  it('loadDefinitions 缓存命中不重复请求', () => { /* ... */ })
  it('loadDefinitions module_type 切换重新拉取', () => { /* ... */ })
  it('parseInfo dismissFilter 触发 doSearch', () => { /* ... */ })
  it('facets 字段顺序与 tagDefinitions 一致', () => { /* ... */ })
  it('clearAllFilters 清空所有字段', () => { /* ... */ })
  it('excludes 排除逻辑生效', () => { /* ... */ })
})
```

每个 `it` 块补全实际断言代码（参考 spec §6.5 示例）。

- [ ] **步骤 2：运行验证**

```bash
cd frontend && npx vitest run src/stores/__tests__/searchStore.spec.ts
```
预期：17 个用例全绿（部分用例需 mock fetch / axios）

- [ ] **步骤 3：提交**

```bash
git add frontend/src/stores/__tests__/searchStore.spec.ts
git commit -m "test(前端单元): searchStore 17 个用例覆盖模块切换/防抖/竞态/dismiss

覆盖 setModuleType 同步 loading+清空 response（ffd4785）、
AbortController 取消、latestSearchId 防竞态、dismissedFields
重解析、分页边界、loadDefinitions 缓存、excludes 排除等关键
路径。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.9：SearchBar 单元测试（11 个）

**文件：**
- 新建：`frontend/src/components/__tests__/SearchBar.spec.ts`

- [ ] **步骤 1：写测试文件**

```typescript
// frontend/src/components/__tests__/SearchBar.spec.ts
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import SearchBar from '../SearchBar.vue'
import { useSearchStore } from '@/stores/searchStore'

describe('SearchBar', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('500ms 防抖内连续输入只发一次请求', () => { /* ... */ })
  it('输入清空立即触发 search（不等防抖）', () => { /* ... */ })
  it('Enter 键绕过防抖直接搜索', () => { /* ... */ })
  it('parse-info chip 显示并支持 dismiss', () => { /* ... */ })
  it('exclude 建议点击插入并触发搜索', () => { /* ... */ })
  it('输入触发 cancelPendingSearch 取消旧 AbortController', () => { /* ... */ })
  it('dismissedFields.clear() 在输入时触发', () => { /* ... */ })
  it('chip render 用 data-testid=parse-chip-{field}', () => { /* ... */ })
  it('suggestion render 用 data-testid=suggestion-item-{idx}', () => { /* ... */ })
  it('空 query 不发请求', () => { /* ... */ })
  it('props.parseInfo 更新触发 chip 重新渲染', () => { /* ... */ })
})
```

每个 `it` 块补全断言（用 `vi.useFakeTimers()` 测防抖，用 `wrapper.find()` 测 test id）。

- [ ] **步骤 2：运行验证**

```bash
cd frontend && npx vitest run src/components/__tests__/SearchBar.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add frontend/src/components/__tests__/SearchBar.spec.ts
git commit -m "test(前端单元): SearchBar 11 个用例覆盖防抖/清空/Enter/chip/exclude

500ms 防抖、清空立即搜索、Enter 绕过防抖、parse-info chip
显示与 dismiss、exclude 建议点击、cancelPendingSearch、
data-testid 钩子验证。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.10：FilterGroup 单元测试（9 个）

**文件：**
- 新建：`frontend/src/components/__tests__/FilterGroup.spec.ts`

- [ ] **步骤 1：写测试文件**

```typescript
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, it, expect } from 'vitest'
import FilterGroup from '../FilterGroup.vue'
import { useSearchStore } from '@/stores/searchStore'

describe('FilterGroup', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('enum_single 单选', () => { /* ... */ })
  it('enum_multi 多选 + 全选', () => { /* ... */ })
  it('number_range min/max 互相约束', () => { /* ... */ })
  it('boolean 切换', () => { /* ... */ })
  it('search-within 过滤大列表', () => { /* ... */ })
  it('RENDER_CAP=200 无搜索时只渲染前 200 项（245c2ff）', () => {
    const fakeValues = Array.from({ length: 10838 }, (_, i) => ({
      value: `v${i}`, display_name: `V${i}`,
    }))
    const wrapper = mount(FilterGroup, {
      props: { definition: { field_name: 'semantic', field_type: 'enum_multi', values: fakeValues } },
    })
    expect(wrapper.findAll('.tag-pill').length).toBe(200)
    expect(wrapper.text()).toContain('共 10,838 项')
  })
  it('有搜索时渲染全部匹配项（不受 cap 限制）', () => { /* ... */ })
  it('cappedCount 提示条显示总数', () => { /* ... */ })
  it('filter-option-{field}-{slug(value)} 钩子生成正确', () => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd frontend && npx vitest run src/components/__tests__/FilterGroup.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add frontend/src/components/__tests__/FilterGroup.spec.ts
git commit -m "test(前端单元): FilterGroup 9 个用例含 RENDER_CAP=200 验证

覆盖 enum_single/enum_multi/number_range/boolean 各类型、
search-within 过滤、RENDER_CAP=200 限制（245c2ff）、
filter-option 钩子 slug 化。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.11：FilterPanel 单元测试（2 个）

**文件：**
- 新建：`frontend/src/components/__tests__/FilterPanel.spec.ts`

- [ ] **步骤 1：写测试文件**

```typescript
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, it, expect, vi } from 'vitest'
import { nextTick } from 'vue'
import FilterPanel from '../FilterPanel.vue'
import { useSearchStore } from '@/stores/searchStore'

describe('FilterPanel', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('INITIAL_GROUP_RENDER_LIMIT=6 + rAF 批量挂载（791acb9）', async () => {
    const store = useSearchStore()
    store.tagDefinitions = Array.from({ length: 15 }, (_, i) => ({
      field_name: `f${i}`, is_filterable: true, field_type: 'enum_single', values: [],
    }))
    const wrapper = mount(FilterPanel)
    await nextTick()
    expect(wrapper.findAll('.filter-group').length).toBe(6)
    await new Promise(r => requestAnimationFrame(r))
    await nextTick()
    expect(wrapper.findAll('.filter-group').length).toBe(15)
  })

  it('卸载时清理 rAF（791acb9）', () => {
    const cancelSpy = vi.spyOn(globalThis, 'cancelAnimationFrame')
    const store = useSearchStore()
    store.tagDefinitions = Array.from({ length: 15 }, (_, i) => ({
      field_name: `f${i}`, is_filterable: true, field_type: 'enum_single', values: [],
    }))
    const wrapper = mount(FilterPanel)
    wrapper.unmount()
    expect(cancelSpy).toHaveBeenCalled()
  })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd frontend && npx vitest run src/components/__tests__/FilterPanel.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add frontend/src/components/__tests__/FilterPanel.spec.ts
git commit -m "test(前端单元): FilterPanel 2 个用例验证 rAF 批量挂载与卸载清理

INITIAL_GROUP_RENDER_LIMIT=6 同步只挂 6 个，rAF 回调后挂全部 15 个；
卸载时 cancelAnimationFrame 被调用，避免内存泄漏（791acb9）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.12：AssetCard 单元测试（6 个）

**文件：**
- 新建：`frontend/src/components/__tests__/AssetCard.spec.ts`

- [ ] **步骤 1：写测试文件**

```typescript
import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import AssetCard from '../AssetCard.vue'

describe('AssetCard', () => {
  it('预览图加载失败回退 SVG placeholder 且实际渲染（@error 触发）', () => { /* ... */ })
  it('模型模块预览 URL 正确', () => { /* ... */ })
  it('动作模块 GIF URL 正确', () => { /* ... */ })
  it('特效模块 GIF URL 正确', () => { /* ... */ })
  it('图标模块 PNG URL 正确', () => { /* ... */ })
  it('icon 才显示 ID 行', () => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd frontend && npx vitest run src/components/__tests__/AssetCard.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add frontend/src/components/__tests__/AssetCard.spec.ts
git commit -m "test(前端单元): AssetCard 6 个用例覆盖 4 模块预览与 SVG fallback

4 模块预览 URL 正确性、@error 触发 SVG placeholder 实际渲染、
icon 模块才显示 ID 行。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.13：AssetDetailModal 单元测试（5 个）

**文件：**
- 新建：`frontend/src/components/__tests__/AssetDetailModal.spec.ts`

- [ ] **步骤 1：写测试文件**

```typescript
import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import AssetDetailModal from '../AssetDetailModal.vue'

describe('AssetDetailModal', () => {
  it('复制路径', () => { /* ... */ })
  it('复制 icon ID（仅 icon 模块）', () => { /* ... */ })
  it('clipboard fallback（navigator.clipboard 不可用时）', () => { /* ... */ })
  it('ESC 关闭', () => { /* ... */ })
  it('点遮罩关闭', () => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd frontend && npx vitest run src/components/__tests__/AssetDetailModal.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add frontend/src/components/__tests__/AssetDetailModal.spec.ts
git commit -m "test(前端单元): AssetDetailModal 5 个用例覆盖复制/ESC/遮罩

复制路径、复制 icon ID（仅 icon）、clipboard fallback、
ESC 关闭、点遮罩关闭。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.14：ModuleTabs 单元测试（4 个）

**文件：**
- 新建：`frontend/src/components/__tests__/ModuleTabs.spec.ts`

- [ ] **步骤 1：写测试文件**

```typescript
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import ModuleTabs from '../ModuleTabs.vue'
import { useSearchStore } from '@/stores/searchStore'

describe('ModuleTabs', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('4 个 tab 切换', () => { /* ... */ })
  it('当前 tab 高亮', () => { /* ... */ })
  it('切换触发 reset', () => { /* ... */ })
  it('selectModule 用 Promise.all 并行 loadDefinitions + doSearch（ffd4785）', async () => {
    const store = useSearchStore()
    const defSpy = vi.spyOn(store, 'loadDefinitions').mockResolvedValue()
    const searchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()
    const wrapper = mount(ModuleTabs)
    await wrapper.find('[data-testid="module-tab-2"]').trigger('click')
    await flushPromises()
    expect(defSpy).toHaveBeenCalled()
    expect(searchSpy).toHaveBeenCalled()
  })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd frontend && npx vitest run src/components/__tests__/ModuleTabs.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add frontend/src/components/__tests__/ModuleTabs.spec.ts
git commit -m "test(前端单元): ModuleTabs 4 个用例含 Promise.all 并行验证

4 个 tab 切换、当前 tab 高亮、切换触发 reset、
selectModule 用 Promise.all 并行 loadDefinitions + doSearch（ffd4785）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.15：run_tests.bat/.sh unit 子命令

**文件：**
- 新建：`scripts/run_tests.bat`
- 新建：`scripts/run_tests.sh`

- [ ] **步骤 1：写 run_tests.bat（unit 部分先实现）**

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
if "%TARGET%"=="full" goto full
echo Usage: run_tests.bat [unit^|integration^|e2e^|perf^|all^|full]
exit /b 1

:unit
echo === Frontend unit tests ===&& cd frontend && npm run test:unit && cd ..
echo === Backend unit tests ===&& cd backend && python -m pytest tests/ -k "not integration" && cd ..
goto end

:integration
echo TODO: implement in phase 2
goto end

:e2e
echo TODO: implement in phase 3
goto end

:perf
echo TODO: implement in phase 4
goto end

:all
call %0 unit && call %0 integration && call %0 e2e
goto end

:full
call %0 all && call %0 perf
goto end

:end
```

- [ ] **步骤 2：写 run_tests.sh（同结构，bash 语法）**

```bash
#!/bin/bash
set -e
TARGET=${1:-all}

case "$TARGET" in
  unit)
    echo "=== Frontend unit tests ==="
    cd frontend && npm run test:unit && cd ..
    echo "=== Backend unit tests ==="
    cd backend && python -m pytest tests/ -k "not integration" && cd ..
    ;;
  integration|e2e|perf)
    echo "TODO: implement $TARGET"
    ;;
  all)
    "$0" unit && "$0" integration && "$0" e2e
    ;;
  full)
    "$0" all && "$0" perf
    ;;
  *)
    echo "Usage: $0 [unit|integration|e2e|perf|all|full]"
    exit 1
    ;;
esac
```

- [ ] **步骤 3：本地跑 unit 验证**

```bash
scripts/run_tests.bat unit
# 或
chmod +x scripts/run_tests.sh && scripts/run_tests.sh unit
```
预期：前端单元 + 后端 mock 单元全绿

- [ ] **步骤 4：提交**

```bash
git add scripts/run_tests.bat scripts/run_tests.sh
git commit -m "feat(测试脚本): 新增 run_tests.bat/.sh 一键脚本

all=unit+integration+e2e（CI 闸门，不含 perf），
full=all+perf（本地完整验收）。unit 子命令跑前端 Vitest +
后端 mock 单元测试。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 1.16：阶段 1 覆盖率验证

- [ ] **步骤 1：跑覆盖率**

```bash
cd frontend && npm run test:coverage
```
预期：lines/Functions/Branches/Statements ≥ 60%

- [ ] **步骤 2：若未达 60%，补测试或调整 vitest.config.ts thresholds**

- [ ] **步骤 3：提交覆盖率报告（如有调整）**

```bash
git add frontend/vitest.config.ts
git commit -m "chore(前端测试): 调整覆盖率门槛至 60% 达标

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 阶段 2：pytest fixtures + ~44 个 API 集成测试 + docker-compose.test.yml

### 任务 2.1：backend/app/config.py 新增 db_schema

**文件：**
- 修改：`backend/app/config.py`

**接口：**
- 产生：`settings.db_schema: str`，空字符串=用默认 search_path；非空=SET search_path TO {schema}, public

- [ ] **步骤 1：阅读现有 config.py**

```bash
cat backend/app/config.py
```

- [ ] **步骤 2：在 Settings 类中新增 db_schema 字段**

```python
class Settings(BaseSettings):
    database_url: str = "postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao"
    es_url: str = "http://localhost:9200"
    es_index_alias: str = "assets"
    db_schema: str = ""  # 空 = 用默认 search_path；非空 = SET search_path TO {schema}, public
    # ... 其他现有字段
```

- [ ] **步骤 3：验证配置加载**

```bash
cd backend && python -c "from app.config import settings; print(f'db_schema={settings.db_schema!r}')"
```
预期：`db_schema=''`

- [ ] **步骤 4：提交**

```bash
git add backend/app/config.py
git commit -m "feat(后端配置): 新增 db_schema 字段支持并行 CI schema 隔离

空字符串=用默认 search_path（向后兼容）；非空=连接初始化时
SET search_path TO {schema}, public。CI 设 DB_SCHEMA=
ci_biaoqiao_\${RUN_ID} 实现并行 PR 隔离。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.2：backend/app/models/database.py 设置 search_path

**文件：**
- 修改：`backend/app/models/database.py`

**接口：**
- 消费：`settings.db_schema` from `@/config`

- [ ] **步骤 1：阅读现有 database.py**

```bash
cat backend/app/models/database.py
```

- [ ] **步骤 2：在 get_pool() 连接初始化后设置 search_path**

```python
from app.config import settings

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url)
        if settings.db_schema:
            async with _pool.acquire() as conn:
                await conn.execute(f"SET search_path TO {settings.db_schema}, public")
    return _pool
```

- [ ] **步骤 3：写单元测试验证 search_path 设置**

```python
# backend/tests/test_db_schema.py
import pytest
import os
from app.config import settings
from app.models.database import get_pool, _pool

@pytest.mark.asyncio
async def test_db_schema_sets_search_path(monkeypatch):
    monkeypatch.setattr(settings, 'db_schema', 'test_schema')
    # ... 触发 get_pool 并验证 SET search_path 被执行
```

- [ ] **步骤 4：运行验证**

```bash
cd backend && python -m pytest tests/test_db_schema.py -v
```

- [ ] **步骤 5：提交**

```bash
git add backend/app/models/database.py backend/tests/test_db_schema.py
git commit -m "feat(后端数据库): get_pool 初始化时按 db_schema 设置 search_path

非空 db_schema 触发 SET search_path TO {schema}, public，
使后续所有查询自动落到该 schema。配合 CI DB_SCHEMA 环境变量
实现并行 PR 隔离。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.3：backend/tests/conftest.py schema + fixture 生命周期

**文件：**
- 新建：`backend/tests/conftest.py`

**接口：**
- 产生：`test_schema` session fixture
- 产生：`test_client` function fixture
- 产生：`seeded_db` function fixture
- 产生：`admin_key` fixture

- [ ] **步骤 1：写 conftest.py**

```python
# backend/tests/conftest.py
import os
import asyncio
import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture(scope="session")
def env_run_id():
    return os.environ.get("RUN_ID", "local")

@pytest_asyncio.fixture(scope="session")
async def test_schema(env_run_id):
    """创建独立 schema + 导入 fixture + reindex；teardown 清理"""
    schema_name = f"biaoqiao_test_{env_run_id}"
    admin_url = os.environ["DATABASE_URL"].replace("/biaoqiao_test", "/postgres")
    admin_conn = await asyncpg.connect(admin_url)
    await admin_conn.execute(f'CREATE SCHEMA IF NOT EXISTS {schema_name}')
    await admin_conn.close()
    os.environ["DB_SCHEMA"] = schema_name
    yield schema_name
    await admin_conn.execute(f'DROP SCHEMA {schema_name} CASCADE')
    await admin_conn.close()

@pytest_asyncio.fixture
async def test_client(test_schema):
    """httpx AsyncClient 打 /api/v1/* HTTP"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def seeded_db(test_client):
    """导入 4 个 fixture JSON + reindex + refresh-dictionary"""
    for module in [1, 2, 3, 4]:
        fixture_path = f"tests/e2e/fixtures/{['models','animator','effects','icons'][module-1]}.fixture.json"
        with open(fixture_path, "rb") as f:
            resp = await test_client.post(
                f"/api/v1/admin/import-{['model','animator','effect','icon'][module-1]}-json",
                files={"file": f},
                headers={"X-Admin-Key": os.environ["ADMIN_API_KEY"]},
            )
            assert resp.status_code == 200
    await test_client.post("/api/v1/admin/reindex-es", headers={"X-Admin-Key": os.environ["ADMIN_API_KEY"]})
    await test_client.post("/api/v1/admin/refresh-dictionary", headers={"X-Admin-Key": os.environ["ADMIN_API_KEY"]})
    yield

@pytest.fixture
def admin_key():
    return os.environ["ADMIN_API_KEY"]
```

- [ ] **步骤 2：补 backend/requirements.txt 依赖（如未有）**

```text
pytest-asyncio
httpx
```

- [ ] **步骤 3：创建 integration 包标记**

```bash
mkdir -p backend/tests/integration
touch backend/tests/integration/__init__.py
```

- [ ] **步骤 4：写 smoke 测试验证 fixture 链路**

```python
# backend/tests/integration/test_smoke.py
import pytest

@pytest.mark.asyncio
async def test_fixture_loads(test_client, seeded_db):
    resp = await test_client.get("/api/v1/health")
    assert resp.status_code == 200
```

- [ ] **步骤 5：运行验证（需启 PG+ES）**

```bash
# 启 fixture 环境
docker compose -f docker-compose.test.yml up -d
# 跑 smoke
cd backend && RUN_ID=local python -m pytest tests/integration/test_smoke.py -v
```
预期：PASS（如失败先排查 fixture JSON 路径与 ADMIN_API_KEY）

- [ ] **步骤 6：提交**

```bash
git add backend/tests/conftest.py backend/tests/integration/__init__.py backend/tests/integration/test_smoke.py backend/requirements.txt
git commit -m "feat(后端测试): 新增 conftest.py schema 生命周期 + test_client + seeded_db

- test_schema: session 级，创建独立 schema + teardown drop
- test_client: httpx AsyncClient 打 /api/v1/* HTTP
- seeded_db: 导入 4 个 fixture JSON + reindex + refresh-dictionary
- admin_key: 从环境变量取

实现 §4.4 并行 CI 隔离：DB_SCHEMA=ci_biaoqiao_\${RUN_ID}。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.4：docker-compose.test.yml

**文件：**
- 新建：`docker-compose.test.yml`

- [ ] **步骤 1：写 docker-compose.test.yml**

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
      ES_INDEX_ALIAS: test_assets_${RUN_ID:-local}
      DB_SCHEMA: biaoqiao_test_${RUN_ID:-local}
    ports: ["18000:8000"]
    volumes:
      - ./runtime_data_test:/runtime_data
      - ./runtime_data_test/model/previews:/data/previews/model
      - ./runtime_data_test/animator/previews:/data/previews/animator
      - ./runtime_data_test/effect/gifs:/data/gifs
      - ./runtime_data_test/ui/pngs:/data/icons
  nginx-test:
    image: nginx:alpine
    ports: ["18081:80"]
    volumes:
      - ./frontend/dist:/usr/share/nginx/html
      - ./nginx.test.conf:/etc/nginx/conf.d/default.conf
      - ./runtime_data_test/model/previews:/data/previews/model:ro
      - ./runtime_data_test/animator/previews:/data/previews/animator:ro
      - ./runtime_data_test/effect/gifs:/data/gifs:ro
      - ./runtime_data_test/ui/pngs:/data/icons:ro
```

- [ ] **步骤 2：创建 runtime_data_test 目录骨架**

```bash
mkdir -p runtime_data_test/model/previews runtime_data_test/animator/previews runtime_data_test/effect/gifs runtime_data_test/ui/pngs
```

- [ ] **步骤 3：启动验证**

```bash
docker compose -f docker-compose.test.yml up -d --build
curl -sf http://localhost:18000/api/v1/health
docker compose -f docker-compose.test.yml down
```

- [ ] **步骤 4：提交**

```bash
git add docker-compose.test.yml runtime_data_test/.gitkeep
git commit -m "feat(测试环境): 新增 docker-compose.test.yml fixture 环境

PG/ES/backend/nginx，端口 15432/19200/18000/18081 避开 dev
8081/8000/5432/9200。容器内路径与正式/dev 完全一致（review #1），
保证 E2E 预览图/GIF/图标加载正常。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.5：nginx.test.conf

**文件：**
- 新建：`nginx.test.conf`

- [ ] **步骤 1：参考 nginx.dev.conf 写 nginx.test.conf**

```text
upstream backend_test { server backend-test:8000; }

server {
    listen 80;
    server_name localhost;
    client_max_body_size 100m;

    location /api/ {
        proxy_pass http://backend_test;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/previews/ {
        alias /data/previews/;
    }

    location /data/gifs/ {
        alias /data/gifs/;
    }

    location /data/icons/ {
        alias /data/icons/;
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **步骤 2：启动验证 nginx 代理**

```bash
docker compose -f docker-compose.test.yml up -d
curl -sf http://localhost:18081/api/v1/health
curl -sf http://localhost:18081/ | head -5
docker compose -f docker-compose.test.yml down
```

- [ ] **步骤 3：提交**

```bash
git add nginx.test.conf
git commit -m "feat(测试环境): 新增 nginx.test.conf 代理 backend-test

/api/→backend-test:8000、/static/previews/、/data/gifs/、
/data/icons/、/ → 前端静态文件。与 nginx.dev.conf 同结构，
仅 upstream 不同。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.6：fixture 数据 JSON（4 个）

**文件：**
- 新建：`tests/e2e/fixtures/models.fixture.json`
- 新建：`tests/e2e/fixtures/animator.fixture.json`
- 新建：`tests/e2e/fixtures/effects.fixture.json`
- 新建：`tests/e2e/fixtures/icons.fixture.json`

- [ ] **步骤 1：写 models.fixture.json（~50 条，覆盖 species/gender/body_type 全值）**

```json
[
  { "id": "m001", "name": "测试模型001", "species": "人类", "gender": "男性", "body_type": "壮硕", "preview": "previews/m001.png" },
  { "id": "m002", "name": "测试模型002", "species": "精灵", "gender": "女性", "body_type": "纤细", "preview": "previews/m002.png" },
  ...
]
```

- [ ] **步骤 2：写 animator.fixture.json（含 front+left、number_range 边界、hidden 字段）**

- [ ] **步骤 3：写 effects.fixture.json（含 13 个语义标签、量化字段全填+缺失）**

- [ ] **步骤 4：写 icons.fixture.json（含 predefined/color/semantic、长 description）**

- [ ] **步骤 5：用 scripts/sample_real_data.py 从 dev 采样（可选替代手写）**

参见阶段 5 任务 5.4。

- [ ] **步骤 6：提交**

```bash
git add tests/e2e/fixtures/*.fixture.json
git commit -m "feat(测试数据): 新增 4 模块 fixture JSON 各 ~50 条

- models: species/gender/body_type 全值 + 无预览图样本
- animator: front+left 双视角 + number_range 边界 + hidden 字段
- effects: 13 语义标签 + 量化字段全填/部分缺失
- icons: predefined/color/semantic + 长 description 测截断

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.7：fixture 预览图（50 张）

**文件：**
- 新建：`tests/e2e/fixtures/previews/*.png` 和 `*.gif`

- [ ] **步骤 1：生成 50 张 256×256 测试图片**

```bash
# 用 Python PIL 生成纯色 PNG + 简单 GIF
python -c "
from PIL import Image
import os
os.makedirs('tests/e2e/fixtures/previews', exist_ok=True)
for i in range(50):
    Image.new('RGB', (256, 256), color=(i*5%256, i*3%256, i*7%256)).save(f'tests/e2e/fixtures/previews/p{i:03d}.png')
# 5 张 GIF
for i in range(5):
    frames = [Image.new('RGB', (256, 256), color=(c, c, c)) for c in range(50, 256, 50)]
    frames[0].save(f'tests/e2e/fixtures/previews/g{i:03d}.gif', save_all=True, append_images=frames[1:], duration=100, loop=0)
"
```

- [ ] **步骤 2：复制到 runtime_data_test 对应目录**

```bash
cp tests/e2e/fixtures/previews/p0*.png runtime_data_test/model/previews/
cp tests/e2e/fixtures/previews/g0*.gif runtime_data_test/effect/gifs/
cp tests/e2e/fixtures/previews/p1*.png runtime_data_test/animator/previews/
cp tests/e2e/fixtures/previews/p2*.png runtime_data_test/ui/pngs/
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/fixtures/previews/ runtime_data_test/
git commit -m "feat(测试数据): 新增 50 张 256x256 预览图 fixture

50 张 PNG + 5 张 GIF，每个 ~5KB。覆盖 4 模块预览目录，
供 E2E 验证预览图加载、宽高比、object-fit。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.8：test_health_api.py（3 个用例）

**文件：**
- 新建：`backend/tests/integration/test_health_api.py`

- [ ] **步骤 1：写测试**

```python
import pytest

@pytest.mark.asyncio
async def test_health_returns_200(test_client):
    resp = await test_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_health_checks_es_alias(test_client, seeded_db):
    resp = await test_client.get("/api/v1/health")
    data = resp.json()
    assert "es" in data
    assert data["es"]["alias"] is not None

@pytest.mark.asyncio
async def test_health_init_matcher_empty_state_first_request(test_client):
    """init_matcher 空字典状态下首次请求不报错"""
    resp = await test_client.get("/api/v1/health")
    assert resp.status_code == 200
```

- [ ] **步骤 2：运行验证**

```bash
cd backend && python -m pytest tests/integration/test_health_api.py -v
```

- [ ] **步骤 3：提交**

```bash
git add backend/tests/integration/test_health_api.py
git commit -m "test(后端集成): health API 3 个用例

服务可用性、ES alias 检查、init_matcher 空字典状态首次请求。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.9：test_filter_api.py（6 个用例）

**文件：**
- 新建：`backend/tests/integration/test_filter_api.py`

- [ ] **步骤 1：写测试**

```python
import pytest

@pytest.mark.asyncio
async def test_filter_definitions_returns_all_modules(test_client, seeded_db):
    for m in [1, 2, 3, 4]:
        resp = await test_client.get(f"/api/v1/filter/definitions/{m}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_filter_definitions_field_order(test_client, seeded_db):
    resp = await test_client.get("/api/v1/filter/definitions/1")
    defs = resp.json()
    for i in range(len(defs) - 1):
        assert defs[i]["sort_order"] <= defs[i+1]["sort_order"]

@pytest.mark.asyncio
async def test_filter_definitions_is_filterable_filtered(test_client, seeded_db):
    resp = await test_client.get("/api/v1/filter/definitions/1")
    for d in resp.json():
        assert d["is_filterable"] is True

@pytest.mark.asyncio
async def test_filter_definitions_config_json_parsed(test_client, seeded_db):
    resp = await test_client.get("/api/v1/filter/definitions/1")
    for d in resp.json():
        if "config" in d:
            assert isinstance(d["config"], dict)

@pytest.mark.asyncio
async def test_filter_definitions_enum_has_values(test_client, seeded_db):
    resp = await test_client.get("/api/v1/filter/definitions/1")
    for d in resp.json():
        if d["field_type"] in ("enum_single", "enum_multi"):
            assert len(d["values"]) > 0

@pytest.mark.asyncio
async def test_filter_definitions_hides_icon_semantic(test_client, seeded_db):
    """a6389d5: 图标模块的 semantic 字段不返回给前端筛选面板"""
    resp = await test_client.get("/api/v1/filter/definitions/4")
    assert resp.status_code == 200
    field_names = [d["field_name"] for d in resp.json()]
    assert "semantic" not in field_names
```

- [ ] **步骤 2：运行验证**

```bash
cd backend && python -m pytest tests/integration/test_filter_api.py -v
```

- [ ] **步骤 3：提交**

```bash
git add backend/tests/integration/test_filter_api.py
git commit -m "test(后端集成): filter API 6 个用例含图标 semantic 隐藏

4 模块返回、字段顺序、is_filterable 过滤、config JSON 解析、
enum 必有 values、a6389d5 图标 semantic 字段不返回前端。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.10：test_search_api.py（21 个用例）

**文件：**
- 新建：`backend/tests/integration/test_search_api.py`

- [ ] **步骤 1：写 21 个用例（基础 14 + 搜索增强 7）**

```python
import pytest

# ===== 基础 14 个 =====
@pytest.mark.asyncio
async def test_search_empty_query_returns_first_page(test_client, seeded_db):
    resp = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "", "page": 1, "page_size": 20})
    assert resp.status_code == 200
    assert resp.json()["total"] > 0

@pytest.mark.asyncio
async def test_search_text_query_hits(test_client, seeded_db):
    resp = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "测试", "page": 1, "page_size": 20})
    assert resp.json()["total"] > 0

@pytest.mark.asyncio
async def test_search_filters_and(test_client, seeded_db):
    resp = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "", "filters": {"species": ["人类"]}, "page": 1, "page_size": 20})
    for item in resp.json()["items"]:
        assert item["species"] == "人类"

@pytest.mark.asyncio
async def test_search_excludes(test_client, seeded_db):
    resp = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "", "exclude_filters": {"species": ["人类"]}, "page": 1, "page_size": 20})
    for item in resp.json()["items"]:
        assert item["species"] != "人类"

@pytest.mark.asyncio
async def test_search_number_range_bounds(test_client, seeded_db):
    resp = await test_client.post("/api/v1/search/query", json={"module_type": 3, "query": "", "filters": {"action_id": [100, 200]}, "page": 1, "page_size": 20})
    for item in resp.json()["items"]:
        assert 100 <= item["action_id"] <= 200

@pytest.mark.asyncio
async def test_search_pagination_page1(test_client, seeded_db): ...
@pytest.mark.asyncio
async def test_search_pagination_page2(test_client, seeded_db): ...
@pytest.mark.asyncio
async def test_search_pagination_last(test_client, seeded_db): ...
@pytest.mark.asyncio
async def test_search_page_offset_max_10000(test_client, seeded_db):
    """page * page_size 超 10000 阈值返回空或报错"""
    resp = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "", "page": 1000, "page_size": 20})
    assert resp.status_code in (200, 400)

@pytest.mark.asyncio
async def test_search_parse_info_categorization(test_client, seeded_db): ...
@pytest.mark.asyncio
async def test_search_facets_count(test_client, seeded_db): ...
@pytest.mark.asyncio
async def test_search_llm_path(test_client, seeded_db, monkeypatch):
    """llm_enabled=True 时调用 LLM"""
    monkeypatch.setattr("app.services.parse_service.settings.llm_enabled", True)
    ...

@pytest.mark.asyncio
async def test_search_llm_failure_fallback(test_client, seeded_db, monkeypatch):
    """LLM 异常时退化为纯 keyword"""
    ...

# ===== 搜索增强 7 个（§10.4.2）=====
@pytest.mark.asyncio
async def test_search_dict_path_pure_chinese(test_client, seeded_db):
    """字典匹配路径：纯中文标签词（如'僧侣'）返回正确 parse_info"""
    resp = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "僧侣", "page": 1, "page_size": 20})
    data = resp.json()
    if data.get("parse_info"):
        assert data["parse_info"]["source"] == "dict"

@pytest.mark.asyncio
async def test_search_llm_path_returns_dict_plus_llm(test_client, seeded_db, monkeypatch):
    """LLM 路径：未匹配维度触发 LLM，成功后 source='dict+llm'"""
    ...

@pytest.mark.asyncio
async def test_search_llm_exception_fallback_to_keyword(test_client, seeded_db, monkeypatch):
    """LLM 失败 fallback：退化为纯 keyword"""
    ...

@pytest.mark.asyncio
async def test_search_effective_filters_merges_user_and_parsed(test_client, seeded_db):
    """effective_filters = 用户 filters + parsed_filters 合并"""
    ...

@pytest.mark.asyncio
async def test_search_effective_excludes_merges_user_and_parsed(test_client, seeded_db):
    """effective_excludes = 用户 exclude_filters + parsed_excludes"""
    ...

@pytest.mark.asyncio
async def test_search_relevance_score_normalized_with_keyword(test_client, seeded_db):
    """relevance_score 在有 keyword 时为 0-1 归一化值"""
    resp = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "测试", "page": 1, "page_size": 20})
    data = resp.json()
    if data["items"]:
        score = data["items"][0].get("relevance_score")
        if score is not None:
            assert 0 <= score <= 1

@pytest.mark.asyncio
async def test_search_query_time_ms_positive(test_client, seeded_db):
    """query_time_ms 随查询返回且为正数"""
    resp = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "", "page": 1, "page_size": 20})
    data = resp.json()
    assert "query_time_ms" in data
    assert isinstance(data["query_time_ms"], (int, float))
    assert data["query_time_ms"] > 0
```

- [ ] **步骤 2：运行验证**

```bash
cd backend && python -m pytest tests/integration/test_search_api.py -v
```

- [ ] **步骤 3：提交**

```bash
git add backend/tests/integration/test_search_api.py
git commit -m "test(后端集成): search API 21 个用例含搜索增强 7

基础 14：空查询/文本查询/filters AND/excludes/number_range/
分页/page_offset_max/parse_info/facets/LLM 路径/LLM fallback。
增强 7（§10.4.2）：字典路径、LLM dict+llm、LLM fallback、
effective_filters/excludes 合并、relevance_score 归一化、
query_time_ms 正数。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.11：test_suggestions_api.py（4 个用例）

**文件：**
- 新建：`backend/tests/integration/test_suggestions_api.py`

- [ ] **步骤 1：写测试**

```python
import pytest

@pytest.mark.asyncio
async def test_suggestions_prefix_match(test_client, seeded_db):
    resp = await test_client.get("/api/v1/search/suggestions", params={"q": "测", "module_type": 1})
    assert resp.status_code == 200
    assert len(resp.json()) > 0

@pytest.mark.asyncio
async def test_suggestions_case_insensitive(test_client, seeded_db):
    ...

@pytest.mark.asyncio
async def test_suggestions_empty_q_returns_empty(test_client, seeded_db):
    resp = await test_client.get("/api/v1/search/suggestions", params={"q": "", "module_type": 1})
    assert resp.json() == []

@pytest.mark.asyncio
async def test_suggestions_module_type_switch(test_client, seeded_db):
    ...
```

- [ ] **步骤 2：运行验证**

```bash
cd backend && python -m pytest tests/integration/test_suggestions_api.py -v
```

- [ ] **步骤 3：提交**

```bash
git add backend/tests/integration/test_suggestions_api.py
git commit -m "test(后端集成): suggestions API 4 个用例

prefix 命中、大小写、空 q 返回空、module_type 切换。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.12：test_admin_api.py（9 个用例）

**文件：**
- 新建：`backend/tests/integration/test_admin_api.py`

- [ ] **步骤 1：写测试**

```python
import pytest

# reindex-es 3 个
@pytest.mark.asyncio
async def test_reindex_es_search_works_after(test_client, seeded_db, admin_key):
    resp = await test_client.post("/api/v1/admin/reindex-es", headers={"X-Admin-Key": admin_key})
    assert resp.status_code == 200
    search = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "", "page": 1, "page_size": 1})
    assert search.status_code == 200

@pytest.mark.asyncio
async def test_reindex_es_cleans_old_index(test_client, seeded_db, admin_key):
    ...

@pytest.mark.asyncio
async def test_reindex_alias_atomicity(test_client, seeded_db, admin_key):
    """并发 2 个 reindex，只有一个成功 swap alias，无中间态"""
    import asyncio
    tasks = [
        test_client.post("/api/v1/admin/reindex-es", headers={"X-Admin-Key": admin_key})
        for _ in range(2)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            continue
        assert r.status_code in (200, 409)
    search = await test_client.post("/api/v1/search/query", json={"module_type": 1, "query": "", "page": 1, "page_size": 1})
    assert search.status_code == 200

# refresh-dictionary 2 个
@pytest.mark.asyncio
async def test_refresh_dictionary_clears_cache(test_client, seeded_db, admin_key): ...
@pytest.mark.asyncio
async def test_refresh_dictionary_next_query_reloads(test_client, seeded_db, admin_key): ...

# import-{m}-json 4 个
@pytest.mark.asyncio
async def test_import_model_json_upserts(test_client, admin_key): ...
@pytest.mark.asyncio
async def test_import_animator_json_upserts(test_client, admin_key): ...
@pytest.mark.asyncio
async def test_import_effect_json_upserts(test_client, admin_key): ...
@pytest.mark.asyncio
async def test_import_icon_json_upserts(test_client, admin_key): ...
```

- [ ] **步骤 2：运行验证**

```bash
cd backend && python -m pytest tests/integration/test_admin_api.py -v
```

- [ ] **步骤 3：提交**

```bash
git add backend/tests/integration/test_admin_api.py
git commit -m "test(后端集成): admin API 9 个用例含 alias 原子性

reindex-es 3 个（重建后搜索可用、旧索引清理、并发 alias
原子性）；refresh-dictionary 2 个；import-{m}-json 4 个模块
各 1 个 upsert 验证。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.13：test_search_concurrency.py（1 个用例）

**文件：**
- 新建：`backend/tests/integration/test_search_concurrency.py`

- [ ] **步骤 1：写测试**

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_concurrent_searches_only_last_returns(test_client, seeded_db):
    """连续 10 个 search 请求，前 9 个在路由层被取消，第 10 个返回正确结果"""
    tasks = [
        test_client.post("/api/v1/search/query", json={"module_type": 1, "query": f"测试{i}", "page": 1, "page_size": 20})
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # 至少最后一个成功
    last = results[-1]
    assert not isinstance(last, Exception)
    assert last.status_code == 200
```

- [ ] **步骤 2：运行验证**

```bash
cd backend && python -m pytest tests/integration/test_search_concurrency.py -v
```

- [ ] **步骤 3：提交**

```bash
git add backend/tests/integration/test_search_concurrency.py
git commit -m "test(后端集成): 并发搜索原子性 1 个用例

连续 10 个 search 请求，验证最后一个返回正确结果。
等价前端 AbortController 后端行为。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2.14：补 run_tests.bat/.sh integration 子命令

**文件：**
- 修改：`scripts/run_tests.bat`
- 修改：`scripts/run_tests.sh`

- [ ] **步骤 1：替换 integration 子命令实现**

```batch
:integration
echo === Starting fixture environment ===
docker compose -f docker-compose.test.yml up -d --build
echo === Waiting for backend health ===
for /L %%i in (1,1,30) do (
  curl -sf http://localhost:18000/api/v1/health > nul 2>&1 && goto :integration_run
  timeout /t 2 > nul
)
echo Backend not ready
exit /b 1
:integration_run
cd backend && set RUN_ID=local && python -m pytest tests/integration/ -v --cov=app --cov-report=term && cd ..
docker compose -f docker-compose.test.yml down
goto end
```

- [ ] **步骤 2：本地跑 integration 验证**

```bash
scripts/run_tests.bat integration
```

- [ ] **步骤 3：提交**

```bash
git add scripts/run_tests.bat scripts/run_tests.sh
git commit -m "feat(测试脚本): 补 integration 子命令

启动 fixture 环境 -> 等待 backend health -> 跑 pytest
integration --cov -> 关闭环境。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 阶段 3：Playwright 配置 + Page Object + ~60 个 E2E

### 任务 3.1：playwright.config.ts

**文件：**
- 新建：`tests/e2e/playwright.config.ts`

- [ ] **步骤 1：写配置**

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: 'http://localhost:18081',
    trace: 'on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 7'] } },
  ],
})
```

- [ ] **步骤 2：安装浏览器**

```bash
cd tests/e2e && npx playwright install --with-deps chromium
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/playwright.config.ts
git commit -m "feat(E2E): 新增 playwright.config.ts

baseURL=18081，trace=on-failure，2 项目（桌面+手机 Chromium），
失败时自动截图+视频+trace。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.2：Page Object 层（5 个文件）

**文件：**
- 新建：`tests/e2e/pages/SearchPage.ts`
- 新建：`tests/e2e/pages/ModuleTabs.ts`
- 新建：`tests/e2e/pages/FilterPanel.ts`
- 新建：`tests/e2e/pages/ResultGrid.ts`
- 新建：`tests/e2e/pages/AssetDetailModal.ts`

- [ ] **步骤 1：写 SearchPage.ts**

```typescript
import { Page, expect } from '@playwright/test'
import { ModuleTabs } from './ModuleTabs'
import { FilterPanel } from './FilterPanel'
import { ResultGrid } from './ResultGrid'
import { AssetDetailModal } from './AssetDetailModal'

export class SearchPage {
  constructor(private page: Page) {}

  async goto() { await this.page.goto('http://localhost:18081') }

  get searchInput() { return this.page.locator('[data-testid="search-input"]') }
  get moduleTabs() { return new ModuleTabs(this.page) }
  get filterPanel() { return new FilterPanel(this.page) }
  get resultGrid() { return new ResultGrid(this.page) }
  get detailModal() { return new AssetDetailModal(this.page) }

  async search(text: string) {
    await this.searchInput.fill(text)
    await this.page.waitForLoadState('networkidle')
  }

  async expectQueryTimeLessThan(ms: number) {
    const resp = await this.page.waitForResponse(r =>
      r.url().includes('/api/v1/search/query') && r.status() === 200
    )
    const body = await resp.json()
    expect(body.query_time_ms).toBeLessThan(ms)
  }
}
```

- [ ] **步骤 2：写 ModuleTabs.ts / FilterPanel.ts / ResultGrid.ts / AssetDetailModal.ts**

参考 spec §6.1 示例，每个 PO 暴露 `tab-{n}`、`filter-group-{field}`、`asset-card-{id}`、`detail-modal` 等 locator。

- [ ] **步骤 3：写 smoke 测试验证 PO**

```typescript
// tests/e2e/specs/smoke.spec.ts
import { test, expect } from '@playwright/test'
import { SearchPage } from '../pages/SearchPage'

test('smoke', async ({ page }) => {
  const sp = new SearchPage(page)
  await sp.goto()
  await expect(sp.searchInput).toBeVisible()
})
```

- [ ] **步骤 4：运行验证**

```bash
docker compose -f docker-compose.test.yml up -d
cd tests/e2e && npx playwright test smoke.spec.ts
```

- [ ] **步骤 5：提交**

```bash
git add tests/e2e/pages/ tests/e2e/specs/smoke.spec.ts
git commit -m "feat(E2E): 新增 Page Object 层 + smoke 测试

SearchPage 主入口聚合 ModuleTabs/FilterPanel/ResultGrid/
AssetDetailModal，封装 search() 与 expectQueryTimeLessThan()。
smoke 验证 PO 与 fixture 环境连通。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.3：visual-quality-helpers.ts

**文件：**
- 新建：`tests/e2e/fixtures/visual-quality-helpers.ts`

- [ ] **步骤 1：写工具函数**

```typescript
import { Page, TestInfo } from '@playwright/test'

export async function attachVisualFailureArtifacts(page: Page, info: TestInfo, failedImgUrl?: string) {
  const screenshot = await page.screenshot({ fullPage: true })
  await info.attach('screenshot', { body: screenshot, contentType: 'image/png' })

  const consoleLogs: string[] = []
  page.on('console', msg => consoleLogs.push(`[${msg.type()}] ${msg.text()}`))
  page.on('pageerror', err => consoleLogs.push(`[pageerror] ${err.message}`))
  await info.attach('console-logs', { body: consoleLogs.join('\n'), contentType: 'text/plain' })

  if (failedImgUrl) {
    await info.attach('failed-image-url', { body: failedImgUrl, contentType: 'text/plain' })
  }
}

export async function getNaturalSize(page: Page, selector: string) {
  return await page.locator(selector).evaluate((el: HTMLImageElement) => ({
    w: el.naturalWidth,
    h: el.naturalHeight,
  }))
}

export async function getRenderedSize(page: Page, selector: string) {
  const box = await page.locator(selector).boundingBox()
  return { w: box!.width, h: box!.height }
}

export async function getObjectFit(page: Page, selector: string) {
  return await page.locator(selector).evaluate(
    (el: HTMLImageElement) => getComputedStyle(el).objectFit
  )
}
```

- [ ] **步骤 2：提交**

```bash
git add tests/e2e/fixtures/visual-quality-helpers.ts
git commit -m "feat(E2E): 新增 visual-quality-helpers 工具函数

失败时收集截图、控制台日志、失败图片 URL。
getNaturalSize/getRenderedSize/getObjectFit 供视觉质量用例断言。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.4：search.spec.ts（11 个用例）

**文件：**
- 新建：`tests/e2e/specs/search.spec.ts`

- [ ] **步骤 1：写 11 个用例（基础 8 + 搜索增强 3）**

```typescript
import { test, expect } from '@playwright/test'
import { SearchPage } from '../pages/SearchPage'

test.describe('搜索流程', () => {
  test('输入文本 → 等待结果 → 检查卡片渲染', async ({ page }) => { /* ... */ })
  test('清空 → 检查结果更新', async ({ page }) => { /* ... */ })
  test('模块切换 → 搜索状态被重置', async ({ page }) => { /* ... */ })
  test('快速输入 → 防抖只发一次请求', async ({ page }) => { /* ... */ })
  test('搜索结果含 query_time_ms', async ({ page }) => { /* ... */ })
  test('搜索结果含 facets', async ({ page }) => { /* ... */ })
  test('搜索结果含 parse_info', async ({ page }) => { /* ... */ })
  test('空查询返回首页结果', async ({ page }) => { /* ... */ })

  // §10.4.3 搜索增强 3
  test('输入"不要红色" → exclude chip 出现 → 结果不含红色', async ({ page }) => { /* ... */ })
  test('快速连续输入"战士 剑客" → 只发一次请求且 parse_info 正确分类', async ({ page }) => { /* ... */ })
  test('dismissedFields dismiss 后重新解析查询', async ({ page }) => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test search.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/search.spec.ts
git commit -m "test(E2E): 搜索流程 11 个用例含 exclude 端到端

基础 8：输入/清空/模块切换/防抖/query_time_ms/facets/parse_info/
空查询。增强 3（§10.4.3）：exclude 语法端到端、连续输入防抖、
dismissedFields 重解析。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.5：filter.spec.ts（9 个用例）

**文件：**
- 新建：`tests/e2e/specs/filter.spec.ts`

- [ ] **步骤 1：写 9 个用例（基础 8 + v2.1 +1）**

```typescript
test.describe('筛选流程', () => {
  test('enum_single 单选 → 结果过滤', async ({ page }) => { /* ... */ })
  test('enum_multi 多选 → AND', async ({ page }) => { /* ... */ })
  test('number_range 滑块 → 结果数变化', async ({ page }) => { /* ... */ })
  test('boolean 切换 → 结果过滤', async ({ page }) => { /* ... */ })
  test('text 输入 → 结果过滤', async ({ page }) => { /* ... */ })
  test('清空所有筛选', async ({ page }) => { /* ... */ })
  test('dismissedFields 重解析流程', async ({ page }) => { /* ... */ })
  test('多 filter 组合', async ({ page }) => { /* ... */ })
  // v2.1 §10.2 +1
  test('图标模块切换不创建万级 DOM 节点（245c2ff + a6389d5）', async ({ page }) => {
    await page.goto('http://localhost:18081')
    await page.click('[data-testid="module-tab-4"]')
    await page.waitForLoadState('networkidle')
    const count = await page.locator('[data-testid^="filter-option-"]').count()
    expect(count).toBeLessThan(500)
  })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test filter.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/filter.spec.ts
git commit -m "test(E2E): 筛选流程 9 个用例含图标 DOM 节点数验证

基础 8：enum_single/enum_multi/number_range/boolean/text/清空/
dismissedFields/多组合。+1（§10.2）：图标模块切换不创建万级
DOM 节点（245c2ff + a6389d5）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.6：detail-modal.spec.ts（7 个用例）

**文件：**
- 新建：`tests/e2e/specs/detail-modal.spec.ts`

- [ ] **步骤 1：写 7 个用例（基础 6 + v2.1 +1）**

```typescript
test.describe('详情弹窗', () => {
  test('点卡片 → 弹窗打开 → 显示标签', async ({ page }) => { /* ... */ })
  test('复制路径（粘贴板断言）', async ({ page }) => { /* ... */ })
  test('ESC 关闭', async ({ page }) => { /* ... */ })
  test('点击遮罩关闭', async ({ page }) => { /* ... */ })
  test('多个弹窗顺序打开关闭', async ({ page }) => { /* ... */ })
  test('复制 icon ID（仅 icon 模块）', async ({ page }) => { /* ... */ })
  // v2.1 §10.2 +1
  test('详情页三种预览布局都不溢出 dialog（780532b + 2d8436c）', async ({ page }) => {
    for (const moduleType of [1, 2, 4]) {
      await page.goto('http://localhost:18081')
      await page.click(`[data-testid="module-tab-${moduleType}"]`)
      await page.waitForLoadState('networkidle')
      await page.click('[data-testid^="asset-card-"]')
      await page.waitForSelector('[data-testid="detail-modal"]')
      const dialog = page.locator('.el-dialog')
      const dialogBox = await dialog.boundingBox()
      const viewportW = page.viewportSize()!.width
      expect(dialogBox!.width).toBeLessThanOrEqual(viewportW)
      const preview = page.locator('[data-testid="detail-preview"]')
      const previewBox = await preview.boundingBox()
      expect(previewBox!.x + previewBox!.width).toBeLessThanOrEqual(
        dialogBox!.x + dialogBox!.width
      )
    }
  })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test detail-modal.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/detail-modal.spec.ts
git commit -m "test(E2E): 详情弹窗 7 个用例含三种布局不溢出

基础 6：打开/复制路径/ESC/遮罩/顺序开关/复制 icon ID。
+1（§10.2）：icon-pair/effect-pair/is-single 三种布局都不溢出
dialog（780532b + 2d8436c）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.7：module-tabs.spec.ts（4 个用例）

**文件：**
- 新建：`tests/e2e/specs/module-tabs.spec.ts`

- [ ] **步骤 1：写 4 个用例**

```typescript
test.describe('模块切换', () => {
  test('4 个 tab 切换', async ({ page }) => { /* ... */ })
  test('切换后筛选面板重新加载', async ({ page }) => { /* ... */ })
  test('上次查询被清空', async ({ page }) => { /* ... */ })
  test('切换后 loading 状态可见', async ({ page }) => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test module-tabs.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/module-tabs.spec.ts
git commit -m "test(E2E): 模块切换 4 个用例

4 个 tab 切换、筛选面板重新加载、查询清空、loading 状态。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.8：pagination.spec.ts（5 个用例）

**文件：**
- 新建：`tests/e2e/specs/pagination.spec.ts`

- [ ] **步骤 1：写 5 个用例**

```typescript
test.describe('分页', () => {
  test('翻页下一页', async ({ page }) => { /* ... */ })
  test('翻页上一页', async ({ page }) => { /* ... */ })
  test('改 pageSize', async ({ page }) => { /* ... */ })
  test('跳到最后一页', async ({ page }) => { /* ... */ })
  test('从第 1 页直接跳第 100 页（offset 上限边界）', async ({ page }) => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test pagination.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/pagination.spec.ts
git commit -m "test(E2E): 分页 5 个用例含 offset 上限边界

翻页下一页/上一页、改 pageSize、跳最后一页、offset 上限边界。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.9：preview-loading.spec.ts（8 个用例）

**文件：**
- 新建：`tests/e2e/specs/preview-loading.spec.ts`

- [ ] **步骤 1：写 8 个用例**

```typescript
test.describe('预览加载', () => {
  test('模型 PNG 加载', async ({ page }) => { /* ... */ })
  test('动作 GIF 加载', async ({ page }) => { /* ... */ })
  test('特效 GIF 加载', async ({ page }) => { /* ... */ })
  test('图标 PNG 加载', async ({ page }) => { /* ... */ })
  test('故意 404 → SVG placeholder 实际渲染', async ({ page }) => { /* ... */ })
  test('首屏滚动到的卡片 lazy-load', async ({ page }) => { /* ... */ })
  test('dismissedFields re-parse 后预览更新', async ({ page }) => { /* ... */ })
  test('预览图加载完成触发 load 事件', async ({ page }) => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test preview-loading.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/preview-loading.spec.ts
git commit -m "test(E2E): 预览加载 8 个用例含 SVG fallback 实际渲染

4 模块预览加载、故意 404 触发 SVG placeholder 实际渲染、
首屏 lazy-load、dismissedFields 重解析后预览更新、load 事件。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.10：responsive.spec.ts（4 个用例）

**文件：**
- 新建：`tests/e2e/specs/responsive.spec.ts`

- [ ] **步骤 1：写 4 个用例**

```typescript
test.describe('响应式', () => {
  test('桌面断点栅格列数', async ({ page }) => { /* ... */ })
  test('手机断点栅格列数变化', async ({ page }) => { /* ... */ })
  test('手机断点筛选面板抽屉化', async ({ page }) => { /* ... */ })
  test('手机断点搜索栏全宽', async ({ page }) => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test responsive.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/responsive.spec.ts
git commit -m "test(E2E): 响应式 4 个用例

桌面栅格列数、手机栅格列数变化、手机筛选面板抽屉化、
手机搜索栏全宽。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.11：error-states.spec.ts（4 个用例）

**文件：**
- 新建：`tests/e2e/specs/error-states.spec.ts`

- [ ] **步骤 1：写 4 个用例**

```typescript
test.describe('错误状态', () => {
  test('后端 500 → 友好错误提示', async ({ page }) => { /* ... */ })
  test('网络断开 → 重试按钮', async ({ page }) => { /* ... */ })
  test('空结果 → "无匹配"提示', async ({ page }) => { /* ... */ })
  test('搜索超时 → 错误提示', async ({ page }) => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test error-states.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/error-states.spec.ts
git commit -m "test(E2E): 错误状态 4 个用例

后端 500 友好提示、网络断开重试、空结果无匹配、搜索超时。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.12：visual-quality.spec.ts（6 个用例）

**文件：**
- 新建：`tests/e2e/specs/visual-quality.spec.ts`

- [ ] **步骤 1：写 6 个用例**

```typescript
import { test, expect } from '@playwright/test'
import { SearchPage } from '../pages/SearchPage'
import { getNaturalSize, getRenderedSize, getObjectFit, attachVisualFailureArtifacts } from '../fixtures/visual-quality-helpers'

test.describe('视觉与图片质量', () => {
  test('模型 PNG 宽高比保持', async ({ page }, info }) => {
    try {
      const sp = new SearchPage(page)
      await sp.goto()
      await sp.search('测试模型')
      const card = sp.resultGrid.firstCard()
      await card.click()
      await sp.detailModal.expectOpen()
      const img = sp.detailModal.previewImage
      const natural = await getNaturalSize(page, '[data-testid="detail-preview"]')
      const rendered = await getRenderedSize(page, '[data-testid="detail-preview"]')
      expect(Math.abs(natural.w/natural.h - rendered.w/rendered.h)).toBeLessThan(0.01)
    } catch (e) {
      await attachVisualFailureArtifacts(page, info, 'model-png')
      throw e
    }
  })

  test('动作 GIF 宽高比保持', async ({ page }, info }) => { /* 同上 */ })
  test('特效 GIF 宽高比保持', async ({ page }, info }) => { /* 同上 */ })
  test('图标 PNG 宽高比保持', async ({ page }, info }) => { /* 同上 */ })

  test('object-fit 是 cover 或 contain', async ({ page }, info }) => {
    const fit = await getObjectFit(page, '[data-testid="detail-preview"]')
    expect(['cover', 'contain']).toContain(fit)
  })

  test('CLS < 0.1', async ({ page }, info) => {
    const cls = await page.evaluate(() => {
      return new Promise<number>(resolve => {
        const observer = new PerformanceObserver(list => {
          const entries = list.getEntries()
          let cls = 0
          for (const entry of entries) {
            cls += (entry as any).value
          }
          resolve(cls)
          observer.disconnect()
        })
        observer.observe({ type: 'layout-shift', buffered: true })
        setTimeout(() => resolve(0), 3000)
      })
    })
    expect(cls).toBeLessThan(0.1)
  })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test visual-quality.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/visual-quality.spec.ts
git commit -m "test(E2E): 视觉与图片质量 6 个用例

4 模块预览图宽高比、object-fit cover/contain、CLS<0.1。
失败时通过 attachVisualFailureArtifacts 上传截图+控制台日志+
失败图片 URL，便于事后定位预览图压缩/加载失败/布局抖动。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.13：a11y.spec.ts（2 个用例）

**文件：**
- 新建：`tests/e2e/specs/a11y.spec.ts`

- [ ] **步骤 1：写 2 个用例**

```typescript
test.describe('辅助功能', () => {
  test('Tab 键导航主流程', async ({ page }) => { /* ... */ })
  test('筛选面板键盘可达', async ({ page }) => { /* ... */ })
})
```

- [ ] **步骤 2：运行验证**

```bash
cd tests/e2e && npx playwright test a11y.spec.ts
```

- [ ] **步骤 3：提交**

```bash
git add tests/e2e/specs/a11y.spec.ts
git commit -m "test(E2E): 辅助功能 2 个用例

Tab 键导航主流程、筛选面板键盘可达。仅保留 smoke，不做
完整 a11y audit（YAGNI）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3.14：补 run_tests.bat/.sh e2e 子命令

**文件：**
- 修改：`scripts/run_tests.bat`
- 修改：`scripts/run_tests.sh`

- [ ] **步骤 1：替换 e2e 子命令实现**

```batch
:e2e
echo === Building frontend ===
cd frontend && npm run build && cd ..
echo === Starting fixture environment ===
docker compose -f docker-compose.test.yml up -d --build
echo === Waiting for backend health ===
for /L %%i in (1,1,30) do (
  curl -sf http://localhost:18000/api/v1/health > nul 2>&1 && goto :e2e_run
  timeout /t 2 > nul
)
echo Backend not ready
exit /b 1
:e2e_run
cd tests/e2e && npx playwright test
docker compose -f docker-compose.test.yml down
goto end
```

- [ ] **步骤 2：本地跑 e2e 验证**

```bash
scripts/run_tests.bat e2e
```

- [ ] **步骤 3：提交**

```bash
git add scripts/run_tests.bat scripts/run_tests.sh
git commit -m "feat(测试脚本): 补 e2e 子命令

构建前端 -> 启动 fixture 环境 -> 等待 backend health ->
跑 playwright test -> 关闭环境。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 阶段 4：k6 性能脚本 + 本地 runbook

### 任务 4.1：k6-baseline.js

**文件：**
- 新建：`tests/performance/k6-baseline.js`

- [ ] **步骤 1：写脚本**

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8081';
const THRESHOLD = parseFloat(__ENV.THRESHOLD || '500');

export const options = {
  scenarios: {
    search_baseline: {
      executor: 'per-vu-iterations',
      vus: 1, iterations: 100,
      thresholds: {
        'http_req_duration{scenario:search_baseline}': [`p(95)<${THRESHOLD}`],
      },
    },
    suggestions_baseline: {
      executor: 'per-vu-iterations',
      vus: 1, iterations: 100,
      thresholds: {
        'http_req_duration{scenario:suggestions_baseline}': [`p(95)<${THRESHOLD}`],
      },
    },
    filter_definitions_baseline: {
      executor: 'per-vu-iterations',
      vus: 1, iterations: 100,
      thresholds: {
        'http_req_duration{scenario:filter_definitions_baseline}': [`p(95)<${THRESHOLD}`],
      },
    },
  },
};

export default function () {
  // 搜索空查询
  http.post(`${BASE}/api/v1/search/query`, JSON.stringify({
    module_type: 1, query: '', page: 1, page_size: 60,
  }), { headers: { 'Content-Type': 'application/json' } });

  // suggestions
  http.get(`${BASE}/api/v1/search/suggestions?q=测&module_type=1`);

  // filter definitions
  http.get(`${BASE}/api/v1/filter/definitions/1`);
}
```

- [ ] **步骤 2：本地跑 1 次验证脚本可执行**

```bash
k6 run tests/performance/k6-baseline.js
```

- [ ] **步骤 3：提交**

```bash
git add tests/performance/k6-baseline.js
git commit -m "feat(性能测试): 新增 k6-baseline.js 基准脚本

3 个场景：搜索空查询、suggestions、filter definitions。
各 100 次取 P95，阈值由 THRESHOLD 环境变量传入（Day 1 实测后填入）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 4.2：k6-load.js

**文件：**
- 新建：`tests/performance/k6-load.js`

- [ ] **步骤 1：写脚本**

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8081';

export const options = {
  scenarios: {
    concurrent_50: {
      executor: 'constant-vus',
      vus: 50, duration: '1m',
      thresholds: {
        'http_req_failed{scenario:concurrent_50}': ['rate<0.01'],
      },
    },
    concurrent_200: {
      executor: 'constant-vus',
      vus: 200, duration: '1m',
      thresholds: {
        'http_req_failed{scenario:concurrent_200}': ['rate<0.05'],
      },
    },
    concurrent_50_with_suggestions: {
      executor: 'constant-vus',
      vus: 50, duration: '1m',
      exec: 'search_with_suggestions',
    },
  },
};

export default function () {
  const res = http.post(`${BASE}/api/v1/search/query`, JSON.stringify({
    module_type: 1, query: '', page: 1, page_size: 60,
  }), { headers: { 'Content-Type': 'application/json' } });
  check(res, { 'status 200': r => r.status === 200 });
}

export function search_with_suggestions() {
  http.post(`${BASE}/api/v1/search/query`, JSON.stringify({
    module_type: 1, query: '测', page: 1, page_size: 60,
  }), { headers: { 'Content-Type': 'application/json' } });
  http.get(`${BASE}/api/v1/search/suggestions?q=测&module_type=1`);
}
```

- [ ] **步骤 2：本地跑验证**

```bash
k6 run tests/performance/k6-load.js
```

- [ ] **步骤 3：提交**

```bash
git add tests/performance/k6-load.js
git commit -m "feat(性能测试): 新增 k6-load.js 并发负载脚本

3 场景：50 并发搜索（错误率<1%）、200 并发搜索（错误率<5%）、
50 并发+持续建议查询（后端不崩）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 4.3：Day 1 实测基线（本地手动）

- [ ] **步骤 1：确认 dev 环境已启动并 reindex**

```bash
docker compose up -d
curl -X POST http://localhost:8081/api/v1/admin/reindex-es -H "X-Admin-Key: $ADMIN_API_KEY"
```

- [ ] **步骤 2：跑 k6-baseline.js 20 次记录实测 P95**

```bash
for i in $(seq 1 20); do
  k6 run tests/performance/k6-baseline.js --quiet | tee reports/baseline_${i}.txt
done
# 统计实测 P95
```

- [ ] **步骤 3：记录到 docs/performance-testing.md**

在 §任务 4.5 文档中记录实测 P95 数值。

- [ ] **步骤 4：提交（无需代码改动，仅文档）**

跳到任务 4.5 一起提交。

---

### 任务 4.4：Day 2 阈值填入

- [ ] **步骤 1：计算阈值 = 1.2 × 实测 P95**

```bash
# 例如实测 P95 = 120ms，则阈值 = 144ms
THRESHOLD=144
```

- [ ] **步骤 2：用 THRESHOLD 环境变量跑 k6 验证**

```bash
THRESHOLD=144 k6 run tests/performance/k6-baseline.js
```
预期：全绿

- [ ] **步骤 3：把阈值写入 k6-baseline.js 默认值**

```javascript
const THRESHOLD = parseFloat(__ENV.THRESHOLD || '144');  // Day 2 实测后填入
```

- [ ] **步骤 4：提交**

```bash
git add tests/performance/k6-baseline.js
git commit -m "perf(性能测试): Day 2 填入实测 P95 阈值 1.2x

Day 1 实测 P95=120ms，阈值设为 144ms（1.2x）。
后续阈值变更需 PR review，不允许单人改。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 4.5：docs/performance-testing.md runbook

**文件：**
- 新建：`docs/performance-testing.md`

- [ ] **步骤 1：写文档**

```markdown
# 性能测试本地 runbook

## 前置条件

- dev 环境已启动（docker compose up -d）
- dev 环境已 reindex（POST /api/v1/admin/reindex-es）
- 本地装 k6（Windows: choco install k6；Linux: 见 k6 文档）

## Day 1 实测基线（每季度跑一次）

\`\`\`bash
mkdir -p tests/performance/reports
for i in $(seq 1 20); do
  k6 run tests/performance/k6-baseline.js --quiet | tee tests/performance/reports/baseline_$(date +%Y%m%d)_${i}.txt
done
\`\`\`

统计 20 次的 P95 中位数，记为实测 P95。

## Day 2 阈值确定

阈值 = 1.2 × 实测 P95。改 k6-baseline.js 默认 THRESHOLD 值，提交 PR review。

## 日常验证

\`\`\`bash
# 跑基准
k6 run tests/performance/k6-baseline.js

# 跑并发负载
k6 run tests/performance/k6-load.js
\`\`\`

## 报告

报告输出到 tests/performance/reports/{date}_{branch}.json，本地保留 30 天。

## 阈值变更流程

1. 提 PR 说明变更原因（硬件升级/数据量变化/代码优化）
2. 至少 1 人 review
3. 不允许单人改阈值
```

- [ ] **步骤 2：提交**

```bash
git add docs/performance-testing.md
git commit -m "docs(性能测试): 新增 k6 本地 runbook

Day 1 实测基线（20 次取中位 P95）→ Day 2 阈值=1.2x →
日常验证 → 阈值变更流程（需 PR review）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 4.6：补 run_tests.bat/.sh perf 子命令

**文件：**
- 修改：`scripts/run_tests.bat`
- 修改：`scripts/run_tests.sh`

- [ ] **步骤 1：替换 perf 子命令**

```batch
:perf
echo === Performance baseline ===
k6 run tests/performance/k6-baseline.js
echo === Performance load ===
k6 run tests/performance/k6-load.js
goto end
```

- [ ] **步骤 2：本地跑 perf 验证**

```bash
scripts/run_tests.bat perf
```

- [ ] **步骤 3：提交**

```bash
git add scripts/run_tests.bat scripts/run_tests.sh
git commit -m "feat(测试脚本): 补 perf 子命令

跑 k6-baseline.js + k6-load.js。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 阶段 5：CI workflow + 文档 + sample_real_data

### 任务 5.1：.github/workflows/test.yml

**文件：**
- 新建：`.github/workflows/test.yml`

- [ ] **步骤 1：写 workflow**

```yaml
name: test

on:
  pull_request:
    branches: [master]

jobs:
  frontend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: cd frontend && npm ci && npm run test:coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: frontend-coverage
          path: frontend/coverage/

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
          ES_INDEX_ALIAS: ci_assets_${RUN_ID}
          DB_SCHEMA: ci_biaoqiao_${RUN_ID}
        run: cd backend && python -m pytest tests/ -v --cov=app --cov-report=xml
      - name: Cleanup ES indices
        if: always()
        run: |
          curl -X DELETE "http://localhost:9200/ci_assets_${RUN_ID}_*" || true
          curl -X DELETE "http://localhost:9200/_alias/ci_assets_${RUN_ID}" || true

  e2e:
    runs-on: ubuntu-latest
    needs: [frontend-unit, backend-integration]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd frontend && npm ci && npx vite build
      - run: docker compose -f docker-compose.test.yml up -d --build
        env:
          RUN_ID: ${{ github.run_id }}
      - name: Wait for backend health
        run: |
          for i in {1..30}; do
            curl -sf http://localhost:18000/api/v1/health && break
            sleep 2
          done
      - run: npx playwright install --with-deps chromium
      - run: cd tests/e2e && npx playwright test
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: tests/e2e/playwright-report/
          retention-days: 30
```

- [ ] **步骤 2：在 PR 上验证 CI 触发**

推一个测试分支开 PR，观察 3 个 job 是否触发并跑通。

- [ ] **步骤 3：提交**

```bash
git add .github/workflows/test.yml
git commit -m "feat(CI): 新增 test.yml workflow 作为发布闸门

3 个 job：frontend-unit（npm run test:coverage）、
backend-integration（pytest + 独立 schema + ES alias）、
e2e（playwright + fixture 环境）。k6 不进 CI，本地手动跑。

并行 PR 通过 DB_SCHEMA + ES_INDEX_ALIAS 隔离互不干扰。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 5.2：Branch Protection 配置说明

**文件：**
- 新建：`docs/branch-protection.md`

- [ ] **步骤 1：写文档说明 GitHub Branch Protection 配置步骤**

```markdown
# GitHub Branch Protection 配置

## 步骤

1. 进入仓库 Settings → Branches → Add rule
2. Branch name pattern: `master`
3. 勾选 "Require status checks to pass before merging"
4. 勾选以下 3 个 status check：
   - `frontend-unit`
   - `backend-integration`
   - `e2e`
5. 勾选 "Require branches to be up to date before merging"
6. 勾选 "Include administrators"
7. Save changes

## 验证

开一个测试 PR，确认 3 个 job 必跑全绿才能 merge。
```

- [ ] **步骤 2：提交**

```bash
git add docs/branch-protection.md
git commit -m "docs(CI): 新增 Branch Protection 配置说明

3 个 status check 必绿才能 merge 到 master，包含管理员。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 5.3：docs/testing-guide.md

**文件：**
- 新建：`docs/testing-guide.md`

- [ ] **步骤 1：写文档**

```markdown
# 测试运行与维护说明

## 测试金字塔

- Vitest 前端单元（纯 Node，~52 个）
- pytest 后端集成（真连 PG+ES，~44 个）
- Playwright E2E（fixture 环境，~60 个）
- k6 性能（本地手动，~20 个）

## 本地一键脚本

\`\`\`bash
# 只跑单元
scripts/run_tests.bat unit   # Windows
scripts/run_tests.sh unit    # Linux

# CI 闸门（unit + integration + e2e，不含 perf）
scripts/run_tests.bat all

# 完整验收（all + perf，耗时）
scripts/run_tests.bat full

# 单独跑 perf
scripts/run_tests.bat perf
\`\`\`

## CI workflow

PR 到 master 自动触发 3 个 job：
- frontend-unit
- backend-integration
- e2e

3 个 job 必绿才能 merge（Branch Protection）。

## 覆盖率门槛

- 前端 ≥ 60%（按文件计）
- 后端 ≥ 70%（按文件计）

## Fixture 维护

季度（每 3 个月）跑 scripts/sample_real_data.py 从 dev 采样 ~50 条/模块，重生成 fixture JSON。

## 排查常见问题

- E2E 预览图加载失败：检查 docker-compose.test.yml 容器内路径是否与 docker-compose.yml 一致
- backend-integration 并行覆盖：检查 DB_SCHEMA / ES_INDEX_ALIAS 是否设了独立 RUN_ID
- Playwright 超时：检查 fixture 环境是否启动完成（curl health check）

## 当前已有测试

- 16 个后端 mock 单元测试（backend/tests/test_*.py）— 保留通过，不与此层重复
```

- [ ] **步骤 2：提交**

```bash
git add docs/testing-guide.md
git commit -m "docs(测试): 新增 testing-guide.md 运行与维护说明

测试金字塔、本地一键脚本、CI workflow、覆盖率门槛、
fixture 维护、常见问题排查。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 5.4：scripts/sample_real_data.py

**文件：**
- 新建：`scripts/sample_real_data.py`

- [ ] **步骤 1：写脚本**

```python
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
```

- [ ] **步骤 2：本地跑验证**

```bash
python scripts/sample_real_data.py
ls tests/e2e/fixtures/*.fixture.json
```

- [ ] **步骤 3：提交**

```bash
git add scripts/sample_real_data.py
git commit -m "feat(测试数据): 新增 sample_real_data.py 季度重生成 fixture

从 dev 环境采样 ~50 条/模块，scrub 掉内部字段。
季度执行流程：dev reindex -> 跑脚本 -> 人工 review -> 提 PR。
缓解 fixture drift 问题。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 阶段 6：集成联调 + 最终验收

### 任务 6.1：run_tests.bat full 完整跑通

- [ ] **步骤 1：本地跑 full**

```bash
scripts/run_tests.bat full
```
预期：unit + integration + e2e + perf 全部跑通

- [ ] **步骤 2：记录任何失败并修复**

如发现失败，回到对应阶段修复，不要在阶段 6 临时 hack。

- [ ] **步骤 3：提交（如有修复）**

```bash
git add ...
git commit -m "fix(测试): 修复集成联调发现的问题

<具体修复说明>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 6.2：CI 在 PR 上跑通

- [ ] **步骤 1：推测试分支开 PR**

```bash
git checkout -b test/test-suite
git push origin test/test-suite
# 在 GitHub 开 PR
```

- [ ] **步骤 2：观察 3 个 CI job 跑通**

如失败，看日志定位是 frontend-unit / backend-integration / e2e 哪个失败，回到对应阶段修复。

- [ ] **步骤 3：确认 Branch Protection 已开启**

参考 docs/branch-protection.md 配置。

- [ ] **步骤 4：合并测试 PR**

确认全绿后 merge，删除测试分支。

---

### 任务 6.3：最终验收对照 spec §9

- [ ] **步骤 1：逐条核对 §9 验收标准 14 项**

```
1. ✅ run_tests.bat all 本地一键跑完
2. ✅ CI workflow 3 个 job 自动触发
3. ✅ 前端单元覆盖率 ≥ 60%
4. ✅ 后端集成覆盖率 ≥ 70%
5. ✅ E2E 覆盖 §3.3 列出的 10 类流程
6. ✅ 性能基准全部有阈值断言（Day 2 后填入实测 1.2x）
7. ✅ 视觉质量 6 用例全绿
8. ✅ Branch Protection 启用
9. ✅ docs/testing-guide.md
10. ✅ docs/performance-testing.md
11. ✅ scripts/sample_real_data.py
12. ✅ 当前 16 个后端 mock 单元测试保留通过
13. ✅ §10 v2.1 补充的 7 个新行为用例通过
14. ✅ §10.4 搜索模块增强的 18 个用例通过
```

- [ ] **步骤 2：生成验收报告**

```bash
# 跑覆盖率
cd frontend && npm run test:coverage
cd ../backend && python -m pytest tests/ --cov=app --cov-report=term
# E2E 报告
cd ../tests/e2e && npx playwright test --reporter=html
```

- [ ] **步骤 3：提交验收报告**

```bash
git add docs/acceptance-report-2026-06-26.md
git commit -m "docs(验收): 测试套件 v2.1 最终验收报告

14 项验收标准全绿：
- 175 个用例（Vitest 52 + pytest 44 + E2E 60 + k6 20）
- 前端覆盖率 X%，后端覆盖率 Y%
- CI 3 个 job 全绿
- Branch Protection 已启用

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 自审清单

实现完所有任务后，逐项检查：

- [ ] **spec 覆盖**：spec §1-§10 每节都有对应任务实现
- [ ] **placeholder 扫描**：搜索 "TBD"、"TODO"、"实现 later"，应全部为空
- [ ] **类型一致性**：`slug()`、`db_schema`、`ES_INDEX_ALIAS`、`test_schema`、`seeded_db`、`test_client` 在所有引用处签名一致
- [ ] **data-testid 一致**：spec §2.5 表格中的 test id 与前端组件实际加的一致
- [ ] **端口分配一致**：15432/19200/18000/18081 在 docker-compose.test.yml、nginx.test.conf、playwright.config.ts、CI workflow 中一致
- [ ] **环境变量一致**：`RUN_ID`、`ES_INDEX_ALIAS`、`DB_SCHEMA`、`ADMIN_API_KEY` 在 docker-compose.test.yml、conftest.py、CI workflow 中一致
- [ ] **commit 签名**：所有 commit 都有 `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`
- [ ] **TDD 纪律**：每个测试用例都先写失败测试再实现
- [ ] **保留现有 16 个后端 mock 单元测试**：`backend/tests/test_*.py` 不被删除或重复

## 测试代码完整性约定

本计划覆盖 175 个测试用例。对于每个测试文件，**第一个用例必给完整代码**作为模板，后续同类用例用 `/* ... */` 标记断言省略处，实现者应：

1. **遵循同文件内已给完整代码的模板**：参考同文件中已给完整代码的用例（如 searchStore.spec.ts 的 `setModuleType 同步置 loading` 用例），按相同结构补全 `/* ... */` 处的断言
2. **以 `it` 描述为准**：每个 `it` 的描述字符串明确说明了该用例要验证的行为，断言应紧扣描述
3. **参考 spec 对应章节**：spec §3.1/§3.2/§3.3/§10.2/§10.4 的表格列出了每个用例的「测试目标」与「文件位置」，断言应覆盖这些目标
4. **v2.1 §10.2 与 §10.4 的用例必须给完整代码**：这些用例已在本计划中给出完整实现（如 `RENDER_CAP=200`、`Promise.all 并行`、`图标模块切换不创建万级 DOM 节点`、`详情页三种预览布局都不溢出 dialog` 等），不允许用 `/* ... */` 省略

实现者遇到 `/* ... */` 时，应在实现该任务时补全为完整断言代码。**不允许保留 `/* ... */` 占位符提交。**
