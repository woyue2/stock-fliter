# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame, title, dates
# OUTPUT: Path (HTML summary)
# POS:    check-volupxyangxshipan/reporters/html_reporter.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd

# 确保 util/ 可被导入
_UTIL_DIR = Path(__file__).resolve().parent.parent.parent / "util"
if str(_UTIL_DIR) not in sys.path:
    sys.path.insert(0, str(_UTIL_DIR))
from index_writer import write_to_stocks_index  # noqa: E402


def generate_html_report(
    df: pd.DataFrame,
    output_dir: Path,
    title: str,
    report_date: str,
    module_name: str,
    strategy_name: str,
    full_market_df: Optional[pd.DataFrame] = None,
) -> Path:
    ts = datetime.now().strftime("%H%M%S")
    summary_path = output_dir / f"summary_{report_date}_{ts}.html"

    data_date = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:8]}"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    _write_assets(output_dir)
    
    # 汇总各组数据
    matched_groups = _build_groups(df)
    final_groups = []
    
    # 如果有全市场数据，先加入全市场组（方便搜索全量）
    if full_market_df is not None and not full_market_df.empty:
        final_groups.append(("全市场", full_market_df.copy()))
        
    final_groups.extend(matched_groups)

    for group_name, group_df in final_groups:
        _write_detail_page(
            output_dir=output_dir,
            group_name=group_name,
            group_df=group_df,
            title=title,
            data_date=data_date,
            generated_at=generated_at,
        )

    default_group = final_groups[0][0] if final_groups else "全市场"
    summary_html = _build_summary_html(
        title=title,
        data_date=data_date,
        generated_at=generated_at,
        strategy_name=strategy_name,
        total_count=len(df),
        groups=final_groups,
        default_group=default_group,
    )
    summary_path.write_text(summary_html, encoding="utf-8")

    _export_to_index_csv(df, module_name, strategy_name, report_date, summary_path)
    return summary_path


def _build_groups(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    groups: list[tuple[str, pd.DataFrame]] = [("全部命中", df.copy())]
    if df.empty or "tag" not in df.columns:
        return groups

    tag_order = ["多重试盘", "准突破", "纯量价"]

    for group_name in tag_order:
        sub_df = df[df["tag"] == group_name]
        if len(sub_df) > 0:
            groups.append((group_name, sub_df.reset_index(drop=True)))
    return groups


def _build_summary_html(
    title: str,
    data_date: str,
    generated_at: str,
    strategy_name: str,
    total_count: int,
    groups: list[tuple[str, pd.DataFrame]],
    default_group: str,
) -> str:
    nav_items = []
    for group_name, group_df in groups:
        active = "active" if group_name == default_group else ""
        nav_items.append(
            f'''<div class="nav-item {active}" onclick="showGroup('{escape(group_name)}')">
                <span class="group-name">{escape(group_name)}</span>
                <span class="group-count">{len(group_df)}</span>
            </div>'''
        )

    nav_html = "\n".join(nav_items)
    default_src = f"{default_group}.html"

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)} - {data_date}</title>
    <link rel="stylesheet" href="assets/common_summary.css">
</head>
<body>
    <div class="layout">
        <aside class="sidebar">
            <div class="logo">📊 {escape(title)}</div>
            <div class="meta">
                <div>策略: {escape(strategy_name)}</div>
                <div>数据日期: {data_date}</div>
                <div>命中数量: {total_count}</div>
                <div>生成时间: {generated_at}</div>
            </div>
            <nav class="nav">
                {nav_html}
            </nav>
        </aside>
        <main class="main">
            <iframe id="contentFrame" src="{escape(default_src)}"></iframe>
        </main>
    </div>

    <script src="assets/common_summary.js"></script>
