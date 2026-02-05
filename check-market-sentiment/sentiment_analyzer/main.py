#!/usr/bin/env python3
"""
Minute-level Market Sentiment Analyzer
分钟级市场情绪分析器 - 主入口
"""

import argparse
import logging
from pathlib import Path
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentiment_analyzer.data_loader import DataLoader
from sentiment_analyzer.sentiment_engine import SentimentEngine
from sentiment_analyzer.tomorrow_predictor import TomorrowPredictor
from sentiment_analyzer.report_generator import ReportGenerator
from pattern_analyzer import PatternAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='分钟级市场情绪分析器'
    )
    
    parser.add_argument(
        '--date', '-d',
        type=str,
        help='分析日期 (YYYY-MM-DD)，默认使用最新可用日期'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        help='分钟数据根目录'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default='./output',
        help='报告输出目录 (默认: ./output)'
    )
    
    parser.add_argument(
        '--sample', '-s',
        type=int,
        help='采样股票数量 (用于测试)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细信息'
    )
    
    return parser.parse_args()


def analyze_date(date: str, 
                data_loader: DataLoader,
                output_dir: str,
                sample: int = None) -> str:
    """
    分析指定日期的市场情绪
    
    Args:
        date: 日期
        data_loader: 数据加载器
        output_dir: 输出目录
        sample: 采样数量
    
    Returns:
        报告文件路径
    """
    logger.info(f"=" * 50)
    logger.info(f"开始分析 {date} 的市场情绪")
    logger.info(f"=" * 50)
    
    # Step 1: 加载数据
    logger.info(f"[1/4] 加载分钟数据...")
    stocks = data_loader.load_all_stocks(date, sample=sample)
    
    if not stocks:
        logger.error("未加载到任何股票数据")
        raise ValueError("No stock data available")
    
    logger.info(f"成功加载 {len(stocks)} 只股票")
    
    # Step 2: 形态分析
    logger.info(f"[2/4] 进行形态分析...")
    pattern_analyzer = PatternAnalyzer()
    patterns = {}
    
    for stock in stocks[:min(100, len(stocks))]:  # 限制数量加速
        try:
            result = pattern_analyzer.analyze_market(stock['data'])
            pattern = result.get('pattern', 'unknown')
            patterns[stock['code']] = pattern
        except Exception as e:
            logger.warning(f"形态分析失败 {stock['code']}: {e}")
    
    # 对于未分析的股票，使用默认形态
    analyzed = len(patterns)
    for stock in stocks:
        if stock['code'] not in patterns:
            patterns[stock['code']] = 'unknown'
    
    logger.info(f"完成 {analyzed} 只股票形态分析")
    
    # Step 3: 情绪聚合
    logger.info(f"[3/4] 聚合市场情绪...")
    engine = SentimentEngine()
    aggregated_stats = engine.aggregate_all(stocks, patterns)
    
    # 计算基础统计
    market_stats = data_loader.calculate_market_statistics(stocks)
    
    logger.info(f"  - 平均涨幅: {market_stats.get('avg_return', 0):.2%}")
    logger.info(f"  - 涨跌比: {market_stats.get('up_down_ratio', 0):.2f}")
    
    # Step 4: 明日推断
    logger.info(f"[4/4] 生成明日推断...")
    predictor = TomorrowPredictor()
    prediction = predictor.predict(aggregated_stats)
    
    logger.info(f"  - 偏强: {prediction.bullish_prob:.1%}")
    logger.info(f"  - 震荡: {prediction.neutral_prob:.1%}")
    logger.info(f"  - 偏弱: {prediction.bearish_prob:.1%}")
    logger.info(f"  - 置信度: {prediction.confidence:.0%}")
    
    # Step 5: 生成报告
    logger.info(f"[5/5] 生成HTML报告...")
    generator = ReportGenerator(output_dir)
    report_path = generator.generate(date, aggregated_stats, prediction, market_stats)
    
    logger.info(f"报告已生成: {report_path}")
    
    return report_path


def main():
    """主函数"""
    args = parse_args()
    
    # 配置
    data_dir = Path(args.data_dir) if args.data_dir else None
    output_dir = args.output_dir
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 初始化
    data_loader = DataLoader(data_dir)
    
    # 确定日期
    date = args.date
    if not date:
        date = data_loader.get_latest_date()
        if date:
            logger.info(f"自动选择最新日期: {date}")
        else:
            logger.error("未找到可用的日期数据")
            sys.exit(1)
    
    try:
        report_path = analyze_date(date, data_loader, output_dir, args.sample)
        logger.info("=" * 50)
        logger.info("分析完成!")
        logger.info(f"报告: {report_path}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"分析失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
