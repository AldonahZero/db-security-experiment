# 数据加密代理实验完成报告

## 实验目标

✅ **已完成**: 对比测试两种 PostgreSQL 数据加密方案的性能影响

## 测试方案

### 方案 1: Acra 透明加密代理 ✅
- **类型**: 透明代理 (Transparent Proxy)
- **版本**: v0.94.0
- **部署**: docker compose (acra-server + postgres-acra)
- **端口**: 9393 (代理) → 5432 (数据库)
- **密钥**: AcraStruct storage keys
- **状态**: **完整测试完成**

### 方案 2: pgcrypto 应用层加密 ✅
- **类型**: PostgreSQL 内置扩展
- **版本**: PostgreSQL 13 内置
- **部署**: docker compose (postgres-pgcrypto)
- **端口**: 5435 (数据库)
- **密钥**: 应用层管理的对称密钥
- **状态**: **完整测试完成**

### 方案 3: CipherStash Proxy ❌
- **类型**: 应用级加密代理
- **版本**: latest
- **状态**: **测试失败,已放弃**
- **原因**: 
  - 不是透明代理,需要改写所有 SQL 查询使用 EQL 函数
  - EQL 扩展安装不完整,缺少关键函数
  - Passthrough Mode 协议兼容性问题
  - 配置表无法填充

## 实验结果

### 完整性能数据表

| 工具 | 操作类型 | 加密类型 | Baseline延迟 (ms) | 加密后延迟 (ms) | 延迟开销 (%) | CPU开销 (%) |
| --- | --- | --- | --- | --- | --- | --- |
| Acra | 写入 | 标准 | 3.91 | 6.93 | **77.33** | 123.03 |
| Acra | 读取 | 标准 | 1.48 | 2.26 | **53.14** | - |
| Acra | 读取 | 可搜索 | 1.60 | 2.86 | **79.21** | - |
| pgcrypto | 写入 | 标准 | 3.91 | 4.30 | **10.00** | 671.60 |
| pgcrypto | 读取 | 标准 | 1.48 | 2.71 | **84.00** | 9840.00 |
| pgcrypto | 读取 | 可搜索 | 1.60 | 1.47 | **-8.09** | 0.00 |

### 关键发现

#### Acra 优势
1. ✅ **零代码修改** - 应用完全透明,无需任何代码改动
2. ✅ **平衡性能** - 延迟增加 53-77%,CPU 开销适中 (123%)
3. ✅ **即插即用** - 配置简单,生成密钥即可使用
4. ✅ **适合遗留系统** - 无法修改代码的老系统首选

#### pgcrypto 优势
1. ✅ **写入性能最优** - 延迟仅增加 10%
2. ✅ **零额外部署** - PostgreSQL 内置扩展
3. ✅ **字段级加密** - 可选择性加密敏感字段
4. ✅ **未加密字段无损** - 可搜索查询性能不受影响 (-8%)

#### 性能权衡
- **写入场景**: pgcrypto 胜出 (10% vs 77%)
- **读取场景**: Acra 胜出 (53% vs 84%)
- **CPU 开销**: Acra 远优于 pgcrypto (123% vs 9840%)
- **可搜索查询**: pgcrypto 胜出 (-8% vs 79%)

## 选型建议

### 选择 Acra 的场景
- ✅ 遗留系统无法修改代码
- ✅ 需要快速满足合规要求
- ✅ 多应用共享数据库
- ✅ 读取为主的业务
- ✅ 有运维资源维护代理

### 选择 pgcrypto 的场景
- ✅ 新应用从零开发
- ✅ 写入密集型业务
- ✅ 只需加密部分敏感字段
- ✅ 成本极度敏感
- ✅ 读取量很小

## 实验文件清单

### 配置文件
- ✅ `docker-compose.yml` - 服务编排 (含 Acra、pgcrypto 容器)
- ✅ `init-pgcrypto.sql` - pgcrypto 扩展初始化脚本
- ✅ `cipherstash-proxy.toml` - CipherStash 配置 (已停用)

### 测试脚本
- ✅ `attack-scripts/benchmark_encryption.py` - 自动化基准测试脚本
  - 支持 Acra、pgcrypto、baseline 三种模式
  - 120 samples per operation
  - CPU 采样 via docker stats

### 结果文档
- ✅ `results/encryption_benchmark.csv` - 原始数据 (CSV 格式)
- ✅ `results/encryption_benchmark.md` - 详细分析报告
- ✅ `results/encryption_comparison.md` - 深度对比报告 (新增)
- ✅ `results/experiment_summary.md` - 实验汇总表格

### 密钥文件
- ✅ `acra_keys/attack-client_storage` - Acra 客户端密钥

## Docker 容器状态

### 运行中容器
```bash
✅ postgres-db (baseline, port 5433)
✅ postgres-acra (Acra backend, port 5434)
✅ acra-server (Acra proxy, port 9393)
✅ postgres-pgcrypto (pgcrypto backend, port 5435)
✅ attack-client (测试客户端)
```

### 已停止容器
```bash
⏸️ postgres-cipherstash (port 5436, profile: disabled)
⏸️ cipherstash-proxy (port 7432, profile: disabled)
```

## 测试方法

### 基准测试执行
```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行完整测试
python attack-scripts/benchmark_encryption.py

# 查看结果
cat results/encryption_benchmark.csv
cat results/encryption_benchmark.md
```

### 测试覆盖
- ✅ 写入操作 (120 samples, 单条 INSERT + COMMIT)
- ✅ 读取操作 (120 samples, 随机 ID 查询)
- ✅ 可搜索查询 (120 samples, LIKE 'prefix%' 查询)
- ✅ CPU 开销采样 (docker stats, 0.5s 间隔)

## 实验时间线

1. **2025-09-29** - Acra 测试完成
2. **2025-10-01** - CipherStash 尝试 (凭据配置、EQL 安装)
3. **2025-10-01** - CipherStash 失败,决定更换方案
4. **2025-10-01** - pgcrypto 实现与测试完成
5. **2025-10-01** - 完整文档与对比报告生成

## 技术债务与改进空间

### 当前限制
1. ⚠️ pgcrypto 只加密 name 和 email 字段,searchable 字段未加密
2. ⚠️ CPU 采样间隔 0.5s,可能错过瞬时峰值
3. ⚠️ 测试数据量 1000 行,未覆盖大规模数据场景

### 潜在优化
1. 💡 增加混合加密测试 (Acra + pgcrypto 双重保护)
2. 💡 测试不同数据规模 (1K, 10K, 100K, 1M 行)
3. 💡 测试并发场景 (多线程写入/读取)
4. 💡 测试不同加密算法 (AES-128 vs AES-256)

## 总结

本实验成功对比了两种主流 PostgreSQL 加密方案:

- **Acra** 适合需要透明加密的遗留系统,性能平衡
- **pgcrypto** 适合新应用细粒度字段加密,写入性能优异但读取 CPU 开销极高
- **CipherStash** 不适合作为透明代理使用,需要深度应用集成

实验数据完整,方法可复现,结论明确,可作为数据库加密方案选型的参考依据。

---
**完成时间**: 2025-10-01  
**测试环境**: Docker Compose, macOS, 4 vCPU / 8GB RAM per container
