# -*- coding: utf-8 -*-
"""
生成选股报告索引页 reports_index.html。

扫描 check-steady-uptrend/output 与 check-trend-bottom/output，
按日期聚合，同一日期只链接该日最新时间戳下的 summary 报告。
索引页生成在项目根目录，链接为相对路径，便于本地双击打开使用。
"""

import os
import re
from pathlib import Path
import webbrowser


# 模块显示名 -> output 相对路径（相对项目根）
CONFIG = [
    ("稳步上升", "check-steady-uptrend/output"),
    ("TD九底", "check-trend-bottom/output"),
    ("指标组合", "check-indicator-combo/output"),  # 新增
    ("量价确认", "check-volume-confirmation/output"),
]

# 日期目录 YYYY-MM-DD
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 时间目录 HH-MM-SS
TIME_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{2}$")


def project_root() -> Path:
    """项目根目录（scripts 的上一级）。"""
    return Path(__file__).resolve().parent.parent


def extract_data_date_from_filename(filename: str) -> str | None:
    """
    从 summary_YYYYMMDD_HHMMSS.html 中提取数据日期 YYYYMMDD，
    转换为 YYYY-MM-DD 格式。
    """
    match = re.match(r"summary_(\d{8})_\d{6}\.html", filename)
    if match:
        date_str = match.group(1)  # YYYYMMDD
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return None


def find_latest_summary_for_date(output_root: Path, date_str: str) -> Path | None:
    """
    在 output_root/date_str 下找最新的 HH-MM-SS 目录，返回其内 summary_*.html 路径。
    若不存在或没有 summary 文件则返回 None。
    """
    date_dir = output_root / date_str
    if not date_dir.is_dir():
        return None
    time_dirs = [
        d for d in date_dir.iterdir()
        if d.is_dir() and TIME_PATTERN.match(d.name)
    ]
    if not time_dirs:
        return None
    latest_time_dir = sorted(time_dirs, key=lambda d: d.name, reverse=True)[0]
    summaries = list(latest_time_dir.glob("summary_*.html"))
    if not summaries:
        return None
    return summaries[0]


def scan_module(project: Path, module_name: str, output_rel: str) -> dict[str, Path]:
    """
    扫描一个模块的 output 目录。
    返回: 数据日期字符串 -> 该日期下最新 summary 的路径（相对 project）。
    注意：这里的日期是从文件名中提取的数据日期，而不是目录名（生成日期）。
    """
    result = {}
    output_root = project / output_rel
    if not output_root.is_dir():
        return result
    
    # 收集所有 summary 文件及其数据日期
    summaries_by_data_date = {}  # data_date -> [(gen_date, gen_time, path)]
    
    for gen_date_dir in output_root.iterdir():
        if not gen_date_dir.is_dir() or not DATE_PATTERN.match(gen_date_dir.name):
            continue
        
        for gen_time_dir in gen_date_dir.iterdir():
            if not gen_time_dir.is_dir() or not TIME_PATTERN.match(gen_time_dir.name):
                continue
            
            for summary_file in gen_time_dir.glob("summary_*.html"):
                # 从文件名提取数据日期
                data_date = extract_data_date_from_filename(summary_file.name)
                if data_date is None:
                    continue
                
                if data_date not in summaries_by_data_date:
                    summaries_by_data_date[data_date] = []
                
                summaries_by_data_date[data_date].append(
                    (gen_date_dir.name, gen_time_dir.name, summary_file)
                )
    
    # 对每个数据日期，选择最新生成的报告
    for data_date, summaries in summaries_by_data_date.items():
        # 按生成日期和时间排序，取最新的
        summaries.sort(key=lambda x: (x[0], x[1]), reverse=True)
        latest_summary = summaries[0][2]
        
        try:
            rel = latest_summary.relative_to(project)
            result[data_date] = rel
        except ValueError:
            continue
    
    return result


def collect_all_dates(per_module: dict[str, dict[str, Path]]) -> list[str]:
    """汇总所有出现过的日期，降序排列。"""
    dates = set()
    for data in per_module.values():
        dates.update(data.keys())
    return sorted(dates, reverse=True)


