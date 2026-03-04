@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo   股票筛选系统
echo ==========================================
echo.

:: 检查是否有分析结果
if exist "output\*\*\trend_rules_detail_*.csv" (
    set HAS_DATA=1
) else (
    set HAS_DATA=0
)

echo 请选择运行模式:
echo   1. 完整分析（获取数据+分析+生成报告）
echo   2. 快速模式（使用已有分析结果，仅重新组合和生成报告）
echo   3. 仅生成报告（需要已有组合结果）
echo   4. 退出
echo.

set /p choice=请输入选项 (1-4): 

if "%choice%"=="1" (
    echo.
    echo 正在运行完整分析...
    C:\ProgramData\Anaconda3\envs\py311\python.exe main.py
) else if "%choice%"=="2" (
    echo.
    echo 正在使用已有分析结果...
    C:\ProgramData\Anaconda3\envs\py311\python.exe main.py --skip-fetch
) else if "%choice%"=="3" (
    echo.
    echo 正在生成报告...
    C:\ProgramData\Anaconda3\envs\py311\python.exe main.py --only-report
) else if "%choice%"=="4" (
    exit /b 0
) else (
    echo 无效选项，请重新运行
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   分析完成！
echo ==========================================
echo.

:: 打开输出目录
for /f "delims=" %%i in ('dir /b /ad /o-d "output\2026-*" 2^>nul') do (
    for /f "delims=" %%j in ('dir /b /ad /o-d "output\%%i\*" 2^>nul') do (
        echo 输出目录: output\%%i\%%j
        start "" "output\%%i\%%j"
        goto :done
    )
)
:done

pause
