#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
接口预诊断工具 (Interface Diagnostic Tool)
用于检测外部数据接口连通性、本地环境配置及依赖库状态。
"""
import sys
import time
import requests
import importlib
import contextlib
import os
from pathlib import Path
from datetime import datetime

# ANSI 颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class Logger:
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"diagnosis_{timestamp}.log"
        self.entries = []

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.entries.append(entry)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception:
            pass

_logger = Logger()

def print_status(step, status, message, elapsed=None):
    if status == "PASS":
        status_str = f"{Colors.GREEN}[PASS]{Colors.ENDC}"
        log_status = "[PASS]"
    elif status == "FAIL":
        status_str = f"{Colors.FAIL}[FAIL]{Colors.ENDC}"
        log_status = "[FAIL]"
    elif status == "WARN":
        status_str = f"{Colors.WARNING}[WARN]{Colors.ENDC}"
        log_status = "[WARN]"
    else:
        status_str = f"[{status}]"
        log_status = f"[{status}]"
    
    elapsed_str = f" ({elapsed:.2f}s)" if elapsed is not None else ""
    print(f"{status_str} {Colors.BOLD}{step}{Colors.ENDC}: {message}{elapsed_str}")
    
    # 记录到日志
    _logger.log(f"{log_status} {step}: {message}{elapsed_str}")

def check_network():
    """检查基础网络连接"""
    start = time.time()
    try:
        requests.get("https://www.baidu.com", timeout=5)
        print_status("基础网络", "PASS", "互联网连接正常", time.time() - start)
        return True
    except Exception as e:
        print_status("基础网络", "FAIL", f"无法连接互联网: {str(e)}", time.time() - start)
        return False

def check_baostock():
    """检查 BaoStock 接口"""
    start = time.time()
    try:
        bs = importlib.import_module("baostock")
        
        # 抑制 baostock 的 stdout 输出
        with contextlib.redirect_stdout(open(os.devnull, 'w')):
            lg = bs.login()
        
        if lg.error_code != "0":
            print_status("BaoStock", "FAIL", f"登录失败: {lg.error_msg}", time.time() - start)
            return False
        
        # 尝试获取一条数据
        rs = bs.query_history_k_data_plus(
            "sh.000001", "date,close", 
            start_date=(datetime.now() - importlib.import_module("datetime").timedelta(days=10)).strftime("%Y-%m-%d"), 
            end_date=datetime.now().strftime("%Y-%m-%d"), 
            frequency="d", adjustflag="3"
        )
        
        with contextlib.redirect_stdout(open(os.devnull, 'w')):
            bs.logout()
        
        if rs.error_code != "0":
            print_status("BaoStock", "FAIL", f"数据获取失败: {rs.error_msg}", time.time() - start)
            return False
            
        print_status("BaoStock", "PASS", "接口登录与数据获取正常", time.time() - start)
        return True
    except ImportError:
        print_status("BaoStock", "FAIL", "未安装 baostock 库", time.time() - start)
        return False
    except Exception as e:
        print_status("BaoStock", "FAIL", f"发生异常: {str(e)}", time.time() - start)
        return False

def check_tencent():
    """检查腾讯财经接口"""
    start = time.time()
    symbol = "sh000001"
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,1,qfq"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and symbol in data["data"]:
                print_status("腾讯接口", "PASS", "接口访问正常", time.time() - start)
                return True
            else:
                print_status("腾讯接口", "WARN", "接口返回格式异常", time.time() - start)
                return True # 视为警告但不失败
        else:
            print_status("腾讯接口", "FAIL", f"HTTP状态码: {resp.status_code}", time.time() - start)
            return False
    except Exception as e:
        print_status("腾讯接口", "FAIL", f"连接超时或错误: {str(e)}", time.time() - start)
        return False

def check_akshare():
    """检查 AkShare 接口 (如果存在)"""
    start = time.time()
    try:
        ak = importlib.import_module("akshare")
        # 尝试获取一个轻量级数据，例如上证指数 (东方财富源)
        try:
            # 使用更稳定的接口
            if hasattr(ak, 'stock_zh_index_spot_em'):
                # 获取实时行情，不带参数通常返回列表
                df = ak.stock_zh_index_spot_em()
                if not df.empty:
                    # 简单验证是否有数据
                    pass
            elif hasattr(ak, 'stock_zh_index_spot'): # 旧版本
                df = ak.stock_zh_index_spot()
            else:
                 print_status("AkShare", "WARN", "未找到合适的指数接口", time.time() - start)
                 return True

            if not df.empty:
                 print_status("AkShare", "PASS", "接口调用正常", time.time() - start)
                 return True
            else:
                 print_status("AkShare", "WARN", "数据为空", time.time() - start)
                 return True
        except Exception as e:
             print_status("AkShare", "WARN", f"接口调用报错: {str(e)}", time.time() - start)
             return False
    except ImportError:
        print_status("AkShare", "WARN", "未安装 AkShare (可选)", time.time() - start)
        return True # 可选
    except Exception as e:
        print_status("AkShare", "FAIL", f"导入或运行时异常: {str(e)}", time.time() - start)
        return False

def check_filesystem():
    """检查文件系统权限"""
    start = time.time()
    try:
        data_dir = Path("data")
        if not data_dir.exists():
            data_dir.mkdir(parents=True)
            print_status("文件系统", "PASS", "data 目录已创建", time.time() - start)
        else:
            # 尝试写入测试文件
            test_file = data_dir / "diagnosis_test.tmp"
            test_file.write_text("test")
            test_file.unlink()
            print_status("文件系统", "PASS", "读写权限正常", time.time() - start)
        return True
    except Exception as e:
        print_status("文件系统", "FAIL", f"文件读写错误: {str(e)}", time.time() - start)
        return False

def main():
    print(f"{Colors.HEADER}=== 接口预诊断工具启动 ==={Colors.ENDC}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    results = []
    
    # 交互模式或直接运行模式
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # 自动模式（CI/CD或脚本调用）
        print("-" * 30)
        results.append(check_network())
        results.append(check_filesystem())
        print("-" * 30)
        results.append(check_baostock())
        results.append(check_tencent())
        results.append(check_akshare())
        
        print("-" * 50)
        critical_success = all(results[:4])
        if critical_success:
            print(f"{Colors.GREEN}诊断完成: 核心接口正常。{Colors.ENDC}")
            sys.exit(0)
        else:
            print(f"{Colors.FAIL}诊断完成: 存在核心异常。{Colors.ENDC}")
            sys.exit(1)
    else:
        # 交互菜单模式
        while True:
            print("\n" + "="*30)
            print(f"{Colors.BOLD}请选择要执行的诊断项目:{Colors.ENDC}")
            print("1. 全面诊断 (运行所有测试)")
            print("2. 基础环境 (网络 + 文件系统)")
            print("3. BaoStock 数据接口")
            print("4. 腾讯财经数据接口")
            print("5. AkShare 数据接口")
            print("0. 退出")
            print("="*30)
            
            choice = input(f"{Colors.CYAN}请输入选项 [0-5]: {Colors.ENDC}").strip()
            
            if choice == '0':
                print("退出诊断工具。")
                break
            elif choice == '1':
                check_network()
                check_filesystem()
                check_baostock()
                check_tencent()
                check_akshare()
            elif choice == '2':
                check_network()
                check_filesystem()
            elif choice == '3':
                check_baostock()
            elif choice == '4':
                check_tencent()
            elif choice == '5':
                check_akshare()
            else:
                print(f"{Colors.WARNING}无效选项，请重新输入。{Colors.ENDC}")
            
            # 暂停一下以便用户查看结果
            if choice in ['1', '2', '3', '4', '5']:
                input(f"\n按 Enter 键继续...")

if __name__ == "__main__":
    main()
