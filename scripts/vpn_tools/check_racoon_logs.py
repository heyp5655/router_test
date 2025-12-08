# -*- coding: utf-8 -*-
"""
检查Racoon详细日志，分析Phase1失败原因
"""
import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVER_IP = '192.168.50.48'
USERNAME = 'yuxy'
PASSWORD = 'milesight123'

def run_sudo_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

print('=' * 80)
print('Racoon详细日志分析')
print('=' * 80)
print()

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)

    # 查看最近50条racoon日志
    print('📋 最近50条Racoon日志:')
    print('-' * 80)
    stdout, _ = run_sudo_command(ssh, 'tail -50 /var/log/syslog | grep racoon')

    for line in stdout.strip().split('\n'):
        if 'ERROR' in line:
            print(f'❌ {line}')
        elif 'ISAKMP-SA' in line or 'IPsec-SA' in line:
            print(f'✅ {line}')
        elif 'INFO' in line:
            print(f'ℹ️  {line}')
        else:
            print(f'   {line}')

    print()

    # 查看当前IPSec SA
    print('🔐 当前IPSec SA状态:')
    print('-' * 80)
    stdout, _ = run_sudo_command(ssh, 'setkey -D')

    if stdout.strip():
        print(stdout.strip())
    else:
        print('(无活动的IPSec SA)')

    print()

    # 检查PSK配置
    print('🔑 PSK密钥配置:')
    print('-' * 80)
    stdin, stdout_obj, stderr = ssh.exec_command('cat /etc/racoon/psk.txt')
    psk_content = stdout_obj.read().decode('utf-8', errors='ignore')

    for line in psk_content.strip().split('\n'):
        if line.strip() and not line.startswith('#'):
            print(f'  {line}')

    print()

    # 检查Racoon配置
    print('⚙️ Racoon关键配置:')
    print('-' * 80)
    stdin, stdout_obj, stderr = ssh.exec_command('grep -A 10 "nat_traversal" /etc/racoon/racoon.conf')
    print(stdout_obj.read().decode('utf-8', errors='ignore'))

    ssh.close()

except Exception as e:
    print(f'❌ 错误: {e}')
