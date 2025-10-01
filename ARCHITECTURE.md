# 数据库安全实验环境架构图

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           数据库安全实验环境                                      │
│                      (Docker Compose Network: bridge)                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  模块一: 攻击与检测实验                                                           │
│  目标: 测试 SQL 注入攻击及 WAF/IDS 检测效果                                       │
└──────────────────────────────────────────────────────────────────────────────────┘

                      ┌─────────────────┐
                      │ attack-client   │ (攻击模拟器)
                      │ - SQLMap        │
                      │ - Hydra         │
                      │ - 自定义脚本     │
                      └────────┬────────┘
                               │ HTTP 请求
                               │ (SQL 注入、暴力破解)
                               ↓
                      ┌─────────────────┐
                      │  modsecurity    │ ← WAF (Web Application Firewall)
                      │   (OWASP CRS)   │    - 规则匹配
                      │  Port: 8081     │    - 写入审计日志
                      └────────┬────────┘
                               │ 监听流量
                               ├──────────────────────────┐
                               │                          │
                               ↓                          ↓
                      ┌─────────────────┐       ┌────────────────┐
                      │    suricata     │       │   vuln-api     │ (漏洞后端)
                      │ (IDS 入侵检测)   │       │   Flask App    │
                      │ - SQL注入规则    │       │   Port: 8081   │
                      │ - 写入 eve.json  │       └────────┬───────┘
                      └─────────────────┘                 │
                                                          │ 数据库查询
                               ┌──────────────────────────┼──────────────────┐
                               ↓                          ↓                  ↓
                      ┌─────────────────┐       ┌─────────────────┐  ┌──────────────┐
                      │   juiceshop     │       │  postgres-db    │  │   mongo-db   │
                      │  (漏洞靶场)      │       │  Port: 5433     │  │  Port: 27018 │
                      │  Port: 3001     │       │  (攻击目标)     │  │  (NoSQL注入) │
                      └─────────────────┘       └─────────────────┘  └──────────────┘


┌──────────────────────────────────────────────────────────────────────────────────┐
│  模块二: 数据加密性能对比实验                                                      │
│  目标: 对比透明加密代理 (Acra) vs 应用层加密 (pgcrypto) 性能                      │
└──────────────────────────────────────────────────────────────────────────────────┘

                      ┌─────────────────────────────────────┐
                      │         attack-client               │
                      │    (性能测试脚本运行环境)            │
                      │  benchmark_encryption.py            │
                      └──────┬────────────┬─────────────┬───┘
                             │            │             │
                        ┌────┘            │             └────┐
                        │                 │                  │
                        ↓                 ↓                  ↓
              ┌──────────────────┐  ┌─────────────┐  ┌──────────────────┐
              │  postgres-db     │  │ acra-server │  │postgres-pgcrypto │
              │   (Baseline)     │  │   透明代理   │  │ (应用层加密)      │
              │  Port: 5433      │  │ Port: 9393  │  │  Port: 5435      │
              │  未加密基准测试   │  └──────┬──────┘  │  pgcrypto 扩展   │
              └──────────────────┘         │         └──────────────────┘
                                           │ PostgreSQL 协议
                                           │ (拦截并加密)
                                           ↓
                                  ┌─────────────────┐
                                  │ postgres-acra   │
                                  │  (加密数据库)    │
                                  │  Port: 5434     │
                                  │  AES-256-GCM    │
                                  └─────────────────┘
                                           ↑
                                           │ 密钥加载
                                  ┌────────┴────────┐
                                  │  acra-keymaker  │
                                  │  (密钥生成工具)  │
                                  │  初始化后退出    │
                                  └─────────────────┘


┌──────────────────────────────────────────────────────────────────────────────────┐
│  已禁用服务 (测试失败)                                                            │
└──────────────────────────────────────────────────────────────────────────────────┘

                      ┌─────────────────────────┐
                      │  cipherstash-proxy      │ ✗ 协议不兼容
                      │  Port: 7432             │
                      └────────┬────────────────┘
                               │
                               ↓
                      ┌─────────────────────────┐
                      │ postgres-cipherstash    │ ✗ 配置表无法填充
                      │  Port: 5436             │
                      └─────────────────────────┘
```

## 详细架构说明

### 模块一: 攻击与检测链路

```
攻击流程:
┌──────────┐   ①恶意请求    ┌──────────┐   ②规则检测   ┌──────────┐
│ attack-  │ ──────────→   │  ModSec  │ ──────────→  │  vuln-   │
│ client   │               │   WAF    │               │   api    │
└──────────┘               └────┬─────┘               └────┬─────┘
                                │                          │
                         ③流量镜像                    ④数据库查询
                                │                          │
                                ↓                          ↓
                         ┌─────────┐               ┌─────────────┐
                         │Suricata │               │postgres/mongo│
                         │  IDS    │               │     DB      │
                         └─────────┘               └─────────────┘
                                │                          │
                         ⑤写入eve.json              ⑥返回查询结果
                                ↓                          ↓
                         results/suricata/         (正常/异常响应)
```

**关键点**:
1. **ModSecurity (WAF)**: 
   - 作为反向代理拦截所有 HTTP 请求
   - 应用 OWASP CRS 规则检测 SQL 注入
   - 记录到 `/var/log/modsecurity/audit.log`

2. **Suricata (IDS)**: 
   - 使用 `network_mode: "service:modsecurity"` 共享网络栈
   - 监听 `eth0` 接口捕获所有流量
   - 自定义 SQL 注入检测规则
   - 输出到 `results/suricata/eve.json`

3. **vuln-api**: 
   - 故意存在 SQL 注入漏洞的 Flask 应用
   - 连接 postgres-db 和 mongo-db

### 模块二: 加密性能测试架构

```
性能测试对比:

