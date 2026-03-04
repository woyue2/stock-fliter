@echo off
chcp 65001 >nul
echo ========================================
echo 股票搜索功能测试
echo ========================================
echo.

echo [1/3] 检查索引文件...
if exist "get-data\data\stocks_index.csv" (
    echo ✓ 索引文件存在
    for %%A in ("get-data\data\stocks_index.csv") do echo   文件大小: %%~zA 字节
) else (
    echo ✗ 索引文件不存在
    echo   请先运行分析模块生成数据
    pause
    exit /b 1
)
echo.

echo [2/3] 检查依赖...
python -c "import flask, flask_cors, pandas" 2>nul
if %errorlevel% equ 0 (
    echo ✓ 依赖已安装
) else (
    echo ✗ 缺少依赖，正在安装...
    pip install flask flask-cors pandas
)
echo.

echo [3/3] 启动API服务...
echo   访问地址: http://localhost:5000
echo   索引页面: reports_index.html
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

python api_server.py

pause

