# analyze-sector-rotation

> **板块轮动分析 · 分时板块强度合成**
> 状态：🧪 原型阶段（Prototype）

## 一句话定位

通过聚合**成员股分时数据**，合成板块的"实时强度曲线"，用于识别资金在不同板块之间的轮动路径。

---

## 核心逻辑

```
概念名 → 找成员股 → 抓各股分时 → 对齐时间轴 → 均值聚合 → 板块强度曲线
```

1. **成员寻找**：从 `get-data/data/selected_stocks_all.csv` 中按 `concepts` 字段匹配
2. **分时抓取**：调用 akshare `stock_zh_a_minute` 接口，获取 1分钟 K 线
3. **强度合成**：每只个股相对开盘价的涨幅均值 → `sector_strength`
4. **输出**：保存至 `data/sector_minutes/{板块名}_{日期}.csv`

---

## 快速使用

```bash
cd analyze-sector-rotation
python prototype_minute.py  # 默认合成"光通信"板块
```

修改脚本末尾的板块名即可替换目标：

```python
if __name__ == "__main__":
    synthesize_sector_minute("半导体", sample_limit=8)
```

---

## 目录结构

```
analyze-sector-rotation/
├── README.md                 ← 本文件
├── CLAUDE.md                 ← L2 文档（模块地图）
├── prototype_minute.py       ← 板块分时合成核心函数（原型）
└── data/
    └── sector_minutes/       ← 合成结果输出目录
```

---

## 依赖

| 依赖 | 用途 |
|------|------|
| `akshare` | 拉取 A 股分时数据 |
| `pandas` | 数据聚合与时间对齐 |
| `tqdm` | 进度显示 |
| `get-data/data/selected_stocks_all.csv` | 股票-概念映射表（需提前生成） |

---

## 演进路线

- [ ] 当前：单板块原型脚本
- [ ] 下一步：多板块批量合成，可视化轮动热力图
- [ ] 成熟后：核心函数迁移至 `util/minute_analysis/sector_synthesizer.py`，接入 `check-*` 流水线

---

## 注意事项

- 请求受 akshare/Sina 频率限制，每只股票间默认有 `0.2s` 延迟
- 仅适用于**盘中**或当日收盘后使用（分时数据为当日最新）
- 分时数据取最近 240 个时间点（约一个交易日）
