#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接修改Racoon配置 - 使用sudo权限
"""

import paramiko
import time

def update_racoon_config():
    server_ip = "192.168.50.48"
    username = "yuxy"
    password = "milesight123"

    # 新配置内容
    new_config = """# Racoon configuration - Router Compatible
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
        print("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, username=username, password=password, timeout=10)

        # 使用sftp上传配置文件
        print("Uploading new config via SFTP...")
        sftp = ssh.open_sftp()

        # 写入到临时文件
        with sftp.file('/tmp/racoon_new.conf', 'w') as f:
            f.write(new_config)

        sftp.close()
        print("Config uploaded to /tmp/racoon_new.conf")

        # 备份旧配置
        print("Backing up old config...")
        stdin, stdout, stderr = ssh.exec_command('sudo cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.backup_old')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("Backup created")

        # 复制新配置
        print("Installing new config...")
        stdin, stdout, stderr = ssh.exec_command('sudo cp /tmp/racoon_new.conf /etc/racoon/racoon.conf')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("New config installed")

        # 修改权限
        stdin, stdout, stderr = ssh.exec_command('sudo chmod 644 /etc/racoon/racoon.conf')
        stdout.channel.recv_exit_status()

        # 重启服务
        print("Restarting racoon service...")
        stdin, stdout, stderr = ssh.exec_command('sudo systemctl restart racoon')
        exit_status = stdout.channel.recv_exit_status()

        time.sleep(3)

        # 验证配置
        print("\n===== Verify new config =====")
        stdin, stdout, stderr = ssh.exec_command('sudo cat /etc/racoon/racoon.conf | grep -E "encryption_algorithm|hash_algorithm|dh_group" | head -6')
        output = stdout.read().decode('utf-8')
        print(output)

        # 检查服务状态
        print("\n===== Racoon status =====")
        stdin, stdout, stderr = ssh.exec_command('sudo systemctl is-active racoon')
        status = stdout.read().decode('utf-8').strip()
        print(f"Status: {status}")

        ssh.close()

        print("\n" + "=" * 70)
        print("SUCCESS! Config updated to router-compatible settings:")
        print("  Phase 1: AES-128 + SHA1 + DH Group 2")
        print("  Phase 2: AES-128 + HMAC-SHA1")
        print("\nPlease configure your router with the same settings!")
        print("=" * 70)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_racoon_config()
