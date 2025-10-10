# 数据库安全实验环境

本实验环境提供了完整的数据库安全攻防测试平台，包括：
1. **攻击模拟**: SQL 注入、NoSQL 注入、暴力破解等
2. **防御检测**: ModSecurity WAF、Suricata IDS
3. **数据加密**: Acra 透明代理、pgcrypto 应用层加密

## 实验模块

### 📦 模块一: 攻击与检测 (已完成)
- 攻击工具: sqlmap, Hydra, 自定义脚本
- 防御工具: ModSecurity (WAF), Suricata (IDS)
- 结果: TPR 95-97%, FPR 0.7-3.7%

### 🔐 模块二: 数据加密对比 (已完成)
- **Acra 透明代理**: 延迟 +21-127%, 相对CPU增长 +91-255%
- **pgcrypto 内置扩展**: 延迟 +34-112%, 相对CPU增长 +106-152%
- **SQL注入防护测试**: 使用50个真实Enron员工数据
  - Acra: 透明解密导致100%明文泄露（离线攻击防护有效，在线攻击无效）
  - pgcrypto: 加密字段保持密文（字段级防护有效）
- 完整报告: `ENCRYPTION_REPORT.md`, `ENRON_TEST_SUMMARY.md`

## 实验环境
- 主机操作系统：Linux/macOS（实验节点默认 shell 为 `bash`/`zsh`）
- 编排方式：Docker Compose（`docker-compose.yml` 定义，语法基于 v3.8）
- 资源配额：所有核心服务均限制为 4 vCPU、8 GiB 内存（`cpus: "4"`，`mem_limit: 8g`，`mem_reservation: 6g`）

### 服务拓扑
| 服务 | 镜像 / 构建 | 端口映射 | 资源限制 | 说明 |
| --- | --- | --- | --- | --- |
| Juice Shop 靶场 | `bkimminich/juice-shop:latest` | `3001 -> 3000/tcp` | 4 vCPU / 8 GiB | Web 靶站，提供 SQL/NoSQL 漏洞入口 |
| PostgreSQL (Baseline) | `postgres:13` | `5433 -> 5432/tcp` | 4 vCPU / 8 GiB | 基准数据库，SQLMap & Hydra 攻击目标，数据库名 `juiceshop_db` |
| PostgreSQL (Acra) | `postgres:13` | `5434 -> 5432/tcp` | 4 vCPU / 8 GiB | Acra 加密代理后端数据库，数据库名 `acra_db` |
| Acra Server | `cossacklabs/acra-server:0.94.0` | `9393 -> 9393/tcp` | 2 vCPU / 4 GiB | 透明加密代理，拦截并加密 PostgreSQL 通信 |
| PostgreSQL (pgcrypto) | `postgres:13` | `5435 -> 5432/tcp` | 4 vCPU / 8 GiB | pgcrypto 扩展测试数据库，数据库名 `pgcrypto_db` |
| MongoDB | `mongo:4` | `27018 -> 27017/tcp` | 4 vCPU / 8 GiB | NoSQL 注入测试目标 |
| Vulnerable API (`vuln-api`) | 本地构建 `Dockerfile.vuln` | 内部 `8081/tcp`（不对外暴露） | 2 vCPU / 4 GiB | Flask 漏洞 API，ModSecurity 与 Suricata 的后端目标 |
| ModSecurity WAF | 本地构建 `Dockerfile.modsecurity` → `local-modsecurity:latest` | `8081 -> 8080/tcp` | 2 vCPU / 4 GiB | 反向代理 + OWASP CRS，挂载审计/访问日志目录 |
| Suricata IDS | 本地构建 `Dockerfile.suricata` → `local-suricata:latest` | 与 WAF 共用网络（无独立端口） | 2 vCPU / 4 GiB | 监听 WAF 流量，加载 SQL 注入规则并写入 `results/suricata` |
| 攻击客户端 | 自定义镜像 `db-security-attack-client:latest`（由根目录 Dockerfile 构建） | 无对外端口 | 4 vCPU / 8 GiB | 运行自动化攻击、漏洞应用与测量脚本 | 主机操作系统：Linux（实验节点默认 shell 为 `bash`）。
- 编排方式：Docker Compose（`docker-compose.yml` 定义，语法基于 v3.8）。
- 资源配额：所有核心服务均限制为 4 vCPU、8 GiB 内存（`cpus: "4"`，`mem_limit: 8g`，`mem_reservation: 6g`）。

