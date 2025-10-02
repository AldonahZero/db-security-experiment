# Database Security Experiment Environment# 数据库安全实验环境



[中文文档](readme_zh.md) | English本实验环境提供了完整的数据库安全攻防测试平台，包括：

1. **攻击模拟**: SQL 注入、NoSQL 注入、暴力破解等

This experimental environment provides a complete database security offensive-defensive testing platform, including:2. **防御检测**: ModSecurity WAF、Suricata IDS

1. **Attack Simulation**: SQL Injection, NoSQL Injection, Brute Force, etc.3. **数据加密**: Acra 透明代理、pgcrypto 应用层加密

2. **Defense Detection**: ModSecurity WAF, Suricata IDS

3. **Data Encryption**: Acra Transparent Proxy, pgcrypto Application-level Encryption## 实验模块



## Experiment Modules### 📦 模块一: 攻击与检测 (已完成)

- 攻击工具: sqlmap, Hydra, 自定义脚本

### 📦 Module 1: Attack & Detection (Completed)- 防御工具: ModSecurity (WAF), Suricata (IDS)

- Attack Tools: sqlmap, Hydra, custom scripts- 结果: TPR 95-97%, FPR 0.7-3.7%

- Defense Tools: ModSecurity (WAF), Suricata (IDS)

- Results: TPR 95-97%, FPR 0.7-3.7%### 🔐 模块二: 数据加密对比 (已完成)

- **Acra 透明代理**: 延迟 +21-127%, 相对CPU增长 +91-255%

### 🔐 Module 2: Encryption Performance Comparison (Completed)- **pgcrypto 内置扩展**: 延迟 +34-112%, 相对CPU增长 +106-152%

- **Acra Transparent Proxy**: Latency +21-127%, Relative CPU Growth +91-255%- 完整报告: `ENCRYPTION_REPORT.md`

- **pgcrypto Built-in Extension**: Latency +34-112%, Relative CPU Growth +106-152%

- Full Report: `ENCRYPTION_REPORT.md`## 实验环境

- 主机操作系统：Linux/macOS（实验节点默认 shell 为 `bash`/`zsh`）

## Experiment Environment- 编排方式：Docker Compose（`docker-compose.yml` 定义，语法基于 v3.8）

- 资源配额：所有核心服务均限制为 4 vCPU、8 GiB 内存（`cpus: "4"`，`mem_limit: 8g`，`mem_reservation: 6g`）

- Host OS: Linux/macOS (default shell: `bash`/`zsh`)

- Orchestration: Docker Compose (`docker-compose.yml`, syntax based on v3.8)### 服务拓扑

- Resource Quota: All core services limited to 4 vCPU, 8 GB memory (`cpus: "4"`, `mem_limit: 8g`, `mem_reservation: 6g`)| 服务 | 镜像 / 构建 | 端口映射 | 资源限制 | 说明 |

| --- | --- | --- | --- | --- |

### Service Topology| Juice Shop 靶场 | `bkimminich/juice-shop:latest` | `3001 -> 3000/tcp` | 4 vCPU / 8 GiB | Web 靶站，提供 SQL/NoSQL 漏洞入口 |

| PostgreSQL (Baseline) | `postgres:13` | `5433 -> 5432/tcp` | 4 vCPU / 8 GiB | 基准数据库，SQLMap & Hydra 攻击目标，数据库名 `juiceshop_db` |

| Service | Image / Build | Port Mapping | Resource Limit | Description || PostgreSQL (Acra) | `postgres:13` | `5434 -> 5432/tcp` | 4 vCPU / 8 GiB | Acra 加密代理后端数据库，数据库名 `acra_db` |

| --- | --- | --- | --- | --- || Acra Server | `cossacklabs/acra-server:0.94.0` | `9393 -> 9393/tcp` | 2 vCPU / 4 GiB | 透明加密代理，拦截并加密 PostgreSQL 通信 |

| Juice Shop Target | `bkimminich/juice-shop:latest` | `3001 -> 3000/tcp` | 4 vCPU / 8 GB | Web target with SQL/NoSQL vulnerabilities || PostgreSQL (pgcrypto) | `postgres:13` | `5435 -> 5432/tcp` | 4 vCPU / 8 GiB | pgcrypto 扩展测试数据库，数据库名 `pgcrypto_db` |

