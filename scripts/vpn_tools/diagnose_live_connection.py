#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实时监控DMVPN连接失败原因"""

import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

print("=" * 70)
print("实时DMVPN连接诊断")
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

print("\n[1/6] 检查当前配置...")
print("-" * 70)
out, _ = run_cmd("cat /etc/racoon/racoon.conf", use_sudo=False)

# 提取关键配置
config_lines = out.split('\n')
in_remote = False
in_proposal = False
in_sainfo = False

print("关键配置参数:")
for line in config_lines:
    line = line.strip()

    # 检查listen块
    if 'listen {' in line or 'listen{' in line:
        print("  ⚠️  发现listen块（这会导致问题）")

    if 'remote anonymous' in line or 'remote 192.168.50' in line:
        in_remote = True
        print(f"\n  Remote配置:")

    if in_remote:
        if 'exchange_mode' in line:
            print(f"    {line}")
        elif 'my_identifier' in line:
            print(f"    {line}")
        elif 'nat_traversal' in line:
            print(f"    {line}")
        elif 'proposal {' in line:
            in_proposal = True
        elif in_proposal:
            if 'encryption_algorithm' in line:
                print(f"    {line}")
            elif 'hash_algorithm' in line:
                print(f"    {line}")
            elif 'dh_group' in line:
                print(f"    {line}")
            elif '}' in line:
                in_proposal = False
                in_remote = False

    if 'sainfo anonymous' in line:
        in_sainfo = True
        print(f"\n  SA配置:")

    if in_sainfo:
        if 'encryption_algorithm' in line:
            print(f"    {line}")
        elif 'authentication_algorithm' in line:
            print(f"    {line}")
        elif '}' in line and 'sainfo' not in line:
            in_sainfo = False

print("\n[2/6] 检查PSK配置...")
out, _ = run_cmd("cat /etc/racoon/psk.txt")
print(f"  PSK: {out.strip()}")

print("\n[3/6] 检查服务状态...")
out, _ = run_cmd("systemctl is-active racoon", use_sudo=False)
status = out.strip()
print(f"  Racoon状态: {status}")

if status != "active":
    print("  ⚠️  Racoon未运行，正在启动...")
    run_cmd("systemctl start racoon")
    time.sleep(3)

print("\n[4/6] 检查端口监听...")
out, _ = run_cmd("ss -ulnp | grep ':500' | head -2", use_sudo=False)
if "500" in out:
    print("  ✓ 端口500/4500已监听")
else:
    print("  ✗ 端口未监听 - 这是问题所在！")
    print("  正在尝试修复...")

    # 停止并重启
    run_cmd("systemctl stop racoon")
    time.sleep(2)

    # 检查是否有listen块
    out, _ = run_cmd("grep -n 'listen' /etc/racoon/racoon.conf", use_sudo=False)
    if out.strip():
        print("  发现listen块，需要移除:")
        print(f"  {out}")

print("\n[5/6] 清空旧日志...")
run_cmd("journalctl --rotate")
run_cmd("journalctl --vacuum-time=1s")

print("\n[6/6] 实时监控连接尝试（60秒）...")
print("=" * 70)
print("⚠️  现在请在路由器上:")
print("   1. 禁用DMVPN")
print("   2. 等待5秒")
print("   3. 重新启用DMVPN")
print("   4. 或者直接重启路由器")
print("=" * 70)
print("\n等待路由器连接...\n")

# 实时监控
stdin, stdout, stderr = ssh.exec_command("timeout 60 journalctl -u racoon -f --no-pager -n 0")

start_time = time.time()
error_lines = []
success_lines = []

while time.time() - start_time < 60:
    line = stdout.readline()
    if line:
        line = line.rstrip()
        print(line)

        # 收集关键信息
        if 'ERROR' in line or 'failed' in line or 'reject' in line:
            error_lines.append(line)
            print("  ^^^ ⚠️  错误信息 ^^^")

        if 'ISAKMP-SA established' in line or 'IPsec-SA established' in line:
            success_lines.append(line)
            print("  ^^^ ✅ 成功建立连接 ^^^")

        if 'no suitable proposal' in line:
            print("  ^^^ ⚠️  参数不匹配 ^^^")

    time.sleep(0.1)

print("\n" + "=" * 70)
print("监控结束")
print("=" * 70)

if success_lines:
    print("\n✅ 成功建立的连接:")
    for line in success_lines:
        print(f"  {line}")
else:
    print("\n❌ 没有成功建立连接")

if error_lines:
    print("\n❌ 发现的错误:")
    for line in error_lines[-10:]:  # 只显示最后10条错误
        print(f"  {line}")

# 最终状态检查
print("\n[最终检查] IPSec SA状态...")
out, _ = run_cmd("setkey -D | head -20")
if "esp mode" in out and "state=mature" in out:
    print("✓ 发现活跃的IPSec SA")
else:
    print("✗ 没有活跃的IPSec SA")

ssh.close()

print("\n" + "=" * 70)
