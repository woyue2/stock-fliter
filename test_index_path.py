# -*- coding: utf-8 -*-
"""
测试索引文件路径修改
验证各模块是否正确使用带日期的 stocks_index.csv
"""
from pathlib import Path
from datetime import datetime

def test_index_path():
    """测试索引文件路径"""
    project_root = Path(__file__).parent
    
    # 测试数据日期
    test_date = "20260130"
    date_folder = f"{test_date[:4]}-{test_date[4:6]}-{test_date[6:8]}"
    
    # 预期的索引文件路径
    expected_path = project_root / "get-data" / "data" / "stocks_index" / date_folder / "stocks_index.csv"
    
    print("=" * 60)
    print("测试索引文件路径修改")
    print("=" * 60)
    print(f"\n测试日期: {test_date}")
    print(f"日期文件夹: {date_folder}")
    print(f"\n预期路径: {expected_path}")
    print(f"路径存在: {expected_path.exists()}")
    
    if expected_path.exists():
        print(f"文件大小: {expected_path.stat().st_size} 字节")
        
        # 读取前几行
        with open(expected_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()[:5]
            print(f"\n文件内容预览 (前5行):")
            for i, line in enumerate(lines, 1):
                print(f"  {i}: {line.strip()}")
    
    # 检查 stocks_index 目录下的所有日期
    stocks_index_dir = project_root / "get-data" / "data" / "stocks_index"
    if stocks_index_dir.exists():
        date_dirs = sorted([d.name for d in stocks_index_dir.iterdir() if d.is_dir()])
        print(f"\n可用的日期目录:")
        for date_dir in date_dirs:
            csv_path = stocks_index_dir / date_dir / "stocks_index.csv"
            status = "[OK]" if csv_path.exists() else "[X]"
            print(f"  {status} {date_dir}")
        
        if date_dirs:
            latest_date = date_dirs[-1]
            print(f"\n最新日期: {latest_date}")
    
    print("\n" + "=" * 60)

def test_api_server():
    """测试 API 服务器的索引文件获取"""
    print("\n测试 API 服务器索引文件获取")
    print("=" * 60)
    
    # 模拟 api_server.py 的逻辑
    project_root = Path(__file__).parent
    stocks_index_dir = project_root / "get-data" / "data" / "stocks_index"
    
    if not stocks_index_dir.exists():
        print("stocks_index 目录不存在")
        return
    
    date_dirs = [d for d in stocks_index_dir.iterdir() if d.is_dir()]
    if not date_dirs:
        print("没有找到日期目录")
        return
    
    latest_date_dir = sorted(date_dirs, key=lambda d: d.name, reverse=True)[0]
    index_file = latest_date_dir / "stocks_index.csv"
    
    print(f"最新日期目录: {latest_date_dir.name}")
    print(f"索引文件路径: {index_file}")
    print(f"文件存在: {index_file.exists()}")
    
    if index_file.exists():
        import pandas as pd
        df = pd.read_csv(index_file, encoding='utf-8-sig')
        print(f"\n索引文件统计:")
        print(f"  总记录数: {len(df)}")
        print(f"  独立股票数: {df['代码'].nunique()}")
        print(f"  模块分布: {df['模块'].value_counts().to_dict()}")
    
    print("=" * 60)

def test_build_reports_index():
    """测试 build_reports_index.py 的输出路径"""
    print("\n测试 build_reports_index.py 输出路径")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    stocks_index_dir = project_root / "get-data" / "data" / "stocks_index"
    
    if not stocks_index_dir.exists():
        print("stocks_index 目录不存在")
        return
    
    date_dirs = [d for d in stocks_index_dir.iterdir() if d.is_dir()]
    if not date_dirs:
        print("没有找到日期目录")
        return
    
    latest_date = sorted(date_dirs, key=lambda d: d.name, reverse=True)[0].name
    output_dir = project_root / "report_index" / f"reports_index_{latest_date}"
    
    print(f"最新日期: {latest_date}")
    print(f"预期输出目录: {output_dir}")
    print(f"目录存在: {output_dir.exists()}")
    
    if output_dir.exists():
        files = list(output_dir.glob("*.html"))
        print(f"\n输出文件:")
        for f in files:
            print(f"  - {f.name}")
    else:
        print("\n提示: 运行 python scripts/build_reports_index.py 生成报告索引")
    
    print("=" * 60)

if __name__ == "__main__":
    test_index_path()
    test_api_server()
    test_build_reports_index()
    
    print("\n[OK] 测试完成")
    print("\n下一步:")
    print("  1. 运行各模块生成报告，验证 stocks_index.csv 是否正确生成到日期目录")
    print("  2. 运行 python scripts/build_reports_index.py 生成报告索引")
    print("  3. 运行 python api_server.py 启动 API 服务")

