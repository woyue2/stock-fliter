"""
Report Generator
HTML报告生成模块
"""

from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class ReportGenerator:
    """市场情绪报告生成器"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Args:
            output_dir: 报告输出目录 (默认: ./output)
        """
        self.output_dir = Path(output_dir or "./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, date: str, 
                aggregated_stats: Dict,
                prediction,
                market_stats: Dict) -> str:
        """
        生成HTML报告
        
        Args:
            date: 日期
            aggregated_stats: 聚合统计
            prediction: 明日预测
            market_stats: 市场基础统计
        
        Returns:
            报告文件路径
        """
        html = self._build_html(date, aggregated_stats, prediction, market_stats)
        
        output_path = self.output_dir / f"sentiment_{date}.html"
        output_path.write_text(html, encoding='utf-8')
        
        return str(output_path)
    
    def _build_html(self, date: str, 
                   aggregated_stats: Dict,
                   prediction,
                   market_stats: Dict) -> str:
        """构建HTML内容"""
        
        distribution = aggregated_stats.get('distribution', {})
        ma_stats = aggregated_stats.get('morning_afternoon', {})
        intensity = aggregated_stats.get('intensity', {})
        signal = aggregated_stats.get('signal', {})
        
        # 形态分布饼图数据
        pie_data = self._make_pie_data(distribution)
        
        # 生成信号标签
        signal_html = self._make_signal_html(signal)
        
        # 预测结果
        prediction_html = self._make_prediction_html(prediction) if prediction else ""
        
        # 推理过程
        reasoning_html = self._make_reasoning_html(prediction.reasoning) if prediction and hasattr(prediction, 'reasoning') else ""
        
        # 统计表格
        stats_html = self._make_stats_html(market_stats, ma_stats, intensity)
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>分钟级市场情绪报告 - {date}</title>
    <style>
        :root {{
            --primary-color: #2563eb;
            --success-color: #10b981;
            --danger-color: #ef4444;
            --warning-color: #f59e0b;
            --neutral-color: #6b7280;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .card {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        
        .card-title {{
            font-size: 1.4em;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }}
        
        .stat-item {{
            text-align: center;
            padding: 16px;
            background: #f9fafb;
            border-radius: 12px;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: 700;
            color: var(--primary-color);
        }}
        
        .stat-value.positive {{ color: var(--success-color); }}
        .stat-value.negative {{ color: var(--danger-color); }}
        
        .stat-label {{
            font-size: 0.9em;
            color: #6b7280;
            margin-top: 4px;
        }}
        
        .chart-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        
        .pie-chart {{
            width: 300px;
            height: 300px;
        }}
        
        .legend {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            padding: 20px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95em;
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }}
        
        .prediction-section {{
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 24px;
        }}
        
        @media (max-width: 768px) {{
            .prediction-section {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .probability-chart {{
            display: flex;
            height: 60px;
            border-radius: 30px;
            overflow: hidden;
        }}
        
        .prob-segment {{
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 1.1em;
            transition: all 0.3s ease;
        }}
        
        .prob-segment:hover {{
            filter: brightness(1.1);
        }}
        
        .reasoning-list {{
            list-style: none;
            padding: 0;
        }}
        
        .reasoning-list li {{
            padding: 12px 16px;
            background: #f3f4f6;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid var(--primary-color);
        }}
        
        .signal-tag {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 1.2em;
        }}
        
        .signal-strong {{ background: #d1fae5; color: #065f46; }}
        .signal-weak {{ background: #fee2e2; color: #991b1b; }}
        .signal-neutral {{ background: #f3f4f6; color: #374151; }}
        
        .confidence-bar {{
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}
        
        .confidence-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--primary-color), var(--success-color));
            border-radius: 4px;
            transition: width 0.5s ease;
        }}
        
        .table-container {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        th {{
            background: #f9fafb;
            font-weight: 600;
            color: #374151;
        }}
        
        tr:hover td {{
            background: #f9fafb;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            opacity: 0.8;
            padding: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>分钟级市场情绪报告</h1>
            <div class="subtitle">{date} · 基于{market_stats.get('total_stocks', 0)}只股票分钟数据分析</div>
        </div>
        
        <!-- 市场概况 -->
        <div class="card">
            <div class="card-title">📊 市场概况</div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{market_stats.get('total_stocks', 0)}</div>
                    <div class="stat-label">分析股票</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value {'positive' if market_stats.get('avg_return', 0) > 0 else 'negative'}">
                        {market_stats.get('avg_return', 0):.2%}
                    </div>
                    <div class="stat-label">平均涨幅</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value {'positive' if market_stats.get('up_down_ratio', 0) > 1 else 'negative'}">
                        {market_stats.get('up_down_ratio', 0):.2f}
                    </div>
                    <div class="stat-label">涨跌比</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value {'positive' if market_stats.get('positive_ratio', 0) > 0.5 else 'negative'}">
                        {market_stats.get('positive_ratio', 0):.1%}
                    </div>
                    <div class="stat-label">上涨占比</div>
                </div>
            </div>
        </div>
        
        <!-- 形态分布 -->
        <div class="card">
            <div class="card-title">📈 形态分布</div>
            <div class="chart-container">
                <svg class="pie-chart" viewBox="0 0 100 100">
                    {pie_data['svg']}
                </svg>
            </div>
            <div class="legend">
                {pie_data['legend']}
            </div>
        </div>
        
        <!-- 明日推断 -->
        <div class="card">
            <div class="card-title">🔮 明日推断</div>
            {prediction_html}
        </div>
        
        <!-- 信号解读 -->
        <div class="card">
            <div class="card-title">💡 信号解读</div>
            <ul class="reasoning-list">
                {reasoning_html}
            </ul>
        </div>
        
        <!-- 详细统计 -->
        <div class="card">
            <div class="card-title">📉 详细统计</div>
            <div class="table-container">
                <table>
                    <tr>
                        <th>指标</th>
                        <th>数值</th>
                        <th>说明</th>
                    </tr>
                    <tr>
                        <td>上涨股票</td>
                        <td>{market_stats.get('up_count', 0)}只</td>
                        <td>涨幅 > 0</td>
                    </tr>
                    <tr>
                        <td>下跌股票</td>
                        <td>{market_stats.get('down_count', 0)}只</td>
                        <td>涨幅 < 0</td>
                    </tr>
                    <tr>
                        <td>早盘平均涨幅</td>
                        <td>{ma_stats.get('morning_avg', 0):.2%}</td>
                        <td>前120分钟</td>
                    </tr>
                    <tr>
                        <td>午盘平均涨幅</td>
                        <td>{ma_stats.get('afternoon_avg', 0):.2%}</td>
                        <td>后120分钟</td>
                    </tr>
                    <tr>
                        <td>强势股(Top10%)</td>
                        <td class="positive">{intensity.get('top_10_avg', 0):.2%}</td>
                        <td>平均涨幅</td>
                    </tr>
                    <tr>
                        <td>弱势股(Bottom10%)</td>
                        <td class="negative">{intensity.get('bottom_10_avg', 0):.2%}</td>
                        <td>平均跌幅</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>本报告基于分钟数据分析，仅供参考，不构成投资建议</p>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _make_pie_data(self, distribution: Dict) -> Dict:
        """生成饼图数据"""
        colors = [
            '#10b981', '#3b82f6', '#f59e0b', '#ef4444',
            '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6'
        ]
        
        # 过滤掉占比太小的
        filtered = {k: v for k, v in distribution.items() if v > 0.01}
        
        total = sum(filtered.values()) or 1
        items = list(filtered.items())
        
        svg_paths = []
        legend_html = ""
        cumulative_percent = 0
        
        for i, (name, ratio) in enumerate(sorted(items, key=lambda x: -x[1])):
            percent = ratio / total
            color = colors[i % len(colors)]
            
            # SVG饼图路径
            start_angle = cumulative_percent * 2 * 3.14159
            end_angle = (cumulative_percent + percent) * 2 * 3.14159
            
            cx, cy, r = 50, 50, 40
            
            x1 = cx + r * 0.01  # 简化处理
            y1 = cy
            x2 = cx + r * 0.01
            y2 = cy
            
            large_arc = 1 if percent > 0.5 else 0
            
            # 简化的环形图
            svg_paths.append(f"""
                <circle cx="50" cy="50" r="30" fill="transparent" stroke="{color}" 
                        stroke-width="20" stroke-dasharray="{percent * 188.5} 188.5" 
                        stroke-dashoffset="-{(cumulative_percent) * 188.5}"
                        transform="rotate(-90 50 50)"/>
            """)
            
            legend_html += f"""
                <div class="legend-item">
                    <div class="legend-color" style="background: {color}"></div>
                    <span>{name}: {percent:.1%}</span>
                </div>
            """
            
            cumulative_percent += percent
        
        return {
            'svg': '\n'.join(svg_paths),
            'legend': legend_html
        }
    
    def _make_signal_html(self, signal_info: Dict) -> str:
        """生成信号HTML"""
        # signal_info 可能是 {'signals': [...], 'signal': '偏强'} 或直接是字符串
        if isinstance(signal_info, str):
            signals = [signal_info]
            signal_text = signal_info
        else:
            signals = signal_info.get('signals', [])
            signal_text = signal_info.get('signal', '')
        
        if not signals:
            signals = ['无明显信号']
        if not signal_text:
            signal_text = '震荡'
        
        signal_class_map = {
            '偏强': 'signal-strong',
            '偏弱': 'signal-weak',
            '震荡': 'signal-neutral'
        }
        
        signal_class = signal_class_map.get(signal_text, 'signal-neutral')
        
        return f"""
            <div style="text-align: center; padding: 20px;">
                <span class="signal-tag {signal_class}">
                    今日信号: {' | '.join(signals[:3])}
                </span>
            </div>
        """
    
    def _make_prediction_html(self, prediction) -> str:
        """生成预测HTML"""
        bullish = prediction.bullish_prob
        neutral = prediction.neutral_prob
        bearish = prediction.bearish_prob
        
        colors = {
            'bullish': '#10b981',
            'neutral': '#6366f1',
            'bearish': '#ef4444'
        }
        
        return f"""
            <div class="prediction-section">
                <div>
                    <div style="font-size: 1.5em; font-weight: 600; margin-bottom: 10px;">
                        {prediction.signal}
                    </div>
                    <div style="font-size: 0.9em; color: #6b7280;">
                        置信度: {prediction.confidence:.0%}
                    </div>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: {prediction.confidence * 100}%"></div>
                    </div>
                </div>
                <div>
                    <div class="probability-chart">
                        <div class="prob-segment" style="width: {bullish * 100}%; background: {colors['bullish']}">
                            {bullish:.0%}
                        </div>
                        <div class="prob-segment" style="width: {neutral * 100}%; background: {colors['neutral']}">
                            {neutral:.0%}
                        </div>
                        <div class="prob-segment" style="width: {bearish * 100}%; background: {colors['bearish']}">
                            {bearish:.0%}
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-around; margin-top: 10px; font-size: 0.85em;">
                        <span style="color: {colors['bullish']}">偏强</span>
                        <span style="color: {colors['neutral']}">震荡</span>
                        <span style="color: {colors['bearish']}">偏弱</span>
                    </div>
                </div>
            </div>
        """
    
    def _make_reasoning_html(self, reasoning: List[str]) -> str:
        """生成推理过程HTML"""
        return '\n'.join(f'<li>{r}</li>' for r in reasoning)
    
    def _make_stats_html(self, market_stats: Dict, 
                         ma_stats: Dict, 
                         intensity: Dict) -> str:
        """生成统计表格HTML"""
        return ""
