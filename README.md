# 美术资产检索工作台

面向美术团队的游戏资产检索工作台，支持模型、特效、动作、图标四大模块的结构化标签筛选与自然语言搜索。

## 技术栈

| 层级     | 技术                                      |
| -------- | ----------------------------------------- |
| 前端     | Vue 3 + Element Plus + Pinia + TypeScript |
| 后端     | FastAPI + asyncpg + elasticsearch-py      |
| 数据库   | PostgreSQL 16 (JSONB)                     |
| 搜索引擎 | Elasticsearch 8.15 + IK 中文分词          |
| 部署     | Docker Compose (4 服务)                   |

## 模块说明

| 模块类型 | module_type | 数据源                     | 预览目录                       |
| -------- | ----------- | -------------------------- | ------------------------------ |
| 模型     | 1           | Excel + JSON + PNGs        | runtime_data/model/previews/   |
| 特效     | 2           | JSON + GIFs                | runtime_data/effect/gifs/      |
| 动作     | 3           | JSON + GIFs                | runtime_data/animator/previews/ |
| 图标     | 4           | JSON + PNGs                | runtime_data/ui/pngs/          |

## 快速部署

### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac)
- Git
- Node.js 18+（用于构建前端）

### 步骤

```bash
# 1. 克隆项目
git clone https://github.com/yinapan/biaoqian.git
cd biaoqian

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env，修改 ADMIN_API_KEY 为随机字符串

# 3. 准备数据文件（放到项目根目录对应位置）
# - 资源标签对照表.xlsx               （模型 Excel）
# - model/merged/model_png_results.json + pngs/   （模型 JSON+PNG）
# - animator/actions_tags_format.json + gifs/     （动作 JSON+GIF）
# - 特效/data/effect_gif_results.json + gifs/      （特效 JSON+GIF）
# - icon_png_results/icon_png_results.json + pngs/ （图标 JSON+PNG）

# 4. 构建前端（首次部署或前端代码变更时）
cd frontend && npm install && npx vite build && cd ..

# 5. 启动服务
start.bat
# 或手动: docker compose up -d --build

# 6. 导入数据（见下方"数据导入"）

# 7. 提取缩略图（首次导入后执行一次）
python scripts/extract_thumbnails.py
```

### 访问

- 本机: http://localhost
- 内网: http://<你的局域网IP> (start.bat 会自动显示)

## 数据导入

### 命令行脚本（推荐）

`scripts/import_data.py` 支持批量导入各模块数据，自动推断预览目录：

```bash
# 导入模型（Excel + JSON）
python scripts/import_data.py --excel 资源标签对照表.xlsx --models-json model/merged/model_png_results.json --reindex

# 导入动作
python scripts/import_data.py --animator-json animator/actions_tags_format.json --reindex

# 导入特效
python scripts/import_data.py --effects-json 特效/data/effect_gif_results.json --reindex

# 导入图标
python scripts/import_data.py --icons-json icon_png_results/icon_png_results.json --reindex

# 从 canonical 归档恢复（不读源 JSON，从 runtime_data 的 JSONL 还原）
python scripts/import_data.py --from-canonical --reindex

# 验证预览图可访问
python scripts/import_data.py --verify-previews --verify-sample-size 20
```

参数说明：
- `--pg-url` PostgreSQL 连接串（默认 `postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao`）
- `--admin-key` 管理密钥（不传则从 `.env` 读取）
- `--backend-url` 后端地址（默认 `http://localhost`）
- `--reindex` 导入后触发 ES 重建索引 + 字典刷新

### Admin API（在线导入）

服务启动后，可通过 HTTP 接口上传 JSON 触发导入：

| 接口                          | 说明           |
| ----------------------------- | -------------- |
| POST /api/v1/admin/import-excel          | 导入模型 Excel |
| POST /api/v1/admin/import-models-json   | 导入模型 JSON  |
| POST /api/v1/admin/import-animator-json  | 导入动作 JSON  |
| POST /api/v1/admin/import-effects-json  | 导入特效 JSON  |
| POST /api/v1/admin/import-icons-json    | 导入图标 JSON  |
| POST /api/v1/admin/reindex-es            | 重建 ES 索引   |
| POST /api/v1/admin/refresh-dictionary    | 刷新字典缓存   |

所有接口需携带 `X-Admin-Key` 头。

## 日常管理

| 操作       | 命令           |
| ---------- | -------------- |
| 启动       | `start.bat`    |
| 停止       | `stop.bat`     |
| 导入数据   | `import.bat`   |
| 备份数据库 | `backup.bat`   |

### 备份与恢复

**备份** — 运行 `backup.bat`，SQL 文件保存在 `backups/` 目录，自动保留最近 7 份。

**恢复** — 将备份文件导入：

```bash
docker compose exec -T postgres psql -U biaoqian -d biaoqian < backups/biaoqian_YYYY-MM-DD_HHMM.sql
```

## 目录结构

```
biaoqian/
├── backend/                # FastAPI 后端
│   └── app/importers/      # 各模块导入器（model/animator/effects/icon/excel）
├── frontend/               # Vue 3 前端
├── docker/                  # Dockerfile (ES + IK)
├── sql/                     # 数据库初始化 SQL
├── scripts/                 # 数据导入/提取脚本
│   └── import_data.py       # 统一导入入口
├── runtime_data/            # 运行时数据（生成，不进 git）
│   ├── model/previews/      # 模型 PNG 预览
│   ├── animator/previews/   # 动作 GIF 预览（前/左视角）
│   ├── effect/gifs/         # 特效 GIF 预览
│   ├── ui/pngs/             # 图标 PNG
│   └── canonical/           # 归档的 JSONL（用于灾难恢复）
├── model/                   # 模型源数据（不进 git）
├── animator/                # 动作源数据（不进 git）
├── 特效/                    # 特效源数据（不进 git）
├── icon_png_results/        # 图标源数据（不进 git）
├── nginx.conf               # Nginx 配置
├── docker-compose.yml
├── start.bat / stop.bat / import.bat / backup.bat
└── .env.example             # 环境变量模板
```

## 常见问题

**Q: Docker 镜像拉不下来？**
修改 `.env` 中的镜像源地址，或参考 `docs/docker-offline-images.md` 使用离线镜像。

**Q: 启动后页面空白？**
确认已执行 `cd frontend && npx vite build` 构建前端。

**Q: 搜索没结果？**
确认已运行 `import.bat` 导入数据。可通过 health 接口检查服务状态:

```bash
curl http://localhost/api/v1/health
```

**Q: 如何更新数据？**
重新运行 `import.bat` 或对应的 `python scripts/import_data.py --xxx-json ...` 命令，会自动 upsert 更新。

**Q: 筛选面板出现 `["乌鸦", "鸟"]` 这种带方括号的选项？**
这是 `tag_values` 表里残留了数组字符串。运行：

```bash
docker compose exec postgres psql -U biaoqiao -d biaoqiao -c "DELETE FROM tag_values WHERE value LIKE '[%'"
curl -X POST http://localhost/api/v1/admin/refresh-dictionary -H "X-Admin-Key: <你的key>"
```

然后重新 `--reindex`。

**Q: 模型/动作预览图不显示？**
检查 `runtime_data/model/previews/` 或 `runtime_data/animator/previews/` 是否有对应文件，且 `docker-compose.yml` 挂载了 `./runtime_data:/runtime_data`。

**Q: 内网其他人访问不了？**
检查 Windows 防火墙是否放行了 80 端口入站规则。