方案 A - Baseline (无加密)
┌──────────┐  直接连接  ┌──────────┐
│benchmark │ ────────→ │postgres- │
│ script   │  5433端口  │   db     │
└──────────┘           └──────────┘

方案 B - Acra 透明代理
┌──────────┐  ①客户端   ┌──────────┐  ②代理转发  ┌──────────┐
│benchmark │ ────────→ │  acra-   │ ────────→  │postgres- │
│ script   │  9393端口  │  server  │    5432     │  acra    │
└──────────┘           └────┬─────┘             └──────────┘
                            │
                       ③加密/解密
                       (AES-256-GCM)
                            │
                       ┌────┴─────┐
                       │ 密钥存储  │
                       │acra_keys/│
                       └──────────┘

方案 C - pgcrypto 应用层加密
┌──────────┐  SQL + 加密函数  ┌──────────┐
│benchmark │ ──────────────→ │postgres- │
│ script   │   5435端口       │pgcrypto  │
│          │ pgp_sym_encrypt  └──────────┘
└──────────┘ pgp_sym_decrypt   ↑ 内置 pgcrypto 扩展
```

**关键差异**:

| 特性 | Baseline | Acra | pgcrypto |
|------|----------|------|----------|
| **透明度** | N/A | 完全透明 | 需修改 SQL |
| **加密位置** | 无 | 代理层 | 数据库内 |
| **应用改造** | N/A | 零改造 | 调用加密函数 |
| **密钥管理** | N/A | 外部密钥文件 | 传入参数 |

## 网络端口映射

| 服务 | 容器内端口 | 主机端口 | 协议 | 用途 |
|------|-----------|---------|------|------|
| juiceshop | 3000 | 3001 | HTTP | Web UI |
| postgres-db | 5432 | 5433 | PostgreSQL | 基准数据库 |
| postgres-acra | 5432 | 5434 | PostgreSQL | Acra 后端 |
| acra-server | 9393 | 9393 | PostgreSQL | 加密代理 |
| postgres-pgcrypto | 5432 | 5435 | PostgreSQL | pgcrypto 扩展 |
| mongo-db | 27017 | 27018 | MongoDB | NoSQL 数据库 |
| vuln-api | 8081 | (内部) | HTTP | 漏洞后端 |
| modsecurity | 8080 | 8081 | HTTP | WAF 入口 |

## 容器依赖关系

```
启动顺序依赖 (depends_on):

postgres-acra
    ↓
acra-keymaker (生成密钥后退出)
    ↓
acra-server

postgres-db, mongo-db
    ↓
vuln-api
    ↓
modsecurity
    ↓
suricata

所有服务
    ↓
attack-client (最后启动，可访问所有服务)
```

## 数据卷 (Volumes)

```
持久化存储:
- postgres_acra_data:      Acra 数据库数据
- postgres_pgcrypto_data:  pgcrypto 数据库数据
- postgres_cipherstash_data: (已禁用)

宿主机挂载:
- ./acra_keys → /keys           (密钥文件)
- ./results/modsecurity → /var/log/modsecurity (WAF 日志)
- ./results/suricata → /var/log/suricata (IDS 日志)
- ./init-pgcrypto.sql → /docker-entrypoint-initdb.d/ (初始化)
```

## 资源配额

| 服务类型 | CPU 限制 | 内存限制 | 内存预留 |
|---------|---------|---------|---------|
| 数据库 & 靶场 | 4 vCPU | 8 GB | 6 GB |
| 代理 & 工具 | 2 vCPU | 4 GB | 2 GB |
| 攻击客户端 | 4 vCPU | 8 GB | 6 GB |

## 安全能力 (Capabilities)

```
attack-client & suricata:
  cap_add:
    - NET_ADMIN  (网络管理权限)
    - NET_RAW    (原始套接字权限)

用途: 
- 网络流量捕获 (tcpdump, Suricata)
- 攻击模拟 (原始数据包构造)
```

## 实验数据流

### 攻击检测实验
```
attack-client 生成攻击
    ↓
ModSecurity 拦截 + Suricata 监听
    ↓
日志写入 results/
    ↓
detect_metrics.py 分析
    ↓
生成 attack_detection_metrics.csv
```

### 加密性能实验
```
benchmark_encryption.py 执行
    ↓
连接 3 个数据库环境 (baseline, acra, pgcrypto)
    ↓
执行 500 次操作 (写入/读取/搜索)
    ↓
docker stats 采样 CPU
    ↓
生成 encryption_benchmark.csv
```

## 总结

此架构实现了两个独立的实验环境:

1. **攻击检测环境**: 完整的攻击-防御-检测链路
   - 攻击层: SQLMap, Hydra, 自定义脚本
   - 防御层: ModSecurity WAF, Suricata IDS
   - 目标层: 漏洞应用 + 数据库

2. **加密性能环境**: 三种数据库配置对比
   - Baseline: 未加密基准
   - Acra: 透明代理加密 (零代码改造)
   - pgcrypto: 应用层字段加密 (细粒度控制)

所有服务运行在同一 Docker 网络中,通过服务名互相访问,资源隔离但网络互通。
