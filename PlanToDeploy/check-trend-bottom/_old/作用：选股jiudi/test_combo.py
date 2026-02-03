"""
测试组合信号扫描器（测试模式）
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from combo_signal_scanner import ComboSignalScanner


def main():
    """测试函数"""
    print("\n[测试] 组合信号扫描器\n")

    scanner = ComboSignalScanner(output_dir='./output_combo_test')

    # 测试模式：扫描前50只股票
    scanner.scan_market(
        max_workers=5,
        limit=50,       # 只扫描前50只
        min_score=0     # 显示所有结果
    )

    # 保存结果
    scanner.save_results()

    print("\n[完成] 测试结束")


if __name__ == '__main__':
    main()
