@echo off
chcp 65001 >nul
echo ================================
echo 选股扫描器 - 快速启动
echo ================================
echo.
echo 请选择模式:
echo 1. 快速测试 (前100只股票, 2个信号)
echo 2. 全市场扫描 (最少2个信号)
echo 3. 自定义股票池
echo 4. 测试单个股票指标
echo.

set /p choice=请输入选项 (1-4):

if "%choice%"=="1" (
    echo.
    echo 开始快速测试...
    python run_scan.py --mode test --n 100 --min-signals 2
) else if "%choice%"=="2" (
    echo.
    echo 开始全市场扫描...
    python run_scan.py --mode full --min-signals 2
) else if "%choice%"=="3" (
    echo.
    set /p stocks=请输入股票代码 (空格分隔, 如: 000001 600036):
    python run_scan.py --mode custom --stocks %stocks% --min-signals 1
) else if "%choice%"=="4" (
    echo.
    echo 测试技术指标计算...
    python test_indicator.py
) else (
    echo.
    echo 无效选项！
)

echo.
pause
