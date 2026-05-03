@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo ==========================================
echo   Doubao Data Collector (No Strategy)
echo ==========================================
echo.

echo [1/13] Getting index data...
python .\py\collectors\get_index_only.py
if errorlevel 1 (echo Index data failed! & pause & exit /b 1)

echo [2/13] Getting sector data...
python .\py\collectors\get_sector.py
if errorlevel 1 (echo Sector data failed! & pause & exit /b 1)

echo [3/13] Getting sector MA data...
python .\py\collectors\get_sector_ma.py

echo [4/13] Getting strong stock pool...
python .\py\collectors\get_qs_pool.py

echo [5/13] Getting limit-up data...
python .\py\collectors\get_limit_up.py
if errorlevel 1 (echo Limit-up data failed! & pause & exit /b 1)

echo [6/13] Getting zhaban data...
python .\py\collectors\get_zhaban.py

echo [7/13] Getting limit-down data...
python .\py\collectors\get_limit_down.py

echo [8/13] Getting top amount ^& mid-cap data...
python .\py\collectors\get_top_amount.py
python .\py\collectors\get_mid_cap.py

echo [9/13] Saving history...
python .\py\collectors\get_history.py

echo [10/13] Getting subscription data...
python .\py\collectors\get_subscription_data.py

echo [11/13] Getting market context...
python .\py\collectors\market_context_builder.py

echo [12/13] Merging replay file...
python .\py\collectors\merge_replay.py

echo [13/13] Cleaning up temp files...
python .\py\collectors\clean_all.py

echo.
echo ==========================================
echo   All tasks completed!
echo ==========================================
pause
