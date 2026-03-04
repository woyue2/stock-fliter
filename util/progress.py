try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False
    import time
    import sys

class ProgressBar:
    """进度条上下文管理器 (tqdm 包装版)"""
    
    def __init__(self, total: int, desc: str = "", unit: str = "it"):
        self.total = total
        self.desc = desc
        self.unit = unit
        self.current = 0
        self.success = 0
        self.failed = 0
        
        if _HAS_TQDM:
            self.pbar = tqdm(total=total, desc=desc, unit=unit, leave=True)
        else:
            self.start_time = time.time()
            print(f"{desc}: 开始执行 ({total} {unit})...")
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if _HAS_TQDM:
            self.pbar.close()
        else:
            print(f"\n{self.desc}: 完成 (成功:{self.success}, 失败:{self.failed})")
        
    def update(self, n: int = 1, success: bool = True):
        self.current += n
        if success:
            self.success += n
        else:
            self.failed += n
            
        if _HAS_TQDM:
            self.pbar.update(n)
            self.pbar.set_postfix(OK=self.success, Fail=self.failed)
        else:
            # 简易 fallback
            if self.current % max(1, self.total // 10) == 0 or self.current == self.total:
                print(f"  > {self.desc}: {self.current}/{self.total} ({self.current/self.total*100:.1f}%) [OK:{self.success} Fail:{self.failed}]")
        
    def set_description(self, desc: str):
        self.desc = desc
        if _HAS_TQDM:
            self.pbar.set_description(desc)

def print_progress(*args, **kwargs):
    """已废弃，请使用 ProgressBar 类"""
    pass
