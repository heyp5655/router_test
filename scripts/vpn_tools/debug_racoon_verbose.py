# -*- coding: utf-8 -*-
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

PASSWORD = 'milesight123'

# Racoon配置 - 启用详细调试日志
RACOON_CONFIG = """#
# Racoon配置 - 调试模式
# 查看路由器发送的实际参数
#
log debug2;                                     # 启用最详细的调试日志
path include "/etc/racoon/";
path pre_shared_key "/etc/racoon/psk.txt";

remote anonymous {
        exchange_mode main, aggressive;         # 支持两种模式
        lifetime time 10800 seconds;
        my_identifier address;
        dpd_delay 30;
        dpd_retry 3;
        dpd_maxfail 6;
        nat_traversal on;

        # 提案1: AES256 + SHA256 + modp2048
        proposal {
                encryption_algorithm aes 256;
                hash_algorithm sha256;
                dh_group modp2048;
                authentication_method pre_shared_key;
        }

        # 提案2: AES256 + SHA1 + modp2048
        proposal {
                encryption_algorithm aes 256;
                hash_algorithm sha1;
                dh_group modp2048;
                authentication_method pre_shared_key;
        }

        # 提案3: AES128 + SHA256 + modp2048
        proposal {
                encryption_algorithm aes 128;
                hash_algorithm sha256;
                dh_group modp2048;
                authentication_method pre_shared_key;
        }

        # 提案4: 3DES + SHA1 + modp1024
        proposal {
                encryption_algorithm 3des;
                hash_algorithm sha1;
                dh_group modp1024;
                authentication_method pre_shared_key;
        }
}

sainfo anonymous {
        lifetime time 3600 seconds;
        compression_algorithm deflate;

        encryption_algorithm aes 256, aes 128, 3des;
        authentication_algorithm hmac_sha256, hmac_sha1;
}
"""

def run_sudo_command(ssh, command):
    """执行需要sudo的命令"""
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

try:
    print('连接服务器...')
    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)
    print('✅ 连接成功\n')

    # 写入调试配置
    print('=' * 60)
    print('步骤1: 启用Racoon调试日志')
    print('=' * 60)

    sftp = ssh.open_sftp()
    with sftp.file('/tmp/racoon_debug.conf', 'w') as f:
        f.write(RACOON_CONFIG)
    sftp.close()

    stdout, stderr = run_sudo_command(ssh, 'mv /tmp/racoon_debug.conf /etc/racoon/racoon.conf')
    stdout, stderr = run_sudo_command(ssh, 'chmod 644 /etc/racoon/racoon.conf')
    print('✅ 调试配置已写入\n')

    # 清空日志
    print('=' * 60)
    print('步骤2: 清空现有日志')
    print('=' * 60)
    run_sudo_command(ssh, 'truncate -s 0 /var/log/syslog')
    print('✅ 日志已清空\n')

    # 重启Racoon
    print('=' * 60)
    print('步骤3: 重启Racoon服务')
    print('=' * 60)
    run_sudo_command(ssh, 'systemctl restart racoon')
    time.sleep(3)
    print('✅ 服务已重启\n')

    # 等待协商
    print('=' * 60)
    print('步骤4: 等待路由器发起协商 (20秒)')
    print('=' * 60)
    print('请确保路由器DMVPN已启用...\n')

    for i in range(20, 0, -1):
        print(f'等待... {i}秒', end='\r')
        time.sleep(1)
    print('等待完成      \n')

    # 查看详细日志
    print('=' * 60)
    print('步骤5: 查看详细调试日志')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'tail -100 /var/log/syslog | grep -E "(racoon|192.168.50.16)"')

    print('日志输出:\n')
    lines = stdout.strip().split('\n')
    for line in lines[-50:]:  # 显示最后50行
        # 高亮关键信息
        if 'proposal' in line.lower():
            print(f'  📋 {line}')
        elif 'encryption' in line.lower() or 'hash' in line.lower() or 'dh_group' in line.lower():
            print(f'  🔑 {line}')
        elif 'ERROR' in line:
            print(f'  ❌ {line}')
        elif 'INFO' in line:
            print(f'  ℹ️  {line}')
        else:
            print(f'     {line}')

    print('\n' + '=' * 60)
    print('分析完成')
    print('=' * 60)
    print('\n请查看上面的日志，特别是包含以下关键字的行:')
    print('  - "proposal"    : 路由器发送的提案参数')
    print('  - "encryption"  : 加密算法')
    print('  - "hash"        : 哈希算法')
    print('  - "dh_group"    : DH组')
    print('  - "lifetime"    : 生存时间')

finally:
    ssh.close()
    print('\nSSH连接已关闭')
