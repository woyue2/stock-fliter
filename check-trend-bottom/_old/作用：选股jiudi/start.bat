@echo off
chcp 65001 >nul
echo ====================================
echo 三周期九底共振选股系统
echo ====================================
echo.

echo [0] 激活Conda环境...
call conda activate py311
if errorlevel 1 (
    echo 警告: 无法激活conda环境 py311
    echo 将使用当前Python环境继续...
)
echo.

echo [1] 检查依赖包...
pip show akshare >nul 2>&1
if errorlevel 1 (
    echo 检测到缺少依赖包，正在安装...
    pip install -r requirements.txt
) else (
    echo 依赖包已安装
)

echo.
echo [2] 开始扫描全市场...
echo 这将需要 15-25 分钟，请耐心等待...
echo.

python jiudi_scanner.py

echo.
echo ====================================
echo 扫描完成！请查看 output 目录中的结果文件
echo ====================================
echo.
echo 按任意键退出...
pause >nul
