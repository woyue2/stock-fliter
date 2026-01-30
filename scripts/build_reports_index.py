# -*- coding: utf-8 -*-
"""
生成选股报告索引页 reports_index.html。

扫描 check-steady-uptrend/output 与 check-trend-bottom/output，
按日期聚合，同一日期只链接该日最新时间戳下的 summary 报告。
索引页生成在项目根目录，链接为相对路径，便于本地双击打开使用。
"""

import re
from pathlib import Path


# 模块显示名 -> output 相对路径（相对项目根）
CONFIG = [
    ("稳步上升", "check-steady-uptrend/output"),
    ("TD九底", "check-trend-bottom/output"),
    # ("新指标", "check-new-indicators/output"),  # 新增
]

# 日期目录 YYYY-MM-DD
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 时间目录 HH-MM-SS
TIME_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{2}$")


def project_root() -> Path:
    """项目根目录（scripts 的上一级）。"""
    return Path(__file__).resolve().parent.parent


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
    返回: 日期字符串 -> 该日期下最新 summary 的路径（相对 project）。
    """
    result = {}
    output_root = project / output_rel
    if not output_root.is_dir():
        return result
    for candidate in output_root.iterdir():
        if not candidate.is_dir() or not DATE_PATTERN.match(candidate.name):
            continue
        date_str = candidate.name
        summary_path = find_latest_summary_for_date(output_root, date_str)
        if summary_path is None:
            continue
        try:
            rel = summary_path.relative_to(project)
            result[date_str] = rel
        except ValueError:
            continue
    return result


def collect_all_dates(per_module: dict[str, dict[str, Path]]) -> list[str]:
    """汇总所有出现过的日期，降序排列。"""
    dates = set()
    for data in per_module.values():
        dates.update(data.keys())
    return sorted(dates, reverse=True)


def build_index_html(project: Path, per_module: dict[str, dict[str, Path]], dates: list[str]) -> str:
    """生成索引页 HTML 内容。"""
    module_names = [name for name, _ in CONFIG]
    rows = []
    for date_str in dates:
        cells = [f"<td>{date_str}</td>"]
        for name in module_names:
            data = per_module.get(name, {})
            path = data.get(date_str)
            if path:
                # 相对路径，用正斜杠便于在浏览器中打开
                href = path.as_posix()
                cells.append(f'<td><a href="{href}">查看</a></td>')
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


def main() -> None:
    project = project_root()
    per_module = {}
    for module_name, output_rel in CONFIG:
        per_module[module_name] = scan_module(project, module_name, output_rel)
    dates = collect_all_dates(per_module)
    html = build_index_html(project, per_module, dates)
    out_path = project / "reports_index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"已生成: {out_path}")
    print(f"共 {len(dates)} 个日期, {sum(len(d) for d in per_module.values())} 条报告链接。")


if __name__ == "__main__":
    main()