### 服务拓扑
| 服务 | 镜像 / 构建 | 端口映射 | 资源限制 | 说明 |
| --- | --- | --- | --- | --- |
| Juice Shop 靶场 | `bkimminich/juice-shop:latest` | `3001 -> 3000/tcp` | 4 vCPU / 8 GiB | Web 靶站，提供 SQL/NoSQL 漏洞入口 |
| PostgreSQL | `postgres:13` | `5433 -> 5432/tcp` | 4 vCPU / 8 GiB | SQLMap & Hydra 攻击目标，数据库名 `juiceshop_db` |
| MongoDB | `mongo:4` | `27018 -> 27017/tcp` | 4 vCPU / 8 GiB | NoSQL 注入测试目标 |
| Vulnerable API (`vuln-api`) | 本地构建 `Dockerfile.vuln` | 内部 `8081/tcp`（不对外暴露） | 2 vCPU / 4 GiB | Flask 漏洞 API，ModSecurity 与 Suricata 的后端目标 |
| ModSecurity WAF | 本地构建 `Dockerfile.modsecurity` → `local-modsecurity:latest` | `8081 -> 8080/tcp` | 2 vCPU / 4 GiB | 反向代理 + OWASP CRS，挂载审计/访问日志目录 |
| Suricata IDS | 本地构建 `Dockerfile.suricata` → `local-suricata:latest` | 与 WAF 共用网络（无独立端口） | 2 vCPU / 4 GiB | 监听 WAF 流量，加载 SQL 注入规则并写入 `results/suricata` |
| 攻击客户端 | 自定义镜像 `db-security-attack-client:latest`（由根目录 Dockerfile 构建） | 无对外端口 | 4 vCPU / 8 GiB | 运行自动化攻击、漏洞应用与测量脚本 |

## 攻击客户端镜像
- 基础镜像：`ubuntu:20.04`。
- APT 安装：`python3`、`python3-pip`、`python3-psycopg2`、`python3-venv`、`curl`、`git`、`sqlmap`、`hydra`。
- Python 依赖：`Flask`、`PyMongo`（通过 `pip3` 安装）。
- 自带文件：
	- `/root/attack-scripts/*.py` —— 自动化攻击与测量脚本。
	- `/root/vuln_app.py` —— Flask 漏洞演示应用（需手动启动）。

## 核心工具与框架版本
| 工具 / 库 | 版本 | 获取方式 | 备注 |
| --- | --- | --- | --- |
| Python | 3.8.10 | `python3 --version` | Ubuntu 20.04 默认 |
| sqlmap | 1.4.4#stable | `sqlmap --version` | apt 软件源提供 |
| Hydra | v9.0 | `hydra -h` 首行 | apt 软件源提供 |
| Flask | 3.0.3 | `python3 -c "import flask"` | pip 安装 |
| PyMongo | 4.10.1 | `python3 -c "import pymongo"` | pip 安装 |

## 数据库与靶场版本
- PostgreSQL：镜像 `postgres:13`（数据库用户/密码由 Compose 环境变量设置：`youruser` / `password123`）。
- MongoDB：镜像 `mongo:4`。
- Juice Shop：镜像 `bkimminich/juice-shop:latest`（官方最新发布）。

## 字典与输入数据
- `attack-scripts/users.txt` —— Hydra 字典攻击使用的用户名列表。
- `attack-scripts/passwords.txt` —— Hydra 字典攻击使用的密码列表。
- `results/pins_4digit_top1000.txt` —— 自动脚本从 SecLists（`Passwords/Common-Credentials/four-digit-pin-codes-sorted-by-frequency-withcount.csv`）提取的前 1000 个四位 PIN；若 SecLists 不存在则脚本回退到纯数字暴力枚举。

## 自动化与监控脚本
- `attack-scripts/automate_attacks.py`
	- 串联 SQLMap、Hydra 场景并写入 `results/attack_metrics.csv`。
	- 记录指标：成功率、平均请求延迟、`docker stats` 采集的峰值 CPU / 内存占用。
- `attack-scripts/measure_http_requests.py` 及 `measure_pg_union.py` / `measure_pg_timeblind.py`
	- 为不同流程测量 HTTP 响应时间，支持同步或异步采样。
- 资源监控：`monitor_resources` 线程使用 `docker stats --no-stream` 采集数据。

## 快速开始

```bash
# 1. 启动所有服务
docker compose up -d

# 2. 运行攻击测试
docker compose exec attack-client python3 /root/attack-scripts/automate_attacks.py

# 3. 运行加密性能测试（在主机环境）
source .venv/bin/activate
python attack-scripts/benchmark_encryption.py

# 4. 查看结果
cat results/experiment_summary.md
cat ENCRYPTION_REPORT.md
```

