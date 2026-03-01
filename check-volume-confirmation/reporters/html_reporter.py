# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd


def generate_html_report(
    df: pd.DataFrame,
    output_dir: Path,
    title: str,
    report_date: str,
    module_name: str,
    strategy_name: str,
) -> Path:
    ts = datetime.now().strftime("%H%M%S")
    summary_path = output_dir / f"summary_{report_date}_{ts}.html"

    data_date = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:8]}"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    grouped = _build_groups(df)
    for group_name, group_df in grouped:
        _write_detail_page(
            output_dir=output_dir,
            group_name=group_name,
            group_df=group_df,
            title=title,
            data_date=data_date,
            generated_at=generated_at,
        )

    default_group = grouped[0][0] if grouped else "全部命中"
    summary_html = _build_summary_html(
        title=title,
        data_date=data_date,
        generated_at=generated_at,
        strategy_name=strategy_name,
        total_count=len(df),
        groups=grouped,
        default_group=default_group,
    )
    summary_path.write_text(summary_html, encoding="utf-8")

    _export_to_index_csv(df, module_name, strategy_name, report_date, summary_path)
    return summary_path


def _build_groups(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    groups: list[tuple[str, pd.DataFrame]] = [("全部命中", df.copy())]
    if df.empty or "board" not in df.columns:
        return groups

    board_order = ["主板", "创业板", "科创板", "北交所", "其他"]

    board_map = {
        "上海主板": "主板",
        "深圳主板": "主板",
        "主板": "主板",
        "创业板": "创业板",
        "科创板": "科创板",
        "北交所": "北交所",
    }

    tagged = df.copy()
    tagged["group"] = tagged["board"].map(lambda x: board_map.get(str(x), "其他"))

    for group_name in board_order:
        sub_df = tagged[tagged["group"] == group_name].drop(columns=["group"], errors="ignore")
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
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, "Microsoft YaHei", sans-serif;
            background: #f5f5f5;
            height: 100vh;
            overflow: hidden;
        }}
        .layout {{ display: flex; height: 100vh; }}
        .sidebar {{
            width: 220px;
            background: #fff;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
        }}
        .logo {{
            padding: 18px 20px;
            font-size: 16px;
            font-weight: 600;
            color: #333;
            border-bottom: 1px solid #e0e0e0;
        }}
        .meta {{
            padding: 12px 20px;
            border-bottom: 1px solid #e0e0e0;
            color: #666;
            font-size: 12px;
            line-height: 1.7;
        }}
        .nav {{
            flex: 1;
            overflow-y: auto;
            padding: 10px 0;
        }}
        .nav-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .nav-item:hover {{ background: #f5f5f5; }}
        .nav-item.active {{
            background: #e3f2fd;
            color: #1976d2;
        }}
        .group-name {{ font-size: 14px; }}
        .group-count {{
            font-size: 12px;
            background: #e0e0e0;
            padding: 2px 8px;
            border-radius: 10px;
        }}
        .nav-item.active .group-count {{
            background: #1976d2;
            color: #fff;
        }}
        .main {{ flex: 1; background: #fff; }}
        iframe {{ width: 100%; height: 100%; border: none; }}
    </style>
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

    <script>
        function showGroup(groupName) {{
            const frame = document.getElementById('contentFrame');
            frame.src = `${{groupName}}.html`;

            document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
            const current = Array.from(document.querySelectorAll('.nav-item'))
                .find(item => item.querySelector('.group-name').textContent === groupName);
            if (current) {{
                current.classList.add('active');
            }}
        }}
    </script>
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
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, "Microsoft YaHei", sans-serif;
        font-size: 13px;
        color: #333;
        background: #fff;
        height: 100vh;
        overflow: hidden;
    }}
    .layout {{ display: flex; height: 100vh; }}
    .left-panel {{
        width: 60%;
        min-width: 520px;
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
    .header {{
        padding: 16px 20px;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .toolbar {{
        display: flex;
        gap: 10px;
        align-items: center;
    }}
    .search {{
        padding: 6px 10px;
        border: 1px solid #ddd;
        border-radius: 4px;
        width: 150px;
        font-size: 12px;
    }}
    .btn {{
        padding: 6px 12px;
        border: 1px solid #ddd;
        background: #fff;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
    }}
    .btn:hover {{ background: #f5f5f5; }}
    .btn.active {{
        background: #e3f2fd;
        color: #1976d2;
        border-color: #1976d2;
        font-weight: bold;
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
    .title {{
        font-size: 16px;
        font-weight: 600;
    }}
    .count {{
        color: #666;
        margin-left: 8px;
    }}
    .meta {{
        color: #666;
        font-size: 12px;
    }}
    .table-wrap {{
        flex: 1;
        overflow: auto;
    }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #eee; padding: 10px 12px; text-align: left; }}
    th {{ background: #fafafa; font-weight: 500; position: sticky; top: 0; z-index: 10; }}
    tr:nth-child(even) {{ background: #fafafa; }}
    tr:hover {{ background: #f9f9f9; }}
    tr.checked {{ background: #e8f5e9; }}
    .code {{
        color: #1976d2;
        text-decoration: none;
        cursor: pointer;
    }}
    .code:hover {{ text-decoration: underline; }}
    .checked-info {{
        font-size: 12px;
        color: #4caf50;
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
    .open-new {{
        font-size: 11px;
        color: #1976d2;
        text-decoration: none;
        cursor: pointer;
    }}
    .open-new:hover {{ text-decoration: underline; }}
    .placeholder {{
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #999;
    }}
    /* iframe 居中包装器 */
    .iframe-wrapper {{
        flex: 1;
        width: 100%;
        overflow: hidden;
        position: relative;
        background: #fff;
    }}
    .stock-frame {{
        width: 150%;
        height: 100%;
        border: none;
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
    }}
  </style>
</head>
<body>
  <div class="layout">
    <div class="left-panel">
      <div class="header">
        <div>
          <span class="title">{escape(title)} - {escape(group_name)}</span>
          <span class="count">共 {len(group_df)} 只</span>
        </div>
        <div class="toolbar">
          <span class="checked-info" id="checkedInfo">已选 0</span>
          <button id="shipanFilterBtn" class="btn" onclick="toggleShipanFilter()">试盘</button>
          <button id="priceFilterBtn" class="btn active" onclick="togglePriceFilter()">股价 < 10</button>
          <button class="btn" onclick="selectAll()">全选</button>
          <button class="btn" onclick="clearAll()">清除</button>
          <input type="text" class="search" placeholder="搜索..." oninput="filterTable(this.value)">
          <div class="meta">数据日期: {data_date}</div>
        </div>
      </div>
      <div class="stats">
        <div class="stats-group">
          <span class="stats-label">板块:</span>
          {_build_stats_tags(group_df, 'board')}
        </div>
        <div class="stats-group">
          <span class="stats-label">行业:</span>
          {_build_stats_tags(group_df, 'industry')}
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
              <th>试盘次数</th>
              <th>今天开盘</th>
              <th>今天收盘</th>
              <th>昨天量</th>
              <th>前2天量</th>
              <th>前3天量</th>
              <th>前4天量</th>
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
    const STORAGE_KEY = 'volume_confirmation_{escape(group_name.replace(" ", "_"))}';
    let currentUrl = '';
    let isPriceFilterActive = true; // 默认开启
    let isShipanFilterActive = true; // 试盘筛选默认开启
    let currentSearchKeyword = '';

    // 初始化
    document.addEventListener('DOMContentLoaded', () => {{
      loadChecked();
      const btn = document.getElementById('shipanFilterBtn');
      if (isShipanFilterActive) {{
        btn.classList.add('active');
      }}
      applyFilters(); // 初始应用筛选
    }});

    function togglePriceFilter() {{
      isPriceFilterActive = !isPriceFilterActive;
      const btn = document.getElementById('priceFilterBtn');
      if (isPriceFilterActive) {{
        btn.classList.add('active');
      }} else {{
        btn.classList.remove('active');
      }}
      applyFilters();
    }}

    function toggleShipanFilter() {{
      isShipanFilterActive = !isShipanFilterActive;
      const btn = document.getElementById('shipanFilterBtn');
      if (isShipanFilterActive) {{
        btn.classList.add('active');
      }} else {{
        btn.classList.remove('active');
      }}
      applyFilters();
    }}

    function filterTable(keyword) {{
      currentSearchKeyword = keyword.toLowerCase();
      applyFilters();
    }}

    function applyFilters() {{
      document.querySelectorAll('#tbody tr').forEach(tr => {{
        const price = parseFloat(tr.dataset.price || 0);
        const shipanCount = parseInt(tr.dataset.shipan || 0);
        const text = tr.textContent.toLowerCase();
        
        const matchesSearch = text.includes(currentSearchKeyword);
        const matchesPrice = !isPriceFilterActive || price < 10;
        const matchesShipan = !isShipanFilterActive || shipanCount >= 2;
        
        tr.style.display = (matchesSearch && matchesPrice && matchesShipan) ? '' : 'none';
      }});
    }}

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

    function showStock(url) {{
      currentUrl = url;
      const code = url.match(/([a-z]+\\d+)\\.html/)[1];
      document.getElementById('stockTitle').textContent = code.toUpperCase();
      document.getElementById('openNew').style.display = 'inline';
      document.getElementById('placeholder').style.display = 'none';
      document.getElementById('frameWrapper').style.display = 'block';
      const frame = document.getElementById('stockFrame');
      frame.src = url;
    }}
  </script>
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
        em_code = f"sh{code}" if code.startswith("6") else f"sz{code}"
        em_url = f"https://quote.eastmoney.com/{em_code}.html"
        
        shipan_display = f'<span title="{escape(shipan_detail)}">{shipan_count}</span>' if shipan_count > 0 else "0"
        
        chunks.append(
            f"<tr data-code=\"{code}\" data-price=\"{close_price}\" data-shipan=\"{shipan_count}\">"
            f"<td><input type=\"checkbox\" class=\"check\" data-code=\"{code}\" onchange=\"saveChecked()\"></td>"
            f"<td><a href=\"javascript:void(0)\" class=\"code\" onclick=\"showStock('{escape(em_url)}')\">{escape(code)}</a></td>"
            f"<td>{escape(str(row['name']))}</td>"
            f"<td>{escape(str(row['board']))}</td>"
            f"<td>{escape(str(row['industry']))}</td>"
            f"<td>{shipan_display}</td>"
            f"<td>{close_price:.3f}</td>"
            f"<td>{float(row['close_0']):.3f}</td>"
            f"<td>{float(row['volume_m1']):.0f}</td>"
            f"<td>{float(row['volume_m2']):.0f}</td>"
            f"<td>{float(row['volume_m3']):.0f}</td>"
            f"<td>{float(row['volume_m4']):.0f}</td>"
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

    date_folder = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:8]}"
    project_root = Path(__file__).resolve().parent.parent.parent
    index_dir = project_root / "get-data" / "data" / "stocks_index" / date_folder
    index_dir.mkdir(parents=True, exist_ok=True)
    index_file = index_dir / "stocks_index.csv"

    web_path = str(report_path.relative_to(project_root)).replace("\\", "/")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for _, row in df.iterrows():
        rows.append(
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
        )

    append_df = pd.DataFrame(rows)
    if index_file.exists():
        append_df.to_csv(index_file, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        append_df.to_csv(index_file, index=False, encoding="utf-8-sig")
