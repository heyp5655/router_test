@echo off
:: 以管理员权限运行程序的启动脚本
:: 双击此文件即可自动以管理员权限启动

:: 检查是否已经是管理员权限
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Already running as Administrator
    cd /d "%~dp0"
    python app.py
    pause
) else (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && python app.py && pause' -Verb RunAs"
)
