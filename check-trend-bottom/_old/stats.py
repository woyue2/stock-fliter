# -*- coding: utf-8 -*-
"""
快速统计分析结果

用法：
  python stats.py                    # 使用最新的分析文件
  python stats.py --file xxx.csv     # 指定分析文件
  python stats.py --td 7             # 筛选日TD>=7的股票
"""
import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class Tee(object):
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()


def find_latest_analysis(output_dir: Path) -> Path:
    """查找最新的分析结果文件"""
    files = sorted(output_dir.glob("analysis_summary_*.csv"), reverse=True)
    if not files:
        raise FileNotFoundError("未找到分析结果文件，请先运行 python analyze_data.py")
    return files[0]


def get_display_width(text: str) -> int:
    """计算字符串的显示宽度（中文字符算2个宽度）"""
    width = 0
    for char in str(text):
        if ord(char) > 127:  # 中文字符
            width += 2
        else:
            width += 1
    return width


def pad_string(text: str, width: int) -> str:
    """填充字符串到指定显示宽度"""
    text = str(text)
    current_width = get_display_width(text)
    if current_width >= width:
        return text
    # 用空格填充
    return text + ' ' * (width - current_width)


def print_stats(df: pd.DataFrame, title: str = "统计结果"):
    """打印统计信息"""
    print(f"\n{'='*70}")
    print(f" {title} (共 {len(df)} 只)")
    print('='*70)
    
    # 交易板块分布
    if '交易板块' in df.columns:
        print("\n📊 交易板块分布:")
        print("| 交易板块   | 数量 | 占比   |")
        print("|-----------|------|--------|")
        board_counts = Counter(df['交易板块'])
        for board, count in board_counts.most_common():
            pct = count / len(df) * 100
            board_padded = pad_string(board, 10)
            print(f"| {board_padded} | {count:4d} | {pct:6.1f}% |")
    
    # 行业分布（前10）
    if '行业' in df.columns:
        print("\n📊 行业分布 (前10):")
        print("| 行业                             | 数量 | 占比   |")
        print("|----------------------------------|------|--------|")
        industry_counts = Counter(df['行业'])
        for industry, count in industry_counts.most_common(10):
            pct = count / len(df) * 100
            industry_padded = pad_string(industry, 32)
            print(f"| {industry_padded} | {count:4d} | {pct:6.1f}% |")
    
    # 共振级别分布
    if '共振级别' in df.columns:
        print("\n📊 共振级别分布:")
        print("| 共振级别   | 数量 | 占比   |")
        print("|-----------|------|--------|")
        level_counts = Counter(df['共振级别'])
        for level in ['三周期九底', '双周期九底', '单周期九底', '无九底']:
            count = level_counts.get(level, 0)
            pct = count / len(df) * 100 if len(df) > 0 else 0
            level_padded = pad_string(level, 10)
            print(f"| {level_padded} | {count:4d} | {pct:6.1f}% |")


