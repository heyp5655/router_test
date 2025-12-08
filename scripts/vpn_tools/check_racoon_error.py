# -*- coding: utf-8 -*-
import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect('192.168.50.48', username='yuxy', password='milesight123', timeout=10)

    print('检查Racoon服务为什么启动失败...\n')

    # 查看详细状态
    print('=' * 60)
    print('Racoon服务详细状态')
    print('=' * 60)
    stdin, stdout, stderr = ssh.exec_command('sudo systemctl status racoon')
    print(stdout.read().decode('utf-8', errors='ignore'))

    # 查看配置文件
    print('\n' + '=' * 60)
    print('检查配置文件语法')
    print('=' * 60)
    stdin, stdout, stderr = ssh.exec_command('sudo racoon -f /etc/racoon/racoon.conf -C')
    stdout_text = stdout.read().decode('utf-8', errors='ignore')
    stderr_text = stderr.read().decode('utf-8', errors='ignore')

    if stdout_text:
        print('stdout:', stdout_text)
    if stderr_text:
        print('stderr:', stderr_text)

    # 查看系统日志
    print('\n' + '=' * 60)
    print('最近的系统日志 (racoon相关)')
    print('=' * 60)
    stdin, stdout, stderr = ssh.exec_command('sudo journalctl -u racoon -n 30 --no-pager')
    print(stdout.read().decode('utf-8', errors='ignore'))

finally:
    ssh.close()
