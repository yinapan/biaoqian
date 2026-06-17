# 美术标签搜索平台 - 项目审视改进建议

## 审视结论

本次审视覆盖后端、前端、导入脚本、Docker Compose、Nginx、SQL 初始化和仓库状态。

整体判断：

- 后端核心测试覆盖较好，当前 `pytest` 全部通过。
- Docker Compose 配置可正常解析。
- 前端构建当前失败，会阻断部署。
- 特效导入和特效预览存在路径不一致问题，会影响特效模块可用性。
- 仓库中有较多生成产物和大型素材处于未跟踪状态，需要尽快收口。

---

## 必须修复项

### 1. 前端当前无法构建

验证命令：

```powershell
cd frontend
npm run build
```

当前失败信息：

```text
tsconfig.app.json(4,5): error TS5023: Unknown compiler option 'useDefineForExpose'.
vite.config.ts(3,36): error TS2307: Cannot find module 'node:url' or its corresponding type declarations.
vite.config.ts(9,55): error TS2339: Property 'url' does not exist on type 'ImportMeta'.
```

涉及文件：

- `frontend/tsconfig.app.json`
- `frontend/vite.config.ts`
- `frontend/package.json`

建议：

- 删除 `tsconfig.app.json` 中的 `useDefineForExpose`。
- 在前端开发依赖中增加 `@types/node`。
- 在 `tsconfig.node.json` 中配置 Node 类型，例如 `"types": ["node"]`。
- 修复后重新运行 `npm run build`。

### 2. 特效导入脚本引用了错误文件名

当前实际存在的文件是：

```text
特效/merged/effect_gif_results.json
```

但 `import.bat` 检查的是：

```bat
if exist "特效\merged\effects_data.json" (
    python scripts/import_data.py --effects-json "特效\merged\effects_data.json"
)
```

影响：

- 执行 `import.bat` 时会跳过特效数据导入。
- 用户看到“数据导入完成”，但特效模块没有实际入库。

建议：

- 将 `effects_data.json` 改为 `effect_gif_results.json`。
- 或让 `import.bat` 同时兼容两个文件名，并优先使用实际存在的文件。

### 3. 特效 GIF 悬停预览路径会 404

后端导入逻辑中，GIF 文件按原始 GIF 文件名复制：

```python
gif_filename = Path(gif_rel_path).name
dst_gif = effects_dir / gif_filename
```

缩略图路径类似：

```text
effects/001_D_____01_d5e77d48_angle45.png
```

但前端悬停时用 `item.name` 拼 GIF 路径：

```ts
const baseName = props.item.name
return `/static/previews/effects/${baseName}.gif`
```

问题：

- `item.name` 来自资源路径，例如 `d_毒雾01`。
- GIF 文件名来自渲染产物，例如 `001_D_____01_d5e77d48_angle45.gif`。
- 两者不一致，悬停动图大概率 404。

建议：

- 后端在 `tags` 中保留 `gif_path`，或在响应中增加 `preview_gif_path`。
- 前端悬停时使用后端返回的实际 GIF 路径。
- 或导入时把 GIF 复制为和 `item.name` 一致的文件名，但要处理重名冲突。

推荐方案：后端返回 `preview_gif_path`，避免前端猜路径。

### 4. 数值范围筛选逻辑不匹配

前端 `FilterGroup.vue` 对 `number_range` 使用 slider，写入的是数组：

```ts
store.setFilter(field.value, val)
```

其中 `val` 是：

```ts
[min, max]
```

但后端 `es_query_builder.py` 中，list 会被当成 `terms` 查询：

```python
if isinstance(value, list):
    bool_filter.append({"terms": {f"tags.{field}": value}})
```

影响：

- 特效时长、长度、宽度、高度这类数值筛选不会按范围查询。
- 用户调整 slider 后，ES 查询语义错误。

建议：

- 前端对 `number_range` 写入结构化对象：

```ts
{
  op: "between",
  gte: min,
  lte: max
}
```

- 或后端根据 `tag_definitions.field_type` 判断字段类型，遇到数值字段数组时生成 range 查询。

推荐方案：后端基于字段类型构建查询，避免前端协议过度脆弱。

---

## 建议修改项

### 1. ES 重建需要检查 bulk 写入结果

当前 `reindex_with_alias` 中执行 bulk 后没有检查 `errors`，随后直接切换 alias。

