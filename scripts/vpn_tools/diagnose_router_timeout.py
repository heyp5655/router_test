# -*- coding: utf-8 -*-
"""
紧急：路由器正在尝试连接112.48.19.183但超时
需要改为192.168.50.48（私网直连）
"""
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVER_IP = '192.168.50.48'
USERNAME = 'yuxy'
PASSWORD = 'milesight123'

print('=' * 80)
print('紧急分析：路由器Phase1超时问题')
print('=' * 80)
print()

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)

    print('📋 路由器日志分析:')
    print('-' * 80)
    print('  路由器尝试连接: 10.9.139.97[500] => 112.48.19.183[500]')
    print('  结果: phase1 negotiation failed due to time up')
    print('  原因: 路由器发送到112.48.19.183:500，但NAT未映射该端口')
    print()

    print('❌ 当前NAT端口映射:')
    print('  112.48.19.183:11025 → 192.168.50.48:500  (路由器不会连11025)')
    print('  112.48.19.183:11026 → 192.168.50.48:4500 (路由器不会连11026)')
    print()

    print('✅ 解决方案A - 路由器改为直连私网IP (推荐):')
    print('-' * 80)
    print('  在路由器Web界面修改:')
    print('    Hub地址: 112.48.19.183 → 192.168.50.48')
    print()
    print('  优点: 无需改NAT，立即生效')
    print('  前提: 路由器能ping通192.168.50.48')
    print()

    print('✅ 解决方案B - 修改NAT端口映射:')
    print('-' * 80)
    print('  在NAT网关上修改:')
    print('    删除: 112.48.19.183:11025 → 192.168.50.48:500')
    print('    删除: 112.48.19.183:11026 → 192.168.50.48:4500')
    print('    新增: 112.48.19.183:500 → 192.168.50.48:500')
    print('    新增: 112.48.19.183:4500 → 192.168.50.48:4500')
    print()

    # 检查路由器是否能连接到私网IP
    print('🔍 测试路由器10.9.139.97连通性:')
    print('-' * 80)

    stdin, stdout_obj, stderr = ssh.exec_command('ping -c 3 -W 2 10.9.139.97')
    ping_result = stdout_obj.read().decode('utf-8', errors='ignore')

    if '0% packet loss' in ping_result or '3 received' in ping_result:
        print('  ✅ 服务器能ping通路由器10.9.139.97')
        print('  ✅ 说明双方在同一网络或路由可达')
        print('  ✅ 推荐: 让路由器直连192.168.50.48')
        can_connect = True
    else:
        print('  ❌ 服务器无法ping通路由器10.9.139.97')
        print('  ⚠️ 路由器可能在不同网络')
        print('  ⚠️ 必须使用方案B修改NAT端口映射')
        can_connect = False

    print()

    if can_connect:
        print('🎯 推荐操作（最快）:')
        print('=' * 80)
        print()
        print('1. 登录路由器Web界面')
        print('2. 进入DMVPN配置页面')
        print('3. 修改Hub地址:')
        print('   当前: 112.48.19.183')
        print('   改为: 192.168.50.48')
        print('4. 保存并应用')
        print()
        print('预计1分钟内连接成功！')
    else:
        print('🎯 必须修改NAT:')
        print('=' * 80)
        print()
        print('在NAT网关上配置标准端口映射:')
        print('  外部端口500 → 192.168.50.48:500')
        print('  外部端口4500 → 192.168.50.48:4500')

    print()
    print('📡 我现在开始持续监控服务器，等待路由器连接...')
    print('=' * 80)
    print()

    # 持续监控
    for i in range(1, 61):  # 60次 x 5秒 = 5分钟
        print(f'[检查 {i}/60] - {time.strftime("%H:%M:%S")}', end='')

        # 检查IPSec SA
        stdout, _ = ssh.exec_command('sudo setkey -D | grep -E "10.9.139" | head -3')
        sa_output = stdout.read().decode('utf-8', errors='ignore')

        if '10.9.139' in sa_output:
            print(' ✅ 检测到SA!')
            print()
            print('=' * 80)
            print('🎉🎉🎉 路由器已连接！🎉🎉🎉')
            print('=' * 80)
            print()
            print('IPSec SA:')
            for line in sa_output.strip().split('\n')[:5]:
                print(f'  {line}')

            # 测试GRE
            print()
            print('测试GRE隧道:')
            stdin, stdout_obj, stderr = ssh.exec_command('ping -c 4 10.0.0.3')
            ping = stdout_obj.read().decode('utf-8', errors='ignore')

            for line in ping.split('\n'):
                if 'transmitted' in line:
                    print(f'  {line}')

            if '0% packet loss' in ping:
                print()
                print('✅ DMVPN完全连通！')
                print('✅ 服务器10.0.0.1 <=> 路由器10.0.0.3')

            break

        # 检查日志
        stdout, _ = ssh.exec_command('sudo tail -2 /var/log/syslog | grep racoon')
        log = stdout.read().decode('utf-8', errors='ignore')

        if '10.9.139.97' in log or '112.48.19.183' in log:
            if 'ISAKMP-SA established' in log:
                print(' ✅ IKE建立中...')
            elif 'ERROR' in log:
                print(' ⚠️ 仍有错误')
            else:
                print(' ⏳ 等待...')
        else:
            print(' ⏳ 等待...')

        time.sleep(5)
    else:
        print()
        print('=' * 80)
        print('⏰ 5分钟监控结束，未检测到连接')
        print('=' * 80)
        print()
        print('请确认:')
        if can_connect:
            print('  1. 路由器Hub地址已改为 192.168.50.48')
        else:
            print('  1. NAT端口映射已修改为标准端口500/4500')
        print('  2. 路由器DMVPN已重新启用')

    ssh.close()

except Exception as e:
    print(f'❌ 错误: {e}')
    import traceback
    traceback.print_exc()