| PostgreSQL (Baseline) | `postgres:13` | `5433 -> 5432/tcp` | 4 vCPU / 8 GB | Baseline database, SQLMap & Hydra target, DB: `juiceshop_db` || MongoDB | `mongo:4` | `27018 -> 27017/tcp` | 4 vCPU / 8 GiB | NoSQL 注入测试目标 |

| PostgreSQL (Acra) | `postgres:13` | `5434 -> 5432/tcp` | 4 vCPU / 8 GB | Acra encrypted proxy backend, DB: `acra_db` || Vulnerable API (`vuln-api`) | 本地构建 `Dockerfile.vuln` | 内部 `8081/tcp`（不对外暴露） | 2 vCPU / 4 GiB | Flask 漏洞 API，ModSecurity 与 Suricata 的后端目标 |

| Acra Server | `cossacklabs/acra-server:0.94.0` | `9393 -> 9393/tcp` | 2 vCPU / 4 GB | Transparent encryption proxy, intercepts PostgreSQL traffic || ModSecurity WAF | 本地构建 `Dockerfile.modsecurity` → `local-modsecurity:latest` | `8081 -> 8080/tcp` | 2 vCPU / 4 GiB | 反向代理 + OWASP CRS，挂载审计/访问日志目录 |

| PostgreSQL (pgcrypto) | `postgres:13` | `5435 -> 5432/tcp` | 4 vCPU / 8 GB | pgcrypto extension test database, DB: `pgcrypto_db` || Suricata IDS | 本地构建 `Dockerfile.suricata` → `local-suricata:latest` | 与 WAF 共用网络（无独立端口） | 2 vCPU / 4 GiB | 监听 WAF 流量，加载 SQL 注入规则并写入 `results/suricata` |

| MongoDB | `mongo:4` | `27018 -> 27017/tcp` | 4 vCPU / 8 GB | NoSQL injection test target || 攻击客户端 | 自定义镜像 `db-security-attack-client:latest`（由根目录 Dockerfile 构建） | 无对外端口 | 4 vCPU / 8 GiB | 运行自动化攻击、漏洞应用与测量脚本 | 主机操作系统：Linux（实验节点默认 shell 为 `bash`）。

| Vulnerable API | Build `Dockerfile.vuln` | Internal `8081/tcp` (not exposed) | 2 vCPU / 4 GB | Flask vulnerable API, backend for ModSecurity & Suricata |- 编排方式：Docker Compose（`docker-compose.yml` 定义，语法基于 v3.8）。

| ModSecurity WAF | Build `Dockerfile.modsecurity` | `8081 -> 8080/tcp` | 2 vCPU / 4 GB | Reverse proxy + OWASP CRS, mounts audit/access logs |- 资源配额：所有核心服务均限制为 4 vCPU、8 GiB 内存（`cpus: "4"`，`mem_limit: 8g`，`mem_reservation: 6g`）。

| Suricata IDS | Build `Dockerfile.suricata` | Shares network with WAF | 2 vCPU / 4 GB | Listens to WAF traffic, loads SQL injection rules |

| Attack Client | Custom `db-security-attack-client:latest` | No external ports | 4 vCPU / 8 GB | Runs automated attacks, vulnerability apps, measurement scripts |### 服务拓扑

| 服务 | 镜像 / 构建 | 端口映射 | 资源限制 | 说明 |

## Attack Client Image| --- | --- | --- | --- | --- |

| Juice Shop 靶场 | `bkimminich/juice-shop:latest` | `3001 -> 3000/tcp` | 4 vCPU / 8 GiB | Web 靶站，提供 SQL/NoSQL 漏洞入口 |

- Base Image: `ubuntu:20.04`| PostgreSQL | `postgres:13` | `5433 -> 5432/tcp` | 4 vCPU / 8 GiB | SQLMap & Hydra 攻击目标，数据库名 `juiceshop_db` |

- APT Packages: `python3`, `python3-pip`, `python3-psycopg2`, `python3-venv`, `curl`, `git`, `sqlmap`, `hydra`| MongoDB | `mongo:4` | `27018 -> 27017/tcp` | 4 vCPU / 8 GiB | NoSQL 注入测试目标 |

