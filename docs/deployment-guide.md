# 部署与数据导入指南

本文档说明 `biaoqian` 项目的本地测试环境和正式环境部署方式，以及停服、备份、重新导入数据、增量导入数据的操作流程。

## 环境区分

| 环境 | 脚本目录 | Docker Compose 项目名 | 访问地址 |
| --- | --- | --- | --- |
| 本地测试 | `deploy/local` | `biaoqian_local` | `http://localhost:8081` |
| 正式环境 | `deploy/prod` | `biaoqian` | `https://artsearch.testplus.cn` |

本地测试环境使用 `8081` 端口，避免和正式环境或其他本机服务占用的 `8080` 端口冲突。

## 前置检查

进入项目根目录：

```powershell
Set-Location F:\biaoqian
```

确认 Docker Desktop 已启动：

```powershell
docker info
```

如果出现 `failed to connect to the docker API`，说明 Docker Desktop 还没有启动。请先打开 Docker Desktop，等待它显示运行中。

## 本地测试部署

从项目根目录执行：

```powershell
.\deploy\local\deploy.bat
```

也可以进入脚本目录执行：

```powershell
Set-Location F:\biaoqian\deploy\local
.\deploy.bat
```

部署完成后访问：

```text
http://localhost:8081
```

健康检查地址：

```text
http://localhost:8081/api/v1/health
```

## 本地常用命令

启动或更新服务：

```powershell
.\deploy\local\start.bat
```

停止服务：

```powershell
.\deploy\local\stop.bat
```

备份数据库：

```powershell
.\deploy\local\backup.bat
```

重新导入全部数据：

```powershell
.\deploy\local\reimport-data.bat
```

增量导入新增或更新的数据：

```powershell
.\deploy\local\import-new-data.bat
```

## 正式环境部署

从项目根目录执行：

```powershell
.\deploy\prod\deploy.bat
```

正式环境根目录包装脚本默认也指向 `deploy/prod`，所以也可以执行：

```powershell
.\deploy.bat
```

正式环境访问地址：

```text
https://artsearch.testplus.cn
```

## 正式环境常用命令

启动或更新服务：

```powershell
.\deploy\prod\start.bat
```

停止服务：

```powershell
.\deploy\prod\stop.bat
```

备份数据库：

```powershell
.\deploy\prod\backup.bat
```

重新导入全部数据：

```powershell
.\deploy\prod\reimport-data.bat
```

增量导入新增或更新的数据：

```powershell
.\deploy\prod\import-new-data.bat
```

## 数据源规则

数据导入覆盖 3 个可见模块：

| 模块 | 默认数据源 |
| --- | --- |
| 模型 | 项目根目录下第一个 `.xlsx` 文件 |
| 特效 | `特效\data\effect_gif_results.json` |
| 图标 | `icon_png_results\icon_png_results.json` |

导入脚本支持自动查找模型 Excel 和特效 JSON。为了避免找错文件，生产环境首次导入时建议显式指定数据源。

## 重新导入数据

适用于以下场景：

- 新环境首次灌入数据。
- 数据库为空，需要重新恢复数据。
- 已确认要按源文件重新覆盖标签信息。

本地：

```powershell
.\deploy\local\reimport-data.bat
```

正式：

```powershell
.\deploy\prod\reimport-data.bat
```

显式指定数据源：

```powershell
.\deploy\local\reimport-data.bat /excel "F:\biaoqian\资源标签对照表.xlsx" /effects "F:\biaoqian\特效\data\effect_gif_results.json" /icons "F:\biaoqian\icon_png_results\icon_png_results.json"
```

正式环境同理，将 `deploy\local` 换成 `deploy\prod`。

## 增量导入数据

适用于后续新增或更新一批数据。重复数据不会插入两份，会按 `module_type + resource_path` 更新。

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
.\deploy\local\import-new-data.bat /excel "F:\biaoqian\资源标签对照表.xlsx"
.\deploy\local\import-new-data.bat /effects "F:\biaoqian\特效\data\effect_gif_results.json"
.\deploy\local\import-new-data.bat /icons "F:\biaoqian\icon_png_results\icon_png_results.json"
```

## 备份建议

正式环境重新部署或重新导入前，建议先备份：

```powershell
.\deploy\prod\backup.bat
```

备份文件会保存到项目根目录的 `backups` 目录中。

## 安全注意事项

不要执行会删除 Docker volume 的命令，例如：

```powershell
docker compose down -v
docker volume prune
docker system prune --volumes
```

停止服务请使用：

```powershell
.\deploy\local\stop.bat
.\deploy\prod\stop.bat
```

这些脚本只停止容器，不删除 PostgreSQL 和 Elasticsearch 的数据卷。

## 常见问题

### `localhost:8080` 打不开

本地环境现在使用：

```text
http://localhost:8081
```

`8080` 可能已经被正式环境或其他服务占用。

### 提示 Docker Desktop 未运行

先启动 Docker Desktop，然后执行：

```powershell
docker info
```

确认 Docker 可用后，再重新执行部署脚本。

### 提示端口被占用

查看端口占用：

```powershell
netstat -ano | findstr :8081
```

如果本地端口被占用，可以先停止占用进程，或调整 `docker-compose.dev.yml` 中的端口映射。

