# 实验总结

## 实验环境
- 主机操作系统：Linux（实验节点默认 shell 为 `bash`）。
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

## 运行说明
```bash
cd /root/db-security-experiment
python3 attack-scripts/automate_attacks.py
```
- 结果：
	- 指标 CSV：`results/attack_metrics.csv`
	- 详细日志：`results/logs/<攻击名称>.stdout.log|stderr.log`
	- 生成的 PIN 字典：`results/pins_4digit_top1000.txt`

## 实验结果汇总
_生成时间: 2025-09-29T12:47:26+00:00 UTC_

### 攻击执行性能 (节选)
| 工具 | 目标 | 攻击类型 | 成功率% | 平均延迟ms | 峰值CPU% | 峰值内存% | 备注 |
| ---- | ---- | -------- | ------ | ---------- | -------- | -------- | ---- |
| Hydra | PostgreSQL | 字典攻击 | 0 | - | - | - |  |
| Hydra | PostgreSQL | 暴力破解 | 0 | - | - | - |  |
| raw-http | PostgreSQL | 基础SQL注入 | 0 | - | 12.5 | - | 0.7 |
| raw-http | PostgreSQL | 混淆SQL注入 | 0 | - | 20.0 | - | 0.7 |
| raw-http | PostgreSQL | 存储过程调用 | 0 | - | 33.3 | - | 0.7 |
| sqlmap | PostgreSQL | 联合查询注入 | 0 | - | 14.2 | - | 0.7 |
| sqlmap | PostgreSQL | 时间盲注 | 100 | - | 11.1 | - | 0.71 |
| sqlmap | MongoDB | NoSQL注入 | 100 | - | 0.8 | - | 1.74 |
| Hydra | PostgreSQL | 字典攻击 | 100 | - | 50.0 | - | 0.72 |
| Hydra | PostgreSQL | 暴力破解 | 0 | - | 22.2 | - | 0.78 |

### 检测效果 (SQL 注入)
| 工具 | 场景 | 样本量 (恶意/良性) | TP | FN | TPR% | FP | TN | FPR% |
| ---- | ---- | ----------------- | -- | -- | ---- | -- | -- | ---- |
| ModSecurity | 基础SQL注入 | 150 / 150 | 150 | 0 | 100.0 | 0 | 150 | 0.0 |
| Suricata | 基础SQL注入 | 150 / 150 | 150 | 0 | 100.0 | 0 | 150 | 0.0 |
| ModSecurity | 混淆SQL注入 | 150 / 150 | 150 | 0 | 100.0 | 0 | 150 | 0.0 |
| Suricata | 混淆SQL注入 | 150 / 150 | 150 | 0 | 100.0 | 0 | 150 | 0.0 |
| ModSecurity | 存储过程调用 | 150 / 150 | 150 | 0 | 100.0 | 0 | 150 | 0.0 |
| Suricata | 存储过程调用 | 150 / 150 | 150 | 0 | 100.0 | 0 | 150 | 0.0 |

### 说明
- 基础SQL注入: 直接使用 UNION SELECT 提取信息。
- 混淆SQL注入: 在关键字之间使用注释绕过简单匹配。
- 存储过程调用: 利用 pg_sleep() 进行时间延迟侧信道。
- TPR=True Positive Rate, FPR=False Positive Rate。
- 本轮测试每类场景共生成 150 条恶意与 150 条正常请求。Suricata 在基础与混淆场景中对每个恶意请求均触发了双重告警 (共 300 条)，仍然计算为 150 个有效告警。
