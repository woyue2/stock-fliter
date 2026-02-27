#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量形态分析 - 快速了解市场整体情况

使用方法：
python batch_analyze.py                    # 分析所有有数据的股票
python batch_analyze.py --sample 100      # 随机采样100只
python batch_analyze.py --top 20          # 显示TOP20强势/弱势股
python batch_analyze.py --save            # 保存详细结果
python batch_analyze.py --html            # 生成HTML报告
"""
from __future__ import annotations
import argparse
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

from minute_pattern_analyzer import MinutePatternAnalyzer, MinuteDataLoader


class MinuteDataHTMLReporter:
    """分钟数据HTML报告生成器"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, df: pd.DataFrame, stats: dict, date_str: str = None) -> Path:
        """
        生成HTML报告

        Args:
            df: 分析结果DataFrame
            stats: 统计信息字典
            date_str: 日期字符串

        Returns:
            报告文件路径
        """
        if df.empty:
            raise ValueError("分析结果为空")

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"minute_analysis_{timestamp}.html"
        filepath = self.output_dir / filename

        # 生成HTML
        html = self._generate_html(df, stats, date_str)

        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return filepath

    def _generate_html(self, df: pd.DataFrame, stats: dict, date_str: str = None) -> str:
        """生成HTML内容"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>分钟数据形态分析 - {date_str}</title>
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
            cursor: pointer;
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
            <h1>📊 分钟数据形态分析</h1>
            <div class="date">{date_str}</div>
        </div>

        <div class="content">
            {self._generate_summary_section(df, stats)}
            {self._generate_pattern_distribution_section(df)}
            {self._generate_top_patterns_section(df)}
            {self._generate_detailed_table_section(df)}
        </div>

        <div class="footer">
            生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""

        return html

    def _generate_summary_section(self, df: pd.DataFrame, stats: dict) -> str:
        """生成概览部分"""
        total = len(df)
        avg_return = df['return'].mean()
        up_count = len(df[df['return'] > 0])
        down_count = len(df[df['return'] < 0])

        # 判断市场情绪
        if avg_return > 1:
            sentiment_label = "强势"
            sentiment_class = "bullish"
        elif avg_return > 0.3:
            sentiment_label = "偏强"
            sentiment_class = "bullish"
        elif avg_return > -0.3:
            sentiment_label = "震荡"
            sentiment_class = "neutral"
        elif avg_return > -1:
            sentiment_label = "偏弱"
            sentiment_class = "bearish"
        else:
            sentiment_label = "弱势"
            sentiment_class = "bearish"

        minute_count = len(df[df['data_source'] == 'minute'])

        html = f"""
            <div class="section">
                <div class="summary">
                    <div class="summary-card">
                        <div class="label">分析股票数</div>
                        <div class="value">{total}</div>
                    </div>

                    <div class="summary-card bullish">
                        <div class="label">上涨股票</div>
                        <div class="value">{up_count}</div>
                        <div class="label">{up_count/total*100:.1f}%</div>
                    </div>

                    <div class="summary-card bearish">
                        <div class="label">下跌股票</div>
                        <div class="value">{down_count}</div>
                        <div class="label">{down_count/total*100:.1f}%</div>
                    </div>

                    <div class="summary-card {sentiment_class}">
                        <div class="label">市场情绪</div>
                        <div class="value">{sentiment_label}</div>
                    </div>

                    <div class="summary-card neutral">
                        <div class="label">平均收益</div>
                        <div class="value">{avg_return:+.2f}%</div>
                    </div>

                    <div class="summary-card neutral">
                        <div class="label">平均波动率</div>
                        <div class="value">{df['volatility'].mean():.2f}%</div>
                    </div>

                    <div class="summary-card neutral">
                        <div class="label">数据来源</div>
                        <div class="value">{minute_count}</div>
                        <div class="label">真实分钟数据</div>
                    </div>
                </div>
            </div>
        """

        return html

    def _generate_pattern_distribution_section(self, df: pd.DataFrame) -> str:
        """生成形态分布部分"""
        pattern_counts = df['pattern'].value_counts()
        total = len(df)

        html = """
            <div class="section">
                <h2 class="section-title">形态分布</h2>
                <div class="pattern-grid">
        """

        for pattern, count in pattern_counts.items():
            percentage = count / total * 100

            html += f"""
                    <div class="pattern-card">
                        <div class="pattern-name">{pattern}</div>
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

    def _generate_top_patterns_section(self, df: pd.DataFrame) -> str:
        """生成TOP案例部分"""
        html = """
            <div class="section">
                <h2 class="section-title">TOP 10 强势股</h2>
                <table>
                    <thead>
                        <tr>
                            <th>代码</th>
                            <th>形态</th>
                            <th>日内收益</th>
                            <th>波动率</th>
                            <th>数据来源</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        top_up = df.nlargest(10, 'return')
        for idx, row in top_up.iterrows():
            return_class = 'positive' if row['return'] > 0 else 'negative' if row['return'] < 0 else 'neutral'
            marker = "✓" if row['data_source'] == 'minute' else "~"

            html += f"""
                        <tr>
                            <td>{row['code']}</td>
                            <td>{row['pattern']}</td>
                            <td class="{return_class}">{row['return']:+.2f}%</td>
                            <td>{row['volatility']:.2f}%</td>
                            <td>{marker}</td>
                        </tr>
            """

        html += """
                    </tbody>
                </table>

                <h2 class="section-title" style="margin-top: 40px;">TOP 10 弱势股</h2>
                <table>
                    <thead>
                        <tr>
                            <th>代码</th>
                            <th>形态</th>
                            <th>日内收益</th>
                            <th>波动率</th>
                            <th>数据来源</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        top_down = df.nsmallest(10, 'return')
        for idx, row in top_down.iterrows():
            return_class = 'positive' if row['return'] > 0 else 'negative' if row['return'] < 0 else 'neutral'
            marker = "✓" if row['data_source'] == 'minute' else "~"

            html += f"""
                        <tr>
                            <td>{row['code']}</td>
                            <td>{row['pattern']}</td>
                            <td class="{return_class}">{row['return']:+.2f}%</td>
                            <td>{row['volatility']:.2f}%</td>
                            <td>{marker}</td>
                        </tr>
            """

        html += """
                    </tbody>
                </table>
            </div>
        """

        return html

    def _generate_detailed_table_section(self, df: pd.DataFrame) -> str:
        """生成详细数据表格部分"""
        html = f"""
            <div class="section">
                <h2 class="section-title">详细数据 (共{len(df)}条)</h2>

                <!-- 搜索工具栏 -->
                <div style="margin-bottom: 20px; padding: 20px; background: #f8f9ff; border-radius: 10px;">
                    <div style="display: flex; gap: 15px; flex-wrap: wrap; align-items: center;">
                        <div style="flex: 1; min-width: 200px;">
                            <input type="text" id="searchInput" placeholder="搜索股票代码..."
                                   style="width: 100%; padding: 10px; border: 2px solid #667eea; border-radius: 8px; font-size: 14px;">
                        </div>
                        <div>
                            <select id="patternFilter" style="padding: 10px; border: 2px solid #667eea; border-radius: 8px; font-size: 14px;">
                                <option value="">所有形态</option>
        """

        # 添加形态筛选选项
        for pattern in sorted(df['pattern'].unique()):
            html += f'                                <option value="{pattern}">{pattern}</option>\n'

        html += """
                            </select>
                        </div>
                        <div>
                            <button onclick="resetFilters()" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">
                                重置筛选
                            </button>
                        </div>
                    </div>
                    <div style="margin-top: 10px; color: #666; font-size: 14px;">
                        显示 <span id="displayCount">0</span> / <span id="totalCount">{}</span> 条记录
                    </div>
                </div>

                <table id="dataTable">
                    <thead>
                        <tr>
                            <th onclick="sortTable(0)" style="cursor: pointer;">代码 ▼</th>
                            <th onclick="sortTable(1)" style="cursor: pointer;">形态 ▼</th>
                            <th onclick="sortTable(2)" style="cursor: pointer;">日内收益 ▼</th>
                            <th onclick="sortTable(3)" style="cursor: pointer;">波动率 ▼</th>
                            <th onclick="sortTable(4)" style="cursor: pointer;">数据来源 ▼</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">
        """.format(len(df))

        for idx, row in df.iterrows():
            # 判断形态类型
            if '上涨' in row['pattern'] or '反转' in row['pattern'] and '倒' not in row['pattern']:
                badge_class = 'badge-bullish'
            elif '下跌' in row['pattern'] or '倒V' in row['pattern']:
                badge_class = 'badge-bearish'
            else:
                badge_class = 'badge-neutral'

            return_class = 'positive' if row['return'] > 0 else 'negative' if row['return'] < 0 else 'neutral'
            data_source = '✓ 真实分钟' if row['data_source'] == 'minute' else '~ 日K估算'

            html += f"""
                        <tr class="data-row"
                            data-code="{row['code']}"
                            data-pattern="{row['pattern']}">
                            <td>{row['code']}</td>
                            <td><span class="badge {badge_class}">{row['pattern']}</span></td>
                            <td class="{return_class}">{row['return']:+.2f}%</td>
                            <td>{row['volatility']:.2f}%</td>
                            <td>{data_source}</td>
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
                    document.addEventListener('DOMContentLoaded', function() {{
                        allRows = Array.from(document.querySelectorAll('.data-row'));
                        filteredRows = [...allRows];
                        updateDisplay();

                        // 添加搜索事件监听
                        document.getElementById('searchInput').addEventListener('input', filterData);
                        document.getElementById('patternFilter').addEventListener('change', filterData);
                    }});

                    // 筛选数据
                    function filterData() {{
                        const searchText = document.getElementById('searchInput').value.toLowerCase();
                        const patternFilter = document.getElementById('patternFilter').value;

                        filteredRows = allRows.filter(row => {{
                            const code = row.dataset.code.toLowerCase();
                            const pattern = row.dataset.pattern;

                            // 搜索筛选
                            const matchSearch = !searchText || code.includes(searchText);

                            // 形态筛选
                            const matchPattern = !patternFilter || pattern === patternFilter;

                            return matchSearch && matchPattern;
                        }});

                        currentPage = 1;
                        updateDisplay();
                    }}

                    // 重置筛选
                    function resetFilters() {{
                        document.getElementById('searchInput').value = '';
                        document.getElementById('patternFilter').value = '';
                        filterData();
                    }}

                    // 排序表格
                    function sortTable(columnIndex) {{
                        if (sortColumn === columnIndex) {{
                            sortAscending = !sortAscending;
                        }} else {{
                            sortColumn = columnIndex;
                            sortAscending = true;
                        }}

                        filteredRows.sort((a, b) => {{
                            const cellA = a.cells[columnIndex].textContent.trim();
                            const cellB = b.cells[columnIndex].textContent.trim();

                            // 尝试作为数字比较
                            const numA = parseFloat(cellA.replace(/[^0-9.-]/g, ''));
                            const numB = parseFloat(cellB.replace(/[^0-9.-]/g, ''));

                            let comparison = 0;
                            if (!isNaN(numA) && !isNaN(numB)) {{
                                comparison = numA - numB;
                            }} else {{
                                comparison = cellA.localeCompare(cellB, 'zh-CN');
                            }}

                            return sortAscending ? comparison : -comparison;
                        }});

                        updateDisplay();
                    }}

                    // 更改页码
                    function changePage(delta) {{
                        const totalPages = Math.ceil(filteredRows.length / pageSize);
                        currentPage = Math.max(1, Math.min(currentPage + delta, totalPages));
                        updateDisplay();
                    }}

                    // 更改每页显示数量
                    function changePageSize() {{
                        const newSize = parseInt(document.getElementById('pageSize').value);
                        pageSize = newSize === -1 ? filteredRows.length : newSize;
                        currentPage = 1;
                        updateDisplay();
                    }}

                    // 更新显示
                    function updateDisplay() {{
                        const tbody = document.getElementById('tableBody');
                        tbody.innerHTML = '';

                        // 计算分页
                        const start = (currentPage - 1) * pageSize;
                        const end = pageSize === filteredRows.length ? filteredRows.length : Math.min(start + pageSize, filteredRows.length);
                        const displayRows = filteredRows.slice(start, end);

                        // 显示数据
                        displayRows.forEach(row => {{
                            tbody.appendChild(row.cloneNode(true));
                        }});

                        // 更新统计信息
                        document.getElementById('displayCount').textContent = filteredRows.length;

                        // 更新分页信息
                        const totalPages = Math.ceil(filteredRows.length / pageSize);
                        document.getElementById('pageInfo').textContent =
                            pageSize === filteredRows.length
                            ? `显示全部 ${{filteredRows.length}} 条`
                            : `第 ${{currentPage}} / ${{totalPages}} 页 (${{start + 1}}-${{end}})`;
                    }}
                </script>
            </div>
        """

        return html


