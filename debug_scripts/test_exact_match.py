# -*- coding: utf-8 -*-
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

PASSWORD = 'milesight123'

# 精确匹配路由器配置的Racoon配置
# Phase 1: Main Mode + AES256 + SHA256 + modp2048
# Phase 2: AES256 + SHA256 + NO PFS
RACOON_CONFIG = """#
# Racoon配置 - 精确匹配路由器参数
# 测试日期: 2025-11-27
#
# Phase 1: Main Mode, AES256, SHA256, modp2048 (DH Group 14)
# Phase 2: AES256, SHA256, PFS=null
# PSK: 123456
# GRE Key: 123456
#
log notify;
path include "/etc/racoon/";
path pre_shared_key "/etc/racoon/psk.txt";

remote anonymous {
        exchange_mode main;                     # 仅使用 Main Mode
        lifetime time 10800 seconds;
        my_identifier address;
        dpd_delay 30;
        dpd_retry 3;
        dpd_maxfail 6;
        nat_traversal on;

        # 精确匹配: AES256 + SHA256 + modp2048 (DH Group 14)
        proposal {
                encryption_algorithm aes 256;   # AES256
                hash_algorithm sha256;          # SHA256
                dh_group modp2048;              # DH Group 14
                authentication_method pre_shared_key;
        }
}

sainfo anonymous {
        lifetime time 3600 seconds;
        compression_algorithm deflate;
        # 不使用PFS (注释掉pfs_group)
        # pfs_group modp2048;

        # Phase 2: AES256 + HMAC-SHA256
        encryption_algorithm aes 256;           # 仅AES256
        authentication_algorithm hmac_sha256;   # 仅SHA256
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
    print('步骤2: 写入新配置 (精确匹配路由器参数)')
    print('=' * 60)
    print('配置参数:')
    print('  Phase 1: Main Mode, AES256, SHA256, modp2048 (DH14)')
    print('  Phase 2: AES256, SHA256, PFS=null')
    print()

    # 使用临时文件
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/racoon_exact.conf', 'w') as f:
        f.write(RACOON_CONFIG)
    sftp.close()

    # 移动到正式位置
    stdout, stderr = run_sudo_command(ssh, 'mv /tmp/racoon_exact.conf /etc/racoon/racoon.conf')
    stdout, stderr = run_sudo_command(ssh, 'chmod 644 /etc/racoon/racoon.conf')
    print('✅ 配置文件已更新\n')

    # 显示配置内容
    print('=' * 60)
    print('步骤3: 验证配置内容')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'cat /etc/racoon/racoon.conf')
    print(stdout)

    # 验证配置语法
    print('=' * 60)
    print('步骤4: 验证配置语法')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'racoon -f /etc/racoon/racoon.conf -C')
    if 'ERROR' in stderr or 'error' in stderr:
        print('❌ 配置文件有错误:')
        print(stderr)
        print('\n尝试查看详细错误:')
        stdout, stderr = run_sudo_command(ssh, 'racoon -f /etc/racoon/racoon.conf -F')
        print(stderr)
    else:
        print('✅ 配置文件语法正确\n')

    # 重启Racoon服务
    print('=' * 60)
    print('步骤5: 重启Racoon服务')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'systemctl restart racoon')
    time.sleep(3)

    stdout, stderr = run_sudo_command(ssh, 'systemctl is-active racoon')
    if 'active' in stdout:
        print('✅ Racoon服务已重启并运行中')

        # 查看服务详细状态
        stdout, stderr = run_sudo_command(ssh, 'systemctl status racoon | head -15')
        print('\n服务状态:')
        print(stdout)
    else:
        print('❌ Racoon服务启动失败')
        stdout, stderr = run_sudo_command(ssh, 'systemctl status racoon')
        print(stdout)

    # 等待IPSec协商
    print('\n' + '=' * 60)
    print('步骤6: 等待IPSec协商 (20秒)')
    print('=' * 60)
    print('路由器配置应该为:')
    print('  Phase 1: Main Mode, AES256, SHA2-256, modp2048-14')
    print('  Phase 2: AES256-SHA256, PFS=null')
    print('  PSK: 123456')
    print()

    for i in range(20, 0, -1):
        print(f'等待协商... {i}秒', end='\r')
        time.sleep(1)
    print('等待完成              \n')

    # 检查IPSec SA
    print('=' * 60)
    print('步骤7: 检查IPSec SA状态')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'setkey -D')

    if '192.168.50.16' in stdout:
        print('✅ IPSec SA已建立!')
        print('\nSA详细信息:')
        # 提取192.168.50.16相关的部分
        for line in stdout.split('\n'):
            if '192.168.50' in line or 'esp' in line or 'aes' in line or 'sha256' in line:
                print(f'  {line}')
    else:
        print('⚠️ IPSec SA尚未建立')
        print(f'\n完整SA输出 (前500字符):')
        print(stdout[:500])

    # 查看详细日志
    print('\n' + '=' * 60)
    print('步骤8: 查看Racoon详细日志')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'tail -30 /var/log/syslog | grep racoon')

    has_error = False
    has_success = False
    for line in stdout.strip().split('\n')[-15:]:
        if 'ERROR' in line:
            has_error = True
            print(f'  ❌ {line}')
        elif 'ISAKMP-SA established' in line or 'IPsec-SA established' in line:
            has_success = True
            print(f'  ✅ {line}')
        elif 'INFO' in line:
            print(f'  ℹ️  {line}')

    if has_success:
        print('\n✅ 在日志中发现成功建立SA的记录!')
    elif has_error:
        print('\n❌ 仍然存在协商错误')

    # 测试GRE连通性
    print('\n' + '=' * 60)
    print('步骤9: 测试GRE隧道连通性')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 5 -W 2 10.0.0.3')
    ping_output = stdout_obj.read().decode('utf-8', errors='ignore')

    received_count = 0
    for line in ping_output.split('\n'):
        if 'packets transmitted' in line:
            parts = line.split()
            if len(parts) >= 4:
                received_count = int(parts[3])
            print(f'\n结果: {line}')

    if received_count > 0:
        print(f'✅ GRE隧道连通! (收到 {received_count}/5 个回包)')
    else:
        print('❌ GRE隧道不通 (0/5 个回包)')

    print('\n' + '=' * 60)
    print('测试完成!')
    print('=' * 60)

finally:
    ssh.close()
    print('\nSSH连接已关闭')
