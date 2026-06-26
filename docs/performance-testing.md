# 性能测试本地 runbook

## 前置条件

- dev 环境已启动（docker compose up -d）
- dev 环境已 reindex（POST /api/v1/admin/reindex-es）
- 本地装 k6（Windows: choco install k6；Linux: 见 k6 文档）

## Day 1 实测基线（每季度跑一次）

```bash
mkdir -p tests/performance/reports
for i in $(seq 1 20); do
  k6 run tests/performance/k6-baseline.js --quiet | tee tests/performance/reports/baseline_$(date +%Y%m%d)_${i}.txt
done
```

统计 20 次的 P95 中位数，记为实测 P95。

## Day 2 阈值确定

阈值 = 1.2 × 实测 P95。改 k6-baseline.js 默认 THRESHOLD 值，提交 PR review。

## 日常验证

```bash
# 跑基准
k6 run tests/performance/k6-baseline.js

# 跑并发负载
k6 run tests/performance/k6-load.js
```

## 报告

报告输出到 tests/performance/reports/{date}_{branch}.json，本地保留 30 天。

## 阈值变更流程

1. 提 PR 说明变更原因（硬件升级/数据量变化/代码优化）
2. 至少 1 人 review
3. 不允许单人改阈值
