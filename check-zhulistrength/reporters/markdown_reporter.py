"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

INPUT: Analyzed DataFrame / Output Directory
OUTPUT: zhulistrength_report.md
"""
import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class MarkdownReporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def generate(self, df: pd.DataFrame) -> str:
        if df.empty:
            logger.warning("DataFrame is empty. Skip markdown generating.")
            return ""
            
        report_path = os.path.join(self.output_dir, "zhulistrength_report.md")
        
        # 将必要列整理并格式化
        cols_to_show = ["板块", "涨幅", "成交额", "主力净额", "散户净额", "主力强度", "主力行为", "资金效率", "预期"]
        df_show = df[cols_to_show].copy()
        
        # 格式化
        df_show['涨幅'] = df_show['涨幅'].apply(lambda x: f"{x:.2f}%")
        df_show['主力强度'] = df_show['主力强度'].apply(lambda x: f"{x:.2f}")
        df_show['资金效率'] = df_show['资金效率'].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else "0.00")
        
        md_table = df_show.to_markdown(index=False)
        
        content = f"""# 主力资金与散户博弈分析报告 (Check-ZhuliStrength)

> [!NOTE]
> 本报告基于 A*B*C 维度模型生成。
> - **A (主力强度)** = (主力净额 / 总成交额) * 100
> - **B (散户行为** = 判断散户与主力是否同向（背离判定为真）
> - **C (资金效率)** = 每单位强度换取的涨幅

## 分析结果矩阵

{md_table}

## 风险提示
本数据侧推算由于包含大量主观假设（散户逆向必涨、容量小必骗炮等），仅供技术层面验证交流，不作为投资决策使用。
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.info("Markdown report generated successfully.")
        return report_path
