@echo off
chcp 65001 >nul
echo ========================================
echo 股票搜索API服务
echo ========================================
echo.
echo 正在启动服务...
echo 访问地址: http://localhost:5000
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.
python api_server.py
pause

