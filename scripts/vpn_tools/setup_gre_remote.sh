#!/bin/bash
# 快速检查和创建GRE隧道

echo "=========================================="
echo "步骤1: 检查当前GRE隧道状态"
echo "=========================================="
if ip addr show gre1 2>/dev/null; then
    echo "GRE隧道gre1已存在"
else
    echo "GRE隧道gre1不存在"
fi
echo ""

echo "=========================================="
echo "步骤2: 创建永久化配置文件"
echo "=========================================="
CONFIG_FILE="/etc/network/interfaces.d/gre1"

# 备份现有配置
if [ -f "$CONFIG_FILE" ]; then
    sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "已备份现有配置"
fi

# 创建配置文件
sudo tee "$CONFIG_FILE" > /dev/null << 'EOF'
# GRE隧道配置 - DMVPN Hub
# 创建时间: 2025-11-26
# 本地物理IP: 192.168.50.48
# 隧道IP: 10.0.0.1
# GRE密钥: 123456

auto gre1
iface gre1 inet static
    address 10.0.0.1
    netmask 255.255.255.0
    pre-up ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
    post-down ip tunnel del gre1
EOF

echo "配置文件已创建: $CONFIG_FILE"
echo ""

echo "=========================================="
echo "步骤3: 立即创建GRE隧道"
echo "=========================================="

# 删除现有隧道
if ip link show gre1 2>/dev/null; then
    echo "删除现有隧道..."
    sudo ip link set gre1 down 2>/dev/null
    sudo ip tunnel del gre1 2>/dev/null
fi

# 创建新隧道
echo "创建GRE隧道..."
sudo ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
sudo ip addr add 10.0.0.1/24 dev gre1
sudo ip link set gre1 up

echo "GRE隧道已创建并启动"
echo ""

echo "=========================================="
echo "步骤4: 验证隧道状态"
echo "=========================================="
echo "--- GRE隧道接口信息 ---"
ip addr show gre1
echo ""
echo "--- GRE隧道详细信息 ---"
ip tunnel show gre1
echo ""
echo "--- 路由表 ---"
ip route | grep 10.0.0
echo ""

echo "=========================================="
echo "步骤5: 测试连通性"
echo "=========================================="
echo "尝试ping路由器 10.0.0.3 ..."
if ping -c 3 -W 2 10.0.0.3; then
    echo "✓ 成功ping通路由器!"
else
    echo "✗ 无法ping通路由器（可能路由器还未配置完成）"
fi
echo ""

echo "=========================================="
echo "配置完成!"
echo "=========================================="
