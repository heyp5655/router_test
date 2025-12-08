#!/bin/bash
################################################################################
# GRE隧道永久化配置脚本
# 服务器IP: 192.168.50.48
# 用途: 为DMVPN服务器配置永久GRE隧道
################################################################################

echo "=========================================="
echo "GRE隧道永久化配置脚本"
echo "=========================================="
echo ""

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then
    echo "错误: 请使用sudo运行此脚本"
    echo "用法: sudo bash setup_gre_tunnel.sh"
    exit 1
fi

# 配置参数
GRE_INTERFACE="gre1"
GRE_LOCAL_IP="192.168.50.48"
GRE_TUNNEL_IP="10.0.0.1"
GRE_NETMASK="255.255.255.0"
GRE_KEY="123456"

echo "步骤1: 检查当前GRE隧道状态..."
if ip link show $GRE_INTERFACE &> /dev/null; then
    echo "  ✓ GRE隧道 $GRE_INTERFACE 已存在"
    ip addr show $GRE_INTERFACE
else
    echo "  ! GRE隧道 $GRE_INTERFACE 不存在，将在配置后创建"
fi
echo ""

echo "步骤2: 创建永久化配置文件..."
CONFIG_FILE="/etc/network/interfaces.d/gre1"

# 备份现有配置（如果存在）
if [ -f "$CONFIG_FILE" ]; then
    echo "  ! 发现现有配置文件，创建备份..."
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  ✓ 备份已保存"
fi

# 创建配置文件
cat > "$CONFIG_FILE" << EOF
# GRE隧道配置 - DMVPN Hub
# 创建时间: $(date)
# 本地物理IP: $GRE_LOCAL_IP
# 隧道IP: $GRE_TUNNEL_IP
# GRE密钥: $GRE_KEY

auto $GRE_INTERFACE
iface $GRE_INTERFACE inet static
    address $GRE_TUNNEL_IP
    netmask $GRE_NETMASK
    pre-up ip tunnel add $GRE_INTERFACE mode gre local $GRE_LOCAL_IP key $GRE_KEY
    post-down ip tunnel del $GRE_INTERFACE
EOF

echo "  ✓ 配置文件已创建: $CONFIG_FILE"
echo ""

echo "步骤3: 验证配置文件内容..."
cat "$CONFIG_FILE"
echo ""

echo "步骤4: 立即创建GRE隧道（不等待重启）..."
# 如果隧道已存在，先删除
if ip link show $GRE_INTERFACE &> /dev/null; then
    echo "  - 删除现有隧道..."
    ip link set $GRE_INTERFACE down 2>/dev/null
    ip tunnel del $GRE_INTERFACE 2>/dev/null
fi

# 创建新隧道
echo "  - 创建GRE隧道..."
ip tunnel add $GRE_INTERFACE mode gre local $GRE_LOCAL_IP key $GRE_KEY
ip addr add $GRE_TUNNEL_IP/24 dev $GRE_INTERFACE
ip link set $GRE_INTERFACE up

echo "  ✓ GRE隧道已创建并启动"
echo ""

echo "步骤5: 验证隧道状态..."
echo ""
echo "--- GRE隧道接口信息 ---"
ip addr show $GRE_INTERFACE
echo ""
echo "--- GRE隧道详细信息 ---"
ip tunnel show $GRE_INTERFACE
echo ""
echo "--- 路由表（10.0.0.0网段）---"
ip route | grep "10.0.0"
echo ""

echo "步骤6: 测试连通性..."
echo "  尝试ping路由器GRE IP: 10.0.0.3"
if ping -c 3 -W 2 10.0.0.3 > /dev/null 2>&1; then
    echo "  ✓ 成功! 可以ping通路由器 10.0.0.3"
else
    echo "  ✗ 无法ping通路由器 10.0.0.3"
    echo "    可能原因:"
    echo "    1. 路由器GRE隧道未配置"
    echo "    2. 路由器DMVPN连接未建立"
    echo "    3. 路由器防火墙阻止ICMP"
fi
echo ""

echo "=========================================="
echo "配置完成!"
echo "=========================================="
echo ""
echo "重要提示:"
echo "1. GRE隧道已永久化配置，重启后自动生效"
echo "2. 配置文件位置: $CONFIG_FILE"
echo "3. 隧道IP: $GRE_TUNNEL_IP"
echo "4. 路由器隧道IP: 10.0.0.3"
echo ""
echo "管理命令:"
echo "  查看隧道状态: ip addr show $GRE_INTERFACE"
echo "  手动启动隧道: sudo ifup $GRE_INTERFACE"
echo "  手动停止隧道: sudo ifdown $GRE_INTERFACE"
echo "  重启网络服务: sudo systemctl restart networking"
echo ""
echo "如果需要修改配置，请编辑: $CONFIG_FILE"
echo "修改后执行: sudo ifdown $GRE_INTERFACE && sudo ifup $GRE_INTERFACE"
echo ""
