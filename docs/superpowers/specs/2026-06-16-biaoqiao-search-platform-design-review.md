# 美术标签搜索平台 - 新版方案评审建议

## 评审结论

新版方案已经吸收了多项关键改进：去掉 Redis、改用进程内 `TTLCache`，ES mapping 改为按 `tag_definitions` 显式生成，增加 alias 重建索引，补充 `/admin` 鉴权说明，并增加 `/admin/check-sync` 做 PG/ES 一致性检查。

当前方案可以作为开工基础，但建议在实现前继续补齐 5 个落地风险：

- LLM 外发数据边界。
- 多 worker 下 `TTLCache` 的刷新一致性。
- ES 同步失败后的自动重试闭环。
- 备份与恢复策略。
- 可压测验收的 P95 性能指标。

---

## 必须补充项

### 1. 明确 LLM 外发数据安全边界

方案允许 LLM 解析请求走外网，但还没有定义哪些数据允许发送、哪些数据禁止发送。美术资源路径、内部文件名、项目命名和标签体系都可能属于公司内部信息。

建议增加“LLM 数据安全”章节：

- 默认只发送剩余未匹配文本和必要候选标签。
- 不发送资源路径、完整文件名、完整标签库、用户身份、导入原始表格内容。
- Prompt 日志和响应日志做脱敏处理。
- LLM 失败、超时或关闭时，自动降级为普通关键词搜索。
- 提供配置开关：

```env
LLM_PARSE_ENABLED=false
LLM_TIMEOUT_SECONDS=3
```

推荐把 LLM 定位为增强能力，而不是主搜索链路的必需依赖。

### 2. 说明 `TTLCache` 在多 worker 下的一致性策略

方案中使用 `uvicorn --workers 4`，这意味着每个 worker 进程都有独立的 `TTLCache`。管理端修改标签配置或同义词后，如果只清理当前进程缓存，其他 worker 不会立即感知。

建议采用“版本号轮询 + 定时刷新”的轻量方案：

- 在 `tag_definitions`、`tag_values`、`tag_synonyms` 中维护 `updated_at`。
- 应用内存记录当前已加载的 `dictionary_version`。
- 每个 worker 每 30～60 秒查询一次最大 `updated_at`。
- 如果版本变更，则重新加载词典、标签配置和 LLM prompt schema。
- `/admin/refresh-dictionary` 仅触发当前 worker 立即刷新，同时其他 worker 通过版本号轮询在短时间内刷新。

可在文档中明确一致性承诺：

> 标签配置变更后，当前请求所在 worker 立即生效，其他 worker 最多 60 秒内生效。

如果后续需要强一致，再引入 Redis pub/sub 或统一后台配置服务。

### 3. 补 ES 同步失败自动重试

当前方案把 ES bulk index 失败写入 `import_errors`，可以追踪问题，但还不能形成自动恢复闭环。建议增加一张轻量同步事件表：

```sql
CREATE TABLE asset_index_events (
    id              BIGSERIAL PRIMARY KEY,
    asset_id        BIGINT NOT NULL,
    event_type      VARCHAR(20) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    retry_count     INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_asset_index_events_status
    ON asset_index_events (status, updated_at);
```

建议规则：

- PG 写入成功后创建 `asset_index_events`。
- ES index/delete 成功后标记为 `done`。
- ES 失败后标记为 `failed`，记录错误和重试次数。
- 后台任务定时重试 `pending` 和可重试的 `failed`。
- `/admin/check-sync` 用于发现最终不一致，`/admin/reindex-es` 作为兜底修复。

这样可以避免每次小规模同步失败都依赖全量重建。

### 4. 补备份与恢复策略

方案已经说明 ES 可重建，但缺少 PG 和预览文件的备份策略。建议增加：

- PostgreSQL 每日备份，至少保留 7 天。
- `previews/` 目录定期备份，和 PG 备份保持相近时间点。
- ES 不作为主备份对象，可从 PG 全量重建。
- 每次 Excel 导入记录 `batch_id`，导入结果可追踪。
- 必要时支持按 `batch_id` 回查或回滚本次导入。

