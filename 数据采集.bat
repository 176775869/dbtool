@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo ==========================================
echo   Doubao Data Collector (No Strategy)
echo ==========================================
echo.

echo [1/12] Getting index data...
python .\py\collectors\get_index_only.py
if errorlevel 1 (echo Index data failed! & pause & exit /b 1)

echo [2/12] Getting sector data...
python .\py\collectors\get_sector.py
if errorlevel 1 (echo Sector data failed! & pause & exit /b 1)

echo [3/12] Getting sector MA data...
python .\py\collectors\get_sector_ma.py

echo [4/12] Getting strong stock pool...
python .\py\collectors\get_qs_pool.py

echo [5/12] Getting limit-up data...
python .\py\collectors\get_limit_up.py
if errorlevel 1 (echo Limit-up data failed! & pause & exit /b 1)

echo [6/12] Getting zhaban data...
python .\py\collectors\get_zhaban.py

echo [7/12] Getting limit-down data...
python .\py\collectors\get_limit_down.py

echo [8/12] Getting top amount ^& mid-cap data...
python .\py\collectors\get_top_amount.py
python .\py\collectors\get_mid_cap.py

echo [9/12] Saving history...
python .\py\collectors\get_history.py

echo [10/12] Getting subscription data...
python .\py\collectors\get_subscription_data.py

echo [11/12] Getting market context...
python .\py\collectors\market_context_builder.py

echo [12/12] Cleaning up old data files...
python .\py\collectors\clean_data.py

echo.
echo ==========================================
echo   All tasks completed!
echo ==========================================
pause