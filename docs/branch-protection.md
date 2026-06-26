# GitHub Branch Protection 配置

## 步骤

1. 进入仓库 Settings → Branches → Add rule
2. Branch name pattern: `master`
3. 勾选 "Require status checks to pass before merging"
4. 勾选以下 3 个 status check：
   - `frontend-unit`
   - `backend-integration`
   - `e2e`
5. 勾选 "Require branches to be up to date before merging"
6. 勾选 "Include administrators"
7. Save changes

## 验证

开一个测试 PR，确认 3 个 job 必跑全绿才能 merge。
