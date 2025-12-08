#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRE隧道自动化配置脚本
使用SSH连接到服务器并配置GRE隧道永久化
"""

import paramiko
import time
import sys
import io

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 服务器配置
SERVER_IP = "192.168.50.48"
USERNAME = "yuxy"
PASSWORD = "milesight123"
GRE_LOCAL_IP = "192.168.50.48"
GRE_TUNNEL_IP = "10.0.0.1"
GRE_KEY = "123456"
ROUTER_GRE_IP = "10.0.0.3"

# GRE配置文件内容
GRE_CONFIG = """# GRE隧道配置 - DMVPN Hub
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
"""

def execute_command(ssh, command, use_sudo=False, password=None):
    """执行SSH命令"""
    if use_sudo and not command.startswith('sudo'):
        command = f"sudo {command}"

    print(f"执行: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)

    # 如果需要sudo密码
    if use_sudo and password:
        stdin.write(password + '\n')
        stdin.flush()

    # 等待命令完成
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if output:
        print(output)
    if error and exit_status != 0:
        print(f"错误: {error}", file=sys.stderr)

    return exit_status, output, error

def main():
    print("=" * 50)
    print("GRE隧道自动化配置脚本")
    print("=" * 50)
    print(f"服务器: {SERVER_IP}")
    print(f"用户: {USERNAME}")
    print(f"GRE隧道IP: {GRE_TUNNEL_IP}")
    print("=" * 50)
    print()

    # 创建SSH客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 连接SSH
        print("步骤1: 连接SSH服务器...")
        ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)
        print("[OK] SSH连接成功\n")

        # 检查当前GRE隧道状态
        print("=" * 50)
        print("步骤2: 检查当前GRE隧道状态")
        print("=" * 50)
        exit_code, output, error = execute_command(ssh, "ip addr show gre1 2>&1 || echo 'GRE隧道不存在'")
        print()

        # 创建永久化配置文件
        print("=" * 50)
        print("步骤3: 创建永久化配置文件")
        print("=" * 50)

        # 先备份现有配置（如果存在）
        execute_command(ssh, "[ -f /etc/network/interfaces.d/gre1 ] && sudo cp /etc/network/interfaces.d/gre1 /etc/network/interfaces.d/gre1.backup.$(date +%Y%m%d_%H%M%S) || true",
                       use_sudo=True, password=PASSWORD)

        # 写入配置文件
        config_command = f"echo '{GRE_CONFIG}' | sudo tee /etc/network/interfaces.d/gre1 > /dev/null"
        execute_command(ssh, config_command, use_sudo=False, password=PASSWORD)
        print("[OK] 配置文件已创建\n")

        # 验证配置文件
        print("验证配置文件内容:")
        execute_command(ssh, "cat /etc/network/interfaces.d/gre1")
        print()

        # 清理现有GRE隧道
        print("=" * 50)
        print("步骤4: 清理现有GRE隧道（如果存在）")
        print("=" * 50)
        execute_command(ssh, "ip link set gre1 down 2>/dev/null || true", use_sudo=True, password=PASSWORD)
        execute_command(ssh, "ip tunnel del gre1 2>/dev/null || true", use_sudo=True, password=PASSWORD)
        print("[OK] 清理完成\n")

        # 创建GRE隧道
        print("=" * 50)
        print("步骤5: 创建并启动GRE隧道")
        print("=" * 50)

        execute_command(ssh, f"ip tunnel add gre1 mode gre local {GRE_LOCAL_IP} key {GRE_KEY}",
                       use_sudo=True, password=PASSWORD)
        execute_command(ssh, f"ip addr add {GRE_TUNNEL_IP}/24 dev gre1",
                       use_sudo=True, password=PASSWORD)
        execute_command(ssh, "ip link set gre1 up",
                       use_sudo=True, password=PASSWORD)
        print("[OK] GRE隧道已创建并启动\n")

        # 验证隧道状态
        print("=" * 50)
        print("步骤6: 验证GRE隧道状态")
        print("=" * 50)

        print("\n--- GRE隧道接口信息 ---")
        execute_command(ssh, "ip addr show gre1")

        print("\n--- GRE隧道详细信息 ---")
        execute_command(ssh, "ip tunnel show gre1")

        print("\n--- 路由表 ---")
        execute_command(ssh, "ip route | grep 10.0.0")
        print()

        # 测试连通性
        print("=" * 50)
        print("步骤7: 测试连通性")
        print("=" * 50)
        print(f"尝试ping路由器 {ROUTER_GRE_IP} ...")
        exit_code, output, error = execute_command(ssh, f"ping -c 3 -W 2 {ROUTER_GRE_IP}")

        if exit_code == 0:
            print(f"\n[OK] 成功! 可以ping通路由器 {ROUTER_GRE_IP}")
        else:
            print(f"\n[WARN] 无法ping通路由器 {ROUTER_GRE_IP}")
            print("可能原因:")
            print("1. 路由器DMVPN还未配置完成")
            print("2. 路由器防火墙阻止ICMP")
            print("3. 路由器GRE隧道未启动")
        print()

        # 完成
        print("=" * 50)
        print("配置完成!")
        print("=" * 50)
        print("\n配置摘要:")
        print(f"- 永久化配置文件: /etc/network/interfaces.d/gre1")
        print(f"- GRE隧道IP: {GRE_TUNNEL_IP}/24")
        print(f"- 路由器隧道IP: {ROUTER_GRE_IP}")
        print(f"- GRE密钥: {GRE_KEY}")
        print("- 系统重启后自动生效")
        print("\n管理命令:")
        print("  查看状态: ip addr show gre1")
        print("  手动启动: sudo ifup gre1")
        print("  手动停止: sudo ifdown gre1")
        print()

    except paramiko.AuthenticationException:
        print("[ERROR] SSH认证失败，请检查用户名和密码")
        sys.exit(1)
    except paramiko.SSHException as e:
        print(f"[ERROR] SSH连接错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        ssh.close()
        print("SSH连接已关闭")

if __name__ == "__main__":
    main()
