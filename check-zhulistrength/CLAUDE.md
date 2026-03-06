# check-zhulistrength

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

该模块用于解析通达信、同花顺等导出的数据，计算真实的主力强度（A）、散户行为（B）、资金效率（C），并进行策略验证（回测、对比）。

## 成员清单

- `calc_accuracy.py` - 计算新老策略预期命中率
- `check_columns.py` - 检查数据表字段分布
- `compare.py` - 对比原预期与新预期的差异
- `convert_and_compare.py` - 批量转换并提取表头
- `convert_ths.py` - 转换同花顺导出的特殊数据
- `run_strategy.py` - 核心逻辑，运行 A*B*C 判定规则
- `verify_data.py` - 验证公式数值正确性
- `calculator.html` - 网页版简易策略评估器
- `calculator.js` - 网页版简易策略评估器的计算逻辑
