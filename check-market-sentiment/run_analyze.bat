@echo off
chcp 65001 >nul
echo ========================================
echo   股票走势形态分析
echo ========================================
echo.
echo 正在分析最新日期的股票走势...
echo.

python analyze_market.py

echo.
echo ========================================
echo   分析完成！
echo ========================================
echo.
echo 输出文件位于 output/ 目录
echo.
pause

