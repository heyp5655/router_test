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
    print('=' * 70)
    print('服务器DMVPN连接日志详细排查')
    print('=' * 70)
    print()

    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)

    # 1. IPSec SA状态
    print('1️⃣  IPSec SA状态')
    print('=' * 70)
    stdout, _ = run_sudo_command(ssh, 'setkey -D')
    if '10.33.126.188' in stdout or '192.168.50.16' in stdout:
        print('✅ IPSec SA已建立\n')

        # 显示SA详情
        lines = stdout.split('\n')
        for i, line in enumerate(lines):
            if '10.33.126.188' in line or '192.168.50.16' in line:
                print(f'  {line}')
                for j in range(1, min(6, len(lines) - i)):
                    if lines[i+j].strip():
                        print(f'  {lines[i+j]}')
                    else:
                        break
                print()
    else:
        print('❌ 未找到IPSec SA\n')

    # 2. GRE隧道状态
    print('\n2️⃣  GRE隧道状态')
    print('=' * 70)
    stdin, stdout_obj, stderr = ssh.exec_command('ip addr show gre1')
    gre_output = stdout_obj.read().decode('utf-8', errors='ignore')
    print(gre_output)

    stdin, stdout_obj, stderr = ssh.exec_command('ip tunnel show gre1')
    tunnel_output = stdout_obj.read().decode('utf-8', errors='ignore')
    print('GRE隧道配置:')
    print(tunnel_output)

    # 3. 检查GRE流量统计
    print('\n3️⃣  GRE接口流量统计')
    print('=' * 70)
    stdin, stdout_obj, stderr = ssh.exec_command('ip -s link show gre1')
    stats = stdout_obj.read().decode('utf-8', errors='ignore')
    print(stats)

    # 4. Racoon最近日志（最近50行）
    print('\n4️⃣  Racoon最近日志')
    print('=' * 70)
    stdout, _ = run_sudo_command(ssh, 'tail -50 /var/log/syslog | grep -E "(racoon|10.33.126.188|192.168.50.16)"')
    log_lines = stdout.strip().split('\n')

    print('最近的重要日志:')
    for line in log_lines[-30:]:
        if 'ISAKMP-SA established' in line:
            print(f'  ✅ {line}')
        elif 'IPsec-SA established' in line:
            print(f'  ✅ {line}')
        elif 'ERROR' in line:
            print(f'  ❌ {line}')
        elif '10.33.126.188' in line or 'INFO' in line:
            print(f'  ℹ️  {line}')

    # 5. 检查NHRP状态（如果有）
    print('\n5️⃣  NHRP状态')
    print('=' * 70)
    stdin, stdout_obj, stderr = ssh.exec_command('which opennhrpctl')
    if stdout_obj.read().decode('utf-8', errors='ignore').strip():
        stdin, stdout_obj, stderr = ssh.exec_command('opennhrpctl show')
        nhrp_output = stdout_obj.read().decode('utf-8', errors='ignore')
        if nhrp_output.strip():
            print(nhrp_output)
        else:
            print('(NHRP未运行或无条目)')
    else:
        print('(未安装NHRP)')

    # 6. 测试路由器物理IP连通性
    print('\n6️⃣  测试路由器物理IP连通性')
    print('=' * 70)

    print('测试 10.33.126.188:')
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 3 -W 2 10.33.126.188')
    ping1 = stdout_obj.read().decode('utf-8', errors='ignore')
    if '0% packet loss' in ping1 or '3 received' in ping1:
        print('  ✅ 可以ping通 10.33.126.188')
    else:
        print('  ❌ 无法ping通 10.33.126.188')
        for line in ping1.split('\n'):
            if 'transmitted' in line:
                print(f'     {line}')

    print('\n测试 192.168.50.16:')
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 3 -W 2 192.168.50.16')
    ping2 = stdout_obj.read().decode('utf-8', errors='ignore')
    if '0% packet loss' in ping2 or '3 received' in ping2:
        print('  ✅ 可以ping通 192.168.50.16')
    else:
        print('  ❌ 无法ping通 192.168.50.16')

    # 7. 测试GRE隧道IP
    print('\n7️⃣  测试GRE隧道IP (10.0.0.3)')
    print('=' * 70)
    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 3 -W 2 10.0.0.3')
    ping_gre = stdout_obj.read().decode('utf-8', errors='ignore')

    for line in ping_gre.split('\n'):
        if 'transmitted' in line or 'Unreachable' in line:
            print(f'  {line}')

    # 8. 检查路由表
    print('\n8️⃣  路由表')
    print('=' * 70)
    stdin, stdout_obj, stderr = ssh.exec_command('ip route | grep -E "(10.0.0|gre)"')
    routes = stdout_obj.read().decode('utf-8', errors='ignore')
    if routes.strip():
        print(routes)
    else:
        print('(未找到相关路由)')

    # 9. 检查ARP缓存
    print('\n9️⃣  ARP缓存')
    print('=' * 70)
    stdin, stdout_obj, stderr = ssh.exec_command('ip neigh show dev gre1')
    arp = stdout_obj.read().decode('utf-8', errors='ignore')
    if arp.strip():
        print(arp)
    else:
        print('(无ARP缓存条目)')

    # 10. 抓包检查GRE流量
    print('\n🔟  检查GRE数据包（抓包5秒）')
    print('=' * 70)
    print('正在抓包，请稍候...')
    stdin, stdout_obj, stderr = ssh.exec_command('timeout 5 tcpdump -i any proto gre -c 5 2>&1 || true')
    tcpdump = stdout_obj.read().decode('utf-8', errors='ignore')

    if 'GRE' in tcpdump or 'gre' in tcpdump:
        print('✅ 检测到GRE数据包:')
        for line in tcpdump.split('\n')[-10:]:
            if line.strip():
                print(f'  {line}')
    else:
        print('⚠️ 未检测到GRE数据包')
        if tcpdump.strip():
            print('输出:')
            for line in tcpdump.split('\n')[-5:]:
                if line.strip():
                    print(f'  {line}')

    # 11. 分析结果
    print('\n' + '=' * 70)
    print('问题分析')
    print('=' * 70)

    # 检查关键指标
    has_ipsec_sa = '10.33.126.188' in stdout or '192.168.50.16' in stdout
    can_ping_physical = '0% packet loss' in ping1 or '0% packet loss' in ping2
    can_ping_gre = '0% packet loss' in ping_gre
    has_gre_packets = 'GRE' in tcpdump or 'gre' in tcpdump

    print()
    if has_ipsec_sa:
        print('✅ IPSec SA已建立 - 安全隧道正常')
    else:
        print('❌ IPSec SA未建立 - 安全隧道异常')

    if can_ping_physical:
        print('✅ 可以ping通路由器物理IP - 网络连接正常')
    else:
        print('❌ 无法ping通路由器物理IP - 网络连接异常')

    if can_ping_gre:
        print('✅ 可以ping通GRE隧道IP - GRE隧道正常')
    else:
        print('❌ 无法ping通GRE隧道IP - GRE隧道异常')

    if has_gre_packets:
        print('✅ 检测到GRE数据包 - GRE流量正常')
    else:
        print('⚠️ 未检测到GRE数据包 - GRE流量异常或为空')

    print('\n可能的问题:')

    if not can_ping_gre and has_ipsec_sa:
        print('  1. 路由器GRE隧道IP可能不是10.0.0.3')
        print('  2. 路由器GRE隧道可能未启动')
        print('  3. 路由器GRE密钥可能不是123456')
        print('  4. 路由器到服务器的GRE流量被防火墙阻止')

    if not has_ipsec_sa:
        print('  1. 路由器未连接到服务器')
        print('  2. 加密参数不匹配')
        print('  3. PSK密钥不正确')

finally:
    ssh.close()
    print('\nSSH连接已关闭')