- Python Dependencies: `Flask`, `PyMongo` (installed via `pip3`)| Vulnerable API (`vuln-api`) | 本地构建 `Dockerfile.vuln` | 内部 `8081/tcp`（不对外暴露） | 2 vCPU / 4 GiB | Flask 漏洞 API，ModSecurity 与 Suricata 的后端目标 |

- Included Files:| ModSecurity WAF | 本地构建 `Dockerfile.modsecurity` → `local-modsecurity:latest` | `8081 -> 8080/tcp` | 2 vCPU / 4 GiB | 反向代理 + OWASP CRS，挂载审计/访问日志目录 |

  - `/root/attack-scripts/*.py` — Automated attack and measurement scripts| Suricata IDS | 本地构建 `Dockerfile.suricata` → `local-suricata:latest` | 与 WAF 共用网络（无独立端口） | 2 vCPU / 4 GiB | 监听 WAF 流量，加载 SQL 注入规则并写入 `results/suricata` |

  - `/root/vuln_app.py` — Flask vulnerable demo app (requires manual start)| 攻击客户端 | 自定义镜像 `db-security-attack-client:latest`（由根目录 Dockerfile 构建） | 无对外端口 | 4 vCPU / 8 GiB | 运行自动化攻击、漏洞应用与测量脚本 |



## Core Tools & Framework Versions## 攻击客户端镜像

- 基础镜像：`ubuntu:20.04`。

| Tool / Library | Version | Retrieval Method | Notes |- APT 安装：`python3`、`python3-pip`、`python3-psycopg2`、`python3-venv`、`curl`、`git`、`sqlmap`、`hydra`。

| --- | --- | --- | --- |- Python 依赖：`Flask`、`PyMongo`（通过 `pip3` 安装）。

| Python | 3.8.10 | `python3 --version` | Ubuntu 20.04 default |- 自带文件：

| sqlmap | 1.4.4#stable | `sqlmap --version` | From apt repository |	- `/root/attack-scripts/*.py` —— 自动化攻击与测量脚本。

| Hydra | v9.0 | `hydra -h` first line | From apt repository |	- `/root/vuln_app.py` —— Flask 漏洞演示应用（需手动启动）。

| Flask | 3.0.3 | `python3 -c "import flask"` | Installed via pip |

| PyMongo | 4.10.1 | `python3 -c "import pymongo"` | Installed via pip |## 核心工具与框架版本

| 工具 / 库 | 版本 | 获取方式 | 备注 |

## Database & Target Versions| --- | --- | --- | --- |

| Python | 3.8.10 | `python3 --version` | Ubuntu 20.04 默认 |

- PostgreSQL: Image `postgres:13` (DB user/password set via Compose environment variables: `youruser` / `password123`)| sqlmap | 1.4.4#stable | `sqlmap --version` | apt 软件源提供 |

- MongoDB: Image `mongo:4`| Hydra | v9.0 | `hydra -h` 首行 | apt 软件源提供 |

- Juice Shop: Image `bkimminich/juice-shop:latest` (official latest release)| Flask | 3.0.3 | `python3 -c "import flask"` | pip 安装 |

| PyMongo | 4.10.1 | `python3 -c "import pymongo"` | pip 安装 |

## Dictionaries & Input Data

## 数据库与靶场版本

- `attack-scripts/users.txt` — Username list for Hydra dictionary attack- PostgreSQL：镜像 `postgres:13`（数据库用户/密码由 Compose 环境变量设置：`youruser` / `password123`）。

- `attack-scripts/passwords.txt` — Password list for Hydra dictionary attack- MongoDB：镜像 `mongo:4`。

- `results/pins_4digit_top1000.txt` — Top 1000 4-digit PINs extracted from SecLists; fallback to brute-force enumeration if SecLists unavailable- Juice Shop：镜像 `bkimminich/juice-shop:latest`（官方最新发布）。



## Automation & Monitoring Scripts## 字典与输入数据

- `attack-scripts/users.txt` —— Hydra 字典攻击使用的用户名列表。

