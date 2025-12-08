#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMVPN连接诊断脚本
快速检查DMVPN服务器配置和连接状态

使用方法：
  python scripts/diagnose_dmvpn.py
"""

import paramiko
import sys

# 服务器信息
SERVER_IP = "192.168.50.48"
SERVER_USER = "yuxy"
SERVER_PASS = "milesight123"

def check_dmvpn_status():
    """检查DMVPN所有组件状态"""

    print("=" * 70)
    print("DMVPN服务器诊断工具 v1.0")
    print("=" * 70)

    try:
        # SSH连接
        print(f"\n[1/7] 连接到服务器 {SERVER_IP}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        print("  [OK] SSH连接成功")

        # 检查Racoon进程
        print("\n[2/7] 检查Racoon进程...")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep '[r]acoon -f'")
        out = stdout.read().decode('utf-8')
        if "racoon -f" in out:
            print("  [OK] Racoon进程运行正常")
            print(f"    {out.strip()}")
        else:
            print("  [ERROR] Racoon进程未运行！")
            return False

        # 检查GRE隧道
        print("\n[3/7] 检查GRE隧道...")
        stdin, stdout, stderr = ssh.exec_command("ip addr show gre1")
        out = stdout.read().decode('utf-8')
        if "10.0.0.1" in out and "UP" in out:
            print("  [OK] GRE隧道已创建并运行")
            for line in out.split('\n'):
                if 'inet' in line or 'gre1' in line:
                    print(f"    {line.strip()}")
        else:
            print("  [ERROR] GRE隧道未创建或未UP！")
            return False

        # 检查OpenNHRP
        print("\n[4/7] 检查OpenNHRP...")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep '[o]pennhrp'")
        out = stdout.read().decode('utf-8')
        if "opennhrp" in out:
            print("  [OK] OpenNHRP运行正常")
            print(f"    {out.strip()}")
        else:
            print("  [ERROR] OpenNHRP未运行！")
            return False

        # 检查IPsec策略（最关键！）
        print("\n[5/7] 检查IPsec策略...")
        stdin, stdout, stderr = ssh.exec_command("setkey -DP 2>&1")
        out = stdout.read().decode('utf-8')
        if "esp/transport" in out and "gre" in out:
            print("  [OK] IPsec策略已加载")
            print("    GRE流量将通过ESP加密")
            # 显示策略详情
            for line in out.split('\n'):
                if 'gre' in line or 'esp' in line:
                    print(f"    {line.strip()}")
        else:
            print("  [ERROR] IPsec策略未加载！")
            print("    这是导致DMVPN连接失败的最常见原因")
            print("    解决方法: 运行 'cd /home && sudo sh dmvpn.sh start'")
            return False

        # 检查Racoon配置
        print("\n[6/7] 检查Racoon配置...")
        stdin, stdout, stderr = ssh.exec_command("grep -E 'remote|encryption|hash|dh_group' /etc/racoon/racoon.conf | head -20")
        out = stdout.read().decode('utf-8')
        if "remote anonymous" in out:
            print("  [OK] 使用anonymous模式（允许任意路由器IP）")
        elif "remote" in out:
            print("  [WARNING] 使用特定IP模式（可能拒绝其他路由器）")

        # 显示加密参数
        for line in out.split('\n')[:10]:
            if line.strip():
                print(f"    {line.strip()}")

        # 检查已连接的路由器
        print("\n[7/7] 检查已连接的路由器...")
        stdin, stdout, stderr = ssh.exec_command("ip neighbor show dev gre1")
        out = stdout.read().decode('utf-8')
        if out.strip():
            print("  已发现的路由器:")
            for line in out.split('\n'):
                if line.strip():
                    print(f"    {line.strip()}")

            # 尝试ping路由器
            for line in out.split('\n'):
                if 'lladdr' in line:
                    router_gre_ip = line.split()[0]
                    print(f"\n  测试连通性: ping {router_gre_ip}...")
                    stdin, stdout, stderr = ssh.exec_command(f"ping -c 2 -W 2 {router_gre_ip}")
                    ping_out = stdout.read().decode('utf-8')
                    if '2 received' in ping_out or '100% packet loss' not in ping_out:
                        print(f"    [OK] 路由器 {router_gre_ip} 可达")
                    else:
                        print(f"    [ERROR] 路由器 {router_gre_ip} 不可达")
        else:
            print("  [WARNING] 尚未发现路由器（可能还没有路由器连接）")

        # 最终结果
        print("\n" + "=" * 70)
        print("诊断完成：所有组件正常运行！")
        print("=" * 70)
        print("\n提示:")
        print("  - 如果路由器无法连接，请检查路由器端配置")
        print("  - 查看服务器日志: journalctl -u racoon -n 50 --no-pager")
        print("  - 查看路由器日志: tail -f /etc/urlog/vpn.log")

        ssh.close()
        return True

    except Exception as e:
        print(f"\n[ERROR] 错误: {str(e)}")
        return False

def main():
    """主函数"""
    success = check_dmvpn_status()

    if not success:
        print("\n" + "=" * 70)
        print("诊断发现问题！")
        print("=" * 70)
        print("\n建议修复步骤:")
        print("  1. 使用完整的DMVPN启动脚本:")
        print("     cd /home && sudo sh dmvpn.sh stop")
        print("     cd /home && sudo sh dmvpn.sh start")
        print("\n  2. 或使用DMVPN配置工具GUI:")
        print("     双击 '启动DMVPN配置工具.bat'")
        print("     点击 '重启DMVPN服务' 按钮")

        return 1

    return 0

if __name__ == "__main__":
    exit(main())
