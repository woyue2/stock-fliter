"""
小规模扫描测试（前50只股票）
"""
import sys
import io
from pathlib import Path

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from jiudi_scanner import JiuDiScanner

print("=" * 60)
print("🔍 小规模扫描测试（前50只主板股票）")
print("=" * 60)
print()

scanner = JiuDiScanner(output_dir='./output')

# 扫描前50只主板股票（6开头或0开头）
print("⚡ 开始扫描...\n")

scanner.scan_market(
    max_workers=5,  # 使用5个线程
    limit=None      # 我们会在scan_market内部手动过滤
)
