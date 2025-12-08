#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速修复Racoon文件权限
"""

import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def fix_permissions():
    """修复Racoon配置文件权限"""

    host = "192.168.50.48"
    port = 22
    username = "yuxy"
    password = "milesight123"

    print("=" * 60)
    print("修复Racoon文件权限")
    print("=" * 60)

    try:
        # 连接SSH
        print("\n[1/3] 连接SSH...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, port=port, username=username, password=password, timeout=10)
        print("✓ SSH连接成功")

        # 修复racoon.conf权限
        print("\n[2/3] 修复racoon.conf权限...")
        cmd = "sudo -S chown root:root /etc/racoon/racoon.conf && sudo -S chmod 644 /etc/racoon/racoon.conf"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdin.write(password + '\n')
        stdin.flush()
        stdout.read()
        print("✓ racoon.conf权限已修复 (root:root 644)")

        # 修复psk.txt权限
        print("\n[3/3] 修复psk.txt权限...")
        cmd = "sudo -S chown root:root /etc/racoon/psk.txt && sudo -S chmod 600 /etc/racoon/psk.txt"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdin.write(password + '\n')
        stdin.flush()
        stdout.read()
        print("✓ psk.txt权限已修复 (root:root 600)")

        # 验证权限
        print("\n验证文件权限:")
        stdin, stdout, stderr = ssh.exec_command("ls -la /etc/racoon/racoon.conf /etc/racoon/psk.txt")
        output = stdout.read().decode('utf-8')
        print(output)

        # 重启服务
        print("正在重启Racoon服务...")
        cmd = "sudo -S systemctl restart racoon"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdin.write(password + '\n')
        stdin.flush()
        stdout.read()

        import time
        time.sleep(3)

        # 检查服务状态
        stdin, stdout, stderr = ssh.exec_command("systemctl status racoon --no-pager")
        output = stdout.read().decode('utf-8')

        if "active (running)" in output:
            print("\n✓ Racoon服务启动成功！")
        else:
            print("\n⚠ Racoon服务状态:")
            for line in output.split('\n')[:15]:
                print(f"  {line}")

        ssh.close()

        print("\n" + "=" * 60)
        print("权限修复完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    fix_permissions()
