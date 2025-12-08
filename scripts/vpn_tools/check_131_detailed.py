#!/usr/bin/env python3
"""
Check server logs for router 131 detailed analysis
检查服务器端对路由器131的详细日志
"""

import paramiko

hostname = "192.168.50.48"
username = "yuxy"
password = "milesight123"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=10)

def run_cmd(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

print("=" * 70)
print("Server Side Analysis - Router 192.168.50.131")
print("=" * 70)

# 查看路由器131的最新连接日志 (最近3分钟)
print("\n1. Server logs for 192.168.50.131 (last 30 lines):")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep '192.168.50.131' /var/log/syslog | tail -30")
print(out)

# 查看最近的错误
print("\n2. Recent errors:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep -E 'racoon.*ERROR|racoon.*failed' /var/log/syslog | grep -v '192.168.50.40' | tail -20")
print(out if out.strip() else "[No errors for other routers]")

# 检查NAT-T相关日志
print("\n3. NAT-T related logs:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep -E 'NAT|nat' /var/log/syslog | tail -15")
print(out if out.strip() else "[No NAT-T logs]")

# 当前配置确认
print("\n4. Current server configuration (key parts):")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep -A 15 'remote anonymous' /etc/racoon/racoon.conf")
print(out)

ssh.close()

print("\n" + "=" * 70)
print("Analysis:")
print("=" * 70)
print("Router 192.168.50.131 is sending packets, but negotiation times out.")
print("This suggests:")
print("  1. Router might have NAT-T enabled, but server has it disabled")
print("  2. Or router/server proposal mismatch")
print("  3. Or firewall blocking certain packets")
