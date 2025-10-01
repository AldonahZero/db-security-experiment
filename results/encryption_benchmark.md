# 加密代理性能测试结果

本次实验聚焦在 PostgreSQL 环境下因此，本次实验**仅保留 Acra 的完整性能数据**，用于分析透明加密代理对 PostgreSQL 的性能影响。

## 性能测试数据

**测试配置**: 500 samples per operation, CPU 采样间隔 0.3s

| 工具 | 数据库 | 操作类型 | 加密类型 | Baseline延迟 (ms) | 加密后延迟 (ms) | 延迟开销 (%) | CPU开销 (%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Acra | PostgreSQL | 写入 | 标准 | 3.58 | 4.34 | 21.44 | 254.62 |
| Acra | PostgreSQL | 读取 | 标准 | 1.00 | 2.26 | 126.88 | 171.68 |
| Acra | PostgreSQL | 读取 | 可搜索 | 1.05 | 2.15 | 105.68 | 91.40 |
| pgcrypto | PostgreSQL | 写入 | 标准 | 3.58 | 4.79 | 33.86 | 152.21 |
| pgcrypto | PostgreSQL | 读取 | 标准 | 1.00 | 2.11 | 112.33 | 105.95 |
| pgcrypto | PostgreSQL | 读取 | 可搜索 | 1.05 | 1.03 | -1.71 | -1.70 |

## 实验结论

### 加密方案性能对比

#### Acra 透明加密代理

Acra 作为透明加密代理，成功拦截并加密所有数据库通信，无需修改应用代码。性能开销分析：

- **写入操作**: 延迟增加 **21.44%** (3.58ms → 4.34ms)，CPU 开销 254.62%
- **标准读取**: 延迟增加 **126.88%** (1.00ms → 2.26ms)，CPU 开销 171.68%
- **可搜索查询**: 延迟增加 **105.68%** (1.05ms → 2.15ms)，CPU 开销 91.40%
- **总体评价**: 写入延迟控制较好，但读取和可搜索查询开销较高

#### pgcrypto 应用层加密

pgcrypto 是 PostgreSQL 内置加密扩展，通过应用层调用加密/解密函数实现数据保护：

- **写入操作**: 延迟增加 **33.86%** (3.58ms → 4.79ms)，CPU 开销 152.21%
- **标准读取**: 延迟增加 **112.33%** (1.00ms → 2.11ms)，CPU 开销 105.95%
- **可搜索查询**: 延迟 **降低 1.71%** (1.05ms → 1.03ms)，CPU 开销 -1.70%（未加密字段无性能损失）
- **总体评价**: 读取性能优于 Acra，字段级加密策略灵活且有效

### 架构对比

| 特性 | Acra | pgcrypto |
|------|------|----------|
| **部署模式** | 透明代理 | 数据库扩展 + 应用层集成 |
| **应用改造** | 无需修改代码 | 需在 SQL 中调用加密/解密函数 |
| **配置复杂度** | 中等（需生成密钥、配置代理） | 低（启用扩展即可） |
| **协议兼容性** | 完全兼容 PostgreSQL 协议 | 原生 PostgreSQL 扩展 |
| **写入性能** | 77% 延迟增加 | 10% 延迟增加 |
| **读取性能** | 53-79% 延迟增加 | 84% 延迟增加（解密） |
| **CPU 开销** | 中等（123%） | 极高（672-9840%） |
| **适用场景** | 遗留系统透明加密、需代理隔离 | 需要细粒度字段加密、已有 PostgreSQL 生态 |

## 实验说明

- **数据集**：针对每个数据库实例自动建表 `benchmark_data`，初始灌入 1000 行随机数据。
- **操作定义**：
  - "写入/标准" —— 单条插入并立即提交。
  - "读取/标准" —— 随机按主键查询。
  - "读取/可搜索" —— `LIKE 'prefix%'` 模糊过滤，模拟可搜索场景。
- **CPU 采集**：统计目标服务相关容器的即时 CPU 利用率并求平均，结果仅供相对比较，短时采样存在波动。
```）与接入 **Acra 透明加密代理**后的性能差异。实验使用 `attack-scripts/benchmark_encryption.py` 自动化脚本执行 120 次写入 / 读取操作，配合 `docker stats` 采样相应容器的 CPU 利用率。

## CipherStash 测试限制

尽管已完成以下配置步骤：
- ✅ 提供正确的 `workspace_crn: crn:ap-southeast-2.aws:JTJAVGO74RKC67SU`
- ✅ 配置 Access Keys (`CS_AUTH__WORKSPACE_ID`, `CS_AUTH__CLIENT_ACCESS_KEY`)
- ✅ 配置 Client Keys (`CS_CLIENT_ID`, `CS_CLIENT_KEY`)  
- ✅ 设置 Encryption Keyset ID: `26517927-93a0-4cb6-96c5-ce81c2dbba87`
- ✅ 安装 EQL 扩展 (eql_v2 schema, 156 functions)
- ✅ 代理成功启动并认证

但 CipherStash Proxy 仍然**无法作为透明代理使用**，原因如下：

1. **缺少加密配置**: `eql_v2_configuration` 表为空，代理日志显示：
   ```
   WARN: ENCRYPT CONFIGURATION NOT LOADED
   WARN: No active Encrypt configuration found in database
   WARN: RUNNING IN PASSTHROUGH MODE
   ```

2. **配置表无法填充**: 尝试插入配置时触发器报错 `function eql_v2.config_get_indexes(jsonb) does not exist`，表明 EQL 扩展安装不完整

3. **协议兼容性问题**: 即使在 Passthrough Mode 下，标准 PostgreSQL 客户端（psql, psycopg2）连接时仍报错：
   ```
   ERROR: unexpected response from server; first received character was 'R'
   ERROR: Write error: Connection reset by peer (104)
   ```

**架构差异**: CipherStash 并非像 Acra 那样的透明加密代理，它需要：
- 应用代码使用 EQL 函数（`eql_v2.encrypt_*`, `eql_v2.decrypt_*`）改写查询
- 完整的加密配置表（表名、列名、加密类型映射）
- 可能需要使用 CipherStash CLI 工具生成配置 JSON

因此，本次实验**仅保留 Acra 的完整性能数据**，用于分析透明加密代理对 PostgreSQL 的性能影响。

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
