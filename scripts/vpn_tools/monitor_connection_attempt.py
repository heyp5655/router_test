#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实时监控Racoon日志 - 查看路由器连接尝试"""

import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

print("=" * 70)
print("实时监控DMVPN连接尝试")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=host, port=22, username=username, password=password)

def run_cmd(cmd, use_sudo=True):
    if use_sudo:
        full_cmd = f"sudo -S {cmd}"
        stdin, stdout, stderr = ssh.exec_command(full_cmd)
        stdin.write(password + '\n')
        stdin.flush()
    else:
        stdin, stdout, stderr = ssh.exec_command(cmd)

    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    return out, err

print("\n[1] 检查当前Racoon配置...")
print("-" * 70)
out, _ = run_cmd("cat /etc/racoon/racoon.conf", use_sudo=False)
for i, line in enumerate(out.split('\n'), 1):
    if i <= 50:  # 只显示前50行
        print(f"{i:3d}: {line}")

print("\n[2] 检查PSK配置...")
out, _ = run_cmd("cat /etc/racoon/psk.txt")
print(f"PSK: {out.strip()}")

print("\n[3] 检查端口监听...")
out, _ = run_cmd("ss -ulnp | grep -E ':(500|4500)' | grep racoon", use_sudo=False)
if out.strip():
    print("✓ 端口监听正常:")
    for line in out.split('\n')[:4]:
        if line.strip():
            print(f"  {line}")
else:
    print("✗ 端口未监听")

print("\n[4] 清空日志缓存...")
run_cmd("journalctl --rotate")
run_cmd("journalctl --vacuum-time=1s")

print("\n[5] 查看最近的Racoon日志（最近20条）...")
print("-" * 70)
out, _ = run_cmd("journalctl -u racoon -n 20 --no-pager", use_sudo=False)
print(out)

print("\n[6] 实时监控新的连接尝试（60秒）...")
print("-" * 70)
print("⚠️  现在请在路由器上启用DMVPN或重启路由器...")
print("等待连接尝试...\n")

# 实时跟踪日志
stdin, stdout, stderr = ssh.exec_command("timeout 60 journalctl -u racoon -f --no-pager")

start_time = time.time()
line_count = 0

while time.time() - start_time < 60:
    line = stdout.readline()
    if line:
        line_count += 1
        print(f"{line.rstrip()}")

        # 高亮关键信息
        if any(keyword in line for keyword in ['ERROR', 'failed', 'reject', 'respond', 'received', 'phase1']):
            print(f"  ^^^ 关键信息 ^^^")

    time.sleep(0.1)

print(f"\n监控结束，共记录 {line_count} 行日志")

print("\n[7] 检查IPSec SA状态...")
print("-" * 70)
out, _ = run_cmd("setkey -D")
if out.strip() and "esp mode" in out:
    print("✓ 发现IPSec SA:")
    print(out[:500])  # 只显示前500字符
else:
    print("✗ 没有建立IPSec SA")

print("\n[8] 检查SPD策略...")
out, _ = run_cmd("setkey -DP")
if out.strip():
    print("SPD策略:")
    print(out[:300])

ssh.close()

print("\n" + "=" * 70)
print("监控完成")
print("=" * 70)
