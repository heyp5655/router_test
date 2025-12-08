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
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

try:
    print('=' * 70)
    print('检查路由器 10.33.126.188 的连接状态')
    print('=' * 70)
    print()

    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)
    print('✅ 连接服务器成功\n')

    # 1. 检查最近的日志中是否有10.33.126.188
    print('1️⃣  搜索日志中的 10.33.126.188')
    print('=' * 70)
    stdout, _ = run_sudo_command(ssh, 'tail -100 /var/log/syslog | grep "10.33.126.188"')

    if stdout.strip():
        print('✅ 找到来自 10.33.126.188 的连接记录:')
        for line in stdout.strip().split('\n')[-10:]:
            if 'ERROR' in line:
                print(f'  ❌ {line}')
            elif 'INFO' in line:
                print(f'  ℹ️  {line}')
            else:
                print(f'     {line}')
    else:
        print('❌ 未找到来自 10.33.126.188 的连接记录')
        print('   说明: 路由器可能还没有尝试连接到服务器\n')

    # 2. 检查UDP 500端口的连接
    print('\n2️⃣  检查UDP 500端口（IPSec）的连接')
    print('=' * 70)
    stdin, stdout_obj, stderr = ssh.exec_command('netstat -un | grep ":500"')
    netstat_output = stdout_obj.read().decode('utf-8', errors='ignore')

    if '10.33.126.188' in netstat_output:
        print('✅ 找到来自 10.33.126.188 的UDP连接:')
        for line in netstat_output.split('\n'):
            if '10.33.126.188' in line:
                print(f'  {line}')
    else:
        print('❌ 未找到来自 10.33.126.188 的UDP连接')

    # 3. 测试能否ping通路由器
    print('\n3️⃣  测试能否ping通路由器 10.33.126.188')
    print('=' * 70)
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 3 -W 2 10.33.126.188')
    ping_output = stdout_obj.read().decode('utf-8', errors='ignore')

    if '0% packet loss' in ping_output or '3 received' in ping_output:
        print('✅ 可以ping通 10.33.126.188')
        for line in ping_output.split('\n'):
            if 'transmitted' in line:
                print(f'  {line}')
    else:
        print('❌ 无法ping通 10.33.126.188')
        for line in ping_output.split('\n'):
            if 'transmitted' in line or 'Unreachable' in line:
                print(f'  {line}')

    # 4. 检查所有近期的IPSec尝试
    print('\n4️⃣  最近的IPSec连接尝试')
    print('=' * 70)
    stdout, _ = run_sudo_command(ssh, 'tail -50 /var/log/syslog | grep -E "(respond new phase|INFO:.*<=>)"')

    if stdout.strip():
        print('最近的连接尝试:')
        for line in stdout.strip().split('\n')[-10:]:
            print(f'  {line}')
    else:
        print('(无最近的连接尝试记录)')

    # 5. 查看PSK配置
    print('\n5️⃣  验证PSK配置')
    print('=' * 70)
    stdout, _ = run_sudo_command(ssh, 'grep "10.33.126.188" /etc/racoon/psk.txt')

    if stdout.strip():
        print('✅ PSK配置存在:')
        print(f'  {stdout.strip()}')
    else:
        print('❌ PSK配置不存在！')
        print('   这可能是问题的原因！')

    # 6. 实时监控新连接（10秒）
    print('\n6️⃣  实时监控新连接（10秒）')
    print('=' * 70)
    print('请在路由器上触发DMVPN连接...')
    print('监控中...\n')

    # 记录当前日志位置
    stdin, stdout_obj, stderr = ssh.exec_command('wc -l /var/log/syslog')
    start_lines = int(stdout_obj.read().decode('utf-8').strip().split()[0])

    time.sleep(10)

    # 查看新增的日志
    stdout, _ = run_sudo_command(ssh, f'tail -n +{start_lines} /var/log/syslog | grep -E "(racoon|10.33.126.188)"')

    if stdout.strip():
        print('✅ 检测到新的日志:')
        for line in stdout.strip().split('\n'):
            if '10.33.126.188' in line:
                print(f'  🎯 {line}')
            elif 'ERROR' in line:
                print(f'  ❌ {line}')
            elif 'INFO' in line:
                print(f'  ℹ️  {line}')
    else:
        print('❌ 10秒内未检测到新的连接尝试')
        print('   说明: 路由器可能没有尝试连接')

    print('\n' + '=' * 70)
    print('诊断完成')
    print('=' * 70)
    print('\n如果路由器 10.33.126.188 完全没有连接记录，请检查:')
    print('  1. 路由器DMVPN是否真的启用了')
    print('  2. 路由器中配置的服务器IP是否正确（192.168.50.48）')
    print('  3. 路由器是否有正确的出口路由')
    print('  4. 路由器防火墙是否阻止了UDP 500端口')

finally:
    ssh.close()
    print('\nSSH连接已关闭')
