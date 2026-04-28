@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo ==========================================
echo   豆包模式 · 完整调试策略生成（自动拼包）
echo ==========================================
echo.
echo [1/3] 合并最新数据文件...
python .\py\collectors\merge_replay.py
echo.
echo [2/3] 清除日期锁...
if exist py\data\last_strategy_date.txt del py\data\last_strategy_date.txt
echo.
echo [3/3] 生成策略...
python .\py\core\generate_strategy.py
echo.
echo ==========================================
echo   策略已生成，文件名 strategy_*.md
echo ==========================================
pause