@echo off
REM DMVPN服务器配置工具启动脚本
REM 使用pythonw.exe启动GUI，不显示CMD窗口

start "" pythonw "%~dp0scripts\vpn_tools\dmvpn_config_gui.py"
