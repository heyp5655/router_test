#!/bin/bash
# DMVPN 连接诊断脚本

SERVER="192.168.50.48"
USER="yuxy"
PASS="milesight123"

echo "========================================="
echo "DMVPN 服务器连接诊断"
echo "========================================="
echo ""

echo "1. 检查 Racoon 进程..."
ssh ${USER}@${SERVER} "ps aux | grep racoon | grep -v grep"
echo ""

echo "2. 检查 IPSec 端口监听..."
ssh ${USER}@${SERVER} "netstat -uln | grep -E '500|4500'"
echo ""

echo "3. 检查 GRE 隧道..."
ssh ${USER}@${SERVER} "ip link show | grep gre"
echo ""

echo "4. 查看最近的 Racoon 日志（最后30行）..."
ssh ${USER}@${SERVER} "tail -30 /var/log/syslog | grep racoon"
echo ""

echo "5. 查看 IPSec SA（安全关联）..."
ssh ${USER}@${SERVER} "setkey -D"
echo ""

echo "6. 查看 IPSec SPD（安全策略）..."
ssh ${USER}@${SERVER} "setkey -DP"
echo ""

echo "========================================="
echo "诊断完成"
echo "========================================="
