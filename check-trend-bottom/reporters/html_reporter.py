# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame, HTML titles and config
# OUTPUT: Path (HTML summary)
# POS:    check-trend-bottom/reporters/html_reporter.py
# -*- coding: utf-8 -*-
"""
HTML 报告生成器 - 极简风格

功能：
- 生成单页应用（summary.html）
- 左侧导航 + 右侧 iframe 展示详情
- localStorage 记住已选股票
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# 确保 util/ 可被导入
_UTIL_DIR = Path(__file__).resolve().parent.parent.parent / "util"
if str(_UTIL_DIR) not in sys.path:
    sys.path.insert(0, str(_UTIL_DIR))
from index_writer import write_to_stocks_index  # noqa: E402


class HTMLReporter:
    """HTML 报告生成器"""
    
    def __init__(self, output_dir: Path, end_date: Optional[str] = None, display_date: Optional[str] = None):
        self.output_dir = output_dir
        self.end_date = end_date
        self.display_date = display_date  # 用于在HTML title中显示的日期

    def generate(self, df: pd.DataFrame, title: str = "TD底部分析") -> Path:
        """生成 HTML 报告"""
        now = datetime.now()
        ts = now.strftime("%H%M%S")
        
        # 如果没有 display_date 和 end_date，从数据中读取日期
        if not self.display_date and not self.end_date and not df.empty:
            # 尝试从多个可能的日期列中读取
            date_columns = ["日最新日期", "周最新日期", "月最新日期", "最新日期", "日期", "交易日期", "date"]
            data_date = None
            for col in date_columns:
                if col in df.columns:
                    first_date = df[col].iloc[0]
                    if pd.notna(first_date):
                        data_date = str(first_date)
                        print(f"  [INFO] 从数据中读取到日期: {data_date}")
                        break
            
            if data_date:
                # 提取日期部分（可能是 "2024-01-30" 或 "2024-01-30 00:00:00" 格式）
                date_str = data_date.split()[0].replace("-", "")
            else:
                date_str = now.strftime("%Y%m%d")
                print(f"  [WARN] 数据中未找到日期信息，使用当前日期: {date_str}")
        else:
            # display_date 优先级最高，其次 end_date，最后使用系统日期
            date_str = (self.display_date or self.end_date or now.strftime("%Y-%m-%d")).replace("-", "")
        
        # summary_end-date_生成时间
        # 不再创建子目录，直接使用 pipeline 传入的 output_dir (已经包含 HH-MM-SS)
        report_dir = self.output_dir
        # report_dir.mkdir(parents=True, exist_ok=True) # Pipeline 已经创建了
        
        # 收集可用级别（动态从数据中获取）
        available_levels = []
        level_data = {}
        if "共振级别" in df.columns:
            counts = df["共振级别"].value_counts()
            for level, count in counts.items():
                if level != "无底部信号" and count > 0:
                    available_levels.append(level)
                    level_data[level] = count
        
        # 生成各级别详情页
        level_vols = {}
        for level in available_levels:
            sub_df = df[df["共振级别"] == level]
            self._generate_detail_page(sub_df, report_dir, level)
            # 记录波动率数据供主页过滤使用
            level_vols[level] = sub_df["波动率"].tolist()
        
        # 生成主页（带 iframe）
        summary_filename = f"summary_{date_str}_{ts}.html"
        summary_path = self._generate_summary(df, report_dir, title, available_levels, level_data, level_vols, summary_filename, date_str)
        
        # 导出到索引CSV
        self._export_to_index_csv(df, "TD九底", date_str, summary_path)
        
        return summary_path
    
    def _generate_summary(self, df: pd.DataFrame, report_dir: Path, title: str,
                          available_levels: list, level_data: dict, level_vols: dict, 
                          filename: str = "summary.html", date_str: str = None) -> Path:
        """生成主页"""

        # 按底部级别分组
        groups = {
            "(20+极限)": [],
            "(15-20极地)": [],
            "(10-15深底)": [],
            "9底": [],
            "8底": [],
            "7底": [],
            "6底": []
        }
        
        # 预先根据权重排序 available_levels
        # 获取每个 level 的代表性权重（由于同一 level 内权重可能不同，取并集中的最大值或直接用 df 辅助）
        level_weights = df.groupby("共振级别")["底部权重"].max()
        sorted_levels = sorted(available_levels, key=lambda l: level_weights.get(l, 0), reverse=True)

        for level in sorted_levels:
            found = False
            for group_key in ["(20+极限)", "(15-20极地)", "(10-15深底)"]:
                if group_key in level:
                    groups[group_key].append((level, level_data[level]))
                    found = True
                    break
            if not found:
                for single_key in ["9底", "8底", "7底", "6底"]:
                    if single_key in level:
                        groups[single_key].append((level, level_data[level]))
                        break

        # 生成导航项
        nav_items = ""
        first_level = sorted_levels[0] if sorted_levels else ""

        # 分组显示：极限->极地->深底->9->8->7->6
        display_order = ["(20+极限)", "(15-20极地)", "(10-15深底)", "9底", "8底", "7底", "6底"]
        for group_name in display_order:
            items = groups[group_name]
            if items:
                # 标题美化
                clean_name = group_name.strip("()")
                nav_items += f'<div class="nav-group">{clean_name}</div>'
                for level, count in items:
                    active = "active" if level == first_level else ""
                    nav_items += f'''
                    <div class="nav-item {active}" data-level="{level}" onclick="showLevel('{level}')">
                        <span class="level-name">{level}</span>
                        <span class="level-count">{count}</span>
                    </div>
                    '''

        available_levels_js = str(available_levels).replace("'", '"')

        # 使用 date_str 来显示标题日期（已经从数据中读取或使用 display_date/end_date）
        if date_str and len(date_str) == 8:
            display_date = date_str[:4] + "-" + date_str[4:6] + "-" + date_str[6:8]
            display_title = f"{title} - {display_date}"
        else:
            display_title = title
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{display_title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, "Microsoft YaHei", sans-serif;
            background: #f5f5f5;
            height: 100vh;
            overflow: hidden;
        }}
        .layout {{
            display: flex;
            height: 100vh;
        }}
        .sidebar {{
            width: 200px;
            background: #fff;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
        }}
        .logo {{
            padding: 20px;
            font-size: 16px;
            font-weight: 600;
            color: #333;
            border-bottom: 1px solid #e0e0e0;
        }}
        .nav {{
            flex: 1;
            overflow-y: auto;
            padding: 10px 0;
        }}
        .nav-group {{
            padding: 12px 20px 6px;
            font-size: 12px;
            color: #999;
            font-weight: 500;
        }}
        .nav-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .nav-item:hover {{
            background: #f5f5f5;
        }}
        .nav-item.active {{
            background: #e3f2fd;
            color: #1976d2;
        }}
        .level-name {{
            font-size: 14px;
        }}
        .level-count {{
            font-size: 12px;
            background: #e0e0e0;
            padding: 2px 8px;
            border-radius: 10px;
        }}
        .nav-item.active .level-count {{
            background: #1976d2;
            color: #fff;
        }}
        .main {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        .content {{
            flex: 1;
            background: #fff;
        }}
        .content iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
        .empty {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #999;
        }}
        
        .filter-panel {{
            padding: 10px 20px;
            border-bottom: 1px solid #e0e0e0;
            background: #fff;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .filter-input {{
            width: 60px;
            padding: 4px;
            border: 1px solid #ddd;
            border-radius: 4px;
            text-align: center;
        }}
        .filter-btn {{
            padding: 4px 10px;
            background: #1976d2;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        .filter-btn:hover {{ background: #1565c0; }}
        
        @media (prefers-color-scheme: dark) {{
            body {{ background: #1a1a1a; color: #e0e0e0; }}
            .sidebar {{ background: #242424; border-color: #333; }}
            .logo {{ color: #e0e0e0; border-color: #333; }}
            .nav-item {{ color: #ccc; border-color: #333; }}
            .nav-item:hover {{ background: #2e2e2e; }}
            .nav-item.active {{ background: #1e3a5f; color: #8ab4f8; border-color: #2d5a8e; }}
            .nav-group {{ color: #999; }}
            .content {{ background: #1a1a1a; }}
            .filter-panel {{ background: #242424; border-color: #333; }}
            .filter-input {{ background: #333; color: #fff; border-color: #444; }}
        }}
    </style>
</head>
<body>
    <div class="layout">
        <div class="sidebar">
            <div class="logo">📊 {title}</div>
            <div class="filter-panel" title="波动率过滤器">
                <span style="font-size:12px">波动率<</span>
                <input type="number" id="volFilter" class="filter-input" value="0.5" step="0.1" min="0">
                <button class="filter-btn" onclick="applyVolFilter()">过滤</button>
            </div>
            <div class="nav">
                {nav_items}
            </div>
        </div>
        <div class="main">
            <div class="content" id="content">
                {f'<iframe src="{first_level}.html"></iframe>' if first_level else '<div class="empty">暂无数据</div>'}
            </div>
        </div>
    </div>
    
    <script>
        const availableLevels = {available_levels_js};
        const levelVols = {str(level_vols)}; // 注入所有级别的波动率分布数据
        let currentVolLimit = null;
        
        function showLevel(level) {{
            const navItem = document.querySelector(`.nav-item[data-level="${{level}}"]`);
            if (!navItem) return;

            // 更新导航状态
            document.querySelectorAll('.nav-item').forEach(item => {{
                item.classList.remove('active');
            }});
            navItem.classList.add('active');
            
            // 更新 iframe
            if (availableLevels.includes(level)) {{
                const content = document.getElementById('content');
                content.innerHTML = `<iframe id="detailFrame" src="${{level}}.html"></iframe>`;
                
                // 等待 iframe 加载完成发送过滤指令
                const iframe = document.getElementById('detailFrame');
                iframe.onload = () => {{
                    if (currentVolLimit !== null) {{
                        iframe.contentWindow.postMessage({{ type: 'filterVol', limit: currentVolLimit }}, '*');
                    }}
                }};
            }}
        }}

        function applyVolFilter() {{
            const val = document.getElementById('volFilter').value;
            if (val === "") {{
                currentVolLimit = 999;
            }} else {{
                currentVolLimit = parseFloat(val);
            }}
            
            // 1. 立即计算并更新侧边栏所有标志位的数字
            for (const level in levelVols) {{
                const vols = levelVols[level];
                const count = vols.filter(v => v <= currentVolLimit).length;
                
                const navItem = document.querySelector(`.nav-item[data-level="${{level}}"]`);
                if (navItem) {{
                    const countBadge = navItem.querySelector('.level-count');
                    countBadge.textContent = count;
                    // 如果数量为 0，则显著淡化显示
                    navItem.style.opacity = count === 0 ? '0.2' : '1';
                }}
            }}

            // 2. 通知当前正在显示的 iframe 过滤内容
            const iframe = document.getElementById('detailFrame');
            if (iframe && iframe.contentWindow) {{
                iframe.contentWindow.postMessage({{ type: 'filterVol', limit: currentVolLimit }}, '*');
            }}
        }}

        // 监听来自详情页的反馈（如手动点击后的自同步）
        window.addEventListener('message', (event) => {{
            if (event.data && event.data.type === 'updateCount') {{
                const {{ level, count }} = event.data;
                const navItem = document.querySelector(`.nav-item[data-level="${{level}}"]`);
                if (navItem) {{
                    navItem.querySelector('.level-count').textContent = count;
                    navItem.style.opacity = count === 0 ? '0.2' : '1';
                }}
            }}
        }});
    </script>
</body>
</html>
'''
        
        path = report_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    
    def _generate_detail_page(self, df: pd.DataFrame, report_dir: Path, level: str) -> Path:
        """生成详情页（极简风格）"""
        # 按权重排序
        if "底部权重" in df.columns:
            df = df.sort_values("底部权重", ascending=False)
            
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
            vol = row.get("波动率", 0.0)
            vol_str = f"{vol:.2%}" if vol > 0 else "-"
            vol_color = self._get_vol_color(vol)
            
            # 构建东方财富链接
            if str(code).startswith("6"):
                em_code = f"sh{code}"
            else:
                em_code = f"sz{code}"
            em_url = f"https://quote.eastmoney.com/{em_code}.html"
            
            rows_html += f'''
            <tr data-code="{code}" data-vol="{vol}">
                <td><input type="checkbox" class="check" data-code="{code}" onchange="saveChecked()"></td>
                <td><a href="javascript:void(0)" onclick="showStock('{em_url}')" class="code">{code}</a></td>
                <td>{name}</td>
                <td>{board}</td>
                <td>{industry}</td>
                <td class="td td-{self._get_td_class(daily_td)}">{daily_td}</td>
                <td class="td td-{self._get_td_class(weekly_td)}">{weekly_td}</td>
                <td class="td td-{self._get_td_class(monthly_td)}">{monthly_td}</td>
                <td class="detail">{detail}</td>
                <td>{latest_price}</td>
                <td class="vol-cell" style="color: {vol_color}; font-weight: 500;">{vol_str}</td>
            </tr>
            '''
        
        # 板块统计
        board_stats = ""
        if "板块" in df.columns:
            stats = df["板块"].value_counts()
            for board, count in stats.items():
                board_stats += f'<span class="tag">{board} {count}</span>'
        
        # 行业统计
        industry_stats = ""
        if "行业" in df.columns:
            stats = df["行业"].value_counts().head(10)
            for ind, count in stats.items():
                industry_stats += f'<span class="tag">{ind} {count}</span>'
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{level}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, "Microsoft YaHei", sans-serif;
            font-size: 13px;
            color: #333;
            background: #fff;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }}
        .left-panel {{
            width: 35%;
            min-width: 400px;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #e0e0e0;
        }}
        .right-panel {{
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #fafafa;
        }}
        .right-header {{
            padding: 10px 16px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .stock-frame {{
            flex: 1;
            border: none;
            width: 100%;
        }}
        .placeholder {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
        }}
        .header {{
            padding: 16px 20px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .title {{
            font-size: 16px;
            font-weight: 600;
        }}
        .count {{
            color: #666;
        }}
        .toolbar {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .btn {{
            padding: 6px 12px;
            border: 1px solid #ddd;
            background: #fff;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        .btn:hover {{
            background: #f5f5f5;
        }}
        .search {{
            padding: 6px 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 150px;
        }}
        .stats {{
            padding: 12px 20px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .stats-group {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .stats-label {{
            font-size: 12px;
            color: #999;
            margin-right: 4px;
        }}
        .tag {{
            font-size: 11px;
            padding: 2px 6px;
            background: #f0f0f0;
            border-radius: 3px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #fafafa;
            font-weight: 500;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        tr.checked {{
            background: #e8f5e9;
        }}
        .code {{
            color: #1976d2;
            text-decoration: none;
        }}
        .code:hover {{
            text-decoration: underline;
        }}
        .td {{
            font-weight: 600;
            text-align: center;
        }}
        .td-high {{ color: #d32f2f; }}
        .td-mid {{ color: #f57c00; }}
        .td-low {{ color: #999; }}
        .detail {{
            font-size: 11px;
            color: #1976d2;
        }}
        .table-wrap {{
            overflow: auto;
            flex: 1;
        }}
        .checked-info {{
            font-size: 12px;
            color: #4caf50;
        }}
        .open-new {{
            font-size: 11px;
            color: #1976d2;
            text-decoration: none;
            cursor: pointer;
        }}
        .open-new:hover {{
            text-decoration: underline;
        }}
        @media (prefers-color-scheme: dark) {{
            body {{ background: #1a1a1a; color: #e0e0e0; }}
            .left-panel {{ border-color: #333; }}
            .right-panel {{ background: #242424; }}
            .right-header {{ border-color: #333; color: #999; background: #1f1f1f; }}
            .header {{ background: #1f1f1f; border-color: #333; }}
            .title {{ color: #e0e0e0; }}
            .count {{ color: #999; }}
            .stock-list {{ background: #1a1a1a; }}
            .stock-item {{ border-color: #333; }}
            .stock-item:hover {{ background: #2a2a2a; }}
            .stock-item.selected {{ background: #1e3a5f; border-color: #2d5a8e; }}
            .code {{ color: #8ab4f8; }}
            .name {{ color: #e0e0e0; }}
            .board {{ color: #999; }}
            .industry {{ color: #90caf9; }}
            .tag {{ background: #2a2a2a; color: #ccc; }}
            .open-new {{ color: #8ab4f8; }}
        }}
    </style>
</head>
<body>
    <div class="left-panel">
        <div class="header">
        <div>
            <span class="title">{level}</span>
            <span class="count">共 {len(df)} 只</span>
        </div>
        <div class="toolbar">
            <span class="checked-info" id="checkedInfo">已选 0</span>
            <button class="btn" onclick="selectAll()">全选</button>
            <button class="btn" onclick="clearAll()">清除</button>
            <button class="btn" onclick="exportCSV()">导出</button>
            <input type="text" class="search" placeholder="搜索..." oninput="filterTable(this.value)">
        </div>
    </div>
    
    <div class="stats">
        <div class="stats-group">
            <span class="stats-label">板块:</span>
            {board_stats}
        </div>
        <div class="stats-group">
            <span class="stats-label">行业:</span>
            {industry_stats}
        </div>
    </div>
    
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th width="30"></th>
                    <th>代码</th>
                    <th>名称</th>
                    <th>板块</th>
                    <th>行业</th>
                    <th>日TD</th>
                    <th>周TD</th>
                    <th>月TD</th>
                    <th>底部详情</th>
                    <th>最新价</th>
                    <th>波动率(Park)</th>
                </tr>
            </thead>
            <tbody id="tbody">
                {rows_html}
            </tbody>
        </table>
    </div>
    </div>
    
    <div class="right-panel">
        <div class="right-header">
            <span id="stockTitle">点击左侧股票代码查看详情</span>
            <a id="openNew" class="open-new" style="display:none" onclick="window.open(currentUrl)" title="新窗口打开">↗ 新窗口</a>
        </div>
        <div class="placeholder" id="placeholder">← 选择股票查看行情</div>
        <iframe id="stockFrame" class="stock-frame" style="display:none"></iframe>
    </div>
    
    <script>
        const STORAGE_KEY = 'td_{level.replace(" ", "_")}';
        let currentUrl = '';
        
        // 初始化
        document.addEventListener('DOMContentLoaded', loadChecked);
        
        function loadChecked() {{
            const checked = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            checked.forEach(code => {{
                const cb = document.querySelector(`input[data-code="${{code}}"]`);
                if (cb) {{
                    cb.checked = true;
                    cb.closest('tr').classList.add('checked');
                }}
            }});
            updateInfo();
        }}
        
        function saveChecked() {{
            const checked = [];
            document.querySelectorAll('.check:checked').forEach(cb => {{
                checked.push(cb.dataset.code);
                cb.closest('tr').classList.add('checked');
            }});
            document.querySelectorAll('.check:not(:checked)').forEach(cb => {{
                cb.closest('tr').classList.remove('checked');
            }});
            localStorage.setItem(STORAGE_KEY, JSON.stringify(checked));
            updateInfo();
        }}
        
        function updateInfo() {{
            const count = document.querySelectorAll('.check:checked').length;
            document.getElementById('checkedInfo').textContent = '已选 ' + count;
        }}
        
        function selectAll() {{
            document.querySelectorAll('.check').forEach(cb => cb.checked = true);
            saveChecked();
        }}
        
        function clearAll() {{
            document.querySelectorAll('.check').forEach(cb => cb.checked = false);
            saveChecked();
        }}
        
        function exportCSV() {{
            const rows = [['代码', '名称']];
            document.querySelectorAll('.check:checked').forEach(cb => {{
                const tr = cb.closest('tr');
                rows.push([cb.dataset.code, tr.cells[2].textContent]);
            }});
            if (rows.length === 1) {{ alert('请先选择股票'); return; }}
            const csv = rows.map(r => r.join(',')).join('\\n');
            const blob = new Blob(['\\ufeff' + csv], {{type: 'text/csv'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = '{level}.csv';
            a.click();
        }}
        
        function filterTable(keyword) {{
            keyword = keyword.toLowerCase();
            document.querySelectorAll('#tbody tr').forEach(tr => {{
                tr.style.display = tr.textContent.toLowerCase().includes(keyword) ? '' : 'none';
            }});
        }}
        
        function showStock(url) {{
            currentUrl = url;
            const code = url.match(/([a-z]+\\d+)\\.html/)[1];
            document.getElementById('stockTitle').textContent = code.toUpperCase();
            document.getElementById('openNew').style.display = 'inline';
            document.getElementById('placeholder').style.display = 'none';
            const frame = document.getElementById('stockFrame');
            frame.style.display = 'block';
            frame.src = url;
        }}

        // 波动率过滤逻辑
        window.addEventListener('message', (event) => {{
            if (event.data && event.data.type === 'filterVol') {{
                const limit = event.data.limit;
                filterByVolatility(limit);
            }}
        }});

        function filterByVolatility(limit) {{
            let visibleCount = 0;
            document.querySelectorAll('#tbody tr').forEach(tr => {{
                const vol = parseFloat(tr.dataset.vol || 0);
                if (vol > limit) {{
                    tr.style.display = 'none';
                }} else {{
                    tr.style.display = '';
                    visibleCount++;
                }}
            }});
            
            // 更新当前页面的副标题计数
            document.querySelector('.count').textContent = '过滤后: ' + visibleCount + ' 只';
            
            // 通知父窗口更新侧边栏计数
            window.parent.postMessage({{ 
                type: 'updateCount', 
                level: '{level}', 
                count: visibleCount 
            }}, '*');
        }}
    </script>
</body>
</html>
'''
        
        path = report_dir / f"{level}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    
    def _get_td_class(self, value: int) -> str:
        """根据TD值返回CSS类"""
        if value >= 9:
            return "high"
        elif value >= 7:
            return "mid"
        return "low"
    
    def _get_vol_color(self, vol: float) -> str:
        """根据波动率返回颜色"""
        if vol <= 0: return "#999"
        if vol < 0.2: return "#4caf50"  # 绿色：极稳
        if vol < 0.4: return "#1976d2"  # 蓝色：正常
        if vol < 0.7: return "#f57c00"  # 橙色：高波动
        return "#d32f2f"  # 红色：妖/极高波动
    
    def _export_to_index_csv(self, df: pd.DataFrame, module_name: str,
                             report_date: str, report_path: Path):
        """将股票数据追加到索引CSV（委托 util/index_writer）"""
        project_root = Path(__file__).resolve().parent.parent.parent
        web_path = str(report_path.relative_to(project_root)).replace("\\", "/")
        date_str = (report_date[:4] + "-" + report_date[4:6] + "-" + report_date[6:8]
                    if len(report_date) == 8 else report_date)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rows = []
        for _, row in df.iterrows():
            code = str(row.get("代码", "")).strip()
            level = str(row.get("共振级别", "")).strip()
            if not code or level == "无底部信号":
                continue
            rows.append({
                "代码": code,
                "名称": str(row.get("名称", "")).strip(),
                "日期": date_str,
                "模块": module_name,
                "策略级别": level,
                "报告路径": web_path,
                "板块": str(row.get("板块", "")).strip(),
                "行业": str(row.get("行业", "")).strip(),
                "生成时间": now_str,
            })

        write_to_stocks_index(rows, report_date, project_root)
