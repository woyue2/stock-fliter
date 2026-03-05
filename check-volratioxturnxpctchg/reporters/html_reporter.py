# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame, output_dir, end_date
# OUTPUT: Path to HTML report
# POS:    check-volratioxturnxpctchg/reporters/html_reporter.py
# -*- coding: utf-8 -*-
"""
HTML 报告生成器 — 交互式双栏 UI（适配 check-volupxyangxshipan 风格）
"""
from __future__ import annotations

import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional

import pandas as pd


class HTMLReporter:
    """量比×换手率×涨跌幅 HTML 报告"""

    def __init__(self, output_dir: Path, end_date: Optional[str] = None):
        self.output_dir = output_dir
        self.end_date = end_date

    def generate(self, df: pd.DataFrame) -> Path:
        """生成 HTML 报告"""
        now = datetime.now()
        date_str = (self.end_date or now.strftime("%Y%m%d")).replace("-", "")
        filename = f"volratio_report_{date_str}_{now.strftime('%H%M%S')}.html"

        # 生成 assets (CSS / JS)
        _write_assets(self.output_dir)

        html = _render_html(df, now, self.end_date)
        path = self.output_dir / filename
        path.write_text(html, encoding="utf-8")
        return path


def _render_html(df: pd.DataFrame, now: datetime, end_date: str | None) -> str:
    """拼装双栏交互式 HTML"""
    title = "量比×换手率×涨跌幅"
    data_date = end_date or now.strftime("%Y-%m-%d")
    
    rows_html = _build_rows_html(df)
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)} - {data_date}</title>
  <link rel="stylesheet" href="assets/common_detail.css">
</head>
<body>
  <div class="layout">
    <div class="left-panel">
      <div class="header">
        <div>
          <span class="title">{escape(title)}</span>
          <span class="count" id="visibleCount">共 {len(df)} 只</span>
        </div>
        <div class="toolbar">
          <span class="checked-info" id="checkedInfo">已选 0</span>
          <button id="priceFilterBtn" class="btn active" onclick="togglePriceFilter()">股价 < 10</button>
          <button id="hideChuangKeBtn" class="btn active" onclick="toggleHideChuangKe()">隐藏创/科</button>
          <button class="btn" onclick="selectAll()">全选</button>
          <button class="btn" onclick="clearAll()">清除</button>
          <input type="text" class="search" placeholder="搜索..." oninput="filterTable(this.value)">
          <div class="meta">数据日期: {data_date}</div>
        </div>
      </div>
      <div class="stats">
        <div class="stats-group">
          <span class="stats-label">板块:</span>
          <span id="boardStatsContainer">{_build_stats_tags(df, '行业')}</span>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th width="30"></th>
              <th>代码</th>
              <th>名称</th>
              <th>行业</th>
              <th>概念</th>
              <th>收盘价</th>
              <th>涨跌幅%</th>
              <th>量比</th>
              <th>换手率%</th>
              <th>总金额(万)</th>
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
      <div class="iframe-wrapper" id="frameWrapper" style="display:none">
        <iframe id="stockFrame" class="stock-frame"></iframe>
      </div>
    </div>
  </div>
  <script>
    const STORAGE_KEY = 'volratio_{data_date}';
  </script>
  <script src="assets/common_detail.js"></script>
