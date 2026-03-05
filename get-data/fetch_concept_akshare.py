# -*- coding: utf-8 -*-
"""
获取股票概念信息工具 - 统一入口
由于东方财富 (AkShare) 接口近日对数据中心等 IP 限制较严，
此脚本已改为调用更稳定的新浪财经接口进行抓取。
"""
import os
from pathlib import Path
import sys

# 添加当前目录到路径
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

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
