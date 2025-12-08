# -*- coding: utf-8 -*-
import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

PASSWORD = 'milesight123'

try:
    print('=' * 60)
    print('测试GRE隧道 - 正确的IP: 10.0.0.2')
    print('=' * 60)
    print()

    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)
    print('✅ 连接服务器成功\n')

    # 测试ping 10.0.0.2
    print('测试 ping 10.0.0.2 (路由器实际GRE IP):')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 5 10.0.0.2')
    ping_output = stdout_obj.read().decode('utf-8', errors='ignore')

    print(ping_output)

    # 检查结果
    if '0% packet loss' in ping_output or '5 received' in ping_output:
        print('\n' + '=' * 60)
        print('✅✅✅ 成功！GRE隧道连通！✅✅✅')
        print('=' * 60)
        print()
        print('路由器GRE隧道IP: 10.0.0.2 ✅')
        print('服务器GRE隧道IP: 10.0.0.1 ✅')
        print()
        print('问题原因: 之前测试时使用了错误的IP 10.0.0.3')
        print('实际路由器IP: 10.0.0.2')
    else:
        print('\n⚠️ 仍然无法ping通')

    # 显示ARP表
    print('\n检查ARP缓存:')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ip neigh show dev gre1')
    arp = stdout_obj.read().decode('utf-8', errors='ignore')
    print(arp)

    # 显示当前IPSec SA状态
    print('\n检查IPSec SA状态:')
    print('=' * 60)

    def run_sudo_command(ssh, command):
        stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
        return stdout.read().decode('utf-8', errors='ignore')

    sa_output = run_sudo_command(ssh, 'setkey -D')

    if '192.168.50.16' in sa_output or '10.33.126.188' in sa_output:
        print('✅ IPSec SA已建立')

        # 提取关键信息
        for line in sa_output.split('\n'):
            if '192.168.50' in line or '10.33.126' in line:
                print(f'  {line}')
    else:
        print('⚠️ IPSec SA未建立')
        print('   说明: 路由器可能还没有重新建立IPSec连接')
        print('   建议: 在路由器上重启DMVPN服务或等待自动重连')

finally:
    ssh.close()
    print('\nSSH连接已关闭')
