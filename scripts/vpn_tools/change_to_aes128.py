# -*- coding: utf-8 -*-
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

PASSWORD = 'milesight123'

# 修改 Phase 2 为 AES128 + SHA256
RACOON_CONFIG = """#
# Racoon配置 - Phase 2: AES128 + SHA256
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
        dh_group modp3072;
        authentication_method pre_shared_key;
    }
}

sainfo anonymous {
    lifetime time 3600 seconds;
    compression_algorithm deflate;
    encryption_algorithm aes128;       # Phase 2: AES128
    authentication_algorithm hmac_sha256;
}
"""

def run_sudo_command(ssh, command):
    """执行需要sudo的命令"""
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

try:
    print('=' * 60)
    print('修改 Phase 2 SA算法为 AES128 + SHA256')
    print('=' * 60)
    print()

    print('连接服务器...')
    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)
    print('✅ 连接成功\n')

    # 写入新配置
    print('写入配置...')
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/racoon_aes128.conf', 'w') as f:
        f.write(RACOON_CONFIG)
    sftp.close()

    run_sudo_command(ssh, 'mv /tmp/racoon_aes128.conf /etc/racoon/racoon.conf')
    run_sudo_command(ssh, 'chmod 644 /etc/racoon/racoon.conf')
    print('✅ 配置已更新\n')

    # 完全清除IPSec状态
    print('清除现有IPSec状态...')
    run_sudo_command(ssh, 'systemctl stop racoon')
    time.sleep(2)
    run_sudo_command(ssh, 'setkey -F')
    run_sudo_command(ssh, 'setkey -FP')
    time.sleep(1)

    # 重新加载SPD策略
    spd_commands = """spdadd 0.0.0.0/0 0.0.0.0/0 gre -P out ipsec esp/transport//require;
spdadd 0.0.0.0/0 0.0.0.0/0 gre -P in ipsec esp/transport//require;
spdadd 0.0.0.0/0 0.0.0.0/0 gre -P fwd ipsec esp/transport//require;
"""
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/ipsec_spd.conf', 'w') as f:
        f.write(spd_commands)
    sftp.close()
    run_sudo_command(ssh, 'setkey -f /tmp/ipsec_spd.conf')
    print('✅ 已清除并重新加载策略\n')

    # 启动Racoon
    print('启动Racoon服务...')
    run_sudo_command(ssh, 'systemctl start racoon')
    time.sleep(3)

    stdout, _ = run_sudo_command(ssh, 'systemctl is-active racoon')
    if 'active' in stdout:
        print('✅ Racoon服务运行中\n')
    else:
        print('❌ Racoon服务启动失败\n')

    # 等待协商
    print('=' * 60)
    print('等待IPSec协商 (20秒)')
    print('=' * 60)
    for i in range(20, 0, -1):
        print(f'等待... {i:2d}秒', end='\r')
        time.sleep(1)
    print('等待完成      \n')

    # 检查SA
    print('=' * 60)
    print('检查IPSec SA状态')
    print('=' * 60)
    stdout, _ = run_sudo_command(ssh, 'setkey -D')

    if '192.168.50.16' in stdout:
        print('✅ IPSec SA已建立\n')

        # 显示加密算法信息
        lines = stdout.split('\n')
        print('SA详细信息:')
        for i, line in enumerate(lines):
            if '192.168.50.16' in line or '192.168.50.48' in line:
                print(f'  {line}')
                for j in range(1, min(5, len(lines) - i)):
                    if lines[i+j].strip() and ('esp' in lines[i+j] or 'aes' in lines[i+j] or 'hmac' in lines[i+j]):
                        print(f'  {lines[i+j]}')
                        if 'aes-cbc' in lines[i+j]:
                            print(f'  ℹ️  使用的加密算法: AES-CBC (AES128)')
                    elif not lines[i+j].strip():
                        break
                print()
                break
    else:
        print('⚠️ IPSec SA尚未建立\n')

        # 查看日志
        print('查看Racoon日志:')
        stdout, _ = run_sudo_command(ssh, 'tail -15 /var/log/syslog | grep racoon')
        for line in stdout.strip().split('\n')[-8:]:
            if 'ERROR' in line:
                print(f'  ❌ {line}')
            elif 'ISAKMP-SA' in line or 'IPsec-SA' in line:
                print(f'  ✅ {line}')

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
        print(f'\n✅ GRE隧道连通成功! ({received}/4)')
    elif received > 0:
        print(f'\n⚠️ 部分连通 ({received}/4)')
    else:
        print(f'\n⚠️ GRE隧道不通 (0/4)')

    print('\n' + '=' * 60)
    print('配置完成!')
    print('=' * 60)
    print('\n最终服务器配置:')
    print('  Phase 1: Main Mode, AES256, SHA256, modp3072 (DH15)')
    print('  Phase 2: AES128, HMAC-SHA256')
    print('  PSK: 123456')
    print('  GRE Key: 123456')

finally:
    ssh.close()
    print('\nSSH连接已关闭')
