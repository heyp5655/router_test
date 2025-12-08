#!/usr/bin/env python3
"""
Fix Router PSK for NAT Scenario
修复NAT场景下的路由器PSK配置

问题：路由器通过NAT连接Hub时，PSK应该使用Hub的内网IP，而不是公网IP
"""

import paramiko
import sys

def run_ssh_command(ssh, command, use_sudo=False, sudo_pass=None):
    """执行SSH命令"""
    if use_sudo and sudo_pass:
        command = f"echo '{sudo_pass}' | sudo -S {command}"

    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    return output, error

def main():
    print("=" * 70)
    print("Fix Router PSK Configuration for NAT Scenario")
    print("=" * 70)

    # 获取路由器信息
    print("\n[Step 1] Enter router SSH information")
    router_ip = input("Router IP (default: 192.168.50.40): ").strip() or "192.168.50.40"
    router_user = input("SSH username (default: root): ").strip() or "root"
    router_pass = input("SSH password: ").strip()

    if not router_pass:
        print("[ERROR] Password is required")
        return 1

    # Hub信息
    print("\n[Step 2] Enter Hub information")
    print("IMPORTANT: Use Hub's INTERNAL IP, not public IP!")
    print("Example: 192.168.50.48 (NOT 112.48.19.183)")
    hub_internal_ip = input("Hub internal IP (default: 192.168.50.48): ").strip() or "192.168.50.48"
    psk_key = input("PSK key (default: 123456): ").strip() or "123456"

    print("\n" + "=" * 70)
    print("Configuration Summary:")
    print("=" * 70)
    print(f"Router IP: {router_ip}")
    print(f"Hub Internal IP: {hub_internal_ip}")
    print(f"PSK Key: {psk_key}")
    print("\nPSK file content will be:")
    print(f"  {hub_internal_ip}    {psk_key}")
    print(f"  *                    {psk_key}")

    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled")
        return 0

    try:
        # 建立SSH连接
        print(f"\n[Step 3] Connecting to {router_ip}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(router_ip, username=router_user, password=router_pass, timeout=10)
        print("[OK] SSH connected")

        # 备份当前配置
        print("\n[Step 4] Backup current psk.txt...")
        output, error = run_ssh_command(ssh,
            "cp /etc/racoon/psk.txt /etc/racoon/psk.txt.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true",
            use_sudo=True, sudo_pass=router_pass)
        print("[OK] Backup created (if file existed)")

        # 显示当前内容
        print("\n[Step 5] Current psk.txt content:")
        output, error = run_ssh_command(ssh, "cat /etc/racoon/psk.txt 2>/dev/null || echo '[File not found]'",
            use_sudo=True, sudo_pass=router_pass)
        print(output if output.strip() else "[EMPTY]")

        # 创建新PSK配置
        print("\n[Step 6] Writing new PSK configuration...")

        psk_content = f"""# DMVPN Hub PSK Configuration
# IMPORTANT: Use Hub's INTERNAL IP (after NAT), not public IP
#
# Example:
#   Hub public IP: 112.48.19.183 (for connection)
#   Hub internal IP: 192.168.50.48 (for PSK lookup) <- Use this!
#
# Reason: IPSec negotiation sees the internal IP after NAT translation

# Hub internal IP and PSK
{hub_internal_ip}    {psk_key}

# Wildcard for any IP (fallback)
*                    {psk_key}
"""

        # 转义单引号
        psk_content_escaped = psk_content.replace("'", "'\\''")

        # 写入文件
        cmd = f"echo '{psk_content_escaped}' > /etc/racoon/psk.txt"
        output, error = run_ssh_command(ssh, cmd, use_sudo=True, sudo_pass=router_pass)

        # 验证写入
        print("\n[Step 7] Verify new content:")
        output, error = run_ssh_command(ssh, "cat /etc/racoon/psk.txt",
            use_sudo=True, sudo_pass=router_pass)
        print(output)

        # 设置权限
        print("\n[Step 8] Setting correct permissions...")
        run_ssh_command(ssh, "chmod 600 /etc/racoon/psk.txt", use_sudo=True, sudo_pass=router_pass)
        run_ssh_command(ssh, "chown root:root /etc/racoon/psk.txt", use_sudo=True, sudo_pass=router_pass)

        output, error = run_ssh_command(ssh, "ls -l /etc/racoon/psk.txt",
            use_sudo=True, sudo_pass=router_pass)
        print(output)

        # 重启Racoon
        print("\n[Step 9] Restarting Racoon service...")
        run_ssh_command(ssh, "systemctl restart racoon", use_sudo=True, sudo_pass=router_pass)

        import time
        time.sleep(3)

        output, error = run_ssh_command(ssh, "systemctl status racoon | head -10",
            use_sudo=True, sudo_pass=router_pass)

        if "active (running)" in output:
            print("[OK] Racoon is running")
        else:
            print("[WARNING] Racoon status unclear:")
            print(output)

        # 等待连接
        print("\n[Step 10] Waiting for connection attempt (10 seconds)...")
        time.sleep(10)

        # 检查日志
        print("\n[Step 11] Checking connection logs...")
        output, error = run_ssh_command(ssh, "grep racoon /var/log/syslog | tail -15",
            use_sudo=True, sudo_pass=router_pass)
        print(output)

        # 分析日志
        if "ISAKMP-SA established" in output:
            print("\n" + "=" * 70)
            print("[SUCCESS] IPSec Phase 1 established!")
            print("=" * 70)
        elif "couldn't find the pskey" in output:
            print("\n" + "=" * 70)
            print("[WARNING] Still can't find PSK - may need manual check")
            print("=" * 70)
        elif "no suitable proposal found" in output:
            print("\n" + "=" * 70)
            print("[WARNING] Encryption parameters mismatch")
            print("=" * 70)
        else:
            print("\n[INFO] Check logs above for connection status")

        ssh.close()

        print("\n" + "=" * 70)
        print("[DONE] PSK configuration updated")
        print("=" * 70)
        print("\nManual verification commands (on router):")
        print("  sudo cat /etc/racoon/psk.txt")
        print("  sudo grep racoon /var/log/syslog | tail -20")
        print("  sudo setkey -D  # Check IPSec SA")
        print("  ping 10.0.0.1   # Test GRE tunnel")

        return 0

    except paramiko.AuthenticationException:
        print("\n[ERROR] SSH authentication failed - check username/password")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