</body>
</html>
'''


def _write_detail_page(
    output_dir: Path,
    group_name: str,
    group_df: pd.DataFrame,
    title: str,
    data_date: str,
    generated_at: str,
) -> None:
    detail_path = output_dir / f"{group_name}.html"
    rows_html = _build_rows_html(group_df)

    detail_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)} - {escape(group_name)}</title>
  <link rel="stylesheet" href="assets/common_detail.css">
</head>
<body>
  <div class="layout">
    <div class="left-panel">
      <div class="header">
        <div>
          <span class="title">{escape(title)} - {escape(group_name)}</span>
          <span class="count" id="visibleCount">共 {len(group_df)} 只</span>
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
          <span id="boardStatsContainer">{_build_stats_tags(group_df, 'board')}</span>
        </div>
        <div class="stats-group">
          <span class="stats-label">行业:</span>
          <span id="industryStatsContainer">{_build_stats_tags(group_df, 'industry')}</span>
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
              <th>信心分</th>
              <th>标签</th>
              <th>试盘</th>
              <th>量比</th>
              <th>今天收盘</th>
              <th>昨天量</th>
              <th>前3日均量</th>
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
    const STORAGE_KEY = 'volupxyangxshipan_{escape(group_name.replace(" ", "_"))}';
  </script>
  <script src="assets/common_detail.js"></script>
</body>
</html>
'''
    detail_path.write_text(detail_html, encoding="utf-8")


def _build_rows_html(df: pd.DataFrame) -> str:
    if df.empty:
        return '<tr><td colspan="12">无命中股票</td></tr>'

    chunks: list[str] = []
    for _, row in df.iterrows():
        code = str(row["code"])
        close_price = float(row['close_0'])
        shipan_count = int(row.get('shipan_count', 0))
        shipan_detail = str(row.get('shipan_detail', ''))
        confidence = int(row.get('confidence', 0))
        tag = escape(str(row.get('tag', '')))
        volume_ratio = float(row.get('volume_ratio', 0.0))
        avg_prev_vol = (float(row.get('volume_m2', 0)) + float(row.get('volume_m3', 0)) + float(row.get('volume_m4', 0))) / 3.0
        
        em_code = f"sh{code}" if code.startswith("6") else f"sz{code}"
        em_url = f"https://quote.eastmoney.com/{em_code}.html"
        
        shipan_display = f'<span title="{escape(shipan_detail)}">{shipan_count}</span>' if shipan_count > 0 else "0"
        
        if tag == "多重试盘":
            tag_class = "tag-strong"
        elif tag == "准突破":
            tag_class = "tag-mod"
        else:
            tag_class = "tag-plain"
            
        conf_class = "conf-high" if confidence >= 60 else ""
        
        board_str = escape(str(row['board']))
        industry_str = escape(str(row['industry']))
        is_hit = row.get('is_hit', True)
        
        row_style = "" if is_hit else "style=\"opacity: 0.6; filter: grayscale(0.8);\""
        hit_tag = "" if is_hit else "<span style=\"color:#999;font-size:11px\"> (未命中)</span>"
        
        chunks.append(
            f"<tr data-code=\"{code}\" data-price=\"{close_price}\" data-board=\"{board_str}\" data-industry=\"{industry_str}\" {row_style}>"
            f"<td><input type=\"checkbox\" class=\"check\" data-code=\"{code}\" onchange=\"saveChecked()\"></td>"
            f"<td><a href=\"javascript:void(0)\" class=\"code\" onclick=\"showStock('{escape(em_url)}')\">{escape(code)}</a></td>"
            f"<td>{escape(str(row['name']))}{hit_tag}</td>"
            f"<td>{board_str}</td>"
            f"<td>{industry_str}</td>"
            f"<td class=\"{conf_class}\">{confidence}</td>"
            f"<td class=\"{tag_class}\">{tag}</td>"
            f"<td>{shipan_display}</td>"
            f"<td>{volume_ratio:.2f}</td>"
            f"<td>{close_price:.3f}</td>"
            f"<td>{float(row.get('volume_m1', 0)):.0f}</td>"
            f"<td>{avg_prev_vol:.0f}</td>"
            "</tr>"
        )
    return "\n".join(chunks)


def _build_stats_tags(df: pd.DataFrame, column: str) -> str:
    if column not in df.columns:
        return ""
    stats = df[column].value_counts().head(10)
    tags = []
    for val, count in stats.items():
        tags.append(f'<span class="tag">{escape(str(val))} {count}</span>')
    return "\n".join(tags)


