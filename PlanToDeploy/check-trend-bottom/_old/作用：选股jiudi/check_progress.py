"""
全市场扫描进度监控
"""
import time
import subprocess
import os

print("全市场扫描进行中...")
print("预计需要15-25分钟")
print("=" * 60)
print()

# 检查输出目录
output_dir = "./output"
latest_file = None
last_size = 0

print("正在监控扫描进度...")
print("提示：按 Ctrl+C 停止监控（扫描会继续在后台运行）")
print()

try:
    check_count = 0
    while True:
        check_count += 1

        # 检查是否有新的输出文件
        import glob
        csv_files = glob.glob(f"{output_dir}/全部分析结果_*.csv")

        if csv_files:
            # 获取最新的文件
            latest_file = max(csv_files, key=os.path.getctime)
            file_size = os.path.getsize(latest_file)

            if file_size > last_size:
                print(f"[{check_count}] ✅ 检测到文件更新: {os.path.basename(latest_file)}")
                print(f"     文件大小: {file_size/1024:.1f} KB")
                last_size = file_size

        # 每30次检查（约5分钟）显示一次
        if check_count % 30 == 0:
            elapsed = check_count * 10  # 每次循环10秒
            print(f"[{check_count}] ⏱️  已运行: {elapsed//60} 分 {elapsed%60} 秒")
            if csv_files:
                print(f"     当前文件数: {len(csv_files)}")

        time.sleep(10)  # 每10秒检查一次

except KeyboardInterrupt:
    print("\n" + "=" * 60)
    print("监控已停止")
    print(f"扫描仍在后台运行，请稍后查看 {output_dir} 目录")
    print("=" * 60)
