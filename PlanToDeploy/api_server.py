# -*- coding: utf-8 -*-
"""
股票搜索 & 云端 Runner API 服务
启动: python api_server.py
访问: http://localhost:5000
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许跨域

BASE_DIR = Path(__file__).parent


class RunnerManager:
    """管理云端轻量 Runner 的执行与日志."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current_proc: Optional[subprocess.Popen[str]] = None
        self._stop_requested: bool = False
        self._running: bool = False
        self._logs: List[str] = []
        self._max_logs: int = 2000
        self._status: Dict[str, Any] = {
            "status": "idle",
            "start_time": None,
            "end_time": None,
            "exit_code": None,
            "error": None,
            "end_date": None,
            "test": False,
            "mode": "all",
        }

    def _append_log(self, line: str) -> None:
        line = line.rstrip("\n")
        with self._lock:
            self._logs.append(line)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs :]

    def start_run(
        self,
        end_date: Optional[str] = None,
        test: bool = False,
        mode: str = "all",
    ) -> bool:
        """启动一次 Runner 执行（异步）。"""
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._logs = []
            self._stop_requested = False
            self._current_proc = None
            self._status = {
                "status": "running",
                "start_time": datetime.utcnow().isoformat() + "Z",
                "end_time": None,
                "exit_code": None,
                "error": None,
                "end_date": end_date,
                "test": bool(test),
                "mode": (mode or "all"),
            }

        thread = threading.Thread(
            target=self._run_worker,
            args=(end_date, test, mode),
            daemon=True,
        )
        thread.start()
        return True

    def _run_worker(self, end_date: Optional[str], test: bool, mode: str) -> None:
        """
        根据运行模式执行 Runner 脚本:
        - all(默认): 运行 unified_optimized_runner.py（统一优化版，读一次数据）
        - td: 仅运行 TD九底
        - xuanxue: 仅运行玄学组合
        - new: 仅运行新指标

        注意：统一优化版（unified_optimized_runner.py）读一次数据运行所有模块，
        比分别运行三个脚本快3倍
        """
        mode = (mode or "all").lower()

        py = sys.executable

        def _build_cmd(script: Path, extra_args: List[str] = None) -> List[str]:
            cmd: List[str] = [py, str(script)]
            if end_date:
                cmd.extend(["--end-date", end_date])
            if test:
                cmd.append("--test")
            if extra_args:
                cmd.extend(extra_args)
            return cmd

        unified_script = BASE_DIR / "unified_optimized_runner.py"
        index_script = BASE_DIR / "scripts" / "build_reports_index.py"

        commands: List[List[str]] = []

        # 优先使用统一优化版（读一次数据）
        if unified_script.exists() and mode == "all":
            self._append_log(f"[Runner] 使用统一优化版（读一次数据）")
            commands.append(_build_cmd(unified_script))
        elif mode == "td":
            if unified_script.exists():
                commands.append(_build_cmd(unified_script, ["--no-xuanxue", "--no-new"]))
                self._append_log(f"[Runner] 运行 TD九底（使用统一脚本）")
        elif mode == "xuanxue":
            if unified_script.exists():
                commands.append(_build_cmd(unified_script, ["--no-td", "--no-new"]))
                self._append_log(f"[Runner] 运行玄学组合（使用统一脚本）")
        elif mode == "new":
            if unified_script.exists():
                commands.append(_build_cmd(unified_script, ["--no-td", "--no-xuanxue"]))
                self._append_log(f"[Runner] 运行新指标（使用统一脚本）")
        else:
            # 回退到旧的分别运行模式
            self._append_log(f"[Runner] 未找到统一脚本，使用分别运行模式")
            daily_script = BASE_DIR / "stream_run_daily.py"
            xuanxue_script = BASE_DIR / "cloud_xuanxue_stream_runner.py"
            new_script = BASE_DIR / "cloud_new_stream_runner.py"

            if mode == "all" or mode in ("daily", "td"):
                if daily_script.exists():
                    commands.append(_build_cmd(daily_script))
            if mode == "all" or mode == "xuanxue":
                if xuanxue_script.exists():
                    commands.append(_build_cmd(xuanxue_script))
            if mode == "all" or mode == "new":
                if new_script.exists():
                    commands.append(_build_cmd(new_script))

        # 无论运行哪种模式, 最后都追加一次索引构建, 确保统一入口更新
        if index_script.exists():
            commands.append([py, str(index_script)])

        if not commands:
            self._append_log("[Runner] 未找到可执行脚本, 任务结束")
            with self._lock:
                self._status["status"] = "error"
                self._status["error"] = "no_runner_scripts"
                self._status["end_time"] = datetime.utcnow().isoformat() + "Z"
                self._running = False
            return

        overall_rc = 0
        env = os.environ.copy()
        env["NO_BROWSER"] = "1"

        for cmd in commands:
            self._append_log(f"$ {' '.join(cmd)} (cwd={BASE_DIR})")
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(BASE_DIR),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    text=True,
                )
                with self._lock:
                    self._current_proc = proc
            except Exception as exc:  # 启动失败
                self._append_log(f"[Runner] 启动失败: {exc!r}")
                overall_rc = 1
                break

            assert proc.stdout is not None
            for line in proc.stdout:
                self._append_log(line)

            return_code = proc.wait()
            with self._lock:
                self._current_proc = None

            overall_rc = return_code
            if return_code != 0:
                self._append_log(
                    f"[Runner] 命令退出码非零: {return_code}, 中断后续执行"
                )
                break

        with self._lock:
            self._status["exit_code"] = overall_rc
            if self._stop_requested:
                self._status["status"] = "stopped"
            else:
                self._status["status"] = "success" if overall_rc == 0 else "error"
            self._status["end_time"] = datetime.utcnow().isoformat() + "Z"
            self._running = False

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "status": self._status.get("status"),
                "start_time": self._status.get("start_time"),
                "end_time": self._status.get("end_time"),
                "exit_code": self._status.get("exit_code"),
                "error": self._status.get("error"),
                "end_date": self._status.get("end_date"),
                "test": bool(self._status.get("test", False)),
                "mode": self._status.get("mode", "all"),
            }

    def get_logs(self, start: int = 0) -> Dict[str, Any]:
        with self._lock:
            total = len(self._logs)
            start = max(0, min(start, total))
            lines = self._logs[start:total]
            return {
                "from": start,
                "next": total,
                "lines": lines,
                "running": self._running,
                "status": self._status.get("status"),
                "end_date": self._status.get("end_date"),
                "test": bool(self._status.get("test", False)),
                "mode": self._status.get("mode", "all"),
            }

    def stop_run(self) -> bool:
        """请求停止当前运行中的任务。"""
        proc: Optional[subprocess.Popen[str]] = None
        with self._lock:
            if not self._running:
                return False
            self._stop_requested = True
            proc = self._current_proc
            self._logs.append("[Runner] 收到停止请求, 正在尝试终止当前任务...")

        if proc is not None:
            try:
                proc.terminate()
            except Exception as exc:  # noqa: BLE001
                self._append_log(f"[Runner] 终止子进程时出错: {exc!r}")

        return True


