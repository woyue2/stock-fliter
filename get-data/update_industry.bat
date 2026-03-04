@echo off
chcp 65001 >nul
echo ========================================
echo 更新股票行业信息 (使用 akshare)
echo ========================================
echo.

python fetch_industry_akshare.py

echo.
echo 按任意键退出...
pause >nul

