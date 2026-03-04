# -*- coding: utf-8 -*-
"""
通用进度条工具
"""
import sys
import time
from typing import Optional

def print_progress(current: int, total: int, start_time: float, 
                  success: int = 0, failed: int = 0, 
                  prefix: str = "", suffix: str = "",
                  bar_length: int = 30):
    """
    打印进度条 (ASCII 兼容版)
    
    Args:
        current: 当前进度
        total: 总任务数
        start_time: 开始时间戳
        success: 成功数量
        failed: 失败数量
        prefix: 前缀文本
        suffix: 后缀文本
        bar_length: 进度条长度
    """
    elapsed = time.time() - start_time
    if total > 0:
        percent = (current / total) * 100
        eta = (elapsed / current * (total - current)) if current > 0 else 0
        filled = int(bar_length * current // total)
    else:
        percent = 0
        eta = 0
        filled = 0

    # 使用 ASCII 字符以避免 Windows GBK 编码错误
    bar = "#" * filled + "-" * (bar_length - filled)
    
    # 构建状态字符串
    status_parts = []
    if success > 0 or failed > 0:
        status_parts.append(f"OK:{success}")
        status_parts.append(f"Fail:{failed}")
    
    status_str = " ".join(status_parts)
    if status_str:
        status_str = f" [{status_str}]"
    
    # 格式化输出
    # \r 回车不换行
    output = f"\r{prefix}[{bar}] {current}/{total} ({percent:.1f}%) | 耗时:{elapsed:.1f}s ETA:{eta:.1f}s{status_str} {suffix}"
    
    sys.stdout.write(output)
    sys.stdout.flush()

    # 完成时换行
    if current >= total and total > 0:
        sys.stdout.write("\n")
        sys.stdout.flush()

class ProgressBar:
    """进度条上下文管理器"""
    
    def __init__(self, total: int, desc: str = "", unit: str = "it"):
        self.total = total
        self.desc = desc
        self.unit = unit
        self.current = 0
        self.success = 0
        self.failed = 0
        self.start_time = time.time()
        
    def __enter__(self):
        self.start_time = time.time()
        self.print_bar()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.current < self.total:
            self.current = self.total
            self.print_bar()
        sys.stdout.write("\n")
        
    def update(self, n: int = 1, success: bool = True):
        self.current += n
        if success:
            self.success += n
        else:
            self.failed += n
        self.print_bar()
        
    def set_description(self, desc: str):
        self.desc = desc
        self.print_bar()
        
    def print_bar(self):
        print_progress(
            self.current, 
            self.total, 
            self.start_time, 
            self.success, 
            self.failed,
            prefix=f"{self.desc}: " if self.desc else ""
        )
