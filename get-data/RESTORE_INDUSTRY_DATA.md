# 恢复行业数据指南

## 当前状态
- ✅ CSV文件已添加 `industry` 列
- ✅ 已添加22只示例股票的行业信息（用于测试）
- ⚠️ 需要恢复完整的5000+只股票的行业数据

## 恢复方法

### 方法1：从Git仓库恢复（推荐）

如果你之前将数据保存在Git仓库中，请按以下步骤操作：

#### 1.1 如果是本地Git仓库
```bash
# 找到你的git仓库目录，例如：
cd /path/to/your/git/repo

# 查看文件历史
git log --all --full-history -- get-data/data/selected_stocks_all.csv

# 查看某个提交的文件内容
git show <commit-hash>:get-data/data/selected_stocks_all.csv > selected_stocks_all_backup.csv

# 或者直接恢复到某个提交
git checkout <commit-hash> -- get-data/data/selected_stocks_all.csv
```

#### 1.2 如果是远程Git仓库（GitHub/Gitee等）
```bash
# 克隆仓库
git clone <your-repo-url>

# 或者如果已经克隆过，拉取最新数据
cd /path/to/repo
git pull origin main

# 复制文件到当前项目
cp /path/to/repo/get-data/data/selected_stocks_all.csv C:\Users\Administrator\Desktop\Park\stocks-fliter\get-data\data\
```

### 方法2：使用akshare重新获取（网络正常时）

当网络连接正常时，运行以下命令：

```bash
cd C:\Users\Administrator\Desktop\Park\stocks-fliter\get-data
python fetch_industry_akshare.py
```

或者使用新创建的工具：
```bash
python get_industry_util.py
```

### 方法3：使用批处理文件
```bash
cd C:\Users\Administrator\Desktop\Park\stocks-fliter\get-data
update_industry.bat
```

## 验证数据

恢复后，验证数据是否正确：

```bash
# 查看前10行
Get-Content "C:\Users\Administrator\Desktop\Park\stocks-fliter\get-data\data\selected_stocks_all.csv" -TotalCount 10

# 统计有行业信息的股票数量
python -c "import pandas as pd; df = pd.read_csv('data/selected_stocks_all.csv'); print(f'总数: {len(df)}, 有行业: {len(df[df[\"industry\"] != \"\"])}')"
```

## HTML报告中的行业显示

恢复数据后，重新运行分析：

```bash
cd C:\Users\Administrator\Desktop\Park\stocks-fliter\check-steady-uptrend
python main.py --end-date 2026-01-30
```

HTML报告将显示：
1. **股票列表**：股票名称后显示行业，如 "浦发银行 (银行)"
2. **侧边栏统计**：显示行业分布统计表
3. **总览页面**：已勾选股票显示行业标签

## 常见问题

### Q: 如何找到我的Git仓库？
A: 可能的位置：
- GitHub/Gitee个人账号下
- 本地其他目录（搜索 `.git` 文件夹）
- 公司/团队的Git服务器

### Q: akshare获取失败怎么办？
A: 可能原因：
- 网络连接问题（检查代理设置）
- API限流（等待后重试）
- akshare版本过旧（运行 `pip install --upgrade akshare`）

### Q: 能否手动编辑CSV添加行业？
A: 可以，但不推荐。如果只有少量股票，可以手动编辑：
```csv
code,name,bs_code,industry
600000,浦发银行,sh.600000,银行
600036,招商银行,sh.600036,银行
```

## 下一步

1. **找到Git仓库位置**（如果有）
2. **恢复完整数据**
3. **重新运行分析**
4. **验证HTML报告显示正确**

## 联系方式

如果需要帮助，请提供：
- Git仓库URL或路径
- 或者网络连接问题的详细错误信息

