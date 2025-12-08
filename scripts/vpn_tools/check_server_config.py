#!/usr/bin/env python3
"""
Check DMVPN Server Configuration
检查DMVPN服务器配置是否正确
"""

import paramiko
import sys

def run_ssh_command(ssh, command, use_sudo=False):
    """执行SSH命令"""
    if use_sudo:
        command = f"echo 'milesight123' | sudo -S {command}"

    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    return output, error

def main():
    hostname = "192.168.50.48"
    username = "yuxy"
    password = "milesight123"

    print("=" * 70)
    print("DMVPN Server Configuration Checker")
    print("=" * 70)

    try:
        print(f"\nConnecting to {hostname}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password, timeout=10)
        print("[OK] Connected")

        # 1. 检查完整的racoon.conf配置
        print("\n" + "=" * 70)
        print("1. Full Racoon Configuration (/etc/racoon/racoon.conf)")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "cat /etc/racoon/racoon.conf", use_sudo=True)
        print(output)

        # 2. 检查PSK配置
        print("\n" + "=" * 70)
        print("2. PSK Configuration (/etc/racoon/psk.txt)")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "cat /etc/racoon/psk.txt", use_sudo=True)
        print(output if output.strip() else "[EMPTY FILE]")

        # 检查权限
        output, error = run_ssh_command(ssh, "ls -l /etc/racoon/psk.txt", use_sudo=True)
        print(f"\nPermissions: {output.strip()}")

        # 3. 检查Racoon服务状态
        print("\n" + "=" * 70)
        print("3. Racoon Service Status")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "systemctl status racoon", use_sudo=True)

        if "active (running)" in output:
            print("[OK] Racoon is running")
        elif "failed" in output or "dead" in output:
            print("[ERROR] Racoon is NOT running!")
            print(output[:500])
        else:
            print(output[:500])

        # 4. 检查配置文件语法
        print("\n" + "=" * 70)
        print("4. Configuration Syntax Check")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "racoon -C -f /etc/racoon/racoon.conf", use_sudo=True)

        if error.strip():
            print("[ERROR] Configuration has syntax errors:")
            print(error)
        else:
            print("[OK] No syntax errors detected")

        # 5. 检查GRE隧道
        print("\n" + "=" * 70)
        print("5. GRE Tunnel Status")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "ip addr show gre1", use_sudo=True)

        if "10.0.0.1" in output:
            print("[OK] GRE tunnel configured")
            print(output)
        else:
            print("[ERROR] GRE tunnel not found or misconfigured")
            print(output if output.strip() else "gre1 interface not found")

        # 6. 检查最近的Racoon错误日志
        print("\n" + "=" * 70)
        print("6. Recent Racoon Error Logs")
        print("=" * 70)
        output, error = run_ssh_command(ssh,
            "grep -E 'racoon.*ERROR|racoon.*failed|racoon.*invalid' /var/log/syslog | tail -15",
            use_sudo=True)

        if output.strip():
            print(output)
        else:
            print("[OK] No recent errors in logs")

        # 7. 检查当前IPSec SA
        print("\n" + "=" * 70)
        print("7. Current IPSec Security Associations")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "setkey -D | head -40", use_sudo=True)

        if output.strip():
            print(output)
        else:
            print("[INFO] No active IPSec SA")

        # 8. 分析配置问题
        print("\n" + "=" * 70)
        print("8. Configuration Analysis")
        print("=" * 70)

        # 重新获取配置内容进行分析
        output, error = run_ssh_command(ssh, "cat /etc/racoon/racoon.conf", use_sudo=True)
        config = output

        issues = []
        warnings = []

        # 检查remote配置
        if "remote anonymous" not in config:
            issues.append("Missing 'remote anonymous' block")

        # 检查加密算法
        if "encryption_algorithm" not in config:
            issues.append("Missing encryption_algorithm")
        elif "aes 128" in config or "aes128" in config:
            warnings.append("Using AES-128 (should match router)")

        # 检查hash算法
        if "hash_algorithm" not in config:
            issues.append("Missing hash_algorithm")
        elif "sha1" in config:
            warnings.append("Using SHA1 (should match router)")

        # 检查DH组
        if "dh_group" not in config:
            issues.append("Missing dh_group")
        elif "modp3072" in config:
            warnings.append("Using MODP3072/Group15 (should match router)")

        # 检查NAT穿透
        if "nat_traversal" not in config:
            warnings.append("NAT traversal not explicitly configured")

        if issues:
            print("\n[CRITICAL ISSUES]")
            for issue in issues:
                print(f"  - {issue}")

        if warnings:
            print("\n[WARNINGS/INFO]")
            for warning in warnings:
                print(f"  - {warning}")

        if not issues and not warnings:
            print("[OK] Configuration looks good")

        # 9. 检查路由器连接尝试
        print("\n" + "=" * 70)
        print("9. Router Connection Attempts (Last 10)")
        print("=" * 70)
        output, error = run_ssh_command(ssh,
            "grep 'respond new phase 1' /var/log/syslog | tail -10",
            use_sudo=True)

        if output.strip():
            print(output)

            # 统计尝试连接的路由器IP
            import re
            ips = re.findall(r'<=>(\d+\.\d+\.\d+\.\d+)\[', output)
            if ips:
                print(f"\nRouters trying to connect:")
                for ip in set(ips):
                    count = ips.count(ip)
                    print(f"  - {ip} ({count} attempts)")
        else:
            print("[INFO] No recent connection attempts")

        ssh.close()

        print("\n" + "=" * 70)
        print("Diagnostic Complete")
        print("=" * 70)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
