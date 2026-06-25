#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  美术资产检索工作台 — 一键部署脚本
#
#  用法:
#    1. git clone https://github.com/yinapan/biaoqian.git
#    2. cd biaoqian
#    3. 将源数据文件 (model/animator/特效/icon) 拷贝到对应目录
#    4. bash deploy.sh
#
#  前置条件: Docker, Docker Compose, Node.js (>=18)
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# ------ 1. 检查依赖 ------
info "检查依赖..."
command -v docker   >/dev/null 2>&1 || error "未安装 Docker，请先安装: https://docs.docker.com/get-docker/"
command -v node     >/dev/null 2>&1 || error "未安装 Node.js，请先安装: https://nodejs.org/"
docker compose version >/dev/null 2>&1 || error "未安装 Docker Compose V2"

# ------ 2. 配置 .env ------
if [ ! -f .env ]; then
    info "未找到 .env，基于 .env.example 创建..."
    cp .env.example .env

    ADMIN_KEY=$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^ADMIN_API_KEY=.*/ADMIN_API_KEY=${ADMIN_KEY}/" .env
    else
        sed -i "s/^ADMIN_API_KEY=.*/ADMIN_API_KEY=${ADMIN_KEY}/" .env
    fi

    warn ".env 已创建，ADMIN_API_KEY 已自动生成: ${ADMIN_KEY}"
    warn "如需启用 LLM 搜索，请编辑 .env 填写以下配置后重新运行:"
    warn "  LLM_API_KEY=你的密钥"
    warn "  LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3"
    warn "  LLM_MODEL=ark-code-latest"
    echo ""
fi

source .env

# ------ 3. SSL 证书检查 ------
info "检查 SSL 证书..."
mkdir -p ssl
if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
    warn "未找到 SSL 证书文件"
    warn "请将证书放到 ${PROJECT_DIR}/ssl/ 目录:"
    warn "  ssl/cert.pem  — 证书文件（含中间证书链）"
    warn "  ssl/key.pem   — 私钥文件"
    warn ""
    warn "域名申请后，从证书颁发方下载 Nginx 格式的证书即可"
    error "SSL 证书缺失，无法继续部署"
fi
info "SSL 证书就绪"

# ------ 4. 构建前端 ------
info "构建前端..."
cd frontend
if [ ! -d node_modules ]; then
    npm install
fi
npm run build
cd "$PROJECT_DIR"

if [ ! -d frontend/dist ] || [ ! -f frontend/dist/index.html ]; then
    error "前端构建失败，frontend/dist/index.html 不存在"
fi
info "前端构建完成"

# ------ 5. 启动 Docker 服务 ------
info "启动 Docker 服务 (PostgreSQL + Elasticsearch + Backend + Nginx)..."
docker compose up -d --build

info "等待服务健康启动..."
MAX_WAIT=120
WAITED=0
until curl -sf -k https://localhost/api/v1/health >/dev/null 2>&1; do
    sleep 3
    WAITED=$((WAITED + 3))
    if [ $WAITED -ge $MAX_WAIT ]; then
        error "服务启动超时 (${MAX_WAIT}s)，请检查: docker compose logs"
    fi
    echo -n "."
done
echo ""
info "服务已启动"

# ------ 6. 导入数据 ------
ADMIN_KEY="${ADMIN_API_KEY:-dev-admin-key-change-in-prod}"
API_BASE="https://localhost/api/v1/admin"

import_json() {
    local file="$1"
    local endpoint="$2"
    local label="$3"
    info "导入 ${label}: $(basename "$file")"
    HTTP_CODE=$(curl -s -k -o /tmp/import_result.json -w "%{http_code}" \
        -X POST "${API_BASE}/${endpoint}" \
        -H "X-Admin-Key: ${ADMIN_KEY}" \
        -F "file=@${file}" \
        --max-time 600)
    if [ "$HTTP_CODE" = "200" ]; then
        info "  导入成功: $(cat /tmp/import_result.json)"
    else
        warn "  导入失败 (HTTP ${HTTP_CODE}): $(cat /tmp/import_result.json)"
    fi
}

IMPORT_COUNT=0

MODELS_JSON="$PROJECT_DIR/model/merged/model_png_results.json"
if [ -f "$MODELS_JSON" ]; then
    import_json "$MODELS_JSON" "import-models-json" "模型 JSON"
    IMPORT_COUNT=$((IMPORT_COUNT + 1))
fi

ANIMATOR_JSON="$PROJECT_DIR/animator/actions_tags_format.json"
if [ -f "$ANIMATOR_JSON" ]; then
    import_json "$ANIMATOR_JSON" "import-animator-json" "动作 JSON"
    IMPORT_COUNT=$((IMPORT_COUNT + 1))
fi

EFFECTS_JSON="$PROJECT_DIR/特效/data/effect_gif_results.json"
if [ -f "$EFFECTS_JSON" ]; then
    import_json "$EFFECTS_JSON" "import-effects-json" "特效 JSON"
    IMPORT_COUNT=$((IMPORT_COUNT + 1))
fi

ICONS_JSON="$PROJECT_DIR/icon_png_results/icon_png_results.json"
if [ -f "$ICONS_JSON" ]; then
    import_json "$ICONS_JSON" "import-icons-json" "图标 JSON"
    IMPORT_COUNT=$((IMPORT_COUNT + 1))
fi

if [ $IMPORT_COUNT -eq 0 ]; then
    warn "未找到任何 JSON 数据文件"
    warn "请将源 JSON 文件放到对应目录，然后手动通过 Admin API 导入"
fi

# ------ 7. 重建索引 ------
info "重建 Elasticsearch 索引..."
curl -sf -k -X POST "${API_BASE}/reindex-es" \
    -H "X-Admin-Key: ${ADMIN_KEY}" \
    -o /dev/null || warn "索引重建失败，可手动执行"

# ------ 8. 完成 ------
echo ""
echo "============================================"
info "部署完成!"
echo "============================================"
echo ""
echo "  域名:      https://artsearch.testplus.cn"
echo "  IP:        10.11.11.191"
echo "  管理密钥:  ${ADMIN_KEY}"
echo ""
echo "  常用命令:"
echo "    docker compose logs -f        # 查看日志"
echo "    docker compose restart        # 重启服务"
echo "    docker compose down           # 停止服务"
echo "    docker compose down -v        # 停止并清除数据"
echo ""