- `attack-scripts/automate_attacks.py`- `attack-scripts/passwords.txt` —— Hydra 字典攻击使用的密码列表。

  - Chains SQLMap, Hydra scenarios and writes to `results/attack_metrics.csv`- `results/pins_4digit_top1000.txt` —— 自动脚本从 SecLists（`Passwords/Common-Credentials/four-digit-pin-codes-sorted-by-frequency-withcount.csv`）提取的前 1000 个四位 PIN；若 SecLists 不存在则脚本回退到纯数字暴力枚举。

  - Recorded metrics: success rate, average request latency, peak CPU/memory usage collected by `docker stats`

- `attack-scripts/measure_http_requests.py` and `measure_pg_union.py` / `measure_pg_timeblind.py`## 自动化与监控脚本

  - Measures HTTP response time for different processes, supports sync/async sampling- `attack-scripts/automate_attacks.py`

- Resource monitoring: `monitor_resources` thread uses `docker stats --no-stream` to collect data	- 串联 SQLMap、Hydra 场景并写入 `results/attack_metrics.csv`。

	- 记录指标：成功率、平均请求延迟、`docker stats` 采集的峰值 CPU / 内存占用。

## Quick Start- `attack-scripts/measure_http_requests.py` 及 `measure_pg_union.py` / `measure_pg_timeblind.py`

	- 为不同流程测量 HTTP 响应时间，支持同步或异步采样。

```bash- 资源监控：`monitor_resources` 线程使用 `docker stats --no-stream` 采集数据。

# 1. Start all services

docker compose up -d## 快速开始



# 2. Run attack tests```bash

docker compose exec attack-client python3 /root/attack-scripts/automate_attacks.py# 1. 启动所有服务

docker compose up -d

# 3. Run encryption performance tests (on host environment)

source .venv/bin/activate# 2. 运行攻击测试

python attack-scripts/benchmark_encryption.pydocker compose exec attack-client python3 /root/attack-scripts/automate_attacks.py



# 4. View results# 3. 运行加密性能测试（在主机环境）

cat results/experiment_summary.mdsource .venv/bin/activate

cat ENCRYPTION_REPORT.mdpython attack-scripts/benchmark_encryption.py

```

# 4. 查看结果

## Run Instructionscat results/experiment_summary.md

cat ENCRYPTION_REPORT.md

### Attack Testing```



```bash## 运行说明

cd /root/db-security-experiment

python3 attack-scripts/automate_attacks.py### 攻击测试

``````bash

cd /root/db-security-experiment

**Results**:python3 attack-scripts/automate_attacks.py

- Metrics CSV: `results/attack_metrics.csv````

- Detailed logs: `results/logs/<attack_name>.stdout.log|stderr.log`- 结果：

- Generated PIN dictionary: `results/pins_4digit_top1000.txt`	- 指标 CSV：`results/attack_metrics.csv`

	- 详细日志：`results/logs/<攻击名称>.stdout.log|stderr.log`

### Encryption Performance Testing	- 生成的 PIN 字典：`results/pins_4digit_top1000.txt`



```bash### 加密性能测试

# Start encryption proxy containers```bash

docker compose up -d postgres-acra acra-server postgres-pgcrypto# 启动加密代理容器

docker compose up -d postgres-acra acra-server postgres-pgcrypto

# Run benchmark (requires host environment)

source .venv/bin/activate# 运行基准测试（需要在主机环境）

python attack-scripts/benchmark_encryption.pysource .venv/bin/activate

```python attack-scripts/benchmark_encryption.py

```

**Results**:- 结果：

- Raw data: `results/encryption_benchmark.csv`	- 原始数据：`results/encryption_benchmark.csv`

- Detailed analysis: `results/encryption_benchmark.md`	- 详细分析：`results/encryption_benchmark.md`

- Deep comparison: `results/encryption_comparison.md`	- 深度对比：`results/encryption_comparison.md`

- Full report: `ENCRYPTION_REPORT.md`	- 完整报告：`ENCRYPTION_REPORT.md`



## Experiment Results Summary## 实验结果汇总

_生成时间: 2025-09-29T12:47:26+00:00 UTC_

_Generated: 2025-10-01 UTC_

