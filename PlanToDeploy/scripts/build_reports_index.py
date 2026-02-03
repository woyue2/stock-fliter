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
# 云端精简版: 固定入口仅关注云端轻量结果, 只保留 cloud_* 三个模块
CONFIG = [
    ("玄学(云端)", "output/cloud_xuanxue"),
    ("TD九底(云端)", "output/cloud_td"),
    ("新指标(云端)", "output/cloud_new"),
]


# 日期目录 YYYY-MM-DD
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 时间目录 HH-MM-SS
TIME_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{2}$")


def project_root() -> Path:
    """项目根目录（云端模式下即 PlanToDeploy 根目录）。

    通过向上查找包含 stream_run_daily.py 的目录来确定根路径，
    兼容「只部署 PlanToDeploy」和「完整仓库」两种结构。
    """
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "stream_run_daily.py").exists():
            return parent
    # 兜底：退回 scripts 的上一级
    return current


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


def build_list_html(project: Path, per_module: dict[str, dict[str, Path]], dates: list[str]) -> str:
    """生成简单列表页 HTML 内容（reports_list.html）。"""
    module_names = [name for name, _ in CONFIG]
    rows = []
    for date_str in dates:
        cells = [f"<td>{date_str}</td>"]
        for name in module_names:
            data = per_module.get(name, {})
            path = data.get(date_str)
            if path:
                # 统一使用标准 file:// 绝对路径, 便于在纯 Linux/Docker 环境中访问
                full_path = (project / path).resolve()
                href = full_path.as_uri()
                cells.append(f'<td><a href="{href}" target="_blank">查看</a></td>')
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


