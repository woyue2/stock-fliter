"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

INPUT: 命令行参数 args
OUTPUT: 启动 pipeline 并进行整体调度
"""
import argparse
import sys
import os

# 将根目录假如 PYTHONPATH 供模块调用 util 等
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="主力强度与散户背离(A*B*C)分析模块")
    parser.add_argument("--test", action="store_true", help="测试模式 (使用样本文件或少量存量数据)")
    
    args = parser.parse_args()
    
    print("⚓【GEB 协议已内置】启动主力资金博弈分析 (A*B*C)...")
    run_pipeline(args)

if __name__ == "__main__":
    main()
