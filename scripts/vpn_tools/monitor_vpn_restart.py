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
    print('监控路由器VPN服务重启后的连接状态')
    print('=' * 70)
    print()

    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)
    print('✅ 连接服务器成功')
    print()

    print('等待路由器VPN服务重启...')
    print('=' * 70)

    # 监控60秒，每5秒检查一次
    for attempt in range(1, 13):  # 12次 x 5秒 = 60秒
        print(f'\n[检查 {attempt}/12] - {time.strftime("%H:%M:%S")}')
        print('-' * 70)

        # 1. 检查IPSec SA
        stdout, _ = run_sudo_command(ssh, 'setkey -D | grep -E "(10.33.126.188|192.168.50.16)" | head -5')

        has_sa = False
        if stdout.strip():
            has_sa = True
            print('  ✅ IPSec SA已建立')
            for line in stdout.strip().split('\n')[:3]:
                print(f'     {line}')
        else:
            print('  ⏳ IPSec SA尚未建立...')

        # 2. 如果SA建立了，测试GRE连通性
        if has_sa:
            print('\n  测试GRE隧道 (10.0.0.3):')
            stdin, stdout_obj, stderr = ssh.exec_command('ping -c 3 -W 1 10.0.0.3')
            ping_output = stdout_obj.read().decode('utf-8', errors='ignore')

            received = 0
            for line in ping_output.split('\n'):
                if 'packets transmitted' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        received = int(parts[3])
                    print(f'     {line}')

            if received >= 2:
                print('\n' + '=' * 70)
                print('🎉🎉🎉 成功！GRE隧道已连通！🎉🎉🎉')
                print('=' * 70)
                print()
                print(f'✅ IPSec SA: 已建立')
                print(f'✅ GRE隧道: 连通 ({received}/3 包)')
                print(f'✅ 路由器GRE IP: 10.0.0.3')
                print(f'✅ 服务器GRE IP: 10.0.0.1')

                # 显示ARP
                print('\nARP缓存:')
                stdin, stdout_obj, stderr = ssh.exec_command('ip neigh show dev gre1')
                arp = stdout_obj.read().decode('utf-8', errors='ignore')
                for line in arp.strip().split('\n'):
                    if '10.0.0.3' in line:
                        print(f'  {line}')

                print('\n✅ DMVPN连接完全正常！')
                break
            else:
                print('     ⏳ GRE尚未连通，继续等待...')

        # 3. 查看最新日志
        if attempt % 2 == 0:  # 每两次显示一次日志
            stdout, _ = run_sudo_command(ssh, 'tail -5 /var/log/syslog | grep racoon')
            if stdout.strip():
                recent_lines = stdout.strip().split('\n')
                if recent_lines:
                    last_line = recent_lines[-1]
                    if 'ERROR' in last_line:
                        print(f'  ❌ 日志: {last_line[-80:]}')
                    elif 'ISAKMP-SA established' in last_line or 'IPsec-SA' in last_line:
                        print(f'  ✅ 日志: {last_line[-80:]}')

        # 等待5秒
        if attempt < 12:
            print('  等待5秒...')
            time.sleep(5)

    else:
        # 超时未建立连接
        print('\n' + '=' * 70)
        print('⏰ 监控超时（60秒）')
        print('=' * 70)
        print()
        print('IPSec连接尚未建立，可能的原因:')
        print('  1. 路由器VPN服务还在重启中')
        print('  2. 路由器配置有误')
        print('  3. 网络连接问题')
        print()
        print('建议: 再等待片刻或检查路由器日志')

finally:
    ssh.close()
    print('\n' + '=' * 70)
    print('SSH连接已关闭')
    print('=' * 70)
