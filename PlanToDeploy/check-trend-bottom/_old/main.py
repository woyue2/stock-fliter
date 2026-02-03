# -*- coding: utf-8 -*-
"""
股票筛选主流程

自动执行完整流程：
1. 获取股票数据 (fetch_data.py --all)
2. 分析TD九底模式 (analyze_data.py)
3. 生成统计报告 (stats.py)

用法：
  python main.py              # 执行完整流程
  python main.py --skip-fetch # 跳过数据获取，仅分析和统计
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(command: list, description: str) -> bool:
    """
    执行命令并实时输出结果
    
    Args:
        command: 要执行的命令列表
        description: 命令描述
        
    Returns:
        bool: 命令是否成功执行
    """
    print(f"\n{'='*70}")
    print(f"  {description}")
    print('='*70)
    
    try:
        # 实时输出命令执行结果
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 实时读取输出
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        
        if process.returncode == 0:
            print(f"\n✅ {description} 完成")
            return True
        else:
            print(f"\n❌ {description} 失败 (退出码: {process.returncode})")
            return False
            
    except Exception as e:
        print(f"\n❌ 执行命令时出错: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="股票筛选完整流程")
    parser.add_argument("--skip-fetch", action="store_true", help="跳过数据获取步骤")
    parser.add_argument("--sample", action="store_true", help="使用样本模式获取数据（仅10只股票）")
    args = parser.parse_args()
    
    start_time = datetime.now()
    print(f"\n🚀 开始执行股票筛选流程")
    print(f"⏰ 启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 确认工作目录
    script_dir = Path(__file__).resolve().parent
    print(f"📁 工作目录: {script_dir}")
    
    # 步骤1: 获取数据
    if not args.skip_fetch:
        fetch_cmd = [sys.executable, "fetch_data.py"]
        if not args.sample:
            fetch_cmd.append("--all")
        
        if not run_command(fetch_cmd, "步骤 1/3: 获取股票数据"):
            print("\n⚠️  数据获取失败，是否继续分析现有数据？")
            choice = input("输入 y 继续，其他键退出: ")
            if choice.lower() != 'y':
                return 1
    else:
        print(f"\n{'='*70}")
        print("  ⏭️  跳过数据获取步骤")
        print('='*70)
    
    # 步骤2: 分析数据
    if not run_command([sys.executable, "analyze_data.py"], "步骤 2/3: 分析TD九底模式"):
        print("\n❌ 分析失败，流程中止")
        return 1
    
    # 步骤3: 生成统计报告
    if not run_command([sys.executable, "stats.py"], "步骤 3/3: 生成统计报告"):
        print("\n⚠️  统计报告生成失败")
        return 1
    
    # 完成
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n{'='*70}")
    print("  ✨ 全部流程执行完成！")
    print('='*70)
    print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏰ 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  总耗时: {duration}")
    print(f"\n📊 统计报告已保存到 output/ 目录")
    print(f"💡 提示: 可使用 python main.py --skip-fetch 跳过数据获取步骤")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
