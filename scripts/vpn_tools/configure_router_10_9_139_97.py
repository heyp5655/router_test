# -*- coding: utf-8 -*-
"""
直接SSH调试DMVPN服务器，配置支持路由器10.9.139.97连接
"""
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVER_IP = '192.168.50.48'
USERNAME = 'yuxy'
PASSWORD = 'milesight123'
ROUTER_IP = '10.9.139.97'

def run_sudo_command(ssh, command):
    """执行需要sudo的命令"""
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

def run_command(ssh, command):
    """执行普通命令"""
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

print('=' * 80)
print('DMVPN服务器调试 - 配置支持路由器10.9.139.97')
print('=' * 80)
print()

try:
    # 1. 连接服务器
    print('🔌 [1/6] 连接服务器 192.168.50.48...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)
    print('  ✅ SSH连接成功')
    print()

    # 2. 检查当前配置
    print('📋 [2/6] 检查当前配置...')
    print('-' * 80)

    # 检查Racoon服务状态
    print('  检查Racoon服务状态:')
    stdout, _ = run_sudo_command(ssh, 'systemctl is-active racoon')
    if 'active' in stdout:
        print('    ✅ Racoon服务运行中')
    else:
        print('    ⚠️ Racoon服务未运行')

    # 检查当前PSK配置
    print('\n  当前PSK配置:')
    stdout, _ = run_command(ssh, 'cat /etc/racoon/psk.txt')
    has_router = False
    for line in stdout.strip().split('\n'):
        if line.strip() and not line.startswith('#'):
            print(f'    {line}')
            if ROUTER_IP in line:
                has_router = True

    if has_router:
        print(f'    ✅ 已包含路由器IP {ROUTER_IP}')
    else:
        print(f'    ⚠️ 未找到路由器IP {ROUTER_IP}')

    # 检查GRE隧道
    print('\n  GRE隧道状态:')
    stdout, _ = run_command(ssh, 'ip addr show gre1')
    if 'inet 10.0.0.1' in stdout:
        print('    ✅ GRE隧道已配置 (10.0.0.1/24)')
    else:
        print('    ⚠️ GRE隧道未配置或异常')

    print()

    # 3. 备份现有配置
    print('💾 [3/6] 备份现有配置...')
    print('-' * 80)
    timestamp = time.strftime('%Y%m%d_%H%M%S')

    stdout, _ = run_sudo_command(ssh, f'cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.backup.{timestamp}')
    print(f'  ✅ 备份 racoon.conf → racoon.conf.backup.{timestamp}')

    stdout, _ = run_sudo_command(ssh, f'cp /etc/racoon/psk.txt /etc/racoon/psk.txt.backup.{timestamp}')
    print(f'  ✅ 备份 psk.txt → psk.txt.backup.{timestamp}')
    print()

    # 4. 更新配置
    print('🔧 [4/6] 更新Racoon配置...')
    print('-' * 80)

    # 新的Racoon配置
    racoon_config = f"""# Racoon configuration for DMVPN with NAT traversal
# Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}
# Router IP: {ROUTER_IP}

log notify;
path include "/etc/racoon/";
path pre_shared_key "/etc/racoon/psk.txt";

# Listen on all interfaces
listen {{
    isakmp 0.0.0.0[500];
    isakmp_natt 0.0.0.0[4500];
}}

# Accept connections from any IP
remote anonymous {{
    exchange_mode main;
    lifetime time 10800 seconds;
    my_identifier address;

    # DPD (Dead Peer Detection)
    dpd_delay 30;
    dpd_retry 3;
    dpd_maxfail 6;

    # NAT Traversal - FORCE mode
    nat_traversal force;

    # Phase 1 proposals (multiple for compatibility)
    proposal {{
        encryption_algorithm aes256;
        hash_algorithm sha256;
        dh_group modp3072;
        authentication_method pre_shared_key;
    }}

    proposal {{
        encryption_algorithm aes192;
        hash_algorithm sha256;
        dh_group modp3072;
        authentication_method pre_shared_key;
    }}

    proposal {{
        encryption_algorithm aes128;
        hash_algorithm sha1;
        dh_group modp768;
        authentication_method pre_shared_key;
    }}
}}

# Phase 2 - IPSec SA
sainfo anonymous {{
    lifetime time 3600 seconds;
    encryption_algorithm aes256, aes192, aes128, 3des;
    authentication_algorithm hmac_sha256, hmac_sha1;
    compression_algorithm deflate;
}}
"""

    # 写入配置
    sftp = ssh.open_sftp()
    with sftp.open('/tmp/racoon.conf.new', 'w') as f:
        f.write(racoon_config)
    sftp.close()

    stdout, stderr = run_sudo_command(ssh, 'mv /tmp/racoon.conf.new /etc/racoon/racoon.conf')
    stdout, stderr = run_sudo_command(ssh, 'chmod 644 /etc/racoon/racoon.conf')
    print('  ✅ Racoon配置已更新')
    print('    - NAT-T模式: force')
    print('    - Phase 1: AES256/192/128 + SHA256/SHA1 + modp3072/768')
    print('    - Phase 2: AES256/192/128/3DES + SHA256/SHA1')

    # 更新PSK配置
    if not has_router:
        print('\n  添加路由器IP到PSK配置...')
        stdout, _ = run_command(ssh, 'cat /etc/racoon/psk.txt')
        psk_content = stdout.strip()

        # 添加新路由器IP
        psk_content += f'\n{ROUTER_IP}    123456    # Router WAN IP\n'

        sftp = ssh.open_sftp()
        with sftp.open('/tmp/psk.txt.new', 'w') as f:
            f.write(psk_content)
        sftp.close()

        stdout, stderr = run_sudo_command(ssh, 'mv /tmp/psk.txt.new /etc/racoon/psk.txt')
        stdout, stderr = run_sudo_command(ssh, 'chmod 600 /etc/racoon/psk.txt')
        print(f'    ✅ 已添加 {ROUTER_IP} → PSK: 123456')
    else:
        print(f'\n  ✅ PSK配置已包含路由器IP {ROUTER_IP}')

    print()

    # 5. 检查和配置GRE隧道
    print('🌐 [5/6] 检查GRE隧道...')
    print('-' * 80)

    stdout, _ = run_command(ssh, 'ip addr show gre1')

    if 'does not exist' in stdout or 'inet 10.0.0.1' not in stdout:
        print('  创建GRE隧道...')

        # 删除旧隧道
        run_sudo_command(ssh, 'ip link set gre1 down 2>/dev/null')
        run_sudo_command(ssh, 'ip tunnel del gre1 2>/dev/null')

        # 创建新隧道
        run_sudo_command(ssh, 'ip tunnel add gre1 mode gre local 192.168.50.48 key 123456')
        run_sudo_command(ssh, 'ip addr add 10.0.0.1/24 dev gre1')
        run_sudo_command(ssh, 'ip link set gre1 up')

        # 验证
        stdout, _ = run_command(ssh, 'ip addr show gre1')
        if 'inet 10.0.0.1' in stdout:
            print('    ✅ GRE隧道创建成功')
            print('    - 本地IP: 10.0.0.1/24')
            print('    - GRE密钥: 123456')
            print('    - Remote: any (自动学习)')
        else:
            print('    ❌ GRE隧道创建失败')
    else:
        print('  ✅ GRE隧道已存在')
        print('    - 本地IP: 10.0.0.1/24')

    print()

    # 6. 重启Racoon服务
    print('🔄 [6/6] 重启Racoon服务...')
    print('-' * 80)

    stdout, stderr = run_sudo_command(ssh, 'systemctl restart racoon')
    time.sleep(2)

    stdout, _ = run_sudo_command(ssh, 'systemctl is-active racoon')
    if 'active' in stdout:
        print('  ✅ Racoon服务已重启并运行中')
    else:
        print('  ❌ Racoon服务重启失败')
        print(f'  错误: {stderr}')

    print()

    # 7. 显示配置总结和验证步骤
    print('=' * 80)
    print('✅ 服务器配置完成！')
    print('=' * 80)
    print()
    print('📊 配置总结:')
    print('-' * 80)
    print(f'  服务器IP: {SERVER_IP}')
    print(f'  服务器GRE IP: 10.0.0.1/24')
    print(f'  路由器出口IP: {ROUTER_IP}')
    print(f'  PSK密钥: 123456')
    print(f'  GRE密钥: 123456')
    print()
    print('  IPSec配置:')
    print('    Phase 1: AES256/192/128, SHA256/SHA1, modp3072/768')
    print('    Phase 2: AES256/192/128/3DES, SHA256/SHA1')
    print('    NAT-T: force (强制模式)')
    print('-' * 80)
    print()

    print('🔍 监控连接状态:')
    print('-' * 80)
    print('  实时查看Racoon日志:')
    print('  $ sudo tail -f /var/log/syslog | grep racoon')
    print()
    print('  查看IPSec SA:')
    print('  $ sudo setkey -D')
    print()
    print('  测试GRE连通性:')
    print('  $ ping 10.0.0.3')
    print('-' * 80)
    print()

    # 开始监控日志
    print('📡 开始监控连接（60秒）...')
    print('=' * 80)
    print('等待路由器连接...\n')

    for i in range(1, 13):  # 12次 x 5秒 = 60秒
        print(f'[检查 {i}/12] - {time.strftime("%H:%M:%S")}')

        # 检查IPSec SA
        stdout, _ = run_sudo_command(ssh, f'setkey -D | grep -E "({ROUTER_IP})" | head -5')

        if stdout.strip():
            print('  🎉 检测到IPSec SA!')
            print('  ' + '-' * 76)
            for line in stdout.strip().split('\n')[:5]:
                print(f'  {line}')
            print('  ' + '-' * 76)

            # 测试GRE
            print('\n  测试GRE隧道 (10.0.0.3):')
            stdin, stdout_obj, stderr = ssh.exec_command('ping -c 3 -W 1 10.0.0.3')
            ping_output = stdout_obj.read().decode('utf-8', errors='ignore')

            for line in ping_output.split('\n'):
                if 'transmitted' in line or 'packets' in line:
                    print(f'    {line}')

            if '0% packet loss' in ping_output or '3 received' in ping_output:
                print('\n' + '=' * 80)
                print('🎉🎉🎉 DMVPN连接成功！🎉🎉🎉')
                print('=' * 80)
                print()
                print('✅ IPSec隧道: 已建立')
                print('✅ GRE隧道: 已连通')
                print(f'✅ 路由器IP: {ROUTER_IP}')
                print('✅ 可以互相通信')
                break
        else:
            print(f'  ⏳ 等待连接... (还未检测到{ROUTER_IP}的IPSec SA)')

        # 查看最近日志
        if i % 2 == 0:
            stdout, _ = run_sudo_command(ssh, 'tail -3 /var/log/syslog | grep racoon')
            if stdout.strip():
                last_log = stdout.strip().split('\n')[-1]
                if 'ERROR' in last_log:
                    print(f'  ⚠️ 日志: ...{last_log[-60:]}')
                elif 'ISAKMP' in last_log or 'IPsec' in last_log:
                    print(f'  ℹ️ 日志: ...{last_log[-60:]}')

        print()

        if i < 12:
            time.sleep(5)
    else:
        print('=' * 80)
        print('⏰ 监控结束（60秒）')
        print('=' * 80)
        print()
        print('💡 如果路由器还未连接，请检查:')
        print('  1. 路由器DMVPN是否已启用')
        print(f'  2. 路由器Hub地址是否配置为: {SERVER_IP}')
        print('  3. 路由器PSK密钥是否为: 123456')
        print('  4. 路由器加密参数是否匹配')
        print()
        print('  继续监控: sudo tail -f /var/log/syslog | grep racoon')

    ssh.close()
    print('\n' + '=' * 80)
    print('SSH连接已关闭')
    print('=' * 80)

except paramiko.AuthenticationException:
    print('❌ SSH认证失败')
except Exception as e:
    print(f'❌ 发生错误: {e}')
    import traceback
    traceback.print_exc()
