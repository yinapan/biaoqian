#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  特效数据导入脚本
#
#  用法:
#    bash scripts/import_effects.sh [json_file]
#
#  参数:
#    json_file  可选，默认为 特效/data/effect_gif_results.json
#
#  前置条件: Docker 服务已启动 (start.bat 或 docker compose up -d)
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# Load admin key from .env
if [ -f .env ]; then
    source .env
fi
ADMIN_KEY="${ADMIN_API_KEY:-dev-admin-key-change-in-prod}"
API_BASE="http://localhost/api/v1/admin"

# JSON file path
JSON_FILE="${1:-特效/data/effect_gif_results.json}"

if [ ! -f "$JSON_FILE" ]; then
    error "特效 JSON 文件不存在: $JSON_FILE"
fi

# ------ 1. Check services ------
info "检查服务状态..."
curl -sf http://localhost/api/v1/health >/dev/null 2>&1 || error "服务未运行，请先启动: start.bat"
info "服务正常"

# ------ 2. Clear old effects data ------
info "清除旧特效数据..."
docker compose exec -T postgres psql -U biaoqiao -d biaoqiao -c \
    "DELETE FROM assets WHERE module_type=2;" 2>/dev/null
info "旧数据已清除"

# ------ 3. Import effects JSON ------
info "导入特效数据: $(basename "$JSON_FILE")"
HTTP_CODE=$(curl -s -o /tmp/effects_import.json -w "%{http_code}" \
    -X POST "${API_BASE}/import-effects-json" \
    -H "X-Admin-Key: ${ADMIN_KEY}" \
    -F "file=@${JSON_FILE}" \
    --max-time 600)
if [ "$HTTP_CODE" = "200" ]; then
    info "导入成功: $(cat /tmp/effects_import.json)"
else
    error "导入失败 (HTTP ${HTTP_CODE}): $(cat /tmp/effects_import.json)"
fi

# ------ 4. Rebuild ES index ------
info "重建 Elasticsearch 索引..."
curl -sf -X POST "${API_BASE}/reindex-es" \
    -H "X-Admin-Key: ${ADMIN_KEY}" \
    -o /tmp/reindex_result.json || warn "索引重建失败"
info "索引重建完成: $(cat /tmp/reindex_result.json)"

# ------ 5. Refresh dictionary ------
info "刷新搜索词典..."
curl -sf -X POST "${API_BASE}/refresh-dictionary" \
    -H "X-Admin-Key: ${ADMIN_KEY}" \
    -o /dev/null || warn "词典刷新失败"

# ------ Done ------
echo ""
echo "============================================"
info "特效数据导入完成!"
echo "============================================"
echo ""
echo "  访问地址: http://localhost"
echo "  切换到\"特效\"Tab 查看"
echo ""
