import pandas as pd
import numpy as np

class MagicNumberAnalyzer:
    """
    Magic Number Analyzer (神奇数字分析器)
    Implements price digit patterns and mathematical relations based on specialized rules.
    """
    
    @staticmethod
    def analyze(df: pd.DataFrame) -> pd.Series:
        """
        Analyze a dataframe of OHLCV data for 'Magic Number' patterns in the 'low' price.
        Returns a boolean Series 'is_magic_number'.
        """
        if df.empty or 'low' not in df.columns:
            return pd.Series(False, index=df.index)
            
        return df['low'].apply(MagicNumberAnalyzer.is_magic_number)

    @staticmethod
    def is_magic_number(price: float) -> bool:
        if price <= 0:
            return False
            
        # 1. Basic digits extraction
        pl = round(price, 2)
        
        # 百位 (D0), 十位 (D1), 个位 (D2), 十分位 (D3), 百分位 (D4)
        d0 = int(pl // 100) % 10
        d1 = int(pl // 10) % 10
        d2 = int(pl // 1) % 10
        d3 = int(pl * 10) % 10
        d4 = int(pl * 100) % 10
        
        # 2. Base 4-bit Patterns (AAAA, AABB, ABAB, ABBA, ABAC) for price >= 10
        base_4bit = False
        if pl >= 10:
            aaaa = (d1 == d2 == d3 == d4)
            aabb = (d1 == d2 and d3 == d4)
            abab = (d1 == d3 and d2 == d4)
            abba = (d1 == d4 and d2 == d3)
            abac = (d1 == d3 and abs(d2 - d4) == 1)
            base_4bit = aaaa or aabb or abab or abba or abac
            
        # 3. Base 3-bit Patterns (AAA, ABA, CC, 0, Sequence)
        aaa = (d2 == d3 == d4)
        aba = (d2 == d4)
        cc = (d3 == d4)
        tail_zero = (d4 == 0)
        # Sequence: 123 or 321
        seq_up = (d2 == d3 - 1 == d4 - 2)
        seq_down = (d2 == d3 + 1 == d4 + 2)
        base_3bit = aaa or aba or cc or tail_zero or seq_up or seq_down
        
        # 4. Mathematical relations (關注 D2, D3, D4)
        # Sum/Product/SumMod10
        math_1bit = ((d2 + d3 == d4) or (d2 + d4 == d3) or (d3 + d4 == d2)) or \
                    (((d2 * d3 == d4) or (d2 * d4 == d3) or (d3 * d4 == d2)) and pl >= 1) or \
                    ((d2 + d3 + d4) % 10 == 0 and (d2 + d3 + d4) > 0)
                    
        # 5. Math 2-bit (關注 D1, D2, D3, D4) for price >= 10
        math_2bit = False
        if pl >= 10:
            sum_mod_10 = ((d1 + d2 + d3 + d4) % 10 == 0 and (d1 + d2 + d3 + d4) > 0)
            symm = (d1 + d2 == d3 + d4) or (d1 + d4 == d2 + d3) or (d1 + d3 == d2 + d4)
            sum_3_eq_1 = (d1 + d2 + d3 == d4) or (d1 + d2 + d4 == d3) or (d1 + d3 + d4 == d2) or (d2 + d3 + d4 == d1)
            prod_eq = (d1 * d2 == d3 * d4 and pl >= 1)
            math_2bit = sum_mod_10 or symm or sum_3_eq_1 or prod_eq
            
        # 6. Math 3-bit (關注 D0, D1, D2, D3, D4) for price >= 100
        math_3bit = False
        if pl >= 100:
            math_3bit = ((d0 + d1 + d2 + d3 + d4) % 10 == 0 and (d0 + d1 + d2 + d3 + d4) > 0)
            
        # 7. Integer Part vs Decimal Part (關注 INTPART, D3, D4)
        int_val = int(pl)
        int_math = (int_val == d3 + d4) or (int_val == d3 * d4)
        
        return base_4bit or base_3bit or math_1bit or math_2bit or math_3bit or int_math