## 运行说明

### 攻击测试
```bash
cd /root/db-security-experiment
python3 attack-scripts/automate_attacks.py
```
- 结果：
	- 指标 CSV：`results/attack_metrics.csv`
	- 详细日志：`results/logs/<攻击名称>.stdout.log|stderr.log`
	- 生成的 PIN 字典：`results/pins_4digit_top1000.txt`

### 加密性能测试
```bash
# 启动加密代理容器
docker compose up -d postgres-acra acra-server postgres-pgcrypto

# 运行基准测试（需要在主机环境）
source .venv/bin/activate
python attack-scripts/benchmark_encryption.py
```
- 结果：
	- 原始数据：`results/encryption_benchmark.csv`
	- 详细分析：`results/encryption_benchmark.md`
	- 深度对比：`results/encryption_comparison.md`
	- 完整报告：`ENCRYPTION_REPORT.md`

## 实验结果汇总
_生成时间: 2025-09-29T12:47:26+00:00 UTC_

### 攻击执行性能 (节选)
| 工具 | 目标 | 攻击类型 | 成功率% | 平均延迟ms | 峰值CPU% | 峰值内存% | 备注 |
| ---- | ---- | -------- | ------ | ---------- | -------- | -------- | ---- |
| Hydra | PostgreSQL | 字典攻击 | 100 | - | - | - |  |
| Hydra | PostgreSQL | 暴力破解 | 100 | - | - | - |  |
| raw-http | PostgreSQL | 基础SQL注入 | 0 | - | 12.5 | - | 0.7 |
| raw-http | PostgreSQL | 混淆SQL注入 | 0 | - | 20.0 | - | 0.7 |
| raw-http | PostgreSQL | 存储过程调用 | 0 | - | 33.3 | - | 0.7 |
| sqlmap | PostgreSQL | 联合查询注入 | 100 | - | 14.2 | - | 0.7 |
| sqlmap | PostgreSQL | 时间盲注 | 100 | - | 11.1 | - | 0.71 |
| sqlmap | MongoDB | NoSQL注入 | 100 | - | 0.8 | - | 1.74 |
| Hydra | PostgreSQL | 字典攻击 | 100 | - | 50.0 | - | 0.72 |
| Hydra | PostgreSQL | 暴力破解 | 100 | - | 22.2 | - | 0.78 |

### 检测效果 (SQL 注入)
| 工具 | 场景 | 样本量 (恶意/良性) | TP | FN | TPR% | FP | TN | FPR% |
| ---- | ---- | ----------------- | -- | -- | ---- | -- | -- | ---- |
| ModSecurity (OWASP CRS) | 基础SQL注入 | 150 / 150 | 146 | 4 | 97.3 | 2 | 148 | 1.3 |
| Suricata (SQL规则集) | 基础SQL注入 | 150 / 150 | 145 | 5 | 96.7 | 3 | 147 | 2.0 |
| ModSecurity (OWASP CRS) | 混淆SQL注入 | 150 / 150 | 143 | 7 | 95.3 | 1 | 149 | 0.7 |
| Suricata (SQL规则集) | 混淆SQL注入 | 150 / 150 | 146 | 4 | 97.3 | 2 | 148 | 1.3 |
| ModSecurity (OWASP CRS) | 存储过程调用 | 150 / 150 | 144 | 6 | 96.0 | 4 | 146 | 2.7 |
| Suricata (SQL规则集) | 存储过程调用 | 150 / 150 | 143 | 7 | 95.3 | 6 | 144 | 3.7 |

### 数据加密代理性能
_更新时间: 2025-10-01 | 测试配置: 500 samples per operation, CPU 采样间隔 0.3s_

| 工具 | 操作类型 | 加密类型 | Baseline延迟 (ms) | 加密后延迟 (ms) | 延迟开销 (%) | CPU开销 (%) |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| Acra | 写入 | 标准 | 3.58 | 4.34 | 21.44 | 254.62 |
| Acra | 读取 | 标准 | 1.00 | 2.26 | 126.88 | 171.68 |
| Acra | 读取 | 可搜索 | 1.05 | 2.15 | 105.68 | 91.40 |
| pgcrypto | 写入 | 标准 | 3.58 | 4.79 | 33.86 | 152.21 |
| pgcrypto | 读取 | 标准 | 1.00 | 2.11 | 112.33 | 105.95 |
| pgcrypto | 读取 | 可搜索 | 1.05 | 1.03 | -1.71 | -1.70 |

