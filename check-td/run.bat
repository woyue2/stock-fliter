@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo.
echo ========================================
echo   TD分析分析系统
echo ========================================
echo.

:: 检查是否有参数
if "%1"=="" (
    echo 运行完整分析...
    python main.py
) else if "%1"=="test" (
    echo 运行测试模式...
    python main.py --test
) else if "%1"=="help" (
    python main.py --help
) else (
    python main.py %*
)

echo.
pause
