# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pipeline combined DataFrame
# OUTPUT: Path to HTML reports
# POS:    check-maxrsix6u1d/reporters/html_reporter.py
# -*- coding: utf-8 -*-
"""
HTML报告生成器

生成可交互的HTML报告，包含股票列表和东方财富链接
支持localStorage保存勾选状态和备注，总览页面显示所有勾选股票
"""
from __future__ import annotations

import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import json
import webbrowser

import pandas as pd

# 确保 util/ 可被导入
_UTIL_DIR = Path(__file__).resolve().parent.parent.parent / "util"
if str(_UTIL_DIR) not in sys.path:
    sys.path.insert(0, str(_UTIL_DIR))
from url_utils import infer_market_prefix, get_eastmoney_url  # noqa: E402
from index_writer import write_to_stocks_index  # noqa: E402


class HtmlReporter:
    """HTML报告生成器"""

    def __init__(self, result: Any, output_dir: Path, end_date: Optional[str] = None, display_date: Optional[str] = None):
        self.result = result
        self.output_dir = output_dir
        self.end_date = end_date
        self.display_date = display_date  # 用于在HTML title中显示的日期
        self.generated_files: Dict[str, str] = {}  # name -> filename
        self.asset_dir = output_dir / "assets"
        self.asset_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self):
        """生成所有HTML报告"""
        if not self.result.combined:
            print("  ⚠️ 无组合结果，跳过HTML生成")
            return
        
        now = datetime.now()
        
        # 如果没有 display_date 和 end_date，从数据中读取日期
        if not self.display_date and not self.end_date:
            # 尝试从第一个非空的组合数据中读取日期
            data_date = None
            for name, df in self.result.combined.items():
                if not df.empty:
                    date_columns = ["最新日期", "日期", "交易日期", "date"]
                    for col in date_columns:
                        if col in df.columns:
                            first_date = df[col].iloc[0]
                            if pd.notna(first_date):
                                data_date = str(first_date)
                                print(f"  [INFO] 从数据中读取到日期: {data_date}")
                                break
                    if data_date:
                        break
            
            if data_date:
                # 提取日期部分（可能是 "2024-01-30" 或 "2024-01-30 00:00:00" 格式）
                date_str = data_date.split()[0].replace("-", "")
            else:
                date_str = now.strftime("%Y%m%d")
                print(f"  [WARN] 数据中未找到日期信息，使用当前日期: {date_str}")
        else:
            # 如果有 end_date 或 display_date，文件名中使用它们
            date_str = (self.display_date or self.end_date or now.strftime("%Y%m%d")).replace("-", "")
        
        ts = now.strftime("%H%M%S")
        
        # 写入公共资源
        self._write_assets()
        
        # 为每个组合生成HTML
        summary_filename = f"summary_{date_str}_{ts}.html"
        
        for name, df in self.result.combined.items():
            if df.empty:
                continue
            
            # summary_end-date_生成时间
            html_filename = f"{name}_{len(df)}只_{date_str}_{ts}.html"
            html_path = self.output_dir / html_filename
            self._generate_combo_html(df, name, html_path, ts, summary_filename)
            self.generated_files[name] = html_filename
            print(f"  [OK] HTML报告: {html_path.name}")
        
        # 生成总览HTML（需要传递generated_files）
        # summary_end-date_生成时间
        summary_path = self.output_dir / summary_filename
        self._generate_summary_html(summary_path, summary_filename)
        print(f"  [OK] HTML总览: {summary_path.name}")
        
        # 导出到索引CSV
        for name, df in self.result.combined.items():
            if not df.empty:
                self._export_to_index_csv(df, "MAxRSIx6U1D", name, date_str, summary_path)
        
        # 自动打开总览页面
        try:
            print(f"  [START] 正在打开浏览器...")
            webbrowser.open(summary_path.as_uri())
        except Exception as e:
            print(f"  ⚠️ 自动打开浏览器失败: {e}")
    
    def _generate_combo_html(self, df: pd.DataFrame, title: str, output_path: Path, ts: str, summary_filename: str):
        """生成单个组合的HTML"""
        stocks = self._extract_stocks(df)
        
        if not stocks:
            return
        
        first_code, _, first_board, _, _ = stocks[0]
        first_url = get_eastmoney_url(first_code, first_board)
        
        # 生成行业统计
        industry_stats_html = self._generate_combo_industry_stats(df)
        
        list_items = []
        for code, name, board, industry, priority in stocks:
            url = get_eastmoney_url(code, board)
            priority_badge = ""
            if priority == "[STAR]买入":
                priority_badge = '<span class="badge buy">[STAR]买入</span>'
            elif priority == "[STAR]等待":
                priority_badge = '<span class="badge wait">[STAR]等待</span>'
            
            # 显示行业信息
            industry_display = f' <span class="industry">({escape(industry)})</span>' if industry else ''
            
            # data-* 属性用于localStorage
            list_items.append(
                f'        <li data-code="{escape(code)}" data-name="{escape(name)}" data-board="{escape(board)}" data-industry="{escape(industry)}" data-priority="{escape(priority)}">'
                f'<label><input type="checkbox" data-stock="{escape(code)}" /> '
                f'<a href="{escape(url)}" target="quoteFrame">'
                f'<span class="code">{escape(code)}</span> - {escape(name)}{industry_display} '
                f'<span class="board">{escape(board)}</span></a>{priority_badge}</label></li>'
            )
        
        html = self._get_html_template(
            title=title,
            first_url=first_url,
            list_items=list_items,
            stock_count=len(stocks),
            combo_name=title,
            summary_filename=summary_filename,
            industry_stats_html=industry_stats_html
        )
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
    
    def _generate_combo_industry_stats(self, df: pd.DataFrame) -> str:
        """生成单个组合的行业/板块统计HTML"""
        if df.empty:
            return ""
        
        total = len(df)
        sections = []
        
        # 板块统计
        if "板块" in df.columns:
            board_counts = df["板块"].value_counts().reset_index()
            board_counts.columns = ["板块", "数量"]
            board_counts["占比"] = (board_counts["数量"] / total * 100).round(1)
            
            rows = []
            for _, row in board_counts.iterrows():
                rows.append(
                    f'<tr><td>{escape(str(row["板块"]))}</td>'
                    f'<td>{row["数量"]}</td>'
                    f'<td class="pct">{row["占比"]}%</td></tr>'
                )
            
            sections.append(f"""
    <div class="stats-section">
      <h3>[CHART] 板块分布 <button class="collapse-btn" onclick="toggleStats('boardStats')">收起</button></h3>
      <div class="stats-content" id="boardStats">
        <table class="stats-table">
          <thead><tr><th>板块</th><th>数量</th><th>占比</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    </div>""")
        
        # 行业统计（只显示Top 10，因为侧边栏空间有限）
        if "行业" in df.columns:
            industry_counts = df["行业"].value_counts().reset_index()
            industry_counts.columns = ["行业", "数量"]
            industry_counts["占比"] = (industry_counts["数量"] / total * 100).round(1)
            
            show_df = industry_counts.head(10)
            rows = []
            for _, row in show_df.iterrows():
                rows.append(
                    f'<tr><td>{escape(str(row["行业"]))}</td>'
                    f'<td>{row["数量"]}</td>'
                    f'<td class="pct">{row["占比"]}%</td></tr>'
                )
            
            other_info = ""
            if len(industry_counts) > 10:
                other_count = industry_counts.iloc[10:]["数量"].sum()
                other_pct = (other_count / total * 100).round(1)
                other_info = f"<p style='font-size:0.85em;color:#666;margin:6px 0 0 0;'>*其他 {len(industry_counts) - 10} 个行业共 {other_count} 只，占比 {other_pct}%*</p>"
            
            sections.append(f"""
    <div class="stats-section">
      <h3>🏭 行业分布 <button class="collapse-btn" onclick="toggleStats('industryStats')">收起</button></h3>
      <div class="stats-content" id="industryStats">
        <table class="stats-table">
          <thead><tr><th>行业</th><th>数量</th><th>占比</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
        {other_info}
      </div>
    </div>""")
        
        return "\n".join(sections)
    
    def _generate_summary_html(self, output_path: Path, summary_filename: str):
        """生成总览HTML - 组合链接用iframe，勾选股票可点击查看"""
        now = datetime.now()

        # 生成组合链接列表（用onclick在iframe中打开）
        combo_links = []
        combo_files_json = {}
        for name, df in self.result.combined.items():
            count = len(df)
            filename = self.generated_files.get(name, "")
            if count > 0 and filename:
                combo_files_json[name] = filename
                combo_links.append(
                    f'<li><a href="javascript:void(0)" onclick="loadCombo(\'{escape(filename)}\')" class="combo-link">'
                    f'<strong>{escape(name)}</strong></a>: {count} 只</li>'
                )
            elif count > 0:
                combo_links.append(f'<li><strong>{escape(name)}</strong>: {count} 只</li>')
            else:
                combo_links.append(f'<li class="empty-combo"><strong>{escape(name)}</strong>: 0 只</li>')

        # 从 summary_filename 中提取日期（格式：summary_YYYYMMDD_HHMMSS.html）
        # summary_filename 已经使用了从数据中读取的 date_str
        date_match = summary_filename.split('_')
        if len(date_match) >= 2 and len(date_match[1]) == 8:
            date_str_for_title = date_match[1]
            display_date = f"{date_str_for_title[:4]}-{date_str_for_title[4:6]}-{date_str_for_title[6:8]}"
        else:
            display_date = now.strftime('%Y-%m-%d')
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>6U1D6升1跌指标+放量MACD上升筛选(很少用) - {display_date}</title>
  <link rel="stylesheet" href="assets/common_summary.css">
