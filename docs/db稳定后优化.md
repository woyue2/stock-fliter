以后更新的时候get-data还需要经过csv吗？


哥，问到点子上了。这取决于我们当前的迁移进度。

1. 现在的结论 (Phase 1-2)：仍然经过 CSV
目前 

get-data/main.py
 还是先把数据写进 raw/*.csv。这样做有几个好处：

双保险：如果 SQLite 出了问题，CSV 还在，策略模块能自动 fallback 读 CSV。
零风险：您现在的采集逻辑非常复杂（含增量补齐、BaoStock 登录等），直接改写数据库的风险比较大。
可观测性：如果您想在 Excel 里看某只票的数据，CSV 依然是最方便的。
2. 未来的目标 (Phase 3)：直接写 SQLite
一旦我们确认 SQLite 运行稳定，我们可以修改 

get-data/main.py
：

改造点：找到 to_csv 的地方，改成调用 util.db.upsert_daily_rows()。
优点：
快：不需要频繁打开 5000 个文件，数据库的缓存机制（WAL模式）写入极快。
省空间：可以删掉上千个碎 CSV，只留一个大数据库。
🔧 哥，我建议现在的操作：
先保持“CSV 为主，SQLite 为辅（缓存）”的模式。

我稍后可以帮您顺手改一下 

get-data/main.py
，让它在更新完 CSV 的同时，自动把那几行新数据塞进 SQLite。这样：

数据实时同步：SQLite 里永远有最新数据。
无需手动迁移：以后您再也不用手动跑 

migrate_to_sqlite.py
 了。
万无一失：CSV 依然是您的原始备份。
您同意的话，等迁移跑完，我把 

get-data/main.py
 的“双写”逻辑加进去！