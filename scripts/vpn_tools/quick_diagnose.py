#!/usr/bin/env python3
"""
Quick DMVPN Diagnostics Script
快速诊断当前DMVPN连接问题
"""

import paramiko
import sys

def run_ssh_command(ssh, command, use_sudo=False):
    """执行SSH命令并返回输出"""
    if use_sudo:
        command = f"echo 'milesight123' | sudo -S {command}"

    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    return output, error

def main():
    print("=" * 70)
    print("DMVPN Quick Diagnostics")
    print("=" * 70)

    # SSH连接参数
    hostname = "192.168.50.48"
    username = "yuxy"
    password = "milesight123"

    try:
        # 建立SSH连接
        print(f"\nConnecting to {hostname}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password, timeout=10)
        print("[OK] SSH connected successfully")

        # 1. 检查Racoon服务状态
        print("\n" + "=" * 70)
        print("1. Racoon Service Status")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "systemctl status racoon | head -15", use_sudo=True)
        print(output)

        # 2. 检查GRE隧道状态
        print("\n" + "=" * 70)
        print("2. GRE Tunnel Status (gre1)")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "ip addr show gre1", use_sudo=True)
        print(output if output else "[ERROR] GRE tunnel not found")

        # 3. 检查IPSec SA
        print("\n" + "=" * 70)
        print("3. IPSec SA Status")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "setkey -D | grep -E 'esp|10\\.0\\.0\\.|192\\.168\\.' | head -30", use_sudo=True)
        if output.strip():
            print(output)
        else:
            print("[ERROR] No active IPSec SA found")

        # 4. 检查最近的Racoon日志
        print("\n" + "=" * 70)
        print("4. Recent Racoon Logs (Last 20 lines)")
        print("=" * 70)
        output, error = run_ssh_command(ssh,
            "grep racoon /var/log/syslog | tail -20",
            use_sudo=True)
        print(output if output else "[ERROR] No recent logs")

        # 5. 检查NHRP状态
        print("\n" + "=" * 70)
        print("5. NHRP Registration Status")
        print("=" * 70)
        output, error = run_ssh_command(ssh,
            "grep 'NHRP.*Registration' /var/log/syslog | tail -10",
            use_sudo=True)
        print(output if output else "[INFO] No NHRP registration records")

        # 6. 测试GRE连通性
        print("\n" + "=" * 70)
        print("6. GRE Connectivity Test")
        print("=" * 70)

        test_ips = ["10.0.0.3", "10.0.0.4"]
        for ip in test_ips:
            print(f"\nPinging {ip}...")
            output, error = run_ssh_command(ssh, f"ping -c 3 -W 2 {ip}", use_sudo=True)
            if "0% packet loss" in output:
                print(f"[OK] {ip} - Reachable (0% loss)")
            elif "100% packet loss" in output:
                print(f"[ERROR] {ip} - Unreachable (100% loss)")
            else:
                # 显示详细信息
                for line in output.split('\n'):
                    if 'packet loss' in line or 'min/avg/max' in line:
                        print(f"   {line.strip()}")

        # 7. 检查Racoon配置关键参数
        print("\n" + "=" * 70)
        print("7. Racoon Configuration (Key Parameters)")
        print("=" * 70)
        output, error = run_ssh_command(ssh,
            "grep -E 'remote anonymous|encryption_algorithm|hash_algorithm|dh_group|preshared_key' /etc/racoon/racoon.conf | head -20",
            use_sudo=True)
        print(output)

        ssh.close()

        print("\n" + "=" * 70)
        print("[OK] Diagnostics completed")
        print("=" * 70)

    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed - check username/password")
        return 1
    except paramiko.SSHException as e:
        print(f"[ERROR] SSH error: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