def load_minute_data(code: str, data_dir: Path) -> pd.DataFrame:
    """加载分钟数据"""
    akshare_dir = data_dir / "minute_akshare"
    file_path = akshare_dir / f"{code}.csv"
    
    if file_path.exists():
        df = pd.read_csv(file_path)
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        return df
    return pd.DataFrame()


def load_daily_data(code: str, data_dir: Path) -> pd.DataFrame:
    """加载日K数据"""
    file_path = data_dir / f"{code}.csv"
    if not file_path.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(file_path, encoding='utf-8-sig')
    
    if '日期' in df.columns:
        df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close', 
                               '最高': 'high', '最低': 'low'})
    
    for col in ['open', 'close', 'high', 'low']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    return df.sort_values('date').reset_index(drop=True)


def analyze_stock(code: str, raw_dir: Path, minute_dir: Path) -> dict:
    """分析单只股票"""
    analyzer = MinutePatternAnalyzer(normalize=True)
    loader = MinuteDataLoader(str(raw_dir))
    
    # 优先使用真实分钟数据
    minute_df = load_minute_data(code, minute_dir)
    use_minute = False
    
    if not minute_df.empty:
        # 取最后一天
        if 'datetime' in minute_df.columns:
            last_date = minute_df['datetime'].max()
            last_date_date = last_date.date()
            minute_df = minute_df[minute_df['datetime'].dt.date == last_date_date]
        
        if len(minute_df) >= 10:
            use_minute = True
    
    if use_minute:
        # 使用真实分钟数据
        vector = minute_df['close'].values
        base_price = vector[0]
        vector_norm = (vector - base_price) / base_price * 100
        
        minute_for_analysis = pd.DataFrame({'close': minute_df['close'].values})
        result = analyzer.analyze_single_stock(minute_for_analysis)
        
        return {
            'code': code,
            'pattern': result['pattern_name'],
            'return': result['features']['intraday_return'],
            'volatility': result['features']['volatility'],
            'data_source': 'minute',
            'data_points': len(minute_df)
        }
    else:
        # 使用日K估算
        df = load_daily_data(code, raw_dir)
        if df.empty:
            return None

        # estimate_minute_from_daily 已经返回归一化后的向量（百分比）
        # 直接传入分析器，不要再加开盘价
        vector = loader.estimate_minute_from_daily(df.tail(2))

        minute_df = pd.DataFrame({'close': vector})
        result = analyzer.analyze_single_stock(minute_df)
        
        return {
            'code': code,
            'pattern': result['pattern_name'],
            'return': result['features']['intraday_return'],
            'volatility': result['features']['volatility'],
            'data_source': 'daily_estimate',
            'data_points': 240
        }


