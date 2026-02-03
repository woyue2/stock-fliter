# -*- coding: utf-8 -*-
"""
HTML 报告生成器

功能：
- 生成总览页（summary.html）
- 生成各级别详情页（三周期九底.html, 双周期九底.html, 单周期九底.html）
- localStorage 记住已选股票
- iframe 框架显示东方财富行情
- 板块/行业统计
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


class HTMLReporter:
    """HTML 报告生成器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
    
    # 定义所有可能的级别（按优先级排序）
    ALL_LEVELS = [
        "三周期9底", "双周期9底", "单周期9底",
        "3周期8底", "2周期8底", "1周期8底",
        "3周期7底", "2周期7底", "1周期7底",
    ]
    
    def generate(self, df: pd.DataFrame, title: str = "TD底部分析报告") -> Path:
        """
        生成 HTML 报告
        
        Args:
            df: 分析结果 DataFrame
            title: 报告标题
            
        Returns:
            总览页路径
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.output_dir / f"html_{ts}"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # 收集可用级别
        available_levels = []
        if "共振级别" in df.columns:
            level_counts = df["共振级别"].value_counts()
            for level in self.ALL_LEVELS:
                if level in level_counts.index and level_counts[level] > 0:
                    available_levels.append(level)
        
        # 生成总览页
        summary_path = self._generate_summary(df, report_dir, title, available_levels)
        
        # 生成各级别详情页
        for level in available_levels:
            sub_df = df[df["共振级别"] == level]
            self._generate_detail_page(sub_df, report_dir, level, available_levels)
        
        return summary_path
    
    def _generate_summary(self, df: pd.DataFrame, report_dir: Path, title: str, available_levels: list) -> Path:
        """生成总览页"""
        # 统计各级别数量
        level_counts = {}
        if "共振级别" in df.columns:
            counts = df["共振级别"].value_counts()
            for level in self.ALL_LEVELS:
                level_counts[level] = counts.get(level, 0)
        
        # 构建链接卡片（按9底、8底、7底分组）
        level_cards = ""
        
        # 9底组
        group_9 = [("三周期9底", "🔥"), ("双周期9底", "⚡"), ("单周期9底", "💎")]
        cards_9 = ""
        for level, icon in group_9:
            count = level_counts.get(level, 0)
            if count > 0:
                cards_9 += f'''
                <div class="card card-9" onclick="goToLevel('{level}')">
                    <div class="card-icon">{icon}</div>
                    <div class="card-title">{level}</div>
                    <div class="card-count">{count}</div>
                </div>
                '''
        
        # 8底组
        group_8 = [("3周期8底", ""), ("2周期8底", ""), ("1周期8底", "")]
        cards_8 = ""
        for level, icon in group_8:
            count = level_counts.get(level, 0)
            if count > 0:
                cards_8 += f'''
                <div class="card card-8" onclick="goToLevel('{level}')">
                    <div class="card-title">{level}</div>
                    <div class="card-count">{count}</div>
                </div>
                '''
        
        # 7底组
        group_7 = [("3周期7底", ""), ("2周期7底", ""), ("1周期7底", "")]
        cards_7 = ""
        for level, icon in group_7:
            count = level_counts.get(level, 0)
            if count > 0:
                cards_7 += f'''
                <div class="card card-7" onclick="goToLevel('{level}')">
                    <div class="card-title">{level}</div>
                    <div class="card-count">{count}</div>
                </div>
                '''
        
        # 组装卡片区域
        if cards_9:
            level_cards += f'<div class="card-group"><h3>9底信号</h3><div class="cards">{cards_9}</div></div>'
        if cards_8:
            level_cards += f'<div class="card-group"><h3>8底信号</h3><div class="cards">{cards_8}</div></div>'
        if cards_7:
            level_cards += f'<div class="card-group"><h3>7底信号</h3><div class="cards">{cards_7}</div></div>'
        
        # 生成可用级别的 JS 数组
        available_levels_js = str(available_levels).replace("'", "\"")
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 40px 20px;
            color: #fff;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .timestamp {{
            text-align: center;
            color: #888;
            margin-bottom: 40px;
        }}
        .overview {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 40px;
            text-align: center;
        }}
        .overview h2 {{
            color: #00d9ff;
            margin-bottom: 20px;
        }}
        .total {{
            font-size: 4em;
            font-weight: bold;
            background: linear-gradient(90deg, #ff6b6b, #feca57);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .cards {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 40px;
        }}
        .card {{
            background: rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 30px 40px;
            text-decoration: none;
            color: #fff;
            transition: all 0.3s ease;
            text-align: center;
            min-width: 150px;
            cursor: pointer;
        }}
        .card:hover {{
            transform: translateY(-5px);
            background: rgba(255,255,255,0.15);
            box-shadow: 0 10px 30px rgba(0,217,255,0.2);
        }}
        .card-9 {{ border: 2px solid #ff6b6b; }}
        .card-9:hover {{ box-shadow: 0 10px 30px rgba(255,107,107,0.3); }}
        .card-8 {{ border: 2px solid #feca57; }}
        .card-8:hover {{ box-shadow: 0 10px 30px rgba(254,202,87,0.3); }}
        .card-7 {{ border: 2px solid #00d9ff; }}
        .card-7:hover {{ box-shadow: 0 10px 30px rgba(0,217,255,0.3); }}
        .card-icon {{
            font-size: 2em;
            margin-bottom: 5px;
        }}
        .card-title {{
            font-size: 1em;
            color: #fff;
            margin-bottom: 5px;
        }}
        .card-count {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        .card-group {{
            margin-bottom: 30px;
        }}
        .card-group h3 {{
            text-align: center;
            color: #888;
            margin-bottom: 15px;
            font-size: 1em;
        }}
        footer {{
            text-align: center;
            color: #666;
            margin-top: 40px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p class="timestamp">生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        {level_cards}
        
        <footer>
            <p>点击卡片查看详情 | TD底部分析系统</p>
        </footer>
    </div>
    
    <script>
        const availableLevels = {available_levels_js};
        
        function goToLevel(level) {{
            if (availableLevels.includes(level)) {{
                window.location.href = level + '.html';
            }} else {{
                alert('暂无' + level + '的股票');
            }}
        }}
    </script>
</body>
</html>
'''
        
        path = report_dir / "summary.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    
    def _generate_detail_page(self, df: pd.DataFrame, report_dir: Path, level: str, available_levels: list) -> Path:
        """生成详情页"""
        # 生成可用级别的 JS 数组
        available_levels_js = str(available_levels).replace("'", "\"")
        
        # 生成导航链接
        nav_links = '<a href="summary.html">← 返回总览</a>'
        for lvl in self.ALL_LEVELS:
            short_name = lvl.replace("周期", "")
            nav_links += f' <a href="javascript:void(0)" onclick="goToLevel(\'{lvl}\')">{short_name}</a>'
        
        # 生成表格行
        rows_html = ""
        for idx, row in df.iterrows():
            code = row.get("代码", "")
            name = row.get("名称", "")
            board = row.get("板块", "")
            industry = row.get("行业", "")
            daily_td = row.get("日TD计数", 0)
            weekly_td = row.get("周TD计数", 0)
            monthly_td = row.get("月TD计数", 0)
            detail = row.get("底部详情", "")
            latest_price = row.get("日最新价", "")
            
            # 构建东方财富链接
            if code.startswith("6"):
                em_code = f"sh{code}"  # 上海
            else:
                em_code = f"sz{code}"  # 深圳
            em_url = f"https://quote.eastmoney.com/{em_code}.html"
            
            rows_html += f'''
            <tr data-code="{code}">
                <td>
                    <input type="checkbox" class="stock-check" data-code="{code}" 
                           onchange="toggleCheck('{code}')">
                </td>
                <td>
                    <span class="code-link" onclick="showStock('{em_url}', '{code}')">{code}</span>
                </td>
                <td>{name}</td>
                <td><span class="tag tag-board">{board}</span></td>
                <td><span class="tag tag-industry">{industry}</span></td>
                <td><span class="td-value td-{self._get_td_class(daily_td)}">{daily_td}</span></td>
                <td><span class="td-value td-{self._get_td_class(weekly_td)}">{weekly_td}</span></td>
                <td><span class="td-value td-{self._get_td_class(monthly_td)}">{monthly_td}</span></td>
                <td><span class="detail-tag">{detail}</span></td>
                <td>{latest_price}</td>
            </tr>
            '''
        
        # 板块统计
        board_stats_html = self._generate_board_stats(df)
        
        # 行业统计
        industry_stats_html = self._generate_industry_stats(df)
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{level} - TD九底分析</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }}
        .layout {{
            display: flex;
            height: 100vh;
        }}
        .sidebar {{
            width: 50%;
            padding: 20px;
            overflow-y: auto;
            border-right: 1px solid rgba(255,255,255,0.1);
        }}
        .main {{
            width: 50%;
            display: flex;
            flex-direction: column;
        }}
        h1 {{
            font-size: 1.8em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .nav {{
            margin-bottom: 20px;
        }}
        .nav a {{
            color: #00d9ff;
            text-decoration: none;
            margin-right: 20px;
        }}
        .nav a:hover {{
            text-decoration: underline;
        }}
        .stats-section {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .stats-title {{
            color: #00d9ff;
            font-size: 1em;
            margin-bottom: 10px;
        }}
        .stats-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .stat-item {{
            background: rgba(255,255,255,0.08);
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 0.85em;
        }}
        .stat-count {{
            color: #feca57;
            font-weight: bold;
        }}
        .controls {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .btn {{
            background: rgba(0,217,255,0.2);
            border: 1px solid #00d9ff;
            color: #00d9ff;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
        }}
        .btn:hover {{
            background: rgba(0,217,255,0.3);
        }}
        .search-box {{
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            padding: 8px 12px;
            border-radius: 8px;
            color: #fff;
            width: 150px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        th, td {{
            padding: 10px 8px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{
            background: rgba(0,217,255,0.15);
            color: #00d9ff;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        tr.checked {{
            background: rgba(0,255,136,0.1);
        }}
        .code-link {{
            color: #00d9ff;
            cursor: pointer;
            text-decoration: underline;
        }}
        .tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
        }}
        .tag-board {{
            background: rgba(255,107,107,0.3);
            color: #ff6b6b;
        }}
        .tag-industry {{
            background: rgba(254,202,87,0.3);
            color: #feca57;
        }}
        .td-value {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
        }}
        .td-high {{ background: rgba(0,255,136,0.3); color: #00ff88; }}
        .td-mid {{ background: rgba(254,202,87,0.3); color: #feca57; }}
        .td-low {{ background: rgba(255,255,255,0.1); color: #888; }}
        .detail-tag {{
            background: rgba(0,217,255,0.2);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8em;
            color: #00d9ff;
        }}
        .iframe-container {{
            flex: 1;
            background: #fff;
        }}
        .iframe-placeholder {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #888;
            background: rgba(255,255,255,0.03);
        }}
        iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
        .checked-count {{
            color: #00ff88;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="layout">
        <div class="sidebar">
            <div class="nav">
                {nav_links}
            </div>
            
            <h1>{level}</h1>
            <p style="color:#888; margin-bottom:20px;">共 {len(df)} 只股票</p>
            
            {board_stats_html}
            
            {industry_stats_html}
            
            <div class="controls">
                <button class="btn" onclick="selectAll()">全选</button>
                <button class="btn" onclick="clearAll()">清除</button>
                <button class="btn" onclick="exportChecked()">导出已选</button>
                <input type="text" class="search-box" placeholder="搜索..." oninput="filterTable(this.value)">
                <span class="checked-count" id="checkedCount">已选: 0</span>
            </div>
            
            <table id="stockTable">
                <thead>
                    <tr>
                        <th></th>
                        <th>代码</th>
                        <th>名称</th>
                        <th>板块</th>
                        <th>行业</th>
                        <th>日TD</th>
                        <th>周TD</th>
                        <th>月TD</th>
                        <th>底部详情</th>
                        <th>最新价</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        
        <div class="main">
            <div class="iframe-container" id="iframeContainer">
                <div class="iframe-placeholder">
                    <p>👈 点击左侧股票代码查看行情</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const STORAGE_KEY = 'td_checked_stocks_{level.replace(" ", "_")}';
        
        // 初始化
        document.addEventListener('DOMContentLoaded', () => {{
            loadCheckedStocks();
            updateCheckedCount();
        }});
        
        function loadCheckedStocks() {{
            const checked = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            checked.forEach(code => {{
                const checkbox = document.querySelector(`input[data-code="${{code}}"]`);
                if (checkbox) {{
                    checkbox.checked = true;
                    checkbox.closest('tr').classList.add('checked');
                }}
            }});
        }}
        
        function saveCheckedStocks() {{
            const checked = [];
            document.querySelectorAll('.stock-check:checked').forEach(cb => {{
                checked.push(cb.dataset.code);
            }});
            localStorage.setItem(STORAGE_KEY, JSON.stringify(checked));
            updateCheckedCount();
        }}
        
        function toggleCheck(code) {{
            const tr = document.querySelector(`tr[data-code="${{code}}"]`);
            const checkbox = tr.querySelector('.stock-check');
            tr.classList.toggle('checked', checkbox.checked);
            saveCheckedStocks();
        }}
        
        function updateCheckedCount() {{
            const count = document.querySelectorAll('.stock-check:checked').length;
            document.getElementById('checkedCount').textContent = `已选: ${{count}}`;
        }}
        
        function selectAll() {{
            document.querySelectorAll('.stock-check').forEach(cb => {{
                cb.checked = true;
                cb.closest('tr').classList.add('checked');
            }});
            saveCheckedStocks();
        }}
        
        function clearAll() {{
            document.querySelectorAll('.stock-check').forEach(cb => {{
                cb.checked = false;
                cb.closest('tr').classList.remove('checked');
            }});
            saveCheckedStocks();
        }}
        
        function exportChecked() {{
            const checked = [];
            document.querySelectorAll('.stock-check:checked').forEach(cb => {{
                const tr = cb.closest('tr');
                const code = cb.dataset.code;
                const name = tr.cells[2].textContent;
                checked.push(`${{code}},${{name}}`);
            }});
            
            if (checked.length === 0) {{
                alert('请先选择股票');
                return;
            }}
            
            const blob = new Blob([checked.join('\\n')], {{ type: 'text/csv' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{level}_已选.csv';
            a.click();
        }}
        
        function filterTable(keyword) {{
            keyword = keyword.toLowerCase();
            document.querySelectorAll('#stockTable tbody tr').forEach(tr => {{
                const text = tr.textContent.toLowerCase();
                tr.style.display = text.includes(keyword) ? '' : 'none';
            }});
        }}
        
        function showStock(url, code) {{
            document.getElementById('iframeContainer').innerHTML = 
                `<iframe src="${{url}}" title="${{code}}"></iframe>`;
        }}
        
        const availableLevels = {available_levels_js};
        
        function goToLevel(level) {{
            if (availableLevels.includes(level)) {{
                window.location.href = level + '.html';
            }} else {{
                alert('暂无' + level + '的股票');
            }}
        }}
    </script>
</body>
</html>
'''
        
        path = report_dir / f"{level}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    
    def _generate_board_stats(self, df: pd.DataFrame) -> str:
        """生成板块统计 HTML"""
        if "板块" not in df.columns:
            return ""
        
        stats = df["板块"].value_counts()
        items = ""
        for board, count in stats.items():
            pct = count / len(df) * 100
            items += f'<span class="stat-item">{board}: <span class="stat-count">{count}</span> ({pct:.1f}%)</span>'
        
        return f'''
        <div class="stats-section">
            <div class="stats-title">📊 板块分布</div>
            <div class="stats-grid">{items}</div>
        </div>
        '''
    
    def _generate_industry_stats(self, df: pd.DataFrame) -> str:
        """生成行业统计 HTML"""
        if "行业" not in df.columns:
            return ""
        
        stats = df["行业"].value_counts().head(15)
        items = ""
        for industry, count in stats.items():
            pct = count / len(df) * 100
            items += f'<span class="stat-item">{industry}: <span class="stat-count">{count}</span> ({pct:.1f}%)</span>'
        
        return f'''
        <div class="stats-section">
            <div class="stats-title">🏭 行业分布 (Top 15)</div>
            <div class="stats-grid">{items}</div>
        </div>
        '''
    
    def _get_td_class(self, value: int) -> str:
        """根据TD值返回CSS类"""
        if value >= 9:
            return "high"
        elif value >= 7:
            return "mid"
        return "low"
