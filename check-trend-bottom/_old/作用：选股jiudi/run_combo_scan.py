"""
组合信号选股主程序
与九底系统（run_test_scan.py）区分，使用多指标分析

使用方法:
1. 扫描全市场：python run_combo_scan.py
2. 测试模式（前100只）：python run_combo_scan.py --test
3. 扫描自定义股票池：修改代码中的stock_list
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from combo_signal_scanner import ComboSignalScanner


def main():
    """主函数"""
    print("\n" + "🎯" * 30)
    print("   组合信号选股系统 - 多指标分析")
    print("   指标：MACD + RSI + KDJ + 成交量 + 均线 + 突破")
    print("🎯" * 30 + "\n")

    # 创建扫描器
    scanner = ComboSignalScanner(output_dir='./output_combo')

    # ========== 选择扫描模式 ==========

    # 模式1：扫描全市场（默认）
    print("📌 模式：扫描全市场\n")
    scanner.scan_market(
        max_workers=20,  # 线程数，根据网络情况调整（建议10-30）
        limit=None,      # None=全市场，或设置数字如100进行测试
        min_score=3      # 最低评分（0-15分），建议设置为3-5
    )

    # # 模式2：测试模式（扫描前N只股票）
    # print("📌 模式：测试模式（前100只）\n")
    # scanner.scan_market(
    #     max_workers=10,
    #     limit=100,      # 测试前100只
    #     min_score=0     # 测试模式显示所有结果
    # )

    # # 模式3：扫描自定义股票池
    # stock_pool = {
    #     '000001': '平安银行',
    #     '000002': '万科A',
    #     '600000': '浦发银行',
    #     '600036': '招商银行',
    #     # 添加更多股票...
    # }
    # stock_codes = list(stock_pool.keys())
    # scanner.scan_custom_pool(stock_codes, stock_pool)

    # ==================================

    # 保存结果
    print("\n" + "💾" * 30)
    scanner.save_results()

    print("\n" + "✅" * 30)
    print("   扫描完成！结果已保存到 output_combo 目录")
    print("✅" * 30 + "\n")


if __name__ == '__main__':
    main()
