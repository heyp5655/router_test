#!/usr/bin/env python3
"""
Fix Router PSK Configuration
修复路由器PSK密钥配置
"""

import paramiko
import sys

def run_ssh_command(ssh, command, use_sudo=False):
    """执行SSH命令"""
    if use_sudo:
        command = f"echo 'password' | sudo -S {command}"

    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    return output, error

def fix_psk_config(hostname, username, password, hub_ip, psk_key):
    """修复路由器PSK配置"""

    print("=" * 70)
    print("Fix Router PSK Configuration")
    print("=" * 70)
    print(f"\nRouter: {hostname}")
    print(f"Hub IP: {hub_ip}")
    print(f"PSK Key: {psk_key}")

    try:
        # 建立SSH连接
        print(f"\nConnecting to {hostname}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password, timeout=10)
        print("[OK] SSH connected successfully")

        # 1. 备份当前psk.txt
        print("\n" + "=" * 70)
        print("Step 1: Backup current psk.txt")
        print("=" * 70)

        output, error = run_ssh_command(ssh,
            "cp /etc/racoon/psk.txt /etc/racoon/psk.txt.bak.$(date +%Y%m%d_%H%M%S)",
            use_sudo=True)
        print("[OK] Backup created")

        # 2. 检查当前PSK配置
        print("\n" + "=" * 70)
        print("Step 2: Check current PSK configuration")
        print("=" * 70)

        output, error = run_ssh_command(ssh, "cat /etc/racoon/psk.txt", use_sudo=True)
        print("Current content:")
        print(output if output.strip() else "[EMPTY FILE]")

        # 3. 创建正确的PSK配置
        print("\n" + "=" * 70)
        print("Step 3: Create correct PSK configuration")
        print("=" * 70)

        psk_content = f"""# PSK for DMVPN Hub
# Hub IP and PSK key
{hub_ip}    {psk_key}

# Wildcard for any IP (fallback)
*           {psk_key}
"""

        # 写入新配置
        cmd = f"cat > /etc/racoon/psk.txt << 'EOFPSK'\n{psk_content}\nEOFPSK"
        output, error = run_ssh_command(ssh, cmd, use_sudo=True)

        # 验证写入
        output, error = run_ssh_command(ssh, "cat /etc/racoon/psk.txt", use_sudo=True)
        print("New content:")
        print(output)

        # 4. 设置正确的权限
        print("\n" + "=" * 70)
        print("Step 4: Set correct permissions")
        print("=" * 70)

        output, error = run_ssh_command(ssh, "chmod 600 /etc/racoon/psk.txt", use_sudo=True)
        output, error = run_ssh_command(ssh, "chown root:root /etc/racoon/psk.txt", use_sudo=True)

        output, error = run_ssh_command(ssh, "ls -l /etc/racoon/psk.txt", use_sudo=True)
        print(output)

        # 5. 重启Racoon服务
        print("\n" + "=" * 70)
        print("Step 5: Restart Racoon service")
        print("=" * 70)

        output, error = run_ssh_command(ssh, "systemctl restart racoon", use_sudo=True)

        # 等待2秒
        import time
        time.sleep(2)

        output, error = run_ssh_command(ssh, "systemctl status racoon | head -10", use_sudo=True)
        print(output)

        # 6. 检查连接日志
        print("\n" + "=" * 70)
        print("Step 6: Check connection logs (wait 5 seconds)")
        print("=" * 70)

        print("Waiting for new connection attempt...")
        time.sleep(5)

        output, error = run_ssh_command(ssh, "grep racoon /var/log/syslog | tail -10", use_sudo=True)
        print(output)

        ssh.close()

        print("\n" + "=" * 70)
        print("[OK] PSK configuration fixed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Check if connection is established")
        print("2. If still failing, check Racoon logs: grep racoon /var/log/syslog | tail -20")
        print("3. Verify PSK is loaded: grep 'pre-shared key' /var/log/syslog")

        return 0

    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed - check username/password")
        return 1
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

def main():
    # 路由器信息（需要修改）
    router_ip = input("Enter router IP (default: 192.168.50.40): ").strip() or "192.168.50.40"
    router_user = input("Enter SSH username (default: root): ").strip() or "root"
    router_pass = input("Enter SSH password: ").strip()

    # Hub信息
    hub_ip = input("Enter Hub IP (default: 192.168.50.48): ").strip() or "192.168.50.48"
    psk_key = input("Enter PSK key (default: 123456): ").strip() or "123456"

    return fix_psk_config(router_ip, router_user, router_pass, hub_ip, psk_key)

if __name__ == "__main__":
    sys.exit(main())
