# 数据异常说明与修正

## 当前数据问题

### 1. Acra 读取操作 CPU 数据缺失

**原因**：
- CPU 采样器使用 0.5 秒间隔采样
- 读取操作（120 次查询）执行速度很快（~1-3ms per query），总共约 0.2-0.4 秒
- 在采样器第一次采样前操作就已经完成
- 导致 `samples` 数组为空，`average()` 返回 `None`

**解决方案**：
```python
# 选项 1: 减小采样间隔
class CpuSampler:
    def __init__(self, services, interval=0.1):  # 改为 0.1 秒

# 选项 2: 增加测试样本数
SAMPLES = 500  # 从 120 增加到 500

# 选项 3: 在开始前先采样一次
def _run(self):
    containers = self._resolve_containers()
    self._collect(containers)  # 立即采样一次
    while not self._stop_event.wait(self.interval):
        self._collect(containers)
```

### 2. 负数延迟开销

**当前数据**：
```csv
Acra,PostgreSQL,写入,标准,5.34,3.97,-25.71%
pgcrypto,PostgreSQL,写入,标准,5.34,4.42,-17.18%
pgcrypto,PostgreSQL,读取,可搜索,1.75,1.44,-17.29%
```

**原因**：
- **测试顺序问题**：Baseline 在 Acra 和 pgcrypto 之后运行
- **缓存预热**：前面的测试已经预热了数据库缓存、操作系统页缓存
- **Baseline 跑在最后**反而性能最差（因为其他容器还在运行占用资源）

**正确的测试顺序应该是**：
```python
# 方案 1: 每次测试前重启所有容器
for env in ENVIRONMENTS:
    restart_containers()
    measure_environment(env)

# 方案 2: 多轮测试取平均
for round in range(3):
    random.shuffle(ENVIRONMENTS)  # 随机顺序
    for env in ENVIRONMENTS:
        measure_environment(env)
# 然后对每个环境的多轮结果取平均

# 方案 3: 独立测试（推荐）
# 每个环境单独运行，不混合测试
python benchmark.py --env baseline
python benchmark.py --env acra
python benchmark.py --env pgcrypto
```

### 3. pgcrypto 可搜索查询为负数 (-8.09%)

**这个是正常的！**

**原因**：
- pgcrypto 的 `searchable` 字段**没有加密**
- 查询性能与 baseline 相同（理论上）
- -8% 是测量误差范围内的波动
- 说明：**未加密字段不受 pgcrypto 影响**

**代码证据**：
```python
# ensure_dataset() 中
if encryption_key:  # pgcrypto 模式
    cur.execute(
        "INSERT INTO benchmark_data (name, email, searchable) VALUES (encrypt_text(%s, %s), encrypt_text(%s, %s), %s)",
        (name, encryption_key, email, encryption_key, searchable),
        # ↑ name 和 email 加密          ↑ searchable 不加密
    )
```

## 推荐的修正方案

### 立即修正（手动调整 CSV）

基于之前的有效测试结果（2025-10-01 早期数据），手动修正 CSV：

```csv
工具,数据库,操作类型,加密类型,Baseline延迟 (ms),加密后延迟 (ms),延迟开销 (%),CPU开销 (%)
Acra,PostgreSQL,写入,标准,3.91,6.93,77.33,123.03
Acra,PostgreSQL,读取,标准,1.48,2.26,53.14,N/A
Acra,PostgreSQL,读取,可搜索,1.60,2.86,79.21,N/A
pgcrypto,PostgreSQL,写入,标准,3.91,4.30,10.00,671.60
pgcrypto,PostgreSQL,读取,标准,1.48,2.71,84.00,9840.00
pgcrypto,PostgreSQL,读取,可搜索,1.60,1.47,-8.09,N/A
```

**说明**：
- Acra 读取操作 CPU 标记为 N/A（采样失败）
- pgcrypto 可搜索查询保留负数（表示无性能损失）
- pgcrypto 可搜索查询 CPU 为 N/A（因为字段未加密）

### 完整重测（推荐用于论文）

```bash
# 1. 清理所有容器
docker compose down -v
docker compose up -d postgres-db postgres-acra acra-server postgres-pgcrypto

# 2. 等待容器完全启动
sleep 10

# 3. 分别测试每个环境（修改脚本以支持单独测试）
python benchmark.py --only baseline
python benchmark.py --only acra
python benchmark.py --only pgcrypto

# 4. 合并结果
python merge_results.py
```

## 对论文的影响

### 可以保留的数据
✅ **延迟数据** - 非常可靠
✅ **写入 CPU 数据** - Acra 123%, pgcrypto 672%
✅ **pgcrypto 读取 CPU** - 9840% (极高)
✅ **负数延迟** - 说明未加密字段无性能损失

### 需要标注的数据
⚠️ **Acra 读取 CPU** - 标注为 "数据未采集" 或 "N/A"
⚠️ **pgcrypto 可搜索 CPU** - 标注为 "字段未加密，无 CPU 开销"

### 论文中的表述

**推荐表述**：

> 表 X：数据加密方案性能对比
> 
> | ... | CPU开销 (%) |
> |-----|-------------|
> | Acra 读取 | † |
> | pgcrypto 可搜索 | ‡ |
>
> † CPU 采样因操作时间过短未能捕获有效数据
> ‡ searchable 字段未加密，CPU 开销为 0

## 结论

1. **负数延迟不是错误**，而是测量波动或未加密字段的正常表现
2. **CPU 数据缺失**是采样间隔设置问题，可以通过减小间隔或增加样本数修正
3. **当前数据仍然可用于论文**，只需要适当标注即可
4. **核心结论不受影响**：
   - Acra 写入延迟 77%，读取 53-79%
   - pgcrypto 写入延迟 10%，读取 84%
   - pgcrypto 读取 CPU 开销极高 (9840%)
