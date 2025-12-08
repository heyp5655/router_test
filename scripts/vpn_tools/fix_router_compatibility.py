#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMVPN配置快速修复 - 降级到路由器常用参数
从 AES-256+SHA256+modp3072 降级到 AES-128+SHA1+modp1024
"""

import paramiko
import sys

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def fix_dmvpn_config():
    """降级DMVPN配置到路由器常用参数"""

    server_ip = "192.168.50.48"
    username = "yuxy"
    password = "milesight123"

    print("=" * 70)
    print("DMVPN配置快速修复 - 降级到路由器兼容参数")
    print("=" * 70)

    # 新的配置（路由器常用参数）
    new_config = """# Racoon configuration for DMVPN Server
# Compatible with common router settings
# Date: 2025-11-28

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";

log info;

# Router: 192.168.50.16
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

# Router: 192.168.40.207
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

# Router: 10.33.126.188
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

# Router: 10.117.203.7
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
    # pfs_group disabled
    lifetime time 3600 sec;

    encryption_algorithm aes 128;
    authentication_algorithm hmac_sha1;
    compression_algorithm deflate;
}
"""

    try:
        print("\n[1/5] 连接到服务器...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, username=username, password=password, timeout=10)
        print("OK - SSH连接成功")

        print("\n[2/5] 备份当前配置...")
        cmd = "sudo cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.backup_before_downgrade"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()
        print("OK - 备份保存到 racoon.conf.backup_before_downgrade")

        print("\n[3/5] 上传新配置...")
        # 写入新配置到临时文件
        cmd = f"cat > /tmp/racoon_new.conf << 'EOFCONFIG'\n{new_config}\nEOFCONFIG"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()

        # 复制到正式位置
        cmd = "sudo cp /tmp/racoon_new.conf /etc/racoon/racoon.conf"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()
        print("OK - 新配置已上传")

        print("\n[4/5] 验证配置...")
        cmd = "cat /etc/racoon/racoon.conf | grep -E 'encryption_algorithm|hash_algorithm|dh_group' | head -6"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        config_check = stdout.read().decode('utf-8')
        print(config_check)

        print("\n[5/5] 重启Racoon服务...")
        cmd = "sudo systemctl restart racoon"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()

        import time
        time.sleep(2)

        # 检查服务状态
        cmd = "sudo systemctl status racoon | grep Active"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.read().decode('utf-8')
        print(status)

        ssh.close()

        print("\n" + "=" * 70)
        print("配置修复完成！")
        print("=" * 70)
        print("""
新配置参数 (路由器常用):
  Phase 1:
    - 加密: AES-128 (从 AES-256 降级)
    - 认证: SHA1 (从 SHA256 降级)
    - DH组: Group 2 (MODP1024, 从 Group 15 降级)

  Phase 2:
    - 加密: AES-128
    - 认证: HMAC-SHA1

路由器端配置要求:
  请在路由器DMVPN配置中设置:
  - Phase 1: Main Mode, AES-128, SHA1, DH Group 2
  - Phase 2: AES-128, HMAC-SHA1
  - PSK: 123456
  - GRE密钥: 123456
  - Hub地址: 192.168.50.48

现在请在路由器Web界面重新尝试DMVPN连接...
        """)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_dmvpn_config()
