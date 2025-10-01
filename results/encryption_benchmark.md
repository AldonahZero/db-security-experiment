# 加密代理性能测试结果

本次实验聚焦在 PostgreSQL 环境下，比较未加密访问（Baseline）、接入 Acra 透明加密代理后的性能差异，并尝试对 CipherStash 代理进行同样测试。实验使用 `attack-scripts/benchmark_encryption.py` 自动化脚本执行 120 次写入 / 读取操作，配合 `docker stats` 采样相应容器的 CPU 利用率。

> **注意**：CipherStash 代理要求提供 Workspace ID 与 Client Access Key 才能启动，[auth] 配置缺失导致本地代理拒绝连接，相关指标暂留空，待凭据补齐后重新采集。

| 工具 | 数据库 | 操作类型 | 加密类型 | Baseline延迟 (ms) | 加密后延迟 (ms) | 延迟开销 (%) | CPU开销 (%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Acra | PostgreSQL | 写入 | 标准 | 5.34 | 7.83 | 46.48 | -17.18 |
| Acra | PostgreSQL | 读取 | 标准 | 2.05 | 2.63 | 28.16 | — |
| Acra | PostgreSQL | 读取 | 可搜索 | 1.89 | 3.61 | 90.44 | — |
| CipherStash | PostgreSQL | 写入 | 标准 | 5.34 | — | — | — |
| CipherStash | PostgreSQL | 读取 | 标准 | 2.05 | — | — | — |
| CipherStash | PostgreSQL | 读取 | 可搜索 | 1.89 | — | — | — |

## 实验说明

- **数据集**：针对每个数据库实例自动建表 `benchmark_data`，初始灌入 1000 行随机数据。
- **操作定义**：
  - “写入/标准” —— 单条插入并立即提交。
  - “读取/标准” —— 随机按主键查询。
  - “读取/可搜索” —— `LIKE 'prefix%'` 模糊过滤，模拟可搜索场景。
- **CPU 采集**：统计目标服务相关容器的即时 CPU 利用率并求平均，结果仅供相对比较，短时采样存在波动。
- **后续计划**：提供 `CS_AUTH__WORKSPACE_ID` 与 `CS_AUTH__CLIENT_ACCESS_KEY` 后，重新运行 `docker compose up -d cipherstash-proxy` 与 `python attack-scripts/benchmark_encryption.py` 即可自动补齐空缺数据。
