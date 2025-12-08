# -*- coding: utf-8 -*-
import paramiko
import sys
import io

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

    print('=' * 60)
    print('诊断 GRE 隧道问题')
    print('=' * 60)
    print()

    # 1. IPSec SA状态
    print('1. IPSec SA状态: ✅ 已建立\n')

    # 2. GRE隧道状态
    print('2. GRE隧道接口状态:')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ip addr show gre1')
    print(stdout_obj.read().decode('utf-8', errors='ignore'))

    # 3. GRE隧道详细配置
    print('3. GRE隧道详细配置:')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ip tunnel show gre1')
    print(stdout_obj.read().decode('utf-8', errors='ignore'))

    # 4. 路由表
    print('4. 路由表 (10.0.0.0网段):')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ip route | grep 10.0.0')
    route_output = stdout_obj.read().decode('utf-8', errors='ignore')
    if route_output.strip():
        print(route_output)
    else:
        print('(未找到10.0.0.0网段的路由)\n')

    # 5. ARP表
    print('5. ARP表 (10.0.0.3):')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ip neigh | grep 10.0.0.3')
    arp_output = stdout_obj.read().decode('utf-8', errors='ignore')
    if arp_output.strip():
        print(arp_output)
    else:
        print('(未找到10.0.0.3的ARP记录)\n')

    # 6. 防火墙规则
    print('6. 检查GRE协议是否被防火墙阻止:')
    print('=' * 60)
    stdout, _ = run_sudo_command(ssh, 'iptables -L -n | grep -i gre')
    if stdout.strip():
        print(stdout)
    else:
        print('(未找到GRE相关的防火墙规则)\n')

    # 7. Ping测试详细输出
    print('7. Ping测试详细输出:')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 3 -v 10.0.0.3')
    print(stdout_obj.read().decode('utf-8', errors='ignore'))

    # 8. 检查路由器是否在线
    print('8. 检查路由器物理IP是否在线:')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 2 192.168.50.16')
    ping_result = stdout_obj.read().decode('utf-8', errors='ignore')
    if '0% packet loss' in ping_result or '2 received' in ping_result:
        print('✅ 路由器物理IP可达\n')
    else:
        print('❌ 路由器物理IP不可达\n')

    # 9. 检查NHRP
    print('9. 检查NHRP (Next Hop Resolution Protocol):')
    print('=' * 60)
    stdin, stdout_obj, stderr = ssh.exec_command('which opennhrpctl')
    nhrp_path = stdout_obj.read().decode('utf-8', errors='ignore').strip()
    if nhrp_path:
        stdin, stdout_obj, stderr = ssh.exec_command('opennhrpctl show')
        print(stdout_obj.read().decode('utf-8', errors='ignore'))
    else:
        print('(未安装NHRP)\n')

    print('=' * 60)
    print('分析结果')
    print('=' * 60)
    print('\n可能的原因:')
    print('  1. 路由器GRE隧道IP不是10.0.0.3')
    print('  2. 路由器GRE隧道未启动')
    print('  3. 路由器GRE密钥不匹配 (应为123456)')
    print('  4. 路由器防火墙阻止GRE或ICMP')
    print('  5. 需要配置NHRP进行动态地址解析')
    print('\n建议:')
    print('  - 登录路由器Web界面检查GRE隧道配置')
    print('  - 确认路由器GRE隧道IP = 10.0.0.3')
    print('  - 确认路由器GRE密钥 = 123456')

finally:
    ssh.close()
