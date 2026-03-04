# 使用说明（Stocks Filter 项目集）

本仓库包含三个主要模块：
1. **get-data**：**数据中心**，负责获取全市场 A 股日线数据，作为单一数据源 (SSOT)。
2. **just-stock-down**：**TD九底分析**，负责分析下跌衰竭信号。
3. **check-steady-uptrend**：**稳步上升分析**，负责扫描上升趋势和突破信号。

> **数据流向**
> `get-data` (获取/存储) -> `data/raw/*.csv` -> `just-stock-down` (读取分析) & `check-steady-uptrend` (读取分析)

---

## 一、第一步：获取数据 (get-data)

所有分析依赖本地数据，请先运行此步骤。

**目录**: `get-data/`

### 1. 环境准备
```bash
pip install pandas tqdm baostock
```

### 1.5 接口诊断（可选）
如果遇到网络问题或数据获取失败，可使用诊断工具检查环境。

```bash
# 在根目录运行
python diagnose.py

# 或者进入交互模式选择特定接口测试
python diagnose.py
```

### 2. 获取数据
```bash
cd get-data
# 获取全市场数据（初次运行推荐）
python main.py --all

# 或者：获取随机 10 只测试
python main.py
```

**输出**: `get-data/data/raw/` 目录下的 CSV 文件。

---

## 二、第二步：运行分析

### 模块 A：check-trend-bottom (TD九底)

**目录**: `check-trend-bottom/`

**功能**: 识别下跌趋势衰竭点 (TD9/TD13)。

```bash
cd check-trend-bottom

# 运行完整分析 (使用本地数据)
python main.py --skip-fetch

# 仅测试 10 只
python main.py --test --skip-fetch
```

**输出**: `check-trend-bottom/output/` 下的 CSV 和 HTML 报告。

### 模块 B：check-steady-uptrend (稳步上升)

**目录**: `check-steady-uptrend/`

**功能**: 识别稳步上升、趋势跟随、波动收缩突破信号。

```bash
cd check-steady-uptrend

# 运行完整分析 (使用本地数据)
python main.py --skip-fetch

# 仅生成报告 (如果已有分析结果)
python main.py --only-report
```

**输出**: `check-steady-uptrend/output/` 下的 CSV、Markdown 和 HTML 报告。

---

## 三、第三步：结果对比

**工具**: `compare_modules.py`

**功能**: 自动对比 TD九底 和 稳步上升 的筛选结果，找出重合的股票。

```bash
# 在根目录运行
python compare_modules.py
```

**输出**: `comparison_results/` 目录下的 Markdown 和 HTML 报告。

---

## 四、常见问题

### Q1: 数据不足或报错？
请确保先运行了 `get-data/main.py` 并且成功获取了数据。

### Q2: 如何更新数据？
每天收盘后，进入 `get-data` 目录运行 `python main.py --all` 即可增量更新数据。

### Q3: 报告在哪里？
- TD分析报告: `check-trend-bottom/output/`
- 趋势分析报告: `check-steady-uptrend/output/`
