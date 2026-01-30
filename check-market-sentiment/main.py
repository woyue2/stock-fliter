"""
市场情绪分析 - 高开低走统计
分析整个市场的高开低走情况，评估市场情绪
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from get_data.main import load_stock_data


class MarketSentimentAnalyzer:
    """市场情绪分析器 - 专注于高开低走分析"""
    
    def __init__(self, date=None):
        """
        初始化分析器
        
        Args:
            date: 分析日期，默认为最新交易日
        """
        self.date = date
        self.results = []
        
    def analyze_stock(self, code, name, df):
        """
        分析单只股票的高开低走情况
        
        Args:
            code: 股票代码
            name: 股票名称
            df: 股票数据DataFrame
            
        Returns:
            dict: 分析结果
        """
        if len(df) < 2:
            return None
            
        # 获取最新一天和前一天的数据
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        open_price = latest['open']
        close_price = latest['close']
        high_price = latest['high']
        low_price = latest['low']
        prev_close = prev['close']
        
        # 计算关键指标
        gap_up_pct = (open_price - prev_close) / prev_close * 100  # 高开幅度
        pullback_pct = (open_price - close_price) / open_price * 100  # 回落幅度
        net_change_pct = (close_price - prev_close) / prev_close * 100  # 相对昨收涨跌
        
        # 判断是否高开低走
        is_gap_up_pullback = gap_up_pct > 0 and close_price < open_price
        
        if not is_gap_up_pullback:
            return None
            
        # 分类高开低走的强度
        category = self._categorize_pullback(
            close_price, open_price, prev_close, low_price, high_price
        )
        
        # 🆕 分析分时特征（早盘 vs 午盘）
        intraday_pattern = self._analyze_intraday_pattern(
            open_price, close_price, high_price, low_price
        )
        
        # 计算上影线和下影线比例
        upper_shadow = (high_price - max(open_price, close_price)) / (high_price - low_price) * 100 if high_price > low_price else 0
        lower_shadow = (min(open_price, close_price) - low_price) / (high_price - low_price) * 100 if high_price > low_price else 0
        
        return {
            'code': code,
            'name': name,
            'gap_up_pct': round(gap_up_pct, 2),
            'pullback_pct': round(pullback_pct, 2),
            'net_change_pct': round(net_change_pct, 2),
            'category': category,
            'intraday_pattern': intraday_pattern,  # 🆕 分时特征
            'upper_shadow': round(upper_shadow, 2),
            'lower_shadow': round(lower_shadow, 2),
            'volume': latest.get('volume', 0),
            'turnover': latest.get('turnover', 0)
        }
    
    def _categorize_pullback(self, close, open_price, prev_close, low, high):
        """
        分类高开低走的强度
        
        Returns:
            str: 轻度/中度/重度
        """
        # 轻度：收盘仍高于昨收（假阳线）
        if close > prev_close:
            return "轻度"
        
        # 重度：收盘价接近最低价（下影线很短）
        body_range = high - low
        if body_range > 0:
            close_to_low_ratio = (close - low) / body_range
            if close_to_low_ratio < 0.3:  # 收盘价在下方30%区域
                return "重度"
        
        # 中度：其他情况
        return "中度"
    
    def _analyze_intraday_pattern(self, open_price, close_price, high_price, low_price):
        """
        🆕 分析分时特征：判断是早盘高开低走还是午盘高开低走
        
        通过K线形态推断分时走势：
        - 早盘冲高回落：最高价接近开盘价，说明开盘即最高
        - 午盘杀跌：最高价远离开盘价，说明盘中有冲高后杀跌
        - 全天弱势：收盘接近最低，全天承压
        - 尾盘反弹：收盘远离最低，有抄底资金
        
        Args:
            open_price: 开盘价
            close_price: 收盘价
            high_price: 最高价
            low_price: 最低价
            
        Returns:
            str: 分时特征描述
        """
        if high_price == low_price:
            return "一字板"
        
        # 计算关键位置比例
        total_range = high_price - low_price
        
        # 开盘相对位置（0=最低，1=最高）
        open_position = (open_price - low_price) / total_range
        
        # 收盘相对位置
        close_position = (close_price - low_price) / total_range
        
        # 最高价相对开盘的位置
        high_from_open = (high_price - open_price) / total_range
        
        # 收盘相对最低的位置
        close_from_low = (close_price - low_price) / total_range
        
        # 判断逻辑
        # 1. 早盘冲高回落型：开盘就是最高或接近最高
        if high_from_open < 0.2:  # 最高价距离开盘价很近
            if close_from_low < 0.3:  # 收盘接近最低
                return "早盘冲高秒杀"  # 🔴 最危险：开盘即顶，全天暴跌
            else:
                return "早盘冲高回落"  # 🟡 开盘即顶，但有支撑
        
        # 2. 盘中冲高后杀跌型：最高价远离开盘价
        elif high_from_open > 0.3:  # 盘中有明显冲高
            if close_from_low < 0.3:  # 收盘接近最低
                return "午盘冲高杀跌"  # 🔴 危险：盘中诱多后暴跌
            else:
                return "午盘冲高回落"  # 🟡 盘中冲高后回落，但有支撑
        
        # 3. 全天震荡下行型
        else:
            if close_from_low < 0.3:  # 收盘接近最低
                return "全天弱势下行"  # 🔴 全天承压，尾盘杀跌
            elif close_from_low > 0.5:  # 收盘在中上部
                return "震荡回落有支撑"  # 🟢 虽然回落但有抄底
            else:
                return "震荡下行"  # 🟡 普通震荡下行
    
    
    def analyze_market(self):
        """分析整个市场"""
        print("=" * 60)
        print("📊 市场情绪分析 - 高开低走统计")
        print("=" * 60)
        
        # 加载股票列表
        stock_list_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'stocks_index.csv'
        )
        
        if not os.path.exists(stock_list_path):
            print(f"❌ 股票列表文件不存在: {stock_list_path}")
            return
        
        stock_list = pd.read_csv(stock_list_path)
        print(f"📋 加载股票列表: {len(stock_list)} 只股票")
        
        # 分析每只股票
        total_stocks = 0
        analyzed_stocks = 0
        
        for idx, row in stock_list.iterrows():
            code = row['code']
            name = row['name']
            
            try:
                # 加载股票数据
                df = load_stock_data(code)
                if df is None or len(df) < 2:
                    continue
                
                total_stocks += 1
                
                # 分析
                result = self.analyze_stock(code, name, df)
                if result:
                    self.results.append(result)
                    analyzed_stocks += 1
                
                # 进度显示
                if (idx + 1) % 100 == 0:
                    print(f"进度: {idx + 1}/{len(stock_list)}, 发现高开低走: {analyzed_stocks}")
                    
            except Exception as e:
                continue
        
        print(f"\n✅ 分析完成！")
        print(f"   总股票数: {total_stocks}")
        print(f"   高开低走股票数: {analyzed_stocks}")
        
        return self.generate_report()
    
    def generate_report(self):
        """生成分析报告"""
        if not self.results:
            print("⚠️  没有发现高开低走的股票")
            return
        
        df = pd.DataFrame(self.results)
        
        print("\n" + "=" * 60)
        print("📈 市场高开低走分析报告")
        print("=" * 60)
        
        # 1. 整体统计
        total_analyzed = len(df)
        print(f"\n【整体情况】")
        print(f"  高开低走股票数: {total_analyzed}")
        
        # 2. 强度分级统计
        print(f"\n【强度分级】")
        category_counts = df['category'].value_counts()
        for category in ['轻度', '中度', '重度']:
            count = category_counts.get(category, 0)
            pct = count / total_analyzed * 100
            print(f"  {category}: {count} 只 ({pct:.1f}%)")
        
        # 🆕 3. 分时特征统计
        print(f"\n【分时特征】")
        pattern_counts = df['intraday_pattern'].value_counts()
        for pattern, count in pattern_counts.items():
            pct = count / total_analyzed * 100
            emoji = self._get_pattern_emoji(pattern)
            print(f"  {emoji} {pattern}: {count} 只 ({pct:.1f}%)")
        
        # 4. 平均指标
        print(f"\n【平均指标】")
        print(f"  平均高开幅度: {df['gap_up_pct'].mean():.2f}%")
        print(f"  平均回落幅度: {df['pullback_pct'].mean():.2f}%")
        print(f"  平均净涨跌幅: {df['net_change_pct'].mean():.2f}%")
        
        # 4. 市场情绪指数（0-100，越高越差）
        sentiment_score = self._calculate_sentiment_score(df)
        print(f"\n【市场情绪指数】")
        print(f"  情绪指数: {sentiment_score:.1f}/100")
        print(f"  情绪评级: {self._get_sentiment_rating(sentiment_score)}")
        
        # 5. Top 10 最严重的高开低走
        print(f"\n【Top 10 最严重高开低走】")
        top_10 = df.nlargest(10, 'pullback_pct')
        for idx, row in top_10.iterrows():
            print(f"  {row['name']}({row['code']}): "
                  f"高开{row['gap_up_pct']:.2f}% → 回落{row['pullback_pct']:.2f}% "
                  f"[{row['category']}] [{row['intraday_pattern']}]")
        
        # 6. 保存详细结果
        self._save_results(df)
        
        return df
    
    def _get_pattern_emoji(self, pattern):
        """获取分时特征对应的emoji"""
        emoji_map = {
            '早盘冲高秒杀': '💀',
            '早盘冲高回落': '📉',
            '午盘冲高杀跌': '⚠️',
            '午盘冲高回落': '📊',
            '全天弱势下行': '🔻',
            '震荡回落有支撑': '💚',
            '震荡下行': '📉',
            '一字板': '➖'
        }
        return emoji_map.get(pattern, '📊')
    
    def _calculate_sentiment_score(self, df):
        """
        计算市场情绪指数
        
        综合考虑：
        1. 高开低走比例（假设总市场有4000只股票）
        2. 平均回落幅度
        3. 重度高开低走占比
        
        Returns:
            float: 0-100的情绪指数，越高越差
        """
        # 假设市场总股票数
        TOTAL_MARKET_STOCKS = 4000
        
        # 1. 高开低走比例得分 (0-40分)
        ratio = len(df) / TOTAL_MARKET_STOCKS
        ratio_score = min(ratio * 100, 40)
        
        # 2. 平均回落幅度得分 (0-30分)
        avg_pullback = df['pullback_pct'].mean()
        pullback_score = min(avg_pullback * 3, 30)
        
        # 3. 重度占比得分 (0-30分)
        severe_ratio = len(df[df['category'] == '重度']) / len(df)
        severe_score = severe_ratio * 30
        
        total_score = ratio_score + pullback_score + severe_score
        return min(total_score, 100)
    
    def _get_sentiment_rating(self, score):
        """根据情绪指数给出评级"""
        if score >= 70:
            return "😱 极度恐慌"
        elif score >= 50:
            return "😰 恐慌"
        elif score >= 30:
            return "😟 谨慎"
        elif score >= 15:
            return "😐 中性偏弱"
        else:
            return "😊 健康"
    
    def _save_results(self, df):
        """保存结果到文件"""
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存CSV
        csv_path = os.path.join(output_dir, f'market_sentiment_{datetime.now().strftime("%Y%m%d")}.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 详细结果已保存: {csv_path}")
        
        # 生成HTML报告
        self._generate_html_report(df, output_dir)
    
    def _generate_html_report(self, df, output_dir):
        """生成HTML可视化报告"""
        html_path = os.path.join(output_dir, f'market_sentiment_{datetime.now().strftime("%Y%m%d")}.html')
        
        # 计算统计数据
        category_counts = df['category'].value_counts()
        pattern_counts = df['intraday_pattern'].value_counts()
        sentiment_score = self._calculate_sentiment_score(df)
        sentiment_rating = self._get_sentiment_rating(sentiment_score)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>市场情绪分析 - 高开低走统计</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 42px;
            color: #2d3748;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .date {{
            color: #718096;
            font-size: 18px;
        }}
        
        .sentiment-score {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            text-align: center;
        }}
        
        .sentiment-score .score {{
            font-size: 72px;
            font-weight: 700;
            margin: 20px 0;
        }}
        
        .sentiment-score .rating {{
            font-size: 32px;
            margin-top: 10px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-card .label {{
            color: #718096;
            font-size: 14px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card .value {{
            color: #2d3748;
            font-size: 36px;
            font-weight: 700;
        }}
        
        .category-section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }}
        
        .category-section h2 {{
            color: #2d3748;
            font-size: 28px;
            margin-bottom: 30px;
        }}
        
        .category-bars {{
            margin-bottom: 40px;
        }}
        
        .category-bar {{
            margin-bottom: 20px;
        }}
        
        .category-bar .bar-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            color: #4a5568;
            font-weight: 600;
        }}
        
        .category-bar .bar-bg {{
            background: #e2e8f0;
            height: 30px;
            border-radius: 15px;
            overflow: hidden;
        }}
        
        .category-bar .bar-fill {{
            height: 100%;
            border-radius: 15px;
            transition: width 1s ease;
            display: flex;
            align-items: center;
            padding: 0 15px;
            color: white;
            font-weight: 600;
        }}
        
        .bar-fill.light {{
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        }}
        
        .bar-fill.medium {{
            background: linear-gradient(90deg, #fa709a 0%, #fee140 100%);
        }}
        
        .bar-fill.severe {{
            background: linear-gradient(90deg, #f83600 0%, #f9d423 100%);
        }}
        
        .top-stocks {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }}
        
        .top-stocks h2 {{
            color: #2d3748;
            font-size: 28px;
            margin-bottom: 30px;
        }}
        
        .stock-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .stock-table th {{
            background: #f7fafc;
            color: #4a5568;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        .stock-table td {{
            padding: 15px;
            border-bottom: 1px solid #e2e8f0;
            color: #2d3748;
        }}
        
        .stock-table tr:hover {{
            background: #f7fafc;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .badge.light {{
            background: #bee3f8;
            color: #2c5282;
        }}
        
        .badge.medium {{
            background: #fbd38d;
            color: #7c2d12;
        }}
        
        .badge.severe {{
            background: #fc8181;
            color: #742a2a;
        }}
        
        .positive {{
            color: #48bb78;
        }}
        
        .negative {{
            color: #f56565;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 市场情绪分析报告</h1>
            <div class="date">高开低走统计 · {datetime.now().strftime('%Y年%m月%d日')}</div>
        </div>
        
        <div class="sentiment-score">
            <div style="font-size: 20px; opacity: 0.9;">市场情绪指数</div>
            <div class="score">{sentiment_score:.1f}</div>
            <div style="font-size: 16px; opacity: 0.8;">满分100分（越高越恐慌）</div>
            <div class="rating">{sentiment_rating}</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">高开低走股票数</div>
                <div class="value">{len(df)}</div>
            </div>
            <div class="stat-card">
                <div class="label">平均高开幅度</div>
                <div class="value">{df['gap_up_pct'].mean():.2f}%</div>
            </div>
            <div class="stat-card">
                <div class="label">平均回落幅度</div>
                <div class="value">{df['pullback_pct'].mean():.2f}%</div>
            </div>
            <div class="stat-card">
                <div class="label">平均净涨跌幅</div>
                <div class="value" class="{'positive' if df['net_change_pct'].mean() > 0 else 'negative'}">{df['net_change_pct'].mean():.2f}%</div>
            </div>
        </div>
        
        <div class="category-section">
            <h2>强度分级统计</h2>
            <div class="category-bars">
                <div class="category-bar">
                    <div class="bar-label">
                        <span>轻度（假阳线）</span>
                        <span>{category_counts.get('轻度', 0)} 只 ({category_counts.get('轻度', 0) / len(df) * 100:.1f}%)</span>
                    </div>
                    <div class="bar-bg">
                        <div class="bar-fill light" style="width: {category_counts.get('轻度', 0) / len(df) * 100}%">
                        </div>
                    </div>
                </div>
                
                <div class="category-bar">
                    <div class="bar-label">
                        <span>中度</span>
                        <span>{category_counts.get('中度', 0)} 只 ({category_counts.get('中度', 0) / len(df) * 100:.1f}%)</span>
                    </div>
                    <div class="bar-bg">
                        <div class="bar-fill medium" style="width: {category_counts.get('中度', 0) / len(df) * 100}%">
                        </div>
                    </div>
                </div>
                
                <div class="category-bar">
                    <div class="bar-label">
                        <span>重度（收盘近最低）</span>
                        <span>{category_counts.get('重度', 0)} 只 ({category_counts.get('重度', 0) / len(df) * 100:.1f}%)</span>
                    </div>
                    <div class="bar-bg">
                        <div class="bar-fill severe" style="width: {category_counts.get('重度', 0) / len(df) * 100}%">
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="category-section">
            <h2>🆕 分时特征统计</h2>
            <div class="category-bars">"""
        
        # 动态生成分时特征柱状图
        for pattern, count in pattern_counts.items():
            pct = count / len(df) * 100
            emoji = self._get_pattern_emoji(pattern)
            
            # 根据危险程度选择颜色
            if pattern in ['早盘冲高秒杀', '午盘冲高杀跌', '全天弱势下行']:
                bar_class = 'severe'
            elif pattern in ['震荡回落有支撑']:
                bar_class = 'light'
            else:
                bar_class = 'medium'
            
            html_content += f"""
                <div class="category-bar">
                    <div class="bar-label">
                        <span>{emoji} {pattern}</span>
                        <span>{count} 只 ({pct:.1f}%)</span>
                    </div>
                    <div class="bar-bg">
                        <div class="bar-fill {bar_class}" style="width: {pct}%">
                        </div>
                    </div>
                </div>"""
        
        html_content += """
            </div>
        </div>
        
        <div class="top-stocks">
            <h2>Top 20 最严重高开低走</h2>
            <table class="stock-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>股票</th>
                        <th>高开幅度</th>
                        <th>回落幅度</th>
                        <th>净涨跌</th>
                        <th>强度</th>
                        <th>分时特征</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # 添加Top 20股票
        top_20 = df.nlargest(20, 'pullback_pct')
        for idx, (_, row) in enumerate(top_20.iterrows(), 1):
            badge_class = {
                '轻度': 'light',
                '中度': 'medium',
                '重度': 'severe'
            }.get(row['category'], 'medium')
            
            net_class = 'positive' if row['net_change_pct'] > 0 else 'negative'
            pattern_emoji = self._get_pattern_emoji(row['intraday_pattern'])
            
            html_content += f"""
                    <tr>
                        <td>{idx}</td>
                        <td><strong>{row['name']}</strong><br><small>{row['code']}</small></td>
                        <td class="positive">+{row['gap_up_pct']:.2f}%</td>
                        <td class="negative">-{row['pullback_pct']:.2f}%</td>
                        <td class="{net_class}">{row['net_change_pct']:+.2f}%</td>
                        <td><span class="badge {badge_class}">{row['category']}</span></td>
                        <td>{pattern_emoji} {row['intraday_pattern']}</td>
                    </tr>
"""
        
        html_content += """
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // 动画效果
        window.addEventListener('load', function() {
            const bars = document.querySelectorAll('.bar-fill');
            bars.forEach(bar => {
                const width = bar.style.width;
                bar.style.width = '0%';
                setTimeout(() => {
                    bar.style.width = width;
                }, 100);
            });
        });
    </script>
</body>
</html>
"""
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTML报告已生成: {html_path}")


def main():
    """主函数"""
    analyzer = MarketSentimentAnalyzer()
    analyzer.analyze_market()


if __name__ == '__main__':
    main()

