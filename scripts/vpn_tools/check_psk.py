#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查PSK配置"""

import paramiko

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=host, port=22, username=username, password=password)

print("=" * 60)
print("PSK配置检查")
print("=" * 60)

# 查看PSK文件
cmd = "sudo -S cat /etc/racoon/psk.txt"
stdin, stdout, stderr = ssh.exec_command(cmd)
stdin.write(password + '\n')
stdin.flush()
output = stdout.read().decode('utf-8', errors='ignore')

print("\nPSK配置内容:")
print(output)

# 查看文件权限
cmd = "ls -la /etc/racoon/psk.txt"
stdin, stdout, stderr = ssh.exec_command(cmd)
output = stdout.read().decode('utf-8', errors='ignore')
print("文件权限:")
print(output)

ssh.close()