</head>
<body>
  <div class="sidebar">
    <h1>[CHART] 6U1D61指标+放量MACD上升筛选(很少用)</h1>
    <p class="timestamp">生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>📋 组合筛选结果</h2>
    <ul>
      {''.join(combo_links)}
    </ul>
    
    <div class="checked-section">
      <h3>[OK] 已勾选股票 (<span id="checkedCount">0</span>)</h3>
      <ul id="checkedList" class="checked-list">
        <li class="empty">暂无勾选股票</li>
      </ul>
      <button id="clearAllBtn" class="clear-all-btn" style="display:none;">清空所有勾选</button>
    </div>
    
    <div class="priority">
      <h3>📌 优先级说明</h3>
      <ul>
        <li><strong>[STAR]买入</strong>: 6连阳后阴线，立即买入</li>
        <li><strong>[STAR]等待</strong>: 第6天阳线，等回调</li>
      </ul>
    </div>
  </div>
  <div class="main">
    <iframe id="mainFrame" name="mainFrame" src="about:blank"></iframe>
  </div>
  
  <script>
    const COMBO_FILES = {json.dumps(combo_files_json)};
  </script>
  <script src="assets/common_summary.js"></script>
</body>
</html>"""
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
    
    def _extract_stocks(self, df: pd.DataFrame) -> List[tuple]:
        """从DataFrame提取股票信息"""
        stocks = []
        
        code_col = None
        for col in ["代码", "code", "股票代码"]:
            if col in df.columns:
                code_col = col
                break
        
        if code_col is None:
            return stocks
        
        name_col = "名称" if "名称" in df.columns else "name"
        board_col = "板块" if "板块" in df.columns else None
        industry_col = "行业" if "行业" in df.columns else "industry"
        
        for _, row in df.iterrows():
            code_raw = str(row[code_col])
            code_match = re.search(r"\d{6}", code_raw)
            if not code_match:
                continue
            
            code = code_match.group(0)
            name = row.get(name_col, "") or ""
            board = row.get(board_col, "") if board_col else ""
            industry = row.get(industry_col, "") or ""
            
            # 获取优先级
            priority = ""
            if row.get("回调买点", False) in [True, "True", "true", 1, "1"]:
                priority = "[STAR]买入"
            elif row.get("等待买点", False) in [True, "True", "true", 1, "1"]:
                priority = "[STAR]等待"
            
            stocks.append((code, name, board, industry, priority))
        
        return stocks
    
    def _get_html_template(self, title: str, first_url: str, list_items: List[str], 
                           stock_count: int, combo_name: str, summary_filename: str, 
                           industry_stats_html: str = "") -> str:
        """获取HTML模板（带localStorage和返回总览链接）"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="assets/common_detail.css">
