# API 手册

## 概述
本项目主要提供命令行接口，通过运行不同的Python脚本来执行股票扫描功能。

---

## 命令行接口

### 综合选股扫描器

#### run_scan.py

**描述:** 综合选股扫描器，支持多种技术指标组合筛选

**参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| --mode | string | 否 | 扫描模式: test/full/custom，默认test |
| --n | integer | 否 | 测试模式扫描数量，默认300 |
| --min-signals | integer | 否 | 最少信号数量，默认2 |
| --stocks | list | 否 | 自定义股票代码列表 |

**使用示例:**
```bash
# 扫描前300只股票（测试模式）
python run_scan.py --mode test --n 300

# 全市场扫描，最少3个信号
python run_scan.py --mode full --min-signals 3

# 自定义股票池扫描
python run_scan.py --mode custom --stocks 000001 000002 600000
```

---

### TD序列扫描器

#### run_td_scan.py

**描述:** TD序列扫描器，支持多周期TD序列分析

**参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| --mode | string | 否 | 扫描模式: test/full/custom，默认test |
| --n | integer | 否 | 测试模式扫描数量，默认300 |
| --min-td | integer | 否 | 最小TD计数: 7/8/9，默认7 |
| --periods | list | 否 | 分析周期: daily/weekly/monthly，默认全部 |
| --stocks | list | 否 | 自定义股票代码列表 |

**使用示例:**
```bash
# 扫描前300只股票的9底信号
python run_td_scan.py --mode test --n 300 --min-td 9

# 全市场扫描日K和周K的8底及以上信号
python run_td_scan.py --mode full --periods daily weekly --min-td 8
```