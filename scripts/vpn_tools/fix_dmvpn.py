# -*- coding: utf-8 -*-
import paramiko
import sys
import io
import time

# 设置stdout为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print('正在连接服务器...')
    ssh.connect('192.168.50.48', username='yuxy', password='milesight123', timeout=10)
    print('✅ SSH连接成功\n')

    # 启动Racoon服务
    print('=' * 60)
    print('步骤1: 启动Racoon服务')
    print('=' * 60)
    stdin, stdout, stderr = ssh.exec_command('sudo systemctl start racoon')
    stdout.channel.recv_exit_status()  # 等待命令完成
    print('执行: sudo systemctl start racoon')
    time.sleep(2)

    # 检查服务状态
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active racoon')
    status = stdout.read().decode('utf-8').strip()
    print(f'服务状态: {status}')

    if status == 'active':
        print('✅ Racoon服务已启动\n')
    else:
        print('❌ Racoon服务启动失败\n')
        stdin, stdout, stderr = ssh.exec_command('sudo systemctl status racoon')
        print(stdout.read().decode('utf-8', errors='ignore'))

    # 等待IPSec协商
    print('=' * 60)
    print('步骤2: 等待IPSec协商 (10秒)')
    print('=' * 60)
    for i in range(10, 0, -1):
        print(f'等待 {i} 秒...', end='\r')
        time.sleep(1)
    print('等待完成      \n')

    # 检查IPSec SA
    print('=' * 60)
    print('步骤3: 检查IPSec SA状态')
    print('=' * 60)
    stdin, stdout, stderr = ssh.exec_command('sudo setkey -D | grep -A 5 192.168.50.16')
    sa_output = stdout.read().decode('utf-8', errors='ignore')

    if sa_output.strip():
        print('✅ IPSec SA已建立:')
        print(sa_output[:300])  # 只显示前300字符
    else:
        print('⚠️ IPSec SA尚未建立')
        print('查看最近的Racoon日志:')
        stdin, stdout, stderr = ssh.exec_command('sudo tail -10 /var/log/syslog | grep racoon')
        print(stdout.read().decode('utf-8', errors='ignore'))

    # 测试GRE连通性
    print('\n' + '=' * 60)
    print('步骤4: 测试GRE隧道连通性')
    print('=' * 60)
    stdin, stdout, stderr = ssh.exec_command('ping -c 4 -W 2 10.0.0.3')
    ping_output = stdout.read().decode('utf-8', errors='ignore')

    if '0% packet loss' in ping_output or '4 received' in ping_output:
        print('✅ GRE隧道连通正常!')
        # 只显示统计信息
        for line in ping_output.split('\n'):
            if 'packets transmitted' in line or 'rtt' in line:
                print(line)
    else:
        print('❌ GRE隧道不通')
        print(ping_output[-200:])  # 显示最后200字符

    # 设置开机自启
    print('\n' + '=' * 60)
    print('步骤5: 设置Racoon开机自启')
    print('=' * 60)
    stdin, stdout, stderr = ssh.exec_command('sudo systemctl enable racoon')
    stdout.channel.recv_exit_status()

    stdin, stdout, stderr = ssh.exec_command('systemctl is-enabled racoon')
    enabled_status = stdout.read().decode('utf-8').strip()

    if enabled_status == 'enabled':
        print('✅ 已设置开机自启')
    else:
        print(f'状态: {enabled_status}')

    print('\n' + '=' * 60)
    print('修复完成!')
    print('=' * 60)

finally:
    ssh.close()
    print('\nSSH连接已关闭')