def _export_to_index_csv(
    df: pd.DataFrame,
    module_name: str,
    strategy_name: str,
    report_date: str,
    report_path: Path,
) -> None:
    if df.empty:
        return

    project_root = Path(__file__).resolve().parent.parent.parent
    web_path = str(report_path.relative_to(project_root)).replace("\\", "/")
    date_folder = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:8]}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = [
        {
            "代码": row["code"],
            "名称": row["name"],
            "日期": date_folder,
            "模块": module_name,
            "策略级别": strategy_name,
            "报告路径": web_path,
            "板块": row["board"],
            "行业": row["industry"],
            "生成时间": now_str,
        }
        for _, row in df.iterrows()
    ]

    write_to_stocks_index(rows, report_date, project_root)

def _write_assets(output_dir: Path) -> None:
    asset_dir = output_dir / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    
    summary_css = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f5f5f5; height: 100vh; overflow: hidden; }
        .layout { display: flex; height: 100vh; }
        .sidebar { width: 220px; background: #fff; border-right: 1px solid #e0e0e0; display: flex; flex-direction: column; }
        .logo { padding: 18px 20px; font-size: 16px; font-weight: 600; color: #333; border-bottom: 1px solid #e0e0e0; }
        .meta { padding: 12px 20px; border-bottom: 1px solid #e0e0e0; color: #666; font-size: 12px; line-height: 1.7; }
        .nav { flex: 1; overflow-y: auto; padding: 10px 0; }
        .nav-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; cursor: pointer; transition: all 0.2s; }
        .nav-item:hover { background: #f5f5f5; }
        .nav-item.active { background: #e3f2fd; color: #1976d2; }
        .group-name { font-size: 14px; }
        .group-count { font-size: 12px; background: #e0e0e0; padding: 2px 8px; border-radius: 10px; }
        .nav-item.active .group-count { background: #1976d2; color: #fff; }
        .main { flex: 1; background: #fff; }
        iframe { width: 100%; height: 100%; border: none; }
    """
    
    summary_js = """
        function showGroup(groupName) {
            const frame = document.getElementById('contentFrame');
            frame.src = `${groupName}.html`;

            document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
            const current = Array.from(document.querySelectorAll('.nav-item'))
                .find(item => item.querySelector('.group-name').textContent === groupName);
            if (current) {
                current.classList.add('active');
            }
        }
    """
    
    detail_css = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, "Microsoft YaHei", sans-serif; font-size: 13px; color: #333; background: #fff; height: 100vh; overflow: hidden; }
    .layout { display: flex; height: 100vh; }
    .left-panel { width: 60%; min-width: 520px; display: flex; flex-direction: column; border-right: 1px solid #e0e0e0; }
    .right-panel { flex: 1; display: flex; flex-direction: column; background: #fafafa; }
    .header { padding: 16px 20px; border-bottom: 1px solid #e0e0e0; display: flex; justify-content: space-between; align-items: center; }
    .toolbar { display: flex; gap: 10px; align-items: center; }
    .search { padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; width: 150px; font-size: 12px; }
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
    .tag-mod { color: #f57c00; font-weight: bold; }
    .tag-plain { color: #666; }
    .conf-high { color: #d32f2f; font-weight: bold; }
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
    let isPriceFilterActive = true;
    let isHideChuangKeActive = true;
    let currentSearchKeyword = '';

    document.addEventListener('DOMContentLoaded', () => {
      loadChecked();
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
      const boardCounts = {};
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
          if (b) boardCounts[b] = (boardCounts[b] || 0) + 1;
          if (i) industryCounts[i] = (industryCounts[i] || 0) + 1;
        } else {
          tr.style.display = 'none';
        }
      });

      renderStats('boardStatsContainer', boardCounts);
      renderStats('industryStatsContainer', industryCounts);
      
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
      const code = url.match(/([a-z]+\\d+)\\.html/)[1];
      document.getElementById('stockTitle').textContent = code.toUpperCase();
      document.getElementById('openNew').style.display = 'inline';
      document.getElementById('placeholder').style.display = 'none';
      document.getElementById('frameWrapper').style.display = 'block';
      const frame = document.getElementById('stockFrame');
      frame.src = url;
    }
    """
    
    (asset_dir / "common_summary.css").write_text(summary_css, encoding="utf-8")
    (asset_dir / "common_summary.js").write_text(summary_js, encoding="utf-8")
    (asset_dir / "common_detail.css").write_text(detail_css, encoding="utf-8")
    (asset_dir / "common_detail.js").write_text(detail_js, encoding="utf-8")
