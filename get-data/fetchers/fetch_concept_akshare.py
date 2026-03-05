# -*- coding: utf-8 -*-
"""
[L3] fetch_concept_akshare.py
[ROLE]: 统一入口 - 调用更稳定的新浪财经接口抓取股票概念
[INPUT]: N/A (calls fetchers.fetch_concept_sina)
[OUTPUT]: selected_stocks_all.csv
[PROTOCOL]: 变更时更新此头部，然后检查 L2/CLAUDE.md
"""
import os
from pathlib import Path
import sys

# 添加当前目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent
# 让它能导入同级目录下的模块
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent))

try:
    from fetch_concept_sina import update_csv
    print("[INFO] 切换至新浪数据源...")
except ImportError:
    print("[ERROR] 找不到 fetch_concept_sina.py")
    sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("股票概念信息获取工具 (稳定版)")
    print("=" * 60)
    update_csv()