runner_manager = RunnerManager()


def _maybe_start_auto_runner() -> None:
    """可选的每日自动执行线程（通过环境变量启用）。"""
    enabled = os.environ.get("AUTO_RUN_ENABLED", "0") == "1"
    if not enabled:
        return

    hour = int(os.environ.get("AUTO_RUN_HOUR", "3"))
    minute = int(os.environ.get("AUTO_RUN_MINUTE", "0"))

    def loop() -> None:
        while True:
            now = datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target = target + timedelta(days=1)
            sleep_seconds = (target - now).total_seconds()
            time.sleep(max(1, sleep_seconds))

            end_date = target.date().strftime("%Y-%m-%d")
            # 自动任务默认不启用 test 模式, 模式可通过 AUTO_RUN_MODE 配置
            auto_mode = os.environ.get("AUTO_RUN_MODE", "all")
            started = runner_manager.start_run(
                end_date=end_date,
                test=False,
                mode=auto_mode,
            )
            if not started:
                runner_manager._append_log(
                    f"[AutoRunner] {end_date} 已有任务在执行, 自动任务跳过"
                )

    t = threading.Thread(target=loop, daemon=True)
    t.start()

def get_latest_index_file():
    """获取最新日期的 stocks_index.csv"""
    # 云端精简版: 索引统一写入 PlanToDeploy/stocks_index/YYYY-MM-DD/stocks_index.csv
    stocks_index_dir = BASE_DIR / "stocks_index"
    
    if not stocks_index_dir.exists():
        # 向后兼容: 如果旧路径存在, 仍然尝试使用
        old_path = Path(__file__).parent / "get-data" / "data" / "stocks_index.csv"
        return old_path if old_path.exists() else None
    
    # 查找最新日期的目录
    date_dirs = [d for d in stocks_index_dir.iterdir() if d.is_dir()]
    if not date_dirs:
        return None
    
    latest_date_dir = sorted(date_dirs, key=lambda d: d.name, reverse=True)[0]
    index_file = latest_date_dir / "stocks_index.csv"
    
    return index_file if index_file.exists() else None

