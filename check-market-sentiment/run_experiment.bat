@echo off
chcp 65001 >nul
echo ========================================
echo   经典走势形态实验
echo ========================================
echo.
echo 正在运行实验...
echo.

python experiment_patterns.py

echo.
echo ========================================
echo   实验完成！
echo ========================================
echo.
echo 输出文件位于 output/ 目录
echo.
pause

