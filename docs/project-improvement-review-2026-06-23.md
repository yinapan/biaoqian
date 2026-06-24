# 工程改进审视报告（2026-06-23）

## 背景

本报告基于当前 `master` 分支工作区的一次工程级审视，覆盖前端构建、后端测试、搜索链路、数据导入、部署配置和仓库体积。审视过程使用 Superpowers 的代码审查、中文代码审查、系统化调试和完成前验证流程。

本次审视只做问题识别和改进建议，未修改业务代码。

## 当前状态

- 后端测试未全部通过：`python -m pytest backend\tests`，结果为 `1 failed, 69 passed`。
- 前端构建未通过：`npm.cmd run build` 在 `vue-tsc -b` 阶段失败。
- 前端依赖审计通过：`npm.cmd audit --audit-level=moderate`，结果为 `0 vulnerabilities`。
- Git 工作区存在未提交改动，涉及后端搜索、字典匹配、前端搜索交互和 Vite 配置等文件。
- 本地 Git loose objects 体积约 `6.73 GiB`，仓库历史或本地对象库存在明显瘦身空间。

## 主要问题与改进项

### P0：修复前端构建失败

**位置：**

- `frontend/src/components/SearchBar.vue:81`

**现象：**

执行：

```powershell
cd frontend
npm.cmd run build
```

报错：

```text
src/components/SearchBar.vue(81,35): error TS2339:
Property 'setTimeout' does not exist on type 'CreateComponentPublicInstanceWithMixins...'
```

**原因：**

模板表达式中直接调用 `setTimeout`，Vue 类型检查会把它当作组件实例属性解析，而不是全局函数。

**影响：**

前端无法生成 `frontend/dist`，部署链路被阻塞。

**建议措施：**

1. 将 blur 逻辑提取到 `<script setup>` 中，例如 `onBlur()`。
2. 模板里改为 `@blur="onBlur"`。
3. 或显式使用 `window.setTimeout(...)`。
4. 顺手删除当前未使用的 `hasExcludes` 计算属性，避免后续开启严格未使用检查时报错。

**验收标准：**

- `npm.cmd run build` 成功退出。
- `frontend/dist/index.html` 存在。

### P0：修复后端特效导入测试失败

**位置：**

- `backend/app/importers/effects_importer.py:31`
- `backend/tests/test_effects_importer.py:138`

**现象：**

执行：

```powershell
python -m pytest backend\tests
```

结果：

```text
FAILED backend/tests/test_effects_importer.py::TestBuildEffectTags::test_semantic_tags_mapped
KeyError: 'scope_size'
```

**原因：**

测试样例的 `result.tags` 中包含中文键 `范围大小`，但 `TAG_KEY_MAP` 没有将它映射到英文字段 `scope_size`。

**影响：**

特效资源导入后会丢失“范围大小”标签，影响筛选、展示和搜索召回。

**建议措施：**

1. 在 `TAG_KEY_MAP` 中补充：

```python
"范围大小": "scope_size",
```

2. 确认 `sql/002_init_tags.sql` 或初始化逻辑中也包含 `scope_size` 的 `tag_definitions`。
3. 补充导入回归测试，确保中文标签键和英文字段名持续一致。

**验收标准：**

- `python -m pytest backend\tests` 全部通过。
- 导入特效 JSON 后，`assets.tags.scope_size` 有正确值。

### P0：修正关键词与筛选组合搜索语义

**位置：**

- `backend/app/services/es_query_builder.py:97`

**现象：**

当请求同时包含关键词和筛选条件时，关键词被放入 `should`，并设置：

```python
"minimum_should_match": 0
```

**影响：**

只要筛选条件命中，关键词就不再限制结果，只影响排序。用户搜索“红色 剑客”再手动筛选阵营时，可能返回该阵营下所有资产，而不是同时满足关键词的资产。

**建议措施：**

1. 如果业务预期是“筛选 AND 关键词”，应将关键词放入 `must`。
2. 如果业务预期是“筛选命中即可，关键词只做加分”，需要在产品和测试中明确这一点。
3. 为 `filters + keyword` 增加单元测试，防止查询语义再次漂移。

**验收标准：**

- 同时传入 `filters` 和 `keyword` 时，ES 查询结构符合产品预期。
- 单元测试覆盖以下场景：
  - 仅关键词。
  - 仅筛选。
  - 关键词 + 筛选。
  - 关键词 + 筛选 + 排除条件。

### P1：拆清 `exclude_filters` 与“忽略解析标签”的语义

**位置：**

- `backend/app/models/schemas.py:22`
- `backend/app/services/search_service.py:68`
- `backend/app/services/search_service.py:80`
- `frontend/src/stores/searchStore.ts:31`

**现象：**

当前前端将用户点击“移除此标签”的字段写入：

