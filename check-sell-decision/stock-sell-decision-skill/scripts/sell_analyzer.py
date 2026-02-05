#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能卖出分析系统
输入股票代码，给出卖出建议
"""

import numpy as np
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class SellAnalyzer:
    """卖出信号分析器"""

    def __init__(self, mode='standard'):
        """
        mode: 交易模式
            - conservative: 保守（信号非常明确才卖）
            - standard: 标准
            - aggressive: 激进（稍有信号就卖）
        """
        self.mode = mode
        self.temperature = self._get_temperature(mode)

        # 指标权重
        self.weights = {
            'ma_cross': 2.0,          # MA死叉
            'macd': 1.8,              # MACD
            'rsi': 1.5,               # RSI超买
            'kdj': 1.3,               # KDJ
            'bollinger': 1.2,         # 布林带
            'volume_price': 1.6,      # 量价关系
        }

    def _get_temperature(self, mode):
        """温度参数：控制灵敏度"""
        temps = {
            'conservative': 0.5,
            'standard': 1.0,
            'aggressive': 2.0
        }
        return temps.get(mode, 1.0)

    def analyze(self, stock_code):
        """分析股票是否应该卖出"""
        print(f"\n{'='*60}")
        print(f"正在分析股票: {stock_code}")
        print(f"{'='*60}\n")

        try:
            # 1. 获取数据
            stock_data = self._fetch_stock_data(stock_code)
            if stock_data is None or len(stock_data) < 60:
                print("❌ 数据不足，无法分析")
                return None

            # 2. 计算各个指标得分
            scores = self._calculate_all_scores(stock_data)

            # 3. Softmax融合
            sell_prob = self._softmax_fusion(scores)

            # 4. 生成报告
            report = self._generate_report(stock_code, stock_data, scores, sell_prob)

            return report

        except Exception as e:
            print(f"❌ 分析出错: {e}")
            return None

    def _fetch_stock_data(self, stock_code):
        """获取股票历史数据"""
        try:
            # 判断市场
            if stock_code.startswith('6'):
                symbol = f"sh{stock_code}"
            else:
                symbol = f"sz{stock_code}"

            # 获取最近300天数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

            print("📥 正在获取数据...")
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )

            if df is None or len(df) == 0:
                print("❌ 未获取到数据")
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
            print(f"   数据范围: {df['date'].iloc[0].strftime('%Y-%m-%d')} 至 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")

            return df

        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            return None

    def _calculate_all_scores(self, df):
        """计算所有指标得分"""
        scores = {}

        # 1. MA死叉信号
        scores['ma_cross'] = self._ma_cross_score(df)

        # 2. MACD信号
        scores['macd'] = self._macd_score(df)

        # 3. RSI信号
        scores['rsi'] = self._rsi_score(df)

        # 4. KDJ信号
        scores['kdj'] = self._kdj_score(df)

        # 5. 布林带信号
        scores['bollinger'] = self._bollinger_score(df)

        # 6. 量价关系
        scores['volume_price'] = self._volume_price_score(df)

        return scores

    def _ma_cross_score(self, df):
        """MA死叉评分"""
        ma5 = df['close'].rolling(5).mean()
        ma10 = df['close'].rolling(10).mean()
        ma20 = df['close'].rolling(20).mean()
        ma60 = df['close'].rolling(60).mean()

        current = df['close'].iloc[-1]
        current_ma5 = ma5.iloc[-1]
        current_ma20 = ma20.iloc[-1]
        current_ma60 = ma60.iloc[-1]

        prev_ma5 = ma5.iloc[-2]
        prev_ma20 = ma20.iloc[-2]

        score = 0
        reasons = []

        # 死叉判断
        if prev_ma5 > prev_ma20 and current_ma5 < current_ma20:
            score += 8
            reasons.append("5日线刚下穿20日线（死叉）")
        elif current_ma5 < current_ma20:
            score += 5
            reasons.append("5日线下方运行")

        # 跌破重要均线
        if current < current_ma60:
            score += 4
            reasons.append("跌破60日生命线")

        # 均线空头排列
        if current_ma5 < current_ma20 < current_ma60:
            score += 3
            reasons.append("均线空头排列")

        return min(score, 10)

    def _macd_score(self, df):
        """MACD评分"""
        # 计算MACD
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        dif = exp12 - exp26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = (dif - dea) * 2

        current_macd = macd.iloc[-1]
        prev_macd = macd.iloc[-2]
        current_dif = dif.iloc[-1]
        current_dea = dea.iloc[-1]
        prev_dif = dif.iloc[-2]
        prev_dea = dea.iloc[-2]

        score = 0

        # DIF死叉DEA
        if prev_dif > prev_dea and current_dif < current_dea:
            score += 8
        elif current_dif < current_dea:
            score += 5

        # 柱状图由红转绿
        if prev_macd >= 0 and current_macd < 0:
            score += 7
        elif current_macd < 0:
            score += 4

        # 顶背离（简化判断）
        if (df['close'].iloc[-1] > df['close'].iloc[-5] and
            current_dif < dif.iloc[-5]):
            score += 6

        return min(score, 10)

    def _rsi_score(self, df):
        """RSI评分"""
        # 计算RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        score = 0

        # 超买判断
        if current_rsi > 80:
            score = 9
        elif current_rsi > 75:
            score = 7
        elif current_rsi > 70:
            score = 5
        elif current_rsi > 60:
            score = 2

        # 顶背离
        if (current_rsi < rsi.iloc[-5] and
            df['close'].iloc[-1] > df['close'].iloc[-5]):
            score += 4

        return min(score, 10)

    def _kdj_score(self, df):
        """KDJ评分"""
        # 计算KDJ
        low_min = df['low'].rolling(9).min()
        high_max = df['high'].rolling(9).max()

        rsv = (df['close'] - low_min) / (high_max - low_min) * 100

        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d

        current_k = k.iloc[-1]
        current_d = d.iloc[-1]
        current_j = j.iloc[-1]
        prev_k = k.iloc[-2]
        prev_d = d.iloc[-2]

        score = 0

        # KDJ高位死叉
        if prev_k > prev_d and current_k < current_d:
            if current_k > 80:
                score += 9
            elif current_k > 70:
                score += 6
            else:
                score += 3

        # 超买
        if current_k > 90:
            score += 4
        elif current_k > 80:
            score += 2

        # J值过高
        if current_j > 100:
            score += 3

        return min(score, 10)

    def _bollinger_score(self, df):
        """布林带评分"""
        # 计算布林带
        ma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()

        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20

        current = df['close'].iloc[-1]
        current_upper = upper.iloc[-1]
        current_ma20 = ma20.iloc[-1]
        prev_upper = upper.iloc[-2]

        score = 0

        # 触及上轨
        if current >= current_upper * 0.99:
            score += 7
        elif current > current_ma20 + (current_upper - current_ma20) * 0.8:
            score += 4

        # 从上轨回落
        if df['close'].iloc[-2] >= prev_upper and current < current_upper:
            score += 6

        # 开口异常放大
        bandwidth = (upper.iloc[-1] - lower.iloc[-1]) / ma20.iloc[-1]
        if bandwidth > 0.15:  # 开口过大
            score += 3

        return min(score, 10)

    def _volume_price_score(self, df):
        """量价关系评分"""
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        prev_close = df['close'].iloc[-2]
        current_close = df['close'].iloc[-1]

        price_change = (current_close - prev_close) / prev_close
        volume_ratio = current_volume / avg_volume

        score = 0

        # 放量下跌
        if price_change < -0.03:
            if volume_ratio > 2.5:
                score += 10
            elif volume_ratio > 2.0:
                score += 8
            elif volume_ratio > 1.5:
                score += 5

        # 量价背离
        elif price_change > 0:
            if volume_ratio < 0.7:
                score += 6  # 价涨量缩

        # 高位放量滞涨
        if (price_change > 0 and price_change < 0.02 and
            volume_ratio > 2.0):
            score += 5

        return min(score, 10)

    def _softmax_fusion(self, scores):
        """Softmax融合计算卖出概率"""
        # 计算加权得分
        weighted_sum = sum(
            scores[key] * self.weights[key]
            for key in scores.keys()
        )

        # 计算最大可能的加权得分
        max_possible = sum(
            10.0 * self.weights[key]
            for key in scores.keys()
        )

        # 基准线（持有强度）：使用最大得分的25%作为基准
        # 降低基准线，使系统更敏感
        hold_baseline = max_possible * 0.25

        # Softmax转换
        probs = self._softmax([weighted_sum, hold_baseline], self.temperature)

        return probs[0]

    def _softmax(self, x, temperature=1.0):
        """Softmax函数"""
        x = np.array(x) / temperature
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    def _generate_report(self, stock_code, df, scores, sell_prob):
        """生成分析报告"""

        # 获取基本信息
        current_price = df['close'].iloc[-1]
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]

        report = {
            'stock_code': stock_code,
            'current_price': current_price,
            'price_change': price_change,
            'sell_probability': sell_prob,
            'scores': scores,
            'mode': self.mode
        }

        # 打印报告
        self._print_report(report)

        return report

    def _print_report(self, report):
        """打印可视化报告"""

        print(f"\n{'='*60}")
        print(f"📊 卖出分析报告")
        print(f"{'='*60}\n")

        # 基本信息
        print(f"股票代码: {report['stock_code']}")
        print(f"当前价格: {report['current_price']:.2f}")
        print(f"今日涨跌: {report['price_change']:+.2%}")
        print(f"交易模式: {self._get_mode_name()}")
        print(f"\n{'─'*60}\n")

        # 指标得分
        print("📈 技术指标得分 (0-10分, 分数越高风险越大)")
        print(f"{'─'*60}")

        indicators = {
            'ma_cross': '均线死叉',
            'macd': 'MACD',
            'rsi': 'RSI超买',
            'kdj': 'KDJ',
            'bollinger': '布林带',
            'volume_price': '量价关系'
        }

        for key, name in indicators.items():
            score = report['scores'][key]
            weight = self.weights[key]
            bar = self._get_score_bar(score)
            print(f"{name:8s} | {score:2.0f}/10 | 权重{weight:.1f} | {bar}")

        print(f"{'─'*60}\n")

        # 卖出概率
        sell_prob = report['sell_probability']
        print(f"🎯 综合卖出概率: {sell_prob:.1%}")

        # 概率条
        prob_bar = self._get_probability_bar(sell_prob)
        print(f"   {prob_bar}")

        print(f"\n{'─'*60}\n")

        # 操作建议
        action, risk_level = self._get_action(sell_prob)

        print(f"⚡ 风险等级: {risk_level}")
        print(f"💡 操作建议: {action}")

        print(f"\n{'='*60}\n")

    def _get_score_bar(self, score):
        """生成得分条"""
        filled = int(score / 2)
        bar = '█' * filled + '░' * (5 - filled)
        return bar

    def _get_probability_bar(self, prob):
        """生成概率条"""
        filled = int(prob * 30)
        bar = '█' * filled + '░' * (30 - filled)
        return f"[{bar}]"

    def _get_action(self, sell_prob):
        """获取操作建议"""
        if sell_prob > 0.85:
            return "强烈建议卖出 / 减仓至30%以下", "🔴 极高风险"
        elif sell_prob > 0.70:
            return "建议卖出 / 减仓至50%以下", "🟠 高风险"
        elif sell_prob > 0.55:
            return "考虑减仓 / 设置止损", "🟡 中等风险"
        elif sell_prob > 0.40:
            return "持有观望 / 密切关注", "🟢 低风险"
        else:
            return "继续持有 / 趋势良好", "✅ 安全"

    def _get_mode_name(self):
        """获取模式名称"""
        names = {
            'conservative': '保守模式（只在高确定性时卖出）',
            'standard': '标准模式',
            'aggressive': '激进模式（稍有风险即卖出）'
        }
        return names.get(self.mode, self.mode)


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  智能卖出分析系统".center(50))
    print("="*60)

    # 获取股票代码
    stock_code = input("\n请输入股票代码（如 600000）: ").strip()

    if not stock_code:
        print("❌ 股票代码不能为空")
        return

    # 选择模式
    print("\n请选择交易模式：")
    print("1. 保守模式（信号非常明确才卖）")
    print("2. 标准模式")
    print("3. 激进模式（稍有风险就卖）")
    print("4. 默认（标准模式）")

    choice = input("\n请选择 [1-4，默认4]: ").strip()

    mode_map = {
        '1': 'conservative',
        '2': 'standard',
        '3': 'aggressive',
        '4': 'standard',
        '': 'standard'
    }

    mode = mode_map.get(choice, 'standard')

    # 创建分析器并分析
    analyzer = SellAnalyzer(mode=mode)
    report = analyzer.analyze(stock_code)

    if report is None:
        print("\n分析失败，请检查股票代码是否正确")
    else:
        print("\n✅ 分析完成！")


if __name__ == '__main__':
    main()
