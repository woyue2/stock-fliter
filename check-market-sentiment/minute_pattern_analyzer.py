# -*- coding: utf-8 -*-
"""
分钟级走势形态分析器 - 全新方法

核心思想：将每只股票的日内K线分成240份（每分钟一个采样点），
把每分钟的采样当成一个变量，组成一个240维向量，用这个向量来判定股票走向。

优势：
1. 捕捉微观走势细节
2. 完整的日内价格演变过程
3. 可以使用向量相似度/机器学习识别形态
4. 早盘vs午盘对比更精确
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from collections import Counter


class MinutePatternAnalyzer:
    """
    基于240维分钟向量的走势形态分析器
    
    将一天的分时数据转换为240维向量，然后通过向量运算识别形态
    """
    
    # 标准交易时长（分钟）
    TRADING_MINUTES = 240  # 4小时 * 60分钟
    
    # 形态名称映射
    PATTERN_NAMES = {
        'strong_uptrend': '单边上涨',
        'strong_downtrend': '单边下跌',
        'v_reversal': 'V型反转',
        'inverted_v': '倒V型',
        'high_open_low_close': '高开低走',
        'low_open_high_close': '低开高走',
        'consolidation': '震荡整理',
        'flat': '平淡走势',
        'morning_strong': '早盘强势',
        'afternoon_strong': '午盘强势',
        'double_v': '双V走势',
    }
    
    def __init__(self, normalize: bool = True):
        """
        初始化分析器
        
        Args:
            normalize: 是否对向量进行归一化处理
        """
        self.normalize = normalize
    
    def minute_to_vector(self, minute_data: pd.DataFrame) -> np.ndarray:
        """
        将分钟级数据转换为240维向量
        
        核心方法：每分钟采样一次，将一天的走势转换为一个向量
        
        Args:
            minute_data: 分钟级DataFrame，需包含 'time' 和 'price' 列
            
        Returns:
            240维归一化向量
        """
        if minute_data.empty:
            return np.zeros(self.TRADING_MINUTES)
        
        # 提取价格序列
        if 'price' in minute_data.columns:
            prices = minute_data['price'].values
        elif 'close' in minute_data.columns:
            prices = minute_data['close'].values
        else:
            prices = minute_data.iloc[:, 0].values
        
        # 确保价格是数值类型
        prices = pd.to_numeric(prices, errors='coerce')
        
        # 处理缺失值
        if np.any(np.isnan(prices)):
            prices = pd.Series(prices).fillna(method='ffill').fillna(method='bfill').values
        
        # 归一化处理（以开盘价为基准）
        if self.normalize and prices[0] > 0:
            base_price = prices[0]
            vector = (prices - base_price) / base_price * 100  # 转换为百分比变化
        else:
            vector = prices
        
        # 如果数据不足240分钟，用最后一个值填充
        if len(vector) < self.TRADING_MINUTES:
            last_val = vector[-1] if len(vector) > 0 else 0
            padding = np.full(self.TRADING_MINUTES - len(vector), last_val)
            vector = np.concatenate([vector, padding])
        
        # 如果数据超过240分钟，只取前240分钟
        if len(vector) > self.TRADING_MINUTES:
            vector = vector[:self.TRADING_MINUTES]
        
        return vector
    
    def compute_vector_features(self, vector: np.ndarray) -> Dict:
        """
        从240维向量中提取特征
        
        Args:
            vector: 240维价格向量
            
        Returns:
            特征字典
        """
        features = {}
        
        # 1. 基础统计特征
        features['mean'] = np.mean(vector)
        features['std'] = np.std(vector)
        features['max'] = np.max(vector)
        features['min'] = np.min(vector)
        features['range'] = features['max'] - features['min']
        
        # 2. 趋势特征
        # 计算整体趋势（线性回归斜率）
        x = np.arange(len(vector))
        slope = np.polyfit(x, vector, 1)[0]
        features['trend_slope'] = slope
        
        # 趋势方向判断
        if slope > 0.01:
            features['trend_direction'] = 'up'
        elif slope < -0.01:
            features['trend_direction'] = 'down'
        else:
            features['trend_direction'] = 'flat'
        
        # 3. 波动特征
        # 计算日内波动率
        features['volatility'] = features['std']
        
        # 最大回撤
        cummax = np.maximum.accumulate(vector)
        drawdown = cummax - vector
        features['max_drawdown'] = np.max(drawdown)
        
        # 最大涨幅
        features['max_gain'] = features['max']
        
        # 4. 形态特征
        # 早盘表现（0-120分钟）
        morning = vector[:120]
        features['morning_mean'] = np.mean(morning)
        features['morning_std'] = np.std(morning)
        features['morning_max'] = np.max(morning)
        features['morning_min'] = np.min(morning)
        
        # 午盘表现（120-240分钟）
        afternoon = vector[120:]
        features['afternoon_mean'] = np.mean(afternoon)
        features['afternoon_std'] = np.std(afternoon)
        features['afternoon_max'] = np.max(afternoon)
        features['afternoon_min'] = np.min(afternoon)
        
        # 早盘vs午盘对比
        features['morning_afternoon_diff'] = features['afternoon_mean'] - features['morning_mean']
        
        # 5. 形态识别特征
        # 检查是否为V型反转（先跌后涨）
        min_idx = np.argmin(vector)
        if min_idx < len(vector) * 0.6:  # 最低点在60%位置之前
            features['v_shape'] = True
            features['v_position'] = min_idx / len(vector)
        else:
            features['v_shape'] = False
            features['v_position'] = 0
        
        # 检查是否为倒V型（先涨后跌）
        max_idx = np.argmax(vector)
        if max_idx < len(vector) * 0.6:  # 最高点在60%位置之前
            features['inverted_v_shape'] = True
            features['inverted_v_position'] = max_idx / len(vector)
        else:
            features['inverted_v_shape'] = False
            features['inverted_v_position'] = 0
        
        # 6. 动量特征
        # 计算30分钟滚动动量
        momentum_30 = []
        for i in range(30, len(vector)):
            momentum = vector[i] - vector[i-30]
            momentum_30.append(momentum)
        if momentum_30:
            features['avg_momentum_30'] = np.mean(momentum_30)
            features['momentum_30_std'] = np.std(momentum_30)
        else:
            features['avg_momentum_30'] = 0
            features['momentum_30_std'] = 0
        
        # 7. 开盘和收盘表现
        features['open_relative'] = vector[0]  # 开盘相对变化（归一化后应该是0）
        features['close_relative'] = vector[-1]  # 收盘相对变化
        features['intraday_return'] = vector[-1] - vector[0]  # 日内收益
        
        return features
    
    def identify_pattern(self, vector: np.ndarray, features: Dict) -> Tuple[str, str]:
        """
        基于240维向量识别走势形态
        
        Args:
            vector: 240维价格向量
            features: 从向量提取的特征
            
        Returns:
            (形态代码, 形态名称)
        """
        # 提取关键指标
        open_rel = features['open_relative']
        close_rel = features['close_relative']
        intraday = features['intraday_return']
        trend = features['trend_slope']
        volatility = features['volatility']
        morning_afternoon_diff = features['morning_afternoon_diff']
        v_shape = features['v_shape']
        inverted_v_shape = features['inverted_v_shape']
        max_gain = features['max_gain']
        max_drawdown = features['max_drawdown']
        
        # 阈值设定
        TREND_THRESHOLD = 0.02  # 趋势阈值
        VOLATILITY_LOW = 0.5    # 低波动阈值
        VOLATILITY_HIGH = 1.5   # 高波动阈值
        MORNING_AFTERNOON_THRESHOLD = 0.3  # 早盘vs午盘差异阈值
        
        # 1. V型反转检测
        # 特征：开盘下跌，最低点在早盘，之后持续反弹，收盘上涨
        if (open_rel < -0.2 and  # 开盘下跌
            close_rel > 0.2 and   # 收盘上涨
            v_shape and           # 有V型特征
            close_rel > open_rel + 0.5):  # 收盘明显高于开盘
            return 'v_reversal', 'V型反转'
        
        # 2. 倒V型反转检测
        # 特征：开盘上涨，最高点在早盘，之后持续回落，收盘下跌
        if (open_rel > 0.2 and   # 开盘上涨
            close_rel < -0.2 and  # 收盘下跌
            inverted_v_shape and  # 有倒V型特征
            open_rel > close_rel + 0.5):  # 开盘明显高于收盘
            return 'inverted_v', '倒V型'
        
        # 3. 单边上涨检测
        # 特征：持续上涨，收盘高于开盘，趋势向上
        if (trend > TREND_THRESHOLD and 
            close_rel > 0.3 and 
            intraday > 0.3 and
            max_gain > abs(features['max_drawdown'])):
            return 'strong_uptrend', '单边上涨'
        
        # 4. 单边下跌检测
        # 特征：持续下跌，收盘低于开盘，趋势向下
        if (trend < -TREND_THRESHOLD and 
            close_rel < -0.3 and 
            intraday < -0.3 and
            abs(max_drawdown) > features['max_gain']):
            return 'strong_downtrend', '单边下跌'
        
        # 5. 高开低走检测
        # 特征：开盘高于昨收（这里用归一化后的相对值），日内下跌，收盘低于开盘
        if (inverted_v_shape and
            morning_afternoon_diff < -MORNING_AFTERNOON_THRESHOLD):
            return 'high_open_low_close', '高开低走'
        
        # 6. 低开高走检测
        # 特征：开盘低于昨收，日内上涨，收盘高于开盘
        if (v_shape and
            morning_afternoon_diff > MORNING_AFTERNOON_THRESHOLD):
            return 'low_open_high_close', '低开高走'
        
        # 7. 早盘强势检测
        if (features['morning_mean'] > features['afternoon_mean'] + 0.3 and
            features['morning_max'] > features['afternoon_max']):
            return 'morning_strong', '早盘强势'
        
        # 8. 午盘强势检测
        if (features['afternoon_mean'] > features['morning_mean'] + 0.3 and
            features['afternoon_max'] > features['morning_max']):
            return 'afternoon_strong', '午盘强势'
        
        # 9. 震荡整理检测
        if (volatility > VOLATILITY_LOW and 
            abs(intraday) < 0.3 and 
            features['range'] > 1.0):
            return 'consolidation', '震荡整理'
        
        # 10. 平淡走势检测
        if (volatility < VOLATILITY_LOW and 
            abs(trend) < TREND_THRESHOLD):
            return 'flat', '平淡走势'
        
        # 默认判断
        if intraday > 0.1:
            return 'consolidation', '震荡偏强'
        elif intraday < -0.1:
            return 'consolidation', '震荡偏弱'
        else:
            return 'flat', '平淡走势'
    
    def similarity_to_pattern(self, vector: np.ndarray, pattern_type: str) -> float:
        """
        计算向量与某种典型形态的相似度
        
        Args:
            vector: 240维价格向量
            pattern_type: 典型形态类型
            
        Returns:
            相似度 (0-1)
        """
        # 定义典型形态模板（归一化的240维向量）
        templates = {
            'strong_uptrend': np.linspace(0, 2, self.TRADING_MINUTES),  # 线性上涨
            'strong_downtrend': np.linspace(0, -2, self.TRADING_MINUTES),  # 线性下跌
            'v_reversal': self._create_v_shape(self.TRADING_MINUTES),  # V型
            'inverted_v': self._create_inverted_v(self.TRADING_MINUTES),  # 倒V型
        }
        
        if pattern_type not in templates:
            return 0.0
        
        template = templates[pattern_type]
        
        # 归一化向量 (纯numpy实现)
        v_norm = (vector - np.mean(vector)) / (np.std(vector) + 1e-8)
        t_norm = (template - np.mean(template)) / (np.std(template) + 1e-8)
        
        # 计算余弦相似度: cos(A,B) = A·B / (|A|·|B|)
        dot_product = np.dot(v_norm, t_norm)
        norm_v = np.linalg.norm(v_norm)
        norm_t = np.linalg.norm(t_norm)
        similarity = dot_product / (norm_v * norm_t + 1e-8)
        
        return max(0, similarity)  # 确保在0-1范围内
    
    def _create_v_shape(self, length: int) -> np.ndarray:
        """创建V型形态模板，确保恰好length个元素"""
        left = np.linspace(1, -1, length // 2 + 1)
        right = np.linspace(-1, 0.5, length // 2 + 1)
        return np.concatenate([left[:-1], right[1:]])
    
    def _create_inverted_v(self, length: int) -> np.ndarray:
        """创建倒V型形态模板，确保恰好length个元素"""
        left = np.linspace(-1, 1, length // 2 + 1)
        right = np.linspace(1, -0.5, length // 2 + 1)
        return np.concatenate([left[:-1], right[1:]])
    
    def compare_stocks(self, vector1: np.ndarray, vector2: np.ndarray) -> Dict:
        """
        比较两只股票的走势相似度
        
        Args:
            vector1: 第一只股票的240维向量
            vector2: 第二只股票的240维向量
            
        Returns:
            相似度分析结果
        """
        # 皮尔逊相关系数 (纯numpy实现)
        def pearson_correlation(x, y):
            n = len(x)
            mean_x, mean_y = np.mean(x), np.mean(y)
            std_x, std_y = np.std(x), np.std(y)
            covariance = np.mean((x - mean_x) * (y - mean_y))
            return covariance / (std_x * std_y + 1e-8)
        
        # 余弦相似度
        cos_sim = 1 - pearson_correlation(vector1, vector2)
        
        # 欧氏距离
        euc_dist = np.linalg.norm(vector1 - vector2)
        
        # 皮尔逊相关系数
        corr = pearson_correlation(vector1, vector2)
        
        # 动态时间规整距离（简化版）
        dtw_dist = self._dtw_distance(vector1, vector2)
        
        return {
            'cosine_similarity': cos_sim,
            'euclidean_distance': euc_dist,
            'pearson_correlation': corr,
            'dtw_distance': dtw_dist,
            'is_similar': cos_sim > 0.8 or corr > 0.8,
        }
    
    def _dtw_distance(self, s1: np.ndarray, s2: np.ndarray) -> float:
        """
        计算两个序列的动态时间规整距离（简化版）
        
        Args:
            s1: 第一个序列
            s2: 第二个序列
            
        Returns:
            DTW距离
        """
        n, m = len(s1), len(s2)
        
        # 创建距离矩阵
        dtw_matrix = np.full((n + 1, m + 1), np.inf)
        dtw_matrix[0, 0] = 0
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = abs(s1[i-1] - s2[j-1])
                dtw_matrix[i, j] = cost + min(
                    dtw_matrix[i-1, j],    # 插入
                    dtw_matrix[i, j-1],    # 删除
                    dtw_matrix[i-1, j-1]   # 匹配
                )
        
        return dtw_matrix[n, m]
    
    def cluster_patterns(self, vectors: List[np.ndarray], n_clusters: int = 5) -> Tuple[List, np.ndarray]:
        """
        对走势向量进行聚类分析（简化版，无sklearn依赖）
        
        Args:
            vectors: 240维向量列表
            n_clusters: 聚类数量
            
        Returns:
            (聚类标签, 聚类中心)
        """
        # 简化版K-Means实现
        X = np.array(vectors)
        
        # 随机选择初始中心
        np.random.seed(42)
        centers = X[np.random.choice(len(X), n_clusters, replace=False)]
        
        for _ in range(50):  # 最多50次迭代
            # 分配标签
            labels = []
            for v in X:
                distances = [np.linalg.norm(v - c) for c in centers]
                labels.append(np.argmin(distances))
            labels = np.array(labels)
            
            # 更新中心
            new_centers = []
            for i in range(n_clusters):
                cluster_points = X[labels == i]
                if len(cluster_points) > 0:
                    new_centers.append(np.mean(cluster_points, axis=0))
                else:
                    new_centers.append(centers[i])
            new_centers = np.array(new_centers)
            
            # 检查收敛
            if np.allclose(centers, new_centers):
                break
            centers = new_centers
        
        return labels, centers
    
    def analyze_single_stock(self, minute_data: pd.DataFrame) -> Dict:
        """
        分析单只股票的分钟级走势
        
        Args:
            minute_data: 分钟级数据
            
        Returns:
            分析结果字典
        """
        # 转换为向量
        vector = self.minute_to_vector(minute_data)
        
        # 提取特征
        features = self.compute_vector_features(vector)
        
        # 识别形态
        pattern_code, pattern_name = self.identify_pattern(vector, features)
        
        # 计算与各形态的相似度
        similarities = {}
        for pattern_type in ['strong_uptrend', 'strong_downtrend', 'v_reversal', 'inverted_v']:
            similarities[pattern_type] = self.similarity_to_pattern(vector, pattern_type)
        
        return {
            'vector': vector,
            'features': features,
            'pattern_code': pattern_code,
            'pattern_name': pattern_name,
            'similarities': similarities,
        }
    
    def analyze_market(self, market_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        分析整个市场的分钟级走势
        
        Args:
            market_data: 字典格式 {股票代码: 分钟级DataFrame}
            
        Returns:
            市场分析结果
        """
        results = {}
        patterns = []
        
        for code, data in market_data.items():
            if data is None or data.empty:
                continue
            
            try:
                result = self.analyze_single_stock(data)
                result['code'] = code
                results[code] = result
                patterns.append(result['pattern_code'])
            except Exception as e:
                continue
        
        # 统计形态分布
        pattern_counts = Counter(patterns)
        pattern_percentages = {k: v / len(patterns) * 100 for k, v in pattern_counts.items()}
        
        # 形态名称映射
        pattern_names = {k: self.PATTERN_NAMES.get(k, k) for k in pattern_counts.keys()}
        
        return {
            'results': results,
            'pattern_counts': dict(pattern_counts),
            'pattern_percentages': pattern_percentages,
            'pattern_names': pattern_names,
            'total_stocks': len(results),
        }


