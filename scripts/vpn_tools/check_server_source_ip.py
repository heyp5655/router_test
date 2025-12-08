#!/usr/bin/env python3
"""
Check what source IP the server sees
检查服务器看到的源IP
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
    print("Check Server's View of Router Source IPs")
    print("=" * 70)

    try:
        print(f"\nConnecting to {hostname}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password, timeout=10)
        print("[OK] Connected")

        # 1. 检查当前IPSec连接
        print("\n" + "=" * 70)
        print("1. Current IPSec Connections (setkey -D)")
        print("=" * 70)
        output, error = run_ssh_command(ssh,
            "setkey -D | grep -E '^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+' | head -20",
            use_sudo=True)
        print(output if output.strip() else "[No IPSec SA]")

        # 2. 检查Racoon日志中的源IP
        print("\n" + "=" * 70)
        print("2. Source IPs in Racoon Logs")
        print("=" * 70)
        output, error = run_ssh_command(ssh,
            "grep 'respond new phase 1' /var/log/syslog | tail -10",
            use_sudo=True)

        if output.strip():
            print(output)
            print("\nAnalysis:")
            if "192.168.50.40" in output:
                print("  - Found 192.168.50.40 (internal IP)")
            if "106.122.75.37" in output:
                print("  - Found 106.122.75.37 (4G router public IP)")
            if "112.48.19.183" in output:
                print("  - Found 112.48.19.183 (NAT gateway public IP)")
        else:
            print("[No recent connection attempts]")

        # 3. 检查失败的连接尝试
        print("\n" + "=" * 70)
        print("3. Failed Connection Attempts (PSK errors)")
        print("=" * 70)
        output, error = run_ssh_command(ssh,
            "grep 'couldn\\'t find.*pskey' /var/log/syslog | tail -10",
            use_sudo=True)

        if output.strip():
            print(output)
            print("\nRouter is looking for PSK of:")
            # 提取IP
            import re
            ips = re.findall(r'for (\d+\.\d+\.\d+\.\d+)', output)
            for ip in set(ips):
                print(f"  - {ip}")
        else:
            print("[No PSK errors]")

        # 4. 检查服务器当前PSK配置
        print("\n" + "=" * 70)
        print("4. Server's Current PSK Configuration")
        print("=" * 70)
        output, error = run_ssh_command(ssh, "cat /etc/racoon/psk.txt", use_sudo=True)
        print(output if output.strip() else "[EMPTY]")

        # 5. 检查Phase 1协商日志
        print("\n" + "=" * 70)
        print("5. Recent Phase 1 Negotiations")
        print("=" * 70)
        output, error = run_ssh_command(ssh,
            "grep -E 'phase1 negotiation|ISAKMP-SA' /var/log/syslog | tail -10",
            use_sudo=True)
        print(output if output.strip() else "[No phase1 logs]")

        ssh.close()

        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print("\nBased on the logs above:")
        print("1. Check 'Source IPs in Racoon Logs' - what IP does server see?")
        print("2. If source is 192.168.50.40 -> router and server are in same LAN")
        print("3. If source is public IP -> router is from external network")
        print("\nConclusion:")
        print("- Internal router (192.168.50.40): Server sees 192.168.50.40")
        print("  -> No NAT involved, server PSK doesn't need 112.48.19.183")
        print("- External router: Server sees router's public IP")
        print("  -> Server can use 'remote anonymous' or '*' for PSK")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
