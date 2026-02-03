"""
TD Sequential (九底) 核心算法实现
参考 Tom DeMark 的 TD Sequential 指标
"""
import pandas as pd
import numpy as np


def calculate_td_sequence(close_prices: pd.Series) -> dict:
    """
    计算TD序列（九底/九顶）

    参数:
        close_prices: 收盘价序列 (pd.Series)

    返回:
        {
            'buy_sequence': TD买入序列（九底）列表,
            'sell_sequence': TD卖出序列（九顶）列表,
            'current_buy': 当前买入序列值,
            'current_sell': 当前卖出序列值,
            'is_buy_setup': 是否完成买入设置(九底),
            'is_sell_setup': 是否完成卖出设置(九顶)
        }
    """
    if len(close_prices) < 5:
        return {
            'buy_sequence': [],
            'sell_sequence': [],
            'current_buy': 0,
            'current_sell': 0,
            'is_buy_setup': False,
            'is_sell_setup': False
        }

    # 初始化结果数组
    buy_sequence = [0] * len(close_prices)
    sell_sequence = [0] * len(close_prices)

    # 当前计数器
    buy_count = 0
    sell_count = 0

    for i in range(4, len(close_prices)):
        # TD买入设置（九底）：收盘价低于4根K线前的收盘价
        if close_prices.iloc[i] < close_prices.iloc[i-4]:
            buy_count += 1
            if buy_count > 9:  # 超过9后重置为1（进入新的设置）
                buy_count = 1
        else:
            buy_count = 0

        # TD卖出设置（九顶）：收盘价高于4根K线前的收盘价
        if close_prices.iloc[i] > close_prices.iloc[i-4]:
            sell_count += 1
            if sell_count > 13:  # TD卖出设置通常到13
                sell_count = 1
        else:
            sell_count = 0

        buy_sequence[i] = buy_count
        sell_sequence[i] = sell_count

    # 当前状态
    current_buy = buy_sequence[-1] if buy_sequence else 0
    current_sell = sell_sequence[-1] if sell_sequence else 0

    return {
        'buy_sequence': buy_sequence,
        'sell_sequence': sell_sequence,
        'current_buy': current_buy,
        'current_sell': current_sell,
        'is_buy_setup': current_buy >= 9,  # 达到或超过9即为九底
        'is_sell_setup': current_sell >= 13
    }


def get_td_signal_info(df: pd.DataFrame, price_col='close') -> dict:
    """
    获取K线数据的TD信号信息

    参数:
        df: K线数据DataFrame
        price_col: 价格列名

    返回:
        TD信号字典
    """
    if df is None or len(df) == 0:
        return None

    close_prices = df[price_col]
    result = calculate_td_sequence(close_prices)

    # 添加额外信息
    result['latest_close'] = close_prices.iloc[-1]
    result['latest_date'] = df.index[-1] if isinstance(df.index, pd.DatetimeIndex) else df['date'].iloc[-1]

    # 找到历史九底位置
    buy_seq_array = np.array(result['buy_sequence'])
    jiudi_positions = np.where(buy_seq_array >= 9)[0]

    if len(jiudi_positions) > 0:
        last_jiudi_idx = jiudi_positions[-1]
        result['last_jiudi_date'] = df.index[last_jiudi_idx] if isinstance(df.index, pd.DatetimeIndex) else df['date'].iloc[last_jiudi_idx]
        result['last_jiudi_price'] = close_prices.iloc[last_jiudi_idx]
        result['last_jiudi_count'] = buy_seq_array[last_jiudi_idx]
    else:
        result['last_jiudi_date'] = None
        result['last_jiudi_price'] = None
        result['last_jiudi_count'] = 0

    return result


def analyze_resonance(daily_signal: dict, weekly_signal: dict, monthly_signal: dict) -> dict:
    """
    分析三周期共振情况

    参数:
        daily_signal: 日K TD信号
        weekly_signal: 周K TD信号
        monthly_signal: 月K TD信号

    返回:
        共振分析结果
    """
    if not all([daily_signal, weekly_signal, monthly_signal]):
        return {
            'is_resonance': False,
            'reason': '数据不完整'
        }

    daily_count = daily_signal['current_buy']
    weekly_count = weekly_signal['current_buy']
    monthly_count = monthly_signal['current_buy']

    # 判断是否三周期九底共振
    is_resonance = (daily_count >= 9 and weekly_count >= 9 and monthly_count >= 9)

    # 判断接近共振（至少两个周期达到九底）
    jiudi_cycles = sum([
        daily_count >= 9,
        weekly_count >= 9,
        monthly_count >= 9
    ])

    resonance_level = '无共振'
    if is_resonance:
        resonance_level = '🔥 完美共振（三周期九底）'
    elif jiudi_cycles == 2:
        resonance_level = '⚡ 双周期共振'
    elif jiudi_cycles == 1:
        resonance_level = '⚠️ 单周期九底'

    return {
        'is_resonance': is_resonance,
        'resonance_level': resonance_level,
        'jiudi_cycles': jiudi_cycles,
        'daily_count': daily_count,
        'weekly_count': weekly_count,
        'monthly_count': monthly_count,
        'daily_valid': daily_count >= 9,
        'weekly_valid': weekly_count >= 9,
        'monthly_valid': monthly_count >= 9
    }


if __name__ == '__main__':
    # 测试代码
    import pandas as pd

    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=50, freq='D')
    # 模拟下跌趋势（生成九底）
    prices = [100]
    for i in range(1, 50):
        if i % 5 == 0:  # 每5天下跌
            prices.append(prices[-1] * 0.98)
        else:
            prices.append(prices[-1])

    df = pd.DataFrame({'close': prices}, index=dates)

    result = get_td_signal_info(df)
    print(f"当前买入序列: {result['current_buy']}")
    print(f"是否九底: {result['is_buy_setup']}")
    print(f"历史九底位置: {result['last_jiudi_date']}")