class MinuteDataLoader:
    """
    分钟级数据加载器
    
    从原始数据中提取分钟级数据
    """
    
    def __init__(self, data_dir: str):
        """
        初始化
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir
    
    def load_minute_data(self, code: str, date: str) -> pd.DataFrame:
        """
        加载指定股票指定日期的分钟数据
        
        Args:
            code: 股票代码
            date: 日期
            
        Returns:
            分钟级DataFrame
        """
        # 尝试从不同的数据源加载
        # 这里需要根据实际数据格式实现
        pass
    
    def estimate_minute_from_daily(self, daily_data: pd.DataFrame, n_minutes: int = 240) -> np.ndarray:
        """
        从日K数据估算分钟级走势（当没有真实分钟数据时使用）
        
        利用开盘价、最高价、最低价、收盘价，通过算法估算分钟级走势
        
        Args:
            daily_data: 日K数据
            n_minutes: 分钟数
            
        Returns:
            估算的240维向量
        """
        if daily_data.empty:
            return np.zeros(n_minutes)
        
        row = daily_data.iloc[-1]  # 取最新一天
        
        open_price = row['open']
        close_price = row['close']
        high_price = row['high']
        low_price = row['low']
        
        # 生成估算的分钟级走势
        # 使用随机游走+均值回归的方法
        np.random.seed(42)  # 可重复
        
        # 计算需要的参数
        price_range = high_price - low_price
        start_to_end = close_price - open_price
        
        # 生成基础随机游走
        base_changes = np.random.randn(n_minutes - 1) * (price_range / np.sqrt(n_minutes))
        
        # 调整使得最终价格匹配收盘价
        adjustment = (start_to_end - np.sum(base_changes)) / (n_minutes - 1)
        base_changes += adjustment
        
        # 生成价格序列
        prices = np.zeros(n_minutes)
        prices[0] = open_price
        for i in range(1, n_minutes):
            prices[i] = prices[i-1] + base_changes[i-1]
        
        # 确保最高价和最低价被包含
        max_idx = np.argmax(prices)
        min_idx = np.argmin(prices)
        
        if high_price > open_price:
            prices[max_idx] = max(prices[max_idx], high_price)
        if low_price < open_price:
            prices[min_idx] = min(prices[min_idx], low_price)
        
        # 归一化（以开盘价为基准）
        normalized = (prices - open_price) / open_price * 100
        
        return normalized


def demo():
    """演示函数"""
    import matplotlib.pyplot as plt
    
    print("=" * 60)
    print("分钟级走势形态分析器 - 演示")
    print("=" * 60)
    
    # 创建分析器
    analyzer = MinutePatternAnalyzer(normalize=True)
    
    # 生成模拟数据
    np.random.seed(42)
    
    # 1. 单边上涨
    uptrend = np.linspace(0, 2, 240) + np.random.randn(240) * 0.1
    print("\n[单边上涨走势]")
    result = analyzer.analyze_single_stock(pd.DataFrame({'close': uptrend}))
    print(f"  形态: {result['pattern_name']}")
    print(f"  日内收益: {result['features']['intraday_return']:.2f}%")
    print(f"  趋势斜率: {result['features']['trend_slope']:.4f}")
    
    # 2. V型反转
    v_shape = analyzer._create_v_shape(240) + np.random.randn(240) * 0.1
    print("\n[V型反转走势]")
    result = analyzer.analyze_single_stock(pd.DataFrame({'close': v_shape}))
    print(f"  形态: {result['pattern_name']}")
    print(f"  V型特征: {result['features']['v_shape']}")
    print(f"  V位置: {result['features']['v_position']:.2f}")
    
    # 3. 倒V型
    inverted_v = analyzer._create_inverted_v(240) + np.random.randn(240) * 0.1
    print("\n[倒V型走势]")
    result = analyzer.analyze_single_stock(pd.DataFrame({'close': inverted_v}))
    print(f"  形态: {result['pattern_name']}")
    print(f"  倒V特征: {result['features']['inverted_v_shape']}")
    
    # 4. 震荡整理
    consolidation = np.sin(np.linspace(0, 4*np.pi, 240)) * 0.5 + np.random.randn(240) * 0.1
    print("\n[震荡整理走势]")
    result = analyzer.analyze_single_stock(pd.DataFrame({'close': consolidation}))
    print(f"  形态: {result['pattern_name']}")
    print(f"  波动率: {result['features']['volatility']:.2f}")
    
    # 5. 相似度比较
    print("\n[走势相似度比较]")
    sim = analyzer.compare_stocks(uptrend, np.linspace(0, 1.8, 240))
    print(f"  单边上涨 vs 略弱单边上涨: 余弦相似度={sim['cosine_similarity']:.3f}")
    sim = analyzer.compare_stocks(uptrend, inverted_v)
    print(f"  单边上涨 vs 倒V型: 余弦相似度={sim['cosine_similarity']:.3f}")
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    demo()
