# 加密代理性能测试结果

本次实验聚焦在 Po- **后续计划**:如需补充 CipherStash 数据,需在 PostgreSQL 数据库中安装 Encrypt Query Language (EQL) 扩展、创建加密配置表并注册密钥集。具体步骤参见 https://github.com/cipherstash/encrypt-query-language。当前 Acra 数据已完整且可用于分析加密代理对性能的影响。tgreSQL 环境下,比较未加密访问(Baseline)与接入 Acra 透明加密代理后的性能差异。实验使用 `attack-scripts/benchmark_encryption.py` 自动化脚本执行 120 次写入 / 读取操作,配合 `docker stats` 采样相应容器的 CPU 利用率。

> **CipherStash 测试限制**:尽管代理已成功启动（使用正确的 `workspace_crn: crn:ap-southeast-2.aws:JTJAVGO74RKC67SU`、`client_id` 和 `client_access_key`），CipherStash Proxy 要求在目标数据库中安装 **Encrypt Query Language (EQL)** 扩展并配置加密表。代理日志显示：
> - `ERROR: No Encrypt configuration table in database`
> - `ERROR: schema "eql_v2" does not exist`
> - `Client authentication failed: check username and password`
>
> 在缺少 EQL 的情况下，代理进入透传模式（Passthrough Mode）但客户端认证仍然失败，导致连接被拒绝。完整配置 CipherStash 需要安装 EQL 扩展、创建加密配置表并设置密钥集，超出本次基准测试的范围。实验保留完整的 Acra 性能数据供参考。理性能测试结果

本次实验聚焦在 PostgreSQL 环境下，比较未加密访问（Baseline）、接入 Acra 透明加密代理后的性能差异，并尝试对 CipherStash 代理进行同样测试。实验使用 `attack-scripts/benchmark_encryption.py` 自动化脚本执行 120 次写入 / 读取操作，配合 `docker stats` 采样相应容器的 CPU 利用率。

> **注意**：CipherStash 代理要求提供 Workspace ID 与 Client Access Key 才能启动，[auth] 配置缺失导致本地代理拒绝连接，相关指标暂留空，待凭据补齐后重新采集。

| 工具 | 数据库 | 操作类型 | 加密类型 | Baseline延迟 (ms) | 加密后延迟 (ms) | 延迟开销 (%) | CPU开销 (%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Acra | PostgreSQL | 写入 | 标准 | 3.92 | 5.11 | 30.44 | 3171.43 |
| Acra | PostgreSQL | 读取 | 标准 | 1.42 | 2.28 | 60.22 | — |
| Acra | PostgreSQL | 读取 | 可搜索 | 1.53 | 3.37 | 120.51 | — |

## 实验说明

- **数据集**：针对每个数据库实例自动建表 `benchmark_data`，初始灌入 1000 行随机数据。
- **操作定义**：
  - “写入/标准” —— 单条插入并立即提交。
  - “读取/标准” —— 随机按主键查询。
  - “读取/可搜索” —— `LIKE 'prefix%'` 模糊过滤，模拟可搜索场景。
- **CPU 采集**：统计目标服务相关容器的即时 CPU 利用率并求平均，结果仅供相对比较，短时采样存在波动。
- **后续计划**：提供 `CS_AUTH__WORKSPACE_ID` 与 `CS_AUTH__CLIENT_ACCESS_KEY` 后，重新运行 `docker compose up -d cipherstash-proxy` 与 `python attack-scripts/benchmark_encryption.py` 即可自动补齐空缺数据。
