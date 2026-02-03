# just-stock-down/_old 目录

此目录包含重构前的旧文件，保留供参考。

## 文件说明

| 文件 | 用途 |
|------|------|
| `analyze_data.py` | 旧的TD分析逻辑，已迁移到 `analyzers/td_analyzer.py` |
| `fetch_data.py` | 旧的数据获取逻辑，已迁移到 `data_loader.py` |
| `stats.py` | 旧的统计报告生成，已迁移到 `reporters/` |
| `main.py` | 旧的入口文件，已重构为新的 `main.py` + `pipeline.py` |

## 新架构

重构后的模块结构：

```
just-stock-down/
├── main.py          # 主入口
├── run.bat          # 启动脚本
├── pipeline.py      # 流程管理
├── data_loader.py   # 数据加载
├── analyzers/       # 分析器
│   ├── __init__.py
│   └── td_analyzer.py   # TD九底分析
├── reporters/       # 报告生成器
│   ├── __init__.py
│   ├── html_reporter.py
│   └── markdown_reporter.py
├── data/            # 数据目录
└── output/          # 输出目录
```

## 使用新系统

```bash
# 完整分析
python main.py

# 测试模式
python main.py --test

# 帮助
python main.py --help
```