### 攻击执行性能 (节选)

### Attack Execution Performance (Excerpt)| 工具 | 目标 | 攻击类型 | 成功率% | 平均延迟ms | 峰值CPU% | 峰值内存% | 备注 |

| ---- | ---- | -------- | ------ | ---------- | -------- | -------- | ---- |

| Tool | Target | Attack Type | Success Rate% | Avg Latency (ms) | Peak CPU% | Peak Memory% | Notes || Hydra | PostgreSQL | 字典攻击 | 100 | - | - | - |  |

| ---- | ---- | -------- | ------ | ---------- | -------- | -------- | ---- || Hydra | PostgreSQL | 暴力破解 | 100 | - | - | - |  |

| sqlmap | PostgreSQL | Union-based Injection | 100 | - | 14.2 | - | 0.7 || raw-http | PostgreSQL | 基础SQL注入 | 0 | - | 12.5 | - | 0.7 |

| sqlmap | PostgreSQL | Time-based Blind Injection | 100 | - | 11.1 | - | 0.71 || raw-http | PostgreSQL | 混淆SQL注入 | 0 | - | 20.0 | - | 0.7 |

| sqlmap | MongoDB | NoSQL Injection | 100 | - | 0.8 | - | 1.74 || raw-http | PostgreSQL | 存储过程调用 | 0 | - | 33.3 | - | 0.7 |

| Hydra | PostgreSQL | Dictionary Attack | 100 | - | 50.0 | - | 0.72 || sqlmap | PostgreSQL | 联合查询注入 | 100 | - | 14.2 | - | 0.7 |

| Hydra | PostgreSQL | Brute Force | 100 | - | 22.2 | - | 0.78 || sqlmap | PostgreSQL | 时间盲注 | 100 | - | 11.1 | - | 0.71 |

| sqlmap | MongoDB | NoSQL注入 | 100 | - | 0.8 | - | 1.74 |

### Detection Effectiveness (SQL Injection)| Hydra | PostgreSQL | 字典攻击 | 100 | - | 50.0 | - | 0.72 |

| Hydra | PostgreSQL | 暴力破解 | 100 | - | 22.2 | - | 0.78 |

| Tool | Scenario | Sample Size (Malicious/Benign) | TP | FN | TPR% | FP | TN | FPR% |

| ---- | ---- | ----------------- | -- | -- | ---- | -- | -- | ---- |### 检测效果 (SQL 注入)

| ModSecurity (OWASP CRS) | Basic SQL Injection | 150 / 150 | 146 | 4 | 97.3 | 2 | 148 | 1.3 || 工具 | 场景 | 样本量 (恶意/良性) | TP | FN | TPR% | FP | TN | FPR% |

| Suricata (SQL Ruleset) | Basic SQL Injection | 150 / 150 | 145 | 5 | 96.7 | 3 | 147 | 2.0 || ---- | ---- | ----------------- | -- | -- | ---- | -- | -- | ---- |

| ModSecurity (OWASP CRS) | Obfuscated SQL Injection | 150 / 150 | 143 | 7 | 95.3 | 1 | 149 | 0.7 || ModSecurity (OWASP CRS) | 基础SQL注入 | 150 / 150 | 146 | 4 | 97.3 | 2 | 148 | 1.3 |

| Suricata (SQL Ruleset) | Obfuscated SQL Injection | 150 / 150 | 146 | 4 | 97.3 | 2 | 148 | 1.3 || Suricata (SQL规则集) | 基础SQL注入 | 150 / 150 | 145 | 5 | 96.7 | 3 | 147 | 2.0 |

| ModSecurity (OWASP CRS) | Stored Procedure Call | 150 / 150 | 144 | 6 | 96.0 | 4 | 146 | 2.7 || ModSecurity (OWASP CRS) | 混淆SQL注入 | 150 / 150 | 143 | 7 | 95.3 | 1 | 149 | 0.7 |

| Suricata (SQL Ruleset) | Stored Procedure Call | 150 / 150 | 143 | 7 | 95.3 | 6 | 144 | 3.7 || Suricata (SQL规则集) | 混淆SQL注入 | 150 / 150 | 146 | 4 | 97.3 | 2 | 148 | 1.3 |

