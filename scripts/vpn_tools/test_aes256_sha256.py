# -*- coding: utf-8 -*-
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

PASSWORD = 'milesight123'

# 新的Racoon配置 - 专门测试 modp2048 + AES256 + SHA256
RACOON_CONFIG = """#
# Racoon配置 - 测试 modp2048 + AES256 + SHA256
# 测试日期: 2025-11-27
# GRE密钥: 123456
# PSK密钥: 123456
#
log notify;
path include "/etc/racoon/";
path pre_shared_key "/etc/racoon/psk.txt";

remote anonymous {
        exchange_mode main, aggressive;
        lifetime time 10800 seconds;
        my_identifier address;
        dpd_delay 30;
        dpd_retry 3;
        dpd_maxfail 6;
        nat_traversal on;

        # 提案1: AES256 + SHA256 + DH14 (modp2048) - 主要测试
        proposal {
                encryption_algorithm aes256;
                hash_algorithm sha256;
                dh_group modp2048;
                authentication_method pre_shared_key;
        }

        # 提案2: AES256 + SHA1 + DH14 (modp2048) - 备用
        proposal {
                encryption_algorithm aes256;
                hash_algorithm sha1;
                dh_group modp2048;
                authentication_method pre_shared_key;
        }

        # 提案3: AES128 + SHA256 + DH14 (modp2048) - 兼容
        proposal {
                encryption_algorithm aes128;
                hash_algorithm sha256;
                dh_group modp2048;
                authentication_method pre_shared_key;
        }
}

sainfo anonymous {
        lifetime time 3600 seconds;
        compression_algorithm deflate;

        # Phase 2 加密算法
        encryption_algorithm aes256, aes128, 3des;
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

    # 备份当前配置
    print('=' * 60)
    print('步骤1: 备份当前配置')
    print('=' * 60)
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    backup_cmd = f'cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.backup_{timestamp}'
    stdout, stderr = run_sudo_command(ssh, backup_cmd)
    print(f'备份文件: /etc/racoon/racoon.conf.backup_{timestamp}')
    print('✅ 备份完成\n')

    # 写入新配置
    print('=' * 60)
    print('步骤2: 写入新配置 (modp2048 + AES256 + SHA256)')
    print('=' * 60)

    # 使用临时文件
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/racoon_test.conf', 'w') as f:
        f.write(RACOON_CONFIG)
    sftp.close()

    # 移动到正式位置
    stdout, stderr = run_sudo_command(ssh, 'mv /tmp/racoon_test.conf /etc/racoon/racoon.conf')
    stdout, stderr = run_sudo_command(ssh, 'chmod 644 /etc/racoon/racoon.conf')
    print('✅ 配置文件已更新\n')

    # 验证配置语法
    print('=' * 60)
    print('步骤3: 验证配置语法')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'racoon -f /etc/racoon/racoon.conf -C')
    if 'ERROR' in stderr or 'error' in stderr:
        print('❌ 配置文件有错误:')
        print(stderr)
    else:
        print('✅ 配置文件语法正确\n')

    # 检查PSK配置
    print('=' * 60)
    print('步骤4: 检查PSK密钥配置')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'cat /etc/racoon/psk.txt | grep 192.168.50')
    if '192.168.50.16' in stdout and '123456' in stdout:
        print('✅ PSK密钥已配置:')
        for line in stdout.strip().split('\n'):
            if '192.168.50.16' in line:
                print(f'  {line}')
    else:
        print('⚠️ 未找到路由器IP的PSK配置')
    print()

    # 重启Racoon服务
    print('=' * 60)
    print('步骤5: 重启Racoon服务')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'systemctl restart racoon')
    time.sleep(3)

    stdout, stderr = run_sudo_command(ssh, 'systemctl is-active racoon')
    if 'active' in stdout:
        print('✅ Racoon服务已重启并运行中\n')
    else:
        print('❌ Racoon服务启动失败\n')

    # 等待IPSec协商
    print('=' * 60)
    print('步骤6: 等待IPSec协商 (等待15秒)')
    print('=' * 60)
    print('提示: 请确保路由器端DMVPN配置为:')
    print('  - Phase 1: AES256 + SHA256 + DH Group 14 (modp2048)')
    print('  - Phase 2: AES256 + HMAC-SHA256')
    print('  - PSK: 123456')
    print('  - GRE密钥: 123456')
    print()

    for i in range(15, 0, -1):
        print(f'等待协商... {i}秒', end='\r')
        time.sleep(1)
    print('等待完成              \n')

    # 检查IPSec SA
    print('=' * 60)
    print('步骤7: 检查IPSec SA状态')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'setkey -D | grep -A 10 192.168.50.16')

    if stdout.strip() and '192.168.50.16' in stdout:
        print('✅ IPSec SA已建立!')
        print('\nSA详细信息:')
        print(stdout[:500])
    else:
        print('⚠️ IPSec SA尚未建立')
        print('\n查看最近的Racoon日志:')
        stdout, stderr = run_sudo_command(ssh, 'tail -15 /var/log/syslog | grep racoon')
        for line in stdout.strip().split('\n')[-10:]:
            if 'ERROR' in line or 'INFO' in line:
                print(f'  {line}')

    # 测试GRE连通性
    print('\n' + '=' * 60)
    print('步骤8: 测试GRE隧道连通性')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 4 -W 2 10.0.0.3')
    ping_output = stdout_obj.read().decode('utf-8', errors='ignore')

    if '4 received' in ping_output or '0% packet loss' in ping_output:
        print('✅ GRE隧道连通成功!')
        for line in ping_output.split('\n'):
            if 'packets transmitted' in line:
                print(f'  {line}')
    else:
        print('❌ GRE隧道不通')
        if '100% packet loss' in ping_output:
            print('  原因: 无法ping通路由器GRE IP (10.0.0.3)')
            print('  请检查:')
            print('    1. 路由器DMVPN是否启用')
            print('    2. 路由器加密参数是否匹配')
            print('    3. 路由器GRE隧道IP是否配置为 10.0.0.3')

    print('\n' + '=' * 60)
    print('配置完成!')
    print('=' * 60)
    print('\n测试配置摘要:')
    print('  - Phase 1: AES256 + SHA256 + modp2048 (DH Group 14)')
    print('  - Phase 2: AES256/AES128/3DES + HMAC-SHA256/HMAC-SHA1')
    print('  - PSK: 123456')
    print('  - GRE Key: 123456')
    print('\n如果IPSec SA未建立，请检查路由器端配置是否匹配。')

finally:
    ssh.close()
    print('\nSSH连接已关闭')