</head>
<body>
  <div class="sidebar">
    <div class="nav-links">
      <a href="{escape(summary_filename)}">[CHART] 总览</a>
    </div>
    <h1>{escape(title)}</h1>
    <div class="count">{stock_count} 只股票</div>
    <div class="checked-info">已勾选: <span id="checkedCount">0</span> 只</div>
    {industry_stats_html}
    <ul id="stockList">
{chr(10).join(list_items)}
    </ul>
  </div>
  <div class="main">
    <iframe name="quoteFrame" src="{escape(first_url)}"></iframe>
  </div>
  
  <script>
    const COMBO_NAME = '{escape(combo_name)}';
  </script>
  <script src="assets/common_detail.js"></script>
</body>
</html>"""
        
        path = report_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    
    def _export_to_index_csv(self, df: pd.DataFrame, module_name: str,
                             combo_name: str, report_date: str, report_path: Path):
        """将股票数据追加到索引CSV（委托 util/index_writer）"""
        project_root = Path(__file__).resolve().parent.parent.parent
        web_path = str(report_path.relative_to(project_root)).replace("\\", "/")
        date_str = (report_date[:4] + "-" + report_date[4:6] + "-" + report_date[6:8]
                    if len(report_date) == 8 else report_date)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rows = []
        for _, row in df.iterrows():
            code_raw = str(row.get("代码", ""))
            code_match = re.search(r"\d{6}", code_raw)
            if not code_match:
                continue
            code = code_match.group(0)

            priority = ""
            if row.get("回调买点", False) in [True, "True", "true", 1, "1"]:
                priority = "[STAR]买入"
            elif row.get("等待买点", False) in [True, "True", "true", 1, "1"]:
                priority = "[STAR]等待"

            rows.append({
                "代码": code,
                "名称": str(row.get("名称", "")).strip(),
                "日期": date_str,
                "模块": module_name,
                "策略级别": combo_name + (f" {priority}" if priority else ""),
                "报告路径": web_path,
                "板块": str(row.get("板块", "")).strip(),
                "行业": str(row.get("行业", "")).strip(),
                "生成时间": now_str,
            })

        write_to_stocks_index(rows, report_date, project_root)

    def _write_assets(self):
        """生成独立存放的CSS和JS文件"""
        summary_css = """
        :root { color-scheme: light dark; }
        body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", Arial, sans-serif; margin: 0; padding: 0; height: 100vh; display: flex; }
        .sidebar { width: 450px; min-width: 400px; height: 100vh; overflow-y: auto; padding: 16px; box-sizing: border-box; border-right: 1px solid #e0e0e0; background: #fafafa; flex-shrink: 0; }
        .main { flex: 1; height: 100vh; min-width: 0; }
        .main iframe { width: 100%; height: 100%; border: none; }
        h1 { margin-bottom: 8px; color: #1a1a1a; font-size: 1.4em; }
        h2 { color: #333; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; font-size: 1.1em; margin-top: 20px; }
        .timestamp { color: #666; font-size: 0.85em; }
        ul { padding-left: 20px; margin: 8px 0; }
        li { margin: 5px 0; }
        li.empty-combo { color: #999; }
        a { color: #1a73e8; text-decoration: none; cursor: pointer; }
        a:hover { text-decoration: underline; }
        .combo-link { font-weight: bold; }
        .priority { margin-top: 16px; padding: 10px; background: #f0f0f0; border-radius: 8px; font-size: 0.85em; }
        .priority h3 { margin: 0 0 6px 0; font-size: 0.95em; }
        .priority ul { padding-left: 16px; margin: 0; }
        .priority li { margin: 3px 0; }
        
        .checked-section { margin-top: 16px; padding: 12px; background: #e8f5e9; border-radius: 8px; border: 1px solid #c8e6c9; }
        .checked-section h3 { margin: 0 0 10px 0; font-size: 1em; color: #2e7d32; }
        .checked-section .empty { color: #666; font-style: italic; padding: 8px 0; }
        .checked-list { list-style: none; padding: 0; margin: 0; }
        .checked-list li { display: flex; flex-direction: column; padding: 8px; margin: 6px 0; background: #fff; border-radius: 6px; border: 1px solid #ddd; }
        .checked-list li.highlighted { background: #fff9c4; border-color: #fbc02d; }
        .checked-list .stock-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
        .checked-list .stock-info { flex: 1; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
        .checked-list .stock-info a { display: inline-flex; align-items: center; gap: 4px; }
        .checked-list .code { font-family: monospace; background: #e8f0fe; padding: 2px 5px; border-radius: 3px; font-size: 0.9em; }
        .checked-list .source { font-size: 0.7em; color: #666; background: #f5f5f5; padding: 2px 5px; border-radius: 3px; }
        .checked-list .industry { font-size: 0.7em; color: #1565c0; background: #e3f2fd; padding: 2px 5px; border-radius: 3px; }
        .checked-list .badge { font-size: 0.7em; padding: 2px 5px; border-radius: 3px; }
        .checked-list .badge.buy { background: #fce4ec; color: #c62828; }
        .checked-list .badge.wait { background: #fff3e0; color: #e65100; }
        .checked-list .remove-btn { background: #ffebee; border: none; color: #c62828; cursor: pointer; padding: 4px 8px; border-radius: 4px; font-size: 0.75em; flex-shrink: 0; }
        .checked-list .remove-btn:hover { background: #ffcdd2; }
        .checked-list .note-row { margin-top: 6px; display: flex; gap: 6px; align-items: center; }
        .checked-list .note-input { flex: 1; padding: 4px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85em; background: #fafafa; }
        .checked-list .note-input:focus { outline: none; border-color: #1a73e8; background: #fff; }
        .checked-list .note-display { font-size: 0.85em; color: #555; background: #f5f5f5; padding: 4px 8px; border-radius: 4px; flex: 1; cursor: pointer; }
        .checked-list .note-display:hover { background: #e8e8e8; }
        .clear-all-btn { margin-top: 10px; background: #ffebee; border: 1px solid #ffcdd2; color: #c62828; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
        .clear-all-btn:hover { background: #ffcdd2; }
        
        @media (prefers-color-scheme: dark) {
            .sidebar { background: #1a1a1a; border-color: #333; }
            h1 { color: #fff; }
            h2 { color: #ccc; border-color: #444; }
            .timestamp { color: #999; }
            a { color: #8ab4f8; }
            .priority { background: #2a2a2a; }
            .checked-section { background: #1b3320; border-color: #2e7d32; }
            .checked-section h3 { color: #81c784; }
            .checked-list li { background: #2a2a2a; border-color: #444; }
            .checked-list li.highlighted { background: #3e3a1a; border-color: #f9a825; }
            .checked-list .code { background: #303030; color: #8ab4f8; }
            .checked-list .source { background: #333; color: #999; }
            .checked-list .industry { background: #1e3a5f; color: #90caf9; }
            .checked-list .note-input { background: #333; border-color: #555; color: #eee; }
            .checked-list .note-display { background: #333; color: #ccc; }
        }
        """

        summary_js = """
        const STORAGE_KEY = 'stock_checked_list';
        const STORAGE_EXPIRY_KEY = 'stock_checked_expiry';
        const EXPIRY_HOURS = 24;
        
        function loadCombo(filename) { document.getElementById('mainFrame').src = filename; }
        function checkExpiry() {
            const expiry = localStorage.getItem(STORAGE_EXPIRY_KEY);
            if (expiry && Date.now() > parseInt(expiry)) {
                localStorage.removeItem(STORAGE_KEY);
                localStorage.removeItem(STORAGE_EXPIRY_KEY);
            }
        }
        function getCheckedStocks() {
            checkExpiry();
            const data = localStorage.getItem(STORAGE_KEY);
            return data ? JSON.parse(data) : {};
        }
        function saveCheckedStocks(stocks) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(stocks));
            const expiry = Date.now() + EXPIRY_HOURS * 60 * 60 * 1000;
            localStorage.setItem(STORAGE_EXPIRY_KEY, expiry.toString());
        }
        function getEastMoneyUrl(code) {
            const prefix = code.startsWith('6') ? '1.' : '0.';
            return `https://quote.eastmoney.com/concept/${prefix}${code}.html`;
        }
        function saveNote(code, note) {
            const stocks = getCheckedStocks();
            if (stocks[code]) {
                stocks[code].note = note;
                saveCheckedStocks(stocks);
            }
        }
        function viewStock(code) {
            const url = getEastMoneyUrl(code);
            document.getElementById('mainFrame').src = url;
        }
        function renderCheckedList() {
            const stocks = getCheckedStocks();
            const list = document.getElementById('checkedList');
            const countEl = document.getElementById('checkedCount');
            const clearBtn = document.getElementById('clearAllBtn');
            const entries = Object.entries(stocks);
            countEl.textContent = entries.length;
            if (entries.length === 0) {
                list.innerHTML = '<li class="empty">暂无勾选股票</li>';
                clearBtn.style.display = 'none';
                return;
            }
            clearBtn.style.display = 'block';
            entries.sort((a, b) => (b[1].time || 0) - (a[1].time || 0));
            list.innerHTML = entries.map(([code, info]) => {
                let badge = '';
                if (info.priority === '[STAR]买入') { badge = '<span class="badge buy">[STAR]买入</span>'; }
                else if (info.priority === '[STAR]等待') { badge = '<span class="badge wait">[STAR]等待</span>'; }
                const industryDisplay = info.industry ? `<span class="industry">${info.industry}</span>` : '';
                const noteVal = (info.note || '').replace(/"/g, '&quot;');
                const noteDisplay = info.note ? `<div class="note-display" onclick="editNote('${code}')">${info.note}</div>` : '';
                return `
                <li data-code="${code}" class="highlighted">
                    <div class="stock-row">
                    <div class="stock-info">
                        <a onclick="viewStock('${code}')"><span class="code">${code}</span> ${info.name || ''}</a>
                        ${badge}
                        ${industryDisplay}
                        <span class="source">${info.source || ''}</span>
                    </div>
                    <button class="remove-btn" onclick="removeStock('${code}')">移除</button>
                    </div>
                    <div class="note-row" id="note-row-${code}">
                    ${noteDisplay || `<input type="text" class="note-input" placeholder="添加备注..." value="${noteVal}" onblur="saveNoteFromInput('${code}', this)" onkeydown="if(event.key==='Enter')this.blur()">`}
                    </div>
                </li>
                `;
            }).join('');
        }
        function editNote(code) {
            const stocks = getCheckedStocks();
            const info = stocks[code];
            if (!info) return;
            const noteRow = document.getElementById('note-row-' + code);
            const noteVal = (info.note || '').replace(/"/g, '&quot;');
            noteRow.innerHTML = `<input type="text" class="note-input" value="${noteVal}" onblur="saveNoteFromInput('${code}', this)" onkeydown="if(event.key==='Enter')this.blur()" autofocus>`;
            setTimeout(() => noteRow.querySelector('input').focus(), 10);
        }
        function saveNoteFromInput(code, input) { saveNote(code, input.value.trim()); renderCheckedList(); }
        function removeStock(code) { const stocks = getCheckedStocks(); delete stocks[code]; saveCheckedStocks(stocks); renderCheckedList(); }
        document.getElementById('clearAllBtn')?.addEventListener('click', () => {
            if (confirm('确定清空所有勾选股票？')) { saveCheckedStocks({}); renderCheckedList(); }
        });
        window.addEventListener('storage', (e) => { if (e.key === STORAGE_KEY) renderCheckedList(); });
        renderCheckedList();
        """

        detail_css = """
        :root { color-scheme: light dark; }
        body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", Arial, sans-serif; margin: 0; padding: 0; height: 100vh; display: flex; }
        .sidebar { width: 380px; min-width: 340px; height: 100vh; overflow-y: auto; padding: 14px; box-sizing: border-box; border-right: 1px solid #e0e0e0; background: #fafafa; flex-shrink: 0; }
        .sidebar h1 { font-size: 1.1em; margin: 0 0 6px 0; }
        .sidebar .nav-links { margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #e0e0e0; display: flex; gap: 8px; }
        .sidebar .nav-links a { display: inline-block; padding: 5px 10px; background: #e3f2fd; border-radius: 4px; text-decoration: none; color: #1565c0; font-size: 0.85em; }
        .sidebar .nav-links a:hover { background: #bbdefb; }
        .sidebar .count { color: #666; font-size: 0.85em; margin-bottom: 6px; }
        .sidebar .checked-info { font-size: 0.8em; color: #2e7d32; background: #e8f5e9; padding: 5px 8px; border-radius: 4px; margin-bottom: 10px; }
        .sidebar .stats-section { margin: 10px 0; padding: 10px; background: #e3f2fd; border-radius: 6px; border: 1px solid #bbdefb; font-size: 0.85em; }
        .sidebar .stats-section h3 { margin: 0 0 8px 0; font-size: 0.95em; color: #1565c0; display: flex; align-items: center; justify-content: space-between; }
        .sidebar .stats-table { width: 100%; border-collapse: collapse; font-size: 0.9em; margin-top: 6px; }
        .sidebar .stats-table th, .sidebar .stats-table td { padding: 4px 6px; text-align: left; border-bottom: 1px solid #ddd; }
        .sidebar .stats-table th { background: #bbdefb; font-weight: 600; font-size: 0.85em; }
        .sidebar .stats-table tr:hover { background: #e1f5fe; }
        .sidebar .stats-table .pct { color: #1565c0; font-weight: 500; }
        .sidebar .collapse-btn { background: #1a73e8; color: #fff; border: none; padding: 3px 8px; border-radius: 3px; cursor: pointer; font-size: 0.75em; }
        .sidebar .collapse-btn:hover { background: #1557b0; }
        .sidebar .stats-content { max-height: 200px; overflow-y: auto; }
        .sidebar .stats-content.collapsed { display: none; }
        .sidebar ul { list-style: none; padding: 0; margin: 0; }
        .sidebar > ul > li { margin: 3px 0; padding: 3px 0; font-size: 0.9em; }
        .sidebar li.checked { background: #fff9c4; border-radius: 4px; padding: 3px 6px; margin: 3px -6px; }
        .sidebar label { display: flex; align-items: center; gap: 6px; cursor: pointer; }
        .sidebar a { text-decoration: none; color: #1a73e8; }
        .sidebar a:hover { text-decoration: underline; }
        .sidebar .code { font-family: monospace; background: #e8f0fe; padding: 1px 3px; border-radius: 3px; font-size: 0.9em; }
        .sidebar .board { color: #666; font-size: 0.8em; }
        .sidebar .industry { color: #1565c0; font-size: 0.75em; font-style: italic; }
        .sidebar .badge { font-size: 0.7em; padding: 1px 4px; border-radius: 3px; margin-left: 3px; }
        .sidebar .badge.buy { background: #fce4ec; color: #c62828; }
        .sidebar .badge.wait { background: #fff3e0; color: #e65100; }
        .main { flex: 1; height: 100vh; min-width: 0; }
        .main iframe { width: 100%; height: 100%; border: none; }
        @media (prefers-color-scheme: dark) {
            .sidebar { background: #1a1a1a; border-color: #333; }
            .sidebar h1 { color: #fff; }
            .sidebar .nav-links { border-color: #444; }
            .sidebar .nav-links a { background: #1e3a5f; color: #90caf9; }
            .sidebar .nav-links a:hover { background: #2a4a6f; }
            .sidebar .count { color: #999; }
            .sidebar .checked-info { background: #1b3320; color: #81c784; }
            .sidebar li.checked { background: #3e3a1a; }
            .sidebar a { color: #8ab4f8; }
            .sidebar .code { background: #303030; color: #8ab4f8; }
            .sidebar .board { color: #999; }
            .sidebar .industry { color: #90caf9; }
        }
        """

        detail_js = """
        const STORAGE_KEY = 'stock_checked_list';
        const STORAGE_EXPIRY_KEY = 'stock_checked_expiry';
        const EXPIRY_HOURS = 24;
        function toggleStats(sectionId) {
            const content = document.getElementById(sectionId);
            const btn = content.previousElementSibling.querySelector('.collapse-btn');
            if (content.classList.contains('collapsed')) {
                content.classList.remove('collapsed');
                btn.textContent = '收起';
            } else {
                content.classList.add('collapsed');
                btn.textContent = '展开';
            }
        }
        function checkExpiry() {
            const expiry = localStorage.getItem(STORAGE_EXPIRY_KEY);
            if (expiry && Date.now() > parseInt(expiry)) {
                localStorage.removeItem(STORAGE_KEY);
                localStorage.removeItem(STORAGE_EXPIRY_KEY);
            }
        }
        function getCheckedStocks() {
            checkExpiry();
            const data = localStorage.getItem(STORAGE_KEY);
            return data ? JSON.parse(data) : {};
        }
        function saveCheckedStocks(stocks) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(stocks));
            const expiry = Date.now() + EXPIRY_HOURS * 60 * 60 * 1000;
            localStorage.setItem(STORAGE_EXPIRY_KEY, expiry.toString());
        }
        function updateCheckedCount() {
            const stocks = getCheckedStocks();
            const countEl = document.getElementById('checkedCount');
            if (countEl) countEl.textContent = Object.keys(stocks).length;
        }
        function initCheckboxes() {
            const stocks = getCheckedStocks();
            const items = document.querySelectorAll('#stockList li');
            items.forEach(li => {
                const code = li.dataset.code;
                const checkbox = li.querySelector('input[type="checkbox"]');
                if (stocks[code]) { checkbox.checked = true; li.classList.add('checked'); }
                checkbox.addEventListener('change', (e) => {
                    const checked = e.target.checked;
                    const currentStocks = getCheckedStocks();
                    if (checked) {
                        currentStocks[code] = {
                            name: li.dataset.name || '',
                            board: li.dataset.board || '',
                            industry: li.dataset.industry || '',
                            priority: li.dataset.priority || '',
                            source: COMBO_NAME,
                            time: Date.now(),
                            note: ''
                        };
                        li.classList.add('checked');
                    } else {
                        delete currentStocks[code];
                        li.classList.remove('checked');
                    }
                    saveCheckedStocks(currentStocks);
                    updateCheckedCount();
                });
            });
            updateCheckedCount();
        }
        window.addEventListener('storage', (e) => { if (e.key === STORAGE_KEY) initCheckboxes(); });
        initCheckboxes();
        """

        (self.asset_dir / "common_summary.css").write_text(summary_css, encoding="utf-8")
        (self.asset_dir / "common_summary.js").write_text(summary_js, encoding="utf-8")
        (self.asset_dir / "common_detail.css").write_text(detail_css, encoding="utf-8")
        (self.asset_dir / "common_detail.js").write_text(detail_js, encoding="utf-8")