```typescript
exclude_filters[field] = true
```

后端又用 `req.exclude_filters` 判断自然语言解析出的标签是否被用户忽略。但后端构建 ES 查询时使用的是 `effective_excludes`，没有合并用户传入的 `exclude_filters`。

**影响：**

`exclude_filters` 同时承担了两种含义：

- 忽略自然语言解析出来的某个标签。
- 真正排除某类结果，即 ES `must_not`。

这会让接口契约不清晰，也容易引入“以为排除了，实际没排除”的问题。

**建议措施：**

1. 将接口拆成两个字段：
   - `dismissed_fields: list[str]`：只用于忽略自然语言解析标签。
   - `exclude_filters: dict[str, Any]`：只用于真实结果排除。
2. 对 `exclude_filters` 加白名单校验，校验范围应包含 `filters`、`conditions` 和 `exclude_filters`。
3. 前端点击“移除此标签”时传 `dismissed_fields`，不要伪造 `exclude_filters[field] = true`。
4. 为未知 `exclude_filters` 字段补充 422 测试。

**验收标准：**

- “移除此标签”只影响自然语言解析标签，不会错误构造 ES `must_not`。
- 真实排除语法（如“不要红色”）能进入 ES `must_not`。
- 未知排除字段返回 422。

### P1：关闭公网 Elasticsearch 代理

**位置：**

- `nginx.conf:82`
- `docker-compose.yml:38`

**现象：**

Nginx 暴露了：

```nginx
location /elasticsearch/ {
    proxy_pass http://elasticsearch:9200/;
}
```

同时 Elasticsearch 配置为：

```yaml
xpack.security.enabled=false
```

**影响：**

如果域名或内网入口可访问，外部用户可能直接访问 Elasticsearch API，存在数据读取、索引删除和服务破坏风险。

**建议措施：**

1. 删除公网 `/elasticsearch/` 代理。
2. Elasticsearch 只保留 Docker 内网访问。
3. 如确实需要排障入口，使用临时端口转发、VPN、Basic Auth 或 IP 白名单。
4. 生产环境不要暴露无认证 ES。

**验收标准：**

- 外部无法访问 `/elasticsearch/`。
- 后端仍可通过 `ES_URL=http://elasticsearch:9200` 正常访问 ES。

### P1：限制管理上传接口的文件大小与内存占用

**位置：**

- `backend/app/routers/admin.py:63`
- `backend/app/routers/admin.py:83`
- `backend/app/routers/admin.py:105`
- `nginx.conf:16`

**现象：**

管理上传接口使用：

```python
tmp.write(await file.read())
```

Nginx 允许：

```nginx
client_max_body_size 2G;
```

**影响：**

大文件上传会一次性进入后端 worker 内存，可能造成内存暴涨，影响其他请求，甚至触发容器重启。

**建议措施：**

1. 分块读取上传文件并写入临时文件。
2. 在业务层设置大小上限，例如：
   - Excel：按当前数据规模设定明确上限。
   - JSON：按特效或图标数据规模设定明确上限。
3. 超过上限返回 413。
4. 上传失败时确保临时文件被清理。

**验收标准：**

- 上传超限文件返回明确错误。
- 大文件上传不会一次性占用同等大小内存。

### P1：处理多 worker 下缓存刷新不一致

**位置：**

- `docker-compose.yml:58`
- `backend/app/services/cache.py`
- `backend/app/services/parse_service.py`

**现象：**

后端使用 4 个 Uvicorn worker，每个 worker 都有独立的进程内 `TTLCache` 和 `DictionaryMatcher`。

**影响：**

管理接口刷新词典或清理缓存时，只影响处理该请求的 worker。其他 worker 可能继续使用旧标签定义或旧同义词，导致同一查询在不同请求中结果不一致。

**建议措施：**

短期：

1. 数据导入或刷新词典后重启 backend。
2. 或临时将 worker 数降为 1，换取一致性。

中期：

1. 使用 Redis 做共享缓存。
2. 引入词典版本号，每次请求发现版本变化时自动 reload。
3. 或增加跨进程广播刷新机制。

**验收标准：**

- 管理端刷新词典后，所有 worker 在可预期时间内看到同一版本。
- 连续请求不会出现解析结果不一致。

### P2：优化 Elasticsearch 重建索引流程

**位置：**

- `backend/app/services/es_sync_service.py:80`
- `backend/app/services/es_sync_service.py:98`

**现象：**

当前重建索引使用 `LIMIT/OFFSET` 分页：

```sql
SELECT * FROM assets ORDER BY id LIMIT $1 OFFSET $2
```

切换 alias 时使用：

```python
{"remove": {"index": "*", "alias": settings.es_index_alias}}
```

**影响：**

