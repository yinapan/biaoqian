# 测试套件设计审阅意见

审阅对象：`docs/superpowers/specs/2026-06-26-test-suite-design.md`

审阅日期：2026-06-26

## 总体结论

这份测试套件设计方向是对的：分层覆盖前端单元、后端集成、E2E 和性能基准，并把预览图、搜索、筛选、模块切换这些历史高风险点纳入验收。

但当前版本还有几处会直接影响落地的问题，尤其是测试 compose、CI 依赖、并行隔离和本地脚本语义。建议先修订这些点，再进入实现。

## 主要问题

### 1. 测试 compose 与现有部署结构不一致

位置：`2026-06-26-test-suite-design.md` 第 272 行附近

文档中的 `backend-test` 使用：

```yaml
build: ./backend
```

但当前真实 compose 是从仓库根目录引用 `./backend`，并且 backend/nginx 依赖多组 runtime 挂载，例如：

```text
./runtime_data:/runtime_data
./runtime_data/model/previews:/data/previews/model
./runtime_data/animator/previews:/data/previews/animator
./runtime_data/effect/gifs:/data/gifs
./runtime_data/ui/pngs:/data/icons
```

如果测试 compose 不同步这些路径，E2E 的预览图、GIF、图标路径很可能无法加载。

建议：

- 以现有 `docker-compose.yml` 的 backend/nginx 路径结构为模板。
- 单独使用 `runtime_data_test`，但保持容器内路径和正式/dev 一致。
- 明确测试 nginx 配置如何代理 `/api`、`/static`、`/data`。

### 2. CI 前端单元测试缺少依赖和配置

位置：`2026-06-26-test-suite-design.md` 第 355 行附近

CI 中直接执行：

```bash
cd frontend && npm ci && npx vitest run --coverage
```

但当前 `frontend/package.json` 还没有：

- `vitest`
- `@vue/test-utils`
- coverage provider
- `vitest.config.ts`
- npm scripts

按文档直接落地会导致 CI 失败。

建议：

- 第 1 阶段明确交付 `frontend/vitest.config.ts`。
- 在 `frontend/package.json` 增加 `test:unit`、`test:coverage`。
- 在 devDependencies 中补齐 Vitest 相关依赖。
- CI 使用 npm script，而不是裸 `npx vitest run --coverage`。

### 3. 并行 CI 隔离方案没有落到应用配置

位置：`2026-06-26-test-suite-design.md` 第 397 行附近

文档要求每个 CI run 使用独立 PostgreSQL schema 和 ES index 前缀，但 CI 示例只执行：

```bash
psql -h localhost -U biaoqiao -d biaoqiao_test -f sql/001_init_schema.sql
psql -h localhost -U biaoqiao -d biaoqiao_test -f sql/002_init_tags.sql
```

同时设置：

```yaml
ES_INDEX_PREFIX: ci_${RUN_ID}
```

目前文档没有说明：

- 独立 schema 如何创建。
- `search_path` 如何传给应用。
- 测试结束如何 drop schema。
- 后端是否已经支持 `ES_INDEX_PREFIX`。
- ES alias/index 名称如何拼接和清理。

这会导致“并行 CI 隔离”停留在设计描述上，实际仍可能互相污染。

建议：

- 在 `conftest.py` 设计中明确 schema lifecycle。
- 增加 `DB_SCHEMA` 或等价配置，并说明后端如何读取。
- 确认或新增 `ES_INDEX_PREFIX` 支持。
- teardown 阶段同时清理 schema 和 ES index。

### 4. E2E health check 依赖未确认的 nginx 代理

位置：`2026-06-26-test-suite-design.md` 第 423 行附近

E2E workflow 等待：

```bash
curl -sf http://localhost:18081/api/v1/health
```

但测试 compose 示例只写了挂载 `nginx.dev.conf`，没有确认该配置会代理 `/api` 到 `backend-test:8000`。

如果 nginx 配置不匹配，这个 health check 会 404 或连不到 backend。

建议：

- 新增 `nginx.test.conf`。
- 明确 `/api`、`/static`、`/data` 的代理和静态目录。
- E2E health check 也可以直接打 `http://localhost:18000/api/v1/health`，避免 nginx 配置问题掩盖 backend 状态。

### 5. `run_tests.bat all` 与性能测试定位冲突

位置：`2026-06-26-test-suite-design.md` 第 477 行附近

文档前面说 k6 性能测试是本地手动 runbook，不进 CI 强制门禁；但本地脚本中：

```bat
call %0 unit && call %0 integration && call %0 e2e && call %0 perf
```

这会让 `run_tests.bat all` 默认包含 k6，实际变成强制性能测试。

建议：

- `all` 只跑 unit、integration、e2e。
- `perf` 保留手动执行。
- 如需完整验收，可新增 `full`，明确会包含耗时性能测试。

### 6. `data-testid` 使用 idx 不稳定

位置：`2026-06-26-test-suite-design.md` 第 127 行附近

文档建议：

```text
asset-card-{idx}
asset-preview-{idx}
```

这类按列表索引生成的 test id 不稳定。搜索、筛选、排序、分页变化后，idx 会变，E2E 容易误点或误判。

建议：

- 使用后端资产 id：`asset-card-{asset.id}`。
- 或使用稳定资源名 hash。
- 如果只是取首个卡片，Page Object 中封装 `firstCard()`，不要把 idx 写进全局 test id 规范。

## 次要建议

### data-testid 命名需要考虑特殊字符

筛选项 value 里可能包含中文、斜杠、空格、括号等字符。如果直接生成：

```text
filter-option-{field}-{value}
```

选择器会变复杂，也容易不合法。

建议对 value 做 slug/hash：

```text
filter-option-{field}-{hash(value)}
```

### 文档应区分“计划新增”和“当前已有”

文档中多处写“现有 14 个后端 mock 单元测试”，但当前仓库已有的后端测试文件已经超过这个数量。建议把“当前已有”和“计划新增”分开写，避免后续验收时混淆。

### E2E 截图对比已砍掉，但视觉质量用例仍需定义失败产物

虽然不做截图回归是合理的，但宽高比、object-fit、CLS、LCP 失败时仍建议上传：

- Playwright trace
- 当前页面截图
- 控制台日志
- 失败图片 URL

这样能更快定位预览图压缩、加载失败、布局抖动问题。

## 建议修订顺序

1. 先修订 `docker-compose.test.yml` 设计，保证测试环境路径和正式/dev 一致。
2. 补齐 Vitest 依赖、配置和 scripts 的交付说明。
3. 明确 PostgreSQL schema 和 ES index 前缀隔离的代码实现点。
4. 调整 `run_tests.bat all` 语义，不默认跑 k6。
5. 把 `data-testid` 规范从 idx 改成稳定 id/hash。
6. 更新验收标准，区分 CI 必跑和本地手动性能验收。

