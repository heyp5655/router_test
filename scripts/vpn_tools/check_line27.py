#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速查看racoon.conf第27行"""

import paramiko

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=host, port=22, username=username, password=password)

stdin, stdout, stderr = ssh.exec_command("cat /etc/racoon/racoon.conf")
lines = stdout.read().decode('utf-8').split('\n')

print("=" * 60)
print("Racoon配置文件 - 第20-35行:")
print("=" * 60)
for i in range(19, min(35, len(lines))):
    marker = " <<<< ERROR" if i == 26 else ""
    print(f"{i+1:3d}: {lines[i]}{marker}")

ssh.close()
