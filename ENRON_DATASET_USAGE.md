# Enron数据集使用说明

## 数据集概述

本实验使用了真实的**Enron Email Dataset**，这是一个广泛应用于数据挖掘、机器学习和安全研究的真实企业数据集。

### 数据集来源

- **官方网站**: https://www.cs.cmu.edu/~enron/
- **提供机构**: Carnegie Mellon University
- **数据背景**: 安然公司（Enron Corporation）破产调查期间公开的员工邮件数据
- **数据规模**: 150个员工的邮件目录

## 实验数据规模

### 测试数据

- **员工数量**: 50个真实员工
- **数据来源**: 从150个员工目录中提取前50个
- **邮箱域名**: 100% @enron.com 真实域名

### 数据提取方法

使用自动化脚本 `load_enron_data.py` 从Enron邮件数据集中提取：

1. 扫描 `data/maildir/` 目录下的150个员工文件夹
2. 从每个员工的邮件中提取真实邮箱地址
3. 生成符合真实强度的测试密码
4. 输出为Python和SQL格式的测试数据

### 提取的员工示例

| 用户名 | 真实邮箱 | 职位/备注 |
|--------|---------|----------|
| allen-p | phillip.allen@enron.com | 员工 |
| arnold-j | john.arnold@enron.com | 员工 |
| arora-h | harry.arora@enron.com | 员工 |
| badeer-r | robert.badeer@enron.com | 员工 |
| bailey-s | susan.bailey@enron.com | 员工 |
| ... | ... | ... |
| hodge-j | jeffrey.hodge@enron.com | 员工 |

**完整列表**: 共50个员工账户（参见 `attack-scripts/enron_test_data.py`）

## 数据文件位置

### 原始数据集

```
data/
└── maildir/
    ├── allen-p/
    │   ├── inbox/
    │   ├── sent/
    │   └── ...
    ├── arnold-j/
    ├── arora-h/
    └── ... (共150个员工目录)
```

### 测试数据文件

1. **Python格式**: `attack-scripts/enron_test_data.py`
   - 包含50个员工的(username, password, email)元组
   - 可直接导入到测试脚本中使用

2. **SQL格式**: `results/enron_test_data.sql`
   - 基线数据库插入语句（明文）
   - pgcrypto数据库插入语句（密码加密）

## 使用方式

### 1. 在测试脚本中导入

```python
from enron_test_data import ENRON_TEST_USERS

# ENRON_TEST_USERS 是包含50个员工信息的列表
for username, password, email in ENRON_TEST_USERS:
    # 使用真实员工数据进行测试
    print(f"{username}: {email}")
```

### 2. 加密保护测试

在 `test_encryption_protection.py` 中：

```python
# 导入完整的Enron数据集（50个真实员工）
from enron_test_data import ENRON_TEST_USERS

# 使用真实的Enron员工数据（50人）
TEST_USERS = ENRON_TEST_USERS
```

### 3. 重新生成测试数据

如需修改员工数量或更新数据：

```bash
# 提取前50个员工（默认）
python attack-scripts/load_enron_data.py

# 提取更多员工（修改脚本中的limit参数）
# scan_employee_emails(limit=100)
```

## 测试结果

使用50个Enron员工数据的测试结果：

| 环境 | 注入成功率 | 窃取记录数 | 密码保护 | 邮箱保护 |
|------|----------|-----------|---------|---------|
| baseline | 100% | 50 | None | None |
| acra | 100% | 50 | None（透明解密） | None |
| pgcrypto | 100% | 50 | High（加密） | None |

**详细结果**: 参见 `results/encryption_protection_test.csv` 和 `results/encryption_protection_test_report.md`

## 数据集优势

### 1. 真实性

- 来自真实企业环境的员工数据
- 真实的邮箱地址格式和域名
- 反映真实企业的用户名命名规范

### 2. 权威性

- Carnegie Mellon University 提供和维护
- 广泛应用于学术研究和工业界
- 数据集引用可增强论文可信度

### 3. 规模适中

- 50个员工样本具有统计显著性
- 不会因数据量过大导致测试时间过长
- 足以展示加密工具在真实场景下的表现

### 4. 可扩展性

- 原始数据集包含150个员工
- 可根据需要扩展到更多样本
- 脚本支持自动化提取和更新

## 学术价值

### 引用示例

在论文中可以这样引用：

> 本实验使用Carnegie Mellon University提供的Enron Email Dataset [1]，选取了50个真实员工账户进行测试。该数据集包含安然公司破产调查期间公开的员工邮件数据，是数据安全研究中广泛使用的基准数据集。
>
> [1] Enron Email Dataset. https://www.cs.cmu.edu/~enron/

### 研究意义

1. **真实性验证**: 使用真实企业数据验证加密工具的实际防护效果
2. **可复现性**: 数据集公开可下载，其他研究者可复现实验结果
3. **对比研究**: 与其他使用相同数据集的研究具有可比性
4. **实用价值**: 结果可直接指导企业级数据库安全部署

## 数据隐私说明

- Enron数据集是公开的调查数据，可用于研究目的
- 数据集中的邮箱地址和用户名均为真实历史数据
- 测试中使用的密码为随机生成，非真实密码
- 符合学术研究伦理和数据使用规范

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `attack-scripts/load_enron_data.py` | Enron数据提取脚本 |
| `attack-scripts/enron_test_data.py` | 提取的50个员工数据（Python格式） |
| `results/enron_test_data.sql` | 提取的50个员工数据（SQL格式） |
| `attack-scripts/test_encryption_protection.py` | 使用Enron数据的加密保护测试脚本 |
| `results/encryption_protection_test.csv` | 测试结果（CSV格式） |
| `results/encryption_protection_test_report.md` | 测试报告（Markdown格式） |

## 更新日志

- **2025-10-10**: 完成Enron数据集集成
  - 提取50个真实员工账户
  - 生成Python和SQL格式测试数据
  - 完成SQL注入防护能力测试
  - 所有测试通过，数据验证完成

---

**注**: 本数据集仅用于学术研究和安全测试目的，不得用于任何非法用途。
