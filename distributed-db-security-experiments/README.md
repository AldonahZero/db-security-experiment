# 分布式数据库安全补充实验

本目录用于补充论文第4章的分布式架构级攻击与防御评估。当前已完成实验一与实验二：实验一包含 PostgreSQL 三分片机制模拟、PostgreSQL+Citus 分布式扩展对照，以及 TiDB 真实分布式数据库热点键对照；实验二评估 TiDB 热点 Region Leader 所在 TiKV 节点遭遇 CPU 压力或网络扰动时的可用性退化与恢复过程。

## 实验一：单分片泛洪攻击与防御评估

### 定位说明

PostgreSQL 原生不提供 TiDB 这类内置分布式分片、Region 或 Leader 调度能力。本实验将 PostgreSQL 相关结果拆成两类：第一类是不使用扩展的“3 个独立 PostgreSQL 容器 + Python 路由层”机制模拟；第二类是使用 Citus 扩展构造协调节点 + 工作节点拓扑的 PostgreSQL 插件化分布式对照。TiDB 部分则是具备 TiKV、PD、Region/Leader 的真实分布式数据库对照。

### 环境

- Docker Compose：启动 3 个 PostgreSQL 分片容器；当前服务器本地 `postgres:latest` 镜像实测为 PostgreSQL 18.3。
- Python：使用 `psycopg2` 执行读写混合负载，使用 `pandas` 和 `matplotlib` 生成汇总表与图。
- 分片规则：`item_id % 3`，热点键固定路由到 `shard-0`。
- 资源限制：每个 PostgreSQL 分片限制为 2 vCPU、2 GiB 内存。该配置用于当前服务器可复现实验，报告中不将结果泛化为生产容量。
- PostgreSQL 18 镜像的数据卷挂载在 `/var/lib/postgresql`，以兼容官方 18+ 镜像的数据目录布局。
- PostgreSQL+Citus 对照默认使用 `citusdata/citus:12.1` 镜像；当前服务器已缓存 `citusdata/citus:12.1.6`，可通过 `CITUS_IMAGE=citusdata/citus:12.1.6` 复用本地镜像。
- 实验一当前按每组 5 次独立重复运行；原始 CSV 保留 `run_id`，论文表格报告均值±标准差，汇总 CSV 额外给出标准差和 95% 置信区间半宽，柱状图使用 95% 置信区间误差线。CPU、P95/P99、Region、Leader 等通用缩写或产品术语保留原文。

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

# 首次或需要重置数据时使用 --clean；会删除本实验的三个 PostgreSQL 分片卷；论文结果使用 5 次重复
python3 scripts/exp1_single_shard_flood.py --clean --start-services --runs 5

# 重新分析结果
python3 scripts/analyze_results.py
```

也可以缩短实验用于快速验证：

```bash
python3 scripts/exp1_single_shard_flood.py --start-services --runs 1 --requests 300 --db-sleep-ms 8
python3 scripts/analyze_results.py
```

### PostgreSQL+Citus 对照

PostgreSQL+Citus 对照使用 Docker Compose 启动 1 个 Citus 协调节点和 3 个 Citus 工作节点。脚本会创建 Citus 扩展、注册工作节点，并将 `citus_items` 和 `citus_events` 按 `item_id` 分布式分片：

```bash
cd /root/db-security-experiment/distributed-db-security-experiments

# 首次运行可能需要拉取 citusdata/citus:12.1 镜像
python3 scripts/exp1_citus_hotspot.py --clean --start-services --runs 5

# 当前服务器可复用已缓存的 citusdata/citus:12.1.6 镜像
CITUS_IMAGE=citusdata/citus:12.1.6 python3 scripts/exp1_citus_hotspot.py --clean --start-services --runs 5

# 合并 PostgreSQL 三分片、PostgreSQL+Citus 与 TiDB 结果
python3 scripts/analyze_results.py
```

当前服务器已使用 `citusdata/citus:12.1.6` 生成 PostgreSQL+Citus 实测 CSV，并已通过 `scripts/analyze_results.py` 合并到表 A、Citus 汇总表和论文补充文字中。

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
python3 scripts/exp1_tidb_hotspot.py --clean --start-services --runs 5

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

## 实验二：TiDB Leader 压力/网络扰动下的可用性与恢复评估

### 定位说明

本实验不复现、也不声称存在 TiDB 产品级共识漏洞。脚本使用正常 SQL 读写混合负载，通过 `SHOW TABLE ... REGIONS` 定位热点键所在 Region 的初始 Leader Store，并用 PD API 映射到具体 TiKV 容器；随后只在本机受控 Docker Compose 集群中对该 TiKV 容器施加 CPU 压力或网络扰动，观察吞吐量、成功请求 P95/P99 延迟、失败率、TiKV 资源负载、Leader 转移和恢复时间。

网络扰动优先尝试在目标容器内使用 `tc/netem` 注入延迟、抖动和少量丢包；如果容器缺少 `tc` 或网络管理权限，脚本会自动降级为短时暂停目标 TiKV 容器，并在 `results/raw/exp2_tidb_perturbation_events.csv` 中记录实际方式为 `docker_pause_fallback`。

### 运行命令

```bash
cd /root/db-security-experiment/distributed-db-security-experiments

# 使用已启动的 TiDB 集群运行 5 次重复实验
python3 scripts/exp2_tidb_leader_stress.py --runs 5

# 若 TiDB 集群尚未启动，可由脚本启动；--clean 会删除 TiDB 数据卷
python3 scripts/exp2_tidb_leader_stress.py --clean --start-services --runs 5

