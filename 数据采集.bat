@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo ==========================================
echo   Doubao Data Collector (No Strategy)
echo ==========================================
echo.

echo [1/10] Getting index data...
python .\py\get_index_only.py
if errorlevel 1 (echo Index data failed! & pause & exit /b 1)

echo [2/10] Getting sector data...
python .\py\get_sector.py
if errorlevel 1 (echo Sector data failed! & pause & exit /b 1)

echo [3/10] Getting sector MA data...
python .\py\get_sector_ma.py

echo [4/10] Getting strong stock pool...
python .\py\get_qs_pool.py

echo [5/10] Getting limit-up data...
python .\py\get_limit_up.py
if errorlevel 1 (echo Limit-up data failed! & pause & exit /b 1)

echo [6/10] Getting zhaban data...
python .\py\get_zhaban.py

echo [7/10] Getting limit-down data...
python .\py\get_limit_down.py

echo [8/10] "Getting top amount & mid-cap data..."
python .\py\get_top_amount.py
python .\py\get_mid_cap.py

echo [9/10] Saving history...
python .\py\get_history.py

echo [10/10] Merging replay file...
python .\py\merge_replay.py

echo.
echo ==========================================
echo   Replay file generated successfully!
echo   Please run "Strategy Builder.bat" next.
echo ==========================================
pause
echo.
echo Cleaning up temp files...
python .\py\clean_all.py