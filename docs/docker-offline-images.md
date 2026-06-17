# Docker Hub 不可用时的镜像处理方案

## 背景

当前项目本机已有 `postgres:16` 和 `nginx:alpine`，但构建还需要两个基础镜像：

- Elasticsearch：`8.15.0`
- Python：`3.12-slim`

如果 Docker Hub 无法访问，后端和 ES 镜像会在 `docker compose build` 阶段失败。项目现在支持两种处理方式：在线替代源和离线导入。

---

## 方案一：使用替代镜像源

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

默认配置如下：

```env
ELASTICSEARCH_BASE_IMAGE=docker.elastic.co/elasticsearch/elasticsearch:8.15.0
PYTHON_BASE_IMAGE=python:3.12-slim
IK_PLUGIN_URL=https://get.infini.cloud/elasticsearch/analysis-ik/8.15.0
PIP_INDEX_URL=
```

如果 Docker Hub 不能访问，但公司内网或国内代理有 Python 镜像，把 `PYTHON_BASE_IMAGE` 改成可访问的镜像名，例如：

```env
PYTHON_BASE_IMAGE=registry.example.com/library/python:3.12-slim
```

如果 PyPI 也访问慢，可以设置：

```env
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

然后构建：

```powershell
docker compose build
docker compose up -d
```

---

## 方案二：完全离线导入

在一台可以联网的机器上准备镜像和 IK 插件。

### 1. 导出基础镜像

```powershell
docker pull docker.elastic.co/elasticsearch/elasticsearch:8.15.0
docker pull python:3.12-slim

docker save docker.elastic.co/elasticsearch/elasticsearch:8.15.0 -o elasticsearch-8.15.0.tar
docker save python:3.12-slim -o python-3.12-slim.tar
```

### 2. 下载 IK 插件

下载地址：

```text
https://get.infini.cloud/elasticsearch/analysis-ik/8.15.0
```

保存为：

```text
docker/elasticsearch/analysis-ik-8.15.0.zip
```

### 3. 在目标机器导入镜像

把两个 `.tar` 文件和 `analysis-ik-8.15.0.zip` 拷到目标机器后执行：

```powershell
docker load -i elasticsearch-8.15.0.tar
docker load -i python-3.12-slim.tar

docker tag docker.elastic.co/elasticsearch/elasticsearch:8.15.0 biaoqiao/elasticsearch-base:8.15.0
docker tag python:3.12-slim biaoqiao/python-base:3.12-slim
```

确认文件存在：

```powershell
Test-Path .\docker\elasticsearch\analysis-ik-8.15.0.zip
```

### 4. 使用离线 compose 构建

```powershell
docker compose -f docker-compose.yml -f docker-compose.offline.yml build
docker compose -f docker-compose.yml -f docker-compose.offline.yml up -d
```

---

## 验证

查看镜像是否已生成：

```powershell
docker images | Select-String "biaoqiao"
```

查看 ES 插件：

```powershell
docker compose exec elasticsearch elasticsearch-plugin list
```

预期包含：

```text
analysis-ik
```

查看服务状态：

```powershell
docker compose ps
```

如果使用离线 compose 启动，后续命令也保持同样的 `-f` 参数：

```powershell
docker compose -f docker-compose.yml -f docker-compose.offline.yml ps
```