def build_list_html(project: Path, per_module: dict[str, dict[str, Path]], dates: list[str], output_dir: Path) -> str:
    """生成简单列表页 HTML 内容（reports_list.html）。"""
    module_names = [name for name, _ in CONFIG]
    rows = []
    for date_str in dates:
        cells = [f"<td>{date_str}</td>"]
        for name in module_names:
            data = per_module.get(name, {})
            path = data.get(date_str)
            if path:
                # 使用相对路径（从 output_dir 到 report 文件）
                rel_path = os.path.relpath(project / path, output_dir)
                cells.append(f'<td><a href="{rel_path}" target="_blank">查看</a></td>')
            else:
                cells.append("<td>-</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    thead = "<tr><th>日期</th>" + "".join(f"<th>{name}</th>" for name in module_names) + "</tr>"
    tbody = "\n".join(rows)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>选股报告索引</title>
  <style>
    body {{ font-family: sans-serif; margin: 1rem 2rem; }}
    h1 {{ margin-bottom: 0.5rem; }}
    p {{ color: #666; margin-bottom: 1rem; }}
    table {{ border-collapse: collapse; }}
    th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.8rem; text-align: left; }}
    th {{ background: #f5f5f5; }}
    a {{ color: #06c; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>选股报告索引</h1>
  <p>按日期列出各模块报告，同一日期以该日最新生成的时间戳为准。双击打开本页后，点击「查看」即可打开对应报告。</p>
  <table>
    <thead>{thead}</thead>
    <tbody>
{tbody}
    </tbody>
  </table>
</body>
</html>
"""
    return html


def build_index_html(project: Path, per_module: dict[str, dict[str, Path]], dates: list[str], output_dir: Path) -> str:
    """生成带搜索功能的索引页 HTML 内容（reports_index.html）。"""
    module_names = [name for name, _ in CONFIG]

    # 构建报告列表的表格行
    table_rows = []
    for date_str in dates:
        cells = [f"<td>{date_str}</td>"]
        for name in module_names:
            data = per_module.get(name, {})
            path = data.get(date_str)
            if path:
                # 使用相对路径（从 output_dir 到 report 文件）
                rel_path = os.path.relpath(project / path, output_dir)
                cells.append(f'<td><a href="{rel_path}" target="_blank" class="link">查看</a></td>')
            else:
                cells.append("<td>-</td>")
        table_rows.append("<tr>" + "".join(cells) + "</tr>")

    table_body = "\n                        ".join(table_rows)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票报告索引 - 搜索</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 2rem;
        }}
        h1 {{
            color: #333;
            margin-bottom: 0.5rem;
            font-size: 2rem;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 2rem;
            font-size: 0.95rem;
        }}
        .search-box {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .search-box input {{
            flex: 1;
            padding: 0.75rem 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }}
        .search-box input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .btn {{
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 500;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        .btn-secondary {{
            background: #f5f5f5;
            color: #333;
        }}
        .btn-secondary:hover {{
            background: #e0e0e0;
        }}
        .actions {{
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .results {{
            margin-top: 2rem;
        }}
        .result-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e0e0e0;
        }}
        .result-count {{
            font-size: 1.1rem;
            color: #667eea;
            font-weight: 600;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .link {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        .link:hover {{
            text-decoration: underline;
        }}
        .empty {{
            text-align: center;
            padding: 3rem;
            color: #999;
        }}
        .loading {{
            text-align: center;
            padding: 2rem;
            color: #667eea;
        }}
        .error {{
            background: #fee;
            color: #c33;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }}
        .stat-label {{
            font-size: 0.9rem;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 股票报告搜索</h1>
        <p class="subtitle">搜索股票在不同日期、不同分析模块中的出现情况</p>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="输入股票代码或名称（如：600519 或 茅台）" />
            <button class="btn btn-primary" onclick="searchStock()">🔍 搜索</button>
        </div>
        
        <div class="actions">
            <button class="btn btn-secondary" onclick="showHotStocks()">🔥 热门股票</button>
            <button class="btn btn-secondary" onclick="showStats()">📈 统计信息</button>
            <button class="btn btn-secondary" onclick="showReportIndex()">📋 报告列表</button>
        </div>
        
        <div id="results" class="results"></div>
    </div>

    <script>
        const API_BASE = 'http://127.0.0.1:5000';

        // 回车搜索
        document.getElementById('searchInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                searchStock();
            }}
        }});
        
        // 搜索股票
        async function searchStock() {{
            const keyword = document.getElementById('searchInput').value.trim();
            if (!keyword) {{
                alert('请输入股票代码或名称');
                return;
            }}
            
            showLoading();
            
            try {{
                // 判断是代码还是名称
                const isCode = /^\\d+$/.test(keyword);
                const param = isCode ? `code=${{keyword}}` : `name=${{keyword}}`;
                
                const response = await fetch(`${{API_BASE}}/api/search?${{param}}`);
                const data = await response.json();
                
                if (data.error) {{
                    showError(data.error);
                    return;
                }}
                
                displayResults(data.results, `搜索结果：${{keyword}}`);
            }} catch (error) {{
                showError('搜索失败，请确保API服务已启动');
                console.error(error);
            }}
        }}
        
        // 显示热门股票
        async function showHotStocks() {{
            showLoading();
            
            try {{
                const response = await fetch(`${{API_BASE}}/api/hot-stocks?limit=20`);
                const data = await response.json();
                
                displayHotStocks(data);
            }} catch (error) {{
                showError('获取热门股票失败，请确保API服务已启动');
                console.error(error);
            }}
        }}
        
        // 显示统计信息
        async function showStats() {{
            showLoading();
            
            try {{
                const response = await fetch(`${{API_BASE}}/api/stats`);
                const data = await response.json();
                
                if (data.error) {{
                    showError(data.error);
                    return;
                }}
                
                displayStats(data);
            }} catch (error) {{
                showError('获取统计信息失败，请确保API服务已启动');
                console.error(error);
            }}
        }}
        
        // 显示报告列表（使用数据日期）
        function showReportIndex() {{
            const html = `
                <div class="result-header">
                    <h2>📋 报告列表</h2>
                    <span class="result-count">按数据日期排序</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>数据日期</th>
                            {"".join(f"<th>{name}</th>" for name in module_names)}
                        </tr>
                    </thead>
                    <tbody>
                        {table_body}
                    </tbody>
                </table>
            `;
            document.getElementById('results').innerHTML = html;
        }}
        
        // 显示搜索结果
        function displayResults(results, title) {{
            if (results.length === 0) {{
                document.getElementById('results').innerHTML = `
                    <div class="empty">
                        <h3>😔 未找到结果</h3>
                        <p>请尝试其他关键词</p>
                    </div>
                `;
                return;
            }}
            
            let html = `
                <div class="result-header">
                    <h2>${{title}}</h2>
                    <span class="result-count">共 ${{results.length}} 条记录</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>代码</th>
                            <th>名称</th>
                            <th>日期</th>
                            <th>模块</th>
                            <th>策略级别</th>
                            <th>板块</th>
                            <th>行业</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            results.forEach(item => {{
                html += `
                    <tr>
                        <td>${{item.代码}}</td>
                        <td>${{item.名称}}</td>
                        <td>${{item.日期}}</td>
                        <td>${{item.模块}}</td>
                        <td>${{item.策略级别}}</td>
                        <td>${{item.板块}}</td>
                        <td>${{item.行业}}</td>
                        <td><a href="${{item.报告路径}}" target="_blank" class="link">查看报告</a></td>
                    </tr>
                `;
            }});
            
            html += '</tbody></table>';
            document.getElementById('results').innerHTML = html;
        }}
        
        // 显示热门股票
        function displayHotStocks(data) {{
            if (data.length === 0) {{
                document.getElementById('results').innerHTML = '<div class="empty">暂无数据</div>';
                return;
            }}
            
            let html = `
                <div class="result-header">
                    <h2>🔥 热门股票 Top 20</h2>
                    <span class="result-count">按出现次数排序</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>代码</th>
                            <th>名称</th>
                            <th>出现次数</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            data.forEach((item, index) => {{
                html += `
                    <tr>
                        <td>${{index + 1}}</td>
                        <td>${{item.代码}}</td>
                        <td>${{item.名称}}</td>
                        <td><strong>${{item.出现次数}}</strong></td>
                        <td><a href="javascript:void(0)" onclick="searchByCode('${{item.代码}}')" class="link">查看详情</a></td>
                    </tr>
                `;
            }});
            
            html += '</tbody></table>';
            document.getElementById('results').innerHTML = html;
        }}
        
        // 显示统计信息
        function displayStats(data) {{
            let modulesHtml = '';
            for (const [module, count] of Object.entries(data.modules)) {{
                modulesHtml += `
                    <div class="stat-card">
                        <div class="stat-value">${{count}}</div>
                        <div class="stat-label">${{module}}</div>
                    </div>
                `;
            }}
            
            const html = `
                <div class="result-header">
                    <h2>📈 统计信息</h2>
                </div>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">${{data.total_records}}</div>
                        <div class="stat-label">总记录数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${{data.unique_stocks}}</div>
                        <div class="stat-label">独立股票数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${{data.date_range.start}}</div>
                        <div class="stat-label">开始日期</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${{data.date_range.end}}</div>
                        <div class="stat-label">结束日期</div>
                    </div>
                </div>
                <div class="result-header" style="margin-top: 2rem;">
                    <h3>各模块统计</h3>
                </div>
                <div class="stats-grid">
                    ${{modulesHtml}}
                </div>
            `;
            
            document.getElementById('results').innerHTML = html;
        }}
        
        // 按代码搜索
        function searchByCode(code) {{
            document.getElementById('searchInput').value = code;
            searchStock();
        }}
        
        // 显示加载中
        function showLoading() {{
            document.getElementById('results').innerHTML = '<div class="loading">⏳ 加载中...</div>';
        }}
        
        // 显示错误
        function showError(message) {{
            document.getElementById('results').innerHTML = `<div class="error">❌ ${{message}}</div>`;
        }}
        
        // 页面加载时显示报告列表
        window.onload = function() {{
            showReportIndex();
        }};
    </script>
</body>
</html>
"""
    return html


def get_latest_stocks_index_date(project: Path) -> str | None:
    """获取最新的 stocks_index.csv 日期"""
    stocks_index_dir = project / "get-data" / "data" / "stocks_index"
    if not stocks_index_dir.exists():
        return None
    
    date_dirs = [d for d in stocks_index_dir.iterdir() if d.is_dir() and DATE_PATTERN.match(d.name)]
    if not date_dirs:
        return None
    
    # 返回最新日期
    latest_date = sorted(date_dirs, key=lambda d: d.name, reverse=True)[0].name
    return latest_date


def main() -> None:
    project = project_root()
    per_module = {}
    for module_name, output_rel in CONFIG:
        per_module[module_name] = scan_module(project, module_name, output_rel)
    dates = collect_all_dates(per_module)
    
    # 获取最新的 stocks_index.csv 日期
    latest_date = get_latest_stocks_index_date(project)
    if latest_date:
        print(f"使用最新日期的 stocks_index.csv: {latest_date}")
        # 创建带日期的输出目录
        output_dir = project / "report_index" / f"reports_index_{latest_date}"
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        print("未找到 stocks_index 日期目录，使用项目根目录")
        output_dir = project
    
    # 生成 reports_list.html（简单列表）
    list_html = build_list_html(project, per_module, dates, output_dir)
    list_path = output_dir / "reports_list.html"
    list_path.write_text(list_html, encoding="utf-8")
    print(f"已生成: {list_path}")

    # 生成 reports_index.html（带搜索功能）
    index_html = build_index_html(project, per_module, dates, output_dir)
    index_path = output_dir / "reports_index.html"
    index_path.write_text(index_html, encoding="utf-8")
    print(f"已生成: {index_path}")
    
    print(f"共 {len(dates)} 个日期, {sum(len(d) for d in per_module.values())} 条报告链接。")
    print(f"注意: reports_index.html 包含搜索功能，reports_list.html 是简单列表")
    
    # 自动打开 HTML 文件
    print(f"\n正在打开浏览器...")
    try:
        webbrowser.open(index_path.as_uri())
        print(f"✓ 已在浏览器中打开: {index_path}")
    except Exception as e:
        print(f"⚠ 无法自动打开浏览器: {e}")
        print(f"请手动打开: {index_path}")


if __name__ == "__main__":
    main()
