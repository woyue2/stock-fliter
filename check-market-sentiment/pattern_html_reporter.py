# -*- coding: utf-8 -*-
"""
形态分析HTML报告生成器

生成美观的HTML报告，展示各种经典走势形态
"""
from pathlib import Path
from datetime import datetime
from typing import Dict
import pandas as pd


class PatternHTMLReporter:
    """形态分析HTML报告生成器"""
    
    def __init__(self, output_dir: Path):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, result: Dict, date_str: str = None) -> Path:
        """
        生成HTML报告
        
        Args:
            result: 分析结果
            date_str: 日期字符串
        
        Returns:
            报告文件路径
        """
        if not result:
            raise ValueError("分析结果为空")
        
        df = result['data']
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pattern_analysis_{timestamp}.html"
        filepath = self.output_dir / filename
        
        # 生成HTML
        html = self._generate_html(result, date_str)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return filepath
    
    def _generate_html(self, result: Dict, date_str: str = None) -> str:
        """生成HTML内容"""
        df = result['data']
        
        # 获取日期
        if date_str is None:
            if 'date' in df.columns and not df.empty:
                date_obj = df['date'].iloc[0]
                date_str = date_obj.strftime('%Y-%m-%d') if hasattr(date_obj, 'strftime') else str(date_obj)
            else:
                date_str = datetime.now().strftime('%Y-%m-%d')
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>经典走势形态分析 - {date_str}</title>
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
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }}
        
        .header .date {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s;
        }}
        
        .summary-card:hover {{
            transform: translateY(-5px);
        }}
        
        .summary-card.bullish {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        
        .summary-card.bearish {{
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }}
        
        .summary-card.neutral {{
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        }}
        
        .summary-card .label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        .pattern-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .pattern-card {{
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s;
        }}
        
        .pattern-card:hover {{
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.2);
            transform: translateY(-3px);
        }}
        
        .pattern-card .pattern-name {{
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
        }}
        
        .pattern-card .pattern-stats {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        
        .pattern-card .stat-label {{
            color: #666;
        }}
        
        .pattern-card .stat-value {{
            font-weight: bold;
            color: #667eea;
        }}
        
        .pattern-card .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }}
        
        .pattern-card .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        
        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        tbody tr:hover {{
            background: #f8f9ff;
        }}
        
        .positive {{
            color: #e74c3c;
            font-weight: bold;
        }}
        
        .negative {{
            color: #27ae60;
            font-weight: bold;
        }}
        
        .neutral {{
            color: #95a5a6;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        
        .badge-bullish {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        
        .badge-bearish {{
            background: #ffebee;
            color: #c62828;
        }}
        
        .badge-neutral {{
            background: #f5f5f5;
            color: #616161;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .summary {{
                grid-template-columns: 1fr;
            }}
            
            .pattern-grid {{
                grid-template-columns: 1fr;
            }}
            
            table {{
                font-size: 0.9em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 经典走势形态分析</h1>
            <div class="date">{date_str}</div>
        </div>
        
        <div class="content">
            {self._generate_summary_section(result)}
            {self._generate_session_analysis_section(result)}
            {self._generate_pattern_distribution_section(result)}
            {self._generate_top_patterns_section(result)}
            {self._generate_detailed_table_section(result)}
        </div>
        
        <div class="footer">
            生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _generate_summary_section(self, result: Dict) -> str:
        """生成概览部分"""
        sentiment_index = result['sentiment_index']
        
        # 判断市场情绪
        if sentiment_index > 10:
            sentiment_label = "强势"
            sentiment_class = "bullish"
        elif sentiment_index < -10:
            sentiment_label = "弱势"
            sentiment_class = "bearish"
        else:
            sentiment_label = "中性"
            sentiment_class = "neutral"
        
        # 早盘vs午盘的判断
        morning_high_pct = result['morning_high_count'] / result['total_stocks'] * 100
        afternoon_high_pct = result['afternoon_high_count'] / result['total_stocks'] * 100
        
        if morning_high_pct > afternoon_high_pct + 5:
            session_label = "早盘偏强"
            session_class = "bearish"  # 早盘高意味着后续可能回落
        elif afternoon_high_pct > morning_high_pct + 5:
            session_label = "午盘偏强"
            session_class = "bullish"  # 午盘高意味着走势偏强
        else:
            session_label = "全天均衡"
            session_class = "neutral"
        
        html = f"""
            <div class="section">
                <div class="summary">
                    <div class="summary-card">
                        <div class="label">总股票数</div>
                        <div class="value">{result['total_stocks']}</div>
                    </div>
                    
                    <div class="summary-card bullish">
                        <div class="label">强势形态</div>
                        <div class="value">{result['bullish_count']}</div>
                        <div class="label">{result['bullish_count']/result['total_stocks']*100:.1f}%</div>
                    </div>
                    
                    <div class="summary-card bearish">
                        <div class="label">弱势形态</div>
                        <div class="value">{result['bearish_count']}</div>
                        <div class="label">{result['bearish_count']/result['total_stocks']*100:.1f}%</div>
                    </div>
                    
                    <div class="summary-card {sentiment_class}">
                        <div class="label">市场情绪</div>
                        <div class="value">{sentiment_label}</div>
                        <div class="label">指数: {sentiment_index:.2f}</div>
                    </div>
                    
                    <div class="summary-card neutral">
                        <div class="label">平均涨跌</div>
                        <div class="value">{result['avg_metrics']['avg_total_change']:.2f}%</div>
                    </div>
                    
                    <div class="summary-card neutral">
                        <div class="label">平均振幅</div>
                        <div class="value">{result['avg_metrics']['avg_amplitude']:.2f}%</div>
                    </div>
                    
                    <div class="summary-card {session_class}">
                        <div class="label">早盘vs午盘</div>
                        <div class="value">{session_label}</div>
                        <div class="label">早{morning_high_pct:.0f}% 午{afternoon_high_pct:.0f}%</div>
                    </div>
                    
                    <div class="summary-card neutral">
                        <div class="label">早午盘差异</div>
                        <div class="value">{result['avg_metrics']['avg_morning_vs_afternoon']:.2f}%</div>
                        <div class="label">{'早盘高' if result['avg_metrics']['avg_morning_vs_afternoon'] > 0 else '午盘高'}</div>
                    </div>
                </div>
            </div>
        """
        
        return html
    
    def _generate_session_analysis_section(self, result: Dict) -> str:
        """生成早盘vs午盘分析部分"""
        morning_high_count = result['morning_high_count']
        afternoon_high_count = result['afternoon_high_count']
        session_flat_count = result['session_flat_count']
        total = result['total_stocks']
        
        morning_pct = morning_high_count / total * 100
        afternoon_pct = afternoon_high_count / total * 100
        flat_pct = session_flat_count / total * 100
        
        avg_diff = result['avg_metrics']['avg_morning_vs_afternoon']
        
        # 判断市场特征
        if morning_pct > afternoon_pct + 10:
            market_feature = "早盘冲高，午盘回落"
            feature_class = "bearish"
        elif afternoon_pct > morning_pct + 10:
            market_feature = "午盘走强，持续上涨"
            feature_class = "bullish"
        else:
            market_feature = "全天走势均衡"
            feature_class = "neutral"
        
        html = f"""
            <div class="section">
                <h2 class="section-title">📊 早盘vs午盘分析</h2>
                
                <div class="pattern-grid">
                    <div class="pattern-card">
                        <div class="pattern-name" style="color: #e74c3c;">早盘价格高</div>
                        <div class="pattern-stats">
                            <span class="stat-label">数量:</span>
                            <span class="stat-value">{morning_high_count}</span>
                        </div>
                        <div class="pattern-stats">
                            <span class="stat-label">占比:</span>
                            <span class="stat-value">{morning_pct:.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {morning_pct}%; background: linear-gradient(90deg, #fa709a 0%, #fee140 100%);"></div>
                        </div>
                        <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                            开盘冲高，午盘回落
                        </div>
                    </div>
                    
                    <div class="pattern-card">
                        <div class="pattern-name" style="color: #27ae60;">午盘价格高</div>
                        <div class="pattern-stats">
                            <span class="stat-label">数量:</span>
                            <span class="stat-value">{afternoon_high_count}</span>
                        </div>
                        <div class="pattern-stats">
                            <span class="stat-label">占比:</span>
                            <span class="stat-value">{afternoon_pct:.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {afternoon_pct}%; background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);"></div>
                        </div>
                        <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                            持续走强，午盘更高
                        </div>
                    </div>
                    
                    <div class="pattern-card">
                        <div class="pattern-name" style="color: #95a5a6;">全天持平</div>
                        <div class="pattern-stats">
                            <span class="stat-label">数量:</span>
                            <span class="stat-value">{session_flat_count}</span>
                        </div>
                        <div class="pattern-stats">
                            <span class="stat-label">占比:</span>
                            <span class="stat-value">{flat_pct:.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {flat_pct}%; background: linear-gradient(90deg, #a8edea 0%, #fed6e3 100%);"></div>
                        </div>
                        <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                            早午盘价格接近
                        </div>
                    </div>
                </div>
                
                <div style="margin-top: 30px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
                    <h3 style="margin-bottom: 15px; font-size: 1.3em;">市场特征</h3>
                    <div style="font-size: 1.5em; font-weight: bold; margin-bottom: 10px;">{market_feature}</div>
                    <div style="font-size: 1.1em; opacity: 0.9;">
                        平均早午盘价格差异: {avg_diff:+.2f}%
                        {'（早盘价格更高）' if avg_diff > 0 else '（午盘价格更高）' if avg_diff < 0 else '（基本持平）'}
                    </div>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background: #f8f9ff; border-radius: 10px; border-left: 4px solid #667eea;">
                    <h4 style="color: #667eea; margin-bottom: 10px;">💡 分析说明</h4>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.8;">
                        <li><strong>早盘价格高</strong>：早盘特征价格 = 开盘价×70% + 最高价×30%</li>
                        <li><strong>午盘价格高</strong>：午盘特征价格 = 收盘价×70% + 最低价×30%</li>
                        <li><strong>判断标准</strong>：早午盘价格差异 > 0.5% 视为有明显差异</li>
                        <li><strong>市场含义</strong>：
                            <ul style="margin-top: 5px;">
                                <li>早盘高 → 开盘冲高后回落，可能存在获利盘抛压</li>
                                <li>午盘高 → 持续走强，买盘积极，市场承接力好</li>
                            </ul>
                        </li>
                    </ul>
                </div>
            </div>
        """
        
        return html
    
    def _generate_pattern_distribution_section(self, result: Dict) -> str:
        """生成形态分布部分"""
        html = """
            <div class="section">
                <h2 class="section-title">形态分布</h2>
                <div class="pattern-grid">
        """
        
        # 按数量排序
        sorted_patterns = sorted(result['pattern_counts'].items(), key=lambda x: x[1], reverse=True)
        
        for pattern_name, count in sorted_patterns:
            percentage = result['pattern_percentages'][pattern_name]
            
            html += f"""
                    <div class="pattern-card">
                        <div class="pattern-name">{pattern_name}</div>
                        <div class="pattern-stats">
                            <span class="stat-label">数量:</span>
                            <span class="stat-value">{count}</span>
                        </div>
                        <div class="pattern-stats">
                            <span class="stat-label">占比:</span>
                            <span class="stat-value">{percentage:.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {percentage}%"></div>
                        </div>
                    </div>
            """
        
        html += """
                </div>
            </div>
        """
        
        return html
    
    def _generate_top_patterns_section(self, result: Dict) -> str:
        """生成典型形态案例部分"""
        df = result['data']
        
        html = """
            <div class="section">
                <h2 class="section-title">典型形态案例 (TOP 5)</h2>
        """
        
        # 1. 高开低走
        html += self._generate_pattern_top5(
            df, '高开低走', 
            df[df['pattern_name'].str.contains('高开低走')],
            sort_by='open_change_pct',
            ascending=False
        )
        
        # 2. 低开高走
        html += self._generate_pattern_top5(
            df, '低开高走',
            df[df['pattern_name'].str.contains('低开高走')],
            sort_by='intraday_change_pct',
            ascending=False
        )
        
        # 3. V型反转
        html += self._generate_pattern_top5(
            df, 'V型反转',
            df[df['pattern_name'] == 'V型反转'],
            sort_by='intraday_change_pct',
            ascending=False
        )
        
        # 4. 倒V型
        html += self._generate_pattern_top5(
            df, '倒V型',
            df[df['pattern_name'] == '倒V型'],
            sort_by='intraday_change_pct',
            ascending=True
        )
        
        html += """
            </div>
        """
        
        return html
    
    def _generate_pattern_top5(self, df: pd.DataFrame, title: str, pattern_df: pd.DataFrame, 
                                sort_by: str, ascending: bool) -> str:
        """生成单个形态的TOP5表格"""
        if pattern_df.empty:
            return ""
        
        top5 = pattern_df.sort_values(sort_by, ascending=ascending).head(5)
        
        html = f"""
                <h3 style="color: #764ba2; margin: 20px 0 10px 0;">{title}</h3>
                <table>
                    <thead>
                        <tr>
                            <th>代码</th>
                            <th>名称</th>
                            <th>开盘涨跌</th>
                            <th>日内涨跌</th>
                            <th>全天涨跌</th>
                            <th>振幅</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for idx, row in top5.iterrows():
            open_class = 'positive' if row['open_change_pct'] > 0 else 'negative' if row['open_change_pct'] < 0 else 'neutral'
            intraday_class = 'positive' if row['intraday_change_pct'] > 0 else 'negative' if row['intraday_change_pct'] < 0 else 'neutral'
            total_class = 'positive' if row['total_change_pct'] > 0 else 'negative' if row['total_change_pct'] < 0 else 'neutral'
            
            html += f"""
                        <tr>
                            <td>{row['code']}</td>
                            <td>{row.get('name', 'N/A')}</td>
                            <td class="{open_class}">{row['open_change_pct']:+.2f}%</td>
                            <td class="{intraday_class}">{row['intraday_change_pct']:+.2f}%</td>
                            <td class="{total_class}">{row['total_change_pct']:+.2f}%</td>
                            <td>{row['amplitude']:.2f}%</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
        """
        
        return html
    
    def _generate_detailed_table_section(self, result: Dict) -> str:
        """生成详细数据表格部分"""
        df = result['data']
        
        # 显示所有数据（不再限制100条）
        display_df = df
        
        html = f"""
            <div class="section">
                <h2 class="section-title">详细数据 (共{len(display_df)}条)</h2>
                
                <!-- 搜索和筛选工具栏 -->
                <div style="margin-bottom: 20px; padding: 20px; background: #f8f9ff; border-radius: 10px;">
                    <div style="display: flex; gap: 15px; flex-wrap: wrap; align-items: center;">
                        <div style="flex: 1; min-width: 200px;">
                            <input type="text" id="searchInput" placeholder="搜索代码或名称..." 
                                   style="width: 100%; padding: 10px; border: 2px solid #667eea; border-radius: 8px; font-size: 14px;">
                        </div>
                        <div>
                            <select id="patternFilter" style="padding: 10px; border: 2px solid #667eea; border-radius: 8px; font-size: 14px;">
                                <option value="">所有形态</option>
                                <option value="高开低走">高开低走型</option>
                                <option value="低开高走">低开高走型</option>
                                <option value="V型反转">V型反转</option>
                                <option value="倒V型">倒V型</option>
                                <option value="单边上涨">单边上涨</option>
                                <option value="单边下跌">单边下跌</option>
                                <option value="震荡">震荡</option>
                                <option value="平淡">平淡走势</option>
                            </select>
                        </div>
                        <div>
                            <select id="sessionFilter" style="padding: 10px; border: 2px solid #667eea; border-radius: 8px; font-size: 14px;">
                                <option value="">所有早午盘</option>
                                <option value="早盘高">早盘高</option>
                                <option value="午盘高">午盘高</option>
                                <option value="持平">持平</option>
                            </select>
                        </div>
                        <div>
                            <button onclick="resetFilters()" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">
                                重置筛选
                            </button>
                        </div>
                    </div>
                    <div style="margin-top: 10px; color: #666; font-size: 14px;">
                        显示 <span id="displayCount">0</span> / <span id="totalCount">{len(display_df)}</span> 条记录
                    </div>
                </div>
                
                <table id="dataTable">
                    <thead>
                        <tr>
                            <th onclick="sortTable(0)" style="cursor: pointer;">代码 ▼</th>
                            <th onclick="sortTable(1)" style="cursor: pointer;">名称 ▼</th>
                            <th onclick="sortTable(2)" style="cursor: pointer;">形态 ▼</th>
                            <th onclick="sortTable(3)" style="cursor: pointer;">开盘涨跌 ▼</th>
                            <th onclick="sortTable(4)" style="cursor: pointer;">日内涨跌 ▼</th>
                            <th onclick="sortTable(5)" style="cursor: pointer;">全天涨跌 ▼</th>
                            <th onclick="sortTable(6)" style="cursor: pointer;">振幅 ▼</th>
                            <th onclick="sortTable(7)" style="cursor: pointer;">早午盘 ▼</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">
        """
        
        for idx, row in display_df.iterrows():
            # 判断形态类型
            if '低开高走' in row['pattern_name'] or 'V型反转' in row['pattern_name'] or '单边上涨' in row['pattern_name']:
                badge_class = 'badge-bullish'
            elif '高开低走' in row['pattern_name'] or '倒V型' in row['pattern_name'] or '单边下跌' in row['pattern_name']:
                badge_class = 'badge-bearish'
            else:
                badge_class = 'badge-neutral'
            
            open_class = 'positive' if row['open_change_pct'] > 0 else 'negative' if row['open_change_pct'] < 0 else 'neutral'
            intraday_class = 'positive' if row['intraday_change_pct'] > 0 else 'negative' if row['intraday_change_pct'] < 0 else 'neutral'
            total_class = 'positive' if row['total_change_pct'] > 0 else 'negative' if row['total_change_pct'] < 0 else 'neutral'
            
            # 早午盘标签
            session_trend = row.get('session_trend', '未知')
            if session_trend == '早盘高':
                session_badge = '<span class="badge badge-bearish">早盘高</span>'
            elif session_trend == '午盘高':
                session_badge = '<span class="badge badge-bullish">午盘高</span>'
            else:
                session_badge = '<span class="badge badge-neutral">持平</span>'
            
            html += f"""
                        <tr class="data-row" 
                            data-code="{row['code']}" 
                            data-name="{row.get('name', 'N/A')}" 
                            data-pattern="{row['pattern_name']}"
                            data-session="{session_trend}">
                            <td>{row['code']}</td>
                            <td>{row.get('name', 'N/A')}</td>
                            <td><span class="badge {badge_class}">{row['pattern_name']}</span></td>
                            <td class="{open_class}">{row['open_change_pct']:+.2f}%</td>
                            <td class="{intraday_class}">{row['intraday_change_pct']:+.2f}%</td>
                            <td class="{total_class}">{row['total_change_pct']:+.2f}%</td>
                            <td>{row['amplitude']:.2f}%</td>
                            <td>{session_badge}</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
                
                <!-- 分页控件 -->
                <div id="pagination" style="margin-top: 20px; text-align: center;">
                    <button onclick="changePage(-1)" style="padding: 10px 20px; margin: 0 5px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;">
                        上一页
                    </button>
                    <span id="pageInfo" style="margin: 0 20px; font-size: 16px; font-weight: bold;">第 1 页</span>
                    <button onclick="changePage(1)" style="padding: 10px 20px; margin: 0 5px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;">
                        下一页
                    </button>
                    <select id="pageSize" onchange="changePageSize()" style="margin-left: 20px; padding: 10px; border: 2px solid #667eea; border-radius: 8px;">
                        <option value="50">每页50条</option>
                        <option value="100" selected>每页100条</option>
                        <option value="200">每页200条</option>
                        <option value="500">每页500条</option>
                        <option value="-1">显示全部</option>
                    </select>
                </div>
                
                <script>
                    // 全局变量
                    let allRows = [];
                    let filteredRows = [];
                    let currentPage = 1;
                    let pageSize = 100;
                    let sortColumn = -1;
                    let sortAscending = true;
                    
                    // 初始化
                    document.addEventListener('DOMContentLoaded', function() {
                        allRows = Array.from(document.querySelectorAll('.data-row'));
                        filteredRows = [...allRows];
                        updateDisplay();
                        
                        // 添加搜索事件监听
                        document.getElementById('searchInput').addEventListener('input', filterData);
                        document.getElementById('patternFilter').addEventListener('change', filterData);
                        document.getElementById('sessionFilter').addEventListener('change', filterData);
                    });
                    
                    // 筛选数据
                    function filterData() {
                        const searchText = document.getElementById('searchInput').value.toLowerCase();
                        const patternFilter = document.getElementById('patternFilter').value;
                        const sessionFilter = document.getElementById('sessionFilter').value;
                        
                        filteredRows = allRows.filter(row => {
                            const code = row.dataset.code.toLowerCase();
                            const name = row.dataset.name.toLowerCase();
                            const pattern = row.dataset.pattern;
                            const session = row.dataset.session;
                            
                            // 搜索筛选
                            const matchSearch = !searchText || code.includes(searchText) || name.includes(searchText);
                            
                            // 形态筛选
                            const matchPattern = !patternFilter || pattern.includes(patternFilter);
                            
                            // 早午盘筛选
                            const matchSession = !sessionFilter || session === sessionFilter;
                            
                            return matchSearch && matchPattern && matchSession;
                        });
                        
                        currentPage = 1;
                        updateDisplay();
                    }
                    
                    // 重置筛选
                    function resetFilters() {
                        document.getElementById('searchInput').value = '';
                        document.getElementById('patternFilter').value = '';
                        document.getElementById('sessionFilter').value = '';
                        filterData();
                    }
                    
                    // 排序表格
                    function sortTable(columnIndex) {
                        if (sortColumn === columnIndex) {
                            sortAscending = !sortAscending;
                        } else {
                            sortColumn = columnIndex;
                            sortAscending = true;
                        }
                        
                        filteredRows.sort((a, b) => {
                            const cellA = a.cells[columnIndex].textContent.trim();
                            const cellB = b.cells[columnIndex].textContent.trim();
                            
                            // 尝试作为数字比较
                            const numA = parseFloat(cellA.replace(/[^0-9.-]/g, ''));
                            const numB = parseFloat(cellB.replace(/[^0-9.-]/g, ''));
                            
                            let comparison = 0;
                            if (!isNaN(numA) && !isNaN(numB)) {
                                comparison = numA - numB;
                            } else {
                                comparison = cellA.localeCompare(cellB, 'zh-CN');
                            }
                            
                            return sortAscending ? comparison : -comparison;
                        });
                        
                        updateDisplay();
                    }
                    
                    // 更改页码
                    function changePage(delta) {
                        const totalPages = Math.ceil(filteredRows.length / pageSize);
                        currentPage = Math.max(1, Math.min(currentPage + delta, totalPages));
                        updateDisplay();
                    }
                    
                    // 更改每页显示数量
                    function changePageSize() {
                        const newSize = parseInt(document.getElementById('pageSize').value);
                        pageSize = newSize === -1 ? filteredRows.length : newSize;
                        currentPage = 1;
                        updateDisplay();
                    }
                    
                    // 更新显示
                    function updateDisplay() {
                        const tbody = document.getElementById('tableBody');
                        tbody.innerHTML = '';
                        
                        // 计算分页
                        const start = (currentPage - 1) * pageSize;
                        const end = pageSize === filteredRows.length ? filteredRows.length : Math.min(start + pageSize, filteredRows.length);
                        const displayRows = filteredRows.slice(start, end);
                        
                        // 显示数据
                        displayRows.forEach(row => {
                            tbody.appendChild(row.cloneNode(true));
                        });
                        
                        // 更新统计信息
                        document.getElementById('displayCount').textContent = filteredRows.length;
                        
                        // 更新分页信息
                        const totalPages = Math.ceil(filteredRows.length / pageSize);
                        document.getElementById('pageInfo').textContent = 
                            pageSize === filteredRows.length 
                            ? `显示全部 ${filteredRows.length} 条` 
                            : `第 ${currentPage} / ${totalPages} 页 (${start + 1}-${end})`;
                    }
                </script>
            </div>
        """
        
        return html