风险：

- 如果 ES bulk 部分写入失败，新索引数据不完整。
- alias 仍会被切到新索引，线上搜索结果会缺数据。

建议：

- 每批 bulk 后检查 `resp.get("errors")`。
- 发现失败时收集失败 item，并中止 alias 切换。
- 保留旧 alias，返回失败详情。
- 可选：写入 `import_errors` 或独立 `asset_index_events` 表。

### 2. 启动异常不应静默吞掉

当前 `main.py` 中初始化 PG、ES alias 和词典时存在宽泛异常捕获：

```python
except Exception:
    pass
```

风险：

- 服务表面启动成功，但搜索、词典或 ES 后续才失败。
- 排查时缺少日志。

建议：

- 至少使用 `logger.exception(...)` 记录异常。
- 对关键初始化失败，应让 `/api/v1/health` 明确返回错误。
- 如果 PG 不可用，建议启动失败或进入降级状态，而不是静默继续。

### 3. 默认管理密钥需要防误用

当前多个位置仍保留默认密钥：

```text
dev-admin-key-change-in-prod
```

涉及：

- `backend/app/config.py`
- `docker-compose.yml`
- `scripts/import_data.py`

建议：

- 启动时检测到默认密钥则打印强警告。
- 内网共享或生产部署时强制要求 `.env` 中配置随机 `ADMIN_API_KEY`。
- 文档中提供生成命令：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. 仓库卫生需要收口

当前工作区存在较多生成产物、缓存和大型数据文件：

- `frontend/node_modules`
- `frontend/dist`
- `frontend/*.tsbuildinfo`
- `backend/**/__pycache__`
- `.pytest_cache`
- `资源标签对照表.xlsx`
- `特效/`
- 调试脚本和截图文件

建议：

- 补根目录 `.gitignore`。
- 明确大型源数据是否进入 Git。如果不进入 Git，应转为文档说明或外部数据目录。
- 删除已误生成的缓存目录，避免后续提交污染。
- 对必须保留的样例数据，准备小体积 fixture，不直接使用 1 GB 级 Excel。

### 5. `import.bat` 临时开放 PG 端口的恢复逻辑不够稳

当前流程通过写入 `docker-compose.override.yml` 临时开放 `5432`，最后再删除。

风险：

- 如果中途脚本异常退出，override 文件可能残留。
- PG 端口会继续暴露。

建议：

- 优先通过后端管理接口导入，避免宿主机直连 PG。
- 或在批处理异常分支中确保删除 override。
- 或改用单独 `docker-compose.import.yml`，调用时显式传 `-f`，避免写临时文件。

---

## 验证结果

### 后端测试

命令：

```powershell
cd backend
python -m pytest
```

结果：

```text
68 passed, 1 warning
```

说明：后端当前测试通过，但存在 Pydantic V2 配置弃用警告和 pytest-asyncio 配置警告，建议后续顺手处理。

### 前端构建

命令：

```powershell
cd frontend
npm run build
```

结果：失败。失败原因见“前端当前无法构建”。

### Docker Compose 配置

命令：

```powershell
docker compose config
```

结果：

```text
docker compose config OK
```

---

## 推荐修复顺序

1. 修复前端构建失败，确保 `npm run build` 通过。
2. 修复 `import.bat` 特效 JSON 文件名，避免特效数据被跳过。
3. 修复特效 GIF 预览路径协议，前端不要再猜文件名。
4. 修复数值范围筛选协议，确保 slider 生成 ES range 查询。
5. 补 ES 重建 bulk 错误检查，避免切换到不完整索引。
6. 补启动日志和健康检查，避免初始化失败被吞。
7. 补 `.gitignore` 并清理生成产物和大型未跟踪文件。

---

## 最小验收清单

- [ ] `python -m pytest` 通过。
- [ ] `npm run build` 通过。
- [ ] `docker compose config` 通过。
- [ ] `import.bat` 能正确识别 `effect_gif_results.json`。
- [ ] 特效卡片缩略图能显示。
- [ ] 特效卡片悬停 GIF 能播放。
- [ ] 数值范围筛选生成 ES range 查询。
- [ ] ES reindex bulk 失败时不会切换 alias。
- [ ] 默认 `ADMIN_API_KEY` 不会被误用于共享环境。
- [ ] 生成产物和大型数据文件不会被误提交。
