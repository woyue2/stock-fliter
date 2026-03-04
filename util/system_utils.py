import os
import platform
from typing import Optional

def get_total_memory_gb() -> float:
    """获取系统总内存 (GB)"""
    try:
        # Linux
        if os.path.exists('/proc/meminfo'):
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        # MemTotal:       16384544 kB
                        parts = line.split()
                        if len(parts) >= 2:
                            return float(parts[1]) / (1024 * 1024)
        
        # Windows / MacOS / Others using psutil if available
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            pass
            
        # Fallback for Windows using systeminfo (slow but works)
        if platform.system() == "Windows":
            # Guessing 4.0 for standard dev machines or use a faster way
            return 8.0 # Default guess
        
        # MacOS
        if platform.system() == "Darwin":
            try:
                import subprocess
                res = subprocess.check_output(['sysctl', '-n', 'hw.memsize'])
                return float(res.strip()) / (1024 ** 3)
            except Exception:
                pass
            
    except Exception:
        pass
    
    return 8.0 # Default fallback, most modern machines have at least 4-8G

def is_low_memory(threshold_gb: float = 2.5) -> bool:
    """是否为低内存系统 (默认 2.5GB 以下)"""
    return get_total_memory_gb() <= threshold_gb

def get_optimal_worker_count(max_workers: Optional[int] = None) -> int:
    """根据内存和CPU获取最优工作进程数"""
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    total_mem = get_total_memory_gb()
    
    # 规则：
    # 1. 如果内存 <= 2.2G，认为是非常低内存，强制单进程 (1)
    # 2. 如果内存 <= 4.2G，最多 2 个
    # 3. 如果内存 <= 8.2G，最多 4 个
    # 4. 否则，取 cpu_count
    
    if total_mem <= 2.2:
        workers = 1
    elif total_mem <= 4.2:
        workers = min(2, cpu_count)
    elif total_mem <= 8.2:
        workers = min(4, cpu_count)
    else:
        workers = cpu_count
        
    if max_workers is not None:
        workers = min(workers, max_workers)
        
    return max(1, workers)