def load_index():
    """加载索引CSV"""
    index_file = get_latest_index_file()
    if not index_file or not index_file.exists():
        return pd.DataFrame()
    print(f"[INFO] 使用索引文件: {index_file}")
    try:
        # 优先按正常方式读取
        df = pd.read_csv(index_file, encoding="utf-8-sig")
    except pd.errors.ParserError as exc:
        # 兼容旧版 8 列索引 + 新版 9 列写入导致的列数不一致问题
        print(f"[WARN] 读取索引时发生 ParserError, 尝试兼容模式: {exc}")
        df = pd.read_csv(
            index_file,
            encoding="utf-8-sig",
            names=[
                "代码",
                "名称",
                "日期",
                "模块",
                "策略级别",
                "报告路径",
                "板块",
                "行业",
                "生成时间",
            ],
            header=None,
            engine="python",
        )
        # 早期旧数据只有「行业+生成时间」两列，新数据是「板块+行业+生成时间」三列：
        # 如果发现“行业”列长得像时间戳，就把它当成“生成时间”，并把“板块”挪到“行业”，板块留空。
        try:
            if {"板块", "行业", "生成时间"}.issubset(df.columns):
                mask = df["行业"].astype(str).str.match(r"\d{4}-\d{2}-\d{2} ")
                df.loc[mask, "生成时间"] = df.loc[mask, "行业"]
                df.loc[mask, "行业"] = df.loc[mask, "板块"]
                df.loc[mask, "板块"] = ""
        except Exception as fix_exc:
            print(f"[WARN] 修正旧索引行业/生成时间列时出错: {fix_exc}")

    # 过滤掉早期的占位记录, 避免指向不存在的报告路径
    try:
        if "策略级别" in df.columns:
            before = len(df)
            df = df[~df["策略级别"].astype(str).str.startswith("占位-")]
            removed = before - len(df)
            if removed:
                print(f"[INFO] 已过滤占位索引记录: {removed} 条")
    except Exception as filt_exc:
        print(f"[WARN] 过滤占位索引记录时出错: {filt_exc}")

    return df


@app.route("/cloud", methods=["GET"])
def cloud_index():
    """云端轻量报告统一入口页面."""
    cloud_dir = BASE_DIR / "cloud_index"
    index_file = cloud_dir / "cloud_reports_index.html"
    if not index_file.exists():
        return (
            "<h1>云端索引尚未生成</h1><p>请先运行云端 Runner 生成报告。</p>",
            404,
        )
    return send_from_directory(cloud_dir, "cloud_reports_index.html")


@app.route("/reports/<path:subpath>", methods=["GET"])
def serve_report(subpath: str):
    """通过 HTTP 提供报告文件, 供 /cloud 页面点击“查看报告”时访问."""
    # 安全限制: 仅允许访问 BASE_DIR 下的文件, 禁止跳出目录
    target = (BASE_DIR / subpath).resolve()
    try:
        target.relative_to(BASE_DIR)
    except ValueError:
        abort(404)
    if not target.exists():
        abort(404)
    return send_from_directory(target.parent, target.name)

