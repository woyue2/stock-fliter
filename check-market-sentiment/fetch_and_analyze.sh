#!/bin/bash
# ============================================
# 全市场情绪分析脚本
# 1. 获取全部A股分钟数据 -> 2. 分析市场情绪
# ============================================

set -e  # 遇错即停

# 配置
PROJECT_DIR="/home/aa/Park/stock-fliter/check-market-sentiment"
DATA_DIR="/home/aa/Park/stock-fliter/get-data"
MAX_WORKERS=8  # 并行下载线程数

echo "============================================"
echo "全市场情绪分析脚本"
echo "============================================"
echo "目标: 全市场A股 (5000+ 股票)"
echo "并行线程: $MAX_WORKERS"
echo "开始时间: $(date)"
echo "============================================"

# Step 1: 获取全市场分钟数据
echo ""
echo "[1/2] 正在获取全市场分钟数据..."
cd "$DATA_DIR"

echo "开始下载所有A股数据（预计10-30分钟）..."
START_TIME=$(date +%s)

# 使用 --all 获取全部A股，并行加速
python fetch_minute_akshare.py --all --realtime

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo ""
echo "数据下载完成，耗时: ${DURATION}秒"

# Step 2: 分析市场情绪
echo ""
echo "[2/2] 正在分析全市场情绪..."
cd "$PROJECT_DIR"

# 获取最新日期
LATEST_DATE=$(ls -t "$DATA_DIR"/data/minute_akshare/*/ 2>/dev/null | head -1 | xargs -I {} basename {} 2>/dev/null || echo "")

if [ -n "$LATEST_DATE" ]; then
    echo "分析日期: $LATEST_DATE"
    
    # 统计有多少只股票
    STOCK_COUNT=$(ls "$DATA_DIR"/data/minute_akshare/"$LATEST_DATE"/*.csv 2>/dev/null | wc -l)
    echo "分析股票数: $STOCK_COUNT"
    
    # 全市场分析（不采样）
    python -m sentiment_analyzer.main --date "$LATEST_DATE"
else
    echo "未找到日期目录，使用根目录数据..."
    python -m sentiment_analyzer.main
fi

END_TIME2=$(date +%s)
DURATION2=$((END_TIME2 - END_TIME))

echo ""
echo "============================================"
echo "全市场分析完成!"
echo "总耗时: $((END_TIME2 - START_TIME))秒"
echo "报告位置: $PROJECT_DIR/output/sentiment_*.html"
echo "============================================"