- 数据量增大后，`OFFSET` 越往后越慢。
- `index: "*"` 移除 alias 的范围过大，容易误伤同名 alias 的其他索引。
- bulk 写入没有充分处理单条失败。

**建议措施：**

1. 改为 keyset 分页：`WHERE id > $last_id ORDER BY id LIMIT $batch_size`。
2. 查询当前 alias 指向的索引，只从这些索引移除 alias。
3. 检查每批 bulk 的 `errors` 字段并记录失败项。
4. 重建失败时保留旧 alias，不切换到不完整索引。

**验收标准：**

- 万级、十万级数据重建索引耗时稳定。
- bulk 失败可观测。
- 新索引完整后才切换 alias。

### P2：收紧生产环境默认密钥与配置

**位置：**

- `backend/app/config.py:8`
- `backend/app/main.py:19`
- `docker-compose.yml:8`
- `docker-compose.yml:68`
- `scripts/import_data.py`
- `scripts/extract_thumbnails.py`

**现象：**

工程中仍存在默认管理密钥和默认数据库密码兜底。

**影响：**

如果共享环境或生产环境忘记配置 `.env`，管理接口可能使用公开默认值。

**建议措施：**

1. 增加 `APP_ENV` 或 `ENVIRONMENT` 配置。
2. 非本地开发环境下，默认 `ADMIN_API_KEY` 直接启动失败。
3. 脚本读取不到 `ADMIN_API_KEY` 时直接报错，不再 fallback 到默认值。
4. 数据库密码从 `.env` 注入，避免写死在 compose 文件里。

**验收标准：**

- 生产或共享环境缺少密钥时，服务启动失败并输出明确错误。
- 导入脚本缺少密钥时失败退出，不会静默使用默认值。

### P2：清理仓库体积与数据资产管理方式

**现象：**

执行：

```powershell
git count-objects -vH
```

显示：

```text
count: 7049
size: 6.73 GiB
```

同时工作区存在大文件，例如 `资源标签对照表.xlsx` 超过 1 GB，大量 GIF 资源超过 50 MB。

**影响：**

仓库 clone、备份、CI 和本地 Git 操作都会变慢。即使 `.gitignore` 已忽略当前大文件，历史对象和 loose objects 仍可能占用大量空间。

**建议措施：**

1. 确认哪些大对象已经进入 Git 历史。
2. 对本地 dangling 对象进行安全清理前，先确认没有未保存工作。
3. 后续数据文件迁移到对象存储、制品库、共享盘或 Git LFS。
4. 在 README 中明确数据文件获取和放置方式。

**验收标准：**

- 新 clone 仓库不包含大体量数据资产。
- `git count-objects -vH` 体积回到合理范围。
- 数据导入流程仍可通过外部数据源复现。

### P3：清理测试与依赖升级警告

**位置：**

- `backend/app/config.py:21`
- pytest 配置缺失

**现象：**

后端测试输出包含：

- Pydantic V2 `class Config` 弃用警告。
- `pytest-asyncio` 默认事件循环作用域未显式配置警告。

**建议措施：**

1. 将 `Settings.Config` 迁移到 Pydantic V2 推荐的 `model_config`。
2. 增加 pytest 配置，显式设置 `asyncio_default_fixture_loop_scope`。

**验收标准：**

- `python -m pytest backend\tests` 输出不再包含上述警告。

## 建议执行顺序

1. 修复 `SearchBar.vue` 构建失败，恢复前端部署链路。
2. 修复 `effects_importer.py` 的 `scope_size` 标签映射，恢复后端测试。
3. 明确并修正 `filters + keyword` 的 ES 查询语义。
4. 拆清 `dismissed_fields` 和 `exclude_filters`，补齐字段校验和测试。
5. 关闭公网 `/elasticsearch/` 代理，收紧生产默认密钥。
6. 优化管理上传接口，避免大文件内存风险。
7. 处理 4 worker 缓存一致性问题。
8. 优化重建索引流程。
9. 清理仓库大对象和数据资产管理方式。
10. 清理测试警告，提升依赖升级余量。

## 回归验证清单

```powershell
# 后端
python -m pytest backend\tests

# 前端
cd frontend
npm.cmd run build
npm.cmd audit --audit-level=moderate
```

部署验证：

```powershell
docker compose up -d --build
curl http://localhost/api/v1/health
```

搜索验证：

- 普通关键词搜索有结果。
- 手动筛选和关键词组合时，结果符合产品预期。
- “不要红色”等自然语言排除语法进入 `must_not`。
- “移除此标签”只忽略解析标签，不误伤真实排除逻辑。
- 未知 `filters`、`conditions`、`exclude_filters` 字段返回 422。

安全验证：

- 外部访问 `/elasticsearch/` 不可用。
- 未配置生产管理密钥时，服务无法以默认密钥启动。

