#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查路由器192.168.50.16的加密参数proposal
分析为什么出现 "no suitable proposal found" 错误
"""

import paramiko
import re

def check_router_proposal():
    """检查路由器发送的proposal详情"""

    # 服务器连接信息
    server_ip = "192.168.50.48"
    username = "yuxy"
    password = "milesight123"

    print("=" * 70)
    print("分析路由器192.168.50.16的IPSec Proposal不匹配问题")
    print("=" * 70)

    try:
        # SSH连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, username=username, password=password, timeout=10)

        print("\n[1/5] 服务器当前配置 (应该匹配):")
        print("-" * 70)
        print("Phase 1:")
        print("  - 加密算法: AES-256")
        print("  - 认证算法: SHA256")
        print("  - DH组: modp3072 (Group 15)")
        print("  - 模式: Main Mode")
        print("\nPhase 2:")
        print("  - 加密算法: AES-256")
        print("  - 认证算法: HMAC-SHA256")

        # 查看详细的Racoon日志，寻找路由器发送的proposal
        print("\n[2/5] 查看路由器发送的加密参数...")
        print("-" * 70)

        cmd = """sudo tail -200 /var/log/syslog | grep -A 20 '192.168.50.16.*proposal' | tail -50"""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        proposal_log = stdout.read().decode('utf-8')

        if proposal_log.strip():
            print(proposal_log)
        else:
            print("未找到详细的proposal信息，查看一般错误...")

        # 查看最近的错误
        print("\n[3/5] 查看最近的Phase 1协商错误...")
        print("-" * 70)

        cmd = """sudo tail -100 /var/log/syslog | grep '192.168.50.16' | grep -E 'ERROR|proposal|phase1'"""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        errors = stdout.read().decode('utf-8')
        print(errors if errors.strip() else "无错误日志")

        # 启用详细日志
        print("\n[4/5] 临时启用racoon详细日志模式...")
        print("-" * 70)
        print("修改日志级别为debug...")

        # 备份配置
        cmd = "sudo cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.backup_debug"
        ssh.exec_command(cmd)

        # 修改日志级别
        cmd = """sudo sed -i 's/log info;/log debug;/g' /etc/racoon/racoon.conf"""
        ssh.exec_command(cmd)

        # 重启racoon
        cmd = "sudo systemctl restart racoon"
        ssh.exec_command(cmd)

        import time
        time.sleep(2)

        print("✓ Racoon已重启，日志级别设为debug")
        print("\n现在请在路由器Web界面重新尝试DMVPN连接...")
        print("等待30秒观察日志...")

        # 实时监控日志
        print("\n[5/5] 实时监控详细日志（30秒）...")
        print("-" * 70)

        # 清空之前的日志缓存
        cmd = "sudo journalctl --rotate && sudo journalctl --vacuum-time=1s"
        ssh.exec_command(cmd)

        time.sleep(30)

        # 查看详细日志
        cmd = """sudo tail -150 /var/log/syslog | grep -E '192.168.50.16|proposal|ERROR|encryption|hash|dh_group'"""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        debug_log = stdout.read().decode('utf-8')

        print(debug_log)

        # 恢复日志级别
        print("\n恢复日志级别为info...")
        cmd = """sudo sed -i 's/log debug;/log info;/g' /etc/racoon/racoon.conf"""
        ssh.exec_command(cmd)
        cmd = "sudo systemctl restart racoon"
        ssh.exec_command(cmd)

        print("\n" + "=" * 70)
        print("分析建议:")
        print("=" * 70)
        print("""
1. 检查路由器DMVPN配置中的Phase 1参数:
   - 加密算法: 必须选择 AES-256
   - 认证算法: 必须选择 SHA256 (或 SHA2-256)
   - DH组: 必须选择 Group 15 (MODP3072)
   - 模式: 必须选择 Main Mode (不要选择 Aggressive Mode)

2. 检查路由器DMVPN配置中的Phase 2参数:
   - 加密算法: 必须选择 AES-256
   - 认证算法: 必须选择 HMAC-SHA256

3. 常见错误原因:
   - 路由器选择了 AES-128 而不是 AES-256
   - 路由器选择了 SHA1 而不是 SHA256
   - 路由器选择了较低的DH组 (如 Group 2 或 Group 14)
   - 路由器使用了 Aggressive Mode 而不是 Main Mode

4. 如果路由器不支持这些高级参数，可以降低服务器要求:
   运行: python scripts/vpn_tools/change_to_aes128.py
   降级为: AES-128 + SHA1 + Group 2
""")

        ssh.close()

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_router_proposal()
