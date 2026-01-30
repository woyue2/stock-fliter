@echo off
chcp 65001 >nul
echo ========================================
echo 玄学指标版本对比测试
echo ========================================
echo.

echo [1/3] 测试容忍版指标模块...
python -c "from mystic_indicators_tolerant import compute_all_mystic_indicators_tolerant; print('✓ 容忍版模块导入成功')"
if errorlevel 1 (
    echo ✗ 容忍版模块导入失败
    pause
    exit /b 1
)

echo [2/3] 测试趋势分析器更新...
python -c "from analyzers.trend_analyzer import TrendAnalyzer; print('✓ 趋势分析器更新成功')"
if errorlevel 1 (
    echo ✗ 趋势分析器更新失败
    pause
    exit /b 1
)

echo [3/3] 测试组合器更新...
python -c "from combiners.xuanxue_combiner import XuanxueCombiner; print('✓ 组合器更新成功'); print('✓ 组合数量:', len(XuanxueCombiner.COMBINATIONS))"
if errorlevel 1 (
    echo ✗ 组合器更新失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 所有测试通过！
echo ========================================
echo.
echo 现在可以运行完整分析：
echo   python main.py
echo.
echo 或者对比两个版本：
echo   python compare_versions.py
echo.
pause

