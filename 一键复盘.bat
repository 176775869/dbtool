@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo ==========================================
echo   Doubao One-Click Replay (Data + Strategy)
echo ==========================================
echo.

echo [0/11] Cleaning up old files...
python .\py\collectors\clean_all.py

echo [1/11] Getting index data...
python .\py\collectors\get_index_only.py
if errorlevel 1 (echo Index data failed! & pause & exit /b 1)

echo [2/11] Getting sector data...
python .\py\collectors\get_sector.py
if errorlevel 1 (echo Sector data failed! & pause & exit /b 1)

echo [3/11] Getting sector MA data...
python .\py\collectors\get_sector_ma.py

echo [4/11] Getting strong stock pool...
python .\py\collectors\get_qs_pool.py

echo [5/11] Getting limit-up data...
python .\py\collectors\get_limit_up.py
if errorlevel 1 (echo Limit-up data failed! & pause & exit /b 1)

echo [6/11] Getting zhaban data...
python .\py\collectors\get_zhaban.py

echo [7/11] Getting limit-down data...
python .\py\collectors\get_limit_down.py

echo "[8/11] Getting top amount & mid-cap data..."
python .\py\collectors\get_top_amount.py
python .\py\collectors\get_mid_cap.py

echo [9/11] Saving history...
python .\py\collectors\get_history.py

echo [10/11] Merging replay file...
python .\py\collectors\merge_replay.py

echo [11/11] Generating strategy...
python .\py\core\generate_strategy.py

echo.
echo ==========================================
echo   Replay completed! Check the root folder.
echo ==========================================
pause