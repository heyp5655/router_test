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
    print('=' * 60)
    print('测试路由器GRE IP改为10.0.0.3后的连通性')
    print('=' * 60)
    print()

    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)
    print('✅ 连接服务器成功\n')

    # 清除旧的ARP缓存
    print('清除旧的ARP缓存...')
    stdin, stdout_obj, stderr = ssh.exec_command('ip neigh flush dev gre1')
    time.sleep(1)
    print('✅ 已清除\n')

    # 1. 检查IPSec SA状态
    print('1️⃣  检查IPSec SA状态')
    print('=' * 60)
    stdout, _ = run_sudo_command(ssh, 'setkey -D')

    if '10.33.126.188' in stdout or '192.168.50.16' in stdout:
        print('✅ IPSec SA已建立\n')

        # 显示SA信息
        lines = stdout.split('\n')
        for i, line in enumerate(lines):
            if '10.33.126.188' in line or '192.168.50.16' in line:
                print(f'  {line}')
                for j in range(1, min(4, len(lines) - i)):
                    if lines[i+j].strip() and ('esp' in lines[i+j] or 'aes' in lines[i+j]):
                        print(f'  {lines[i+j]}')
                break
    else:
        print('⚠️ IPSec SA未建立')
        print('   说明: 路由器可能正在重新连接')
        print('   等待20秒后重试...\n')

        time.sleep(20)

        stdout, _ = run_sudo_command(ssh, 'setkey -D')
        if '10.33.126.188' in stdout or '192.168.50.16' in stdout:
            print('✅ IPSec SA已建立（第二次检查）\n')
        else:
            print('❌ IPSec SA仍未建立\n')

    # 2. 测试GRE隧道连通性
    print('\n2️⃣  测试GRE隧道连通性 (10.0.0.3)')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 5 -W 2 10.0.0.3')
    ping_output = stdout_obj.read().decode('utf-8', errors='ignore')

    print(ping_output)

    # 统计结果
    received = 0
    for line in ping_output.split('\n'):
        if 'packets transmitted' in line:
            parts = line.split()
            if len(parts) >= 4:
                received = int(parts[3])

    if received >= 4:
        print('\n' + '=' * 60)
        print('✅✅✅ 成功！GRE隧道完全连通！✅✅✅')
        print('=' * 60)
        print()
        print('路由器GRE IP: 10.0.0.3 ✅')
        print('服务器GRE IP: 10.0.0.1 ✅')
        print(f'连通性: {received}/5 包成功')
    elif received > 0:
        print(f'\n⚠️ 部分连通 ({received}/5 包)')
        print('   可能需要等待ARP缓存更新')
    else:
        print('\n❌ GRE隧道不通 (0/5 包)')
        print('   可能的原因:')
        print('   1. 路由器配置还未生效')
        print('   2. 路由器需要重启DMVPN服务')
        print('   3. 检查路由器GRE配置是否正确保存')

    # 3. 显示ARP缓存
    print('\n3️⃣  ARP缓存')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ip neigh show dev gre1')
    arp = stdout_obj.read().decode('utf-8', errors='ignore')
    if arp.strip():
        print(arp)
    else:
        print('(无ARP缓存条目)')

    # 4. 显示GRE接口统计
    print('\n4️⃣  GRE接口流量统计')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ip -s link show gre1 | grep -A 2 "RX:"')
    stats = stdout_obj.read().decode('utf-8', errors='ignore')
    print(stats)

    print('\n' + '=' * 60)
    print('测试完成')
    print('=' * 60)

finally:
    ssh.close()
    print('\nSSH连接已关闭')
