# 部署与数据导入指南

本文档说明 `biaoqian` 的本地测试环境、正式环境、停服、部署、重导数据、增量导入数据，以及从归档数据恢复的方法。

## 环境区分

| 环境 | 脚本目录 | Compose 项目名 | 访问地址 |
| --- | --- | --- | --- |
| 本地测试 | `deploy/local` | `biaoqian_local` | `http://localhost:8081` |
| 正式环境 | `deploy/prod` | `biaoqian` | `https://artsearch.testplus.cn` |

本地和正式环境脚本是一套逻辑，两边都会使用固定的 `runtime_data` 目录保存导入后的 JSONL 归档和预览图片。

## 数据目录机制

导入时传入的模型 JSON、动作 JSON、特效 JSON、UI 图标 JSON 只是“来源”。脚本会把可用数据归档到项目内固定目录：

```text
runtime_data/
  model/previews/        # 模型预览
  animator/previews/     # 动作预览
  effect/gifs/           # 特效 GIF
  ui/pngs/               # UI 图标 PNG
  model/data.jsonl       # 模型归档
  effect/data.jsonl      # 特效归档
  animator/data.jsonl    # 动作归档
  ui/data.jsonl          # UI 图标归档
  logs/imports/          # 导入失败完整日志
```

Docker 只挂载 `runtime_data` 下的固定目录。因此后续新增数据源来自哪里都可以，导入后服务读取的都是固定运行目录。

重复导入不会插入两份数据，数据库按 `module_type + resource_path` 做 upsert。JSONL 归档也会按同一规则合并。

## 前置检查

```powershell
Set-Location F:\biaoqian
docker info
```

如果 `docker info` 失败，先启动 Docker Desktop，等 Docker 正常运行后再执行脚本。

## 停服

本地：

```powershell
.\deploy\local\stop.bat
```

正式：

```powershell
.\deploy\prod\stop.bat
```

停服脚本只停止容器，不删除 PostgreSQL 或 Elasticsearch 的 Docker volume。

## 部署前端和后端

本地：

```powershell
.\deploy\local\deploy.bat
```

正式：

```powershell
.\deploy\prod\deploy.bat
```

根目录快捷脚本默认指向正式环境：

```powershell
.\deploy.bat
```

部署脚本会构建前端、启动 Docker 服务、等待后端健康检查，并抽样验证预览图 URL 是否可访问。

## 重新导入数据

适合首次灌数据、数据库为空、或需要按源文件重新覆盖标签信息的情况。

本地默认重导：

```powershell
.\deploy\local\reimport-data.bat
```

正式默认重导：

```powershell
.\deploy\prod\reimport-data.bat
```

建议显式指定来源，避免自动查找选错文件：

```powershell
.\deploy\local\reimport-data.bat /models "F:\biaoqian\model\merged\model_png_results.json" /animator "F:\biaoqian\animator\actions_tags_format.json" /effects "F:\biaoqian\特效\data\effect_gif_results.json" /icons "F:\biaoqian\icon_png_results\icon_png_results.json"
```

只想重导某一个模块时，可以直接传模块名；不传模块名则默认重导全部模块：

```powershell
.\deploy\local\reimport-data.bat model
.\deploy\local\reimport-data.bat animator
.\deploy\local\reimport-data.bat effect
.\deploy\local\reimport-data.bat icon
```

正式环境把 `deploy\local` 换成 `deploy\prod` 即可。

重导脚本不会删除数据库 volume。它会导入数据、统一重建 ES、刷新字典，并抽样验证预览图。

## 增量导入数据

适合后续只新增或更新一批数据。

本地：

```powershell
.\deploy\local\import-new-data.bat
```

正式：

```powershell
.\deploy\prod\import-new-data.bat
```

只导入某一类数据：

```powershell
.\deploy\local\import-new-data.bat model
.\deploy\local\import-new-data.bat animator
.\deploy\local\import-new-data.bat effect
.\deploy\local\import-new-data.bat icon
```

也可以继续显式指定自定义来源文件：

```powershell
.\deploy\local\import-new-data.bat /models "F:\biaoqian\model\merged\model_png_results.json"
.\deploy\local\import-new-data.bat /animator "F:\biaoqian\animator\actions_tags_format.json"
.\deploy\local\import-new-data.bat /effects "F:\biaoqian\特效\data\effect_gif_results.json"
.\deploy\local\import-new-data.bat /icons "F:\biaoqian\icon_png_results\icon_png_results.json"
```

增量导入也会同步更新 `runtime_data` 归档和预览图片。来源路径可以和初始导入不同。

## 从归档恢复

如果数据库坏了，但 `runtime_data` 还在，可以从归档 JSONL 恢复 PostgreSQL，再统一重建 ES。

本地：

```powershell
.\deploy\local\restore-from-canonical.bat
```

正式：

```powershell
.\deploy\prod\restore-from-canonical.bat
```

根目录快捷脚本默认指向正式环境：

```powershell
.\restore-from-canonical.bat
```

恢复脚本是 upsert，不会因为重复数据插入两份。

## 备份

正式环境导入或部署前建议先备份数据库：

```powershell
.\deploy\prod\backup.bat
```

同时建议定期备份整个 `runtime_data` 目录。数据库备份加 `runtime_data`，才包含完整可恢复数据和预览图片。

## 失败日志

导入、复制预览图、归档恢复、预览验证失败时，会写入：

```text
runtime_data/logs/imports/
```

日志格式是 JSONL，每一行是一条失败记录，包含模块、阶段、资源路径、源文件、目标文件、错误堆栈等信息。

## 常见问题

### 预览图 404

先看导入脚本最后的 `Preview verify summary`。如果失败，打开 `runtime_data/logs/imports/` 里的最新日志，通常能看到缺失的是哪个源图片或哪个 URL。

### 本地打不开 `localhost:8080`

本地测试环境使用：

```text
http://localhost:8081
```

`8080` 可能已经被其他服务占用。

### 提示端口被占用

```powershell
netstat -ano | findstr :8081
```

找到占用进程后关闭，或调整 `docker-compose.dev.yml` 里的端口映射。

### 不要执行这些命令

不要执行会删除 Docker volume 的命令：

```powershell
docker compose down -v
docker volume prune
docker system prune --volumes
```

需要停服请使用 `stop.bat`。
