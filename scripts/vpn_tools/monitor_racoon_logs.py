#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看详细的Racoon日志和路由器连接尝试"""

import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_racoon_logs():
    host = "192.168.50.48"
    username = "yuxy"
    password = "milesight123"

    print("=" * 70)
    print("Racoon详细日志分析")
    print("=" * 70)

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, port=22, username=username, password=password, timeout=10)
        print("✓ SSH连接成功\n")

        # 1. 启动Racoon（如果未运行）
        print("[1/5] 确保Racoon服务运行...")
        cmd = "sudo -S systemctl start racoon"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdin.write(password + '\n')
        stdin.flush()
        stdout.read()
        time.sleep(3)

        # 2. 检查服务状态
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active racoon")
        status = stdout.read().decode('utf-8').strip()
        print(f"Racoon服务状态: {status}")

        # 3. 查看完整的系统日志（包括错误）
        print("\n[2/5] 查看完整系统日志（最近100条）...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command("journalctl -u racoon -n 100 --no-pager")
        output = stdout.read().decode('utf-8', errors='ignore')

        # 过滤关键错误信息
        important_lines = []
        for line in output.split('\n'):
            if any(keyword in line for keyword in ['ERROR', 'WARN', 'failed', 'refused', 'timeout', 'INFO:', 'phase1']):
                important_lines.append(line)

        for line in important_lines[-50:]:
            print(f"  {line}")

        # 4. 查看/var/log/syslog中的racoon日志
        print("\n[3/5] 查看syslog中的Racoon日志...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command("grep racoon /var/log/syslog | tail -30")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            for line in output.split('\n'):
                print(f"  {line}")
        else:
            print("  没有找到racoon日志")

        # 5. 检查端口监听
        print("\n[4/5] 检查Racoon端口监听...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command("netstat -ulnp | grep -E ':(500|4500)'")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print("✓ 端口监听正常:")
            print(output)
        else:
            print("✗ 端口500/4500未监听")

        # 6. 实时监控日志（等待30秒看是否有连接尝试）
        print("\n[5/5] 实时监控Racoon日志（等待30秒）...")
        print("-" * 70)
        print("提示: 现在请在路由器上尝试连接DMVPN...\n")

        cmd = "timeout 30 journalctl -u racoon -f"
        stdin, stdout, stderr = ssh.exec_command(cmd)

        start_time = time.time()
        while time.time() - start_time < 30:
            line = stdout.readline()
            if line:
                print(f"  {line.strip()}")
            time.sleep(0.1)

        ssh.close()

        print("\n" + "=" * 70)
        print("日志分析完成")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ 错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_racoon_logs()
