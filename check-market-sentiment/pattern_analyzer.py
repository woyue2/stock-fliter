# -*- coding: utf-8 -*-
"""
经典走势形态分析器

识别几种经典的市场走势形态：
1. 高开低走型 - 先上升再下降，整体往下走
2. 低开高走型 - 先下降再上升，整体往上走
3. V型反转 - 低开后反弹，收盘高于开盘
4. 倒V型 - 高开后回落，收盘低于开盘
5. 单边上涨 - 持续走强
6. 单边下跌 - 持续走弱
7. 震荡整理 - 上下波动，收盘接近开盘
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class PatternAnalyzer:
    """经典走势形态分析器"""
    
    # 形态定义的阈值
    THRESHOLD_OPEN = 0.5      # 开盘涨跌幅阈值 (%)
    THRESHOLD_INTRADAY = 0.5  # 日内涨跌幅阈值 (%)
    THRESHOLD_AMPLITUDE = 2.0 # 振幅阈值 (%)
    
    def __init__(self):
        """初始化分析器"""
        self.patterns = {
            'high_open_low_close': '高开低走型',      # 先上升再下降
            'low_open_high_close': '低开高走型',      # 先下降再上升
            'v_reversal': 'V型反转',                  # 低开后强势反弹
            'inverted_v': '倒V型',                    # 高开后大幅回落
            'strong_uptrend': '单边上涨',             # 持续走强
            'strong_downtrend': '单边下跌',           # 持续走弱
            'consolidation': '震荡整理',              # 上下波动
            'flat': '平淡走势',                       # 几乎无波动
        }
    
    def analyze_pattern(self, row: pd.Series) -> Tuple[str, str, Dict]:
        """
        分析单只股票的走势形态
        
        Args:
            row: 包含 open, close, high, low, prev_close 的数据行
        
        Returns:
            (形态代码, 形态名称, 详细指标)
        """
        # 提取数据
        open_price = row['open']
        close_price = row['close']
        high_price = row['high']
        low_price = row['low']
        prev_close = row.get('prev_close', open_price)
        
        # 计算关键指标
        # 1. 开盘涨跌幅 (相对昨收)
        open_change_pct = (open_price - prev_close) / prev_close * 100 if prev_close > 0 else 0
        
        # 2. 日内涨跌幅 (相对开盘)
        intraday_change_pct = (close_price - open_price) / open_price * 100 if open_price > 0 else 0
        
        # 3. 全天涨跌幅 (相对昨收)
        total_change_pct = (close_price - prev_close) / prev_close * 100 if prev_close > 0 else 0
        
        # 4. 振幅
        amplitude = (high_price - low_price) / prev_close * 100 if prev_close > 0 else 0
        
        # 5. 上影线比例 (最高价到收盘价或开盘价的较高者)
        upper_shadow_ratio = (high_price - max(open_price, close_price)) / (high_price - low_price) * 100 if high_price > low_price else 0
        
        # 6. 下影线比例 (最低价到收盘价或开盘价的较低者)
        lower_shadow_ratio = (min(open_price, close_price) - low_price) / (high_price - low_price) * 100 if high_price > low_price else 0
        
        # 7. 实体比例 (开盘到收盘的距离)
        body_ratio = abs(close_price - open_price) / (high_price - low_price) * 100 if high_price > low_price else 0
        
        # 8. 早盘vs午盘价格分析
        # 早盘特征价格：开盘价权重70%，最高价权重30%（早盘通常冲高）
        morning_price = open_price * 0.7 + high_price * 0.3
        
        # 午盘特征价格：收盘价权重70%，最低价权重30%（午盘可能探底）
        afternoon_price = close_price * 0.7 + low_price * 0.3
        
        # 早午盘价格差异（相对昨收）
        morning_vs_afternoon = (morning_price - afternoon_price) / prev_close * 100 if prev_close > 0 else 0
        
        # 判断早盘高还是午盘高
        if morning_vs_afternoon > 0.5:
            session_trend = '早盘高'
        elif morning_vs_afternoon < -0.5:
            session_trend = '午盘高'
        else:
            session_trend = '持平'
        
        # 详细指标
        metrics = {
            'open_change_pct': round(open_change_pct, 2),
            'intraday_change_pct': round(intraday_change_pct, 2),
            'total_change_pct': round(total_change_pct, 2),
            'amplitude': round(amplitude, 2),
            'upper_shadow_ratio': round(upper_shadow_ratio, 2),
            'lower_shadow_ratio': round(lower_shadow_ratio, 2),
            'body_ratio': round(body_ratio, 2),
            'morning_vs_afternoon': round(morning_vs_afternoon, 2),
            'session_trend': session_trend,
        }
        
        # 形态识别逻辑
        pattern_code, pattern_name = self._identify_pattern(
            open_change_pct, intraday_change_pct, total_change_pct,
            amplitude, upper_shadow_ratio, lower_shadow_ratio, body_ratio
        )
        
        return pattern_code, pattern_name, metrics
    
    def _identify_pattern(
        self, 
        open_change: float,
        intraday_change: float,
        total_change: float,
        amplitude: float,
        upper_shadow: float,
        lower_shadow: float,
        body_ratio: float
    ) -> Tuple[str, str]:
        """
        根据指标识别形态
        
        Args:
            open_change: 开盘涨跌幅
            intraday_change: 日内涨跌幅
            total_change: 全天涨跌幅
            amplitude: 振幅
            upper_shadow: 上影线比例
            lower_shadow: 下影线比例
            body_ratio: 实体比例
        
        Returns:
            (形态代码, 形态名称)
        """
        # 优先识别极端形态（V型、倒V型）
        
        # 1. V型反转：低开后强势反弹，收盘明显高于开盘
        #    特征：开盘低，日内涨幅大，下影线长
        if (open_change < -self.THRESHOLD_OPEN and 
            intraday_change > self.THRESHOLD_INTRADAY * 2 and
            lower_shadow > 30):
            return 'v_reversal', 'V型反转'
        
        # 2. 倒V型：高开后大幅回落，收盘明显低于开盘
        #    特征：开盘高，日内跌幅大，上影线长
        if (open_change > self.THRESHOLD_OPEN and 
            intraday_change < -self.THRESHOLD_INTRADAY * 2 and
            upper_shadow > 30):
            return 'inverted_v', '倒V型'
        
        # 3. 单边上涨：持续走强，开盘涨且日内继续涨
        #    特征：开盘 > 昨收，收盘 > 开盘，实体较大
        if (open_change > self.THRESHOLD_OPEN and 
            intraday_change > self.THRESHOLD_INTRADAY and
            body_ratio > 50):
            return 'strong_uptrend', '单边上涨'
        
        # 4. 单边下跌：持续走弱，开盘跌且日内继续跌
        #    特征：开盘 < 昨收，收盘 < 开盘，实体较大
        if (open_change < -self.THRESHOLD_OPEN and 
            intraday_change < -self.THRESHOLD_INTRADAY and
            body_ratio > 50):
            return 'strong_downtrend', '单边下跌'
        
        # 5. 高开低走型：开盘上涨，但日内下跌，整体往下走
        #    特征：开盘 > 昨收，收盘 < 开盘，收盘可能 < 昨收
        if (open_change > self.THRESHOLD_OPEN and 
            intraday_change < -self.THRESHOLD_INTRADAY):
            # 如果上影线很长，说明冲高后回落明显
            if upper_shadow > 40:
                return 'high_open_low_close', '高开低走型(强回落)'
            return 'high_open_low_close', '高开低走型'
        
        # 6. 低开高走型：开盘下跌，但日内上涨，整体往上走
        #    特征：开盘 < 昨收，收盘 > 开盘，收盘可能 > 昨收
        if (open_change < -self.THRESHOLD_OPEN and 
            intraday_change > self.THRESHOLD_INTRADAY):
            # 如果下影线很长，说明探底后反弹明显
            if lower_shadow > 40:
                return 'low_open_high_close', '低开高走型(强反弹)'
            return 'low_open_high_close', '低开高走型'
        
        # 7. 震荡整理：上下波动，但收盘接近开盘
        #    特征：振幅较大，但实体较小
        if (amplitude > self.THRESHOLD_AMPLITUDE and 
            abs(intraday_change) < self.THRESHOLD_INTRADAY and
            body_ratio < 30):
            return 'consolidation', '震荡整理'
        
        # 8. 平淡走势：几乎无波动
        if amplitude < self.THRESHOLD_AMPLITUDE:
            return 'flat', '平淡走势'
        
        # 默认：根据日内涨跌判断
        if intraday_change > 0:
            return 'consolidation', '震荡偏强'
        elif intraday_change < 0:
            return 'consolidation', '震荡偏弱'
        else:
            return 'flat', '平淡走势'
    
    def analyze_market(self, df: pd.DataFrame) -> Dict:
        """
        分析整个市场的形态分布
        
        Args:
            df: 包含所有股票数据的DataFrame
        
        Returns:
            分析结果字典
        """
        if df.empty:
            return {}
        
        # 确保有必要的列
        required_cols = ['open', 'close', 'high', 'low']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"数据缺少必要的列: {required_cols}")
        
        # 分析每只股票的形态
        patterns = []
        pattern_names = []
        metrics_list = []
        
        for idx, row in df.iterrows():
            pattern_code, pattern_name, metrics = self.analyze_pattern(row)
            patterns.append(pattern_code)
            pattern_names.append(pattern_name)
            metrics_list.append(metrics)
        
        # 添加到DataFrame
        df = df.copy()
        df['pattern_code'] = patterns
        df['pattern_name'] = pattern_names
        
        # 添加详细指标
        for key in metrics_list[0].keys():
            df[key] = [m[key] for m in metrics_list]
        
        # 统计各形态的数量
        pattern_counts = df['pattern_name'].value_counts().to_dict()
        pattern_percentages = (df['pattern_name'].value_counts(normalize=True) * 100).to_dict()
        
        # 计算市场情绪指标
        total_stocks = len(df)
        
        # 强势形态：低开高走、V型反转、单边上涨
        bullish_patterns = ['低开高走型', '低开高走型(强反弹)', 'V型反转', '单边上涨']
        bullish_count = df[df['pattern_name'].isin(bullish_patterns)].shape[0]
        
        # 弱势形态：高开低走、倒V型、单边下跌
        bearish_patterns = ['高开低走型', '高开低走型(强回落)', '倒V型', '单边下跌']
        bearish_count = df[df['pattern_name'].isin(bearish_patterns)].shape[0]
        
        # 市场情绪指数 (-100 到 +100)
        sentiment_index = (bullish_count - bearish_count) / total_stocks * 100 if total_stocks > 0 else 0
        
        # 早盘vs午盘统计
        morning_high_count = df[df['session_trend'] == '早盘高'].shape[0]
        afternoon_high_count = df[df['session_trend'] == '午盘高'].shape[0]
        session_flat_count = df[df['session_trend'] == '持平'].shape[0]
        
        # 平均指标
        avg_metrics = {
            'avg_open_change': df['open_change_pct'].mean(),
            'avg_intraday_change': df['intraday_change_pct'].mean(),
            'avg_total_change': df['total_change_pct'].mean(),
            'avg_amplitude': df['amplitude'].mean(),
            'avg_morning_vs_afternoon': df['morning_vs_afternoon'].mean(),
        }
        
        # 构建结果
        result = {
            'data': df,
            'total_stocks': total_stocks,
            'pattern_counts': pattern_counts,
            'pattern_percentages': pattern_percentages,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'sentiment_index': round(sentiment_index, 2),
            'morning_high_count': morning_high_count,
            'afternoon_high_count': afternoon_high_count,
            'session_flat_count': session_flat_count,
            'avg_metrics': {k: round(v, 2) for k, v in avg_metrics.items()},
        }
        
        return result
    
    def get_pattern_description(self, pattern_code: str) -> str:
        """
        获取形态的详细描述
        
        Args:
            pattern_code: 形态代码
        
        Returns:
            形态描述
        """
        descriptions = {
            'high_open_low_close': '开盘高于昨日收盘，但收盘低于开盘，呈现先上升再下降的走势，整体往下走。可能表示市场抛压较重，多头力量不足。',
            'low_open_high_close': '开盘低于昨日收盘，但收盘高于开盘，呈现先下降再上升的走势，整体往上走。可能表示市场买盘积极，空头力量减弱。',
            'v_reversal': '低开后强势反弹，形成V型走势。表示市场在低位获得强力支撑，买盘涌入。',
            'inverted_v': '高开后大幅回落，形成倒V型走势。表示市场在高位遇到强力阻力，抛盘涌出。',
            'strong_uptrend': '开盘即上涨，日内持续走强，呈现单边上涨态势。表示市场多头力量强劲。',
            'strong_downtrend': '开盘即下跌，日内持续走弱，呈现单边下跌态势。表示市场空头力量强劲。',
            'consolidation': '价格上下波动，但收盘接近开盘，呈现震荡整理态势。表示市场多空力量均衡。',
            'flat': '价格波动很小，呈现平淡走势。表示市场交投清淡，观望情绪浓厚。',
        }
        return descriptions.get(pattern_code, '未知形态')
    
    def generate_pattern_report(self, result: Dict) -> str:
        """
        生成形态分析报告（文本格式）
        
        Args:
            result: analyze_market 返回的结果
        
        Returns:
            报告文本
        """
        if not result:
            return "无数据"
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("经典走势形态分析报告")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # 市场概况
        report_lines.append(f"总股票数: {result['total_stocks']}")
        report_lines.append(f"强势形态数: {result['bullish_count']} ({result['bullish_count']/result['total_stocks']*100:.1f}%)")
        report_lines.append(f"弱势形态数: {result['bearish_count']} ({result['bearish_count']/result['total_stocks']*100:.1f}%)")
        report_lines.append(f"市场情绪指数: {result['sentiment_index']:.2f}")
        report_lines.append("")
        
        # 早盘vs午盘
        report_lines.append("早盘vs午盘:")
        report_lines.append(f"  早盘价格高: {result['morning_high_count']} ({result['morning_high_count']/result['total_stocks']*100:.1f}%)")
        report_lines.append(f"  午盘价格高: {result['afternoon_high_count']} ({result['afternoon_high_count']/result['total_stocks']*100:.1f}%)")
        report_lines.append(f"  持平: {result['session_flat_count']} ({result['session_flat_count']/result['total_stocks']*100:.1f}%)")
        report_lines.append("")
        
        # 平均指标
        report_lines.append("市场平均指标:")
        for key, value in result['avg_metrics'].items():
            report_lines.append(f"  {key}: {value:.2f}%")
        report_lines.append("")
        
        # 形态分布
        report_lines.append("形态分布:")
        for pattern_name, count in sorted(result['pattern_counts'].items(), key=lambda x: x[1], reverse=True):
            pct = result['pattern_percentages'][pattern_name]
            report_lines.append(f"  {pattern_name}: {count} ({pct:.1f}%)")
        report_lines.append("")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)


def main():
    """测试函数"""
    import sys
    from pathlib import Path
    
    # 添加父目录到路径
    parent_dir = Path(__file__).resolve().parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    from data_loader import MarketDataLoader
    
    # 加载数据
    base_dir = Path(__file__).resolve().parent
    stocks_index_dir = base_dir.parent / "get-data" / "data" / "stocks_index"
    
    print("加载数据...")
    loader = MarketDataLoader(stocks_index_dir)
    market_data = loader.load_recent_days(1, show_progress=True)
    
    if market_data.empty:
        print("错误: 没有数据")
        return
    
    # 计算前一日收盘价
    market_data = loader.calculate_previous_close(market_data)
    
    # 过滤有效数据
    market_data = market_data[market_data['prev_close'].notna()]
    
    print(f"\n有效数据: {len(market_data)} 条")
    
    # 分析形态
    print("\n分析形态...")
    analyzer = PatternAnalyzer()
    result = analyzer.analyze_market(market_data)
    
    # 生成报告
    report = analyzer.generate_pattern_report(result)
    print("\n" + report)
    
    # 显示一些示例
    print("\n形态示例 (前10只股票):")
    df = result['data']
    for idx, row in df.head(10).iterrows():
        print(f"\n{row['code']} {row.get('name', 'N/A')}")
        print(f"  形态: {row['pattern_name']}")
        print(f"  开盘涨跌: {row['open_change_pct']:.2f}%")
        print(f"  日内涨跌: {row['intraday_change_pct']:.2f}%")
        print(f"  全天涨跌: {row['total_change_pct']:.2f}%")
        print(f"  振幅: {row['amplitude']:.2f}%")


if __name__ == "__main__":
    main()

