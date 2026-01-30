# 股票选股扫描器

> 本文件包含项目级别的核心信息。详细的模块文档见 `modules/` 目录。

---

## 1. 项目概述

### 目标与背景
基于技术指标的A股选股工具，支持多维度扫描和TD序列分析。帮助用户快速筛选符合技术指标条件的股票，提高选股效率。

### 范围
- **范围内:** 
  - 实时股票数据获取
  - 技术指标计算（均线、MACD、RSI、TD序列等）
  - 股票筛选与扫描
  - 结果输出与保存（Excel/CSV）
  - 支持多周期分析（日K、周K、月K）

- **范围外:**
  - 基本面分析
  - 量化交易策略执行
  - 实盘交易功能

### 干系人
- **负责人:** 个人开发者

---

## 2. 模块索引

| 模块名称 | 职责 | 状态 | 文档 |
|---------|------|------|------|
| data_fetcher | 股票数据获取与保存 | ✅稳定 | [data_fetcher.md](modules/data_fetcher.md) |
| technical_indicators | 技术指标计算 | ✅稳定 | [technical_indicators.md](modules/technical_indicators.md) |
| stock_scanner | 综合选股扫描器 | ✅稳定 | [stock_scanner.md](modules/stock_scanner.md) |

---

## 3. 快速链接
- [技术约定](../project.md)
- [架构设计](arch.md)
- [API 手册](api.md)
- [数据模型](data.md)
- [变更历史](../history/index.md)