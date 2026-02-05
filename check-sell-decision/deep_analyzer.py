#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度卖出分析系统
提供详细的技术面分析，包括：
- 震荡vs趋势判断
- MACD历史追踪
- 顶背离/底背离检测
- 成交量分析
- 均线系统分析
"""

import numpy as np
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class DeepSellAnalyzer:
    """深度卖出分析器"""

    def __init__(self):
        pass

    def analyze(self, stock_code):
        """深度分析股票"""
        print(f"\n{'='*80}")
        print(f"{' '*25}深度卖出分析报告")
        print(f"{'='*80}\n")
        print(f"股票代码: {stock_code}")

        try:
            # 1. 获取数据
            df = self._fetch_data(stock_code)
            if df is None or len(df) < 60:
                print("❌ 数据不足，无法分析")
                return

            # 2. 计算所有指标
            indicators = self._calculate_indicators(df)

            # 3. 打印报告
            self._print_report(stock_code, df, indicators)

        except Exception as e:
            print(f"❌ 分析出错: {e}")

    def _fetch_data(self, stock_code):
        """获取股票数据"""
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')

            print(f"📥 正在获取数据...")
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )

            if df is None or len(df) == 0:
                return None

            # 重命名列
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount'
            })

            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

            print(f"✅ 获取到 {len(df)} 条数据")
            return df

        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            return None

    def _calculate_indicators(self, df):
        """计算所有技术指标"""
        # 均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()

        # MACD
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['dif'] = exp12 - exp26
        df['dea'] = df['dif'].ewm(span=9, adjust=False).mean()
        df['macd'] = (df['dif'] - df['dea']) * 2

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # KDJ
        low_min = df['low'].rolling(9).min()
        high_max = df['high'].rolling(9).max()
        df['rsv'] = (df['close'] - low_min) / (high_max - low_min) * 100
        df['k'] = df['rsv'].ewm(com=2, adjust=False).mean()
        df['d'] = df['k'].ewm(com=2, adjust=False).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']

        # 布林带
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']

        # 波动率
        df['volatility'] = df['close'].pct_change().rolling(10).std() * np.sqrt(252) * 100

        # 振幅
        df['amplitude'] = (df['high'] - df['low']) / df['close'] * 100

        return df

    def _print_report(self, stock_code, df, indicators):
        """打印深度分析报告"""

        # 基本信息
        latest = df.iloc[-1]
        print(f"\n当前价格: {latest['close']:.2f}")
        print(f"今日涨跌: {latest['涨跌幅']:+.2f}%")
        print(f"成交额: {latest['成交额']/100000000:.2f}亿")

        # 分区报告
        self._print_ma_analysis(df)
        self._print_macd_analysis(df)
        self._print_oscillation_analysis(df)
        self._print_volume_analysis(df)
        self._print_divergence_analysis(df)
        self._print_rsi_kdj_analysis(df)
        self._print_summary(df)

    def _print_ma_analysis(self, df):
        """均线分析"""
        print(f"\n{'─'*80}")
        print("📈 一、均线系统分析")
        print(f"{'─'*80}")

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        ma5 = df['ma5'].iloc[-1]
        ma20 = df['ma20'].iloc[-1]
        ma60 = df['ma60'].iloc[-1]

        print(f"\n当前状态：")
        print(f"  收盘价: {latest['close']:.2f}")
        print(f"  MA5:   {ma5:.2f}")
        print(f"  MA20:  {ma20:.2f}")
        print(f"  MA60:  {ma60:.2f}")

        print(f"\n均线关系：")
        if latest['close'] > ma5 > ma20 > ma60:
            print(f"  ✅ 完美多头排列（收盘>MA5>MA20>MA60）")
        elif latest['close'] < ma5 < ma20 < ma60:
            print(f"  ❌ 完美空头排列（收盘<MA5<MA20<MA60）")
        elif ma5 < ma20:
            print(f"  ⚠️ MA5 < MA20（死叉）")
        else:
            print(f"  ✅ MA5 > MA20（金叉）")

        # 死叉/金叉检测
        if prev['ma5'] > prev['ma20'] and ma5 < ma20:
            print(f"  ❌ MA5今日下穿MA20（刚形成死叉）")
        elif prev['ma5'] < prev['ma20'] and ma5 > ma20:
            print(f"  ✅ MA5今日上穿MA20（刚形成金叉）")

        # 突破MA60
        if latest['close'] < ma60:
            print(f"  ❌ 跌破MA60生命线（{ma60:.2f}）")
        else:
            print(f"  ✅ 站稳MA60上方（{ma60:.2f}）")

        # 均线斜率
        ma20_slope = (ma20 - df['ma20'].iloc[-11]) / df['ma20'].iloc[-11] * 100
        ma60_slope = (ma60 - df['ma60'].iloc[-11]) / df['ma60'].iloc[-11] * 100

        print(f"\n均线斜率（10日）：")
        print(f"  MA20: {ma20_slope:+.2f}%")
        print(f"  MA60: {ma60_slope:+.2f}%")

        if abs(ma20_slope) < 2 and abs(ma60_slope) < 2:
            print(f"  → 均线走平，震荡行情")
        elif ma20_slope > 0 and ma60_slope > 0:
            print(f"  → 均线向上，上升趋势")
        else:
            print(f"  → 均线向下，下降趋势")

    def _print_macd_analysis(self, df):
        """MACD分析"""
        print(f"\n{'─'*80}")
        print("📊 二、MACD分析")
        print(f"{'─'*80}")

        print(f"\n最近10天MACD变化：")
        print(f"{'日期':>10} {'收盘':>8} {'DIF':>8} {'DEA':>8} {'MACD柱':>8} {'状态':>12}")
        print("─"*80)

        for i in range(-10, 0):
            date = df['date'].iloc[i]
            close = df['close'].iloc[i]
            dif = df['dif'].iloc[i]
            dea = df['dea'].iloc[i]
            macd_val = df['macd'].iloc[i]

            if i > -10:
                prev_macd = df['macd'].iloc[i-1]
                if prev_macd >= 0 and macd_val < 0:
                    status = "❌由红转绿"
                elif prev_macd < 0 and macd_val >= 0:
                    status = "✅由绿转红"
                elif macd_val < 0:
                    status = "⚠️绿柱"
                else:
                    status = "✅红柱"
            else:
                status = ""

            print(f"{date.strftime('%m/%d'):>10} {close:>8.2f} {dif:>8.3f} {dea:>8.3f} {macd_val:>8.3f} {status:>12}")

        # MACD状态判断
        current_macd = df['macd'].iloc[-1]

        print(f"\nMACD当前状态：")
        if current_macd > 0:
            print(f"  ✅ MACD红柱运行（{current_macd:.3f}）")
        else:
            print(f"  ⚠️ MACD绿柱运行（{current_macd:.3f}）")

        # 死叉/金叉
        if df['dif'].iloc[-2] > df['dea'].iloc[-2] and df['dif'].iloc[-1] < df['dea'].iloc[-1]:
            print(f"  ❌ DIF下穿DEA（MACD死叉）")
        elif df['dif'].iloc[-2] < df['dea'].iloc[-2] and df['dif'].iloc[-1] > df['dea'].iloc[-1]:
            print(f"  ✅ DIF上穿DEA（MACD金叉）")

        # 绿柱持续时间
        green_days = 0
        for i in range(-1, -30, -1):
            if df['macd'].iloc[i] < 0:
                green_days += 1
            else:
                break

        if green_days > 0:
            print(f"  ⚠️ MACD绿柱已持续{green_days}天")
            if green_days > 5:
                print(f"     → 绿柱超过5天，下跌趋势确认")
            else:
                print(f"     → 绿柱{green_days}天，可能是调整")

    def _print_oscillation_analysis(self, df):
        """震荡分析"""
        print(f"\n{'─'*80}")
        print("📉 三、震荡vs趋势判断")
        print(f"{'─'*80}")

        # 价格区间
        recent_60 = df.tail(60)
        high_60 = recent_60['close'].max()
        low_60 = recent_60['close'].min()
        current = df['close'].iloc[-1]

        print(f"\n近60日价格区间：")
        print(f"  最高价: {high_60:.2f}")
        print(f"  最低价: {low_60:.2f}")
        print(f"  当前价: {current:.2f}")
        position = (current - low_60) / (high_60 - low_60) * 100
        print(f"  区间位置: {position:.1f}%")

        # 20日涨跌
        recent_20 = df.tail(20)
        total_change_20 = (recent_20['close'].iloc[-1] - recent_20['close'].iloc[0]) / recent_20['close'].iloc[0] * 100
        print(f"\n近20日总涨跌: {total_change_20:+.2f}%")

        # 波动率
        current_vol = df['volatility'].iloc[-1]
        avg_vol = df['volatility'].iloc[-60:].mean()
        print(f"\n波动率：")
        print(f"  当前: {current_vol:.2f}%")
        print(f"  60日均值: {avg_vol:.2f}%")

        # 综合判断
        震荡信号 = 0
        趋势信号 = 0

        ma20_slope = (df['ma20'].iloc[-1] - df['ma20'].iloc[-11]) / df['ma20'].iloc[-11] * 100
        ma60_slope = (df['ma60'].iloc[-1] - df['ma60'].iloc[-11]) / df['ma60'].iloc[-11] * 100

        if abs(ma20_slope) < 2:
            震荡信号 += 1
        else:
            趋势信号 += 1

        if abs(ma60_slope) < 2:
            震荡信号 += 1
        else:
            趋势信号 += 1

        if abs(total_change_20) < 10:
            震荡信号 += 1
        else:
            趋势信号 += 1

        # 日内振幅
        avg_amplitude = df.tail(10)['amplitude'].mean()
        if avg_amplitude < 4:
            震荡信号 += 1
        else:
            趋势信号 += 1

        print(f"\n震荡信号: {震荡信号}, 趋势信号: {趋势信号}")

        print(f"\n结论：")
        if 震荡信号 >= 3:
            print(f"  ✅ 震荡行情")
            print(f"     震荡区间: {low_60:.2f} - {high_60:.2f}")
            print(f"     中轴: {(high_60 + low_60)/2:.2f}")
            print(f"     策略: 支撑位低吸，压力位高抛")
        elif 趋势信号 >= 3:
            if current > df['ma60'].iloc[-1]:
                print(f"  ✅ 上升趋势")
                print(f"     策略: 回调低吸，持股待涨")
            else:
                print(f"  ❌ 下降趋势")
                print(f"     策略: 反弹减仓，不要抄底")
        else:
            print(f"  ⚠️ 方向不明，观望为主")

    def _print_volume_analysis(self, df):
        """成交量分析"""
        print(f"\n{'─'*80}")
        print("📊 四、成交量分析")
        print(f"{'─'*80}")

        latest = df.iloc[-1]
        avg_vol_20 = df['volume'].rolling(20).mean().iloc[-1]
        avg_vol_60 = df['volume'].rolling(60).mean().iloc[-1]

        vol_ratio_20 = latest['volume'] / avg_vol_20
        vol_ratio_60 = latest['volume'] / avg_vol_60

        print(f"\n今日成交量: {latest['volume']:.0f}")
        print(f"20日均值: {avg_vol_20:.0f} (量比: {vol_ratio_20:.2f}倍)")
        print(f"60日均值: {avg_vol_60:.0f} (量比: {vol_ratio_60:.2f}倍)")

        print(f"\n量价关系：")
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]

        if price_change > 0.03 and vol_ratio_20 > 2:
            print(f"  ✅ 放量上涨（健康）")
        elif price_change > 0.03 and vol_ratio_20 < 1:
            print(f"  ⚠️ 缩量上涨（量价背离，谨慎）")
        elif price_change < -0.03 and vol_ratio_20 > 2:
            print(f"  ❌ 放量下跌（恐慌抛售）")
        elif price_change < -0.03 and vol_ratio_20 < 1:
            print(f"  ⚠️ 缩量下跌（可能未止跌）")
        else:
            print(f"  ✅ 量价配合正常")

    def _print_divergence_analysis(self, df):
        """背离分析"""
        print(f"\n{'─'*80}")
        print("🔄 五、顶背离/底背离检测")
        print(f"{'─'*80}")

        # 检查最近20天
        recent_20 = df.tail(20)
        current_price = df['close'].iloc[-1]
        current_macd = df['macd'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]

        # 找前期高点（10天前）
        prev_20 = recent_20.iloc[:-10]
        if len(prev_20) > 0:
            prev_high = prev_20['close'].max()
            prev_high_idx = prev_20['close'].idxmax()
            prev_macd_at_high = df.loc[prev_high_idx, 'macd']
            prev_rsi_at_high = df.loc[prev_high_idx, 'rsi']

            print(f"\n价格对比：")
            print(f"  当前价: {current_price:.2f}")
            print(f"  10日前高点: {prev_high:.2f}")

            if current_price > prev_high:
                print(f"  ✅ 价格创新高")

                print(f"\nMACD对比：")
                print(f"  当前MACD: {current_macd:.3f}")
                print(f"  前高点MACD: {prev_macd_at_high:.3f}")

                if current_macd < prev_macd_at_high:
                    print(f"  ❌ 顶背离！价格创新高但MACD未创新高")
                    print(f"     → 这是危险信号，可能即将见顶")

                print(f"\nRSI对比：")
                print(f"  当前RSI: {current_rsi:.2f}")
                print(f"  前高点RSI: {prev_rsi_at_high:.2f}")

                if current_rsi < prev_rsi_at_high:
                    print(f"  ❌ 顶背离！RSI未确认价格新高")

            elif current_price < prev_high:
                print(f"  ⚠️ 价格未创新高")

    def _print_rsi_kdj_analysis(self, df):
        """RSI和KDJ分析"""
        print(f"\n{'─'*80}")
        print("📊 六、RSI与KDJ分析")
        print(f"{'─'*80}")

        # RSI
        current_rsi = df['rsi'].iloc[-1]
        print(f"\nRSI(14): {current_rsi:.2f}")

        if current_rsi > 80:
            print(f"  ❌ 严重超买（>80），可能回落")
        elif current_rsi > 70:
            print(f"  ⚠️ 超买（>70），注意风险")
        elif current_rsi < 20:
            print(f"  ✅ 严重超卖（<20），可能反弹")
        elif current_rsi < 30:
            print(f"  ⚠️ 超卖（<30），关注反弹机会")
        else:
            print(f"  ✅ RSI正常（30-70）")

        # KDJ
        k = df['k'].iloc[-1]
        d = df['d'].iloc[-1]
        j = df['j'].iloc[-1]

        print(f"\nKDJ:")
        print(f"  K: {k:.2f}")
        print(f"  D: {d:.2f}")
        print(f"  J: {j:.2f}")

        if k > 80 and d > 80:
            print(f"  ❌ KDJ高位超买")
        elif k < 20 and d < 20:
            print(f"  ✅ KDJ低位超卖")

        # KDJ死叉/金叉
        if df['k'].iloc[-2] > df['d'].iloc[-2] and k < d:
            if k > 80:
                print(f"  ❌ KDJ高位死叉（危险）")
            else:
                print(f"  ⚠️ KDJ死叉")
        elif df['k'].iloc[-2] < df['d'].iloc[-2] and k > d:
            if k < 20:
                print(f"  ✅ KDJ低位金叉（买入信号）")
            else:
                print(f"  ✅ KDJ金叉")

    def _print_summary(self, df):
        """综合总结"""
        print(f"\n{'='*80}")
        print("📋 七、综合总结")
        print(f"{'='*80}")

        latest = df.iloc[-1]
        ma5 = df['ma5'].iloc[-1]
        ma20 = df['ma20'].iloc[-1]
        ma60 = df['ma60'].iloc[-1]
        macd = df['macd'].iloc[-1]
        rsi = df['rsi'].iloc[-1]

        # 风险信号统计
        risk_signals = 0

        print(f"\n风险信号检查：")

        # 均线
        if ma5 < ma20:
            print(f"  ⚠️ MA死叉")
            risk_signals += 1
        else:
            print(f"  ✅ MA多头")

        # MACD
        if macd < 0:
            print(f"  ⚠️ MACD绿柱")
            risk_signals += 1
        else:
            print(f"  ✅ MACD红柱")

        # RSI
        if rsi > 70:
            print(f"  ⚠️ RSI超买")
            risk_signals += 1
        else:
            print(f"  ✅ RSI正常")

        # MA60
        if latest['close'] < ma60:
            print(f"  ⚠️ 跌破MA60")
            risk_signals += 1
        else:
            print(f"  ✅ 站稳MA60")

        print(f"\n风险信号数量: {risk_signals}/4")

        # 操作建议
        print(f"\n💡 操作建议：")

        if risk_signals >= 3:
            print(f"  🔴 高风险")
            print(f"     建议：减仓或止损")
            print(f"     仓位：控制在30%以下")
        elif risk_signals == 2:
            print(f"  🟠 中高风险")
            print(f"     建议：适度减仓")
            print(f"     仓位：控制在50%以下")
        elif risk_signals == 1:
            print(f"  🟡 中等风险")
            print(f"     建议：持有观望")
            print(f"     仓位：可保持60-70%")
        else:
            print(f"  🟢 低风险")
            print(f"     建议：继续持有")
            print(f"     仓位：可保持80-100%")

        # 关键点位
        recent_60 = df.tail(60)
        high_60 = recent_60['close'].max()
        low_60 = recent_60['close'].min()

        print(f"\n📍 关键点位：")
        print(f"  压力位: {high_60:.2f}（近60日高点）")
        print(f"  支撑位: {low_60:.2f}（近60日低点）")
        print(f"  MA60: {ma60:.2f}")
        print(f"  当前: {latest['close']:.2f}")

        print(f"\n{'='*80}\n")


def main():
    """主函数"""
    print("\n" + "="*80)
    print(" "*25 + "深度卖出分析系统")
    print("="*80)

    # 获取股票代码
    stock_code = input("\n请输入股票代码（如 600000）: ").strip()

    if not stock_code:
        print("❌ 股票代码不能为空")
        return

    # 创建分析器并分析
    analyzer = DeepSellAnalyzer()
    analyzer.analyze(stock_code)


if __name__ == '__main__':
    main()
