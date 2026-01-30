"""
结果可视化模块
绘制九底股票的K线图和TD序列
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from datetime import datetime

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class JiuDiVisualizer:
    """九底可视化器"""

    def __init__(self, output_dir: str = './output/charts'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot_stock_with_td(self, code: str, name: str, daily_df: pd.DataFrame,
                           weekly_df: pd.DataFrame, monthly_df: pd.DataFrame,
                           daily_signal: dict, weekly_signal: dict, monthly_signal: dict):
        """
        绘制股票的三个周期K线图和TD序列

        参数:
            code: 股票代码
            name: 股票名称
            daily_df/weekly_df/monthly_df: 三个周期K线数据
            daily_signal/weekly_signal/monthly_signal: 三个周期TD信号
        """
        fig, axes = plt.subplots(3, 2, figsize=(16, 12))
        fig.suptitle(f'{code} - {name} 三周期九底分析', fontsize=16, fontweight='bold')

        # 1. 日K图
        self._plot_kline_and_td(axes[0, 0], daily_df, daily_signal, '日K', 'daily')

        # 2. 日K TD序列柱状图
        self._plot_td_sequence(axes[0, 1], daily_df, daily_signal, '日K TD序列')

        # 3. 周K图
        self._plot_kline_and_td(axes[1, 0], weekly_df, weekly_signal, '周K', 'weekly')

        # 4. 周K TD序列柱状图
        self._plot_td_sequence(axes[1, 1], weekly_df, weekly_signal, '周K TD序列')

        # 5. 月K图
        self._plot_kline_and_td(axes[2, 0], monthly_df, monthly_signal, '月K', 'monthly')

        # 6. 月K TD序列柱状图
        self._plot_td_sequence(axes[2, 1], monthly_df, monthly_signal, '月K TD序列')

        plt.tight_layout()

        # 保存图片
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f'{code}_{name}_{date_str}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

        return filename

    def _plot_kline_and_td(self, ax, df: pd.DataFrame, signal: dict, title: str, period_type: str):
        """绘制K线图和九底标记"""
        if df is None or len(df) == 0:
            ax.text(0.5, 0.5, '数据不足', ha='center', va='center')
            ax.set_title(title)
            return

        # 只显示最近60根K线（日K）或相应比例
        if period_type == 'daily':
            limit = 60
        elif period_type == 'weekly':
            limit = 52
        else:
            limit = 36

        plot_df = df.tail(limit).copy()

        # 绘制K线（简化版，只画收盘价线）
        ax.plot(plot_df.index, plot_df['close'], 'b-', linewidth=1, label='收盘价')

        # 标记九底位置
        buy_seq = signal['buy_sequence'][-limit:] if len(signal['buy_sequence']) > limit else signal['buy_sequence']

        for i, seq in enumerate(buy_seq):
            if seq >= 9:
                idx = len(plot_df) - len(buy_seq) + i
                ax.scatter(plot_df.index[idx], plot_df['close'].iloc[idx],
                          color='red', s=100, marker='^', zorder=5)
                ax.text(plot_df.index[idx], plot_df['close'].iloc[idx],
                       f'九底({seq})', fontsize=8, ha='center', va='bottom')

        # 标注当前序列值
        current_seq = signal['current_buy']
        color = 'red' if current_seq >= 9 else 'orange' if current_seq >= 7 else 'gray'
        ax.text(0.02, 0.98, f'当前序列: {current_seq}', transform=ax.transAxes,
               fontsize=12, verticalalignment='top', bbox=dict(boxstyle='round',
               facecolor=color, alpha=0.3))

        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right')

        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    def _plot_td_sequence(self, ax, df: pd.DataFrame, signal: dict, title: str):
        """绘制TD序列柱状图"""
        if df is None or len(df) == 0:
            ax.text(0.5, 0.5, '数据不足', ha='center', va='center')
            ax.set_title(title)
            return

        # 限制显示数量
        limit = min(60, len(df))
        plot_df = df.tail(limit).copy()
        buy_seq = signal['buy_sequence'][-limit:] if len(signal['buy_sequence']) > limit else signal['buy_sequence']

        # 绘制柱状图
        colors = ['red' if seq >= 9 else 'orange' if seq >= 7 else 'gray' for seq in buy_seq]
        ax.bar(range(len(buy_seq)), buy_seq, color=colors, alpha=0.7)

        # 标记九底线
        ax.axhline(y=9, color='red', linestyle='--', linewidth=2, label='九底线')

        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel('K线索引')
        ax.set_ylabel('TD序列值')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

    def plot_summary_chart(self, all_stocks: list):
        """
        绘制统计摘要图表

        参数:
            all_stocks: 所有分析结果的列表
        """
        if not all_stocks:
            print("⚠️ 没有数据可绘制")
            return

        df = pd.DataFrame(all_stocks)

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('三周期九底扫描统计', fontsize=16, fontweight='bold')

        # 1. 九底周期分布
        cycles_count = df['jiudi_cycles'].value_counts().sort_index()
        axes[0, 0].bar(cycles_count.index, cycles_count.values,
                      color=['gray', 'orange', 'purple', 'red'])
        axes[0, 0].set_xlabel('九底周期数')
        axes[0, 0].set_ylabel('股票数量')
        axes[0, 0].set_title('九底周期分布')
        axes[0, 0].set_xticks([0, 1, 2, 3])
        axes[0, 0].set_xticklabels(['无九底', '单周期', '双周期', '三周期'])
        axes[0, 0].grid(True, alpha=0.3, axis='y')

        # 2. 日K序列分布
        daily_bins = [0, 3, 6, 9, 12, 999]
        daily_labels = ['0-3', '4-6', '7-9', '10-12', '>12']
        df['daily_range'] = pd.cut(df['daily_count'], bins=daily_bins, labels=daily_labels)
        daily_dist = df['daily_range'].value_counts().sort_index()

        axes[0, 1].bar(range(len(daily_dist)), daily_dist.values, color='steelblue')
        axes[0, 1].set_xticks(range(len(daily_dist)))
        axes[0, 1].set_xticklabels(daily_dist.index)
        axes[0, 1].set_xlabel('日K序列区间')
        axes[0, 1].set_ylabel('股票数量')
        axes[0, 1].set_title('日K序列分布')
        axes[0, 1].grid(True, alpha=0.3, axis='y')

        # 3. 周K序列分布
        weekly_bins = [0, 3, 6, 9, 12, 999]
        weekly_labels = ['0-3', '4-6', '7-9', '10-12', '>12']
        df['weekly_range'] = pd.cut(df['weekly_count'], bins=weekly_bins, labels=weekly_labels)
        weekly_dist = df['weekly_range'].value_counts().sort_index()

        axes[1, 0].bar(range(len(weekly_dist)), weekly_dist.values, color='darkorange')
        axes[1, 0].set_xticks(range(len(weekly_dist)))
        axes[1, 0].set_xticklabels(weekly_dist.index)
        axes[1, 0].set_xlabel('周K序列区间')
        axes[1, 0].set_ylabel('股票数量')
        axes[1, 0].set_title('周K序列分布')
        axes[1, 0].grid(True, alpha=0.3, axis='y')

        # 4. 月K序列分布
        monthly_bins = [0, 3, 6, 9, 12, 999]
        monthly_labels = ['0-3', '4-6', '7-9', '10-12', '>12']
        df['monthly_range'] = pd.cut(df['monthly_count'], bins=monthly_bins, labels=monthly_labels)
        monthly_dist = df['monthly_range'].value_counts().sort_index()

        axes[1, 1].bar(range(len(monthly_dist)), monthly_dist.values, color='crimson')
        axes[1, 1].set_xticks(range(len(monthly_dist)))
        axes[1, 1].set_xticklabels(monthly_dist.index)
        axes[1, 1].set_xlabel('月K序列区间')
        axes[1, 1].set_ylabel('股票数量')
        axes[1, 1].set_title('月K序列分布')
        axes[1, 1].grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        # 保存图片
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f'统计摘要_{date_str}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"📊 统计图表已保存：{filename}")

        return filename


if __name__ == '__main__':
    print("可视化模块已就绪")
    print("请在主程序中调用 visualizer 来生成图表")