# 快速验证
python3 scripts/exp2_tidb_leader_stress.py --runs 1 --baseline-s 2 --perturb-s 3 --recovery-s 3 --scenarios baseline,leader_cpu_stress

# 重新生成表 B、P99 恢复曲线和论文文字
python3 scripts/analyze_results.py
```

### 场景与指标

- `baseline`：正常基线，无扰动。
- `leader_cpu_stress`：对热点 Region Leader 所在 TiKV 容器启动 CPU 忙循环压力。
- `leader_network_perturbation`：对热点 Region Leader 所在 TiKV 容器注入网络扰动；不支持 `tc/netem` 时自动降级为短时容器暂停模拟。
- `leader_cpu_stress_limited`：在相同 Leader CPU 压力下使用较低客户端并发，评估应用侧限流的缓解效果。

每个场景默认包含正常期 4 秒、扰动期 6 秒和恢复期 6 秒；每组 5 次独立重复。P95/P99 延迟按成功请求统计，失败请求通过失败率单独报告。恢复时间定义为恢复期内业务成功吞吐量达到正常期 90%，且成功请求 P99 延迟不高于正常期 110% 的最早时间。

### 输出

- `results/raw/exp1_single_shard_flood_requests.csv`：逐请求原始记录，包含 `run_id`。
- `results/raw/exp1_shard_resource_samples.csv`：分片 CPU、内存、连接数、活跃事务采样，包含 `run_id`。
- `results/raw/exp1_citus_hotspot_requests.csv`：PostgreSQL+Citus 逐请求原始记录，包含 `run_id`。
- `results/raw/exp1_citus_resource_samples.csv`：Citus 协调节点/工作节点 CPU、内存采样，包含 `run_id`。
- `results/raw/exp1_citus_shard_placements.csv`：热点键对应 Citus 分片与工作节点位置观测，包含 `run_id`。
- `results/raw/exp1_tidb_hotspot_requests.csv`：TiDB 逐请求原始记录，包含 `run_id`。
- `results/raw/exp1_tidb_tikv_resource_samples.csv`：TiKV CPU、内存采样，包含 `run_id`。
- `results/raw/exp1_tidb_region_observations.csv`：TiDB 表 Region、Leader Store 与 PD 热点 Region 观测，包含 `run_id`。
- `results/raw/exp2_tidb_leader_requests.csv`：实验二逐请求原始记录，包含 `run_id`、阶段、目标 Leader TiKV、延迟与成功/失败状态。
- `results/raw/exp2_tidb_tikv_resource_samples.csv`：实验二 TiKV CPU、内存采样，包含阶段和目标 Leader 节点标识。
- `results/raw/exp2_tidb_leader_observations.csv`：实验二热点 Region Leader 采样，包含 Leader 是否发生转移。
- `results/raw/exp2_tidb_perturbation_events.csv`：实验二扰动开始/停止事件与实际注入方式。
- `results/tables/table_A_single_shard_flood.md`：论文可用表 A，主要指标为均值±标准差。
- `results/tables/exp1_single_shard_flood_summary.csv`：PostgreSQL 三分片结构化汇总结果，包含均值、标准差和 95% 置信区间半宽。
- `results/tables/exp1_citus_hotspot_summary.csv`：PostgreSQL+Citus 对照汇总结果，包含均值、标准差和 95% 置信区间半宽。
- `results/tables/exp1_citus_resource_summary.csv`：Citus 节点资源采样汇总，包含均值、标准差和 95% 置信区间半宽。
- `results/tables/exp1_citus_shard_placement_summary.csv`：Citus 分片/工作节点位置汇总。
- `results/tables/exp1_tidb_hotspot_summary.csv`：TiDB 对照汇总结果，包含均值、标准差和 95% 置信区间半宽。
- `results/tables/exp1_tidb_tikv_resource_summary.csv`：TiKV 资源采样汇总，包含均值、标准差和 95% 置信区间半宽。
- `results/tables/exp1_tidb_region_leader_summary.csv`：TiDB Region/Leader 汇总。
- `results/tables/table_B_tidb_leader_stress.md`：论文可用表 B，汇总 TiDB Leader 压力/网络扰动下的可用性与恢复结果。
- `results/tables/exp2_tidb_leader_summary.csv`：实验二场景级结构化汇总结果。
- `results/tables/exp2_tidb_leader_phase_summary.csv`：实验二正常期、扰动期和恢复期分阶段汇总。
- `results/tables/exp2_tidb_tikv_resource_summary.csv`：实验二 TiKV 资源采样汇总。
- `results/tables/exp2_tidb_leader_transfer_summary.csv`：实验二 Leader 转移观测汇总。
- `results/figures/exp1_shard_load_changes.png`：90% 热点流量下各分片物理负载对比图，误差线表示 95% 置信区间。
- `results/figures/exp1_citus_worker_load.png`：PostgreSQL+Citus 热点流量下节点峰值 CPU 对比图，误差线表示 95% 置信区间。
- `results/figures/exp1_tidb_tikv_load.png`：TiDB 热点流量下 TiKV 峰值 CPU 对比图，误差线表示 95% 置信区间。
- `results/figures/exp2_tidb_p99_recovery_curve.png`：TiDB Leader 扰动前后成功请求 P99 延迟与恢复曲线，阴影表示 95% 置信区间。
- `paper/section_4_append_text.md`：可直接并入论文第4章的实验一与实验二文字。
- `paper/reviewer_response.md`：回复审稿意见的补充实验说明。

### 停止环境

```bash
docker compose -f docker-compose.postgres-shards.yml down
```

若需要彻底清理数据卷：

```bash
docker compose -f docker-compose.postgres-shards.yml down -v
```