| ModSecurity (OWASP CRS) | 存储过程调用 | 150 / 150 | 144 | 6 | 96.0 | 4 | 146 | 2.7 |

### Data Encryption Proxy Performance| Suricata (SQL规则集) | 存储过程调用 | 150 / 150 | 143 | 7 | 95.3 | 6 | 144 | 3.7 |



_Updated: 2025-10-01 | Test Config: 500 samples per operation, CPU sampling interval 0.3s_### 数据加密代理性能

_更新时间: 2025-10-01 | 测试配置: 500 samples per operation, CPU 采样间隔 0.3s_

| Tool | Operation | Encryption Type | Baseline Latency (ms) | Encrypted Latency (ms) | Latency Overhead (%) | CPU Overhead (%) |

| ---- | ---- | ---- | ---- | ---- | ---- | ---- || 工具 | 操作类型 | 加密类型 | Baseline延迟 (ms) | 加密后延迟 (ms) | 延迟开销 (%) | CPU开销 (%) |

| Acra | Write | Standard | 3.58 | 4.34 | 21.44 | 254.62 || ---- | ---- | ---- | ---- | ---- | ---- | ---- |

| Acra | Read | Standard | 1.00 | 2.26 | 126.88 | 171.68 || Acra | 写入 | 标准 | 3.58 | 4.34 | 21.44 | 254.62 |

| Acra | Read | Searchable | 1.05 | 2.15 | 105.68 | 91.40 || Acra | 读取 | 标准 | 1.00 | 2.26 | 126.88 | 171.68 |

| pgcrypto | Write | Standard | 3.58 | 4.79 | 33.86 | 152.21 || Acra | 读取 | 可搜索 | 1.05 | 2.15 | 105.68 | 91.40 |

| pgcrypto | Read | Standard | 1.00 | 2.11 | 112.33 | 105.95 || pgcrypto | 写入 | 标准 | 3.58 | 4.79 | 33.86 | 152.21 |

| pgcrypto | Read | Searchable | 1.05 | 1.03 | -1.71 | -1.70 || pgcrypto | 读取 | 标准 | 1.00 | 2.11 | 112.33 | 105.95 |

| pgcrypto | 读取 | 可搜索 | 1.05 | 1.03 | -1.71 | -1.70 |

> **⚠️ CPU Overhead Explanation**: CPU overhead in the table represents **relative growth rate**, not absolute usage. For example, Acra write 254% means CPU usage increased by 2.5x compared to baseline, but absolute CPU usage remains low (~3-4%). Since baseline database operations consume minimal CPU (~1%), the additional computation from encryption (AES-256) results in high relative growth despite low absolute values. In production environments, encryption impact on overall system CPU resources is typically within acceptable range.

> **⚠️ CPU 开销说明**: 表中 CPU 开销为**相对增长率**，非绝对使用率。例如 Acra 写入 254% 是指相比基准增长了 2.5 倍，但绝对 CPU 使用率仍然很低（~3-4%）。数据库基准操作本身 CPU 消耗极低（~1%），因此加密算法（AES-256）带来的额外计算虽然绝对值不大，但相对增长率较高。实际生产环境中，加密对系统整体 CPU 资源的影响通常在可接受范围内。

**Key Findings**:

**关键发现**:

- **Acra Transparent Encryption Proxy**: - **Acra 透明加密代理**: 

  - ✅ Zero code modification, fully transparent  - ✅ 零代码修改，完全透明

  - ✅ Good write latency control (21.44%)  - ✅ 写入延迟控制较好 (21.44%)

  - ⚠️ Higher read and searchable query overhead (106-127%)  - ⚠️ 读取和可搜索查询开销较高 (106-127%)

  - ✅ Suitable for rapid deployment in legacy systems  - ✅ 适合遗留系统快速部署

    

