# TD九底分析系统 - 使用指南

## 1. 快速开始

### 环境准备

1. 确保已安装 Python 3.8+
2. 安装依赖包：
```bash
pip install pandas tqdm baostock
```

### 流程概览

1. **获取数据**: 使用 `get-data` 模块获取 A 股日线数据
2. **运行分析**: 使用 `check-trend-bottom` 模块分析数据并生成报告

---

## 2. 第一步：获取数据

所有数据获取逻辑已集中在 `get-data` 模块中。

**工作目录**: `../get-data`

```bash
cd ../get-data
```

### 常用命令

#### 测试运行（获取随机 10 只股票）
```bash
python main.py
```

#### 获取全市场数据（约 5000+ 只股票）
```bash
python main.py --all
```

#### 自定义参数
```bash
python main.py --days 365        # 获取最近 365 天数据
python main.py --sample-size 50  # 随机获取 50 只股票
python main.py --resample        # 重新随机采样
```

**输出文件**:
- 数据文件: `get-data/data/raw/{code}.csv`
- 股票列表: `get-data/data/selected_stocks.csv`

---

## 3. 第二步：运行分析

分析逻辑在 `check-trend-bottom` 模块中，默认使用 `get-data` 获取的数据。

**工作目录**: `../check-trend-bottom`

```bash
cd ../check-trend-bottom
```

### 常用命令

#### 完整分析（推荐）
分析所有已获取数据的股票（需要先在第一步获取数据）。
```bash
python main.py --skip-fetch
```
> **注意**: `--skip-fetch` 参数表示直接使用本地 `raw` 目录的数据，不再尝试联网验证。

#### 测试模式
只分析前 10 只股票，快速验证环境。
```bash
python main.py --test --skip-fetch
```

#### 筛选特定级别
只筛选满足特定共振级别的股票。
```bash
python main.py --level 三周期九底 双周期九底 --skip-fetch
```

#### 其他参数
```bash
python main.py --days 180         # 分析最近 180 天
python main.py --no-html          # 不生成 HTML 报告
python main.py --no-open          # 不自动打开浏览器
```

---

## 4. 输出文件说明

所有输出文件位于 `check-trend-bottom/output/` 目录下。

### 1. 分析结果 (CSV)
**位置**: `output/td_analysis_YYYYMMDD_HHMMSS.csv`

包含详细的指标数据：
- **基本信息**: 代码、名称、板块、行业
- **TD 计数**: 日/周/月当前计数
- **底部状态**: 是否 9 底、8 底、7 底
- **共振级别**: 见下文核心概念

### 2. 统计报告 (Markdown)
**位置**: `output/td_report_YYYYMMDD_HHMMSS.md`

包含市场概览、各级别数量统计。

### 3. HTML 交互报告
**位置**: `output/html_YYYYMMDD_HHMMSS/summary.html`

- 支持点击表头排序
- 点击股票代码跳转东方财富行情页
- 支持本地存储（LocalStorage）记住已读/关注状态

---

## 5. 核心概念与指标说明

### TD 九底序列 (TD Sequential)

Tom DeMark 发明的技术分析指标，用于识别趋势衰竭点。

**核心逻辑**:
- **启动**: 收盘价 < 4 天前的收盘价
- **计数**: 连续满足上述条件，计数 +1
- **完成**: 计数达到 **9**，即为 **TD9 (九底)**，通常意味着下跌动能衰竭，可能反弹。

在本系统中：
- **9 底**: 强烈的底部信号 (计数 = 9)
- **8 底**: 潜在的底部信号 (计数 = 8)
- **7 底**: 关注区域 (计数 = 7)

### 多周期共振 (Resonance)

当不同时间周期（日、周、月）同时出现底部信号时，反转概率更高。本系统定义了以下共振级别：

| 级别 | 描述 | 信号强度 |
| :--- | :--- | :--- |
| **三周期九底** | 日线+周线+月线 同时出现 TD9 | ⭐⭐⭐⭐⭐ (极强) |
| **双周期九底** | 日+周 或 日+月 同时出现 TD9 | ⭐⭐⭐⭐ |
| **单周期九底** | 仅日线出现 TD9 | ⭐⭐⭐ |
| **3周期8底** | 日/周/月均 >= TD8 | ⭐⭐ |

### 交易板块

- **上海主板**: 60 开头
- **深圳主板**: 000/002 开头
- **创业板**: 300/301 开头
- **科创板**: 688 开头
- **北交所**: 8 开头
