# Git 使用说明（三部分）

## 一、.gitignore 里写 data/ 会不会自动遍历？

**会。** 在**项目根**的 `.gitignore` 里写一行：

```
data/
```

Git 会忽略**整个仓库里**所有名为 `data` 的目录，例如：

- `get-data/data/`
- `check-steady-uptrend/data/`
- `check-trend-bottom/data/`
- 任意子目录下的 `xxx/data/`

规则是：**没有写路径前缀的模式，会对整个仓库生效**。所以不需要写 `./get-data/data` 或 `get-data/data`，一行 `data/` 就够。

如果只想忽略根目录下的 `data`，要加前导斜杠，例如：

```
/data/
```

这样只忽略「项目根下的 data」，子目录里的 `get-data/data/` 等就不会被忽略。你当前需求是「所有 data 都不提交」，所以用 `data/` 即可。

---

## 二、git checkout -b feature/check-new-indicators 里 -b 是什么意思？

- **`git checkout <分支名>`**：切换到**已经存在**的分支。
- **`git checkout -b <分支名>`**：**新建**一个分支并立刻切换过去；`-b` 表示 “create **b**ranch”。

所以：

```bash
git checkout -b feature/check-new-indicators
```

等价于：

1. 新建分支 `feature/check-new-indicators`（基于当前所在提交）
2. 切换到该分支

之后你的提交都会记在这个新分支上，不会影响原来的分支（如 `main`）。

---

## 三、日常开发常用的 Git 流程与命令（按流程）

按「从零到提交、再到分支」的顺序列一遍，按需使用即可。

### 第一次在本项目用 Git（初始化）

```bash
cd c:\Users\Administrator\Desktop\Park\stocks-fliter
git init
```

（若已经 `git init` 过，可跳过。）

---

### 日常流程 1：看状态（每天/改代码前后）

```bash
git status
```

- 看哪些文件被改过、哪些是未跟踪的、哪些已暂存。
- 红色 = 未跟踪或已修改但未 add；绿色 = 已 add，等待 commit。

---

### 日常流程 2：把要提交的改动加入暂存区

**方式 A：只加指定目录/文件（推荐，避免误加）**

```bash
git add get-data/
git add check-steady-uptrend/
git add check-trend-bottom/
git add scripts/
git add reports_index.html
git add .gitignore
# 按需要继续 add 其他路径
```

**方式 B：加当前目录下所有改动（依赖 .gitignore 排除不想提交的）**

```bash
git add .
```

`.gitignore` 里已写 `check-new-indicators/`、`data/` 等时，这些不会被加进去。

---

### 日常流程 3：确认暂存区内容再提交

```bash
git status
git diff --cached
```

- `git diff --cached`：看「已 add、即将被提交」的差异。
- 确认无误后提交：

```bash
git commit -m "简短描述，例如：统一 main.py 运行模式参数"
```

---

### 日常流程 4：查看历史

```bash
git log
git log --oneline
```

- `--oneline` 每行一条提交，更紧凑。

---

### 日常流程 5：开新分支做功能（例如 check-new-indicators）

```bash
# 当前在 main 上，先保证工作区干净或已提交
git status

# 新建并切换到分支（-b = 创建并切换）
git checkout -b feature/check-new-indicators
```

之后正常改代码、`git add`、`git commit`，这些提交都会在 `feature/check-new-indicators` 上。

切回主分支：

```bash
git checkout main
```

再切回功能分支：

```bash
git checkout feature/check-new-indicators
```

---

### 日常流程 6：功能做完，合并回主分支

```bash
git checkout main
git merge feature/check-new-indicators
```

- 把 `feature/check-new-indicators` 的提交合并进 `main`。
- 合并完后可以删掉功能分支（可选）：  
  `git branch -d feature/check-new-indicators`

---

### 常用命令速查（按使用场景）

| 场景 | 命令 |
|------|------|
| 看状态 | `git status` |
| 看即将提交的改动 | `git diff --cached` |
| 把改动加入暂存 | `git add <路径>` 或 `git add .` |
| 提交 | `git commit -m "说明"` |
| 看提交历史 | `git log` / `git log --oneline` |
| 新建并切换分支 | `git checkout -b <分支名>` |
| 切换分支 | `git checkout <分支名>` |
| 合并分支到当前分支 | `git merge <分支名>` |
| 列出分支 | `git branch` |

---

## 小结

1. **data/**：在根 `.gitignore` 写这一行，Git 会忽略全仓库所有 `data/` 目录，不需要写 `./get-data/data`。
2. **-b**：表示「创建新分支并切换过去」；没有 `-b` 就是切换已有分支。
3. 日常流程就是：**改代码 → `git status` → `git add`（选择性）→ `git commit -m "说明"`**；要做新功能时用 `git checkout -b 分支名`，做完用 `git checkout main` 再 `git merge 分支名`。