def main():
    parser = argparse.ArgumentParser(description="快速统计分析结果")
    parser.add_argument("--file", type=str, help="指定分析文件路径")
    parser.add_argument("--td", type=int, default=0, help="筛选日TD >= 此值的股票")
    parser.add_argument("--list", action="store_true", help="列出符合条件的股票")
    args = parser.parse_args()
    
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.file:
        file_path = Path(args.file)
    else:
        file_path = find_latest_analysis(output_dir)
    
    # 准备保存的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"stats_report_{timestamp}.md"
    csv_td7_path = output_dir / f"stats_td7_{timestamp}.csv"
    csv_td9_path = output_dir / f"stats_td9_{timestamp}.csv"
    
    print(f"[*] 读取文件: {file_path.name}")
    print(f"[*] 统计报告将保存至: {output_path.name}")
    print(f"[*] CSV文件将保存至: {csv_td7_path.name} 和 {csv_td9_path.name}")
    
    # 使用 Tee 同时输出到终端和文件
    with open(output_path, 'w', encoding='utf-8') as f:
        original_stdout = sys.stdout
        sys.stdout = Tee(sys.stdout, f)
        try:
            df = pd.read_csv(file_path)
            
            # 记录基础信息
            print(f"# 股票筛选统计报告 ({timestamp})")
            print(f"\n- **分析源文件:** {file_path.name}")
            print(f"- **股票总数:** {len(df)}")
            
            # 全市场统计
            print_stats(df, "全市场统计")
            
            # 筛选TD >= 指定值
            if args.td > 0 and '日九底计数' in df.columns:
                filtered_df = df[df['日九底计数'] >= args.td]
                print_stats(filtered_df, f"日TD >= {args.td} 的股票")
                
                if args.list:
                    print(f"\n📋 日TD >= {args.td} 的股票列表:")
                    display_cols = ['股票代码', '股票名称', '交易板块', '行业', '日九底计数', '周九底计数', '月九底计数', '共振级别']
                    display_cols = [c for c in display_cols if c in filtered_df.columns]
                    # 按交易板块、行业排序
                    sort_cols = [c for c in ['交易板块', '行业'] if c in filtered_df.columns]
                    if sort_cols:
                        filtered_df = filtered_df.sort_values(by=sort_cols)
                    
                    # 定义列宽
                    col_widths = {
                        '股票代码': 8,
                        '股票名称': 8,
                        '交易板块': 8,
                        '行业': 32,
                        '日九底计数': 10,
                        '周九底计数': 10,
                        '月九底计数': 10,
                        '共振级别': 10
                    }
                    
                    # 输出表头
                    header_parts = []
                    separator_parts = []
                    for col in display_cols:
                        width = col_widths.get(col, 10)
                        header_parts.append(pad_string(col, width))
                        separator_parts.append('-' * width)
                    print("| " + " | ".join(header_parts) + " |")
                    print("|" + "|".join(separator_parts) + "|")
                    
                    # 输出数据行
                    for _, row in filtered_df.iterrows():
                        values = []
                        for col in display_cols:
                            width = col_widths.get(col, 10)
                            values.append(pad_string(str(row[col]), width))
                        print("| " + " | ".join(values) + " |")
            
            # 自动统计TD>=7和TD>=9
            if args.td == 0 and '日九底计数' in df.columns:
                td7_df = df[df['日九底计数'] >= 7]
                td9_df = df[df['日九底计数'] >= 9]
                
                # 用于跟踪是否生成了CSV
                csv_generated = []
                
                if len(td7_df) > 0:
                    print_stats(td7_df, "日TD >= 7 的股票")
                    
                    # 列出TD>=7的股票
                    print(f"\n📋 日TD >= 7 的股票列表:")
                    display_cols = ['股票代码', '股票名称', '交易板块', '行业', '日九底计数', '周九底计数', '月九底计数', '共振级别']
                    display_cols = [c for c in display_cols if c in td7_df.columns]
                    # 按交易板块、行业、TD计数倒序排序
                    sort_cols = []
                    ascending = []
                    for col in ['交易板块', '行业']:
                        if col in td7_df.columns:
                            sort_cols.append(col)
                            ascending.append(True)
                    for col in ['日九底计数', '周九底计数', '月九底计数']:
                        if col in td7_df.columns:
                            sort_cols.append(col)
                            ascending.append(False)  # 倒序
                    if sort_cols:
                        td7_df_sorted = td7_df.sort_values(by=sort_cols, ascending=ascending)
                    else:
                        td7_df_sorted = td7_df
                    
                    # 定义列宽
                    col_widths = {
                        '股票代码': 8,
                        '股票名称': 8,
                        '交易板块': 8,
                        '行业': 32,
                        '日九底计数': 10,
                        '周九底计数': 10,
                        '月九底计数': 10,
                        '共振级别': 10
                    }
                    
                    # 输出表头
                    header_parts = []
                    separator_parts = []
                    for col in display_cols:
                        width = col_widths.get(col, 10)
                        header_parts.append(pad_string(col, width))
                        separator_parts.append('-' * width)
                    print("| " + " | ".join(header_parts) + " |")
                    print("|" + "|".join(separator_parts) + "|")
                    
                    # 输出数据行
                    for _, row in td7_df_sorted.iterrows():
                        values = []
                        for col in display_cols:
                            width = col_widths.get(col, 10)
                            values.append(pad_string(str(row[col]), width))
                        print("| " + " | ".join(values) + " |")
                    
                    # 保存TD>=7股票到CSV
                    csv_cols = ['股票代码', '股票名称', '交易板块', '行业', '日九底计数', '周九底计数', '月九底计数', '共振级别']
                    csv_cols = [c for c in csv_cols if c in td7_df_sorted.columns]
                    td7_df_sorted[csv_cols].to_csv(csv_td7_path, index=False, encoding='utf-8-sig')
                    csv_generated.append(('TD>=7', csv_td7_path.name, len(td7_df)))
                    
                if len(td9_df) > 0:
                    print_stats(td9_df, "日TD >= 9 的股票")
                    
                    # 列出TD=9的股票
                    print(f"\n📋 日TD = 9 的股票列表:")
                    display_cols = ['股票代码', '股票名称', '交易板块', '行业', '日九底计数', '周九底计数', '月九底计数', '共振级别']
                    display_cols = [c for c in display_cols if c in td9_df.columns]
                    # 按交易板块、行业、TD计数倒序排序
                    sort_cols = []
                    ascending = []
                    for col in ['交易板块', '行业']:
                        if col in td9_df.columns:
                            sort_cols.append(col)
                            ascending.append(True)
                    for col in ['日九底计数', '周九底计数', '月九底计数']:
                        if col in td9_df.columns:
                            sort_cols.append(col)
                            ascending.append(False)  # 倒序
                    if sort_cols:
                        td9_df_sorted = td9_df.sort_values(by=sort_cols, ascending=ascending)
                    else:
                        td9_df_sorted = td9_df
                    
                    # 定义列宽
                    col_widths = {
                        '股票代码': 8,
                        '股票名称': 8,
                        '交易板块': 8,
                        '行业': 32,
                        '日九底计数': 10,
                        '周九底计数': 10,
                        '月九底计数': 10,
                        '共振级别': 10
                    }
                    
                    # 输出表头
                    header_parts = []
                    separator_parts = []
                    for col in display_cols:
                        width = col_widths.get(col, 10)
                        header_parts.append(pad_string(col, width))
                        separator_parts.append('-' * width)
                    print("| " + " | ".join(header_parts) + " |")
                    print("|" + "|".join(separator_parts) + "|")
                    
                    # 输出数据行
                    for _, row in td9_df_sorted.iterrows():
                        values = []
                        for col in display_cols:
                            width = col_widths.get(col, 10)
                            values.append(pad_string(str(row[col]), width))
                        print("| " + " | ".join(values) + " |")
                    
                    # 保存TD>=9股票到CSV
                    csv_cols = ['股票代码', '股票名称', '交易板块', '行业', '日九底计数', '周九底计数', '月九底计数', '共振级别']
                    csv_cols = [c for c in csv_cols if c in td9_df_sorted.columns]
                    td9_df_sorted[csv_cols].to_csv(csv_td9_path, index=False, encoding='utf-8-sig')
                    csv_generated.append(('TD>=9', csv_td9_path.name, len(td9_df)))
                
                # 输出CSV生成信息
                sys.stdout = original_stdout
                print(f"\n[OK] 统计完成")
                print(f"  - Markdown报告: {output_path.name}")
                for label, filename, count in csv_generated:
                    print(f"  - {label} CSV: {filename} ({count} 只)")
            else:
                # 如果不是自动模式，恢复stdout
                sys.stdout = original_stdout
                print(f"\n[OK] 统计完成")
                print(f"  - Markdown报告: {output_path.name}")
        except Exception as e:
            sys.stdout = original_stdout
            print(f"\n[Error] 统计过程中出错: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
