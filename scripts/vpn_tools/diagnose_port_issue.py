#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查Racoon为什么不监听端口"""

import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

print("=" * 70)
print("Racoon端口监听问题诊断")
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

# 检查Racoon进程
print("\n[1] 检查Racoon进程...")
out, _ = run_cmd("ps aux | grep racoon | grep -v grep", use_sudo=False)
if out.strip():
    print("Racoon进程:")
    print(out)
else:
    print("没有Racoon进程运行！")

# 检查端口
print("\n[2] 检查UDP端口500和4500...")
out, _ = run_cmd("netstat -ulnp | grep -E '500|4500'", use_sudo=False)
if out.strip():
    print("端口监听:")
    print(out)
else:
    print("没有端口监听！")

# 查看最新日志
print("\n[3] 查看最新Racoon日志...")
out, _ = run_cmd("journalctl -u racoon -n 20 --no-pager", use_sudo=False)
print(out)

# 尝试手动启动Racoon（前台模式）
print("\n[4] 尝试手动前台启动Racoon...")
print("执行: racoon -F -f /etc/racoon/racoon.conf")

cmd = "sudo -S racoon -F -f /etc/racoon/racoon.conf &"
stdin, stdout, stderr = ssh.exec_command(cmd)
stdin.write(password + '\n')
stdin.flush()

time.sleep(5)

# 再次检查端口
out, _ = run_cmd("netstat -ulnp | grep -E '500|4500'", use_sudo=False)
if "500" in out:
    print("\n✓ 端口现在已监听:")
    print(out)
else:
    print("\n✗ 端口仍未监听")

# 检查进程
out, _ = run_cmd("ps aux | grep racoon | grep -v grep", use_sudo=False)
if "racoon" in out:
    print("\n✓ Racoon进程:")
    print(out)

# 查看错误
out, _ = run_cmd("journalctl -u racoon -n 10 --no-pager | grep -i error", use_sudo=False)
if out.strip():
    print("\n错误信息:")
    print(out)

ssh.close()

print("\n" + "=" * 70)
