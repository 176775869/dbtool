@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo [调试] 直接生成策略（跳过数据采集）...
python .\py\core\generate_strategy.py
pause