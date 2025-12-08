#!/usr/bin/env python3
"""
Quick check router 131 connection after server fix
修复服务器后快速检查路由器131连接状态
"""

import paramiko
import time

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

print("\n" + "=" * 70)
print("Checking Router 192.168.50.131 Connection")
print("=" * 70)

# 等待10秒让路由器重新连接
print("\nWaiting 10 seconds for router reconnection...")
time.sleep(10)

# 1. 检查192.168.50.131的最新日志
print("\n1. Router 192.168.50.131 logs (last 10):")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep '192.168.50.131' /var/log/syslog | tail -10")
print(out)

# 2. 检查IPSec SA
print("\n2. IPSec SA status:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S setkey -D | grep -A 3 '192.168.50.131'")
if out.strip():
    print(out)
    print("\n[SUCCESS] IPSec SA established for 192.168.50.131!")
else:
    print("[INFO] No IPSec SA for 192.168.50.131 yet")

# 3. 检查是否有成功的Phase 1
print("\n3. ISAKMP-SA status:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep '192.168.50.131.*ISAKMP-SA' /var/log/syslog | tail -5")
if out.strip():
    print(out)
    print("\n[SUCCESS] ISAKMP-SA established!")
else:
    print("[INFO] No ISAKMP-SA record yet")

# 4. 检查最新的Phase 1协商
print("\n4. Recent Phase 1 negotiations:")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep 'respond new phase 1' /var/log/syslog | tail -5")
print(out)

# 5. 检查最新的错误
print("\n5. Recent errors (if any):")
print("-" * 70)
out, _ = run_cmd("echo 'milesight123' | sudo -S grep -E 'racoon.*ERROR' /var/log/syslog | tail -5")
if out.strip():
    print(out)
else:
    print("[OK] No recent errors")

# 6. Ping测试（如果有GRE IP）
print("\n6. GRE connectivity test:")
print("-" * 70)
print("Checking if router has GRE IP...")

# 尝试ping几个可能的GRE IP
for gre_ip in ["10.0.0.5", "10.0.0.6", "10.0.0.7"]:
    out, _ = run_cmd(f"ping -c 1 -W 1 {gre_ip} 2>&1")
    if "1 received" in out or "0% packet loss" in out:
        print(f"[SUCCESS] {gre_ip} is reachable!")
        break
    elif "Network is unreachable" not in out:
        print(f"[INFO] Tried {gre_ip} - no response")

ssh.close()

print("\n" + "=" * 70)
print("Summary:")
print("=" * 70)
print("Check the logs above to see if router 192.168.50.131 connected successfully.")
print("\nIf still failing:")
print("1. Check router PSK: should have '192.168.50.48  123456'")
print("2. Check router encryption: AES-128, SHA1, MODP3072")
print("3. Check router logs for error messages")