建议补充一张导入批次表：

```sql
CREATE TABLE import_batches (
    batch_id        VARCHAR(64) PRIMARY KEY,
    source_file     VARCHAR(500),
    status          VARCHAR(20) NOT NULL,
    success_count   INTEGER DEFAULT 0,
    skipped_count   INTEGER DEFAULT 0,
    failed_count    INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);
```

这样导入历史、错误分析和恢复操作都会更清楚。

### 5. 将性能预估改为 P95 验收指标

当前方案中仍有 `< 20 ms`、`< 10 ms` 一类理想性能描述。建议改为更适合验收的 P95 指标：

| 场景 | 建议验收指标 | 说明 |
|------|--------------|------|
| 纯筛选查询 | P95 < 100 ms | ES filter，不含静态资源加载 |
| 关键词搜索 | P95 < 200 ms | 包含 IK 分词和 highlight |
| 筛选 + 聚合计数 | P95 < 300 ms | facets 较多时允许更高 |
| 词典解析 | P95 < 10 ms | 进程内词典匹配 |
| LLM 首次解析 | P95 < 3 s | 超时降级 |
| 缓存命中解析 | P95 < 20 ms | TTLCache 命中 |
| Excel 导入 | 10 万条在 10 分钟内完成 | 视图片提取数量调整 |

建议明确使用 k6 或 Locust 做压测，固定 10 万条测试数据作为验收基准。

---

## 建议调整项

### 1. 收紧导入接口权限

当前 API 树中 `/admin/*` 标注了 `X-Admin-Key` 鉴权，但 `/assets/batch-import` 也具备批量导入能力。建议二选一：

- 将 `/assets/batch-import` 移入 `/admin/import-excel`，统一管理入口。
- 或明确 `/assets/batch-import` 同样需要 `X-Admin-Key`。

推荐统一放到 `/admin` 下，避免权限边界混乱。

### 2. 明确 ES 安全部署边界

Docker Compose 中已经没有暴露 ES 的 `9200` 端口，这是正确的。但仍建议在部署章节补一句：

> ES 关闭内置安全能力的前提是仅允许 Docker 内部网络访问，禁止将 `9200` 暴露到宿主机或办公网。

如果未来需要跨机器部署 ES，再重新开启认证和 TLS。

### 3. 完善前端异常状态

建议在前端设计中补充以下状态：

- 空结果：展示当前筛选条件，支持一键清空关键词、放宽筛选、重置全部。
- 解析冲突：手动筛选覆盖 NLP 解析标签时，在 `ParsedTags` 中明确展示。
- LLM 降级：展示普通关键词搜索结果，不阻断用户。
- 预览缺失：统一占位图，避免卡片高度跳动。
- 导入中：管理端显示导入进度、成功数、失败数、未知标签数。

### 4. 增加实施里程碑

建议把开发拆成 4 个阶段：

| 阶段 | 目标 | 交付物 |
|------|------|--------|
| P0 | 数据闭环 | PG schema、Excel 导入、导入错误记录 |
| P1 | 搜索闭环 | ES 索引、筛选查询、关键词搜索、分页 |
| P2 | 前端闭环 | 动态筛选面板、结果卡片、预览展示 |
| P3 | 体验增强 | 词典解析、搜索建议、管理端重建索引 |

LLM 解析建议放在 P3 之后，作为增强项接入。

---

## 推荐修改顺序

1. 先补 LLM 外发边界和关闭开关，降低合规风险。
2. 再补 `TTLCache` 多 worker 刷新策略，避免标签配置变更不一致。
3. 然后补 ES 同步事件表和重试流程，让 PG/ES 同步形成闭环。
4. 接着补 PG 与预览文件备份策略。
5. 最后把性能描述改成 P95 验收指标，并增加压测说明。

完成这些修改后，方案会更接近可实施版本：主链路简单，失败可恢复，安全边界清楚，性能也能被验收。
