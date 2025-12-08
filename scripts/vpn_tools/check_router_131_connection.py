#!/usr/bin/env python3
"""
Check server logs for router connection attempt
检查服务器端日志看路由器连接尝试
"""

import paramiko

hostname = "192.168.50.48"
username = "yuxy"
password = "milesight123"

print("Connecting to server...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=10)

def run_cmd(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

print("=" * 70)
print("Server Side Analysis")
print("=" * 70)

# 1. 当前配置
print("\n1. Current Racoon Configuration:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S cat /etc/racoon/racoon.conf")
print(out[:1000])

# 2. 检查路由器IP (192.168.50.131) 的连接日志
print("\n2. Connection logs from router 192.168.50.131:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep '192.168.50.131' /var/log/syslog | tail -20")
print(out if out.strip() else "[No logs for 192.168.50.131]")

# 3. 最近的Racoon错误
print("\n3. Recent Racoon Errors:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep -E 'racoon.*ERROR|racoon.*failed' /var/log/syslog | tail -15")
print(out if out.strip() else "[No recent errors]")

# 4. Phase 1协商日志
print("\n4. Phase 1 Negotiation Logs (last 15):")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep -E 'phase 1|ISAKMP' /var/log/syslog | tail -15")
print(out)

# 5. 检查Racoon服务状态
print("\n5. Racoon Service Status:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S systemctl status racoon | head -15")
print(out)

# 6. 检查当前IPSec SA
print("\n6. Current IPSec SA:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S setkey -D | head -30")
if out.strip():
    print(out)
else:
    print("[No active SA]")

# 7. 检查PSK配置
print("\n7. PSK Configuration:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S cat /etc/racoon/psk.txt")
print(out)

ssh.close()
print("\nDone!")
