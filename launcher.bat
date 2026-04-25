@echo off
chcp 65001 >nul
echo ==========================================
echo   豆包模式复盘数据一键采集 + 清理 (v3.1)
echo ==========================================
echo.

echo [0/9] 清理历史临时文件...
python .\py\clean_all.py
if errorlevel 1 (
    echo 清理过程出错，但不影响后续采集
)
echo.

echo [1/9] 获取指数数据...
python .\py\get_index_only.py
if errorlevel 1 (
    echo 指数数据获取失败！
    pause
    exit /b 1
)
echo.

echo [2/9] 获取板块数据...
python .\py\get_sector.py
if errorlevel 1 (
    echo 板块数据获取失败！
    pause
    exit /b 1
)
echo.

echo [3/9] 获取板块均线数据...
python .\py\get_sector_ma.py
if errorlevel 1 (
    echo 板块均线获取失败！(非致命)
)
echo.

echo [4/9] 获取涨停板数据...
python .\py\get_limit_up.py
if errorlevel 1 (
    echo 涨停板数据获取失败！
    pause
    exit /b 1
)
echo.

echo [5/9] 获取炸板数据...
python .\py\get_zhaban.py
if errorlevel 1 (
    echo 炸板数据获取失败！(非致命)
)
echo.

echo [6/9] 获取跌停板数据...
python .\py\get_limit_down.py
if errorlevel 1 (
    echo 跌停板数据获取失败！(非致命)
)
echo.

echo [7/9] 获取成交额Top20和核心中军数据...
python .\py\get_top_amount.py
if errorlevel 1 (
    echo 成交额Top20获取失败！(非致命)
)
python .\py\get_mid_cap.py
if errorlevel 1 (
    echo 中军数据获取失败！(非致命)
)
echo.

echo [8/9] 保存历史记录并生成对比...
python .\py\get_history.py
if errorlevel 1 (
    echo 历史对比生成失败！(非致命)
)
echo.

echo [9/9] 整合数据文件...
python .\py\merge_replay.py
echo.

echo ==========================================
echo   采集完成！最终复盘文件在 py 目录下
echo ==========================================
pause