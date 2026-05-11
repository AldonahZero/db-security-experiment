# 分布式数据库安全补充实验

本目录用于补充论文第4章的分布式架构级攻击与防御评估。当前已完成实验一：单分片泛洪攻击与限流/负载均衡防御评估。

## 实验一：单分片泛洪攻击与防御评估

### 环境

- Docker Compose：启动 3 个 PostgreSQL 13 分片容器。
- Python：使用 `psycopg2` 执行读写混合负载，使用 `pandas` 和 `matplotlib` 生成汇总表与图。
- 分片规则：`item_id % 3`，热点 key 固定路由到 `shard-0`。
- 资源限制：每个 PostgreSQL 分片限制为 2 vCPU、2 GiB 内存。该配置用于当前服务器可复现实验，报告中不将结果泛化为生产容量。

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

### 输出

- `results/raw/exp1_single_shard_flood_requests.csv`：逐请求原始记录。
- `results/raw/exp1_shard_resource_samples.csv`：分片 CPU、内存、连接数、活跃事务采样。
- `results/tables/table_A_single_shard_flood.md`：论文可用表 A。
- `results/tables/exp1_single_shard_flood_summary.csv`：结构化汇总结果。
- `results/figures/exp1_shard_load_changes.png`：90% 热点流量下各分片物理负载对比图。
- `paper/section_4_append_text.md`：可直接并入论文第4章的实验一文字。

### 停止环境

```bash
docker compose -f docker-compose.postgres-shards.yml down
```

若需要彻底清理数据卷：

```bash
docker compose -f docker-compose.postgres-shards.yml down -v
```