def build_index_html(project: Path, per_module: dict[str, dict[str, Path]], dates: list[str]) -> str:
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
                full_path = (project / path).resolve()
                href = full_path.as_uri()
                cells.append(f'<td><a href="{href}" target="_blank" class="link">查看</a></td>')
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
        .runner-panel {{
            margin-bottom: 1.5rem;
            padding: 1rem 1.25rem;
            border-radius: 8px;
            background: #e0f2f1;
            border: 1px solid #b2dfdb;
        }}
        .runner-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }}
        .runner-status-text {{
            font-size: 0.9rem;
            color: #004d40;
        }}
        .runner-controls {{
            display: flex;
            gap: 1rem;
            align-items: center;
            margin-bottom: 0.5rem;
            flex-wrap: wrap;
        }}
        .runner-controls label {{
            font-size: 0.85rem;
            color: #004d40;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }}
        .runner-controls input[type="date"],
        .runner-controls select {{
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            border: 1px solid #b2dfdb;
            font-size: 0.85rem;
        }}
        .logs {{
            background: #f5f5f5;
            border-radius: 6px;
            padding: 0.75rem;
            max-height: 260px;
            overflow-y: auto;
            font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 0.8rem;
            white-space: pre-wrap;
            line-height: 1.4;
        }}
        .runner-panel {{
            margin-bottom: 1.5rem;
            padding: 1rem 1.25rem;
            border-radius: 8px;
            background: #e0f2f1;
            border: 1px solid #b2dfdb;
        }}
        .runner-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }}
        .runner-status-text {{
            font-size: 0.9rem;
            color: #004d40;
        }}
        .logs {{
            background: #f5f5f5;
            border-radius: 6px;
            padding: 0.75rem;
            max-height: 260px;
            overflow-y: auto;
            font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 0.8rem;
            white-space: pre-wrap;
            line-height: 1.4;
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

        <div class="runner-panel">
            <div class="runner-header">
                <div>
                    <strong>云端 Runner 状态</strong>
                    <div id="runnerStatus" class="runner-status-text">状态: 未知</div>
                </div>
                <div>
                    <button class="btn btn-secondary" onclick="triggerRunDaily()">🚀 手动运行云端 Runner</button>
                    <button class="btn btn-secondary" style="margin-left: 0.5rem;" onclick="stopRunDaily()">⏹ 停止当前任务</button>
                </div>
            </div>
            <div class="runner-controls">
                <label>
                    <input type="checkbox" id="runnerTestMode" />
                    使用 test 模式(小样本股票池)
                </label>
                <label>
                    截止日期:
                    <input type="date" id="runnerEndDate" />
                </label>
            </div>
            <div id="runnerLogs" class="logs">日志尚未加载</div>
        </div>

        <div id="results" class="results"></div>
    </div>

    <script>
        // 与当前页面同源的 API 地址
        const API_BASE = '';
        // 项目根目录(用于将索引中的相对报告路径转换为本地 file:/// 绝对路径)
        const PROJECT_ROOT = '{project.as_uri()}';
        let logCursor = 0;
        let logTimer = null;

        function resolveReportHref(path) {{
            if (!path) return '#';
            if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('file://')) {{
                return path;
            }}
            try {{
                const base = PROJECT_ROOT.endsWith('/') ? PROJECT_ROOT : PROJECT_ROOT + '/';
                // 去掉开头的 ./ 或 /
                const clean = path.replace(/^\\.?\\//, '');
                return new URL(clean, base).href;
            }} catch (e) {{
                return path;
            }}
        }}
        
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
                        <td><a href="${{resolveReportHref(item.报告路径)}}" target="_blank" class="link">查看报告</a></td>
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
        
        async function stopRunDaily() {{
            if (!confirm('确认要停止当前运行中的云端 Runner 吗？')) {{
                return;
            }}
            try {{
                const resp = await fetch(`${{API_BASE}}/api/run-stop`, {{
                    method: 'POST'
                }});
                const data = await resp.json().catch(() => ({{}}));
                if (!resp.ok) {{
                    alert(data.error || data.message || '停止失败');
                    return;
                }}
                if (logTimer) {{
                    clearInterval(logTimer);
                    logTimer = null;
                }}
                logCursor = 0;
                document.getElementById('runnerLogs').textContent = '任务已停止';
                refreshRunnerStatus();
            }} catch (error) {{
                alert('停止失败，请确保 API 服务已启动');
            }}
        }}

        // 页面加载时显示报告列表
        window.onload = function() {{
            showReportIndex();
            refreshRunnerStatus();
        }};
    </script>
</body>
</html>
"""
    return html


def build_cloud_index_html(project: Path, per_module: dict[str, dict[str, Path]], dates: list[str]) -> str:
    """生成仅展示云端模块的索引页 HTML 内容（cloud_reports_index.html）。"""
    module_names = [name for name, _ in CONFIG if "(云端)" in name]
    
    # 构建报告列表的表格行(仅云端模块)
    table_rows = []
    for date_str in dates:
        cells = [f"<td>{date_str}</td>"]
        for name in module_names:
            data = per_module.get(name, {})
            path = data.get(date_str)
            if path:
                full_path = (project / path).resolve()
                try:
                    rel = full_path.relative_to(project)
                    href = f"/reports/{rel.as_posix()}"
                except ValueError:
                    href = "#"
                cells.append(f'<td><a href="{href}" target="_blank" class="link">查看</a></td>')
            else:
                # 无信号时也给一个“无信号”的占位链接, 不指向实际报告
                cells.append('<td><a href="javascript:void(0)" class="link link-empty">无信号</a></td>')
        table_rows.append("<tr>" + "".join(cells) + "</tr>")
    
    table_body = "\n                        ".join(table_rows)
    
    # 复用与 build_index_html 相同的样式和 JS, 只是标题与默认文案改为“云端轻量”
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>云端轻量报告索引 - 搜索</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #26a69a 0%, #004d40 100%);
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
            border-color: #26a69a;
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
            background: linear-gradient(135deg, #26a69a 0%, #004d40 100%);
            color: white;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(38, 166, 154, 0.4);
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
        .runner-panel {{
            margin-bottom: 1.5rem;
            padding: 1rem 1.25rem;
            border-radius: 8px;
            background: #e0f2f1;
            border: 1px solid #b2dfdb;
        }}
        .runner-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }}
        .runner-status-text {{
            font-size: 0.9rem;
            color: #004d40;
        }}
        .runner-controls {{
            display: flex;
            gap: 1rem;
            align-items: center;
            margin-bottom: 0.5rem;
        }}
        .runner-controls label {{
            font-size: 0.85rem;
            color: #004d40;
        }}
        .runner-controls input[type="date"] {{
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            border: 1px solid #b2dfdb;
            font-size: 0.85rem;
        }}
        .logs {{
            background: #f5f5f5;
            border-radius: 6px;
            padding: 0.75rem;
            max-height: 260px;
            overflow-y: auto;
            font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 0.8rem;
            white-space: pre-wrap;
            line-height: 1.4;
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
            color: #26a69a;
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
            color: #26a69a;
            text-decoration: none;
            font-weight: 500;
        }}
        .link:hover {{
            text-decoration: underline;
        }}
        .link-empty {{
            color: #999;
            cursor: default;
        }}
        .link-empty:hover {{
            text-decoration: none;
        }}
        .empty {{
            text-align: center;
            padding: 3rem;
            color: #999;
        }}
        .loading {{
            text-align: center;
            padding: 2rem;
            color: #26a69a;
        }}
        .error {{
            background: #fee;
            color: #c33;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>☁️ 云端轻量报告搜索</h1>
        <p class="subtitle">只展示 PlanToDeploy/output/cloud_* 生成的报告</p>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="输入股票代码或名称（如：600519 或 茅台）" />
            <button class="btn btn-primary" onclick="searchStock()">🔍 搜索</button>
        </div>
        
        <div class="actions">
            <button class="btn btn-secondary" onclick="showHotStocks()">🔥 热门股票</button>
            <button class="btn btn-secondary" onclick="showStats()">📈 统计信息</button>
            <button class="btn btn-secondary" onclick="showReportIndex()">📋 报告列表</button>
        </div>

        <div class="runner-panel">
            <div class="runner-header">
                <div>
                    <strong>云端 Runner 状态</strong>
                    <div id="runnerStatus" class="runner-status-text">状态: 未知</div>
                </div>
                <div>
                    <button class="btn btn-secondary" onclick="triggerRunDaily()">🚀 手动运行云端 Runner</button>
                    <button class="btn btn-secondary" style="margin-left: 0.5rem;" onclick="stopRunDaily()">⏹ 停止当前任务</button>
                </div>
            </div>
            <div class="runner-controls">
                <label>
                    <input type="checkbox" id="runnerTestMode" />
                    使用 test 模式(小样本股票池)
                </label>
                <label>
                    截止日期:
                    <input type="date" id="runnerEndDate" />
                </label>
                <label>
                    运行模式:
                    <select id="runnerMode">
                        <option value="all">全部脚本(云端轻量)</option>
                        <option value="daily">仅 TD 九底(日常)</option>
                        <option value="xuanxue">仅 玄学(云端)</option>
                        <option value="new">仅 新指标(云端)</option>
                    </select>
                </label>
            </div>
            <div id="runnerLogs" class="logs">日志尚未加载</div>
        </div>
        
        <div id="results" class="results"></div>
    </div>

    <script>
        // 与当前页面同源的 API 地址
        const API_BASE = '';
        let logCursor = 0;
        let logTimer = null;
        
        document.getElementById('searchInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                searchStock();
            }}
        }});

        async function searchStock() {{
            const keyword = document.getElementById('searchInput').value.trim();
            if (!keyword) {{
                alert('请输入股票代码或名称');
                return;
            }}
            showLoading();
            try {{
                const isCode = /^\\d+$/.test(keyword);
                const param = isCode ? `code=${{keyword}}` : `name=${{keyword}}`;
                const response = await fetch(`${{API_BASE}}/api/search?${{param}}`);
                const data = await response.json();
                if (data.error) {{
                    showError(data.error);
                    return;
                }}
                // 这里不对模块做过滤, 仍展示 stocks_index 中所有记录, 方便对比
                displayResults(data.results, `搜索结果：${{keyword}}`);
            }} catch (error) {{
                showError('搜索失败，请检查 API 服务是否已启动');
            }}
        }}

        async function showHotStocks() {{
            showLoading();
            try {{
                const response = await fetch(`${{API_BASE}}/api/hot-stocks`);
                const data = await response.json();
                if (data.error) {{
                    showError(data.error);
                    return;
                }}
                displayHotStocks(data.hot_stocks);
            }} catch (error) {{
                showError('获取热门股票失败，请检查 API 服务是否已启动');
            }}
        }}

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
                showError('获取统计信息失败，请检查 API 服务是否已启动');
            }}
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
                        <td><a href="/reports/${{String(item.报告路径 || '').replace(/^\\.?\\//, '')}}" target="_blank" class="link">查看报告</a></td>
                    </tr>
                `;
            }});
            
            html += '</tbody></table>';
            document.getElementById('results').innerHTML = html;
        }}

        // 显示热门股票
        function displayHotStocks(data) {{
            if (!data || data.length === 0) {{
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
            if (data.modules) {{
                for (const [module, count] of Object.entries(data.modules)) {{
                    modulesHtml += `
                        <div class="stat-card">
                            <div class="stat-value">${{count}}</div>
                            <div class="stat-label">${{module}}</div>
                        </div>
                    `;
                }}
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

        function updateRunnerStatus(status) {{
            const el = document.getElementById('runnerStatus');
            if (!el) return;
            const running = status.running;
            const state = status.status || 'unknown';
            const start = status.start_time || '-';
            const end = status.end_time || '-';
            const test = status.test ? 'test' : 'normal';
            const mode = status.mode || 'all';
            const dateInfo = status.end_date ? (' | 截止日期: ' + status.end_date) : '';
            el.textContent =
                '状态: ' + (running ? '运行中' : state) +
                ' | 模式: ' + test +
                ' | 运行: ' + mode +
                dateInfo +
                ' | 开始: ' + start +
                ' | 结束: ' + end;
        }}

        async function refreshRunnerStatus() {{
            try {{
                const resp = await fetch(`${{API_BASE}}/api/run-status`);
                const data = await resp.json();
                updateRunnerStatus(data);
                if (data.running && !logTimer) {{
                    startLogPolling();
                }}
            }} catch (error) {{
                // 忽略状态刷新错误
            }}
        }}

        function appendLogs(lines) {{
            const el = document.getElementById('runnerLogs');
            if (!el) return;
            if (!lines.length && logCursor === 0) {{
                el.textContent = '暂无日志';
                return;
            }}
            const text = lines.join('\\n');
            el.textContent = (logCursor === 0 ? '' : el.textContent + '\\n') + text;
            el.scrollTop = el.scrollHeight;
        }}

        async function fetchLogs() {{
            try {{
                const resp = await fetch(`${{API_BASE}}/api/run-logs?from=${{logCursor}}`);
                const data = await resp.json();
                appendLogs(data.lines || []);
                logCursor = data.next || logCursor;
                if (!data.running && logTimer) {{
                    clearInterval(logTimer);
                    logTimer = null;
                }}
            }} catch (error) {{
                // 日志拉取错误可以忽略
            }}
        }}

        function startLogPolling() {{
            if (logTimer) return;
            fetchLogs();
            logTimer = setInterval(fetchLogs, 3000);
        }}

        async function triggerRunDaily() {{
            if (!confirm('确认手动运行云端 Runner 吗？该操作可能耗时数分钟。')) {{
                return;
            }}
            const testMode = document.getElementById('runnerTestMode').checked;
            const endDateInput = document.getElementById('runnerEndDate').value.trim();
            const modeSelect = document.getElementById('runnerMode');
            const payload = {{}};
            if (endDateInput) {{
                payload.end_date = endDateInput;
            }}
            if (testMode) {{
                payload.test = true;
            }}
            if (modeSelect && modeSelect.value) {{
                payload.mode = modeSelect.value;
            }}
            try {{
                const resp = await fetch(`${{API_BASE}}/api/run-daily`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload),
                }});
                const data = await resp.json();
                if (!resp.ok) {{
                    alert(data.error || data.message || '启动失败');
                    return;
                }}
                logCursor = 0;
                document.getElementById('runnerLogs').textContent = '任务已启动，正在获取日志...';
                startLogPolling();
                refreshRunnerStatus();
            }} catch (error) {{
                alert('启动云端 Runner 失败，请检查服务是否已启动');
            }}
        }}

        function showReportIndex() {{
            const resultsDiv = document.getElementById('results');
            const tableHtml = `
                <div class="result-header">
                    <h2>📋 云端轻量报告列表</h2>
                    <span class="result-count">只显示云端模块</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>日期</th>
                            {''.join(f'<th>{name}</th>' for name in module_names)}
                        </tr>
                    </thead>
                    <tbody>
                        {table_body}
                    </tbody>
                </table>
            `;
            resultsDiv.innerHTML = tableHtml;
        }}

        function showLoading() {{
            document.getElementById('results').innerHTML = '<div class="loading">⏳ 加载中...</div>';
        }}

        function showError(message) {{
            document.getElementById('results').innerHTML = `<div class="error">❌ ${{message}}</div>`;
        }}

        async function stopRunDaily() {{
            if (!confirm('确认要停止当前运行中的云端 Runner 吗？')) {{
                return;
            }}
            try {{
                const resp = await fetch(`${{API_BASE}}/api/run-stop`, {{
                    method: 'POST'
                }});
                const data = await resp.json().catch(() => ({{}}));
                if (!resp.ok) {{
                    alert(data.error || data.message || '停止失败');
                    return;
                }}
                if (logTimer) {{
                    clearInterval(logTimer);
                    logTimer = null;
                }}
                logCursor = 0;
                document.getElementById('runnerLogs').textContent = '任务已停止';
                refreshRunnerStatus();
            }} catch (error) {{
                alert('停止失败，请确保 API 服务已启动');
            }}
        }}

        // 页面加载时刷新一次 Runner 状态
        refreshRunnerStatus();
    </script>
</body>
</html>
"""
    return html


def build_index_html(project: Path, per_module: dict[str, dict[str, Path]], dates: list[str]) -> str:
    """生成带搜索功能的索引页 HTML 内容（reports_index.html），仅负责搜索/统计/报告列表。"""
    module_names = [name for name, _ in CONFIG]

    table_rows: list[str] = []
    for date_str in dates:
        cells = [f"<td>{date_str}</td>"]
        for name in module_names:
            data = per_module.get(name, {})
            path = data.get(date_str)
            if path:
                full_path = (project / path).resolve()
                href = full_path.as_uri()
                cells.append(
                    f'<td><a href="{href}" target="_blank" class="link">查看</a></td>'
                )
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
        // 与当前页面同源的 API 地址
        const API_BASE = '';
        const PROJECT_ROOT = '{project.as_uri()}';

        function resolveReportHref(path) {{
            if (!path) return '#';
            if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('file://')) {{
                return path;
            }}
            try {{
                const base = PROJECT_ROOT.endsWith('/') ? PROJECT_ROOT : PROJECT_ROOT + '/';
                const clean = path.replace(/^\\.?\\//, '');
                return new URL(clean, base).href;
            }} catch (e) {{
                return path;
            }}
        }}

        document.getElementById('searchInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                searchStock();
            }}
        }});

        async function searchStock() {{
            const keyword = document.getElementById('searchInput').value.trim();
            if (!keyword) {{
                alert('请输入股票代码或名称');
                return;
            }}

            showLoading();

            try {{
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

        function displayResults(results, title) {{
            if (!results || results.length === 0) {{
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
                        <td><a href="${{resolveReportHref(item.报告路径)}}" target="_blank" class="link">查看报告</a></td>
                    </tr>
                `;
            }});

            html += '</tbody></table>';
            document.getElementById('results').innerHTML = html;
        }}

        function displayHotStocks(data) {{
            if (!data || data.length === 0) {{
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

        function displayStats(data) {{
            let modulesHtml = '';
            if (data.modules) {{
                for (const [module, count] of Object.entries(data.modules)) {{
                    modulesHtml += `
                        <div class="stat-card">
                            <div class="stat-value">${{count}}</div>
                            <div class="stat-label">${{module}}</div>
                        </div>
                    `;
                }}
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

        function searchByCode(code) {{
            document.getElementById('searchInput').value = code;
            searchStock();
        }}

        function showLoading() {{
            document.getElementById('results').innerHTML = '<div class="loading">⏳ 加载中...</div>';
        }}

        function showError(message) {{
            document.getElementById('results').innerHTML = `<div class="error">❌ ${{message}}</div>`;
        }}

        window.onload = function() {{
            showReportIndex();
        }};
    </script>
</body>
</html>
"""
    return html


def get_latest_stocks_index_date(project: Path) -> str | None:
    """获取最新的 stocks_index.csv 日期(云端: 使用 PlanToDeploy/stocks_index)"""
    stocks_index_dir = project / "stocks_index"
    if not stocks_index_dir.exists():
        return None
    
    date_dirs = [d for d in stocks_index_dir.iterdir() if d.is_dir() and DATE_PATTERN.match(d.name)]
    if not date_dirs:
        return None
    
    # 返回最新日期
    latest_date = sorted(date_dirs, key=lambda d: d.name, reverse=True)[0].name
    return latest_date


def get_all_stocks_index_dates(project: Path) -> list[str]:
    """获取 stocks_index 目录下所有日期(YYYY-MM-DD), 按降序排序."""
    stocks_index_dir = project / "stocks_index"
    if not stocks_index_dir.exists():
        return []
    date_names: list[str] = []
    for d in stocks_index_dir.iterdir():
        if d.is_dir() and DATE_PATTERN.match(d.name):
            date_names.append(d.name)
    return sorted(date_names, reverse=True)


def main(target_date: str | None = None) -> None:
    project = project_root()
    per_module = {}
    for module_name, output_rel in CONFIG:
        per_module[module_name] = scan_module(project, module_name, output_rel)
    dates = collect_all_dates(per_module)
    # 云端统一入口: 需要展示“运行过但无信号”的日期, 依据 stocks_index 目录补齐
    index_dates = get_all_stocks_index_dates(project)
    cloud_dates = sorted(set(dates) | set(index_dates), reverse=True)
    
    # 获取 stocks_index.csv 目标日期：
    # - 如显式传入 target_date，则优先使用该日期
    # - 否则使用最新日期目录
    latest_date = target_date or get_latest_stocks_index_date(project)
    if latest_date:
        print(f"使用最新日期的 stocks_index.csv: {latest_date}")
        # 创建带日期的输出目录
        output_dir = project / "report_index" / f"reports_index_{latest_date}"
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        print("未找到 stocks_index 日期目录，使用项目根目录")
        output_dir = project
    
    # 生成 reports_list.html（简单列表）——同时更新根目录与按日期的子目录
    list_html = build_list_html(project, per_module, dates)
    list_path = output_dir / "reports_list.html"
    list_path.write_text(list_html, encoding="utf-8")
    print(f"已生成: {list_path}")

    # 生成 reports_index.html（带搜索功能, 全模块）——仅在按日期的子目录下生成
    index_html = build_index_html(project, per_module, dates)
    index_path = output_dir / "reports_index.html"
    index_path.write_text(index_html, encoding="utf-8")
    print(f"已生成: {index_path}")
    
    # 生成 cloud_reports_index.html（仅云端模块视图, 放入当前项目的 cloud_index/ 下）
    cloud_html = build_cloud_index_html(project, per_module, cloud_dates)
    plan_root = project / "cloud_index"
    plan_root.mkdir(parents=True, exist_ok=True)

    # 1) 按日期生成一次（保留历史文件）
    if latest_date:
        cloud_index_path = plan_root / f"cloud_reports_index_{latest_date}.html"
        cloud_index_path.write_text(cloud_html, encoding="utf-8")
        print(f"已生成云端索引: {cloud_index_path}")

    # 2) 始终同步一份统一入口文件，覆盖更新
    cloud_index_latest_path = plan_root / "cloud_reports_index.html"
    cloud_index_latest_path.write_text(cloud_html, encoding="utf-8")
    print(f"已更新云端统一入口: {cloud_index_latest_path}")
    
    print(f"共 {len(dates)} 个日期, {sum(len(d) for d in per_module.values())} 条报告链接。")
    print(f"注意: reports_index.html 包含搜索功能，reports_list.html 是简单列表(均位于 report_index/* 子目录)")
    
    # 自动打开 HTML 文件（主索引），可通过环境变量 NO_BROWSER=1 禁用
    no_browser = os.environ.get("NO_BROWSER", "").lower() in {"1", "true", "yes", "y"}
    if no_browser:
        print("\nNO_BROWSER=1, 跳过自动打开浏览器。")
        print(f"请手动打开: {index_path}")
    else:
        print(f"\n正在打开浏览器...")
        try:
            webbrowser.open(index_path.as_uri())
            print(f"✓ 已在浏览器中打开: {index_path}")
        except Exception as e:
            print(f"⚠ 无法自动打开浏览器: {e}")
            print(f"请手动打开: {index_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="生成/更新选股报告索引（支持指定 stocks_index 日期）"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="指定 stocks_index 日期 (YYYY-MM-DD)，覆盖自动选择的最新日期",
    )
    args = parser.parse_args()
    main(args.date)
