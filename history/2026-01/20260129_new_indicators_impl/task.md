# 任务清单 (Task)

- [ ] **Task 1: 环境与数据加载准备**
  - 创建 `check-new-indicators/data_loader.py`
  - 确保能正确导入 `util.indicators_lib`
  - 验证数据读取功能

- [ ] **Task 2: 核心分析逻辑实现**
  - 创建 `check-new-indicators/analyzer.py`
  - 实现 6 种策略的具体判断逻辑
  - 编写单元测试或简单验证脚本

- [ ] **Task 3: 报告生成模块**
  - 创建 `check-new-indicators/reporter.py`
  - 实现 DataFrame 转 CSV 功能
  - 实现 DataFrame 转 Markdown 报告功能
  - 实现 DataFrame 转 HTML 报告功能

- [ ] **Task 4: 主程序集成与测试**
  - 创建 `check-new-indicators/main.py`
  - 串联加载、分析、报告流程
  - 运行全量测试，检查输出结果

- [ ] **Task 5: 清理与文档**
  - 更新相关 README (如有)
  - 迁移方案包到 history
