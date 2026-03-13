# 🚀 ValueCellMAx - 专业复盘与量化分析系统

ValueCellMAx 是一款专为 A 股交易者设计的 **高性能复盘工具**。它结合了现代 Web 技术 (Streamlit) 与量化策略引擎，支持秒级全量扫描、多周期共振分析以及结构化复盘存证。

---

## 🌟 核心特性

- **📈 动态图表回放**: 集成 `lightweight-charts-python`，提供丝滑的 K 线交互体验。内置日期回溯功能，完美模拟实盘复盘场景。
- **🔍 TD 全量扫描引擎**: 基于多进程加速，能够快速扫描全市场股票。支持 TD 九转、TD 计数及多周期（日/周/月）深度共振分析。
- **📝 结构化复盘日记**: 逻辑存证功能。在观察 K 线的同时记录交易逻辑，笔记自动持久化到 SQLite 数据库，方便后续回溯对比。
- **⌨️ 极客式交互**: 支持键盘快捷键（左/右方向键切换日期，上/下方向键缩放图表），专为高频职业复盘优化。
- **🔗 数据同构**: 基于统一的 SQLite 数据层，与抓取模块、验证模块无缝对接。

---

## 🛠️ 技术栈

- **Frontend**: Streamlit
- **Visualization**: lightweight-charts-python (TradingView Core)
- **Data Engine**: Pandas + SQLite
- **Strategy Architecture**: 多进程并行计算 (Concurrent Futures)

---

## 📂 目录结构

```text
valueCellMAx/
├── main.py            # 应用入口，包含 UI 路由与图表控制
├── data_provider.py   # 数据访问层，提供缓存优化与数据库映射
├── CLAUDE.md          # L2 模块级文档，记录技术约束与接口
├── strategies/        # 策略引擎目录
│   └── td_engine.py   # TD 策略核心实现（多进程版）
└── README.md          # 本文档
```

---

## 🚀 快速开始

### 1. 运行应用
在项目根目录下执行：
```
哥，直接在项目根目录下运行这个命令就行：
python -m streamlit run valueCellMAx/main.py
或者如果你的环境变量里已经有 streamlit：

bash
streamlit run valueCellMAx/main.py

```

### 2. 进行全量扫描
1. 在侧边栏“选择视图”切换至 **TD 策略分析**。
2. 点击 **开始全量扫描**。系统将利用多核 CPU 动力，对全市场 5000+ 股票进行 TD 共振检测。
3. 扫描完成后，结果将展示在左侧列表。点击列表项即可在右侧实时预览 K 线。

### 3. 图表复盘模式
- 使用 **全局日期控制** 调整复盘时间。
- 使用 **方向键** 快速移动和缩放。
- 在 **逻辑存证** 区域记录当前判断，点击“存档”保存。

---

## 💡 使用技巧

- **快捷键映射**:
  - `←` / `→`: 切换至前一个/后一个交易日。
  - `↑` / `↓`: K 线图缩放（光标需在图表区域内）。
- **性能优化**: 首次扫描可能需要 1-2 分钟（取决于 CPU 核心数），后续查看已保存的结果为瞬时加载。

---

## 📜 协议与红线 (GEB Compliance)
本模块遵循 **GEB 分形文档协议**。
- 任何逻辑变更需同步更新 `CLAUDE.md` 管理的 Key Files。
- 保持 `main.py` 逻辑清晰，单函数职责单一。

---
*Created with ❤️ by Antigravity AI*
