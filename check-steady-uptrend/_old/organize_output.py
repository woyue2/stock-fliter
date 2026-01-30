#!/usr/bin/env python3
"""
整理output文件夹，按日期和时间归类文件
"""
import os
import re
import shutil
from pathlib import Path
from collections import defaultdict

def extract_datetime(filename):
    """从文件名提取生成日期和时间戳（忽略baseon数据时间）"""
    # 先移除 baseon 部分，避免误识别数据时间
    # 例如：baseon_01282026 是数据时间，不是生成时间
    filename_cleaned = re.sub(r'baseon_\d{8}_', '', filename)
    
    # 匹配格式：20260128_051251 或 20260128
    pattern = r'(\d{8})(?:_(\d{6}))?'
    matches = re.findall(pattern, filename_cleaned)
    
    if not matches:
        return None, None
    
    # 取最后一个匹配（文件名末尾的是生成时间）
    date_str, time_str = matches[-1]
    
    # 如果没有时间部分，使用000000
    if not time_str:
        time_str = "000000"
    
    return date_str, time_str

def format_date(date_str):
    """格式化日期字符串 20260128 -> 2026-01-28"""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str

def format_time(time_str):
    """格式化时间字符串 051251 -> 05-12-51"""
    if len(time_str) == 6:
        return f"{time_str[:2]}-{time_str[2:4]}-{time_str[4:]}"
    return time_str

def organize_files():
    """组织文件到日期/时间文件夹"""
    output_dir = Path(__file__).parent / "output"
    
    # 扫描所有文件
    files_by_datetime = defaultdict(list)
    other_files = []
    
    for item in output_dir.iterdir():
        if item.is_file() and item.name != ".gitignore":
            date_str, time_str = extract_datetime(item.name)
            if date_str:
                files_by_datetime[(date_str, time_str)].append(item)
            else:
                other_files.append(item)
    
    if not files_by_datetime:
        print("没有找到需要整理的文件")
        return
    
    # 按日期分组
    files_by_date = defaultdict(lambda: defaultdict(list))
    for (date_str, time_str), files in files_by_datetime.items():
        files_by_date[date_str][time_str].extend(files)
    
    # 创建文件夹结构并移动文件
    moved_count = 0
    
    for date_str in sorted(files_by_date.keys()):
        date_folder = output_dir / format_date(date_str)
        date_folder.mkdir(exist_ok=True)
        
        times = files_by_date[date_str]
        
        for time_str in sorted(times.keys()):
            time_folder = date_folder / format_time(time_str)
            time_folder.mkdir(exist_ok=True)
            
            files = times[time_str]
            
            print(f"\n[DIR] {format_date(date_str)} / {format_time(time_str)} ({len(files)} 文件)")
            
            for file_path in files:
                try:
                    target = time_folder / file_path.name
                    shutil.move(str(file_path), str(target))
                    moved_count += 1
                    print(f"  ✓ {file_path.name}")
                except Exception as e:
                    print(f"  ✗ 移动失败: {file_path.name} - {e}")
    
    # 报告其他文件
    if other_files:
        print(f"\n⚠️  未归类文件 ({len(other_files)}):")
        for f in other_files:
            print(f"  - {f.name}")
    
    print(f"\n[OK] 整理完成! 共移动 {moved_count} 个文件")
    print(f"📂 组织结构: output/{format_date('YYYYMMDD')}/{format_time('HHMMSS')}/")

if __name__ == "__main__":
    organize_files()
