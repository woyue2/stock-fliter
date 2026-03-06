"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

INPUT: CLI Args
OUTPUT: 驱动 ETL 流程：load -> analyze -> report
"""
import os
import logging
from datetime import datetime

from data_loader import load_data
from analyzers.strength_analyzer import StrengthAnalyzer
from reporters.markdown_reporter import MarkdownReporter
from reporters.html_reporter import HTMLReporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_pipeline(args):
    logger.info("Starting Zhuli Strength Pipeline (A*B*C logic)")
    
    # 建立输出目录
    now = datetime.now()
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "output",
        now.strftime("%Y-%m-%d"),
        now.strftime("%H-%M-%S")
    )
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load Data
    is_test = getattr(args, "test", False)
    df = load_data(is_test=is_test)
    if df.empty:
        logger.warning("No data loaded. Pipeline stopping.")
        return
        
    logger.info(f"Loaded {len(df)} records for analysis.")
    
    # 2. Analyze
    analyzer = StrengthAnalyzer()
    analyzed_df = analyzer.analyze(df)
    
    # 3. Report
    # Markdown
    md_reporter = MarkdownReporter(output_dir)
    md_file = md_reporter.generate(analyzed_df)
    
    # HTML (Required for the Index building script)
    html_reporter = HTMLReporter(output_dir)
    html_file = html_reporter.generate(analyzed_df)
    
    logger.info(f"Pipeline finished. Reports saved to: {output_dir}")
