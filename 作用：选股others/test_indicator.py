# -*- coding: utf-8 -*-
"""
测试技术指标计算
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from technical_indicators import TechnicalIndicators
from data_fetcher import DataFetcher


def test_indicators():
    """测试单个股票的指标计算"""
    print("\n[测试] 技术指标计算\n")

    # 测试股票
    stock_code = '000001'  # 平安银行

    print(f"正在获取 {stock_code} 的数据...")
    fetcher = DataFetcher()
    df = fetcher.get_stock_data_for_analysis(stock_code, days_needed=60)

    if df is None:
        print(f"✗ 获取数据失败")
        return

    print(f"✓ 获取数据成功: {len(df)} 条记录\n")

    # 提取价格和成交量
    close_prices = df['close']
    volumes = df['volume']

    # 计算各项指标
    print("【指标计算结果】\n")

    # 1. 均线金叉
    ma_cross = TechnicalIndicators.check_ma_golden_cross(close_prices)
    print(f"1. 均线金叉 (5日/20日): {'✓ 信号' if ma_cross else '✗ 无信号'}")

    # 2. MACD金叉
    macd_cross = TechnicalIndicators.check_macd_golden_cross(close_prices)
    macd_cross_zero = TechnicalIndicators.check_macd_golden_cross_below_zero(close_prices)
    print(f"2. MACD金叉: {'✓ 信号' if macd_cross else '✗ 无信号'}")
    print(f"   MACD零轴下金叉: {'✓ 信号（更可靠）' if macd_cross_zero else '✗ 无信号'}")

    # 3. RSI超卖拐头
    rsi_turnup = TechnicalIndicators.check_rsi_oversold_turnup(close_prices)
    print(f"3. RSI超卖拐头: {'✓ 信号' if rsi_turnup else '✗ 无信号'}")

    # 4. 放量突破
    volume_breakout = TechnicalIndicators.check_volume_breakout(close_prices, volumes)
    print(f"4. 放量突破: {'✓ 信号' if volume_breakout else '✗ 无信号'}")

    # 5. 所有信号
    print("\n【组合信号】")
    signals = TechnicalIndicators.check_all_signals(close_prices, volumes)
    print(f"信号总数: {signals['signal_count']}/5")

    if signals['signal_count'] > 0:
        print("\n符合条件的信号:")
        if signals['ma_golden_cross']:
            print("  ✓ 均线金叉")
        if signals['macd_golden_cross_below_zero']:
            print("  ✓ MACD零轴下金叉（强）")
        elif signals['macd_golden_cross']:
            print("  ✓ MACD金叉")
        if signals['rsi_oversold_turnup']:
            print("  ✓ RSI超卖拐头")
        if signals['volume_breakout']:
            print("  ✓ 放量突破")
    else:
        print("  当前无买入信号")

    # 显示最新数据
    print("\n【最新数据】")
    latest = df.iloc[-1]
    print(f"日期: {latest['date'].strftime('%Y-%m-%d')}")
    print(f"收盘: {latest['close']:.2f}")
    print(f"涨跌幅: {latest.get('change_pct', 0):.2f}%")
    print(f"成交量: {int(latest['volume']):,}")


if __name__ == '__main__':
    test_indicators()
