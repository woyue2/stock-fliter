"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

INPUT: DataFrame 包含 (涨幅, 成交额, 主力净额, 散户净额) 等字段
OUTPUT: 新增列 (主力强度, 基础行为, 主力真实验为, 资金效率, 预期)
"""
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class StrengthAnalyzer:
    def __init__(self):
        # 这里的阈值可以后续通过 config 抽离
        self.strong_threshold = 3.0
        self.weak_threshold = 1.0
        self.out_threshold = -1.0
        
    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        核心推导逻辑：
        A: 主力强度 = (主力净额 / 总成交额) * 100
        B: 主力行为 = 根据强度分档 + 散户反向验证
        C: 资金效率 = 强度换取的涨幅比，结合成交额判定预期
        """
        if df.empty:
            logger.warning("Empty DataFrame passed to StrengthAnalyzer.")
            return df
            
        result_df = df.copy()
        
        # 兜底：如果外部没有提供主力净额等数据，则需要有默认机制或返回空
        if '主力净额' not in result_df.columns or '散户净额' not in result_df.columns or '成交额' not in result_df.columns:
            logger.error("Data missing required columns: 主力净额, 散户净额, 成交额")
            # 出于演示/占位，我们可以填充假数据或者抛出异常。
            # 为了能够跑通，抛弃不合规行，或返回。
            return pd.DataFrame()

        # 计算主力强度
        # 注意：避免除以0
        result_df['主力强度'] = result_df.apply(
            lambda x: (x['主力净额'] / x['成交额']) * 100 if x['成交额'] > 0 else 0, 
            axis=1
        )
        
        # Vectorized implementation of the A*B*C logic
        behaviors = []
        expectations = []
        efficiencies = []
        
        for _, row in result_df.iterrows():
            main_strength = row['主力强度']
            retail_net = row['散户净额']
            pct_chg = row.get('涨幅', 0.0)
            amount = row['成交额']
            
            # --- 阶段 A：基础状态划定 ---
            if main_strength >= self.strong_threshold:
                base = "抢筹"
            elif self.weak_threshold < main_strength < self.strong_threshold:
                base = "建仓"
            elif self.out_threshold <= main_strength <= self.weak_threshold:
                base = "洗盘"
            else:
                base = "出货"
                
            # --- 阶段 B：真假意图判别 (与散户博弈) ---
            # 真：主力买、散户卖；或者 主力卖、散户买
            is_true = True
            if main_strength > 0 and retail_net > 0:
                is_true = False  # 如果主力和散户都在买，主力带散户玩，可能是假象(诱多或后续洗盘)
            if main_strength < 0 and retail_net < 0:
                is_true = False  # 主力卖散户也割肉，可能是假出货真打压
                
            behavior = ("真" if is_true else "假") + base
            behaviors.append(behavior)
            
            # --- 阶段 C：资金效率与预期判定 ---
            # 效率：每百元强度换取了多少涨幅
            efficiency = pct_chg / main_strength if main_strength > 0 else 0
            efficiencies.append(round(efficiency, 2))
            
            expectation = "观望"
            # 1. 下跌判定：高效欺骗或滞涨没量
            # 强度很大，但是涨幅不足，容量也很小
            if main_strength > 2.5 and efficiency < 0.3 and amount < 500:
                expectation = "下跌"
            # 真抢筹但散户跟风，预期会下杀洗盘
            elif behavior == "真抢筹" and retail_net > 0:
                expectation = "下跌"
            # 弱势阴跌：洗盘都没力度，成交量极低，被市场边缘化（如序号14: 文化传媒）
            elif main_strength < 0.5 and amount < 300:
                expectation = "下跌"
            
            # 2. 冲高回落判定：巨无霸拉不动 或 获利盘压制
            # 体量过大（如上证指数），就算真洗盘，强度不够也只能冲高回落
            elif amount > 8000 and main_strength < 1.0:
                expectation = "冲高回落"
            # 涨幅已经偏高，有获利盘压力，或者真出货/假建仓
            elif behavior in ["真出货", "假建仓"] or pct_chg > 5.0:
                expectation = "冲高回落"
                
            # 3. 上涨判定：坚实容量、真买入
            elif behavior in ["真建仓", "真抢筹", "真洗盘", "假出货"]:
                if pct_chg < 3.0: # 未透支涨幅
                    expectation = "上涨"
                else:
                    expectation = "冲高回落" # 涨幅已经偏高，有获利盘压力
                
            expectations.append(expectation)
            
        result_df['主力行为'] = behaviors
        result_df['预期'] = expectations
        result_df['资金效率'] = efficiencies
        
        return result_df
