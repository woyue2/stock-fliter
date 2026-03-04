---
name: 统一 main.py 运行模式参数
overview: 在 get-data、check-trend-bottom、check-steady-uptrend 三个模块中统一运行模式：默认无参数等同全量（--all/全部），--test 为测试 10 只，--random-test 为随机测试 50 只；保留现有高级参数供覆盖或兼容。
todos: []
isProject: false
---

# 统一 main.py 运行模式参数

## 目标规则

| 运行方式 | 含义 |
|----------|------|
| 无参数（默认） | 全量：获取/扫描全部 |
| `--test` | 测试模式：10 只股票 |
| `--random-test` | 随机测试：50 只股票 |

三个模块均采用上述规则，减少混淆；原有细粒度参数（如 `--limit`、`--sample-size`、`--all`）可保留为高级/兼容选项，但以「默认 / --test / --random-test」为主入口。

---

## 1. get-data

**当前**：[get-data/main.py](get-data/main.py) 使用 `--days`、`--sample-size`（默认 10）、`--seed`、`--resample`、`--all`。无参数时等价于「随机 10 只」。

**改动**：

- 新增 `--test`、`--random-test`。
- **默认**：无 `--test` 且无 `--random-test` 时，视为全量，即 `use_all=True`（等价于原 `--all`）。
- `--test`：`use_all=False`，`sample_size=10`，不强制 resample（沿用已有 selected_stocks 或固定种子 10 只）。
- `--random-test`：`use_all=False`，`sample_size=50`，`resample=True`（每次随机 50 只）。
- 若同时传入 `--test` 与 `--random-test`，建议约定只认其一（例如后解析覆盖，或 `--random-test` 优先），并在帮助/注释中说明。
- 保留 `--all`、`--sample-size`、`--resample` 为高级选项：显式传 `--all` 时仍强制全量；在 test/random-test 下若传 `--sample-size N` 可覆盖 10/50（可选实现，避免与「10/50」语义冲突也可不覆盖）。

**实现要点**：在 `main()` 中先根据 `args.test` / `args.random_test` 和默认推导 `use_all`、`sample_size`、`resample`，再若有 `args.all` 则强制 `use_all=True`；其余 `select_stocks` 与后续逻辑不变，仅参数来源改为上述规则。

---

## 2. check-trend-bottom

**当前**：[check-trend-bottom/main.py](check-trend-bottom/main.py) 已有 `--test`（limit=10）、`--limit`、`--skip-fetch`（别名 `--all` 表示跳过网络用本地全部）等。

**改动**：

- 新增 `--random-test`：指定时设 `limit=50`。
- 默认无参数：保持 `limit=None`（扫描全部，与「全量」一致）。
- `--test`：保持 `limit=10`。
- `--random-test` 与 `--test` 同时存在时，约定取一（例如 `--random-test` 优先，即 limit=50）。
- `--limit` 保留：若用户显式传 `--limit N`，可在解析顺序上允许覆盖由 `--test`/`--random-test` 得到的 limit（实现时二选一：要么 test/random-test 优先，要么 limit 优先；建议 test/random-test 优先，仅当未传二者时才用 `--limit`）。

**实现要点**：在参数处理处增加 `if args.random_test: limit = 50`，且与现有 `if args.test: limit = 10` 的优先级约定一致（例如先判 `--random-test` 再判 `--test`，最后 `--limit`）。

---

## 3. check-steady-uptrend

**当前**：[check-steady-uptrend/main.py](check-steady-uptrend/main.py) 仅有 `--skip-fetch`、`--only-report`、`--analyzers`、`--limit`、`--output-dir`、`--grid-horizon`、`--end-date`；无「测试/全量」的显式模式。

**改动**：

- 新增 `--test`：分析时 `limit=10`。
- 新增 `--random-test`：分析时 `limit=50`。
- 默认无参数：`limit=None`（全量扫描）。
- 保留 `--limit`：建议仅当未传 `--test`/`--random-test` 时生效，或明确文档说明「与 --test/--random-test 互斥时以 test 为先」。

**实现要点**：在 `parse_args()` 中增加 `--test`、`--random-test`；在组 `PipelineConfig` 前，若 `args.test` 则 `limit=10`，若 `args.random_test` 则 `limit=50`，否则用 `args.limit`（None 即全量）。

---

## 4. 帮助与文档

- 三个模块的 `ArgumentParser` 描述或 epilog 中统一说明：
- 无参数：全量获取/扫描
- `--test`：测试 10 只
- `--random-test`：随机测试 50 只
- 各模块 README 或 USAGE 中可补充一行说明上述三种用法，便于以后查阅。

---

## 5. 小结

| 模块 | 默认（无参数） | --test | --random-test | 备注 |
|------|----------------|--------|----------------|------|
| get-data | 全量（use_all=True） | 10 只 | 50 只随机，resample | 原默认 10 只改为全量 |
| check-trend-bottom | 全量（limit=None） | limit=10 | limit=50 | 新增 --random-test |
| check-steady-uptrend | 全量（limit=None） | limit=10 | limit=50 | 新增 --test、--random-test |

不修改各模块内部 pipeline/分析逻辑，仅在 `main.py` 的参数解析与传入 config 的 `limit`/`use_all`/`sample_size`/`resample` 上做统一与兼容。