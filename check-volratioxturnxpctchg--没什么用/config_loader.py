# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  path: str | Path | None
# OUTPUT: dict (config)
# POS:    check-volratioxturnxpctchg/config_loader.py
# -*- coding: utf-8 -*-
"""
配置加载器

优先级：CLI --config 路径 > config/default.json
"""
from __future__ import annotations

import json
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parent / "config" / "default.json"

# 必须存在的 key（校验用）
_REQUIRED_KEYS = {"volume_ratio", "pct_chg", "price", "turnover", "amount", "vr_lookback_days"}


def load_config(path: str | Path | None = None) -> dict:
    """加载 JSON 配置，若未指定则使用 default.json"""
    target = Path(path) if path else _DEFAULT
    if not target.exists():
        raise FileNotFoundError(f"配置文件不存在: {target}")

    with target.open(encoding="utf-8") as f:
        cfg = json.load(f)

    _validate(cfg, target)
    return cfg


def _validate(cfg: dict, path: Path) -> None:
    """检查必须字段是否齐全"""
    missing = _REQUIRED_KEYS - set(cfg.keys())
    if missing:
        raise ValueError(f"配置 {path} 缺少字段: {missing}")