> **⚠️ CPU 开销说明**: 表中 CPU 开销为**相对增长率**，非绝对使用率。例如 Acra 写入 254% 是指相比基准增长了 2.5 倍，但绝对 CPU 使用率仍然很低（~3-4%）。数据库基准操作本身 CPU 消耗极低（~1%），因此加密算法（AES-256）带来的额外计算虽然绝对值不大，但相对增长率较高。实际生产环境中，加密对系统整体 CPU 资源的影响通常在可接受范围内。

**关键发现**:
- **Acra 透明加密代理**: 
  - ✅ 零代码修改，完全透明
  - ✅ 写入延迟控制较好 (21.44%)
  - ⚠️ 读取和可搜索查询开销较高 (106-127%)
  - ✅ 适合遗留系统快速部署
  
- **pgcrypto 应用层加密**: 
  - ✅ PostgreSQL 内置，无需额外部署
  - ✅ 读取性能优于 Acra (112% vs 127%)
  - ✅ 字段级加密策略灵活 (未加密字段无性能损失 -1.71%)
  - ⚠️ 需要修改 SQL 查询
  - ✅ 适合新应用细粒度加密
  
- **CipherStash**: 测试失败，非透明代理，需要应用改写查询使用 EQL 函数

**性能对比总结**:

| 场景 | 最优方案 | 数据支撑 |
|------|----------|----------|
| 写入延迟 | **Acra** | 21.44% vs 33.86% |
| 写入 CPU | **pgcrypto** | 152% vs 255% |
| 读取延迟 | **pgcrypto** | 112% vs 127% |
| 读取 CPU | **pgcrypto** | 106% vs 172% |
| 可搜索查询 | **pgcrypto** | -1.71% vs 106% |

详细分析见:
- `results/encryption_benchmark.csv` - 原始数据
- `results/encryption_benchmark.md` - 详细性能分析
- `results/encryption_comparison.md` - 深度方案对比
- `results/CPU_SAMPLING_SUCCESS.md` - 数据质量改进报告
- `ENCRYPTION_REPORT.md` - 完整实验报告

### 加密工具对SQL注入防护能力 (使用Enron数据集)

_测试数据: 50个真实Enron员工账户_

| 工具 | 攻击类型 | 密码字段保护 | 邮箱字段保护 | 适用场景 |
|------|---------|------------|------------|---------|
| 无加密 | 联合查询注入 | ❌ 100%明文泄露 | ❌ 100%明文泄露 | 不推荐 |
| Acra | 联合查询注入 | ❌ 100%明文泄露（透明解密） | ❌ 100%明文泄露 | 仅防离线攻击 |
| pgcrypto | 联合查询注入 | ✅ 100%保持密文 | ❌ 100%明文泄露（未加密） | 字段级防护 |

**关键发现**:
- **Acra透明解密问题**: 虽然后端存储为密文，但SQL注入通过应用层访问时会触发自动解密，导致50个员工的密码和邮箱全部以明文形式泄露
- **pgcrypto字段级加密**: 有效保护了加密字段（密码保持Hex密文），但未加密字段（邮箱）仍会暴露
- **分层防御重要性**: WAF/IDS阻止95-97%攻击，加密作为最后一道防线保护突破后的数据

详细测试报告:
- `ENRON_TEST_SUMMARY.md` - Enron数据集测试完成摘要
- `ENRON_DATASET_USAGE.md` - 数据集使用说明
- `results/encryption_protection_test.csv` - 原始测试结果
- `results/encryption_protection_test_report.md` - 详细分析报告
- `attack-scripts/load_enron_data.py` - 数据提取脚本
- `attack-scripts/enron_test_data.py` - 50个员工测试数据

### 说明
- 基础SQL注入: 直接使用 UNION SELECT 提取信息。
- 混淆SQL注入: 在关键字之间使用注释绕过简单匹配。
- 存储过程调用: 利用 pg_sleep() 进行时间延迟侧信道。
- TPR=True Positive Rate, FPR=False Positive Rate。
- Enron数据集: Carnegie Mellon University提供的真实企业邮件数据集。
- 本轮测试每类场景共生成 150 条恶意与 150 条正常请求。Suricata 在基础与混淆场景中对每个恶意请求均触发了双重告警 (共 300 条)，仍然计算为 150 个有效告警。
- **加密测试**: 每种操作执行 500 个样本，CPU 采样间隔 0.3s，确保数据完整性。每个环境测试前清空表以消除缓存干扰。
