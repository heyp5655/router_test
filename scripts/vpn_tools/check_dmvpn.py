# -*- coding: utf-8 -*-
import paramiko
import sys
import io

# 设置stdout为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect('192.168.50.48', username='yuxy', password='milesight123', timeout=10)

    # Racoon服务状态
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active racoon')
    racoon_status = stdout.read().decode('utf-8').strip()

    print('【问题诊断】')
    print()
    print(f'1. Racoon服务状态: {racoon_status}')

    # IPSec SA
    stdin, stdout, stderr = ssh.exec_command('sudo setkey -D')
    sa_output = stdout.read().decode('utf-8', errors='ignore')

    if '192.168.50.16' in sa_output or '192.168.50.40' in sa_output:
        print('2. IPSec SA: 已建立')
    else:
        print('2. IPSec SA: ❌ 未建立')

    # GRE连通性
    stdin, stdout, stderr = ssh.exec_command('ping -c 1 -W 1 10.0.0.3 > /dev/null 2>&1 && echo OK || echo FAIL')
    gre_test = stdout.read().decode('utf-8').strip()
    print(f'3. GRE连通性 (10.0.0.3): {"✅ 正常" if gre_test == "OK" else "❌ 不通"}')

    # 物理IP连通性
    stdin, stdout, stderr = ssh.exec_command('ping -c 1 -W 1 192.168.50.16 > /dev/null 2>&1 && echo OK || echo FAIL')
    physical_test = stdout.read().decode('utf-8').strip()
    print(f'4. 物理IP连通性 (192.168.50.16): {"✅ 正常" if physical_test == "OK" else "❌ 不通"}')

    print()
    print('【具体错误日志】')
    stdin, stdout, stderr = ssh.exec_command('sudo tail -20 /var/log/syslog | grep racoon')
    recent_logs = stdout.read().decode('utf-8', errors='ignore')
    if recent_logs.strip():
        for line in recent_logs.strip().split('\n')[-5:]:
            print('  ' + line)
    else:
        print('  (无最近日志)')

    print()
    print('【结论】')
    if racoon_status != 'active':
        print('🔴 Racoon服务未运行，需要启动服务: sudo systemctl start racoon')
    elif gre_test != 'OK':
        print('🔴 路由器端DMVPN未正常连接')
        print('   可能原因:')
        print('   - 路由器DMVPN未启用或配置错误')
        print('   - 路由器加密参数不匹配')
        print('   - 路由器PSK密钥不正确 (应为: 123456)')
    else:
        print('✅ DMVPN连接正常')

finally:
    ssh.close()
