# -*- coding: utf-8 -*-
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

PASSWORD = 'milesight123'

# 修改回 modp3072 (DH Group 15)
RACOON_CONFIG = """#
# Racoon配置 - modp3072 (DH Group 15)
# 更新时间: 2025-11-27
#
path include "/etc/racoon";
path pre_shared_key "/etc/racoon/psk.txt";

remote anonymous {
    exchange_mode main;
    lifetime time 10800 seconds;
    my_identifier address;
    dpd_delay 30;
    dpd_retry 3;
    dpd_maxfail 6;
    nat_traversal on;

    proposal {
        encryption_algorithm aes256;
        hash_algorithm sha256;
        dh_group modp3072;              # DH Group 15
        authentication_method pre_shared_key;
    }
}

sainfo anonymous {
    lifetime time 3600 seconds;
    compression_algorithm deflate;
    encryption_algorithm aes256;
    authentication_algorithm hmac_sha256;
}
"""

def run_sudo_command(ssh, command):
    """执行需要sudo的命令"""
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

try:
    print('=' * 60)
    print('修改 DH Group 为 modp3072 (DH Group 15)')
    print('=' * 60)
    print()

    print('连接服务器...')
    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)
    print('✅ 连接成功\n')

    # 写入新配置
    print('写入配置 (modp3072 - DH Group 15)...')
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/racoon_modp3072_final.conf', 'w') as f:
        f.write(RACOON_CONFIG)
    sftp.close()

    run_sudo_command(ssh, 'mv /tmp/racoon_modp3072_final.conf /etc/racoon/racoon.conf')
    run_sudo_command(ssh, 'chmod 644 /etc/racoon/racoon.conf')
    print('✅ 配置已更新\n')

    # 重启服务
    print('重启Racoon服务...')
    run_sudo_command(ssh, 'systemctl restart racoon')
    time.sleep(3)

    stdout, _ = run_sudo_command(ssh, 'systemctl is-active racoon')
    if 'active' in stdout:
        print('✅ Racoon服务运行中\n')
    else:
        print('❌ Racoon服务启动失败\n')

    # 等待协商
    print('等待IPSec协商 (15秒)...')
    for i in range(15, 0, -1):
        print(f'等待... {i:2d}秒', end='\r')
        time.sleep(1)
    print('等待完成      \n')

    # 检查SA
    print('=' * 60)
    print('检查IPSec SA状态')
    print('=' * 60)
    stdout, _ = run_sudo_command(ssh, 'setkey -D')

    if '192.168.50.16' in stdout:
        print('✅✅✅ IPSec SA已建立! ✅✅✅\n')

        # 显示SA信息
        lines = stdout.split('\n')
        for i, line in enumerate(lines):
            if '192.168.50.16' in line:
                print(f'  {line}')
                # 显示加密算法信息
                for j in range(1, min(4, len(lines) - i)):
                    if 'esp' in lines[i+j] or 'aes' in lines[i+j] or 'sha' in lines[i+j]:
                        print(f'  {lines[i+j]}')
                break
    else:
        print('⚠️ IPSec SA尚未建立\n')

        # 查看日志
        stdout, _ = run_sudo_command(ssh, 'tail -10 /var/log/syslog | grep racoon')
        for line in stdout.strip().split('\n')[-5:]:
            if 'ERROR' in line:
                print(f'  ❌ {line}')

    # 测试连通性
    print('\n' + '=' * 60)
    print('测试GRE隧道连通性')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 4 -W 2 10.0.0.3')
    ping_output = stdout_obj.read().decode('utf-8', errors='ignore')

    received = 0
    for line in ping_output.split('\n'):
        if 'packets transmitted' in line:
            parts = line.split()
            if len(parts) >= 4:
                received = int(parts[3])
            print(f'{line}')

    if received >= 3:
        print(f'\n✅✅✅ GRE隧道连通成功! ({received}/4) ✅✅✅')
    elif received > 0:
        print(f'\n⚠️ 部分连通 ({received}/4)')
    else:
        print(f'\n⚠️ GRE隧道不通 (0/4) - 可能是路由器端GRE配置问题')

    print('\n' + '=' * 60)
    print('配置完成!')
    print('=' * 60)
    print('\n最终服务器配置:')
    print('  Phase 1: Main Mode, AES256, SHA256, modp3072 (DH15)')
    print('  Phase 2: AES256, HMAC-SHA256')
    print('  PSK: 123456')
    print('  GRE Key: 123456')
    print('\n如果IPSec SA已建立但GRE不通，请检查路由器GRE配置。')

finally:
    ssh.close()
    print('\nSSH连接已关闭')
