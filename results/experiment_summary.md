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