- **pgcrypto Application-level Encryption**: - **pgcrypto 应用层加密**: 

  - ✅ Built into PostgreSQL, no additional deployment  - ✅ PostgreSQL 内置，无需额外部署

  - ✅ Read performance better than Acra (112% vs 127%)  - ✅ 读取性能优于 Acra (112% vs 127%)

  - ✅ Flexible field-level encryption strategy (no performance loss for unencrypted fields -1.71%)  - ✅ 字段级加密策略灵活 (未加密字段无性能损失 -1.71%)

  - ⚠️ Requires SQL query modification  - ⚠️ 需要修改 SQL 查询

  - ✅ Suitable for fine-grained encryption in new applications  - ✅ 适合新应用细粒度加密

    

- **CipherStash**: Testing failed, not a transparent proxy, requires application query rewriting using EQL functions- **CipherStash**: 测试失败，非透明代理，需要应用改写查询使用 EQL 函数



**Performance Comparison Summary**:**性能对比总结**:



| Scenario | Best Solution | Data Support || 场景 | 最优方案 | 数据支撑 |

|------|----------|----------||------|----------|----------|

| Write Latency | **Acra** | 21.44% vs 33.86% || 写入延迟 | **Acra** | 21.44% vs 33.86% |

| Write CPU | **pgcrypto** | 152% vs 255% || 写入 CPU | **pgcrypto** | 152% vs 255% |

| Read Latency | **pgcrypto** | 112% vs 127% || 读取延迟 | **pgcrypto** | 112% vs 127% |

| Read CPU | **pgcrypto** | 106% vs 172% || 读取 CPU | **pgcrypto** | 106% vs 172% |

| Searchable Query | **pgcrypto** | -1.71% vs 106% || 可搜索查询 | **pgcrypto** | -1.71% vs 106% |



**Detailed Analysis**:详细分析见:

- `results/encryption_benchmark.csv` - Raw data- `results/encryption_benchmark.csv` - 原始数据

- `results/encryption_benchmark.md` - Detailed performance analysis- `results/encryption_benchmark.md` - 详细性能分析

- `results/encryption_comparison.md` - Deep solution comparison- `results/encryption_comparison.md` - 深度方案对比

- `results/CPU_SAMPLING_SUCCESS.md` - Data quality improvement report- `results/CPU_SAMPLING_SUCCESS.md` - 数据质量改进报告

- `ENCRYPTION_REPORT.md` - Complete experiment report- `ENCRYPTION_REPORT.md` - 完整实验报告



### Notes### 说明

- 基础SQL注入: 直接使用 UNION SELECT 提取信息。

- **Basic SQL Injection**: Directly uses UNION SELECT to extract information- 混淆SQL注入: 在关键字之间使用注释绕过简单匹配。

- **Obfuscated SQL Injection**: Uses comments between keywords to bypass simple matching- 存储过程调用: 利用 pg_sleep() 进行时间延迟侧信道。

- **Stored Procedure Call**: Exploits pg_sleep() for time-based side-channel attacks- TPR=True Positive Rate, FPR=False Positive Rate。

- **TPR** = True Positive Rate, **FPR** = False Positive Rate- 本轮测试每类场景共生成 150 条恶意与 150 条正常请求。Suricata 在基础与混淆场景中对每个恶意请求均触发了双重告警 (共 300 条)，仍然计算为 150 个有效告警。

- Each scenario generated 150 malicious and 150 benign requests. Suricata triggered double alerts for each malicious request (total 300), still counted as 150 effective alerts- **加密测试**: 每种操作执行 500 个样本，CPU 采样间隔 0.3s，确保数据完整性。每个环境测试前清空表以消除缓存干扰。

- **Encryption Testing**: 500 samples per operation, CPU sampling interval 0.3s, ensures data integrity. Tables cleared before each environment test to eliminate cache interference

## Documentation

- `ARCHITECTURE.md` - System architecture and experiment workflow
- `ENCRYPTION_REPORT.md` - Comprehensive encryption performance report
- `results/encryption_benchmark.md` - Detailed encryption benchmark analysis
- `results/CPU_SAMPLING_SUCCESS.md` - CPU sampling optimization report
- `工具性能比较分析.md` - Tool performance comparison analysis (Chinese)
- `评价指标对比.txt` - Evaluation metrics comparison (Chinese)

## Architecture

For detailed system architecture, container relationships, and experiment workflow, see [ARCHITECTURE.md](ARCHITECTURE.md).

## License

This project is for academic research purposes only.
