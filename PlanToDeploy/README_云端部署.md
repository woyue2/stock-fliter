# 云端轻量部署说明（PlanToDeploy 子项目）

> 目标：只把 `PlanToDeploy` 目录部署到一台 1 核 1G 的小服务器上，就能跑出  
> TD 九底(云端) / 新指标(云端) / 玄学组合(云端) + 搜索 API。

---

## 一、需要上传的内容

建议直接把 `PlanToDeploy` 整个目录打包上传，例如：

- 必备目录/文件：
  - `PlanToDeploy/stream_run_daily.py`
  - `PlanToDeploy/cloud_xuanxue_stream_runner.py`
  - `PlanToDeploy/cloud_new_stream_runner.py`
  - `PlanToDeploy/api_server.py`
  - `PlanToDeploy/util/stream_fetch.py`
  - `PlanToDeploy/util/indicators_lib.py`
  - `PlanToDeploy/check-trend-bottom/**`
  - `PlanToDeploy/check-steady-uptrend/**`
  - `PlanToDeploy/check-new-indicators/**`
  - `PlanToDeploy/selected_stocks_all.csv`
  - （可选）`PlanToDeploy/selected_stocks_all copy.csv`（小样本测试用）

> 一句话：你只要保证服务器上有一个完整的 `PlanToDeploy` 目录，就可以按下面的命令跑。

---

## 二、环境准备（云服务器）

以下假设你已经在服务器上 `cd` 到 `PlanToDeploy` 目录：

```bash
cd /path/to/PlanToDeploy

# 建议使用虚拟环境（任选）
python -m venv .venv
source .venv/bin/activate

# 安装依赖（最小集合）
pip install flask flask-cors pandas numpy requests baostock tqdm
```

> 如你在本地已经有一份 `requirements.txt`，也可以直接用：  
> `pip install -r requirements.txt`（只要这个文件一起上传即可）。

---

## 三、准备股票池文件

- 默认股票池文件：`PlanToDeploy/selected_stocks_all.csv`  
- 测试用精简股票池（可选）：`PlanToDeploy/selected_stocks_all copy.csv`

云端部署时通常做法：

1. 在本地按原流程跑一次，把最新的 `get-data/data/selected_stocks_all.csv` 拷贝到：
   - `PlanToDeploy/selected_stocks_all.csv`
2. 如需小样本测试，可以另外准备一份只包含少数股票的 CSV，命名为：
   - `PlanToDeploy/selected_stocks_all copy.csv`

---

## 四、云端每日 Runner 用法

### 4.1 云端 Daily Runner（TD 九底 + 新指标基础）

在 `PlanToDeploy` 目录下：

```bash
# 小样本验证（使用 selected_stocks_all copy.csv）
python stream_run_daily.py --test --limit 50 --days 180 --end-date 2026-02-03

# 实际跑一遍（使用 selected_stocks_all.csv）
python stream_run_daily.py --days 365 --limit 500 --end-date 2026-02-03
```

行为：
- 流式拉取日线（不写 raw 文件）；
- 生成 TD 九底(云端) 报告到 `output/cloud_td/YYYY-MM-DD/HH-MM-SS/`；
- 可选地生成新指标(云端)报告到 `output/cloud_new/...`（有命中时）；
- 自动写入索引：`stocks_index/YYYY-MM-DD/stocks_index.csv`；
- 生成索引页：`reports_index.html` / `reports_list.html`。

### 4.2 玄学组合（云端）

仍在 `PlanToDeploy` 目录下：

```bash
# 小样本：用 copy 文件，只看 50 只
python cloud_xuanxue_stream_runner.py --test --limit 50 --days 365 --end-date 2026-02-02

# 实际跑一遍（用正式股票池）
python cloud_xuanxue_stream_runner.py --days 365 --end-date 2026-02-03 --limit 500
```

