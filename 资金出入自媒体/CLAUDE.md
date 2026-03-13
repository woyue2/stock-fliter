# check-zhulistrength

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

该模块用于解析通达信、同花顺等导出的数据，计算真实的主力强度（A）、散户行为（B）、资金效率（C），并进行策略验证（回测、对比）。

## 目录地图

- `reporters/` - 自动化报告生成脚本 (多形态报告输出)
- `templates/` - 报告或网页终端所需的前端模板/规则文件
- `playgrounds/` - 早期 UI 或逻辑实验沙盒
- `docs/` - 业务策略与计算规则文档
- `input/` - 每日数据输入源
- `output/` - 生成的报告和分析结果
- `.archive/` - 历史或废弃的临时文件

## 成员清单

- `run_daily_scan.py` - 整合版每日同花顺盘后策略运行入口 (核心执行脚本)
- `organize_files.py` - 旧版的目录整理脚本

*(注：历史计算器和转换脚本如 calc_accuracy.py 等已归档处理，此处仅保留当前最新活跃的文件。)*
