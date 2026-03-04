---
name: Git 使用与模块管理建议
overview: 从软件工程角度肯定「按功能分文件夹」的做法；给出当前阶段最合理的 Git 用法：暂不提交未完成模块（用 .gitignore 或选择性 add），以及可选的分支策略；并列出可执行的 Git 命令与顺序。
todos: []
isProject: false
---

# Git 使用与模块管理建议

## 一、开发顺序与文件夹结构：没有问题

按功能拆成独立文件夹（get-data、check-steady-uptrend、check-trend-bottom、check-new-indicators）是常见且合理的做法：

- **边界清晰**：每个模块职责单一，便于维护和测试。
- **可独立演进**：未完成的 check-new-indicators 不影响已完成的模块。
- **与 Git 配合自然**：可以「只提交部分目录」或「用 .gitignore 排除未完成模块」，无需改结构。

结论：**不必调整开发顺序或取消「按文件夹分模块」**，继续保持即可。

---

## 二、当前阶段「不保存 check-new-indicators」的两种做法

目标：仓库里只保留已接近完成的 check-steady-uptrend、check-trend-bottom 等，暂时不把 check-new-indicators 纳入版本历史。

### 做法 A：用 .gitignore 排除整个目录（推荐）

- 在**项目根**增加或编辑 [.gitignore](.gitignore)，加入一行：
  - `check-new-indicators/`
- 效果：Git 会忽略该目录，`git status` 不会列出其下文件，`git add .` 也不会把它加进去；你本地文件照常保留，只是不进入版本库。
- 等 check-new-indicators 开发完成、愿意纳入版本时：从 .gitignore 删掉这一行，再 `git add check-new-indicators/` 并提交即可。

### 做法 B：不把 check-new-indicators 加入暂存区

- 不修改 .gitignore，每次提交时**不要**执行 `git add check-new-indicators/`，也不要 `git add .`（若根目录有 .gitignore 可 `git add .` 并靠 .gitignore 排除）。
- 若该目录**从未被提交过**：它一直是「未跟踪」状态，不会进入仓库。
- 若该目录**曾经被提交过**：需要先「从索引里移除但保留本地文件」：
  - `git rm -r --cached check-new-indicators/`
  - 再提交这次变更，之后要么用做法 A 在 .gitignore 里加上 `check-new-indicators/`，要么继续不 add 该目录。

建议：**优先用做法 A**，在根目录 .gitignore 里加 `check-new-indicators/`，省心且不易误提交。

---

## 三、当前阶段 Git 使用流程建议

### 1. 确保仓库已初始化

在项目根（stocks-fliter）执行：

```bash
git status
```

若提示「not a git repository」，则先执行：

```bash
git init
```

### 2. 根目录 .gitignore（建议内容）

在项目根新建或编辑 `.gitignore`，至少包含：

- `check-new-indicators/`   # 暂不纳入版本
- `__pycache__/`
- `*.pyc`
- `output/`   # 各模块输出目录若不想提交可统一写这里，或保留各模块子 .gitignore
- `data/`     # 若 get-data 下 data 很大且不必版本管理
- `.DS_Store`
- `*.log`
- `debug.log`

这样 `git add .` 时不会把这些和整个 check-new-indicators 加进去。

### 3. 日常提交节奏

- **只提交你希望纳入历史的文件**（在未 add check-new-indicators 或已用 .gitignore 排除的前提下）：
  - `git add get-data/ check-steady-uptrend/ check-trend-bottom/ scripts/ ...`  
  - 或 `git add .`（依赖 .gitignore 排除不需要的）
- 查看将要提交的内容：
  - `git status`
  - `git diff --cached`
- 提交：
  - `git commit -m "简短描述，如：完成稳步上升与九底模块；统一 main 运行模式参数"`

### 4. 可选：用分支区分「稳定」与「开发中」

- `main`（或 `master`）：只合并已完成的模块和通用脚本（get-data、check-steady-uptrend、check-trend-bottom、scripts、报告索引等）；不包含 check-new-indicators 的提交（或该目录被 .gitignore 忽略）。
- 若将来希望把 check-new-indicators 的提交也纳入历史，可开分支：
  - `git checkout -b feature/check-new-indicators`
  - 在该分支上从 .gitignore 中移除 `check-new-indicators/`，然后 add 并提交；开发完成后再合并回 main。

当前阶段若只有你一人开发，可以**先不分支**，只靠 .gitignore 不提交 check-new-indicators；等需要区分「发布版」与「开发版」时再引入分支。

---

## 四、若 check-new-indicators 曾被提交过

需要从 Git 索引中移除（保留本地文件），再靠 .gitignore 防止再次被加入：

1. 在项目根执行：

   - `git rm -r --cached check-new-indicators/`

2. 确保根目录 .gitignore 中有 `check-new-indicators/`。
3. 提交这次变更：

   - `git add .gitignore`
   - `git commit -m "停止跟踪 check-new-indicators，待完成后再纳入"`

之后 check-new-indicators 的本地修改不会再出现在 `git status` 中，也不会被提交。

---

## 五、小结

| 问题 | 建议 |

|------|------|

| 开发顺序 / 按文件夹分模块是否有问题？ | 没有，保持现有结构即可。 |

| 如何「不保存」check-new-indicators？ | 在根目录 .gitignore 加 `check-new-indicators/`（推荐）；或从不 add 该目录。 |

| 当前阶段 Git 怎么用？ | 根目录 .gitignore 排除不需要的目录和文件；只 add 需要版本管理的路径；小步、有意义的 commit。 |

| 是否需要分支？ | 单人、当前阶段可选；需要区分稳定/开发时再用 feature 分支。 |

按上述方式使用 Git，即可在保留「按功能分文件夹」的前提下，只把已完成的模块纳入版本控制，未完成的 check-new-indicators 留在本地、待完成后再加入仓库。