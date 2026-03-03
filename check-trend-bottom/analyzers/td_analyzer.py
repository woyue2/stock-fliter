# -*- coding: utf-8 -*-
"""
TD多底分析器

实现TD序列分析：
- 日线九底
- 周线九底
- 月线九底
- 多周期共振
- 支持6底/7底/8底/9底

使用项目统一的技术指标库
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# 添加 util 目录到路径
util_dir = Path(__file__).resolve().parent.parent.parent / "util"
if str(util_dir) not in sys.path:
    sys.path.append(str(util_dir))

try:
    from progress import ProgressBar
except ImportError:
    class ProgressBar:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, *args, **kwargs): pass

from data_loader import (
    iter_stock_items, load_daily_data, get_board_type, 
    get_stock_industry, login_baostock, logout_baostock,
    OUTPUT_DIR
)

# 使用项目统一的技术指标库
from indicators_lib import TechnicalIndicators


@dataclass
class TDAnalyzerConfig:
    """TD分析器配置"""
    days: int = 365  # 分析最近天数
    td_threshold: int = 9  # 九底阈值
    near_threshold: int = 7  # 接近九底阈值
    six_threshold: int = 6  # 六底阈值


class TDAnalyzer:
    """TD九底分析器"""
    
    def __init__(self, config: TDAnalyzerConfig, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
    
    def run(self, limit: Optional[int] = None, use_local_files: bool = False) -> tuple[pd.DataFrame, Optional[datetime]]:
        """
        运行TD分析

        Args:
            limit: 限制股票数量（测试用）
            use_local_files: 是否使用本地文件（遍历raw目录）

        Returns:
            (分析结果DataFrame, 数据最新日期)
            分析结果 DataFrame
        """
        bs_ok = False
        
        results = []
        stocks = list(iter_stock_items(limit=limit, from_raw=use_local_files))
        
        print(f"  📈 开始分析 {len(stocks)} 只股票...")
        
        # 预先显示数据日期
        if stocks:
            for item in stocks[:3]:
                try:
                    df = load_daily_data(item.code, self.config.days)
                    if not df.empty and "date" in df.columns:
                        last_date_val = df["date"].iloc[-1]
                        last_dt = pd.to_datetime(last_date_val) if isinstance(last_date_val, str) else last_date_val
                        print(f"[数据] 分析数据基准日期: {last_dt.strftime('%Y-%m-%d')}")
                        break
                except Exception:
                    continue

        global_max_date = None
        success_count = 0
        fail_count = 0
        
        with ProgressBar(len(stocks), desc="TD分析") as pbar:
            for item in stocks:
                try:
                    df = load_daily_data(item.code, self.config.days)
                    if df.empty:
                        pbar.update(1, success=False)
                        fail_count += 1
                        continue
                
                    # 更新全局最新日期
                    if "date" in df.columns and not df.empty:
                        last_date_val = df["date"].iloc[-1]
                        if isinstance(last_date_val, str):
                             last_dt = pd.to_datetime(last_date_val)
                        else:
                             last_dt = last_date_val
                             
                        if global_max_date is None or last_dt > global_max_date:
                            global_max_date = last_dt
                
                    analysis = self._analyze_stock(df)
                    if "error" in analysis:
                        pbar.update(1, success=False)
                        fail_count += 1
                        continue
                
                    # 添加股票基本信息
                    analysis["代码"] = item.code
                    analysis["名称"] = item.name
                    analysis["板块"] = get_board_type(item.code)
                    analysis["行业"] = item.industry if hasattr(item, "industry") and item.industry else "未知"
                
                    results.append(analysis)
                    success_count += 1
                    pbar.update(1, success=True)
                
                except Exception as e:
                    if fail_count == 0:
                        print(f"\n❌ 首次错误 (code={item.code}): {e}")
                        import traceback
                        traceback.print_exc()
                    pbar.update(1, success=False)
                    fail_count += 1
                    continue
        
        # 显示统计信息
        print(f"[统计] 总计: {len(stocks)} | 成功: {success_count} | 失败: {fail_count}")
        if global_max_date:
             print(f"[数据] 数据最新日期: {global_max_date.strftime('%Y-%m-%d')}")
        
        if not results:
            return pd.DataFrame(), global_max_date
        
        result_df = pd.DataFrame(results)
        
        # 调整列顺序
        column_order = [
            # 股票标识
            "代码", "名称", "板块", "行业",
            # 核心筛选指标
            "日TD计数", "周TD计数", "月TD计数",
            "9底周期数", "8底周期数", "7底周期数", "6底周期数",
            "共振级别", "底部详情",
            # 各周期底部级别
            "日底部级别", "周底部级别", "月底部级别",
            # 各周期9/8/7/6底状态
            "日9底", "日8底", "日7底", "日6底",
            "周9底", "周8底", "周7底", "周6底",
            "月9底", "月8底", "月7底", "月6底",
            # 最近高底位置
            "日最近高底日期", "日最近高底价格",
            "周最近高底日期", "周最近高底价格",
            "月最近高底日期", "月最近高底价格",
            # 最新行情
            "日最新日期", "日最新价",
            "周最新日期", "周最新价",
            "月最新日期", "月最新价",
            # 价格区间
            "日最高价", "日最低价", "日均价",
            "周最高价", "周最低价", "周均价",
            "月最高价", "月最低价", "月均价",
        ]
        result_df = result_df[[c for c in column_order if c in result_df.columns]]
        
        return result_df, global_max_date
    
    def _analyze_stock(self, df_daily: pd.DataFrame) -> Dict:
        """分析单只股票"""
        df_daily = df_daily.copy()
        
        # 重采样周线和月线
        df_weekly = TechnicalIndicators.resample_ohlcv(df_daily, "W")
        try:
            df_monthly = TechnicalIndicators.resample_ohlcv(df_daily, "ME") 
        except:
            df_monthly = TechnicalIndicators.resample_ohlcv(df_daily, "M")  # 使用 "M" 替代 "ME" 以兼容旧版本 pandas

        
        result = {}
        
        # 日线分析
        result.update(self._analyze_period(df_daily, "日"))
        result.update(self._get_td_info(df_daily, "日"))
        
        # 周线分析
        result.update(self._analyze_period(df_weekly, "周"))
        result.update(self._get_td_info(df_weekly, "周"))
        
        # 月线分析
        result.update(self._analyze_period(df_monthly, "月"))
        result.update(self._get_td_info(df_monthly, "月"))
        
        # 计算共振
        result.update(self._build_resonance(
            result["日TD计数"],
            result["周TD计数"],
            result["月TD计数"]
        ))
        
        return result
    
    def _analyze_period(self, df: pd.DataFrame, prefix: str) -> Dict:
        """分析单个周期"""
        if df.empty:
            return {
                f"{prefix}最新日期": "",
                f"{prefix}最新价": None,
                f"{prefix}最高价": None,
                f"{prefix}最低价": None,
                f"{prefix}均价": None,
            }
        
        last_row = df.iloc[-1]
        return {
            f"{prefix}最新日期": pd.Timestamp(last_row["date"]).strftime("%Y-%m-%d"),
            f"{prefix}最新价": round(float(last_row["close"]), 2),
            f"{prefix}最高价": round(float(df["high"].max()), 2),
            f"{prefix}最低价": round(float(df["low"].min()), 2),
            f"{prefix}均价": round(float(df["close"].mean()), 2),
        }
    
    def _get_td_info(self, df: pd.DataFrame, prefix: str) -> Dict:
        """获取TD底部信息"""
        if df.empty or "close" not in df.columns:
            return {
                f"{prefix}TD计数": 0,
                f"{prefix}9底": False,
                f"{prefix}8底": False,
                f"{prefix}7底": False,
                f"{prefix}6底": False,
                f"{prefix}底部级别": "无",
                f"{prefix}最近高底日期": "",
                f"{prefix}最近高底价格": None,
            }

        close_series = df["close"].reset_index(drop=True).astype(float)
        sequence = TechnicalIndicators.calculate_td_sequence(close_series)
        td_count = int(sequence.iloc[-1]) if not sequence.empty else 0

        # 判断底部级别
        is_9 = td_count >= 9
        is_8 = td_count >= 8
        is_7 = td_count >= 7
        is_6 = td_count >= 6

        if is_9:
            level = "9底"
        elif is_8:
            level = "8底"
        elif is_7:
            level = "7底"
        elif is_6:
            level = "6底"
        else:
            level = "无"

        # 查找最近高底位置（>=6）
        last_high_date = ""
        last_high_price = None
        for idx in range(len(sequence) - 1, -1, -1):
            if sequence.iloc[idx] >= 6:
                row = df.iloc[idx]
                last_high_date = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
                last_high_price = round(float(row["close"]), 2)
                break

        return {
            f"{prefix}TD计数": td_count,
            f"{prefix}9底": is_9,
            f"{prefix}8底": is_8,
            f"{prefix}7底": is_7,
            f"{prefix}6底": is_6,
            f"{prefix}底部级别": level,
            f"{prefix}最近高底日期": last_high_date,
            f"{prefix}最近高底价格": last_high_price,
        }
    
    def _build_resonance(self, daily_td: int, weekly_td: int, monthly_td: int) -> Dict:
        """
        计算多周期共振，生成所有满足条件的组合并按降序排列
        优先级: 周期数越多越靠前，同周期数时阈值越高越靠前
        支持6底/7底/8底/9底
        """
        # 判断各周期是否达到各级别
        d9, d8, d7, d6 = daily_td >= 9, daily_td >= 8, daily_td >= 7, daily_td >= 6
        w9, w8, w7, w6 = weekly_td >= 9, weekly_td >= 8, weekly_td >= 7, weekly_td >= 6
        m9, m8, m7, m6 = monthly_td >= 9, monthly_td >= 8, monthly_td >= 7, monthly_td >= 6

        # 收集所有满足条件的组合
        combinations = []

        # ========== 单周期组合 ==========
        if d9: combinations.append(("日", 9))
        if w9: combinations.append(("周", 9))
        if m9: combinations.append(("月", 9))
        if d8: combinations.append(("日", 8))
        if w8: combinations.append(("周", 8))
        if m8: combinations.append(("月", 8))
        if d7: combinations.append(("日", 7))
        if w7: combinations.append(("周", 7))
        if m7: combinations.append(("月", 7))
        if d6: combinations.append(("日", 6))
        if w6: combinations.append(("周", 6))
        if m6: combinations.append(("月", 6))

        # ========== 双周期组合 ==========
        # 日周双周期
        if d9 and w9: combinations.append(("日周", 9))
        if d8 and w8: combinations.append(("日周", 8))
        if d7 and w7: combinations.append(("日周", 7))
        if d6 and w6: combinations.append(("日周", 6))
        # 日月双周期
        if d9 and m9: combinations.append(("日月", 9))
        if d8 and m8: combinations.append(("日月", 8))
        if d7 and m7: combinations.append(("日月", 7))
        if d6 and m6: combinations.append(("日月", 6))
        # 周月双周期
        if w9 and m9: combinations.append(("周月", 9))
        if w8 and m8: combinations.append(("周月", 8))
        if w7 and m7: combinations.append(("周月", 7))
        if w6 and m6: combinations.append(("周月", 6))

        # ========== 三周期组合 ==========
        if d9 and w9 and m9: combinations.append(("日周月", 9))
        if d8 and w8 and m8: combinations.append(("日周月", 8))
        if d7 and w7 and m7: combinations.append(("日周月", 7))
        if d6 and w6 and m6: combinations.append(("日周月", 6))

        # 按降序排列: 先按周期数(名称长度)，同周期数时按阈值降序
        def sort_key(item):
            name, threshold = item
            cycle_count = len(name)  # 单周期=1, 双周期=2, 三周期=3
            return (cycle_count, threshold)

        combinations.sort(key=sort_key, reverse=True)

        # 构建共振级别字符串
        if combinations:
            level = combinations[0][0] + str(combinations[0][1]) + "底"
        else:
            level = "无底部信号"

        # 构建详细底部描述 (所有组合)
        details = []
        for name, threshold in combinations:
            details.append(f"{name}{threshold}")
        detail_str = "+".join(details) if details else "无"

        # 计算各级别的周期数
        cycles_9 = sum([d9, w9, m9])
        cycles_8 = sum([d8, w8, m8])
        cycles_7 = sum([d7, w7, m7])
        cycles_6 = sum([d6, w6, m6])

        return {
            "9底周期数": cycles_9,
            "8底周期数": cycles_8,
            "7底周期数": cycles_7,
            "6底周期数": cycles_6,
            "共振级别": level,
            "底部详情": detail_str,
        }

    def save(self, df: pd.DataFrame, filename: Optional[str] = None, output_dir: Optional[Path] = None) -> Path:
        """保存分析结果"""
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"td_analysis_{ts}.csv"

        save_dir = output_dir if output_dir else self.output_dir
        path = save_dir / filename
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return path
