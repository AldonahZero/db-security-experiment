# 实验结果汇总
_生成时间: 2025-09-27T11:03:50.822945 UTC_
## 攻击执行性能 (节选)
| 工具 | 目标 | 攻击类型 | 成功率% | 平均延迟ms | 峰值CPU% | 峰值内存% | 备注 |
| ---- | ---- | -------- | ------ | ---------- | -------- | -------- | ---- |
| Hydra | PostgreSQL | 字典攻击 | 100 | 2.2454380989074707 | 20.0 | - | 0.5 |
| Hydra | PostgreSQL | 暴力破解 | 0 | 2.2516608238220215 | 28.5 | - | 0.56 |
| raw-http | PostgreSQL | 基础SQL注入 | 0 | - | - | - |  |
| raw-http | PostgreSQL | 混淆SQL注入 | 0 | - | - | - |  |
| raw-http | PostgreSQL | 存储过程调用 | 0 | - | - | - |  |
| sqlmap | PostgreSQL | 联合查询注入 | 0 | - | - | - |  |
| sqlmap | PostgreSQL | 时间盲注 | 0 | - | - | - |  |
| sqlmap | MongoDB | NoSQL注入 | 0 | - | - | - |  |
| Hydra | PostgreSQL | 字典攻击 | 0 | - | - | - |  |
| Hydra | PostgreSQL | 暴力破解 | 0 | - | - | - |  |

## 检测效果 (SQL 注入)
| 工具 | 场景 | TP | FN | TPR% | FP | TN | FPR% |
| ---- | ---- | -- | -- | ---- | -- | -- | ---- |
| ModSecurity | 基础SQL注入 | 0 | 0 | 0.0 | 0 | 0 | 0.0 |
| ModSecurity | 混淆SQL注入 | 0 | 0 | 0.0 | 0 | 0 | 0.0 |
| ModSecurity | 存储过程调用 | 0 | 0 | 0.0 | 0 | 0 | 0.0 |
| Suricata | 基础SQL注入 | 0 | 0 | 0.0 | 0 | 0 | 0.0 |
| Suricata | 混淆SQL注入 | 0 | 0 | 0.0 | 0 | 0 | 0.0 |
| Suricata | 存储过程调用 | 0 | 0 | 0.0 | 0 | 0 | 0.0 |

## 说明
- 基础SQL注入: 直接使用 UNION SELECT 提取信息。
- 混淆SQL注入: 在关键字之间使用注释绕过简单匹配。
- 存储过程调用: 利用 pg_sleep() 进行时间延迟侧信道。
- TPR=True Positive Rate, FPR=False Positive Rate。