def main():
    parser = argparse.ArgumentParser(
        description="批量形态分析 - 快速了解市场整体情况",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python batch_analyze.py              # 分析全部
  python batch_analyze.py --sample 100 # 采样100只
  python batch_analyze.py --top 20     # TOP20排名
  python batch_analyze.py --save       # 保存详细结果
        """
    )
    
    parser.add_argument("--sample", type=int, help="随机采样数量")
    parser.add_argument("--top", type=int, default=10, help="TOP排名数量")
    parser.add_argument("--save", action="store_true", help="保存详细结果")
    parser.add_argument("--html", action="store_true", help="生成HTML报告")
    parser.add_argument("--dir", type=str, default="../get-data/data/raw", help="数据目录")
    
    args = parser.parse_args()
    
    raw_dir = Path(__file__).resolve().parent / args.dir
    minute_dir = raw_dir.parent / "minute_akshare"
    
    print("="*70)
    print("批量形态分析 - 市场整体情况概览")
    print("="*70)
    
    # 获取股票列表
    stock_files = list(raw_dir.glob("*.csv"))
    
    if args.sample:
        import random
        random.seed(42)
        stock_files = random.sample(stock_files, min(args.sample, len(stock_files)))
    
    print(f"\n分析股票数: {len(stock_files)} 只")
    print(f"数据目录: {raw_dir}")
    print()
    
    # 批量分析
    results = []
    for i, f in enumerate(stock_files):
        code = f.stem
        result = analyze_stock(code, raw_dir, minute_dir)
        if result:
            results.append(result)
        
        if (i + 1) % 500 == 0:
            print(f"  进度: {i+1}/{len(stock_files)}")
    
    if not results:
        print("❌ 未找到有效数据")
        return
    
    df = pd.DataFrame(results)
    
    # 统计形态分布
    print("="*70)
    print("【形态分布统计】")
    print("="*70)
    
    pattern_counts = df['pattern'].value_counts()
    total = len(df)
    
    print(f"\n{'形态类型':<15} {'数量':>8} {'占比':>8}")
    print("-" * 35)
    
    for pattern, count in pattern_counts.items():
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"{pattern:<15} {count:>8} {pct:>7.1f}% {bar}")
    
    print("-" * 35)
    print(f"{'总计':<15} {total:>8}")
    
    # 整体统计
    print("\n" + "="*70)
    print("【整体市场指标】")
    print("="*70)
    
    avg_return = df['return'].mean()
    std_return = df['return'].std()
    up_count = len(df[df['return'] > 0])
    down_count = len(df[df['return'] < 0])
    
    print(f"\n平均日内收益: {avg_return:+.2f}%")
    print(f"收益标准差: {std_return:.2f}%")
    print(f"上涨/下跌: {up_count}/{down_count} ({up_count/total*100:.1f}%/{down_count/total*100:.1f}%)")
    
    # 数据来源
    minute_count = len(df[df['data_source'] == 'minute'])
    print(f"\n数据来源: 真实分钟 {minute_count} 只, 日K估算 {total - minute_count} 只")
    
    # TOP排名
    print("\n" + "="*70)
    print(f"【TOP {args.top} 强势股】")
    print("="*70)
    
    top_up = df.nlargest(args.top, 'return')
    for i, row in top_up.iterrows():
        marker = "✓" if row['data_source'] == 'minute' else "~"
        print(f"  {marker} {row['code']:<10} {row['return']:>+6.2f}%  ({row['pattern']})")
    
    print(f"\n【TOP {args.top} 弱势股】")
    print("-"*50)
    
    top_down = df.nsmallest(args.top, 'return')
    for i, row in top_down.iterrows():
        marker = "✓" if row['data_source'] == 'minute' else "~"
        print(f"  {marker} {row['code']:<10} {row['return']:>+6.2f}%  ({row['pattern']})")
    
    # 市场情绪判断
    print("\n" + "="*70)
    print("【市场情绪判断】")
    print("="*70)
    
    if avg_return > 1:
        sentiment = "🔥 偏热 - 整体上涨"
    elif avg_return > 0.3:
        sentiment = "📈 偏强 - 小幅上涨"
    elif avg_return > -0.3:
        sentiment = "➡️ 震荡 - 方向不明"
    elif avg_return > -1:
        sentiment = "📉 偏弱 - 小幅下跌"
    else:
        sentiment = "❄️ 偏冷 - 整体下跌"
    
    print(f"\n  {sentiment}")
    print(f"  上涨家数占比: {up_count/total*100:.1f}%")
    print(f"  平均波动率: {df['volatility'].mean():.2f}")
    
    # 保存结果
    if args.save or args.html:
        output_dir = Path(__file__).resolve().parent / "output"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存CSV
        if args.save:
            csv_file = output_dir / f"batch_analysis_{timestamp}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"\n✓ CSV文件已保存: {csv_file}")

        # 生成HTML报告
        if args.html:
            # 获取分析日期（使用分钟数据的最新日期）
            date_str = datetime.now().strftime('%Y-%m-%d')

            # 准备统计信息
            stats = {
                'total': len(df),
                'avg_return': df['return'].mean(),
                'std_return': df['return'].std(),
                'up_count': len(df[df['return'] > 0]),
                'down_count': len(df[df['return'] < 0]),
                'minute_count': len(df[df['data_source'] == 'minute'])
            }

            # 生成HTML报告
            reporter = MinuteDataHTMLReporter(output_dir)
            html_file = reporter.generate_report(df, stats, date_str)
            print(f"✓ HTML报告已生成: {html_file}")

    print("\n" + "="*70)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
