#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用strace追踪Racoon启动过程"""

import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

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

print("=" * 70)
print("Strace追踪Racoon启动")
print("=" * 70)

# 1. 停止Racoon
print("\n[1] 停止现有Racoon...")
run_cmd("systemctl stop racoon")
run_cmd("pkill -9 racoon")
time.sleep(2)

# 2. 使用strace启动
print("\n[2] 使用strace启动Racoon（前台）...")
print("查找bind系统调用...")

cmd = "sudo -S timeout 10 strace -f -e trace=bind,socket,listen racoon -F -f /etc/racoon/racoon.conf 2>&1"
stdin, stdout, stderr = ssh.exec_command(cmd)
stdin.write(password + '\n')
stdin.flush()

# 读取输出
output = stdout.read().decode('utf-8', errors='ignore')
print("\nStrace输出:")
print(output)

# 3. 检查配置文件中的listen部分
print("\n[3] 检查配置文件listen部分...")
out, _ = run_cmd("grep -A 3 'listen' /etc/racoon/racoon.conf", use_sudo=False)
print(out)

# 4. 检查是否有racoon进程残留
out, _ = run_cmd("ps aux | grep racoon | grep -v grep", use_sudo=False)
if out.strip():
    print("\n[4] 发现Racoon进程:")
    print(out)

    # 获取PID
    import re
    match = re.search(r'root\s+(\d+)', out)
    if match:
        pid = match.group(1)
        print(f"\nPID: {pid}")

        # 查看进程打开的文件
        print(f"\n[5] 查看进程{pid}打开的文件...")
        out, _ = run_cmd(f"lsof -p {pid} | grep -E 'LISTEN|UDP'", use_sudo=False)
        if out.strip():
            print(out)
        else:
            print("没有监听任何UDP端口！")

            # 查看所有打开的文件
            print(f"\n所有打开的文件:")
            out, _ = run_cmd(f"lsof -p {pid}", use_sudo=False)
            print(out)

ssh.close()

print("\n" + "=" * 70)
