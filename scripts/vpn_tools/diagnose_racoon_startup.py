#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Racoon服务诊断工具
用于诊断Racoon无法启动的问题
"""

import paramiko
import sys
import io

# 设置stdout为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def diagnose_racoon():
    """诊断Racoon服务问题"""

    # SSH连接信息
    host = "192.168.50.48"
    port = 22
    username = "yuxy"
    password = "milesight123"

    print("=" * 60)
    print("Racoon服务诊断工具")
    print("=" * 60)

    try:
        # 连接SSH
        print("\n[1/7] 连接SSH...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, port=port, username=username, password=password, timeout=10)
        print("✓ SSH连接成功")

        # 检查配置文件语法（不使用sudo）
        print("\n[2/7] 检查配置文件语法...")
        stdin, stdout, stderr = ssh.exec_command("racoon -C -f /etc/racoon/racoon.conf 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print("配置文件检查输出:")
            print(output)
        else:
            print("✓ 配置文件语法检查通过")

        # 尝试前台运行racoon查看详细错误
        print("\n[3/7] 前台运行racoon查看错误...")
        cmd = "sudo -S racoon -F -f /etc/racoon/racoon.conf -d 2>&1 &"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdin.write(password + '\n')
        stdin.flush()

        import time
        time.sleep(2)  # 等待2秒

        # 杀掉前台racoon
        stdin, stdout, stderr = ssh.exec_command("echo " + password + " | sudo -S pkill -9 racoon")

        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print("Racoon前台运行输出:")
            for line in output.split('\n')[:30]:
                if line.strip():
                    print(f"  {line}")

        # 检查端口占用
        print("\n[4/7] 检查端口占用...")
        stdin, stdout, stderr = ssh.exec_command("netstat -tuln | grep -E ':(500|4500)\\s'")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print("⚠ 端口已被占用:")
            print(output)
        else:
            print("✓ 端口500和4500未被占用")

        # 检查是否有racoon进程
        print("\n[5/7] 检查racoon进程...")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep racoon | grep -v grep")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print("⚠ 发现racoon进程:")
            print(output)
        else:
            print("✓ 没有racoon进程运行")

        # 查看配置文件内容
        print("\n[6/7] 查看配置文件内容...")
        stdin, stdout, stderr = ssh.exec_command("cat /etc/racoon/racoon.conf")
        output = stdout.read().decode('utf-8', errors='ignore')
        print("配置文件内容:")
        print("-" * 60)
        for i, line in enumerate(output.split('\n'), 1):
            print(f"{i:3d}: {line}")
        print("-" * 60)

        # 查看PSK文件
        print("\n[7/7] 检查PSK文件...")
        stdin, stdout, stderr = ssh.exec_command("ls -la /etc/racoon/psk.txt && cat /etc/racoon/psk.txt")
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)

        ssh.close()

        print("\n" + "=" * 60)
        print("诊断完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    diagnose_racoon()
