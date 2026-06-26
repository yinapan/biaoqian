# 测试运行与维护说明

## 测试金字塔

- Vitest 前端单元（纯 Node，~52 个）
- pytest 后端集成（真连 PG+ES，~44 个）
- Playwright E2E（fixture 环境，~60 个）
- k6 性能（本地手动，~20 个）

## 本地一键脚本

```bash
# 只跑单元
scripts/run_tests.bat unit   # Windows
scripts/run_tests.sh unit    # Linux

# CI 闸门（unit + integration + e2e，不含 perf）
scripts/run_tests.bat all

# 完整验收（all + perf，耗时）
scripts/run_tests.bat full

# 单独跑 perf
scripts/run_tests.bat perf
```

## CI workflow

PR 到 master 自动触发 3 个 job：
- frontend-unit
- backend-integration
- e2e

3 个 job 必绿才能 merge（Branch Protection）。

## 覆盖率门槛

- 前端 ≥ 60%（按文件计）
- 后端 ≥ 70%（按文件计）

## Fixture 维护

季度（每 3 个月）跑 scripts/sample_real_data.py 从 dev 采样 ~50 条/模块，重生成 fixture JSON。

## 排查常见问题

- E2E 预览图加载失败：检查 docker-compose.test.yml 容器内路径是否与 docker-compose.yml 一致
- backend-integration 并行覆盖：检查 DB_SCHEMA / ES_INDEX_ALIAS 是否设了独立 RUN_ID
- Playwright 超时：检查 fixture 环境是否启动完成（curl health check）

## 当前已有测试

- 16 个后端 mock 单元测试（backend/tests/test_*.py）— 保留通过，不与此层重复
