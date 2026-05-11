# 分布式数据库安全补充实验

本目录用于补充论文第4章的分布式架构级攻击与防御评估。当前实验一包含三部分：PostgreSQL 三分片机制模拟、PostgreSQL+Citus 分布式扩展对照，以及 TiDB 真实分布式数据库热点 key 对照。

## 实验一：单分片泛洪攻击与防御评估

### 定位说明

PostgreSQL 原生不提供 TiDB 这类内置分布式分片、Region 或 Leader 调度能力。本实验将 PostgreSQL 相关结果拆成两类：第一类是不使用扩展的“3 个独立 PostgreSQL 容器 + Python 路由层”机制模拟；第二类是使用 Citus 扩展构造 coordinator + worker 拓扑的 PostgreSQL 插件化分布式对照。TiDB 部分则是具备 TiKV、PD、Region/Leader 的真实分布式数据库对照。

### 环境

- Docker Compose：启动 3 个 PostgreSQL 分片容器；当前服务器本地 `postgres:latest` 镜像实测为 PostgreSQL 18.3。
- Python：使用 `psycopg2` 执行读写混合负载，使用 `pandas` 和 `matplotlib` 生成汇总表与图。
- 分片规则：`item_id % 3`，热点 key 固定路由到 `shard-0`。
- 资源限制：每个 PostgreSQL 分片限制为 2 vCPU、2 GiB 内存。该配置用于当前服务器可复现实验，报告中不将结果泛化为生产容量。
- PostgreSQL 18 镜像的数据卷挂载在 `/var/lib/postgresql`，以兼容官方 18+ 镜像的数据目录布局。
- PostgreSQL+Citus 对照默认使用 `citusdata/citus:12.1` 镜像；当前服务器已缓存 `citusdata/citus:12.1.6`，可通过 `CITUS_IMAGE=citusdata/citus:12.1.6` 复用本地镜像。

确认镜像版本：

```bash
docker run --rm postgres:latest postgres --version
```

### 防御组

- `baseline`：无防御。
- `shard_limit`：对单分片并发设置上限，超限请求快速失败。
- `hot_key_limit`：对热点 `item_id` 并发设置上限，超限请求快速失败。
- `queue_isolation`：热点请求进入独立队列；热点读请求使用缓存/副本式分流模拟，非热点请求保留独立执行资源。

### 运行命令

```bash
cd /root/db-security-experiment/distributed-db-security-experiments

# 首次或需要重置数据时使用 --clean；会删除本实验的三个 PostgreSQL 分片卷
python3 scripts/exp1_single_shard_flood.py --clean --start-services

# 重新分析结果
python3 scripts/analyze_results.py
```

也可以缩短实验用于快速验证：

```bash
python3 scripts/exp1_single_shard_flood.py --start-services --requests 300 --db-sleep-ms 8
python3 scripts/analyze_results.py
```

### PostgreSQL+Citus 对照

PostgreSQL+Citus 对照使用 Docker Compose 启动 1 个 Citus coordinator 和 3 个 Citus worker。脚本会创建 Citus 扩展、注册 worker 节点，并将 `citus_items` 和 `citus_events` 按 `item_id` 分布式分片：

```bash
cd /root/db-security-experiment/distributed-db-security-experiments

# 首次运行可能需要拉取 citusdata/citus:12.1 镜像
python3 scripts/exp1_citus_hotspot.py --clean --start-services

# 当前服务器可复用已缓存的 citusdata/citus:12.1.6 镜像
CITUS_IMAGE=citusdata/citus:12.1.6 python3 scripts/exp1_citus_hotspot.py --clean --start-services

# 合并 PostgreSQL 三分片、PostgreSQL+Citus 与 TiDB 结果
python3 scripts/analyze_results.py
```

当前 Tinghua 服务器已使用 `citusdata/citus:12.1.6` 生成 PostgreSQL+Citus 实测 CSV，并已通过 `scripts/analyze_results.py` 合并到表 A、Citus 汇总表和论文补充文字中。

若需要停止 Citus 对照环境：

```bash
docker compose -f docker-compose.citus.yml down
```

若需要删除 Citus 对照环境数据卷：

```bash
docker compose -f docker-compose.citus.yml down -v
```

### TiDB 对照

TiDB 对照使用 Docker Compose 启动 1 个 TiDB Server、3 个 TiKV、3 个 PD：

```bash
cd /root/db-security-experiment/distributed-db-security-experiments

# 首次运行会拉取 pingcap/pd、pingcap/tikv、pingcap/tidb v8.5.0 镜像
python3 scripts/exp1_tidb_hotspot.py --clean --start-services

# 合并 PostgreSQL 三分片、PostgreSQL+Citus 与 TiDB 结果，重新生成表 A 和论文文字
python3 scripts/analyze_results.py
```

若需要停止 TiDB 对照环境：

```bash
docker compose -f docker-compose.tidb.yml down
```

若需要删除 TiDB 对照环境数据卷：

```bash
docker compose -f docker-compose.tidb.yml down -v
```

### 输出

- `results/raw/exp1_single_shard_flood_requests.csv`：逐请求原始记录。
- `results/raw/exp1_shard_resource_samples.csv`：分片 CPU、内存、连接数、活跃事务采样。
- `results/raw/exp1_citus_hotspot_requests.csv`：PostgreSQL+Citus 逐请求原始记录。
- `results/raw/exp1_citus_resource_samples.csv`：Citus coordinator/worker CPU/内存采样。
- `results/raw/exp1_citus_shard_placements.csv`：热点 key 对应 Citus shard 与 worker placement 观测。
- `results/raw/exp1_tidb_hotspot_requests.csv`：TiDB 逐请求原始记录。
- `results/raw/exp1_tidb_tikv_resource_samples.csv`：TiKV CPU/内存采样。
- `results/raw/exp1_tidb_region_observations.csv`：TiDB 表 Region、Leader Store 与 PD 热点 Region 观测。
- `results/tables/table_A_single_shard_flood.md`：论文可用表 A。
- `results/tables/exp1_single_shard_flood_summary.csv`：结构化汇总结果。
- `results/tables/exp1_citus_hotspot_summary.csv`：PostgreSQL+Citus 对照汇总结果。
- `results/tables/exp1_citus_resource_summary.csv`：Citus 节点资源采样汇总。
- `results/tables/exp1_citus_shard_placement_summary.csv`：Citus shard/worker placement 汇总。
- `results/tables/exp1_tidb_hotspot_summary.csv`：TiDB 对照汇总结果。
- `results/tables/exp1_tidb_tikv_resource_summary.csv`：TiKV 资源采样汇总。
- `results/tables/exp1_tidb_region_leader_summary.csv`：TiDB Region/Leader 汇总。
- `results/figures/exp1_shard_load_changes.png`：90% 热点流量下各分片物理负载对比图。
- `results/figures/exp1_citus_worker_load.png`：PostgreSQL+Citus 热点流量下节点峰值 CPU 对比图。
- `results/figures/exp1_tidb_tikv_load.png`：TiDB 热点流量下 TiKV 峰值 CPU 对比图。
- `paper/section_4_append_text.md`：可直接并入论文第4章的实验一文字。

### 停止环境

```bash
docker compose -f docker-compose.postgres-shards.yml down
```

若需要彻底清理数据卷：

```bash
docker compose -f docker-compose.postgres-shards.yml down -v
```
