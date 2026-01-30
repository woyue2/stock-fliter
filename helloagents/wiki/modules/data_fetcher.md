# 数据获取模块

## 目的
负责从akshare API获取股票数据并保存到本地文件。

## 模块概述
- **职责:** 
  - 获取股票列表
  - 获取股票历史K线数据（日K、周K、月K）
  - 数据保存到CSV文件
  - 网络请求失败自动重试
- **状态:** ✅稳定
- **最后更新:** 2025-01-20

## 规范

### 需求: 股票数据获取
**模块:** data_fetcher
从akshare API获取实时股票数据，支持日K、周K、月K三个周期。

#### 场景: 获取股票列表
- 从akshare获取A股所有股票列表
- 保存为CSV文件到data目录
- 包含股票代码和名称信息

#### 场景: 获取股票历史数据
- 根据股票代码和周期获取历史K线数据
- 数据包含开盘价、最高价、最低价、收盘价、成交量
- 自动保存为CSV文件
- 网络请求失败自动重试3次

#### 场景: 数据文件管理
- 自动创建data目录（如不存在）
- 文件名包含时间戳，防止覆盖
- 支持读取已保存的CSV文件

## API接口

### get_stock_list()
**描述:** 获取股票列表
**输入:** 无
**输出:** 股票代码列表

### get_stock_data(stock_code, period='daily')
**描述:** 获取股票历史数据
**输入:** 
- stock_code: 股票代码
- period: 周期（daily/weekly/monthly）
**输出:** pandas DataFrame

### save_stock_data(stock_code, df, period='daily')
**描述:** 保存股票数据到CSV文件
**输入:** 
- stock_code: 股票代码
- df: 数据DataFrame
- period: 周期（daily/weekly/monthly）
**输出:** 无

## 依赖
- akshare: 数据获取库
- pandas: 数据处理库

## 变更历史
- [202501200000_td_scanner](../../history/2025-01/202501200000_td_scanner/) - 新增TD序列扫描器，支持多周期分析