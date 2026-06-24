# 工程改进审视报告（2026-06-18）

## 背景

本报告基于当前 `master` 分支的一次工程级审视，覆盖前端构建、后端接口、部署配置、数据导入脚本和基础测试。目标是把当前可见风险拆成可执行的改进项，便于后续按优先级推进。

## 当前状态

- 后端测试已通过：`python -m pytest backend\tests`，结果为 `66 passed`。
- 后端测试存在 2 类警告：Pydantic V2 配置弃用警告、`pytest-asyncio` 默认事件循环作用域警告。
- 前端构建未通过：`npm.cmd run build` 在 `vue-tsc -b` 阶段失败。
- 代码中文内容本身为 UTF-8，PowerShell 默认输出乱码属于终端编码显示问题。

## 改进项

### P0：修复前端构建失败

**现象：**

在 `frontend` 目录执行：

```powershell
npm.cmd run build
```

报错：

```text
vite.config.ts(3,36): error TS2307: Cannot find module 'node:url' or its corresponding type declarations.
vite.config.ts(9,55): error TS2339: Property 'url' does not exist on type 'ImportMeta'.
```

**影响：**

前端无法生成 `frontend/dist`，会阻断部署流程。`README.md` 和 `deploy.sh` 都依赖前端构建产物。

**建议：**

1. 在 `frontend` 目录重新安装依赖：

```powershell
npm.cmd install
```

2. 如果仍失败，在 `frontend/tsconfig.node.json` 的 `compilerOptions` 中补充：

```json
{
  "types": ["node"]
}
```

3. 重新执行：

```powershell
npm.cmd run build
```

**验收标准：**

- `npm.cmd run build` 成功退出。
- `frontend/dist/index.html` 存在。

### P0：禁止共享环境使用默认管理密钥

**现状：**

以下位置存在默认管理密钥兜底：

- `backend/app/config.py`
- `docker-compose.yml`
- `scripts/import_data.py`
- `scripts/extract_thumbnails.py`

默认值为：

```text
dev-admin-key-change-in-prod
```

**影响：**

如果内网共享或生产部署时忘记配置 `.env`，管理接口会使用公开默认值，存在误操作和安全风险。

**建议：**

- 后端启动时检查 `ADMIN_API_KEY`。
- 当值为空、缺失或等于默认值时，在非本地开发模式下直接启动失败。
- 导入脚本不要静默 fallback 到默认密钥，改为明确报错并提示配置 `.env`。

**验收标准：**

- 未配置 `ADMIN_API_KEY` 时，部署脚本或后端给出明确错误。
- 配置随机密钥后，管理接口可正常访问。

### P1：启动阶段不要吞掉初始化异常

**现状：**

`backend/app/main.py` 的 lifespan 中，对数据库、Elasticsearch、索引别名、词典初始化异常处理过于宽松。部分异常被直接 `pass`。

**影响：**

索引创建失败、词典加载失败时，服务可能看似启动成功，但搜索质量或接口行为异常，排障成本较高。

**建议：**

- 引入 `logging`。
- 对可降级异常使用 `logger.exception(...)` 记录堆栈。
- 对不可降级异常明确中止启动，避免服务进入半可用状态。

**验收标准：**

- ES 初始化失败时日志可定位原因。
- 词典加载失败时有清晰告警。
- `/api/v1/health` 能反映关键依赖不可用状态。

### P1：搜索过滤字段增加白名单校验

**现状：**

`SearchRequest.filters` 接受任意字段，`build_search_query` 虽然接收了 `filterable_fields`，但没有用它拦截未知字段。

**影响：**

调用方可以传入未定义字段，导致无效查询、类型不匹配或额外 ES 查询压力。问题表现可能是“无结果”，也可能是 ES 查询错误。

**建议：**

- 在搜索服务层根据 `tag_definitions` 过滤或拒绝未知字段。
- 推荐对未知字段返回 `422`，并给出字段名。
- 对 `conditions.field` 也做同样校验。

**验收标准：**

- 传入未知 filter 字段时返回明确错误。
- 传入未知 condition 字段时返回明确错误。
- 现有合法筛选不受影响。

### P1：限制管理上传接口的文件大小和内存占用

**现状：**

`/api/v1/admin/import-excel` 和 `/api/v1/admin/import-effects-json` 使用 `await file.read()` 一次性读取上传文件。Nginx 当前允许最大上传 `2G`。

**影响：**

大文件上传可能导致后端 worker 内存暴涨，影响其他请求。

**建议：**

- 设置业务层上传大小上限。
- 使用分块读取写入临时文件。
- 对 Excel 和 JSON 分别设定合理上限。

**验收标准：**

- 超过上限的文件返回明确错误。
- 大文件上传不会一次性占用同等大小内存。

### P2：整理弃用警告

**现状：**

后端测试通过，但存在警告：

- Pydantic class-based `Config` 将在 V3 移除。
- `pytest-asyncio` 未显式配置 `asyncio_default_fixture_loop_scope`。

**建议：**

- 将 `Settings.Config` 迁移为 Pydantic V2 推荐的 `model_config`。
- 在 pytest 配置中显式设置事件循环作用域。

**验收标准：**

- `python -m pytest backend\tests` 通过。
- 测试输出不再出现上述弃用警告。

## 建议执行顺序

1. 修复前端构建失败，恢复部署链路。
2. 收紧 `ADMIN_API_KEY` 默认值策略，降低共享环境风险。
3. 补日志和启动失败策略，提升可观测性。
4. 增加搜索字段白名单校验，减少错误查询。
5. 优化上传接口，避免大文件内存风险。
6. 清理测试警告，保持依赖升级空间。

## 回归验证清单

```powershell
python -m pytest backend\tests
cd frontend
npm.cmd install
npm.cmd run build
```

部署验证：

```powershell
docker compose up -d --build
curl http://localhost/api/v1/health
```

搜索验证：

- 访问首页能正常加载。
- 切换模型、特效、动作模块无报错。
- 普通关键词搜索有响应。
- 手动筛选和自然语言解析可以同时工作。
- 传入未知筛选字段时返回明确错误。
