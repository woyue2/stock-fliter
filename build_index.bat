@echo off
chcp 65001 >nul
echo ========================================
echo 生成报告索引
echo ========================================
echo.

python scripts/build_reports_index.py

echo.
echo ========================================
echo 完成！
echo ========================================
echo.
echo 生成的文件位于: report_index\reports_index_{日期}\
echo   - reports_index.html (带搜索功能)
echo   - reports_list.html (简单列表)
echo.
pause

