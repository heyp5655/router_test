#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMVPN一键修复脚本 - 降级到路由器兼容参数
自动修改服务器配置: AES-256→AES-128, SHA256→SHA1, modp3072→modp1024
"""

import paramiko
import time
import sys

# Windows编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def fix_dmvpn():
    """一键修复DMVPN配置"""

    server_ip = "192.168.50.48"
    username = "yuxy"
    password = "milesight123"

    print("=" * 70)
    print("DMVPN一键修复 - 降级到路由器兼容参数")
    print("=" * 70)
    print("\n修改内容:")
    print("  AES-256    → AES-128")
    print("  SHA256     → SHA1")
    print("  MODP3072   → MODP1024 (DH Group 2)")
    print("\n开始执行...")

    # 新配置内容
    new_config = """# Racoon configuration - Router Compatible
# Auto-fixed by fix_dmvpn_compatibility.py
# Date: 2025-11-28

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";
log info;

remote 192.168.50.16 {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;
    nat_traversal on;
    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group 2;
        lifetime time 10800 sec;
    }
    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

remote 192.168.40.207 {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;
    nat_traversal on;
    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group 2;
        lifetime time 10800 sec;
    }
    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

remote 10.33.126.188 {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;
    nat_traversal on;
    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group 2;
        lifetime time 10800 sec;
    }
    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

remote 10.117.203.7 {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;
    nat_traversal on;
    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group 2;
        lifetime time 10800 sec;
    }
    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

sainfo anonymous {
    lifetime time 3600 sec;
    encryption_algorithm aes 128;
    authentication_algorithm hmac_sha1;
    compression_algorithm deflate;
}
"""

    try:
        # Step 1: SSH连接
        print("\n[1/6] 连接服务器...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, username=username, password=password, timeout=10)
        print("      ✓ SSH连接成功")

        # Step 2: 备份配置
        print("\n[2/6] 备份当前配置...")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        stdin, stdout, stderr = ssh.exec_command(f"sudo cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.bak.{timestamp}")
        stdout.channel.recv_exit_status()
        print(f"      ✓ 备份保存: racoon.conf.bak.{timestamp}")

        # Step 3: 上传新配置
        print("\n[3/6] 上传新配置...")
        sftp = ssh.open_sftp()
        with sftp.file('/tmp/racoon_compatible.conf', 'w') as f:
            f.write(new_config)
        sftp.close()

        stdin, stdout, stderr = ssh.exec_command("sudo cp /tmp/racoon_compatible.conf /etc/racoon/racoon.conf")
        stdout.channel.recv_exit_status()

        stdin, stdout, stderr = ssh.exec_command("sudo chmod 644 /etc/racoon/racoon.conf")
        stdout.channel.recv_exit_status()
        print("      ✓ 配置文件已更新")

        # Step 4: 重启服务
        print("\n[4/6] 重启Racoon服务...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart racoon")
        stdout.channel.recv_exit_status()
        print("      ✓ 服务已重启")

        time.sleep(3)

        # Step 5: 验证配置
        print("\n[5/6] 验证配置...")
        stdin, stdout, stderr = ssh.exec_command("sudo cat /etc/racoon/racoon.conf | grep -E 'encryption_algorithm|hash_algorithm|dh_group' | head -6")
        output = stdout.read().decode('utf-8')

        if 'aes 128' in output and 'sha1' in output and 'dh_group 2' in output:
            print("      ✓ 配置已生效:")
            for line in output.strip().split('\n'):
                print(f"        {line.strip()}")
        else:
            print("      ⚠ 警告: 配置可能未完全生效")
            print(output)

        # Step 6: 检查服务状态
        print("\n[6/6] 检查服务状态...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl is-active racoon")
        status = stdout.read().decode('utf-8').strip()

        if status == 'active':
            print("      ✓ Racoon服务运行正常")
        else:
            print(f"      ⚠ 警告: 服务状态 = {status}")

        ssh.close()

        # 完成
        print("\n" + "=" * 70)
        print("修复完成！")
        print("=" * 70)
        print("\n新配置参数 (路由器兼容):")
        print("  Phase 1:")
        print("    - 加密: AES-128")
        print("    - 认证: SHA1")
        print("    - DH组: Group 2 (MODP1024)")
        print("\n  Phase 2:")
        print("    - 加密: AES-128")
        print("    - 认证: HMAC-SHA1")
        print("\n下一步:")
        print("  请在路由器Web界面配置相同的IPSec参数，然后启用DMVPN")
        print("\n验证连接:")
        print("  python scripts/vpn_tools/monitor_connection_attempt.py")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    fix_dmvpn()
