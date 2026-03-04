import pandas as pd
from pathlib import Path
import glob
import os
import sys
from datetime import datetime

# Force UTF-8 output for Windows to support emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        # Use 'replace' error handler to avoid UnicodeEncodeError on Windows GBK terminals
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

def find_latest_file(directory, pattern):
    files = list(Path(directory).rglob(pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def clean_code(code):
    if isinstance(code, str):
        if "." in code:
            return code.split(".")[1]
    return str(code)

def main():
    root_dir = Path(__file__).parent.absolute()
    
    # 1. Check Steady Uptrend Output
    steady_dir = root_dir / "check-steady-uptrend" / "output"
    steady_file = find_latest_file(steady_dir, "steady_uptrend_*.csv")
    
    # 2. Check Trend Bottom Output
    trend_dir = root_dir / "check-trend-bottom" / "output"
    trend_file = find_latest_file(trend_dir, "td_analysis_*.csv")
    
    print("="*60)
    print("🔍 模块结果对比工具")
    print("="*60)
    
    if not steady_file:
        print("❌ 未找到 check-steady-uptrend 的结果文件。")
        print("请先运行: python check-steady-uptrend/main.py")
    else:
        print(f"✅ Steady Uptrend: {steady_file.name}")
        
    if not trend_file:
        print("❌ 未找到 check-trend-bottom 的结果文件。")
        print("请先运行: python check-trend-bottom/main.py")
    else:
        print(f"✅ Trend Bottom:   {trend_file.name}")
        
    if not steady_file or not trend_file:
        return

    # Load Data
    try:
        df_steady = pd.read_csv(steady_file)
        df_trend = pd.read_csv(trend_file)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return

    # Clean Codes
    steady_col = "code" if "code" in df_steady.columns else "代码"
    trend_col = "代码" if "代码" in df_trend.columns else "code"
    
    if steady_col not in df_steady.columns or trend_col not in df_trend.columns:
        print("❌ 无法找到代码列")
        return

    df_steady["clean_code"] = df_steady[steady_col].apply(clean_code)
    df_trend["clean_code"] = df_trend[trend_col].apply(clean_code)
    
    # Intersect
    steady_codes = set(df_steady["clean_code"])
    trend_codes = set(df_trend["clean_code"])
    
    common_codes = steady_codes & trend_codes
    
    print(f"\n📊 统计结果:")
    print(f"  - 稳步上升股票数: {len(steady_codes)}")
    print(f"  - TD九底股票数:   {len(trend_codes)}")
    print(f"  - 重合股票数:     {len(common_codes)}")
    
    if not common_codes:
        print("\n⚠️ 没有发现重合的股票。")
        return

    # Merge Data for Report
    common_list = sorted(list(common_codes))
    
    report_data = []
    for code in common_list:
        row_steady = df_steady[df_steady["clean_code"] == code].iloc[0]
        row_trend = df_trend[df_trend["clean_code"] == code].iloc[0]
        
        item = {
            "代码": code,
            "名称": row_trend.get("名称", row_steady.get("name", "未知")),
            "最新价": row_trend.get("日最新价", row_steady.get("latest_close", 0)),
            "稳步上升": "是",
            "TD情况": row_trend.get("底部详情", "未知"),
            "共振级别": row_trend.get("共振级别", "0"),
        }
        report_data.append(item)
        
    df_report = pd.DataFrame(report_data)
    
    # Output
    output_dir = root_dir / "comparison_results"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Markdown
    md_path = output_dir / f"overlap_report_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 股票筛选重合报告\n\n")
        f.write(f"- 生成时间: {datetime.now()}\n")
        f.write(f"- 来源1: {steady_file.name}\n")
        f.write(f"- 来源2: {trend_file.name}\n\n")
        f.write(f"## 重合股票列表 ({len(df_report)}只)\n\n")
        f.write(df_report.to_markdown(index=False))
        
    print(f"\n📄 报告已生成: {md_path}")
    
    # HTML (Optional)
    html_path = output_dir / f"overlap_report_{timestamp}.html"
    try:
        html_content = df_report.to_html(index=False, classes="table table-striped", border=0)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(f"""
<html>
<head>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ text-align: left; padding: 8px; }}
tr:nth-child(even) {{ background-color: #f2f2f2; }}
th {{ background-color: #4CAF50; color: white; }}
</style>
</head>
<body>
<h1>股票筛选重合报告</h1>
<p>生成时间: {datetime.now()}</p>
{html_content}
</body>
</html>
""")
        print(f"📄 HTML报告:   {html_path}")
    except Exception as e:
        print(f"HTML生成失败: {e}")

if __name__ == "__main__":
    main()
