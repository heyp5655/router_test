# -*- coding: utf-8 -*-
"""
持续监控服务器，等待4G路由器通过公网连接
路由器4G网络 => 公网112.48.19.183 => NAT => 服务器192.168.50.48
"""
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVER_IP = '192.168.50.48'
USERNAME = 'yuxy'
PASSWORD = 'milesight123'

def run_sudo_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

print('=' * 80)
print('4G路由器通过公网连接 - NAT配置诊断')
print('=' * 80)
print()

print('📡 网络拓扑:')
print('-' * 80)
print('  路由器(4G) => Internet => 112.48.19.183 => NAT => 192.168.50.48(服务器)')
print('-' * 80)
print()

print('❌ 当前问题:')
print('  路由器发送: 10.9.139.97:500 => 112.48.19.183:500')
print('  NAT配置: 112.48.19.183:11025 => 192.168.50.48:500')
print('  结果: 数据包发到500端口，但NAT只监听11025，丢弃！')
print()

print('✅ 必须修改NAT端口映射:')
print('=' * 80)
print()
print('  在NAT网关上配置（删除旧的，添加新的）:')
print()
print('  【删除】')
print('    112.48.19.183:11025 → 192.168.50.48:500   ❌ 删除')
print('    112.48.19.183:11026 → 192.168.50.48:4500  ❌ 删除')
print('    112.48.19.183:11027 → 192.168.50.48:50    ❌ 删除')
print('    112.48.19.183:11028 → 192.168.50.48:47    ❌ 删除')
print()
print('  【添加】')
print('    外部端口 500  → 192.168.50.48:500   ✅ 新增 (IKE)')
print('    外部端口 4500 → 192.168.50.48:4500  ✅ 新增 (NAT-T)')
print()
print('=' * 80)
print()

print('💡 为什么必须用标准端口？')
print('-' * 80)
print('  - IPSec协议标准规定IKE使用UDP 500')
print('  - Racoon无法配置监听11025等自定义端口')
print('  - 路由器也期望连接Hub的500端口')
print('  - 这是协议层面的限制，无法绕过')
print()

print('⏰ 开始监控服务器（等待NAT配置修改完成）...')
print()

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)
    print('✅ SSH连接成功')
    print()

    print('📡 开始监控（持续10分钟）...')
    print('=' * 80)
    print()

    for i in range(1, 121):  # 120次 x 5秒 = 10分钟
        current_time = time.strftime("%H:%M:%S")
        print(f'\r[检查 {i}/120] - {current_time}', end='', flush=True)

        # 检查IPSec SA
        stdout, stderr = run_sudo_command(ssh, 'setkey -D | grep -E "10.9.139" | head -3')

        if '10.9.139' in stdout:
            print()
            print()
            print('=' * 80)
            print('🎉🎉🎉 路由器已连接！🎉🎉🎉')
            print('=' * 80)
            print()
            print('IPSec SA详情:')
            for line in stdout.strip().split('\n')[:8]:
                print(f'  {line}')

            # 测试GRE
            print()
            print('测试GRE隧道 (10.0.0.3):')
            stdin, stdout_obj, stderr_obj = ssh.exec_command('ping -c 4 10.0.0.3')
            ping = stdout_obj.read().decode('utf-8', errors='ignore')

            received = 0
            for line in ping.split('\n'):
                if 'transmitted' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        received = int(parts[3])
                    print(f'  {line}')

            print()
            if received >= 2:
                print('✅ DMVPN完全连通！')
                print('✅ 服务器 10.0.0.1 <=> 路由器 10.0.0.3')
                print()
                print('🎯 连接成功参数:')
                print('  - Hub: 112.48.19.183')
                print('  - Phase 1: AES256, SHA256, modp3072')
                print('  - Phase 2: AES256, HMAC-SHA256')
                print('  - PSK: 123456')
            else:
                print('⚠️ IPSec已建立，但GRE尚未连通')
                print('   继续等待...')

            if received >= 2:
                break

        # 每10次检查显示一次日志
        if i % 10 == 0:
            print()
            stdout, stderr = run_sudo_command(ssh, 'tail -3 /var/log/syslog | grep racoon')
            if stdout.strip():
                lines = stdout.strip().split('\n')
                for line in lines[-2:]:
                    if '10.9.139.97' in line or '112.48.19.183' in line:
                        if 'ERROR' in line:
                            print(f'  ⚠️ {line[-80:]}')
                        elif 'ISAKMP-SA established' in line:
                            print(f'  ✅ {line[-80:]}')
                        elif 'INFO' in line:
                            print(f'  ℹ️  {line[-80:]}')
            print(f'  [{i}/120] 继续监控...', end='', flush=True)

        time.sleep(5)
    else:
        print()
        print()
        print('=' * 80)
        print('⏰ 10分钟监控结束')
        print('=' * 80)
        print()
        print('未检测到连接，请确认:')
        print('  1. ✅ NAT端口映射已修改为 500→500, 4500→4500')
        print('  2. ✅ 路由器Hub地址为 112.48.19.183')
        print('  3. ✅ 路由器DMVPN已启用并重启')
        print()
        print('查看服务器日志:')
        print('  sudo tail -f /var/log/syslog | grep racoon')

    ssh.close()
    print()
    print('SSH连接已关闭')

except KeyboardInterrupt:
    print()
    print()
    print('⚠️ 监控已中断')
except Exception as e:
    print()
    print(f'❌ 错误: {e}')
    import traceback
    traceback.print_exc()
