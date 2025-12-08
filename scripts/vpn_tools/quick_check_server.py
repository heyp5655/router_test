#!/usr/bin/env python3
"""
Quick check current server config
快速检查当前服务器配置
"""

import paramiko

hostname = "192.168.50.48"
username = "yuxy"
password = "milesight123"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=10)

stdin, stdout, stderr = ssh.exec_command("echo 'milesight123' | sudo -S cat /etc/racoon/racoon.conf")
config = stdout.read().decode()

print("=" * 70)
print("Current Server Configuration")
print("=" * 70)
print(config)
print("\n" + "=" * 70)

# 检查关键参数
checks = {
    "remote anonymous": "remote anonymous" in config,
    "nat_traversal force": "nat_traversal force" in config or "nat_traversal on" in config,
    "aes 128": "aes 128" in config,
    "sha1": "sha1" in config,
    "modp3072": "modp3072" in config
}

print("Configuration Check:")
print("=" * 70)
for key, passed in checks.items():
    status = "[OK]" if passed else "[FAIL]"
    print(f"{status} {key}")

if all(checks.values()):
    print("\n[SUCCESS] Server configuration is correct!")
else:
    print("\n[WARNING] Server configuration needs fixing!")

ssh.close()