</body>
</html>
'''

def _build_rows_html(df: pd.DataFrame) -> str:
    if df.empty:
        return '<tr><td colspan="9">无命中股票</td></tr>'

    df_sorted = df.sort_values("量比", ascending=False)
    chunks: list[str] = []
    for _, row in df_sorted.iterrows():
        code = str(row.get("代码", ""))
        name = escape(str(row.get("名称", "")))
        industry = escape(str(row.get("行业", "")))
        concepts = escape(str(row.get("概念", ""))).replace(";", " ")
        close_price = float(row.get("最新收盘", 0.0))
        pct_chg = float(row.get("涨跌幅%", 0.0))
        vr = float(row.get("量比", 0.0))
        turn = float(row.get("换手率%", 0.0))
        amt = float(row.get("总金额(万)", 0.0))
        
        # 简单判断是否创科
        board_str = "创业板" if code.startswith("300") or code.startswith("301") else ("科创板" if code.startswith("688") else "主板")
        
        em_code = f"sh{code}" if code.startswith("6") else f"sz{code}"
        em_url = f"https://quote.eastmoney.com/{em_code}.html"
        
        chunks.append(
            f'<tr data-code="{code}" data-price="{close_price}" data-board="{board_str}" data-industry="{industry}">'
            f'<td><input type="checkbox" class="check" data-code="{code}" onchange="saveChecked()"></td>'
            f'<td><a href="javascript:void(0)" class="code" onclick="showStock(\'{escape(em_url)}\')">{escape(code)}</a></td>'
            f'<td>{name}</td>'
            f'<td>{industry}</td>'
            f'<td style="font-size:11px; color:#666; max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{concepts}">{concepts}</td>'
            f'<td>{close_price:.2f}</td>'
            f'<td class="tag-strong">{pct_chg:.2f}%</td>'
            f'<td><strong>{vr:.2f}</strong></td>'
            f'<td>{turn:.2f}%</td>'
            f'<td>{amt:.0f}</td>'
            '</tr>'
        )
    return "\n".join(chunks)

def _build_stats_tags(df: pd.DataFrame, column: str) -> str:
    if column not in df.columns:
        return ""
    stats = df[column].value_counts().head(10)
    tags = []
    for val, count in stats.items():
        if val == "": continue
        tags.append(f'<span class="tag">{escape(str(val))} {count}</span>')
    return "\n".join(tags)

def _write_assets(output_dir: Path) -> None:
    asset_dir = output_dir / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    
    detail_css = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, "Microsoft YaHei", sans-serif; font-size: 13px; color: #333; background: #fff; height: 100vh; overflow: hidden; }
    .layout { display: flex; height: 100vh; }
    .left-panel { width: 50%; min-width: 520px; display: flex; flex-direction: column; border-right: 1px solid #e0e0e0; }
    .right-panel { flex: 1; display: flex; flex-direction: column; background: #fafafa; }
    .header { padding: 16px 20px; border-bottom: 1px solid #e0e0e0; display: flex; justify-content: space-between; align-items: center; }
    .toolbar { display: flex; gap: 10px; align-items: center; }
    .search { padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; width: 120px; font-size: 12px; }
    .btn { padding: 6px 12px; border: 1px solid #ddd; background: #fff; border-radius: 4px; cursor: pointer; font-size: 12px; }
    .btn:hover { background: #f5f5f5; }
    .btn.active { background: #e3f2fd; color: #1976d2; border-color: #1976d2; font-weight: bold; }
    .stats { padding: 12px 20px; border-bottom: 1px solid #e0e0e0; display: flex; gap: 20px; flex-wrap: wrap; }
    .stats-group { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
    .stats-label { font-size: 12px; color: #999; margin-right: 4px; }
    .tag { font-size: 11px; padding: 2px 6px; background: #f0f0f0; border-radius: 3px; }
    .title { font-size: 16px; font-weight: 600; }
    .count { color: #666; margin-left: 8px; }
    .meta { color: #666; font-size: 12px; }
    .table-wrap { flex: 1; overflow: auto; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border-bottom: 1px solid #eee; padding: 10px 12px; text-align: left; }
    th { background: #fafafa; font-weight: 500; position: sticky; top: 0; z-index: 10; }
    tr:nth-child(even) { background: #fafafa; }
    tr:hover { background: #f9f9f9; }
    tr.checked { background: #e8f5e9; }
    .tag-strong { color: #d32f2f; font-weight: bold; }
    .code { color: #1976d2; text-decoration: none; cursor: pointer; }
    .checked-info { font-size: 12px; color: #4caf50; }
    .right-header { padding: 10px 16px; border-bottom: 1px solid #e0e0e0; font-size: 12px; color: #666; display: flex; justify-content: space-between; align-items: center; }
    .open-new { font-size: 11px; color: #1976d2; text-decoration: none; cursor: pointer; }
    .open-new:hover { text-decoration: underline; }
    .placeholder { flex: 1; display: flex; align-items: center; justify-content: center; color: #999; }
    .iframe-wrapper { flex: 1; width: 100%; overflow: hidden; position: relative; background: #fff; }
    .stock-frame { width: 150%; height: 100%; border: none; position: absolute; left: 50%; transform: translateX(-50%); }
    """
    
    detail_js = """
    let currentUrl = '';
    let isPriceFilterActive = false; /* 默认不激活，以免初始隐藏过多 */
    let isHideChuangKeActive = false; /* 默认不隐藏创科 */
    let currentSearchKeyword = '';

    document.addEventListener('DOMContentLoaded', () => {
      loadChecked();
      
      // 取消按钮默认 active 状态
      document.getElementById('priceFilterBtn').classList.remove('active');
      document.getElementById('hideChuangKeBtn').classList.remove('active');
      
      applyFilters();
    });

    function togglePriceFilter() {
      isPriceFilterActive = !isPriceFilterActive;
      const btn = document.getElementById('priceFilterBtn');
      if (isPriceFilterActive) { btn.classList.add('active'); } else { btn.classList.remove('active'); }
      applyFilters();
    }

    function toggleHideChuangKe() {
      isHideChuangKeActive = !isHideChuangKeActive;
      const btn = document.getElementById('hideChuangKeBtn');
      if (isHideChuangKeActive) { btn.classList.add('active'); } else { btn.classList.remove('active'); }
      applyFilters();
    }

    function filterTable(keyword) {
      currentSearchKeyword = keyword.toLowerCase();
      applyFilters();
    }

    function applyFilters() {
      const industryCounts = {};
      let visibleCount = 0;

      document.querySelectorAll('#tbody tr').forEach(tr => {
        const price = parseFloat(tr.dataset.price || 0);
        const text = tr.textContent.toLowerCase();
        const b = tr.dataset.board || '';
        const i = tr.dataset.industry || '';
        
        const matchesSearch = text.includes(currentSearchKeyword);
        const matchesPrice = !isPriceFilterActive || price < 10;
        const isChuangKe = b === '创业板' || b === '科创板';
        const matchesChuangKe = !isHideChuangKeActive || !isChuangKe;
        
        if (matchesSearch && matchesPrice && matchesChuangKe) {
          tr.style.display = '';
          visibleCount++;
          if (i && i !== 'nan') industryCounts[i] = (industryCounts[i] || 0) + 1;
        } else {
          tr.style.display = 'none';
        }
      });

      renderStats('boardStatsContainer', industryCounts);
      
      const countEl = document.getElementById('visibleCount');
      if (countEl) countEl.textContent = '共 ' + visibleCount + ' 只';
    }

    function renderStats(containerId, countsObj) {
      const container = document.getElementById(containerId);
      if (!container) return;
      const sorted = Object.entries(countsObj).sort((a, b) => b[1] - a[1]).slice(0, 10);
      container.innerHTML = sorted.map(item => `<span class="tag">${item[0]} ${item[1]}</span>`).join('\\n');
    }

    function loadChecked() {
      const checked = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      checked.forEach(code => {
        const cb = document.querySelector(`input[data-code="${code}"]`);
        if (cb) { cb.checked = true; cb.closest('tr').classList.add('checked'); }
      });
      updateInfo();
    }

    function saveChecked() {
      const checked = [];
      document.querySelectorAll('.check:checked').forEach(cb => { checked.push(cb.dataset.code); cb.closest('tr').classList.add('checked'); });
      document.querySelectorAll('.check:not(:checked)').forEach(cb => { cb.closest('tr').classList.remove('checked'); });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(checked));
      updateInfo();
    }

    function updateInfo() {
      const count = document.querySelectorAll('.check:checked').length;
      document.getElementById('checkedInfo').textContent = '已选 ' + count;
    }

    function selectAll() { document.querySelectorAll('.check').forEach(cb => cb.checked = true); saveChecked(); }
    function clearAll() { document.querySelectorAll('.check').forEach(cb => cb.checked = false); saveChecked(); }

    function showStock(url) {
      currentUrl = url;
      const match = url.match(/([a-z]+\\d+)\\.html/);
      if(match) {
          const code = match[1];
          document.getElementById('stockTitle').textContent = code.toUpperCase();
      }
      document.getElementById('openNew').style.display = 'inline';
      document.getElementById('placeholder').style.display = 'none';
      document.getElementById('frameWrapper').style.display = 'block';
      const frame = document.getElementById('stockFrame');
      frame.src = url;
    }
    """
    
    (asset_dir / "common_detail.css").write_text(detail_css, encoding="utf-8")
    (asset_dir / "common_detail.js").write_text(detail_js, encoding="utf-8")
