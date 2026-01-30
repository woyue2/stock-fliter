# 技术指标计算模块

## 目的
计算各种技术指标，包括均线、MACD、RSI、TD序列等。

## 模块概述
- **职责:** 
  - 计算移动平均线
  - 计算MACD指标
  - 计算RSI指标
  - 计算TD序列指标
  - 提供技术指标信号判断
- **状态:** ✅稳定
- **最后更新:** 2025-01-20

## 规范

### 需求: 技术指标计算
**模块:** technical_indicators
计算各种技术指标，并提供信号判断功能。

#### 场景: 计算均线指标
- 计算5日、10日、20日、30日、60日均线
- 判断均线金叉信号
- 支持自定义参数

#### 场景: 计算MACD指标
- 计算MACD线、信号线、柱状图
- 判断MACD金叉信号
- 判断MACD零轴下金叉信号

#### 场景: 计算RSI指标
- 计算RSI值（默认14天）
- 判断RSI超卖和超买信号
- 判断RSI拐头信号

#### 场景: 计算TD序列
- 计算TD买入序列计数
- 判断TD序列的7底、8底、9底信号
- 支持自定义参数

## API接口

### calculate_moving_averages(df, periods=[5, 10, 20, 30, 60])
**描述:** 计算移动平均线
**输入:** 
- df: 包含close列的数据Frame
- periods: 均线周期列表
**输出:** 包含均线列的数据Frame

### calculate_macd(df, fast_period=12, slow_period=26, signal_period=9)
**描述:** 计算MACD指标
**输入:** 
- df: 包含close列的数据Frame
- fast_period: 快线周期
- slow_period: 慢线周期
- signal_period: 信号线周期
**输出:** 包含MACD指标列的数据Frame

### calculate_rsi(df, period=14)
**描述:** 计算RSI指标
**输入:** 
- df: 包含close列的数据Frame
- period: RSI周期
**输出:** 包含RSI列的数据Frame

### calculate_td_sequential(df)
**描述:** 计算TD序列
**输入:** df: 包含close列的数据Frame
**输出:** 包含TD计数列的数据Frame

## 依赖
- pandas: 数据处理库
- numpy: 数值计算库

## 变更历史
- [202501200000_td_scanner](../../history/2025-01/202501200000_td_scanner/) - 新增TD序列计算功能