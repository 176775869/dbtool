@echo off
chcp 65001 >nul
echo ==========================================
echo   豆包模式复盘数据一键采集
echo ==========================================
echo.
echo [1/3] 获取指数数据...
python .\py\get_index_only.py
if errorlevel 1 (
    echo 指数数据获取失败！
    pause
    exit /b 1
)
echo.
echo [2/3] 获取板块数据...
python .\py\get_sector.py
if errorlevel 1 (
    echo 板块数据获取失败！
    pause
    exit /b 1
)
echo.
echo [3/3] 获取涨停板数据...
python .\py\get_limit_up.py
if errorlevel 1 (
    echo 涨停板数据获取失败！
    pause
    exit /b 1
)
echo.
echo ==========================================
echo   整合数据文件...
python .\py\merge_replay.py
echo.
echo ==========================================
echo   采集完成！复盘文件在 py 目录下
echo ==========================================
pause

python .\py\clean_debug.py