@app.route('/api/search', methods=['GET'])
def search_stock():
    """搜索股票
    参数:
        code: 股票代码 (如: 600519)
        name: 股票名称 (如: 茅台)
        date: 日期 (如: 2026-01-30)
        module: 模块 (如: 稳步上升)
    """
    df = load_index()
    if df.empty:
        return jsonify({"error": "索引文件不存在"}), 404
    
    # 获取查询参数
    code = request.args.get('code', '').strip()
    name = request.args.get('name', '').strip()
    date = request.args.get('date', '').strip()
    module = request.args.get('module', '').strip()
    
    # 筛选
    if code:
        df = df[df['代码'].astype(str).str.contains(code, na=False)]
    if name:
        df = df[df['名称'].str.contains(name, na=False)]
    if date:
        df = df[df['日期'] == date]
    if module:
        df = df[df['模块'] == module]
    
    # 转换为JSON前，将所有 NaN/NaT 转为 None，避免前端 JSON.parse 失败
    df = df.where(pd.notna(df), None)
    results = df.to_dict('records')
    return jsonify({
        "total": len(results),
        "results": results
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    df = load_index()
    if df.empty:
        return jsonify({"error": "索引文件不存在"}), 404
    
    stats = {
        "total_records": len(df),
        "unique_stocks": df['代码'].nunique(),
        "date_range": {
            "start": df['日期'].min(),
            "end": df['日期'].max()
        },
        "modules": df['模块'].value_counts().to_dict(),
        "latest_update": df['生成时间'].max() if '生成时间' in df.columns else None
    }
    return jsonify(stats)

@app.route('/api/hot-stocks', methods=['GET'])
def get_hot_stocks():
    """获取热门股票（出现次数最多）"""
    df = load_index()
    if df.empty:
        return jsonify([])
    
    top_n = int(request.args.get('limit', 20))
    hot = df.groupby(['代码', '名称']).size().reset_index(name='出现次数')
    hot = hot.sort_values('出现次数', ascending=False).head(top_n)
    return jsonify(hot.to_dict('records'))

@app.route('/')
def index():
    """首页"""
    return """
    <h1>股票搜索API</h1>
    <ul>
        <li><a href="/api/search?code=600519">/api/search?code=600519</a></li>
        <li><a href="/api/search?name=茅台">/api/search?name=茅台</a></li>
        <li><a href="/api/stats">/api/stats</a></li>
        <li><a href="/api/hot-stocks">/api/hot-stocks</a></li>
    </ul>
    """


@app.route("/api/run-daily", methods=["POST"])
def run_daily():
    """手动触发云端轻量 Runner 执行一次。"""
    payload = request.get_json(silent=True) or {}
    end_date = str(payload.get("end_date") or "").strip() or None
    test_raw = payload.get("test", False)
    mode_raw = payload.get("mode", None)

    def _to_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        s = str(val).strip().lower()
        return s in {"1", "true", "yes", "y", "on"}

    test_flag = _to_bool(test_raw)
    mode = str(mode_raw).strip().lower() if isinstance(mode_raw, str) else None
    if not mode:
        mode = "all"

    if end_date:
        # 简单校验格式 YYYY-MM-DD
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "end_date 格式应为 YYYY-MM-DD"}), 400

    started = runner_manager.start_run(end_date=end_date, test=test_flag, mode=mode)
    if not started:
        return (
            jsonify({"status": "running", "message": "已有任务在执行中，请稍后再试"}),
            409,
        )

    return jsonify(
        {"status": "started", "end_date": end_date, "test": test_flag, "mode": mode}
    )


@app.route("/api/run-status", methods=["GET"])
def run_status():
    """查询当前 Runner 状态。"""
    return jsonify(runner_manager.get_status())


@app.route("/api/run-logs", methods=["GET"])
def run_logs():
    """增量获取 Runner 日志."""
    try:
        start = int(request.args.get("from", "0"))
    except ValueError:
        start = 0
    return jsonify(runner_manager.get_logs(start=start))


@app.route("/api/run-stop", methods=["POST"])
def run_stop():
    """手动停止当前运行中的云端 Runner。"""
    stopped = runner_manager.stop_run()
    if not stopped:
        return jsonify({"status": "idle", "message": "当前没有运行中的任务"}), 200
    return jsonify({"status": "stopping"})

if __name__ == '__main__':
    # 可选启动每日自动 Runner（通过 AUTO_RUN_ENABLED 控制）
    _maybe_start_auto_runner()

    index_file = get_latest_index_file()
    if index_file:
        print(f"索引文件: {index_file}")
    else:
        print("警告: 未找到索引文件")
    print(f"API服务启动: http://localhost:5000")
    app.run(debug=True, port=5000)
