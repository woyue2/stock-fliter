import os
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class HTMLReporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def generate(self, df: pd.DataFrame) -> str:
        if df.empty:
            logger.warning("DataFrame is empty. Skip HTML generating.")
            return ""
            
        # 获取数据日期（取第一行）
        data_date_str = ""
        if 'date' in df.columns:
            # 确保转换日期对象为字符串
            dt_val = df['date'].iloc[0]
            if isinstance(dt_val, str):
                data_date_str = dt_val.replace('-', '')
            else:
                data_date_str = dt_val.strftime("%Y%m%d")
        else:
            data_date_str = datetime.now().strftime("%Y%m%d")
            
        time_str = datetime.now().strftime("%H%M%S")
        filename = f"summary_{data_date_str}_{time_str}.html"
        report_path = os.path.join(self.output_dir, filename)
        
        # 整理列 (板块分析版)
        cols_to_show = ["板块", "涨幅", "成交额", "主力净额", "散户净额", "主力强度", "主力行为", "资金效率", "预期"]
        df_show = df[cols_to_show].copy()
        
        # 转换预期颜色
        def get_expectation_style(val):
            if val == "上涨": return "background: #e6fffa; color: #2c7a7b; font-weight: bold;"
            if val == "下跌": return "background: #fff5f5; color: #c53030; font-weight: bold;"
            if val == "冲高回落": return "background: #fffaf0; color: #9c4221;"
            return ""

        rows_html = ""
        for _, row in df_show.iterrows():
            style = get_expectation_style(row["预期"])
            pctchg_val = row['涨幅']
            color = 'red' if pctchg_val > 0 else 'green' if pctchg_val < 0 else 'black'

            rows_html += "<tr>"
            rows_html += f"<td><strong>{row['板块']}</strong></td>"
            rows_html += f"<td style='color: {color}'>{pctchg_val:.2f}%</td>"
            rows_html += f"<td>{row['成交额']/100000000:.2f}亿</td>"
            rows_html += f"<td>{row['主力净额']/100000000:.2f}亿</td>"
            rows_html += f"<td>{row['散户净额']/100000000:.2f}亿</td>"
            rows_html += f"<td>{row['主力强度']:.2f}</td>"
            rows_html += f"<td>{row['主力行为']}</td>"
            rows_html += f"<td>{row['资金效率']:.2f}</td>"
            rows_html += f"<td style='{style}'>{row['预期']}</td>"
            rows_html += "</tr>"

        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>权重资金博弈分析(板块) - A*B*C Model</title>
    <style>
        body {{ font-family: -apple-system, system-ui, sans-serif; background: #f4f7f6; color: #2d3748; padding: 20px; }}
        .card {{ background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); padding: 30px; max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #1a202c; font-size: 26px; margin-bottom: 8px; display: flex; align-items: center; }}
        h1::before {{ content: ''; display: inline-block; width: 6px; height: 1em; background: #4a5568; margin-right: 12px; border-radius: 3px; }}
        .meta {{ font-size: 14px; color: #718096; margin-bottom: 24px; padding-left: 18px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
        th {{ background: #f8fafc; color: #4a5568; font-weight: 600; text-align: left; padding: 14px 12px; border-bottom: 2px solid #e2e8f0; }}
        td {{ padding: 14px 12px; border-bottom: 1px solid #edf2f7; }}
        tr:hover {{ background: #f9fafb; }}
        .note {{ background: #ebf8ff; border-left: 4px solid #3182ce; padding: 15px; margin-bottom: 25px; border-radius: 4px; font-size: 14px; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>📊 全行业资金博弈分析 (A*B*C 板块版)</h1>
        <p class="meta">数据日期: {df['date'].max() if 'date' in df.columns else 'Unknown'} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="note">
            <strong>核心逻辑 (A*B*C Model):</strong><br>
            • <strong>A (主力强度)</strong>: 行业主力净额占总成交比 | <strong>B (散户行为)</strong>: 判断散户流向是否与主力背离 (背离越深，真实度越高)<br>
            • <strong>C1 (资金效率)</strong>: 单位主力强度换取的行业涨幅 | <strong>C2 (成交容量)</strong>: 判定是否具备承载巨量资金的盘面
        </div>

        <table>
            <thead>
                <tr>
                    <th>板块(行业)</th>
                    <th>平均涨幅</th>
                    <th>成交额</th>
                    <th>主力净额</th>
                    <th>散户净额</th>
                    <th>强度(A)</th>
                    <th>主力行为(B)</th>
                    <th>效率(C)</th>
                    <th>博弈预期</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        
        <div style="margin-top: 30px; font-size: 12px; color: #cbd5e0; text-align: center; letter-spacing: 1px;">
            &copy; 2026 ANTIGRAVITY QUANTITATIVE SYSTEM • SECTOR STRENGTH ANALYSIS
        </div>
    </div>
</body>
</html>
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_template)
            
        logger.info(f"HTML report generated: {filename}")
        return report_path
