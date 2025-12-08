#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看最新Racoon日志"""

import paramiko
import sys
import io

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

    return stdout.read().decode('utf-8', errors='ignore')

print("=" * 70)
print("最新Racoon日志（最近30条）")
print("=" * 70)

out = run_cmd("journalctl -u racoon -n 30 --no-pager", use_sudo=False)
print(out)

print("\n" + "=" * 70)
print("当前配置文件")
print("=" * 70)
out = run_cmd("cat /etc/racoon/racoon.conf | head -50", use_sudo=False)
print(out)

ssh.close()
