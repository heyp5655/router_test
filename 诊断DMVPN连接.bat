@echo off
REM DMVPN 连接诊断脚本
REM 使用方法: 直接运行此脚本

echo =========================================
echo DMVPN 服务器连接诊断
echo 服务器: 192.168.50.48
echo =========================================
echo.

echo [步骤1] 检查与服务器的网络连通性...
ping -n 3 192.168.50.48
echo.

echo [步骤2] 检查 IPSec 端口 (UDP 500, 4500) 是否可达...
echo 测试 UDP 500 (IKE):
powershell -Command "Test-NetConnection -ComputerName 192.168.50.48 -Port 500"
echo.
echo 测试 UDP 4500 (NAT-T):
powershell -Command "Test-NetConnection -ComputerName 192.168.50.48 -Port 4500"
echo.

echo [步骤3] 请手动 SSH 登录服务器检查日志...
echo 命令: ssh yuxy@192.168.50.48
echo 密码: milesight123
echo.
echo 登录后执行以下命令:
echo   1. sudo systemctl status racoon
echo   2. sudo tail -50 /var/log/syslog ^| grep racoon
echo   3. sudo setkey -D    (查看 SA)
echo   4. sudo setkey -DP   (查看 SPD)
echo   5. ps aux ^| grep racoon
echo   6. netstat -uln ^| grep -E '500^|4500'
echo.

echo =========================================
echo 客户端配置检查清单:
echo =========================================
echo 1. 确认路由器 WAN IP 是否在服务器白名单中
echo 2. 确认 PSK 密钥是否匹配: 123456
echo 3. 确认 GRE 密钥是否匹配: 123456
echo 4. 确认加密算法: AES256, SHA256, modp3072
echo 5. 确认 Phase 2: AES256, HMAC-SHA256
echo.

pause
