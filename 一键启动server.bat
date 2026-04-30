@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo ==========================================
echo   豆包模式 · 启动本地服务器
echo ==========================================
echo.
echo 浏览器访问: http://localhost:8080/tool.html
echo 按 Ctrl+C 停止服务器
echo ==========================================
python server.py
pause