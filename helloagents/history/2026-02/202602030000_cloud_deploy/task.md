# 任务清单: 云部署基础工程化

目录: `helloagents/history/2026-02/202602030000_cloud_deploy/`

---

## 1. 依赖与运行环境
- [√] 1.1 在项目根目录创建 `requirements.txt`，整理 Flask、pandas、numpy、baostock、akshare 等核心运行依赖，方便本地与云端统一安装。
- [√] 1.2 在项目根目录新增 `Dockerfile`，以 gunicorn 方式运行 `api_server:app`，支持通过环境变量配置监听地址与端口。

## 2. 统一调度入口
- [√] 2.1 在项目根目录创建 `run_all_strategies.py`，顺序调度 `get-data/main.py`、`check-trend-bottom/main.py`、`check-steady-uptrend/main.py` 和 `check-new-indicators/main.py`，便于本地与云端定时任务统一调用。

## 3. 安全检查
- [√] 3.1 审查新增依赖与脚本，确认仅引入公开第三方库和本地子模块，未接入生产环境数据库、支付通道或敏感外部服务，符合 G9 安全要求。

## 4. 文档更新
- [√] 4.1 在 `helloagents/wiki/api.md` 中新增 `run_all_strategies.py` 使用说明，将统一调度脚本纳入命令行入口文档体系。

## 5. 测试
- [√] 5.1 在本地按需运行 `python -m py_compile run_all_strategies.py` 或最小化参数组合（如只启用某一个模块）进行烟囱测试，确认脚本在当前环境下可正常执行。