行为：
- 使用流式数据 + `check-steady-uptrend` 的 Steady / Trend / Grid 全量逻辑；
- 生成玄学组合 CSV/MD/HTML 到：  
  `output/cloud_xuanxue/YYYY-MM-DD/HH-MM-SS/`；
- 把本批次的玄学结果写入索引，模块字段标记为 `玄学(云端)`。

### 4.3 新指标（独立云端 Runner）

如只想单独跑新指标(云端)，可以用：

```bash
# 小样本
python cloud_new_stream_runner.py --test --limit 50 --days 365 --end-date 2026-02-03

# 实际完整跑
python cloud_new_stream_runner.py --days 365 --end-date 2026-02-03 --limit 500
```

行为：
- 流式拉数 + `check-new-indicators` 分析；
- 输出到 `output/cloud_new/YYYY-MM-DD/HH-MM-SS/`；
- 把结果写入 `stocks_index/YYYY-MM-DD/stocks_index.csv`，模块字段标记为 `新指标(云端)`。

---

## 五、查看报告与搜索 API

### 5.1 静态 HTML 报告

- TD 九底(云端)：`output/cloud_td/YYYY-MM-DD/HH-MM-SS/summary_*.html`
- 新指标(云端)：`output/cloud_new/YYYY-MM-DD/HH-MM-SS/summary_*.html`
- 玄学(云端)：`output/cloud_xuanxue/YYYY-MM-DD/HH-MM-SS/summary_*.html`

可以直接用 `scp` 拉回本地浏览器打开，或在云端起一个简单的静态服务：

```bash
cd /path/to/PlanToDeploy
python -m http.server 8000
# 然后浏览器访问 http://<服务器IP>:8000/output/cloud_td/.../summary_....html
```

### 5.2 搜索 API + 索引页

1. 启动 API：

```bash
cd /path/to/PlanToDeploy
python api_server.py
```

2. 打开索引页（两种选择）：

- 本地下载 `PlanToDeploy/reports_index.html` 后用浏览器打开；  
- 或通过上面的 `http.server` 暴露，直接访问：  
  `http://<服务器IP>:8000/reports_index.html`

3. 索引数据：

- 云端索引 CSV：`stocks_index/YYYY-MM-DD/stocks_index.csv`  
- API 会自动选择最新日期目录下的 `stocks_index.csv` 作为数据源。

---

## 六、最小“上线 checklist”

1. 上传完整 `PlanToDeploy` 目录到服务器指定路径。  
2. 准备 Python 环境并安装依赖。  
3. 把本地最新的 `selected_stocks_all.csv` 拷贝到 `PlanToDeploy/selected_stocks_all.csv`。  
4. 在服务器上执行一遍：  
   - `python stream_run_daily.py --days 365 --limit 300`  
   - `python cloud_xuanxue_stream_runner.py --days 365 --end-date <收盘日期> --limit 300`  
5. 检查：  
   - `output/cloud_td/...`、`output/cloud_xuanxue/...`、`output/cloud_new/...` 是否有 HTML 报告；  
   - `stocks_index/<日期>/stocks_index.csv` 是否生成。  
6. 启动 `python api_server.py`，用浏览器打开 `reports_index.html`，验证搜索是否正常。  



  一个最小示例（在项目根目录新建 docker-compose.yml）可以是：

  version: "3.9"
  services:
    stock-cloud:
      build: .
      ports:
        - "5000:5000"
      environment:
        API_APP_MODULE: "PlanToDeploy.api_server:app"
        # 如需容器内自动跑每日任务再打开：
        # AUTO_RUN_ENABLED: "1"
        # AUTO_RUN_HOUR: "3"
        # AUTO_RUN_MINUTE: "0"

  然后在本地：

  - docker compose build
  - docker compose up

  起来后直接打开：

  - http://localhost:5000/cloud 看云端统一入口 + 手动运行按钮 + 日
    志
  - http://localhost:5000/api/search?... 验证搜索接口

  如果这些在本地都正常，再把同样的镜像和 compose 配置挪到服务器就
  行。