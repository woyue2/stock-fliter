# -*- coding: utf-8 -*-
"""
接口诊断测试套件 (Interface Diagnosis Test Suite)
对应 diagnose.py 的功能，提供标准化测试用例。
"""
import unittest
import importlib
import sys
import os
from pathlib import Path

# 添加项目根目录到路径，以便导入模块
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from diagnose import check_network, check_baostock, check_tencent, check_filesystem

class TestInterfaces(unittest.TestCase):
    
    def test_01_network_connectivity(self):
        """测试基础网络连接"""
        print("\n正在执行: 基础网络连接测试...")
        result = check_network()
        self.assertTrue(result, "基础网络连接失败")

    def test_02_filesystem_permissions(self):
        """测试文件系统读写权限"""
        print("\n正在执行: 文件系统权限测试...")
        result = check_filesystem()
        self.assertTrue(result, "文件系统读写测试失败")

    def test_03_baostock_interface(self):
        """测试 BaoStock 数据接口"""
        print("\n正在执行: BaoStock 接口测试...")
        # 注意：如果网络不稳定，此测试可能失败
        result = check_baostock()
        self.assertTrue(result, "BaoStock 接口测试失败")

    def test_04_tencent_interface(self):
        """测试腾讯财经接口"""
        print("\n正在执行: 腾讯财经接口测试...")
        result = check_tencent()
        self.assertTrue(result, "腾讯财经接口测试失败")

    def test_05_cli_auto_mode(self):
        """测试 CLI 自动模式"""
        print("\n正在执行: CLI --auto 模式测试...")
        import subprocess
        cmd = [sys.executable, "diagnose.py", "--auto"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        print(f"CLI Output: {result.stdout[:200]}...") # 打印部分输出
        self.assertEqual(result.returncode, 0, "CLI 自动模式执行失败")

if __name__ == '__main__':
    unittest.main()
