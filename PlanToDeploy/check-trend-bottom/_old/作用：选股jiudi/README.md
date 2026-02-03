# 三周期九底共振选股系统

## 📖 项目简介

这是一个基于 **TD Sequential（TD序列）** 指标的A股选股工具，能够扫描全市场，找出**日K、周K、月K同时达到九底**的股票。

### 什么是"九底"？

**九底（TD Buy Setup）** 是由 Tom DeMark 创立的技术分析指标，用于识别潜在的市场底部。

**计算规则**：
- 连续9根K线的收盘价低于4根K线前的收盘价
- 当序列值达到9时，视为完成"九底"形态
- 通常预示着下跌趋势可能结束，反弹概率增加

### 什么是"三周期共振"？

当**日K、周K、月K**三个时间周期同时出现九底时，称为"三周期共振"：

| 时间周期 | 信号意义 |
|---------|---------|
| 日K九底 | 短期（数日）反弹信号 |
| 周K九底 | 中期（数周）趋势反转 |
| 月K九底 | 长期（数月）大底确认 |

**三周期同时满足 = 极强的买入信号！**

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行扫描

```bash
python jiudi_scanner.py
```

### 3. 查看结果

扫描完成后，结果保存在 `output/` 目录：

- `三周期九底共振_YYYYMMDD_HHMMSS.csv` - **重点推荐！三周期共振股票**
- `双周期共振_YYYYMMDD_HHMMSS.csv` - 双周期九底股票
- `全部分析结果_YYYYMMDD_HHMMSS.csv` - 所有分析结果

---

## 📁 项目结构

```
作用：选股jiudi/
├── jiudi_scanner.py      # 主程序（扫描全市场）
├── td_sequential.py      # TD序列核心算法
├── data_fetcher.py       # 数据获取模块
├── visualizer.py         # 可视化模块
├── requirements.txt      # 依赖包
├── README.md            # 使用说明
├── data/                # 数据缓存目录
└── output/              # 结果输出目录
    ├── 三周期九底共振_*.csv
    ├── 双周期共振_*.csv
    └── 全部分析结果_*.csv
```

---

## ⚙️ 配置说明

### 调整扫描参数

编辑 `jiudi_scanner.py` 中的 `main()` 函数：

```python
scanner.scan_market(
    max_workers=20,  # 线程数，建议10-30
    limit=None       # None=全市场，或设置数字如100（测试前100只）
)
```

### 参数说明

| 参数 | 说明 | 建议 |
|-----|------|------|
| `max_workers` | 并发线程数 | 网络好20-30，网络差5-10 |
| `limit` | 限制扫描数量 | 全市场=None，测试=100 |

---

## 📊 输出文件说明

### 三周期共振文件（重点推荐）

| 字段 | 说明 |
|-----|------|
| `code` | 股票代码 |
| `name` | 股票名称 |
| `latest_price` | 最新收盘价 |
| `daily_count` | 日K九底序列值 |
| `weekly_count` | 周K九底序列值 |
| `monthly_count` | 月K九底序列值 |
| `is_resonance` | 是否三周期共振 |
| `resonance_level` | 共振等级描述 |

### 示例输出

```
代码     名称     价格    日K序列  周K序列  月K序列  共振等级
000001  平安银行  12.50    11      10      9      🔥 完美共振（三周期九底）
600519  贵州茅台  1680.00   9       12      11     🔥 完美共振（三周期九底）
```

---

## 💡 使用建议

### ⭐⭐⭐⭐⭐ 三周期共振（重点关注）

- **胜率最高**：短中长期趋势都在底部
- **操作建议**：
  - 分批建仓（不要一次性买入）
  - 设置止损（九底失败可能继续下跌）
  - 结合基本面分析（避免买入问题股）

### ⭐⭐⭐⭐ 双周期共振

- **次优选择**：两个周期在底部
- **建议**：观察第三周期是否接近九底

### ⚠️ 重要提示

1. **技术指标仅供参考**：九底不是100%准确的
2. **结合基本面**：选择业绩良好的公司
3. **注意市场环境**：熊市中九底失效概率较高
4. **严格止损**：跌破九底最低价需止损

---

## 🔧 高级功能

### 1. 可视化K线图

```python
from visualizer import JiuDiVisualizer
from data_fetcher import StockDataFetcher
from td_sequential import get_td_signal_info

# 创建可视化器
viz = JiuDiVisualizer()

# 获取数据
fetcher = StockDataFetcher()
daily, weekly, monthly = fetcher.get_multi_period_data('000001')

# 计算TD信号
daily_signal = get_td_signal_info(daily)
weekly_signal = get_td_signal_info(weekly)
monthly_signal = get_td_signal_info(monthly)

# 绘制图表
viz.plot_stock_with_td(
    '000001', '平安银行',
    daily, weekly, monthly,
    daily_signal, weekly_signal, monthly_signal
)
```

### 2. 单只股票分析

```python
from jiudi_scanner import JiuDiScanner

scanner = JiuDiScanner()
result = scanner.analyze_single_stock('000001', '平安银行')

if result and result['is_resonance']:
    print("🔥 三周期共振！")
    print(f"日K: {result['daily_count']}")
    print(f"周K: {result['weekly_count']}")
    print(f"月K: {result['monthly_count']}")
```

---

## 📈 性能参考

| 扫描范围 | 股票数量 | 线程数 | 预计时间 |
|---------|---------|-------|---------|
| 沪深300 | ~300 | 10 | 2-3分钟 |
| 中证500 | ~500 | 15 | 4-6分钟 |
| 全市场 | ~5300 | 20 | 15-25分钟 |

*时间取决于网络速度和服务器响应

---

## ⚠️ 常见问题

### Q1: 扫描速度慢怎么办？

**A**：调整线程数
```python
scanner.scan_market(max_workers=30)  # 增加线程数
```

### Q2: 数据获取失败？

**A**：可能是网络问题或akshare接口限制，建议：
- 检查网络连接
- 降低线程数
- 分时段扫描

### Q3: 没有找到三周期共振股票？

**A**：正常现象！三周期共振非常罕见，建议关注双周期共振股票。

### Q4: 九底后一定会涨吗？

**A**：**不一定！** 九底只是技术信号，受多种因素影响：
- 市场整体趋势
- 个股基本面
- 突发消息事件

**永远不要把所有资金押在一个技术指标上！**

---

## 📞 技术支持

- **数据来源**：akshare（免费开源金融数据接口）
- **参考理论**：Tom DeMark's TD Sequential

---

## 📜 免责声明

⚠️ **重要提示**：

1. 本工具仅供学习研究使用，不构成投资建议
2. 股市有风险，投资需谨慎
3. 使用本工具产生的任何投资决策和后果，由使用者自行承担
4. 作者不对任何投资损失负责

**请务必结合自己的判断和风险承受能力进行投资！**

---

## 🎉 更新日志

### v1.0.0 (2026-01-19)

- ✅ 实现TD Sequential九底算法
- ✅ 支持日K、周K、月K三周期分析
- ✅ 全市场扫描功能
- ✅ 三周期共振筛选
- ✅ 结果导出CSV
- ✅ 多线程并发加速

---

**祝您投资顺利！📈**
