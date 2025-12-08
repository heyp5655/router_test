# -*- coding: utf-8 -*-
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

PASSWORD = 'milesight123'

def run_sudo_command(ssh, command):
    """执行需要sudo的命令"""
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

try:
    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)

    print('检查Racoon服务问题...\n')

    # 尝试启动服务
    print('=' * 60)
    print('步骤1: 尝试启动Racoon')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'systemctl start racoon')
    if stderr and 'password' not in stderr.lower():
        print('错误信息:', stderr)
    time.sleep(2)

    # 查看详细状态
    stdout, stderr = run_sudo_command(ssh, 'systemctl status racoon')
    print(stdout)

    # 查看配置文件语法
    print('\n' + '=' * 60)
    print('步骤2: 检查配置文件')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'racoon -f /etc/racoon/racoon.conf -C')
    if stdout:
        print('输出:', stdout)
    if stderr and 'password' not in stderr.lower():
        print('错误:', stderr)

    # 查看日志
    print('\n' + '=' * 60)
    print('步骤3: 查看最近日志')
    print('=' * 60)
    stdout, stderr = run_sudo_command(ssh, 'tail -30 /var/log/syslog | grep racoon')
    if stdout.strip():
        print(stdout)
    else:
        print('(无racoon日志)')

    # 检查端口占用
    print('\n' + '=' * 60)
    print('步骤4: 检查UDP 500端口')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('netstat -uln | grep :500')
    stdout = stdout_obj.read().decode('utf-8', errors='ignore')
    if stdout.strip():
        print('端口状态:')
        print(stdout)
    else:
        print('UDP 500端口未监听')

finally:
    ssh.close()
