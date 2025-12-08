#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查DMVPN服务器状态和日志"""

import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_dmvpn():
    host = "192.168.50.48"
    username = "yuxy"
    password = "milesight123"

    print("=" * 70)
    print("DMVPN服务器状态检查")
    print("=" * 70)

    try:
        # 连接SSH
        print("\n[1/7] 连接SSH...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, port=22, username=username, password=password, timeout=10)
        print("✓ SSH连接成功")

        # 检查Racoon服务状态
        print("\n[2/7] 检查Racoon服务状态...")
        stdin, stdout, stderr = ssh.exec_command("systemctl status racoon --no-pager")
        output = stdout.read().decode('utf-8', errors='ignore')

        if "active (running)" in output:
            print("✓ Racoon服务运行正常")
        else:
            print("✗ Racoon服务异常")
            for line in output.split('\n')[:15]:
                if line.strip():
                    print(f"  {line}")

        # 查看最近的Racoon日志
        print("\n[3/7] 查看Racoon系统日志（最近50条）...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command("journalctl -u racoon -n 50 --no-pager")
        output = stdout.read().decode('utf-8', errors='ignore')
        for line in output.split('\n')[-50:]:
            if line.strip():
                print(f"  {line}")

        # 查看Racoon配置文件
        print("\n[4/7] 查看当前Racoon配置...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command("cat /etc/racoon/racoon.conf")
        output = stdout.read().decode('utf-8', errors='ignore')
        for i, line in enumerate(output.split('\n'), 1):
            print(f"{i:3d}: {line}")

        # 检查IPSec SA状态
        print("\n[5/7] 检查IPSec SA状态...")
        print("-" * 70)
        cmd = "sudo -S setkey -D"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdin.write(password + '\n')
        stdin.flush()
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print("当前IPSec SA:")
            print(output)
        else:
            print("✗ 没有建立IPSec SA")

        # 检查IPSec SPD状态
        print("\n[6/7] 检查IPSec SPD策略...")
        print("-" * 70)
        cmd = "sudo -S setkey -DP"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdin.write(password + '\n')
        stdin.flush()
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print("当前IPSec SPD:")
            print(output)
        else:
            print("✗ 没有配置IPSec策略")

        # 检查GRE隧道状态
        print("\n[7/7] 检查GRE隧道状态...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command("ip addr show gre1")
        output = stdout.read().decode('utf-8', errors='ignore')
        if "gre1" in output:
            print("✓ GRE隧道已配置:")
            print(output)
        else:
            print("✗ GRE隧道未配置")

        # 检查网络接口
        print("\n检查所有GRE接口...")
        stdin, stdout, stderr = ssh.exec_command("ip link show type gre")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print(output)
        else:
            print("没有GRE接口")

        ssh.close()

        print("\n" + "=" * 70)
        print("检查完成")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ 错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    check_dmvpn()
