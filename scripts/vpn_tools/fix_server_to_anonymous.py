#!/usr/bin/env python3
"""
Fix DMVPN Server Configuration
修复DMVPN服务器配置（从GUI工具错误配置恢复）
"""

import paramiko
import sys
from datetime import datetime

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
    print("Fix DMVPN Server Configuration")
    print("=" * 70)
    print("\nThis will restore the working configuration:")
    print("  - remote anonymous (accept any router IP)")
    print("  - Phase 1: AES-128 + SHA1 + MODP3072")
    print("  - Phase 2: AES-128 + HMAC-SHA1")
    print("  - NAT-T enabled")
    print("\n[AUTO MODE] Proceeding automatically...")

    try:
        print(f"\nConnecting to {hostname}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password, timeout=10)
        print("[OK] Connected")

        # 1. 备份当前配置
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n[Step 1] Backing up current configuration...")

        output, error = run_ssh_command(ssh,
            f"cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.bak.{timestamp}",
            use_sudo=True)
        print(f"[OK] Backup created: racoon.conf.bak.{timestamp}")

        # 2. 创建正确的配置
        print("\n[Step 2] Creating correct Racoon configuration...")

        correct_config = """# Racoon configuration for DMVPN Server
# Fixed configuration - supports any router IP
# Date: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";

log info;

# Accept connections from any router (anonymous mode)
remote anonymous {
    exchange_mode main;
    my_identifier address;

    nat_traversal force;

    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group modp3072;
        lifetime time 10800 sec;
    }

    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

# Phase 2 (IPSec SA) configuration
sainfo anonymous {
    lifetime time 3600 sec;

    encryption_algorithm aes 128;
    authentication_algorithm hmac_sha1;
    compression_algorithm deflate;
}
"""

        # 写入配置文件
        config_escaped = correct_config.replace("'", "'\\''")
        cmd = f"echo '{config_escaped}' > /etc/racoon/racoon.conf"
        output, error = run_ssh_command(ssh, cmd, use_sudo=True)

        # 验证写入
        output, error = run_ssh_command(ssh, "cat /etc/racoon/racoon.conf", use_sudo=True)
        print("\n[Verification] New configuration:")
        print("-" * 70)
        print(output[:800])
        if len(output) > 800:
            print("... (truncated)")

        # 3. 检查语法
        print("\n[Step 3] Checking configuration syntax...")
        output, error = run_ssh_command(ssh, "racoon -C -f /etc/racoon/racoon.conf 2>&1", use_sudo=True)

        if "ERROR" in output or "error" in error:
            print("[ERROR] Configuration has syntax errors:")
            print(error)
            print(output)
            print("\nReverting to backup...")
            run_ssh_command(ssh, f"cp /etc/racoon/racoon.conf.bak.{timestamp} /etc/racoon/racoon.conf", use_sudo=True)
            return 1
        else:
            print("[OK] No syntax errors")

        # 4. 确认PSK配置
        print("\n[Step 4] Verifying PSK configuration...")
        output, error = run_ssh_command(ssh, "cat /etc/racoon/psk.txt", use_sudo=True)

        if output.strip() == "* 123456":
            print("[OK] PSK is correct: * 123456")
        else:
            print(f"[WARNING] PSK content: {output.strip()}")
            print("Fixing PSK...")
            run_ssh_command(ssh, "echo '* 123456' > /etc/racoon/psk.txt", use_sudo=True)
            run_ssh_command(ssh, "chmod 600 /etc/racoon/psk.txt", use_sudo=True)
            print("[OK] PSK fixed")

        # 5. 重启Racoon服务
        print("\n[Step 5] Restarting Racoon service...")
        output, error = run_ssh_command(ssh, "systemctl restart racoon", use_sudo=True)

        import time
        time.sleep(3)

        output, error = run_ssh_command(ssh, "systemctl status racoon | head -10", use_sudo=True)

        if "active (running)" in output:
            print("[OK] Racoon restarted successfully")
        else:
            print("[ERROR] Racoon failed to start:")
            print(output)
            return 1

        # 6. 等待路由器重新连接
        print("\n[Step 6] Waiting for router reconnection (15 seconds)...")
        time.sleep(15)

        # 7. 检查连接状态
        print("\n[Step 7] Checking connection status...")

        # 检查IPSec SA
        output, error = run_ssh_command(ssh, "setkey -D | grep -E 'esp|192\\.168\\.' | head -20", use_sudo=True)

        if output.strip():
            print("[OK] IPSec SA established:")
            print(output[:500])
        else:
            print("[INFO] No IPSec SA yet - checking logs...")

        # 检查最新日志
        output, error = run_ssh_command(ssh, "grep racoon /var/log/syslog | tail -15", use_sudo=True)
        print("\nRecent logs:")
        print(output)

        # 8. 分析结果
        print("\n" + "=" * 70)
        if "ISAKMP-SA established" in output:
            print("[SUCCESS] Router connected successfully!")
        elif "no suitable proposal" in output:
            print("[WARNING] Router encryption parameters mismatch")
        elif "couldn't find.*pskey" in output:
            print("[WARNING] Router PSK configuration issue")
        elif "not allowed in any applicable rmconf" in output:
            print("[ERROR] Still getting rmconf error - check logs")
        else:
            print("[INFO] Check logs above for connection status")

        print("=" * 70)

        ssh.close()

        print("\n[DONE] Configuration updated")
        print("\nNext steps:")
        print("1. Check router logs to ensure it's trying to connect")
        print("2. Verify router PSK has: 192.168.50.48  123456")
        print("3. Check router encryption: AES-128, SHA1, MODP3072")
        print("\nServer is now in anonymous mode - accepts any router IP")

        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
